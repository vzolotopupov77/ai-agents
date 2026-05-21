# Техническое видение проекта

## Технологии

**Основные:**
- **Python 3.11+** — основной язык.
- **uv** — управление зависимостями и виртуальным окружением.
- **make** — обёртки команд.
- **aiogram 3.x** — Telegram Bot API в режиме polling, асинхронно.
- **LangChain 1.0** — `create_agent()` для ReAct-агента.
- **LangGraph** — `MemorySaver` (state persistence), под капотом `create_agent()`.
- **langchain-openai** — клиент к OpenAI-совместимому API (OpenRouter).
- **langchain-huggingface**, **sentence-transformers** — локальные embeddings и cross-encoder.
- **langchain-community / langchain-classic** — `BM25Retriever`, `EnsembleRetriever`.
- **rank-bm25** — BM25.
- **pypdf** — парсинг PDF.
- **langsmith**, **ragas**, **datasets** — трейсинг и оценка качества.
- **python-dotenv** — `.env`.

**LLM-провайдер по умолчанию:** OpenRouter (один провайдер, без альтернативных блоков в `env.example`/`README.md`).

## Принципы разработки

- **KISS, YAGNI** — максимальная простота, ничего «на будущее».
- **Монолитная архитектура** — весь код в `src/`, никаких пакетов и подпакетов.
- **Прямолинейный код** — минимум абстракций, без DI и архитектурных паттернов.
- Глобальные переменные для простых хранилищ (vector store, retriever, агент).
- История диалога управляется агентом через `MemorySaver`.

## Структура проекта

```
/
├── src/
│   ├── bot.py                  # Точка входа: индексация → инициализация агента → polling
│   ├── handlers.py             # Обработчики команд и сообщений
│   ├── agent.py                # ReAct-агент через create_agent() (LangChain 1.0)
│   ├── tools.py                # @tool rag_search для агента
│   ├── rag.py                  # Retriever + reranking, retrieve_documents()
│   ├── indexer.py              # Загрузка PDF/JSON, чанки, vector store
│   ├── config.py               # Загрузка и валидация .env
│   ├── evaluation.py           # RAGAS evaluation + загрузка feedback в LangSmith
│   └── dataset_synthesizer.py  # Синтез тестовых датасетов
├── prompts/
│   └── agent_system.txt        # Системный промпт агента
├── data/                       # PDF + JSON документы
├── datasets/                   # Сгенерированные датасеты для evaluation
├── docs/                       # idea.md, vision.md, tasklist.md, adrs/
├── logs/                       # bot.log (не коммитится)
├── env.example                 # Пример конфигурации
├── pyproject.toml              # uv
├── Makefile                    # install / run / dataset / dataset-upload
└── README.md                   # Документация проекта
```

## Архитектура

**Компоненты:**

1. **bot.py** — точка входа.
   - Индексация документов при старте (`indexer.reindex_all()`).
   - Инициализация retriever под выбранный `RETRIEVAL_MODE`.
   - Создание ReAct-агента (`agent.initialize_agent()`).
   - Регистрация router и polling.

2. **handlers.py** — `/start`, `/help`, `/index`, `/index_status`, `/evaluate_dataset`, текстовые сообщения.
   - На каждое текстовое сообщение вызывает `agent.agent_answer([HumanMessage], chat_id)`.
   - Опционально дописывает источники (`SHOW_SOURCES`).

3. **agent.py** — ReAct-агент.
   - `create_bank_agent()` — `create_agent(model, tools=[rag_search], system_prompt, checkpointer=MemorySaver())`.
   - `agent_answer(messages, chat_id)` — `bank_agent.stream(..., stream_mode="values")`, логирует каждый шаг.
   - `_extract_documents_from_current_request()` — собирает `documents` только из `ToolMessage` после последнего `HumanMessage` (важно для RAGAS).
   - Fallback на пустой ответ.

4. **tools.py** — `@tool rag_search(query: str) -> str`.
   - Вызывает `rag.retrieve_documents(query)`.
   - Возвращает JSON `{"sources": [{source, page, page_content}]}` (`page` только для PDF, `ensure_ascii=False`).

5. **rag.py** — Retriever и reranking.
   - `create_retriever()` — фабрика по `RETRIEVAL_MODE` (semantic / hybrid / hybrid_reranker).
   - `retrieve_documents(query)` — базовая функция поиска для `rag_search`.
   - `cross_encoder` — lazy loading.
   - Никакого `query_transformation_chain` — фразы для поиска формирует сам агент.

6. **indexer.py** — индексация.
   - `load_pdf_documents()`, `load_json_documents()`, `split_documents()`.
   - `create_embeddings()` — фабрика по `EMBEDDING_PROVIDER` (openai / huggingface).
   - `reindex_all()` — возвращает `(vector_store, chunks)` (chunks нужны для BM25).

7. **config.py** — `Config` с полями из `.env`, `validate()` для `RETRIEVAL_MODE` и `EMBEDDING_PROVIDER`.

8. **evaluation.py** — `evaluate_dataset(name)`:
   - Запуск эксперимента в LangSmith с `blocking=False` и сбором данных.
   - Batch RAGAS-метрики (6 штук).
   - Загрузка результатов как feedback к runs.

9. **dataset_synthesizer.py** — синтез QA-пар (по 2 чанка/файл) + загрузка из JSON; CLI с `--upload`.

**Поток данных (ReAct Agent):**
```
Telegram → handlers.py (HumanMessage) →
agent.agent_answer(thread_id = chat_id) →
bank_agent (ReAct цикл):
    1. Reason — анализирует вопрос, контекст из MemorySaver
    2. Act    — при необходимости rag_search(query)
                → rag.retrieve_documents()
                → semantic / hybrid / hybrid_reranker
                → JSON {"sources": [...]} обратно агенту
    3. Respond — финальный AIMessage
→ handlers.py → Telegram (+ опц. источники)
```

**Поток данных (Evaluation):**
```
Telegram /evaluate_dataset → handlers.py → evaluation.evaluate_dataset:
1. Запуск эксперимента в LangSmith (агент отвечает на каждый question)
2. Сбор answers, contexts (page_content из rag_search), ground_truths, run_ids
3. Batch RAGAS на собранных данных
4. Загрузка метрик как feedback в LangSmith
5. Возврат агрегированных метрик в Telegram
```

## Модель данных

**История диалогов — `MemorySaver` в агенте:**
- `thread_id = str(chat_id)` — отдельная история для каждого пользователя.
- Сообщения управляются через `add_messages` reducer внутри агента.
- При `/start` — новый thread.
- При рестарте бота — вся история теряется (in-memory).

**Документы из rag_search:**
- В JSON: `source`, `page` (только для PDF), `page_content`.
- `page_content` обязателен для корректной работы RAGAS (Context Recall / Precision).

## Работа с LLM

**Провайдер:** OpenRouter (`OPENAI_BASE_URL=https://openrouter.ai/api/v1`).

**Клиент:** `langchain_openai.ChatOpenAI(model=config.MODEL, temperature=...)` внутри `create_agent()`.

**Параметры из `.env`:**
- `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `MODEL` — основной агент.
- `RAGAS_LLM_MODEL`, `RAGAS_EMBEDDING_MODEL` — фиксированные модели для воспроизводимой оценки.
- `EMBEDDING_PROVIDER`, `HUGGINGFACE_*`, `EMBEDDING_MODEL` — embeddings.

**Обработка ошибок:** try/except вокруг вызовов LLM/индексации; понятные текстовые сообщения пользователю.

## Сценарии работы

1. **Первый запуск:** `/start` → приветствие, инициализация thread.
2. **Простой диалог:** «Привет» → агент отвечает напрямую, без `rag_search`.
3. **Продуктовый вопрос:** «Какие условия кредита?» → агент вызывает `rag_search` → формирует ответ.
4. **Уточнение:** «А досрочно можно?» → агент использует историю и при необходимости второй раз вызывает `rag_search`.
5. **Сброс:** `/start` → новый thread, история теряется.
6. **Evaluation:** `/evaluate_dataset` → бот возвращает 6 RAGAS-метрик.

## Подход к конфигурированию

- Всё — через `.env` и `python-dotenv`.
- Никаких YAML/JSON/TOML-конфигов и dev/prod окружений.
- Валидация `RETRIEVAL_MODE` и `EMBEDDING_PROVIDER` на старте (только белый список значений).

## Подход к логированию

- Стандартный `logging`.
- StreamHandler в консоль + FileHandler в `logs/bot.log`.
- Что логируем: старт/стоп, индексация, конфигурация, ReAct-шаги (Reason / Act / Tool result / Respond), ошибки.

## Режимы Retrieval

- **semantic** — InMemoryVectorStore + cosine similarity. Быстрый baseline.
- **hybrid** — `EnsembleRetriever` (Semantic + BM25), RRF c весами.
- **hybrid_reranker** — hybrid → cross-encoder → топ-K. Лучшее качество.

## Embeddings

- **openai** — `openai/text-embedding-3-large` через OpenRouter.
- **huggingface** — `intfloat/multilingual-e5-base` локально (CPU/GPU/MPS).
