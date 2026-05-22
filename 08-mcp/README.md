# ReAct Agent с Advanced Hybrid RAG

Интеллектуальный Telegram-бот на базе ReAct агента (Reason + Act) с продвинутым RAG (Retrieval-Augmented Generation) для автономных ответов на вопросы по документам Сбербанка.

## ✨ Возможности

### 🤖 ReAct Agent (Автономный ИИ)
- 🧠 **Самостоятельное принятие решений** - агент сам выбирает какой инструмент использовать
- 🔄 **ReAct паттерн:**
  - **Reason (Think)** - анализирует вопрос и контекст
  - **Act** - вызывает нужный инструмент (rag_search / MCP-инструменты)
  - **Respond** - формирует ответ на основе полученных данных
- 🛠️ **4 типа инструментов:**
  - `rag_search` - поиск в статических PDF документах
  - `search_products` - актуальные банковские продукты (MCP)
  - `currency_converter` - курсы валют ЦБ РФ (MCP)
  - `calculate_deposit_profit` - расчёт доходности вклада по сумме, ставке и сроку (MCP)
- 💾 **MemorySaver** - автоматическое сохранение истории диалогов
- 🎯 **Умная стратегия:**
  - Простые вопросы ("привет", "спасибо") → отвечает напрямую
  - Общие условия → использует rag_search (PDF документы)
  - Актуальные ставки и продукты → использует search_products (MCP)
  - Курсы валют → использует currency_converter (MCP)
  - «Сколько заработаю на вкладе» → использует calculate_deposit_profit (MCP)
- 📝 **Гибкие промпты** - системный промпт загружается из файла

### 🔍 Advanced Hybrid RAG
- 🔍 **3 режима Retrieval:**
  - **Semantic** - классический векторный поиск по смыслу
  - **Hybrid** - комбинация Semantic + BM25 для точных терминов
  - **Hybrid + Reranker** - Hybrid + Cross-encoder для максимальной точности
- 🧬 **Конфигурируемые Embeddings:**
  - **OpenAI** - облачные embeddings (text-embedding-3-large)
  - **HuggingFace** - локальные модели (multilingual-e5-base)
- 🎯 **Cross-Encoder Reranking** - точное переранжирование документов
- ⚖️ **Настраиваемые веса** - балансировка между semantic и BM25

### 📚 Работа с документами
- 📄 **Индексация PDF + JSON** - автоматическая обработка документов и готовых Q&A пар
- 💬 **Контекстный диалог** - понимание уточняющих вопросов через MemorySaver
- 📖 **Отображение источников** - опциональный показ документов для ответа

### 📊 Мониторинг и Quality Assurance
- 📊 **LangSmith трейсинг** - детальный мониторинг RAG pipeline
- 🧪 **Автоматический синтез датасетов** - генерация тестовых Q&A пар
- 📈 **RAGAS Evaluation** - оценка качества с 6 метриками через команду бота
- ⚡ **Асинхронная обработка** - множество пользователей одновременно
- 📝 **Детальное логирование** - запись всех событий для отладки

## 🚀 Быстрый старт

### Требования

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) - менеджер зависимостей

### Установка

1. Клонируйте репозиторий и перейдите в каталог модуля:
   ```bash
   git clone <repository-url>
   cd 08-mcp
   ```

2. Установите зависимости:
   ```bash
   make install
   ```

3. Настройте переменные окружения:
   ```bash
   cp env.example .env
   ```

4. Отредактируйте `.env` (см. раздел "Конфигурация")

5. (Опционально) Запустите MCP сервер для динамических данных:
   ```bash
   make run-mcp-bank
   ```
   
   Сервер предоставляет:
   - Актуальные банковские продукты (вклады, кредиты, карты)
   - Курсы валют ЦБ РФ в реальном времени
   - Расчёт доходности вклада (с капитализацией или без)

6. Запустите бота:
   ```bash
   make run
   ```

## ⚙️ Конфигурация

### Получение токенов

**Telegram Bot Token:**
1. Найдите @BotFather в Telegram
2. Отправьте `/newbot` и следуйте инструкциям
3. Скопируйте токен

**API ключи провайдеров:**

Бот поддерживает работу с разными провайдерами LLM через OpenAI-совместимый API.

#### OpenRouter

1. Зарегистрируйтесь на [OpenRouter.ai](https://openrouter.ai/)
2. Перейдите в раздел API Keys
3. Создайте новый ключ

#### Fireworks

1. Зарегистрируйтесь на [Fireworks.ai](https://fireworks.ai/)
2. Перейдите в раздел API Keys
3. Создайте новый ключ

### Примеры конфигурации

**OpenRouter (рекомендуется для разработки):**

```bash
TELEGRAM_TOKEN=your_telegram_bot_token

OPENAI_API_KEY=sk-or-v1-...
OPENAI_BASE_URL=https://openrouter.ai/api/v1
MODEL=openai/gpt-4o
EMBEDDING_MODEL=openai/text-embedding-3-large

DATA_DIR=data
PROMPTS_DIR=prompts
AGENT_SYSTEM_PROMPT_FILE=agent_system.txt

MCP_ENABLED=true
MCP_SERVER_URL=http://localhost:8000/mcp
```

**Fireworks (только отличия от OpenRouter):**

```bash
OPENAI_API_KEY=fw_...
OPENAI_BASE_URL=https://api.fireworks.ai/inference/v1
MODEL=accounts/fireworks/models/gpt-oss-120b
EMBEDDING_MODEL=accounts/fireworks/models/qwen3-embedding-8b
```

Полный шаблон — **`env.example`**. Поведение агента — **`prompts/agent_system.txt`** (`AGENT_SYSTEM_PROMPT_FILE`). Переменные `SYSTEM_PROMPT`, `conversation_system.txt`, `query_transform.txt` **не используются**.

### Описание параметров

**Обязательные:**
- `TELEGRAM_TOKEN` - токен бота от @BotFather
- `OPENAI_API_KEY` - API ключ от выбранного провайдера
- `OPENAI_BASE_URL` - URL API провайдера

**Модели:**
- `MODEL` - модель для ReAct агента (принятие решений и генерация ответов)
- `EMBEDDING_MODEL` - модель для создания эмбеддингов документов

**Пути и промпт агента:**
- `DATA_DIR` — PDF для RAG (по умолчанию: `data`)
- `PROMPTS_DIR` — каталог промптов (по умолчанию: `prompts`)
- `AGENT_SYSTEM_PROMPT_FILE` — файл системного промпта (по умолчанию: `agent_system.txt`)

**MCP:**
- `MCP_ENABLED` — подключать MCP-инструменты (по умолчанию: `true`)
- `MCP_SERVER_URL` — URL сервера (по умолчанию: `http://localhost:8000/mcp`)

**RAG (опционально):** `RETRIEVAL_MODE`, `EMBEDDING_PROVIDER` и др. — см. [Advanced Hybrid RAG](#-advanced-hybrid-rag) и `env.example`.

## 📚 Добавление документов

1. Поместите PDF файлы в директорию `data/`
2. Перезапустите бота (документы проиндексируются автоматически)
   
   ИЛИ
   
3. Используйте команду `/index` в Telegram для переиндексации

**Примечание:** Бот автоматически:
- Загружает все PDF из `data/`
- Разбивает на чанки по 500 символов
- Создает векторные эмбеддинги
- Сохраняет в памяти для быстрого поиска

## 💬 Использование

### Команды бота

- `/start` - Начать новый диалог (сбросить историю)
- `/help` - Показать справку
- `/index` - Переиндексировать документы
- `/index_status` - Проверить статус индексации
- `/evaluate_dataset` - Оценить качество RAG системы (требует LangSmith)

### Примеры диалогов

**Поиск в документах (rag_search):**
```
👤 Какие условия потребительского кредита?
🤖 По документу, потребительский кредит предоставляется на сумму от 30 000 до 5 000 000 рублей, 
   на срок от 3 месяцев до 5 лет. Процентная ставка зависит от категории заемщика и составляет 
   от 12.9% до 19.9% годовых.
```

**Актуальные продукты (search_products via MCP):**
```
👤 Какие сейчас ставки по вкладам?
🤖 Найдено 4 вклада:

   1. Пополняй — от 15% до 16% годовых, от 1 000 ₽
   2. Сохраняй — от 16% до 17% годовых, от 50 000 ₽
   3. Накопительный счёт — от 12% до 14% годовых
   4. Пенсионный Плюс — от 17% до 18% годовых (для пенсионеров)
```

**Расчёт вклада (calculate_deposit_profit via MCP):**
```
👤 Сколько будет 100 000 ₽ под 15% на 12 месяцев с капитализацией?
🤖 Ожидаемый доход: ~16 075 ₽, итого к концу срока: ~116 075 ₽
   (приблизительный расчёт; не оферта банка)
```

**Курсы валют (currency_converter via MCP):**
```
👤 Какой курс доллара?
🤖 Курс 1 USD = 92.4500 RUB

👤 Сколько будет 1000 долларов в рублях?
🤖 1,000.00 USD = 92,450.00 RUB
```

**Комбинированный диалог (агент сам выбирает инструмент):**
```
👤 Какие вклады есть в Сбербанке?
🤖 [использует search_products] 
   Доступно 4 вида вкладов: Пополняй, Сохраняй, Накопительный счёт, Пенсионный Плюс...

👤 А какие требования к вкладчикам?
🤖 [использует rag_search]
   По документу, для открытия вклада требуется...

👤 Сколько заработаю, если положу 100 000 под 15% на год с капитализацией?
🤖 [использует calculate_deposit_profit]
   Ожидаемый доход и итоговая сумма по заданным параметрам...

👤 Какой курс евро?
🤖 [использует currency_converter]
   Курс 1 EUR = 100.2300 RUB
```

**Вопрос вне контекста:**
```
👤 Какая погода сегодня?
🤖 Извините, я не могу ответить на этот вопрос. Я помогаю с информацией о банковских продуктах.
```

## 🏗️ Архитектура

### Структура проекта

```
├── src/
│   ├── bot.py                  # Точка входа, инициализация, логирование
│   ├── config.py               # Загрузка конфигурации из .env
│   ├── handlers.py             # Обработчики команд и сообщений
│   ├── agent.py                # ReAct агент с MCP инструментами
│   ├── tools.py                # Инструмент rag_search
│   ├── indexer.py              # Загрузка и индексация PDF + JSON
│   ├── rag.py                  # RAG: retriever, режимы semantic/hybrid/reranker
│   ├── dataset_synthesizer.py  # Синтез тестовых датасетов
│   └── evaluation.py           # Оценка качества через RAGAS
├── mcp/
│   └── mcp-bank-agent/         # MCP сервер для динамических данных
│       ├── server.py           # FastMCP: search_products, currency_converter, calculate_deposit_profit
│       ├── data/
│       │   └── bank_products.json  # База актуальных продуктов
│       ├── Makefile            # Команды для MCP сервера
│       └── README.md           # Документация MCP сервера
├── prompts/
│   └── agent_system.txt        # Системный промпт агента
├── data/                       # PDF документы и JSON Q&A для индексации
├── datasets/                   # Сгенерированные датасеты для evaluation
├── logs/                       # Логи работы бота
├── docs/                       # Документация и референсы
├── .env                        # Конфигурация (не в git)
├── env.example                 # Пример конфигурации
├── Makefile                    # Команды для работы
├── pyproject.toml              # Зависимости
└── README.md                   # Документация
```

### Как работает ReAct Agent с MCP

1. **Индексация** (при старте бота):
   ```
   PDF документы → Разбиение на чанки → Создание эмбеддингов → Векторное хранилище (в памяти)
   ```

2. **Подключение к MCP** (при старте бота):
   ```
   MCP Client → http://localhost:8000/mcp → Загрузка инструментов (search_products, currency_converter, calculate_deposit_profit)
   ```

3. **Обработка вопроса пользователя**:
   ```
   Вопрос → ReAct Agent думает (Reason) → 
   → Выбирает инструмент (Act):
     • rag_search (PDF)
     • search_products (MCP)
     • currency_converter (MCP)
     • calculate_deposit_profit (MCP)
   → Получает данные → Формирует ответ (Respond)
   ```

4. **Контекстный диалог**:
   - История сохраняется через MemorySaver (thread_id = chat_id)
   - Агент сам выбирает какой инструмент использовать
   - Может комбинировать инструменты в одном диалоге

### Технологический стек

**Core:**
- **aiogram 3.x** - Telegram Bot API
- **LangChain** - фреймворк для RAG и агентов
- **LangChain OpenAI** - интеграция с OpenAI-совместимыми API
- **LangChain Community** - BM25Retriever, EnsembleRetriever
- **LangChain Classic** - EnsembleRetriever для hybrid режима
- **LangGraph** - ReAct агент с MemorySaver
- **PyPDF** - парсинг PDF документов
- **InMemoryVectorStore** - векторное хранилище в памяти

**MCP Integration:**
- **langchain-mcp-adapters** - адаптеры для MCP инструментов
- **FastMCP** - MCP сервер для динамических данных
- **httpx** - HTTP клиент для MCP streamable HTTP

**Advanced Retrieval:**
- **LangChain HuggingFace** - локальные embeddings модели
- **sentence-transformers** - embeddings и cross-encoder для reranking
- **rank-bm25** - BM25 алгоритм для лексического поиска

**Quality & Monitoring:**
- **LangSmith** - мониторинг и трейсинг RAG pipeline
- **RAGAS** - evaluation качества RAG систем (6 метрик)
- **datasets** - работа с датасетами для evaluation

## 📖 Отображение источников

Бот может показывать источники документов, использованных для генерации ответа.

### Настройка

В `.env` файле установите:
```bash
SHOW_SOURCES=true
```

### Пример работы

С `SHOW_SOURCES=true`:
```
👤 Какие условия потребительского кредита?
🤖 По документу, потребительский кредит предоставляется на сумму от 30 000 
   до 5 000 000 рублей, на срок от 3 месяцев до 5 лет...

📚 Источники: ouk_potrebitelskiy_kredit_lph.pdf (стр. 1, 3, 5)
```

С `SHOW_SOURCES=false` (по умолчанию) источники не показываются.

## 🎯 Advanced Hybrid RAG

### Режимы Retrieval

Бот поддерживает 3 режима поиска документов с разным балансом качества и скорости:

#### 1. **Semantic** (по умолчанию)
Классический векторный поиск через embedding similarity.

```bash
RETRIEVAL_MODE=semantic
SEMANTIC_RETRIEVER_K=10
```

**Когда использовать:**
- Вопросы с разными формулировками
- Поиск по смыслу без точных терминов
- Быстрая работа на CPU

#### 2. **Hybrid** (Semantic + BM25)
Комбинация векторного и лексического поиска.

```bash
RETRIEVAL_MODE=hybrid
SEMANTIC_RETRIEVER_K=10
BM25_RETRIEVER_K=10
ENSEMBLE_SEMANTIC_WEIGHT=0.5
ENSEMBLE_BM25_WEIGHT=0.5
```

**Когда использовать:**
- Вопросы с важными терминами (номера, названия)
- Нужен баланс между смыслом и точностью
- Улучшенное качество без больших затрат

**Как работает:**
1. Semantic находит документы по смыслу
2. BM25 находит точные совпадения слов
3. RRF (Reciprocal Rank Fusion) объединяет результаты с весами

#### 3. **Hybrid + Reranker** (максимальная точность)
Hybrid retrieval + Cross-encoder переранжирование.

```bash
RETRIEVAL_MODE=hybrid_reranker
SEMANTIC_RETRIEVER_K=10
BM25_RETRIEVER_K=10
RERANKER_TOP_K=3
CROSS_ENCODER_MODEL=cross-encoder/mmarco-mMiniLMv2-L12-H384-v1
```

**Когда использовать:**
- Production окружение (лучшее качество)
- Критичные вопросы требующие точности
- Есть ресурсы для дополнительной обработки

**Как работает:**
1. Hybrid retrieval получает топ-10+10 документов
2. Cross-encoder оценивает каждую пару (вопрос, документ)
3. Возвращаются топ-3 наиболее релевантных

### Сравнение режимов

| Характеристика | Semantic | Hybrid | Hybrid + Reranker |
|---|---|---|---|
| **Качество поиска** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Скорость** | 🚀🚀🚀 | 🚀🚀 | 🚀 |
| **Точные термины** | ❌ | ✅ | ✅ |
| **Семантика** | ✅ | ✅ | ✅ |
| **Требования CPU** | Низкие | Средние | Высокие |
| **Latency** | ~100ms | ~200ms | ~500ms |
| **Рекомендация** | Разработка | Production (balanced) | Production (best) |

### Конфигурируемые Embeddings

Бот поддерживает 2 провайдера embeddings:

#### OpenAI (по умолчанию)
Облачные embeddings через API.

```bash
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-large
```

**Преимущества:**
- ✅ Высокое качество (sota models)
- ✅ Быстрый старт (нет загрузки моделей)
- ✅ Не требует ресурсов на сервере

**Недостатки:**
- ❌ Требует API ключ и интернет
- ❌ Стоимость API вызовов
- ❌ Зависимость от внешнего сервиса

#### HuggingFace (локальные)
Модели на вашем сервере.

```bash
EMBEDDING_PROVIDER=huggingface
HUGGINGFACE_EMBEDDING_MODEL=intfloat/multilingual-e5-base
HUGGINGFACE_DEVICE=cpu  # cpu, cuda, mps
```

**Преимущества:**
- ✅ Полная приватность (без отправки данных)
- ✅ Нет зависимости от API
- ✅ Нет costs после загрузки модели
- ✅ Поддержка GPU для ускорения

**Недостатки:**
- ❌ Требует ~1.1GB памяти на модель
- ❌ Первая загрузка занимает время
- ❌ Медленнее на CPU vs облачные

### Требования к ресурсам

#### Минимальная конфигурация (Semantic + OpenAI)
- **CPU:** 2 cores
- **RAM:** 1GB
- **Диск:** 100MB

#### Рекомендуемая конфигурация (Hybrid + HuggingFace)
- **CPU:** 4 cores
- **RAM:** 4GB
- **Диск:** 2GB (модели embeddings)

#### Production конфигурация (Hybrid Reranker + HuggingFace)
- **CPU:** 8 cores или GPU
- **RAM:** 8GB
- **Диск:** 3GB (embeddings + cross-encoder ~470MB)

**Модели и их размеры:**
- `multilingual-e5-base`: 278M параметров, 1.1GB
- `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`: 117M параметров, 470MB

## 📊 Мониторинг и оценка качества

### LangSmith трейсинг

Для детального мониторинга RAG pipeline настройте LangSmith:

**1. Получите API ключ:**
- Зарегистрируйтесь на [smith.langchain.com](https://smith.langchain.com)
- Создайте API ключ в разделе Settings

**2. Добавьте в `.env`:**
```bash
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_TRACING_V2=true
LANGSMITH_PROJECT=rag-assistant
```

**3. Что даёт трейсинг:**
- 🔍 Детальные traces каждого запроса RAG
- 📊 Анализ latency и token usage
- 🐛 Отладка промежуточных шагов
- 💰 Отслеживание стоимости API вызовов

Все запросы к RAG автоматически логируются в LangSmith UI.

### Создание тестовых датасетов

Автоматический синтез Q&A пар из ваших документов для evaluation:

```bash
# Создать датасет (по 2 Q&A из каждого PDF + JSON файла)
make dataset

# Загрузить датасет в LangSmith
make dataset-upload
```

**Что происходит:**
1. Загружаются PDF документы, выбираются чанки
2. LLM генерирует вопросы и ответы на основе чанков
3. Загружаются готовые Q&A пары из JSON файлов
4. Всё сохраняется в `datasets/06-rag-qa-dataset.json`
5. Опционально загружается в LangSmith для evaluation

### Evaluation через RAGAS

Оценка качества RAG системы прямо из Telegram:

**1. Убедитесь что датасет загружен:**
```bash
make dataset-upload
```

**2. В Telegram отправьте команду:**
```
/evaluate_dataset
```

**3. Получите результаты с 6 RAGAS метриками:**
```
✅ Evaluation завершен!

📊 Датасет: 06-rag-qa-dataset
📝 Примеров обработано: 8

🎯 RAGAS Метрики:
🟢 Обоснованность (нет галлюцинаций): 0.875
🟡 Релевантность ответа: 0.654  
🟢 Правильность ответа: 0.823
🟢 Похожесть на эталон: 0.891
🟡 Полнота контекста: 0.750
🟢 Точность поиска: 0.833

💡 Результаты загружены в LangSmith как feedback
```

### Описание RAGAS метрик

- **Faithfulness (Обоснованность)** - ответ не содержит галлюцинаций и основан только на retrieved документах
- **Answer Relevancy (Релевантность)** - ответ релевантен заданному вопросу  
- **Answer Correctness (Правильность)** - ответ соответствует ground truth эталону
- **Answer Similarity (Похожесть)** - семантическая похожесть ответа на эталон
- **Context Recall (Полнота контекста)** - retrieved документы содержат информацию для правильного ответа
- **Context Precision (Точность поиска)** - retrieved документы релевантны вопросу

🟢 0.8+ отличный результат | 🟡 0.6-0.8 хороший | 🔴 <0.6 требует улучшений

### Настройка RAGAS моделей

По умолчанию для evaluation используются фиксированные модели для единообразной оценки:

```bash
RAGAS_LLM_MODEL=gpt-4o
RAGAS_EMBEDDING_MODEL=text-embedding-3-large
```

Можно изменить в `.env` если нужны другие модели для оценки.

## 🔧 Разработка

### Команды Makefile

```bash
make install         # Установить зависимости
make run             # Запустить бота
make run-mcp-bank    # Запустить MCP сервер (порт 8000)
make dataset         # Создать тестовый датасет
make dataset-upload  # Загрузить датасет в LangSmith
```

Подробнее по MCP-серверу: [mcp/mcp-bank-agent/README.md](mcp/mcp-bank-agent/README.md)

### 🏦 MCP Сервер

MCP (Model Context Protocol) сервер предоставляет динамические данные для агента:

**Инструменты:**
- `search_products` - поиск актуальных банковских продуктов (вклады, кредиты, карты, счета)
- `currency_converter` - конвертация валют по курсам ЦБ РФ
- `calculate_deposit_profit` - расчёт дохода и итоговой суммы вклада (без внешних API)

**Запуск:**
```bash
# В отдельном терминале (удобнее на Windows — без вложенного make):
cd mcp/mcp-bank-agent
uv run server.py

# Или из корневой директории
make run-mcp-bank
```

**Проверка:** сервер слушает порт 8000 (`Uvicorn running on http://127.0.0.1:8000`); в Telegram — вопросы про вклады, курс USD или расчёт вклада.

**Конфигурация через `.env`:**
```bash
# Включить/выключить MCP инструменты
MCP_ENABLED=true

# Настройки MCP сервера
MCP_SERVER_NAME=mcp-bank-agent
MCP_SERVER_URL=http://localhost:8000/mcp
MCP_SERVER_TRANSPORT=streamable_http
```

**Файлы данных:**
- База продуктов: `mcp/mcp-bank-agent/data/bank_products.json`
- API валют: `https://www.cbr-xml-daily.ru/latest.js`

**Graceful degradation:**
Если `MCP_ENABLED=false` или MCP сервер недоступен, бот продолжит работать с `rag_search` без MCP-инструментов.

### Редактирование промптов

Системный промпт ReAct-агента — **`prompts/agent_system.txt`**: когда вызывать `rag_search`, MCP-инструменты и примеры вызовов. Редактируется без изменения кода; после правок перезапустите бота.

### Логи

Логи записываются в `logs/bot.log` и дублируются в консоль.

**Логируются:**
- Старт/остановка бота
- Процесс индексации документов
- Входящие сообщения от пользователей
- Ошибки и исключения

**Пример лога:**
```
2025-11-07 18:32:37,399 - __main__ - INFO - Starting indexing...
2025-11-07 18:32:38,384 - indexer - INFO - Split into 377 chunks
2025-11-07 18:32:41,314 - indexer - INFO - Created vector store with 377 chunks
2025-11-07 18:32:41,314 - __main__ - INFO - Indexing completed successfully
```

### Настройка параметров RAG

- **Чанки:** `chunk_size=500`, `chunk_overlap=50` в `src/indexer.py`
- **Retrieval:** `RETRIEVAL_MODE`, `SEMANTIC_RETRIEVER_K`, `BM25_RETRIEVER_K` и др. в `.env` (см. `env.example`)
- **Temperature агента:** `temperature=0.7` в `src/agent.py`

## ⚠️ Ограничения

- История хранится в памяти (теряется при перезапуске)
- Векторное хранилище в памяти (требует переиндексации после перезапуска)
- Только текстовые сообщения (нет поддержки фото, файлов, голосовых)
- Ответы основаны только на проиндексированных документах
- При большом количестве документов может требоваться больше памяти

## 🐛 Устранение неполадок

**Проблема: MCP-инструменты не работают**
- Запустите MCP сервер в отдельном терминале: `make run-mcp-bank` или `cd mcp/mcp-bank-agent && uv run server.py`
- Проверьте `MCP_ENABLED=true` и `MCP_SERVER_URL=http://localhost:8000/mcp` в `.env`
- На Windows при Ctrl+C может спросить «Завершить выполнение пакетного файла?» — ответьте **Y**

**Проблема: Бот не отвечает на вопросы**
- Проверьте `/index_status` - должны быть проиндексированы документы
- Убедитесь, что PDF файлы находятся в `data/`
- Проверьте логи в `logs/bot.log`

**Проблема: Ошибка при индексации**
- Проверьте корректность `EMBEDDING_MODEL` для вашего провайдера
- Убедитесь, что API ключ валиден и имеет доступ к embeddings

**Проблема: Бот отвечает "Я не нашел ответа" на все вопросы**
- Возможно, вопросы не связаны с содержимым документов
- Попробуйте задать более конкретные вопросы по тематике документов
- Проверьте, что индексация прошла успешно (`/index_status`)

## 📄 Документация проекта

| Файл | Содержание |
|------|------------|
| [docs/idea.md](docs/idea.md) | Бизнес-идея, эволюция функционала (в т.ч. MCP и расчёт вклада) |
| [docs/vision.md](docs/vision.md) | Техническое видение, архитектура, разделение инструментов |
| [docs/tasklist.md](docs/tasklist.md) | План итераций: спринты 1–7; **ДЗ-08** (шаг 1 — проверка Спр. 6, шаг 2 — **Спринт 7**) |
| [mcp/mcp-bank-agent/README.md](mcp/mcp-bank-agent/README.md) | MCP-сервер: инструменты и примеры |

## 📝 Лицензия

MIT
