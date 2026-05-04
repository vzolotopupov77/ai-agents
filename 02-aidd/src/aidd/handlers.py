from __future__ import annotations

import html
import logging
import re

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.types import Message

from aidd.dialog_store import DialogStore
from aidd.llm_client import LLMClient

logger = logging.getLogger(__name__)

# https://core.telegram.org/bots/api#sendmessage
_TELEGRAM_MAX_MESSAGE_LENGTH = 4096

_TABLE_SEP_RE = re.compile(r"^\|?\s*:?[\-:]+[\s\-:|]*$")
_MD_HEADER_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_BR_TAGS_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)


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
        buf.append(html.escape(s[pos : m.start()]))
        buf.append(repl(m))
        pos = m.end()
    buf.append(html.escape(s[pos:]))
    return "".join(buf)


def _inline_markdown_to_html_line(line: str) -> str:
    """Жирный ** ** и ссылки [text](url); при непарном ** — строка без жирного, ссылки обрабатываются."""
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


def register_handlers(
    router: Router,
    llm: LLMClient,
    store: DialogStore,
) -> None:
    @router.message(CommandStart())
    async def handle_start(message: Message) -> None:
        await message.answer(
            "Привет! Я коуч карьерного развития. Помогу с резюме, подготовкой к интервью или стратегией поиска работы. С чего начнём?",
        )

    @router.message(F.text)
    async def handle_text(message: Message) -> None:
        user_text = message.text or ""
        chat_id = message.chat.id
        logger.debug(
            "Inbound text message, chat_id=%s length=%s",
            chat_id,
            len(user_text),
        )
        history = store.get(chat_id)
        try:
            reply = await llm.ask(user_text, history)
        except Exception:
            logger.exception("LLM request failed")
            await message.answer(
                "Сервис временно недоступен. Попробуйте позже.",
            )
            return
        if not reply:
            logger.warning("LLM returned empty reply, chat_id=%s", chat_id)
            await message.answer(
                "Сервис не вернул ответ. Попробуйте позже.",
            )
            return
        store.add_turn(chat_id, user_text, reply)
        await _answer_in_chunks(message, reply)
