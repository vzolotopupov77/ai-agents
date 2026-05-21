# ReAct Agent с Advanced Hybrid RAG

Telegram-бот на базе ReAct-агента (Reason + Act) с инструментом `rag_search` поверх продвинутого Hybrid RAG. Агент сам решает, когда искать в документах банка, а когда отвечать напрямую.

## ✨ Возможности

### 🤖 ReAct Agent (автономный ИИ)

- 🧠 **Самостоятельное принятие решений** — агент сам выбирает, когда вызывать `rag_search`.
- 🔄 **ReAct цикл:** Reason → Act → Observe → Respond.
- 💾 **MemorySaver** — независимая история диалога для каждого `chat_id`.
- 🎯 **Умная стратегия:** «привет/спасибо» — без поиска; «какой процент по вкладу» — через `rag_search`.
- 📝 **Системный промпт в файле** `prompts/agent_system.txt` — редактируется без правки кода.

### 🔍 Advanced Hybrid RAG

- **3 режима Retrieval:**
  - `semantic` — векторный поиск по смыслу
  - `hybrid` — Semantic + BM25 (точные термины)
  - `hybrid_reranker` — Hybrid + Cross-encoder (максимальная точность)
- **Конфигурируемые embeddings:** OpenAI (через OpenRouter) или HuggingFace локально (`multilingual-e5-base`).
- **Cross-Encoder Reranking** — точное переранжирование топ-k.
- **Настраиваемые веса** ensemble для balance Semantic/BM25.

### 📚 Работа с документами

- 📄 **Индексация PDF + JSON** — автоматическая обработка PDF и готовых Q&A пар.
- 📖 **Опциональное отображение источников** — показывает имя файла и страницу.

### 📊 Мониторинг и Quality Assurance

- **LangSmith трейсинг** — детальные traces каждого ReAct-шага и каждого вызова `rag_search`.
- **Синтез датасетов** — автоматическая генерация Q&A для evaluation.
- **RAGAS Evaluation** — 6 метрик качества прямо из Telegram-команды.
- **Асинхронная обработка** — много пользователей одновременно.

## 🚀 Быстрый старт

### Требования

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) — менеджер зависимостей

### Установка

```bash
make install
cp env.example .env
# заполните TELEGRAM_TOKEN и OPENAI_API_KEY (OpenRouter)
make run
```

При первом запуске с `EMBEDDING_PROVIDER=huggingface` загрузится локальная модель embeddings (~1.1 GB).

## ⚙️ Конфигурация

### Получение токенов

**Telegram Bot Token:** через @BotFather → `/newbot`.

**OpenRouter API Key:**
1. Зарегистрируйтесь на [OpenRouter.ai](https://openrouter.ai/).
2. Раздел API Keys → создайте новый ключ.

### Пример `.env`

```bash
TELEGRAM_TOKEN=your_telegram_bot_token

OPENAI_API_KEY=sk-or-v1-...
OPENAI_BASE_URL=https://openrouter.ai/api/v1
MODEL=openai/gpt-oss-20b:free
RAGAS_LLM_MODEL=openai/gpt-oss-20b:free
RAGAS_EMBEDDING_MODEL=openai/text-embedding-3-large

EMBEDDING_PROVIDER=huggingface
HUGGINGFACE_EMBEDDING_MODEL=intfloat/multilingual-e5-base
HUGGINGFACE_DEVICE=cpu
```

### Описание параметров

**Обязательные:**
- `TELEGRAM_TOKEN` — токен бота
- `OPENAI_API_KEY`, `OPENAI_BASE_URL` — доступ к OpenRouter
- `MODEL` — модель агента (рассуждение и финальный ответ)

**Пути:**
- `DATA_DIR` — директория с PDF/JSON
- `PROMPTS_DIR`, `AGENT_SYSTEM_PROMPT_FILE` — системный промпт агента

**Системный промпт:**
- `SYSTEM_PROMPT` — инструкция для бота (резерв; основная — в файле промпта)

Подробнее — в `env.example`.

## 📚 Добавление документов

1. Поместите PDF/JSON-файлы в `data/`.
2. Перезапустите бота (индексация автоматическая) или вызовите `/index` в Telegram.

Бот разбивает PDF на чанки по 500 символов и сохраняет векторное хранилище в памяти.

## 💬 Использование

### Команды бота

- `/start` — приветствие, новый диалог
- `/help` — справка
- `/index` — переиндексировать документы
- `/index_status` — статус и текущая конфигурация retrieval
- `/evaluate_dataset [name]` — запустить RAGAS evaluation (нужен LangSmith)

### Примеры диалогов

**Простой диалог без поиска:**
```
👤 Привет!
🤖 Здравствуйте! Я ассистент банка. Чем могу помочь?
```

**Вопрос с вызовом `rag_search`:**
```
👤 Какие условия потребительского кредита?
🤖 Потребительский кредит — от 30 000 до 5 000 000 ₽,
   срок от 3 месяцев до 5 лет, ставка 12.9–19.9% годовых.
```

**Уточнение в контексте диалога:**
```
👤 Какие вклады есть?
🤖 «Пополняй», «Управляй», «Сохраняй».

👤 А проценты по «Сохраняй»?
🤖 По вкладу «Сохраняй» — от 4% до 6% годовых.
```

## 🏗️ Архитектура

### Структура проекта

```
├── src/
│   ├── bot.py                  # Точка входа, индексация, инициализация агента, polling
│   ├── config.py               # Загрузка и валидация .env
│   ├── handlers.py             # /start, /help, /index, /index_status, /evaluate_dataset, чат
│   ├── indexer.py              # Загрузка PDF/JSON, чанки, vector store
│   ├── rag.py                  # Retriever (semantic/hybrid/hybrid_reranker), reranking
│   ├── agent.py                # ReAct-агент через create_agent() из LangChain 1.0
│   ├── tools.py                # @tool rag_search для агента
│   ├── dataset_synthesizer.py  # Синтез тестовых датасетов и загрузка в LangSmith
│   └── evaluation.py           # RAGAS evaluation с LangSmith feedback
├── prompts/
│   └── agent_system.txt        # Системный промпт агента (когда звать rag_search)
├── data/                       # PDF + JSON документы
├── datasets/                   # Сгенерированные датасеты для evaluation
├── docs/                       # idea.md, vision.md, tasklist.md, references/
├── env.example
├── Makefile
├── pyproject.toml
└── README.md
```

### Поток данных (ReAct Agent)

```
Telegram → handlers.py (HumanMessage) →
  agent.agent_answer(thread_id = chat_id) →
    bank_agent (LangChain 1.0 create_agent):
      1. Reason — анализирует вопрос
      2. Act    — при необходимости вызывает rag_search(query)
                  → rag.retrieve_documents() → semantic/hybrid/hybrid_reranker
                  → JSON {"sources": [{"source", "page", "page_content"}]}
      3. Respond — формирует финальный ответ
    MemorySaver сохраняет историю по chat_id
→ AIMessage → handlers.py → Telegram
```

### Технологический стек

**Core:**
- aiogram 3.x — Telegram polling
- LangChain 1.0 — `create_agent()` (ReAct-агент)
- LangGraph + `MemorySaver` — состояние и история
- LangChain OpenAI — клиент к OpenRouter

**Retrieval:**
- LangChain Community / Classic — `BM25Retriever`, `EnsembleRetriever`
- LangChain HuggingFace + sentence-transformers — локальные embeddings и cross-encoder
- rank-bm25 — лексический поиск
- PyPDF — парсинг PDF, InMemoryVectorStore — хранение векторов

**Quality & Monitoring:**
- LangSmith — трейсинг каждого ReAct-шага
- RAGAS — 6 метрик качества RAG
- datasets — работа с тестовыми датасетами

## 📖 Отображение источников

Включается флагом `SHOW_SOURCES=true` в `.env`. После ответа агент дописывает:

```
📚 Источники: ouk_potrebitelskiy_kredit_lph.pdf (стр. 1, 3, 5)
```

Источники собираются только из текущего turn (после последнего вопроса пользователя), а не из всей истории.

## 🎯 Advanced Hybrid RAG

### Режимы Retrieval

#### 1. Semantic (по умолчанию)

```bash
RETRIEVAL_MODE=semantic
SEMANTIC_RETRIEVER_K=10
```

Чисто векторный поиск. Быстро, хорошо работает с перефразированиями.

#### 2. Hybrid (Semantic + BM25)

```bash
RETRIEVAL_MODE=hybrid
SEMANTIC_RETRIEVER_K=10
BM25_RETRIEVER_K=10
ENSEMBLE_SEMANTIC_WEIGHT=0.5
ENSEMBLE_BM25_WEIGHT=0.5
```

Reciprocal Rank Fusion объединяет результаты BM25 и semantic с весами. Лучше ловит точные термины и числа.

#### 3. Hybrid + Reranker (максимальная точность)

```bash
RETRIEVAL_MODE=hybrid_reranker
SEMANTIC_RETRIEVER_K=10
BM25_RETRIEVER_K=10
RERANKER_TOP_K=3
CROSS_ENCODER_MODEL=cross-encoder/mmarco-mMiniLMv2-L12-H384-v1
```

Hybrid выдаёт топ-20, cross-encoder переранжирует и возвращает топ-3.

### Сравнение режимов

| Характеристика | Semantic | Hybrid | Hybrid + Reranker |
|---|---|---|---|
| Качество | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Скорость | 🚀🚀🚀 | 🚀🚀 | 🚀 |
| Точные термины | ❌ | ✅ | ✅ |
| Latency | ~100 ms | ~200 ms | ~500 ms |
| Рекомендация | Разработка | Production (balanced) | Production (best) |

### Embeddings

| Провайдер | Модель | Когда |
|---|---|---|
| `huggingface` (по умолчанию) | `intfloat/multilingual-e5-base` | Приватность, offline, без расходов на API |
| `openai` (через OpenRouter) | `openai/text-embedding-3-large` | Быстрый старт, нет локальной модели |

Модели:
- `multilingual-e5-base` — 278M параметров, ~1.1 GB
- `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` — 117M параметров, ~470 MB

## 📊 Мониторинг и оценка качества

### LangSmith трейсинг

В `.env`:
```bash
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_TRACING_V2=true
LANGSMITH_PROJECT=07-react-agent
```

В UI LangSmith видно ReAct-цикл: рассуждение агента, вызов `rag_search`, найденные документы, финальный ответ.

### Синтез датасета и evaluation

```bash
make dataset          # создаёт datasets/07-react-agent-qa-dataset.json
make dataset-upload   # загружает в LangSmith с проверкой дубликатов
```

В Telegram:
```
/evaluate_dataset
```

Бот вернёт 6 RAGAS-метрик с цветовой подсветкой:

| Метрика | Что измеряет |
|---|---|
| Faithfulness | Ответ опирается на документы, не на параметрическую память |
| Answer Relevancy | Ответ релевантен вопросу |
| Answer Correctness | Совпадение с эталонным ответом |
| Answer Similarity | Семантическая близость к эталону |
| Context Recall | Retriever нашёл все нужные фрагменты |
| Context Precision | В найденном нет «шума» |

🟢 0.8+ отлично · 🟡 0.6–0.8 хорошо · 🔴 <0.6 требует улучшений.

## 🔧 Разработка

### Команды Makefile

```bash
make install         # uv sync
make run             # запуск бота
make dataset         # синтез датасета из data/
make dataset-upload  # загрузка датасета в LangSmith
```

### Редактирование промпта агента

`prompts/agent_system.txt` определяет, когда агент должен звать `rag_search` (продуктовые вопросы), а когда отвечать напрямую (приветствия, уточнения в контексте).

### Логи

Пишутся в `logs/bot.log` и в консоль. Уровень — `INFO`, формат — таймстемп, имя логгера, сообщение. На каждом шаге ReAct-цикла видно тип сообщения, вызов tool и его результат.

## ⚠️ Ограничения

- История диалога — только в памяти (теряется при рестарте).
- Векторное хранилище — InMemoryVectorStore (переиндексация после рестарта).
- Только текстовые сообщения.
- Ответы — на основе документов в `data/`.

## 🐛 Устранение неполадок

- **Бот не отвечает по делу** → `/index_status`, проверьте, что PDF лежат в `data/`.
- **Ошибка при индексации** → проверьте `OPENAI_API_KEY` и доступность `EMBEDDING_MODEL`.
- **Агент всё время отвечает «не нашёл»** → проверьте, что вопросы в тематике загруженных документов.
