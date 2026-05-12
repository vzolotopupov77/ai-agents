"""HTTP-клиент к STT-микросервису (GigaAM). Не импортирует Telegram."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class SttClient:
    """Async POST `/transcribe` с multipart `file`."""

    def __init__(self, base_url: str, *, timeout: float = 120.0) -> None:
        self._base = base_url.rstrip("/")
        self._timeout = timeout

    async def transcribe(
        self,
        audio_bytes: bytes,
        *,
        filename: str = "voice.ogg",
        content_type: str = "audio/ogg",
    ) -> str:
        url = f"{self._base}/transcribe"
        logger.debug("STT POST %s size=%s", url, len(audio_bytes))
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                url,
                files={"file": (filename, audio_bytes, content_type)},
            )
            response.raise_for_status()
            data: Any = response.json()
        if not isinstance(data, dict):
            msg = "STT response is not a JSON object"
            raise ValueError(msg)
        text = data.get("text")
        return (text or "").strip() if isinstance(text, str) else ""
