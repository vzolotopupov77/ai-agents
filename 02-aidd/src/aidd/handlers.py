from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import Message

from aidd.dialog_store import DialogStore
from aidd.llm_client import LLMClient

logger = logging.getLogger(__name__)


def register_handlers(
    router: Router,
    llm: LLMClient,
    store: DialogStore,
) -> None:
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
        store.add_turn(chat_id, user_text, reply)
        await message.answer(reply)
