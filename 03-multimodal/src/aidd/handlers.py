from __future__ import annotations

import html
import logging
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from aidd.dialog_store import DialogStore
from aidd.llm_client import LLMClient
from aidd.transaction import Transaction
from aidd.transaction_extract import TransactionExtract
from aidd.stt_client import SttClient
from aidd.transaction_store import TransactionStore, format_transaction_confirmation

logger = logging.getLogger(__name__)

# https://core.telegram.org/bots/api#sendmessage
_TELEGRAM_MAX_MESSAGE_LENGTH = 4096

_TABLE_SEP_RE = re.compile(r"^\|?\s*:?[\-:]+[\s\-:|]*$")
_MD_HEADER_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_BR_TAGS_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
# Курсив *текст*, не часть ** (ASCII звёздочки, как у моделей)
_ITALIC_MD_RE = re.compile(r"(?<!\*)\*(?!\*)([^*\n]+?)\*(?!\*)")


def _escape_plain_with_italic(t: str) -> str:
    """Экранирует фрагмент и превращает *курсив* в <i>…</i>."""
    if not t:
        return ""
    parts: list[str] = []
    pos = 0
    for m in _ITALIC_MD_RE.finditer(t):
        parts.append(html.escape(t[pos : m.start()]))
        parts.append("<i>" + html.escape(m.group(1)) + "</i>")
        pos = m.end()
    parts.append(html.escape(t[pos:]))
    return "".join(parts)


def _md_links_to_html_segment(s: str) -> str:
    """Экранирует текст и превращает [label](url) в <a href>. Только http(s)."""

    def repl(m: re.Match[str]) -> str:
        label = html.escape(m.group(1))
        url = m.group(2).strip()
        if not url.startswith(("http://", "https://")):
            return html.escape(m.group(0))
        u_attr = html.escape(url, quote=True)
        return f'<a href="{u_attr}">{label}</a>'

    pos = 0
    buf: list[str] = []
    for m in _MD_LINK_RE.finditer(s):
        buf.append(_escape_plain_with_italic(s[pos : m.start()]))
        buf.append(repl(m))
        pos = m.end()
    buf.append(_escape_plain_with_italic(s[pos:]))
    return "".join(buf)


def _inline_markdown_to_html_line(line: str) -> str:
    """Жирный ** **, курсив * *, ссылки [text](url); при непарном ** — без жирного."""
    if line.count("**") % 2 != 0:
        return _md_links_to_html_segment(line)

    parts = re.split(r"(\*\*.+?\*\*)", line)
    res: list[str] = []
    for p in parts:
        if len(p) >= 4 and p.startswith("**") and p.endswith("**"):
            inner = p[2:-2]
            res.append("<b>" + _md_links_to_html_segment(inner) + "</b>")
        elif p:
            res.append(_md_links_to_html_segment(p))
    return "".join(res)


def _markdownish_to_telegram_html(text: str) -> str:
    """Типичный Markdown от LLM -> HTML, поддерживаемый Telegram-ботами (без таблиц)."""
    if not text:
        return ""
    # Модель часто вставляет <br>; в HTML Telegram это не поддерживается / видно как текст
    text = _BR_TAGS_RE.sub("\n", text)
    lines_out: list[str] = []
    for raw_line in text.split("\n"):
        line = raw_line.rstrip("\r")
        stripped = line.strip()
        if not stripped:
            lines_out.append("")
            continue
        if stripped in ("---", "***", "___"):
            lines_out.append("")
            continue
        if stripped.startswith(">"):
            body = stripped[1:].lstrip()
            if body:
                lines_out.append(
                    "<blockquote>"
                    + _inline_markdown_to_html_line(body)
                    + "</blockquote>",
                )
            else:
                lines_out.append("")
            continue
        if _TABLE_SEP_RE.match(stripped):
            continue
        if "|" in stripped and stripped.count("|") >= 2:
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            cells = [c for c in cells if c]
            if cells:
                lines_out.append(
                    "• "
                    + " · ".join(
                        _inline_markdown_to_html_line(c) for c in cells
                    ),
                )
            continue
        m = _MD_HEADER_RE.match(stripped)
        if m:
            title_raw = m.group(2).strip()
            lines_out.append("<b>" + _inline_markdown_to_html_line(title_raw) + "</b>")
            continue
        lines_out.append(_inline_markdown_to_html_line(line))
    return "\n".join(lines_out)


def _strip_html_to_plain_fallback(chunk: str) -> str:
    text = re.sub(r"<[^>]+>", "", chunk)
    return html.unescape(text)


def _chunk_text_for_telegram(text: str, max_len: int = _TELEGRAM_MAX_MESSAGE_LENGTH) -> list[str]:
    """Разбить текст на части, каждая не длиннее лимита Telegram для одного сообщения."""
    if not text:
        return []
    if max_len < 1:
        msg = "max_len must be at least 1"
        raise ValueError(msg)
    chunks: list[str] = []
    buf: list[str] = []
    buf_len = 0
    for line in text.splitlines(keepends=True):
        if len(line) > max_len:
            if buf:
                chunks.append("".join(buf))
                buf = []
                buf_len = 0
            for i in range(0, len(line), max_len):
                chunks.append(line[i : i + max_len])
            continue
        if buf_len + len(line) > max_len:
            chunks.append("".join(buf))
            buf = [line]
            buf_len = len(line)
        else:
            buf.append(line)
            buf_len += len(line)
    if buf:
        chunks.append("".join(buf))
    return chunks


async def _answer_in_chunks(message: Message, text: str) -> None:
    for part in _chunk_text_for_telegram(text):
        html_part = _markdownish_to_telegram_html(part)
        try:
            await message.answer(html_part, parse_mode=ParseMode.HTML)
        except TelegramBadRequest:
            logger.warning(
                "Telegram rejected HTML (chunk len=%s), sending plain fallback",
                len(html_part),
            )
            plain = _strip_html_to_plain_fallback(html_part)
            for plain_chunk in _chunk_text_for_telegram(plain):
                await message.answer(plain_chunk)


def _assistant_reply_after_extract(
    extract: TransactionExtract,
    chat_id: int,
    tx_store: TransactionStore,
    *,
    log_added_prefix: str = "Transaction added",
) -> str | None:
    """Текст ответа пользователю или None, если показывать нейтральную ошибку.

    Некоторые модели (например малые веса в Ollama) возвращают found=true и поля
    транзакции, но оставляют reply пустым — тогда используем подтверждение из учёта.
    """
    reply = (extract.reply or "").strip()

    if extract.found:
        tx = _build_transaction(extract)
        if tx is not None:
            tx_store.add(chat_id, tx)
            out = format_transaction_confirmation(tx)
            logger.debug(
                "%s chat_id=%s flow=%s amount=%s category=%s",
                log_added_prefix,
                chat_id,
                tx.flow,
                tx.amount,
                tx.category,
            )
            return out
        logger.warning(
            "LLM returned found=True but transaction fields incomplete, chat_id=%s",
            chat_id,
        )
        return reply if reply else None

    return reply if reply else None


def register_handlers(
    router: Router,
    llm: LLMClient,
    store: DialogStore,
    tx_store: TransactionStore,
    stt: SttClient | None = None,
) -> None:
    @router.message(CommandStart())
    async def handle_start(message: Message) -> None:
        parts = [
            "Привет! Я финансовый советник. Рассказывайте о тратах и доходах — я буду вести учёт.",
        ]
        if stt is not None:
            parts.append(
                "Можно отправить голосовое сообщение — распознаю речь и отвечу как на текст.",
            )
        parts.extend(
            [
                "Можно прислать фото чека — попробую из него записать операцию.",
                "Команда /report покажет ваш баланс.",
            ],
        )
        await message.answer("\n".join(parts))

    @router.message(Command("report"))
    async def handle_report(message: Message) -> None:
        text = tx_store.report_text(message.chat.id)
        await message.answer(text)

    async def process_text_turn(message: Message, user_text: str) -> None:
        chat_id = message.chat.id
        logger.debug(
            "Inbound text turn, chat_id=%s length=%s",
            chat_id,
            len(user_text),
        )
        history = store.get(chat_id)
        try:
            extract = await llm.extract(user_text, history)
        except Exception:
            logger.exception("LLM extract failed")
            await message.answer("Сервис временно недоступен. Попробуйте позже.")
            return

        assistant_reply = _assistant_reply_after_extract(extract, chat_id, tx_store)
        if assistant_reply is None:
            logger.warning("LLM extract returned empty reply, chat_id=%s", chat_id)
            await message.answer("Сервис не вернул ответ. Попробуйте позже.")
            return

        store.add_turn(chat_id, user_text, assistant_reply)
        await _answer_in_chunks(message, assistant_reply)

    @router.message(F.text)
    async def handle_text(message: Message) -> None:
        await process_text_turn(message, message.text or "")

    @router.message(F.voice)
    async def handle_voice(message: Message) -> None:
        if stt is None:
            await message.answer("Голосовые сообщения не поддерживаются.")
            return

        chat_id = message.chat.id
        voice = message.voice
        if voice is None:
            return

        logger.debug(
            "Inbound voice message, chat_id=%s file_id=%s duration=%s",
            chat_id,
            voice.file_id,
            getattr(voice, "duration", None),
        )

        try:
            buf = await message.bot.download(voice)
            if buf is None:
                logger.warning("Voice download returned None chat_id=%s", chat_id)
                await message.answer(
                    "Не удалось загрузить голосовое сообщение. Попробуйте ещё раз.",
                )
                return
            audio_bytes = buf.read()
        except Exception:
            logger.exception("Voice download failed chat_id=%s", chat_id)
            await message.answer(
                "Не удалось загрузить голосовое сообщение. Попробуйте ещё раз.",
            )
            return

        try:
            user_text = await stt.transcribe(audio_bytes)
        except Exception:
            logger.exception("STT transcribe failed chat_id=%s", chat_id)
            await message.answer("Сервис временно недоступен. Попробуйте позже.")
            return

        if not user_text.strip():
            await message.answer(
                "Не удалось распознать речь. Попробуйте ещё раз или отправьте текст.",
            )
            return

        await process_text_turn(message, user_text)

    @router.message(F.photo)
    async def handle_photo(message: Message) -> None:
        chat_id = message.chat.id
        photo = message.photo[-1]
        logger.debug(
            "Inbound photo message, chat_id=%s file_id=%s",
            chat_id,
            photo.file_id,
        )
        try:
            buf = await message.bot.download(photo)
            if buf is None:
                logger.warning("Photo download returned None chat_id=%s", chat_id)
                await message.answer("Не удалось загрузить фото. Попробуйте ещё раз.")
                return
            image_bytes = buf.read()
        except Exception:
            logger.exception("Photo download failed chat_id=%s", chat_id)
            await message.answer("Не удалось загрузить фото. Попробуйте ещё раз.")
            return

        history = store.get(chat_id)
        try:
            extract = await llm.extract_from_image(image_bytes, "image/jpeg", history)
        except Exception:
            logger.exception("VLM extract failed chat_id=%s", chat_id)
            await message.answer("Сервис временно недоступен. Попробуйте позже.")
            return

        assistant_reply = _assistant_reply_after_extract(
            extract,
            chat_id,
            tx_store,
            log_added_prefix="Transaction from photo",
        )
        if assistant_reply is None:
            logger.warning("VLM extract returned empty reply, chat_id=%s", chat_id)
            await message.answer("Сервис не вернул ответ. Попробуйте позже.")
            return

        store.add_turn(chat_id, "[фото чека]", assistant_reply)
        await _answer_in_chunks(message, assistant_reply)


def _build_transaction(extract: TransactionExtract) -> Transaction | None:
    """Собрать Transaction из structured output; None при неполных данных."""
    if extract.flow is None or extract.amount is None:
        return None
    tx_type = extract.tx_type or "everyday"
    try:
        amount = Decimal(str(extract.amount))
    except InvalidOperation:
        logger.warning("Invalid amount in extract: %s", extract.amount)
        return None
    if amount <= 0:
        logger.warning("Non-positive amount in extract: %s", amount)
        return None

    ts: datetime
    if extract.timestamp:
        try:
            ts = datetime.fromisoformat(extract.timestamp)
        except ValueError:
            logger.warning("Cannot parse timestamp %r, using now", extract.timestamp)
            ts = datetime.now()
    else:
        ts = datetime.now()

    return Transaction(
        timestamp=ts,
        flow=extract.flow,
        amount=amount,
        tx_type=tx_type,
        category=extract.category or "прочее",
        description=extract.description or "",
    )
