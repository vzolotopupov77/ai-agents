"""
Инструменты для ReAct агента

Инструменты - это функции, которые агент может вызывать для получения информации.
Декоратор @tool из LangChain автоматически создает описание для LLM.
"""
import json
import logging
import os
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from langchain_core.tools import tool

import rag

logger = logging.getLogger(__name__)

CBR_XML_URL = "https://www.cbr.ru/scripts/XML_daily.asp"

_CBR_XML_URL_FALLBACKS = (
    "https://www.cbr.ru/scripts/XML_daily.asp",
    "https://cbr.ru/scripts/XML_daily.asp",
)


def _cbr_feed_urls() -> tuple[str, ...]:
    """Один URL из CBR_XML_URL или цепочка резервных."""
    override = os.getenv("CBR_XML_URL", "").strip()
    if override:
        return (override,)
    return _CBR_XML_URL_FALLBACKS


# Кеш на время жизни процесса: курсы (руб. за 1 единицу валюты), дата строкой и источник
_rates_rub_per_unit: Optional[dict[str, float]] = None
_cache_calendar_date: Optional[date] = None
_rates_date_label: str = ""
_rates_source_kind: str = "cbr"  # "cbr" | "public_api"

# Для диагностики (успешные HTTP-загрузки курсов с момента старта процесса)
_http_fetch_count: int = 0


def reset_cbr_rates_cache_for_tests() -> None:
    """Сбросить кеш курсов (только для тестов вручную)."""
    global _rates_rub_per_unit, _cache_calendar_date, _rates_date_label, _rates_source_kind
    _rates_rub_per_unit = None
    _cache_calendar_date = None
    _rates_date_label = ""
    _rates_source_kind = "cbr"


def get_cbr_http_fetch_count() -> int:
    """Счётчик успешных HTTP-загрузок курсов (ЦБ или запасной API) с момента старта процесса."""
    return _http_fetch_count


def _parse_cbr_daily_xml(xml_bytes: bytes) -> tuple[dict[str, float], str]:
    root = ET.fromstring(xml_bytes)
    date_attr = root.get("Date", "").strip()
    rates: dict[str, float] = {}
    for valute in root.findall("Valute"):
        code_el = valute.find("CharCode")
        nominal_el = valute.find("Nominal")
        value_el = valute.find("Value")
        if code_el is None or code_el.text is None:
            continue
        code = code_el.text.strip().upper()
        nominal_s = nominal_el.text if nominal_el is not None and nominal_el.text else "1"
        value_s = value_el.text if value_el is not None and value_el.text else "0"
        nominal_i = max(int(nominal_s.strip()), 1)
        value_f = float(value_s.strip().replace(",", "."))
        rates[code] = value_f / nominal_i
    return rates, date_attr


def _fetch_rates_from_cbr() -> tuple[dict[str, float], str]:
    global _http_fetch_count
    headers = {"User-Agent": "Mozilla/5.0 (compatible; rag-bot/1.0)"}
    failures: list[str] = []
    last_exc: Exception | None = None

    for url in _cbr_feed_urls():
        req = Request(url, headers=headers)
        try:
            with urlopen(req, timeout=30) as resp:
                xml_bytes = resp.read()
        except HTTPError as e:
            failures.append(f"{url}: HTTP {e.code}")
            last_exc = e
            continue
        except URLError as e:
            failures.append(f"{url}: {e.reason!s}")
            last_exc = e
            continue

        try:
            rates, label = _parse_cbr_daily_xml(xml_bytes)
        except Exception as e:
            failures.append(f"{url}: ошибка разбора XML ({e})")
            last_exc = e
            continue

        if not rates:
            failures.append(f"{url}: пустой список валют")
            continue

        _http_fetch_count += 1
        return rates, label or "сегодня"

    hint = (
        "Частая причина — DNS не находит хост cbr.ru (getaddrinfo / 11001): "
        "интернет, VPN, корпоративный DNS или переменная CBR_XML_URL."
    )
    detail = "; ".join(failures) if failures else repr(last_exc)
    raise RuntimeError(f"{hint} Детали: {detail}") from last_exc


def _rub_per_unit_from_rates_vs_rub(rates_foreign_per_one_rub: dict[str, float]) -> dict[str, float]:
    """
    В ответе API base=RUB: rates[X] — сколько единиц X за 1 RUB.
    Нужно RUB за 1 X → 1 / rates[X].
    """
    out: dict[str, float] = {"RUB": 1.0}
    for code, amt in rates_foreign_per_one_rub.items():
        c = str(code).strip().upper()
        if c == "RUB":
            continue
        try:
            v = float(amt)
        except (TypeError, ValueError):
            continue
        if v > 0:
            out[c] = 1.0 / v
    return out


def _fetch_rates_from_public_fallback() -> tuple[dict[str, float], str]:
    """Запасной источник: JSON с базой RUB (если ЦБ недоступен из сети)."""
    global _http_fetch_count
    url = os.getenv(
        "EXCHANGE_FALLBACK_URL",
        "https://api.exchangerate-api.com/v4/latest/RUB",
    ).strip()
    headers = {"User-Agent": "Mozilla/5.0 (compatible; rag-bot/1.0)"}
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=30) as resp:
            raw = resp.read()
    except HTTPError as e:
        raise RuntimeError(f"Запасной API курсов: HTTP {e.code} ({url})") from e
    except URLError as e:
        raise RuntimeError(f"Запасной API курсов: сеть {e.reason!s} ({url})") from e

    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Запасной API курсов: неверный JSON ({url})") from e

    base = str(data.get("base", "")).strip().upper()
    rates_blob = data.get("rates") or {}
    if not isinstance(rates_blob, dict):
        raise RuntimeError("Запасной API курсов: нет объекта rates")

    date_label = str(data.get("date", "") or "").strip() or "сегодня"

    # Ожидаем base=RUB; иначе пересчитываем через RUB если он есть в rates
    if base == "RUB":
        rub_per_unit = _rub_per_unit_from_rates_vs_rub(rates_blob)
    elif "RUB" in rates_blob:
        rub_per_one_base = float(rates_blob["RUB"])
        if rub_per_one_base <= 0:
            raise RuntimeError("Запасной API: некорректный курс к RUB")
        rub_per_unit = {"RUB": 1.0}
        for code, amt in rates_blob.items():
            c = str(code).strip().upper()
            if c == "RUB":
                continue
            try:
                v = float(amt)
            except (TypeError, ValueError):
                continue
            if v > 0:
                foreign_per_one_rub = v / rub_per_one_base
                rub_per_unit[c] = 1.0 / foreign_per_one_rub
    else:
        raise RuntimeError(
            f"Запасной API ({url}): ожидалась база RUB или поле rates.RUB, получено base={base!r}"
        )

    if len(rub_per_unit) < 3:
        raise RuntimeError("Запасной API курсов: слишком мало валют в ответе")

    _http_fetch_count += 1
    return rub_per_unit, date_label


def _fetch_rates_with_fallback() -> tuple[dict[str, float], str, str]:
    """
    Сначала официальный XML ЦБ РФ, при ошибке — открытый JSON с базой RUB.

    Returns:
        rates_rub_per_unit, date_label, source_kind ("cbr" | "public_api")
    """
    cbr_err: RuntimeError | None = None
    try:
        rates, label = _fetch_rates_from_cbr()
        return rates, label or "сегодня", "cbr"
    except RuntimeError as e:
        cbr_err = e
        logger.warning("Курсы ЦБ РФ недоступны, используем запасной источник: %s", e)

    try:
        rates, label = _fetch_rates_from_public_fallback()
        return rates, label, "public_api"
    except RuntimeError as e:
        chain = f"ЦБ РФ: {cbr_err}; запасной API: {e}" if cbr_err else str(e)
        raise RuntimeError(chain) from e


def _get_rates_cached() -> tuple[dict[str, float], str, str]:
    global _rates_rub_per_unit, _cache_calendar_date, _rates_date_label, _rates_source_kind

    today = date.today()
    if (
        _rates_rub_per_unit is not None
        and _cache_calendar_date == today
        and _rates_date_label
    ):
        return _rates_rub_per_unit, _rates_date_label, _rates_source_kind

    rates, label, kind = _fetch_rates_with_fallback()
    _rates_rub_per_unit = rates
    _cache_calendar_date = today
    _rates_date_label = label
    _rates_source_kind = kind
    logger.info(
        "Курсы валют: %d кодов, дата '%s', источник=%s",
        len(rates),
        label,
        kind,
    )
    return rates, label, kind


def _rate_to_rub(code: str, rates: dict[str, float]) -> Optional[float]:
    if code == "RUB":
        return 1.0
    return rates.get(code)


def _format_money_decimal(value: float) -> str:
    q = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{q:.2f}".replace(",", ".")


def _convert_impl(
    amount: float,
    from_currency: str,
    to_currency: str,
) -> str:
    """Внутренняя логика конвертации (строка для агента либо сообщение об ошибке)."""
    if amount <= 0:
        return "Укажите положительную сумму для конвертации."

    frm = from_currency.strip().upper()
    to = to_currency.strip().upper()
    if not frm or not to:
        return "Укажите коды валют (например USD, EUR, RUB)."

    if frm == "RUB" and to == "RUB":
        v = _format_money_decimal(amount)
        return f"{v} RUB = {v} RUB (одинаковая валюта, без обращения к ЦБ РФ)."

    try:
        rates, rates_date, source_kind = _get_rates_cached()
    except RuntimeError as e:
        logger.warning("Не удалось загрузить курсы валют: %s", e)
        return f"Не удалось получить курсы валют: {e}"
    except Exception as e:
        logger.error("Не удалось загрузить курсы валют: %s", e, exc_info=True)
        return f"Не удалось получить курсы валют: {e}"

    if source_kind == "cbr":
        meta = f"курс ЦБ РФ на {rates_date}"
        src_short = "ЦБ РФ"
    else:
        meta = (
            f"оценочный курс по exchangerate-api.com на {rates_date} "
            "(не официальный курс Банка России)"
        )
        src_short = "источник курсов"

    rf = _rate_to_rub(frm, rates)
    rt = _rate_to_rub(to, rates)
    missing: list[str] = []
    if rf is None:
        missing.append(frm)
    if rt is None:
        missing.append(to)
    if missing:
        codes = ", ".join(sorted(set(missing)))
        return (
            f"Валюта не найдена в данных ({src_short}) на {rates_date}: {codes}. "
            f"Используйте трёхбуквенные коды ISO 4217 (USD, EUR, KZT, …)."
        )

    rub_amount = amount * rf
    if to == "RUB":
        out = rub_amount
    else:
        out = rub_amount / rt

    out_s = _format_money_decimal(out)
    parts = []

    def line_for(curr: str, r: Optional[float]) -> str:
        if curr == "RUB" or r is None:
            return ""
        rr = _format_money_decimal(r)
        return f"1 {curr} = {rr} RUB"

    if frm != "RUB":
        parts.append(line_for(frm, rf))
    if to != "RUB":
        parts.append(line_for(to, rt))
    rate_expl = "; ".join(p for p in parts if p)

    head = (
        f"{_format_money_decimal(amount)} {frm} = {out_s} {to} "
        f"({meta}"
    )
    if rate_expl:
        head += f": {rate_expl}"
    head += ")."
    return head


@tool
def rag_search(query: str) -> str:
    """
    Ищет информацию в документах Сбербанка (условия кредитов, вкладов и других банковских продуктов).
    
    Возвращает JSON со списком источников, где каждый источник содержит:
    - source: имя файла
    - page: номер страницы (только для PDF)
    - page_content: текст документа
    """
    try:
        # Получаем релевантные документы через RAG (retrieval + reranking)
        documents = rag.retrieve_documents(query)

        if not documents:
            return json.dumps({"sources": []}, ensure_ascii=False)

        # Формируем структурированный ответ для агента
        sources = []
        for doc in documents:
            source_data = {
                "source": doc.metadata.get("source", "Unknown"),
                "page_content": doc.page_content  # Полный текст документа
            }
            # page только для PDF (у JSON документов его нет)
            if "page" in doc.metadata:
                source_data["page"] = doc.metadata["page"]
            sources.append(source_data)

        # ensure_ascii=False для корректной кириллицы
        return json.dumps({"sources": sources}, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Error in rag_search: {e}", exc_info=True)
        return json.dumps({"sources": []}, ensure_ascii=False)


@tool
def currency_converter(amount: float, from_currency: str, to_currency: str) -> str:
    """
    Конвертирует сумму из одной валюты в другую в рублёвом эквиваленте на текущую дату.

    Сначала используются официальные курсы Банка России (XML); если cbr.ru недоступен,
    применяется открытый JSON-API с базой RUB (см. EXCHANGE_FALLBACK_URL) — это ориентировочные
    рыночные кросс-курсы, не официальное установление ЦБ.

    Аргументы:
    - amount: числовая сумма (например 100 или 499.99)
    - from_currency: трёхбуквенный код ISO 4217 валюты, из которой конвертируем (USD, EUR, KZT …)
    - to_currency: трёхбуквенный код ISO 4217 целевой валюты (часто RUB)

    Возвращает строку с суммой и пояснением источника курса (без финансовых консультаций).
    """
    try:
        return _convert_impl(amount, from_currency, to_currency)
    except Exception as e:
        logger.error(f"Ошибка в currency_converter: {e}", exc_info=True)
        return f"Ошибка конвертации валют: {e}"
