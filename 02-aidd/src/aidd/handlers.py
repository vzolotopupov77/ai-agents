from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from aidd.dialog_store import DialogStore
from aidd.llm_client import LLMClient

logger = logging.getLogger(__name__)

# https://core.telegram.org/bots/api#sendmessage
_TELEGRAM_MAX_MESSAGE_LENGTH = 4096


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
        await message.answer(part)


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
