from __future__ import annotations

import logging

from openai import AsyncOpenAI

from aidd.config import Config

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._client = AsyncOpenAI(
            api_key=config.openrouter_api_key,
            base_url=config.openrouter_base_url,
        )

    async def ask(self, user_text: str) -> str:
        logger.debug(
            "LLM request model=%s user_chars=%s",
            self._config.llm_model,
            len(user_text),
        )
        response = await self._client.chat.completions.create(
            model=self._config.llm_model,
            messages=[
                {"role": "system", "content": self._config.system_prompt},
                {"role": "user", "content": user_text},
            ],
            temperature=self._config.llm_temperature,
            max_tokens=self._config.llm_max_tokens,
        )
        message = response.choices[0].message
        content = message.content
        if not content:
            logger.warning("LLM returned empty content")
            return ""
        return content
