"""Загрузка GigaAM-v3 и транскрибация аудио в текст."""

from __future__ import annotations

import io
import logging
import os
import tempfile
from pathlib import Path

import gigaam
from pydub import AudioSegment

logger = logging.getLogger(__name__)

# Пунктуация и нормализация (см. README GigaAM, ADR 0006).
MODEL_NAME = "v3_e2e_ctc"
TARGET_SAMPLE_RATE_HZ = 16000


class GigaAmModel:
    """Обёртка над `gigaam`: Telegram voice (.ogg/opus) → WAV 16 kHz mono → текст."""

    def __init__(self, *, fp16_encoder: bool = True) -> None:
        kwargs: dict[str, bool] = {}
        if fp16_encoder:
            kwargs["fp16_encoder"] = True
        self._model = gigaam.load_model(MODEL_NAME, **kwargs)
        logger.info("GigaAM model loaded: %s", MODEL_NAME)

    def transcribe(self, audio_bytes: bytes) -> str:
        """Транскрибировать байты аудио (ожидается ogg/opus от Telegram)."""
        segment = _bytes_to_segment(audio_bytes)
        segment = segment.set_frame_rate(TARGET_SAMPLE_RATE_HZ).set_channels(1)

        fd, tmp_name = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        wav_path = Path(tmp_name)
        try:
            segment.export(str(wav_path), format="wav")
            raw = self._model.transcribe(str(wav_path))
            return (raw.text if raw is not None else "").strip()
        finally:
            wav_path.unlink(missing_ok=True)


def _bytes_to_segment(audio_bytes: bytes) -> AudioSegment:
    """Преобразовать байты в AudioSegment (ffmpeg через pydub)."""
    bio = io.BytesIO(audio_bytes)
    try:
        return AudioSegment.from_file(bio, format="ogg")
    except Exception:
        logger.debug("ogg decode failed, retrying with ffmpeg auto-detect")
        bio.seek(0)
        return AudioSegment.from_file(bio)
