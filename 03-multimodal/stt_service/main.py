"""FastAPI STT-сервис: GigaAM-v3."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile

from gigaam_model import GigaAmModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("Loading GigaAM model...")
    app.state.model = GigaAmModel()
    logger.info("STT service ready")
    yield


app = FastAPI(title="GigaAM STT", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/transcribe")
async def transcribe_endpoint(file: UploadFile = File(...)) -> dict[str, str]:
    model: GigaAmModel = app.state.model
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="empty file")

    try:
        text = await asyncio.to_thread(model.transcribe, data)
    except Exception:
        logger.exception("Transcription failed")
        raise HTTPException(
            status_code=500,
            detail="transcription failed",
        ) from None

    return {"text": text}
