"""Индексация PDF + JSON (sberbank_help_documents.json) в одном векторном хранилище."""

import json
import logging
from pathlib import Path

from langchain_core.documents import Document

from config import config
from indexer import create_vector_store, load_pdf_documents, split_documents

logger = logging.getLogger(__name__)


def load_json_documents(data_dir: str) -> list:
    """Загрузка Q&A из JSON: поле full_text в page_content, метаданные из url/question/category."""
    json_path = Path(data_dir) / "sberbank_help_documents.json"
    if not json_path.exists():
        logger.warning("JSON file not found: %s", json_path)
        return []

    with open(json_path, encoding="utf-8") as f:
        records = json.load(f)

    docs = [
        Document(
            page_content=record["full_text"],
            metadata={
                "source": record.get("url", ""),
                "question": record.get("question", ""),
                "category": record.get("category", ""),
            },
        )
        for record in records
    ]
    logger.info("Loaded %s JSON documents from %s", len(docs), json_path.name)
    return docs


async def reindex_all():
    """Полная переиндексация: чанки PDF + чанки из JSON в одном InMemoryVectorStore."""
    logger.info("Starting full reindexing (PDF + JSON)...")

    try:
        all_chunks = []

        pages = load_pdf_documents(config.DATA_DIR)
        if pages:
            all_chunks.extend(split_documents(pages))

        json_docs = load_json_documents(config.DATA_DIR)
        if json_docs:
            all_chunks.extend(split_documents(json_docs))

        if not all_chunks:
            logger.warning("No documents found to index")
            return None

        vector_store = create_vector_store(all_chunks)
        logger.info("Reindexing completed successfully")
        return vector_store

    except FileNotFoundError as e:
        logger.error("Directory not found: %s", e)
        return None
    except Exception as e:
        logger.error("Error during reindexing: %s", e, exc_info=True)
        return None
