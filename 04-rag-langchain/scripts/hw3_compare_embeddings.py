"""
HW-3: сравнение retrieval при разных моделях эмбеддингов (OpenRouter).
Собирает те же чанки, что и indexer_with_json, строит InMemoryVectorStore для каждой модели и печатает top-k фрагменты по тестовым вопросам.

Запуск из корня проекта:
    uv run python scripts/hw3_compare_embeddings.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

load_dotenv(_PROJECT_ROOT / ".env")

# импорт после добавления sys.path и load_dotenv
from config import Config  # noqa: E402
from indexer import load_pdf_documents, split_documents  # noqa: E402
from indexer_with_json import load_json_documents  # noqa: E402

EMBEDDING_MODELS = [
    ("Baseline", "openai/text-embedding-3-large"),
    ("BGE-M3 multilingual", "baai/bge-m3"),
    ("Qwen3 Embedding 8B", "qwen/qwen3-embedding-8b"),
]

QUERIES = [
    "Какие условия потребительского кредита?",
    "Какие проценты по вкладам?",
    "Как заказать карту?",
]


def _build_chunks() -> list:
    cfg = Config()
    data_dir = os.getenv("DATA_DIR", cfg.DATA_DIR)
    all_chunks: list = []

    pages = load_pdf_documents(data_dir)
    if pages:
        all_chunks.extend(split_documents(pages))

    json_docs = load_json_documents(data_dir)
    if json_docs:
        all_chunks.extend(split_documents(json_docs))

    if not all_chunks:
        raise RuntimeError("Нет данных для индексации (PDF/JSON)")
    return all_chunks


def _make_embeddings(model: str) -> OpenAIEmbeddings:
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY не задан в окружении")
    kwargs: dict = {
        "model": model,
        "api_key": api_key,
    }
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAIEmbeddings(**kwargs)


def main() -> None:
    k = int(os.getenv("RETRIEVER_K", "3"))

    chunks = _build_chunks()
    print(f"Всего чанков после split: {len(chunks)}\n")

    for label, mid in EMBEDDING_MODELS:
        print("=" * 72)
        print(f"[{label}] model={mid}")
        print("=" * 72)

        emb = _make_embeddings(mid)
        store = InMemoryVectorStore.from_documents(documents=chunks, embedding=emb)

        for q in QUERIES:
            print(f"\n--- Запрос: {q}")
            docs = store.similarity_search(q, k=k)
            for i, d in enumerate(docs, 1):
                snippet = (d.page_content[:400] + "…") if len(d.page_content) > 400 else d.page_content
                meta = dict(d.metadata or {})
                print(f"  [{i}] meta={meta}\n      {snippet!r}")
        print()

    print("Готово. Сравните релевантность top-k по каждой модели вручную.")


if __name__ == "__main__":
    main()
