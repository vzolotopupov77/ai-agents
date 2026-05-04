from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import Message

from aidd.llm_client import LLMClient

logger = logging.getLogger(__name__)


def register_handlers(router: Router, llm: LLMClient) -> None:
    @router.message(F.text)
    async def handle_text(message: Message) -> None:
        user_text = message.text or ""
        logger.debug("Inbound text message, length=%s", len(user_text))
        try:
            reply = await llm.ask(user_text)
        except Exception:
            logger.exception("LLM request failed")
            await message.answer(
                "Сервис временно недоступен. Попробуйте позже.",
            )
            return
        await message.answer(reply)
