from __future__ import annotations

import os
from dataclasses import dataclass


def _require(name: str) -> str:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        msg = f"Missing or empty required environment variable: {name}"
        raise RuntimeError(msg)
    return value


def _parse_int(name: str) -> int:
    raw = _require(name)
    try:
        return int(raw)
    except ValueError as exc:
        msg = f"Environment variable {name} must be an integer, got {raw!r}"
        raise RuntimeError(msg) from exc


def _parse_float(name: str) -> float:
    raw = _require(name)
    try:
        return float(raw)
    except ValueError as exc:
        msg = f"Environment variable {name} must be a number, got {raw!r}"
        raise RuntimeError(msg) from exc


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str
    llm_api_key: str
    llm_base_url: str
    llm_model: str
    vlm_model: str
    system_prompt: str
    max_history_messages: int
    log_level: str
    llm_temperature: float
    llm_max_tokens: int

    @classmethod
    def from_env(cls) -> Config:
        return cls(
            telegram_bot_token=_require("TELEGRAM_BOT_TOKEN"),
            llm_api_key=_require("LLM_API_KEY"),
            llm_base_url=_require("LLM_BASE_URL"),
            llm_model=_require("LLM_MODEL"),
            vlm_model=_require("VLM_MODEL"),
            system_prompt=_require("SYSTEM_PROMPT"),
            max_history_messages=_parse_int("MAX_HISTORY_MESSAGES"),
            log_level=_require("LOG_LEVEL"),
            llm_temperature=_parse_float("LLM_TEMPERATURE"),
            llm_max_tokens=_parse_int("LLM_MAX_TOKENS"),
        )
