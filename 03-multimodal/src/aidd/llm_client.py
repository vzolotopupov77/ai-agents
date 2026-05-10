from __future__ import annotations

import asyncio
import json
import logging
import re

from openai import AsyncOpenAI, BadRequestError, RateLimitError
from pydantic import ValidationError

from aidd.config import Config
from aidd.transaction_extract import TransactionExtract

logger = logging.getLogger(__name__)

# OpenRouter / часть моделей не отдаёт контент в формате strict structured output;
# json_object + суффикс системному промпту и ручной разбор надёжнее beta.parse.
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)

_EXTRACT_SYSTEM_SUFFIX = (
    "\n\n[Формат ответа] Ответь только одним JSON-объектом на русском там, где это текст "
    'для пользователя. Никакого Markdown вне JSON, никакого текста до или после скобок. '
    'Ключи: "found" (boolean), "reply" (string — всегда: подтверждение записи или совет). '
    'Если found=true: "flow" ("income"|"expense"), "amount" (number > 0), '
    '"tx_type" ("everyday"|"periodic"|"one-time"), "category" (string), '
    '"description" (string), "timestamp" (ISO-строка или null). '
    "Если found=false: остальные поля транзакции — null или опусти их."
)

# Бесплатные модели на OpenRouter часто отвечают 429; коротких SDK-retries мало.
_RATE_LIMIT_ATTEMPTS = 4
_RATE_LIMIT_BASE_DELAY_SEC = 3.0


def _extract_system_content(base_prompt: str) -> str:
    return base_prompt.rstrip() + _EXTRACT_SYSTEM_SUFFIX


def _json_candidates(raw: str) -> list[str]:
    """Варианты строк для парсинга JSON из ответа модели."""
    text = (raw or "").strip()
    out: list[str] = []
    if text:
        out.append(text)
    for m in _JSON_FENCE_RE.finditer(text):
        fenced = m.group(1).strip()
        if fenced:
            out.append(fenced)
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        out.append(text[start : end + 1])
    # сохраняем порядок, убираем дубликаты
    seen: set[str] = set()
    unique: list[str] = []
    for item in out:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def parse_transaction_extract_json(raw: str) -> TransactionExtract:
    """Разобрать ответ модели в TransactionExtract (строго или из fenced / первого объекта)."""
    errors: list[str] = []
    for candidate in _json_candidates(raw):
        try:
            return TransactionExtract.model_validate_json(candidate)
        except (json.JSONDecodeError, ValueError, ValidationError) as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            continue
    preview = (raw or "").strip().replace("\n", " ")[:120]
    logger.warning(
        "Cannot parse TransactionExtract JSON preview=%r errors=%s",
        preview,
        errors[-3:] if errors else [],
    )
    msg = "Model returned unparsable JSON for extraction"
    raise ValueError(msg)


class LLMClient:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._client = AsyncOpenAI(
            api_key=config.openrouter_api_key,
            base_url=config.openrouter_base_url,
            max_retries=0,
        )

    async def ask(
        self,
        user_text: str,
        history: list[dict[str, str]],
    ) -> str:
        logger.debug(
            "LLM request model=%s user_chars=%s history_len=%s",
            self._config.llm_model,
            len(user_text),
            len(history),
        )
        messages: list[dict[str, str]] = [
            {"role": "system", "content": self._config.system_prompt},
            *history,
            {"role": "user", "content": user_text},
        ]
        for attempt in range(_RATE_LIMIT_ATTEMPTS):
            try:
                response = await self._client.chat.completions.create(
                    model=self._config.llm_model,
                    messages=messages,
                    temperature=self._config.llm_temperature,
                    max_tokens=self._config.llm_max_tokens,
                )
            except RateLimitError as exc:
                if attempt + 1 >= _RATE_LIMIT_ATTEMPTS:
                    logger.error(
                        "LLM rate limited after %s attempts",
                        _RATE_LIMIT_ATTEMPTS,
                    )
                    raise
                delay = _RATE_LIMIT_BASE_DELAY_SEC * (2**attempt)
                ra = None
                resp = exc.response
                if resp is not None:
                    ra = resp.headers.get("retry-after")
                if ra is not None:
                    try:
                        delay = max(delay, float(ra))
                    except ValueError:
                        pass
                logger.warning(
                    "LLM rate limited (429), retry in %.1f s, attempt %s/%s",
                    delay,
                    attempt + 1,
                    _RATE_LIMIT_ATTEMPTS,
                )
                await asyncio.sleep(delay)
                continue

            message = response.choices[0].message
            content = message.content
            if not content:
                logger.warning("LLM returned empty content")
                return ""
            return content

    async def extract(
        self,
        user_text: str,
        history: list[dict[str, str]],
    ) -> TransactionExtract:
        """Извлечь транзакцию из текста через structured output.

        Всегда возвращает TransactionExtract с полем `reply`.
        Поднимает исключение при сбое API (обрабатывается в обработчике).
        """
        logger.debug(
            "LLM extract model=%s user_chars=%s history_len=%s",
            self._config.llm_model,
            len(user_text),
            len(history),
        )
        messages: list[dict[str, str]] = [
            {"role": "system", "content": _extract_system_content(self._config.system_prompt)},
            *history,
            {"role": "user", "content": user_text},
        ]
        for attempt in range(_RATE_LIMIT_ATTEMPTS):
            try:
                try:
                    response = await self._client.chat.completions.create(
                        model=self._config.llm_model,
                        messages=messages,
                        temperature=self._config.llm_temperature,
                        max_tokens=self._config.llm_max_tokens,
                        response_format={"type": "json_object"},
                    )
                except BadRequestError:
                    logger.warning(
                        "json_object response_format rejected, retrying without it "
                        "(model=%s)",
                        self._config.llm_model,
                    )
                    response = await self._client.chat.completions.create(
                        model=self._config.llm_model,
                        messages=messages,
                        temperature=self._config.llm_temperature,
                        max_tokens=self._config.llm_max_tokens,
                    )
            except RateLimitError as exc:
                if attempt + 1 >= _RATE_LIMIT_ATTEMPTS:
                    logger.error(
                        "LLM extract rate limited after %s attempts",
                        _RATE_LIMIT_ATTEMPTS,
                    )
                    raise
                delay = _RATE_LIMIT_BASE_DELAY_SEC * (2**attempt)
                ra = None
                resp = exc.response
                if resp is not None:
                    ra = resp.headers.get("retry-after")
                if ra is not None:
                    try:
                        delay = max(delay, float(ra))
                    except ValueError:
                        pass
                logger.warning(
                    "LLM extract rate limited (429), retry in %.1f s, attempt %s/%s",
                    delay,
                    attempt + 1,
                    _RATE_LIMIT_ATTEMPTS,
                )
                await asyncio.sleep(delay)
                continue

            content = response.choices[0].message.content
            if not content:
                logger.warning("LLM extract returned empty content")
                msg = "Model returned empty structured output"
                raise ValueError(msg)

            result = parse_transaction_extract_json(content)
            logger.debug("LLM extract found=%s", result.found)
            return result

        # Недостижимо, но требуется для mypy
        msg = "extract: exhausted retry loop without result"
        raise RuntimeError(msg)
