# Техническое видение проекта

## Технологии

**Основные технологии:**
- **Python 3.11+** - основной язык разработки
- **uv** - управление зависимостями и виртуальным окружением
- **aiogram 3.x** - фреймворк для Telegram Bot API (polling)
- **LangChain** - фреймворк для построения RAG-приложений
- **langchain-openai** - интеграция LangChain с OpenAI-совместимыми API
- **openai** - клиент для работы с LLM через Openrouter
- **pypdf** - загрузка и парсинг PDF-документов
- **python-dotenv** - для работы с переменными окружения
- **Make** - автоматизация сборки и запуска

## Принципы разработки

**Принципы:**
- **KISS** (Keep It Simple, Stupid) - максимальная простота решений
- **YAGNI** (You Aren't Gonna Need It) - реализуем только то, что нужно сейчас
- **Монолитная архитектура** - весь код в одном месте, никаких микросервисов
- **Прямолинейный код** - минимум абстракций, максимум читаемости
- **Быстрый старт** - от идеи до рабочего прототипа за минимальное время

**Что НЕ делаем:**
- Не создаем сложные архитектурные паттерны
- Не делаем преждевременную оптимизацию
- Не добавляем функции "на будущее"
- Не усложняем без крайней необходимости

## Структура проекта

```
/
├── src/
│   ├── bot.py                  # Основной файл бота, инициализация aiogram
│   ├── handlers.py             # Обработчики команд и сообщений Telegram
│   ├── rag.py                  # RAG-логика: retriever, цепочки, query transformation
│   ├── indexer.py              # Индексация PDF: загрузка, splitting, векторное хранилище
│   ├── indexer_with_json.py    # Расширение: объединённая индексация PDF + JSON FAQ
│   └── config.py               # Загрузка конфигурации из .env
├── data/
│   ├── ouk_potrebitelskiy_kredit_lph.pdf   # Общие условия потребительского кредита
│   ├── usl_r_vkladov.pdf                   # Условия по вкладам
│   └── sberbank_help_documents.json        # FAQ по картам (212 Q&A)
├── scripts/
│   └── hw3_compare_embeddings.py           # Сравнение retrieval по трём моделям эмбеддингов
├── prompts/                    # Промпты для диалога и query transformation
├── .env                        # Переменные окружения (токены, настройки)
├── env.example                 # Пример конфигурации
├── pyproject.toml              # Конфигурация проекта для uv
├── Makefile                    # Команды для запуска и управления
└── README.md                   # Документация по запуску
```

**Принцип:** Простая структура — Python-файлы в одной папке `src/`. Никаких пакетов, подпакетов, сложной иерархии.

**Данные:** в `data/` лежат два PDF и файл `sberbank_help_documents.json` (212 Q&A по картам). Активный пайплайн (`indexer_with_json.py`) индексирует оба источника в одном векторном хранилище (~544 чанка).

## Архитектура проекта

**Компоненты:**

1. **bot.py** - точка входа
   - Инициализирует aiogram Bot и Dispatcher
   - Запускает индексацию документов при старте
   - Регистрирует handlers
   - Запускает polling

2. **handlers.py** - обработка событий
   - `/start` - приветствие и очистка истории
   - `/help` - справка по командам и возможностям
   - `/index` - ручная переиндексация документов
   - `/index_status` - статус индексации
   - Обработчик всех текстовых сообщений → вызов RAG → сохранение ответа в историю
   - Хранит историю диалогов в памяти: `dict[int, list]` (chat_id → список сообщений)

3. **indexer.py** - базовая индексация PDF
   - `load_pdf_documents(data_dir)` — загрузка PDF через PyPDFLoader
   - `split_documents(pages)` — разбиение на чанки: `chunk_size=800`, `chunk_overlap=100`, `RecursiveCharacterTextSplitter`
   - `create_vector_store(chunks)` — создание `InMemoryVectorStore` с `OpenAIEmbeddings`; модель из `config.EMBEDDING_MODEL`
   - `reindex_all()` — полная переиндексация только PDF (не используется напрямую ботом)

3a. **indexer_with_json.py** - объединённая индексация PDF + JSON
   - `load_json_documents(data_dir)` — читает `sberbank_help_documents.json`, каждая Q&A → `Document` с метаданными `source`, `question`, `category`
   - `reindex_all()` — вызывает `load_pdf_documents` + `split_documents` из `indexer.py`, затем `load_json_documents` + `split_documents`, один общий `create_vector_store(all_chunks)`
   - **Именно этот модуль подключён к боту**: `import indexer_with_json as indexer`

4. **rag.py** - RAG-логика
   - `format_chunks(chunks)` - форматирование чанков в строку
   - `retrieval_query_transformation_chain` - цепочка трансформации запроса
   - `rag_query_transform_chain` - финальная RAG-цепочка
   - `rag_answer(messages)` - асинхронный метод для получения RAG-ответа
   - Промпты для conversation и query transformation
   - Использует retriever из vector_store

5. **config.py** - конфигурация
   - Класс Config с полями: `TELEGRAM_TOKEN`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `MODEL`, `MODEL_QUERY_TRANSFORM`, `EMBEDDING_MODEL`, `DATA_DIR`, `SYSTEM_PROMPT`
   - Загрузка из .env через python-dotenv

**Поток данных (RAG):**
```
Telegram → handlers.py (добавить в историю) → 
rag.py (query transformation → retriever → context augmentation) → 
LLM → rag.py → handlers.py (сохранить ответ в историю) → Telegram
```

**Принцип:** Никакой DI, никаких интерфейсов, никаких слоев абстракции. Прямые вызовы функций. Глобальные переменные для простых хранилищ.

## Модель данных

**Хранение в памяти (без БД):**

Глобальный словарь в `handlers.py`:
```python
chat_conversations: dict[int, list] = {}
```

**Структура истории диалога** (LangChain Messages):
```python
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

chat_conversations[chat_id] = [
    SystemMessage(content="системный промпт"),
    HumanMessage(content="сообщение пользователя"),
    AIMessage(content="ответ LLM"),
    ...
]
```

**Операции:**
- При `/start` - очищаем историю для данного чата
- При новом сообщении - добавляем в список
- Передаем весь список в LLM для контекста
- При перезапуске бота - вся история теряется

**Принцип:** Максимальная простота. Никаких БД, файлов, сериализации. История живет только в runtime.

## Работа с LLM

**Используемая библиотека:** `langchain-openai` (`ChatOpenAI` — интегрирован в LangChain-цепочки)

**Настройка (ленивая инициализация в `rag.py`):**
```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model=config.MODEL,           # openai/gpt-oss-20b:free
    temperature=0.9,
    # base_url и api_key подхватываются из переменных окружения OPENAI_BASE_URL / OPENAI_API_KEY
)
```

**Параметры из .env:**
- `OPENAI_API_KEY` - ключ от OpenRouter
- `OPENAI_BASE_URL` - `https://openrouter.ai/api/v1`
- `MODEL` - название модели (например `openai/gpt-oss-20b:free`)
- `SYSTEM_PROMPT` - роль/инструкция для LLM

**Обработка ошибок:**
- try/except для сетевых ошибок
- Возврат простого сообщения об ошибке пользователю

**Принцип:** Асинхронный запрос-ответ. Никакого retry, никаких очередей, никакого streaming.

## Сценарии работы

**Сценарий 1: Первый запуск**
1. Пользователь отправляет `/start`
2. Бот отвечает приветственным сообщением
3. История диалога инициализируется с системным промптом

**Сценарий 2: Диалог**
1. Пользователь пишет текстовое сообщение
2. Бот добавляет сообщение в историю чата
3. Бот отправляет историю чата в LLM
4. Бот получает ответ и добавляет его в историю чата
5. Бот отправляет ответ пользователю

**Сценарий 3: Сброс контекста**
1. Пользователь отправляет `/start`
2. История диалога очищается
3. Начинается новый диалог

**Ограничения:**
- Бот работает только с текстом (не обрабатывает фото, файлы, голосовые)
- Один пользователь не блокирует других (асинхронность)
- При перезапуске бота все истории теряются

## Подход к конфигурированию

**Файл .env** (не коммитится в git):
```bash
TELEGRAM_TOKEN=your_telegram_bot_token
OPENAI_API_KEY=sk-or-v1-...
OPENAI_BASE_URL=https://openrouter.ai/api/v1
MODEL=openai/gpt-oss-20b:free
MODEL_QUERY_TRANSFORM=openai/gpt-oss-20b:free
# Варианты: openai/text-embedding-3-large | baai/bge-m3 | qwen/qwen3-embedding-8b
EMBEDDING_MODEL=openai/text-embedding-3-large
DATA_DIR=data
PROMPTS_DIR=prompts
RETRIEVER_K=3
SYSTEM_PROMPT=Ты ассистент Сбербанка, отвечающий на вопросы по документам.
```

**Файл env.example** (коммитится — с комментариями по вариантам `EMBEDDING_MODEL`).

**config.py:**
```python
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
    MODEL = os.getenv("MODEL")
    MODEL_QUERY_TRANSFORM = os.getenv("MODEL_QUERY_TRANSFORM")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
    DATA_DIR = os.getenv("DATA_DIR", "data")
    SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT")

config = Config()
```

**Принципы:**
- Все секреты только в .env
- Нет YAML, JSON, TOML конфигов
- Нет окружений (dev/prod)
- Нет валидации на старте (упадет при первом использовании если что-то не так)

## Подход к логгированию

**Используем встроенный logging Python:**
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
```

**Что логируем:**
- Старт/остановка бота
- Входящие сообщения от пользователей (chat_id + текст)
- Ошибки при вызове LLM
- Исключения

**Что НЕ логируем:**
- Содержимое ответов LLM (избыточно для MVP)
- Детальные трейсы успешных операций
- Метрики, аналитика

**Вывод:** stdout/stderr (консоль) + файл `logs/bot.log` (UTF-8, без ротации).

**Принципы:**
- Без внешних библиотек (structlog и т.п.)
- Без ротации, без внешних систем
- Простой текстовый формат


