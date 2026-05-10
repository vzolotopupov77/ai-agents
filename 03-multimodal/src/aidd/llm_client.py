from __future__ import annotations

import asyncio
import logging

from openai import AsyncOpenAI, RateLimitError

from aidd.config import Config
from aidd.transaction_extract import TransactionExtract

logger = logging.getLogger(__name__)

# Бесплатные модели на OpenRouter часто отвечают 429; коротких SDK-retries мало.
_RATE_LIMIT_ATTEMPTS = 4
_RATE_LIMIT_BASE_DELAY_SEC = 3.0


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
            {"role": "system", "content": self._config.system_prompt},
            *history,
            {"role": "user", "content": user_text},
        ]
        for attempt in range(_RATE_LIMIT_ATTEMPTS):
            try:
                response = await self._client.beta.chat.completions.parse(
                    model=self._config.llm_model,
                    messages=messages,
                    response_format=TransactionExtract,
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

            result = response.choices[0].message.parsed
            if result is None:
                logger.warning("LLM extract returned null parsed result")
                msg = "Model returned null structured output"
                raise ValueError(msg)
            logger.debug("LLM extract found=%s", result.found)
            return result

        # Недостижимо, но требуется для mypy
        msg = "extract: exhausted retry loop without result"
        raise RuntimeError(msg)
