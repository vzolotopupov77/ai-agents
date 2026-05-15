import hashlib
import logging
import pickle
from pathlib import Path
from typing import List
import httpx
from langchain_community.document_loaders import PyPDFLoader, JSONLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import InMemoryVectorStore
from config import config

CACHE_DIR = Path("cache")
CACHE_FILE = CACHE_DIR / "vector_store.pkl"
CACHE_HASH_FILE = CACHE_DIR / "data_hash.txt"

logger = logging.getLogger(__name__)


class OpenRouterEmbeddings(Embeddings):
    """Embeddings через OpenRouter API с явным батчингом по 50 текстов."""

    def __init__(self, model: str, api_key: str, base_url: str, batch_size: int = 50):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.batch_size = batch_size

    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        # Заменяем пустые строки пробелом — API не принимает input=""
        safe_texts = [t if t and t.strip() else " " for t in texts]
        resp = httpx.post(
            f"{self.base_url}/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={"model": self.model, "input": safe_texts, "encoding_format": "float"},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("data"):
            raise ValueError(f"OpenRouter embeddings returned empty data: {str(data)[:200]}")
        return [item["embedding"] for item in data["data"]]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        result = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            result.extend(self._embed_batch(batch))
            logger.debug(f"Embedded batch {i // self.batch_size + 1}, total so far: {len(result)}")
        return result

    def embed_query(self, text: str) -> List[float]:
        return self._embed_batch([text if text and text.strip() else " "])[0]

def load_pdf_documents(data_dir: str) -> list:
    """Загрузка всех PDF документов из директории"""
    pages = []
    data_path = Path(data_dir)
    
    if not data_path.exists():
        logger.warning(f"Directory {data_dir} does not exist")
        return pages
    
    pdf_files = list(data_path.glob("*.pdf"))
    logger.info(f"Found {len(pdf_files)} PDF files in {data_dir}")
    
    for pdf_file in pdf_files:
        loader = PyPDFLoader(str(pdf_file))
        pages.extend(loader.load())
        logger.info(f"Loaded {pdf_file.name}")
    
    return pages

def split_documents(pages: list) -> list:
    """Разбиение документов на чанки"""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    chunks = text_splitter.split_documents(pages)
    logger.info(f"Split into {len(chunks)} chunks")
    return chunks

def load_json_documents(json_file_path: str) -> list:
    """Загрузка Q&A пар из JSON, каждая пара - отдельный чанк"""
    json_path = Path(json_file_path)
    if not json_path.exists():
        logger.warning(f"JSON file {json_file_path} does not exist")
        return []
    
    try:
        loader = JSONLoader(
            file_path=str(json_path),
            jq_schema='.[].full_text',
            text_content=False
        )
        documents = loader.load()
        logger.info(f"Loaded {len(documents)} Q&A pairs from JSON")
        return documents
    except Exception as e:
        logger.error(f"Error loading JSON: {e}")
        return []

def _compute_data_hash(data_dir: str) -> str:
    """Хеш содержимого всех исходных файлов — для инвалидации кеша."""
    h = hashlib.md5()
    for f in sorted(Path(data_dir).glob("**/*")):
        if f.is_file() and f.suffix in (".pdf", ".json"):
            h.update(f.name.encode())
            h.update(str(f.stat().st_mtime).encode())
    h.update(config.EMBEDDING_MODEL.encode())
    return h.hexdigest()


def _load_cache() -> InMemoryVectorStore | None:
    """Загружает векторный стор из кеша, если он актуален."""
    if not CACHE_FILE.exists() or not CACHE_HASH_FILE.exists():
        return None
    stored_hash = CACHE_HASH_FILE.read_text().strip()
    current_hash = _compute_data_hash(config.DATA_DIR)
    if stored_hash != current_hash:
        logger.info("Cache is stale (data changed), will rebuild")
        return None
    try:
        with CACHE_FILE.open("rb") as f:
            store = pickle.load(f)
        logger.info("Loaded vector store from cache")
        return store
    except Exception as e:
        logger.warning(f"Failed to load cache: {e}")
        return None


def _save_cache(vector_store: InMemoryVectorStore) -> None:
    """Сохраняет векторный стор на диск."""
    CACHE_DIR.mkdir(exist_ok=True)
    with CACHE_FILE.open("wb") as f:
        pickle.dump(vector_store, f)
    CACHE_HASH_FILE.write_text(_compute_data_hash(config.DATA_DIR))
    logger.info(f"Vector store cached to {CACHE_FILE}")


def create_vector_store(chunks: list) -> InMemoryVectorStore:
    """Создание векторного хранилища (всегда пересоздаёт, без кеша)."""
    embeddings = OpenRouterEmbeddings(
        model=config.EMBEDDING_MODEL,
        api_key=config.OPENAI_API_KEY,
        base_url=config.OPENAI_BASE_URL,
    )
    vector_store = InMemoryVectorStore.from_documents(
        documents=chunks,
        embedding=embeddings,
    )
    logger.info(f"Created vector store with {len(chunks)} chunks")
    return vector_store


async def reindex_all():
    """Индексация документов с кешированием на диск."""
    logger.info("Starting full reindexing...")

    try:
        # Загрузка PDF документов
        pages = load_pdf_documents(config.DATA_DIR)
        pdf_chunks = split_documents(pages) if pages else []
        logger.info(f"PDF: {len(pdf_chunks)} chunks")

        # Загрузка JSON Q&A пар
        json_file = Path(config.DATA_DIR) / "sberbank_help_documents.json"
        json_documents = load_json_documents(str(json_file))
        logger.info(f"JSON: {len(json_documents)} Q&A pairs")

        all_chunks = pdf_chunks + json_documents

        if not all_chunks:
            logger.warning("No documents found to index")
            return None

        logger.info(f"Total chunks to index: {len(all_chunks)} (PDF: {len(pdf_chunks)}, JSON: {len(json_documents)})")

        # Пытаемся загрузить из кеша
        vector_store = _load_cache()
        if vector_store is not None:
            return vector_store

        # Кеш недоступен — пересоздаём и сохраняем
        vector_store = create_vector_store(all_chunks)
        _save_cache(vector_store)
        logger.info("Reindexing completed successfully")
        return vector_store

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return None
    except Exception as e:
        logger.error(f"Error during reindexing: {e}", exc_info=True)
        return None

