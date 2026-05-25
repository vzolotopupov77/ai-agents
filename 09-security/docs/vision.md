# Техническое видение проекта

## Технологии

**Основные технологии:**
- **Python 3.11+** - основной язык разработки
- **uv** - управление зависимостями и виртуальным окружением
- **aiogram 3.x** - фреймворк для Telegram Bot API (polling)
- **LangChain** - фреймворк для построения RAG-приложений
- **langchain-openai** - интеграция LangChain с OpenAI-совместимыми API
- **langchain-mcp-adapters** - интеграция MCP серверов с LangChain агентами
- **mcp** - Model Context Protocol для расширения возможностей агента
- **langchain-huggingface** - интеграция с HuggingFace embeddings и моделями
- **sentence-transformers** - локальные embeddings и cross-encoder для reranking
- **rank-bm25** - BM25 алгоритм для лексического поиска
- **openai** - клиент для работы с LLM через Openrouter
- **pypdf** - загрузка и парсинг PDF-документов
- **python-dotenv** - для работы с переменными окружения
- **requests** - HTTP клиент для MCP инструментов (currency converter)
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
│   ├── bot.py                  # Основной файл бота, инициализация aiogram и агента
│   ├── handlers.py             # Обработчики команд, сообщений и callback_query (HITL)
│   ├── agent.py                # ReAct агент: лимиты + PII + HITL + MCP
│   ├── middleware.py           # PIIMiddleware, ModelCallLimit, ToolCallLimit
│   ├── tools.py                # Инструмент rag_search для агента
│   ├── rag.py                  # RAG-логика: retriever, базовые функции поиска
│   ├── indexer.py              # Индексация: загрузка PDF, splitting, векторное хранилище
│   ├── config.py               # Загрузка конфигурации из .env
│   ├── evaluation.py           # Оценка качества RAG через RAGAS
│   └── dataset_synthesizer.py  # Синтез тестовых датасетов
├── mcp/                # MCP серверы для расширения функциональности
│   ├── mcp-http/       # Пример: поиск по тикетам поддержки
│   └── mcp-bank-agent/ # MCP сервер с инструментами для банковского агента
│       ├── server.py   # FastMCP сервер с search_products и currency_converter
│       ├── data/       # Статические данные о продуктах банка
│       ├── pyproject.toml
│       ├── Makefile
│       └── README.md
├── data/               # Директория с PDF-документами для индексации
├── datasets/           # Синтезированные тестовые датасеты
├── prompts/            # Промпты для агента
├── logs/               # Логи работы бота
├── .env                # Переменные окружения (токены, настройки)
├── .env.example        # Пример конфигурации
├── pyproject.toml      # Конфигурация проекта для uv
├── Makefile            # Команды для запуска и управления
└── README.md           # Документация по запуску
```

**Принцип:** Простая структура - все Python-файлы в одной папке `src/`. Никаких пакетов, подпакетов, сложной иерархии.

## Архитектура проекта

**Компоненты:**

1. **bot.py** - точка входа
   - Инициализирует aiogram Bot и Dispatcher
   - Запускает индексацию документов при старте
   - Инициализирует ReAct агента с MemorySaver
   - Регистрирует handlers
   - Запускает polling

2. **handlers.py** - обработка событий
   - `/start` - приветствие и очистка истории
   - `/help` - справка по командам и возможностям (включая примеры HITL)
   - `/index` - ручная переиндексация документов
   - `/index_status` - статус индексации
   - Обработчик всех текстовых сообщений → вызов агента → сохранение ответа в историю
   - **HITL обработка:**
     - `pending_interrupts` - хранилище interrupts ожидающих решения пользователя
     - Обработка `interrupt` из результата агента
     - Создание InlineKeyboardMarkup с кнопками "✅ Подтвердить" / "❌ Отклонить"
     - `handle_hitl_callback()` - обработчик callback_query от кнопок
     - Вызов `agent.agent_resume()` с решением пользователя (approve/reject)
   - История управляется через MemorySaver агента (thread_id = chat_id)

3. **indexer.py** - индексация документов
   - `load_pdf_documents(data_dir)` - загрузка PDF через PyPDFLoader
   - `split_documents(pages)` - разбиение на чанки через RecursiveCharacterTextSplitter
   - `create_embeddings()` - фабрика для создания embeddings (OpenAI или HuggingFace)
   - `create_vector_store(chunks)` - создание InMemoryVectorStore с эмбеддингами
   - `reindex_all()` - полная переиндексация с нуля
   - Поддержка двух провайдеров: openai, huggingface
   - Глобальная переменная `vector_store` для хранения векторного хранилища

3. **agent.py** - ReAct агент с MCP, лимитами вызовов, PII и HITL
   - `create_bank_agent()` - создание агента через `create_agent()` из LangChain 1.0
   - **ModelCallLimitMiddleware** / **ToolCallLimitMiddleware** (см. `middleware.py`) — лимиты на вызовы LLM и инструментов за один run (`run_limit`, `exit_behavior="end"`); порядок: сначала лимиты, затем PII, затем HITL
   - **PIIMiddleware** — маскирование номеров карт в выводе модели (`apply_to_output=True`)
   - **HumanInTheLoopMiddleware** - middleware для подтверждения критичных операций
   - Настройка `interrupt_on` для инструментов `open_credit_card` и `open_deposit` (легко расширяется)
   - Использует ChatOpenAI модель и набор инструментов: rag_search + MCP tools
   - MCP клиент (MultiServerMCPClient) для подключения к MCP серверам
   - Системный промпт загружается из файла `prompts/agent_system.txt`
   - MemorySaver для хранения состояния диалогов между сообщениями
   - `agent_answer()` - использует astream() для обработки interrupts
   - `agent_resume()` - продолжение работы агента после approve/reject решения
   - Глобальная переменная `bank_agent` для хранения экземпляра агента

4. **tools.py** - инструменты агента
   - `rag_search(query: str)` - декорирован @tool из langchain_core.tools
   - Описание: "Ищет информацию в документах банка о кредитах, вкладах и услугах"
   - Использует retriever из rag.py для поиска документов
   - Возвращает форматированный контекст из найденных документов
   - MCP инструменты подключаются динамически через MultiServerMCPClient

5. **rag.py** - RAG-логика (упрощенная)
   - `format_chunks(chunks)` - форматирование чанков в строку
   - Поддержка трех режимов: semantic, hybrid, hybrid+reranker
   - `create_retriever()` - фабрика для создания retriever по режиму
   - `retrieve_documents(query)` - базовая функция поиска для использования в tool
   - `get_retriever()` - доступ к текущему retriever
   - Глобальные переменные: vector_store, retriever, chunks, cross_encoder
   - Убрана query_transformation_chain (агент сам формулирует запросы)

6. **config.py** - конфигурация
   - Класс Config с полями: `TELEGRAM_TOKEN`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `MODEL`, `EMBEDDING_MODEL`, `DATA_DIR`, `PROMPTS_DIR`, `AGENT_SYSTEM_PROMPT_FILE`, `SYSTEM_PROMPT`
   - Новые поля для мониторинга: `LANGSMITH_API_KEY`, `LANGSMITH_TRACING_V2`, `LANGSMITH_PROJECT`, `LANGSMITH_DATASET`
   - Флаг отображения источников: `SHOW_SOURCES`
   - Retrieval режим: `RETRIEVAL_MODE` (semantic/hybrid/hybrid_reranker)
   - Embedding провайдер: `EMBEDDING_PROVIDER` (openai/huggingface)
   - HuggingFace модели: `HUGGINGFACE_EMBEDDING_MODEL`, `HUGGINGFACE_DEVICE`
   - Cross-encoder: `CROSS_ENCODER_MODEL`
   - Параметры retrieval: `SEMANTIC_RETRIEVER_K`, `BM25_RETRIEVER_K`, `RERANKER_TOP_K`
   - Веса ensemble: `ENSEMBLE_SEMANTIC_WEIGHT`, `ENSEMBLE_BM25_WEIGHT`
   - Метод `load_prompt()` для загрузки промптов из файлов
   - Загрузка из .env через python-dotenv

7. **evaluation.py** - оценка качества RAG (новое)
   - `evaluate_dataset(dataset_name)` - запуск evaluation на датасете из LangSmith
   - `check_dataset_exists(name)` - проверка существования датасета
   - `evaluate_with_ragas()` - batch вычисление RAGAS метрик
   - `upload_feedback()` - загрузка результатов в LangSmith
   - Метрики: faithfulness, answer_relevancy, answer_correctness, answer_similarity
   - Используется LangSmith API и RAGAS библиотека

8. **dataset_synthesizer.py** - синтез датасетов (новое)
   - `synthesize_dataset()` - создание QA пар из документов
   - `load_and_sample_documents()` - выборка чанков (по 2 на файл)
   - `synthesize_qa_pairs()` - генерация вопросов и ответов через LLM
   - `upload_to_langsmith()` - загрузка датасета в LangSmith с проверкой дубликатов
   - Запуск через CLI: `python -m src.dataset_synthesizer [--upload]`

9. **mcp/mcp-bank-agent/** - MCP сервер для банковских инструментов
   - `server.py` - FastMCP сервер со streamable-http транспортом (порт 8000)
   - `search_products(product_type, keyword, ...)` - универсальный поиск продуктов банка
   - `currency_converter(from_currency, to_currency, amount)` - конвертация валют через ЦБ РФ API
   - `deposit_income_calculator(amount, rate, term_months, ...)` - расчет доходности вклада
   - `open_credit_card(card_type, client_name)` - открытие кредитной/дебетовой карты (требует HITL)
   - `open_deposit(client_name, amount, term_months, rate)` - открытие вклада (требует HITL)
   - `data/bank_products.json` - статические данные о продуктах Сбербанка
   - Запуск: `make run-mcp-bank` или `cd mcp/mcp-bank-agent && uv run python server.py`

10. **prompts/agent_system.txt** - системный промпт агента (обновлено)
    - Инструкции для всех инструментов включая `open_credit_card`
    - Четкое описание когда использовать каждый инструмент
    - Примеры диалогов для лучшего понимания
    - Правила безопасности для критичных операций

**Поток данных (ReAct Agent с MCP, лимитами, PII и HITL):**
> Счётчики лимитов читают `request.state['messages']` и считают только сообщения **текущего хода** (после последнего `HumanMessage`). LangGraph запускает каждый нод через `copy_context()`, поэтому ContextVar между нодами не работает — источник истины это история сообщений. Параллельные tool calls в одном батче получают тот же объект `state`, что делает `id(request.state)` стабильным ключом батча.
```
Telegram → handlers.py (HumanMessage) →
agent.py::agent_answer() (thread_id = chat_id) →
bank_agent (ReAct цикл; middleware: лимиты → PII → HITL; 5 типов инструментов):
    1. Think (Reason) — **ModelCallLimitMiddleware** считает обращение к LLM (при превышении лимита — текст «Запрос ограничен…» без дальнейших вызовов)
    2. Act — **ToolCallLimitMiddleware** считает каждый вызов инструмента; при превышении возвращается ``ToolMessage`` с пояснением; при норме:
       ├─ tools.py::rag_search(query) → PDF документы
       │  rag.py::retrieve_documents() →
       │  retriever (semantic/hybrid/hybrid_reranker) →
       │  найденные документы → возврат контекста агенту
       │
       ├─ MCP::search_products(product_type, ...) → актуальные продукты
       │  HTTP запрос к mcp-bank-agent (port 8000) →
       │  фильтрация по bank_products.json →
       │  список продуктов → возврат агенту
       │
       ├─ MCP::currency_converter(from, to, amount) → курсы валют
       │  HTTP запрос к mcp-bank-agent (port 8000) →
       │  API запрос к cbr-xml-daily.ru →
       │  текущий курс + конвертация → возврат агенту
       │
       ├─ MCP::deposit_income_calculator(amount, rate, term_months, ...) → расчет доходности
       │  HTTP запрос к mcp-bank-agent (port 8000) →
       │  Расчет локально на MCP сервере →
       │  простой/сложный процент + опциональные налоги →
       │  форматированный результат → возврат агенту
       │
       ├─ MCP::open_credit_card(card_type, client_name) → открытие карты
          ⚠️ INTERRUPT! HumanInTheLoopMiddleware останавливает выполнение
          → (аналогично open_deposit ниже)
          
       └─ MCP::open_deposit(client_name, amount, term_months, rate) → открытие вклада
          ⚠️ INTERRUPT! HumanInTheLoopMiddleware останавливает выполнение
          → возврат interrupt объекта в handlers.py через agent_answer()
          → handlers.py форматирует сообщение из параметров инструмента
          → handlers.py создает InlineKeyboardMarkup с кнопками "✅ Подтвердить" / "❌ Отклонить"
          → показ кнопок Accept/Reject в Telegram
          → сохранение interrupt в pending_interrupts[chat_id]
          
          [Пользователь нажимает кнопку]
          ↓
          handlers.py::handle_hitl_callback (callback_query) →
          удаление кнопок из сообщения →
          agent.py::agent_resume(chat_id, decision="approve"/"reject") →
          
          IF approve:
            → HTTP запрос к mcp-bank-agent (port 8000)
            → MCP сервер выполняет open_credit_card
            → возврат данных карты (номер, платежная система, срок, имя)
            → агент формирует ответ с данными карты → **PIIMiddleware** маскирует PAN в тексте `AIMessage` для пользователя
          IF reject:
            → агент получает сообщение "Операция отклонена пользователем"
            → формирует ответ об отклонении
          
          → очистка pending_interrupts[chat_id]
          
    3. Respond - агент формирует ответ на основе полученных данных; **PIIMiddleware** заменяет номера карт в тексте `AIMessage` на маску (`****-****-****-XXXX`) до передачи в Telegram
    4. End - если информация не нужна, агент отвечает напрямую
→ AIMessage → handlers.py → Telegram

История: MemorySaver в bank_agent (thread_id = chat_id)
Промпты: загружаются из prompts/agent_system.txt
MCP: MultiServerMCPClient подключается к localhost:8000
HITL: pending_interrupts словарь хранит ожидающие подтверждения операции
```

**Принципы разделения инструментов:**
- **rag_search** (PDF документы): общие условия, правила, инструкции из статических документов
- **search_products** (MCP): актуальные ставки, акции, текущие продукты (динамические данные)
- **currency_converter** (MCP): курсы валют в реальном времени через API ЦБ РФ
- **deposit_income_calculator** (MCP): расчет доходности вкладов с капитализацией и налогами
- **open_credit_card** (MCP): открытие дебетовой/кредитной карты; выполнение только после подтверждения пользователем (HumanInTheLoopMiddleware); номер карты в тексте ответа маскируется (PIIMiddleware, см. `middleware.py`)
- **open_deposit** (MCP): открытие вклада (имя клиента, сумма, срок, ставка); выполнение только после подтверждения пользователем (HumanInTheLoopMiddleware); возвращает номер договора и ожидаемый доход

**MCP интеграция:**
- Протокол: streamable-http (HTTP transport для MCP)
- Порт: 8001 (8000 занят mcp-http)
- Клиент: MultiServerMCPClient из langchain-mcp-adapters
- Инструменты подключаются динамически при старте агента
- Stateless: каждый вызов = новая сессия MCP

**Поток данных (Evaluation):**
```
Telegram `/evaluate-dataset` → handlers.py → evaluation.py:

1. Загрузка датасета из LangSmith API
   ↓
2. Запуск RAG для каждого вопроса с трейсингом в LangSmith
   (одновременно собираем: questions, answers, contexts, ground_truths, run_ids)
   ↓
3. Batch вычисление RAGAS метрик на всех собранных данных
   (faithfulness, answer_relevancy, answer_correctness, answer_similarity)
   ↓
4. Загрузка результатов как feedback в LangSmith 
   (привязка метрик к соответствующим run_ids)
   ↓
5. Возврат агрегированных результатов → handlers.py → Telegram

Гибридный подход: трейсинг в LangSmith + эффективный batch processing RAGAS
```

**Принцип:** Никакой DI, никаких интерфейсов, никаких слоев абстракции. Прямые вызовы функций. Глобальные переменные для простых хранилищ. Агент управляет потоком выполнения.

## Модель данных

**Хранение состояния (MemorySaver):**

История диалогов управляется через `MemorySaver` в агенте:
```python
# В agent.py
from langgraph.checkpoint.memory import MemorySaver
checkpointer = MemorySaver()

# В handlers.py
config = {"configurable": {"thread_id": str(chat_id)}}
result = await agent.ainvoke({"messages": messages}, config=config)
```

**Структура:**
- `thread_id` = chat_id пользователя Telegram
- MemorySaver хранит состояние графа агента в памяти
- Агент сам управляет историей через add_messages reducer
- Поддерживает полную историю инструментов и ответов

**Операции:**
- При `/start` - история сбрасывается (новый thread)
- При новом сообщении - агент обрабатывает с учетом истории
- При перезапуске бота - вся история теряется (в памяти)

**Принцип:** Максимальная простота. MemorySaver вместо dict. История управляется агентом. В памяти без персистентности.

## Работа с LLM

**Используемая библиотека:** `openai` (официальный Python client, асинхронная версия)

**Настройка:**
```python
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key=config.OPENAI_API_KEY,
    base_url=config.OPENAI_BASE_URL  # https://openrouter.ai/api/v1
)
```

**Основной метод в llm.py:**
```python
async def get_response(message_history: list[dict]) -> str:
    response = await client.chat.completions.create(
        model=config.MODEL,  # например "openai/gpt-oss-20b:free"
        messages=message_history
    )
    return response.choices[0].message.content
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

**Сценарий 1: Первый запуск / сброс контекста**
1. Пользователь отправляет `/start`
2. Бот отвечает приветственным сообщением
3. MemorySaver инициализирует новый thread — история предыдущего диалога очищается

**Сценарий 2: Вопрос по документам банка**
1. Пользователь пишет вопрос об условиях кредита, вклада и т.п.
2. `handlers.py` передаёт `HumanMessage` в `agent_answer()`
3. Агент (ReAct): рассуждает → вызывает `rag_search` → получает фрагменты из PDF
4. Формирует ответ; `PIIMiddleware` проверяет текст (карты здесь нет) → без изменений
5. `AIMessage` → `handlers.py` → Telegram

**Сценарий 3: Запрос актуальных данных (MCP)**
1. Пользователь спрашивает про текущие ставки / курс валюты / доходность вклада
2. Агент выбирает `search_products`, `currency_converter` или `deposit_income_calculator`
3. `MultiServerMCPClient` → HTTP-запрос к mcp-bank-agent (port 8001)
4. MCP-сервер возвращает данные; агент формирует ответ
5. `PIIMiddleware` проверяет текст → без изменений (номеров карт нет)
6. Ответ → Telegram

**Сценарий 4: Открытие карты (HITL + PII)**
1. Пользователь запрашивает открытие карты
2. Агент вызывает `open_credit_card`; `HumanInTheLoopMiddleware` останавливает выполнение (`__interrupt__`)
3. `handlers.py` показывает кнопки ✅ Подтвердить / ❌ Отклонить
4. **Approve:** `agent_resume(..., "approve")` → MCP выполняет операцию → возвращает данные карты (полный PAN)
   - Агент формирует текст ответа с PAN
   - `PIIMiddleware.awrap_model_call` маскирует PAN в `AIMessage.content` → `****-****-****-XXXX`
   - Замаскированный текст → Telegram
5. **Reject:** `agent_resume(..., "reject")` → агент сообщает об отклонении, карта не открыта

**Сценарий 5: Ручная переиндексация**
1. Пользователь отправляет `/index`
2. `handlers.py` → `indexer.reindex_all()` → пересоздаёт InMemoryVectorStore из PDF
3. Бот подтверждает завершение

**Сценарий 6: Оценка качества**
1. Пользователь отправляет `/evaluate-dataset`
2. `handlers.py` → `evaluation.evaluate_dataset()` → прогоняет все вопросы датасета через RAG
3. RAGAS считает метрики; результаты загружаются в LangSmith как feedback
4. Агрегированные метрики возвращаются в Telegram

**Сценарий 8: Открытие вклада (HITL)**
1. Пользователь запрашивает открытие вклада
2. Агент уточняет все параметры (имя, сумма, ставка, срок), затем вызывает `open_deposit`
3. `HumanInTheLoopMiddleware` создаёт `__interrupt__`, `handlers.py` показывает кнопки ✅ / ❌
4. **Approve:** `agent_resume(..., "approve")` → MCP выполняет операцию → возвращает номер договора и доход
5. **Reject:** агент сообщает об отклонении

**Сценарий 7: Превышение лимитов (защита от зацикливания и злоупотреблений)**
1. Агент пытается сделать более **3** вызовов LLM или более **3** вызовов инструментов за один запрос пользователя (`ModelCallLimitMiddleware` / `ToolCallLimitMiddleware`).
2. При превышении пользователь получает дружественное текстовое сообщение об ограничении (ответ от модели-сообщение или текст из ``ToolMessage``), без падения бота.

**Ограничения:**
- Бот работает только с текстом (фото, файлы, голосовые не обрабатываются)
- История хранится в памяти — при перезапуске теряется
- Один пользователь не блокирует других (asyncio)

## Подход к конфигурированию

**Файл .env** (не коммитится в git):
```bash
# Telegram Bot
TELEGRAM_TOKEN=your_telegram_bot_token

# LLM Provider
OPENAI_API_KEY=your_openrouter_api_key
OPENAI_BASE_URL=https://openrouter.ai/api/v1
MODEL=openai/gpt-oss-20b:free
MODEL_QUERY_TRANSFORM=gpt-4o
EMBEDDING_MODEL=text-embedding-3-large

# Data & Prompts
DATA_DIR=data
SYSTEM_PROMPT=Ты ассистент Сбербанка, отвечающий на вопросы по документам.

# LangSmith (опционально, для трейсинга и evaluation)
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_TRACING_V2=true
LANGSMITH_PROJECT=rag-bot
LANGSMITH_DATASET=06-rag-qa-dataset

# Features
SHOW_SOURCES=false
```

**Файл .env.example** (коммитится):
```bash
# Telegram Bot
TELEGRAM_TOKEN=

# LLM Provider
OPENAI_API_KEY=
OPENAI_BASE_URL=https://openrouter.ai/api/v1
MODEL=openai/gpt-oss-20b:free
MODEL_QUERY_TRANSFORM=gpt-4o
EMBEDDING_MODEL=text-embedding-3-large

# Data & Prompts
DATA_DIR=data
SYSTEM_PROMPT=Ты ассистент, отвечающий на вопросы по документам.

# LangSmith (опционально, для трейсинга и evaluation)
LANGSMITH_API_KEY=
LANGSMITH_TRACING_V2=false
LANGSMITH_PROJECT=rag-bot
LANGSMITH_DATASET=06-rag-qa-dataset

# Features
SHOW_SOURCES=false
```

**config.py:**
```python
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram & LLM
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
    MODEL = os.getenv("MODEL")
    MODEL_QUERY_TRANSFORM = os.getenv("MODEL_QUERY_TRANSFORM")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
    DATA_DIR = os.getenv("DATA_DIR", "data")
    SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT")
    
    # LangSmith (опционально)
    LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
    LANGSMITH_TRACING_V2 = os.getenv("LANGSMITH_TRACING_V2", "false")
    LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "rag-bot")
    LANGSMITH_DATASET = os.getenv("LANGSMITH_DATASET", "06-rag-qa-dataset")
    
    # Features
    SHOW_SOURCES = os.getenv("SHOW_SOURCES", "false").lower() == "true"

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

**Вывод:** Только в stdout/stderr (консоль)

**Принципы:**
- Без внешних библиотек (structlog и т.п.)
- Без файлов, ротации логов
- Без отправки в внешние системы
- Простой текстовый формат

## Оценка качества RAG (RAGAS)

### Метрики

**faithfulness** (обоснованность):
- Проверяет, что ответ основан на retrieved documents
- Отсутствие галлюцинаций и выдуманных фактов
- Значение от 0.0 до 1.0 (выше = лучше)

**answer_relevancy** (релевантность):
- Насколько ответ релевантен заданному вопросу
- Проверяет, что ответ действительно отвечает на вопрос
- Значение от 0.0 до 1.0 (выше = лучше)

**answer_correctness** (правильность):
- Правильность ответа относительно ground truth (эталона)
- Комбинирует факт-чекинг и семантическую похожесть
- Значение от 0.0 до 1.0 (выше = лучше)

**answer_similarity** (семантическая похожесть):
- Семантическая похожесть ответа на ground truth
- Фокус на смысле, а не на точных формулировках
- Значение от 0.0 до 1.0 (выше = лучше)

### Интеграция с LangSmith

**Автоматический трейсинг:**
Все вызовы RAG цепочки автоматически логируются в LangSmith при установке переменных окружения:
- `LANGSMITH_TRACING_V2=true` - включает трейсинг
- `LANGSMITH_PROJECT=<name>` - группирует traces в проект
- Детальные traces: latency, tokens, промежуточные шаги

**Датасеты:**
- Хранение тестовых QA пар в LangSmith
- Формат: inputs (question), outputs (answer), metadata (contexts)
- API для загрузки и получения датасетов

**Feedback:**
- Результаты RAGAS метрик загружаются как feedback к traces
- Визуализация в LangSmith UI
- Сравнение экспериментов и версий RAG pipeline

### Синтез датасетов

**Процесс:**
1. Загрузка PDF документов из data/
2. Выбор репрезентативных чанков (по 2 на файл)
3. Генерация QA пар через LLM с промптом из ноутбука
4. Сохранение в JSON: datasets/06-rag-qa-dataset.json
5. Загрузка в LangSmith с проверкой дубликатов

**Формат датасета:**
```json
{
  "question": "Вопрос по документу",
  "ground_truth": "Правильный ответ",
  "contexts": ["Релевантный текст из документа"],
  "metadata": {
    "source": "filename.pdf",
    "page": 3
  }
}
```

## Режимы Retrieval

### Semantic (по умолчанию)
Классический векторный поиск:
- Embeddings превращают текст в векторы
- Косинусное сходство для поиска похожих фрагментов
- Хорошо работает с синонимами и перефразированиями

**Когда использовать:**
- Вопросы с разными формулировками
- Поиск по смыслу без точных терминов
- Базовая настройка (fastest)

### Hybrid (Semantic + BM25)
Комбинация векторного и лексического поиска:
- Semantic находит по смыслу
- BM25 находит точные совпадения слов
- RRF объединяет результаты с весами

**Когда использовать:**
- Вопросы с важными терминами (номера, названия)
- Нужен баланс между смыслом и точностью
- Улучшенное качество без больших затрат

### Hybrid + Reranker
Hybrid retrieval + Cross-encoder переранжирование:
- Сначала hybrid retrieval (широкий поиск)
- Затем cross-encoder точно оценивает каждую пару (вопрос, документ)
- Финальная выборка top_k наиболее релевантных

**Когда использовать:**
- Production окружение (лучшее качество)
- Критичные вопросы требующие точности
- Есть ресурсы для дополнительной обработки

**Модели:**
- Embeddings: multilingual-e5-base (278M, 1.1GB)
- Cross-encoder: mmarco-mMiniLMv2-L12-H384-v1 (117M, 470MB)
- Работают на CPU без GPU

## Выбор Embedding провайдера

### OpenAI (по умолчанию)
- Облачные embeddings через API
- Высокое качество (text-embedding-3-large)
- Требует OPENAI_API_KEY
- Быстрый старт

### HuggingFace (локальные)
- Модели на CPU/GPU
- Нет зависимости от внешних API
- multilingual-e5-base (поддержка русского)
- Больше контроля и приватности


