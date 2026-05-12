from __future__ import annotations

import logging
import sys

from aiogram import Bot, Dispatcher, Router
from dotenv import load_dotenv

from aidd.config import Config
from aidd.dialog_store import DialogStore
from aidd.handlers import register_handlers
from aidd.llm_client import LLMClient
from aidd.stt_client import SttClient
from aidd.transaction_store import TransactionStore


def _configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), None)
    if not isinstance(level, int):
        level = logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )


async def main() -> None:
    load_dotenv()
    config = Config.from_env()
    _configure_logging(config.log_level)

    log = logging.getLogger(__name__)
    log.info("Starting polling")

    llm = LLMClient(config)
    store = DialogStore(config.max_history_messages)
    tx_store = TransactionStore()
    stt = SttClient(config.stt_base_url) if config.stt_base_url else None
    router = Router()
    register_handlers(router, llm, store, tx_store, stt=stt)

    dp = Dispatcher()
    dp.include_router(router)

    async with Bot(token=config.telegram_bot_token) as bot:
        await dp.start_polling(bot)
