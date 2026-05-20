# План разработки RAG-ассистента на базе LangChain

## 📊 Отчет о прогрессе

| Спринт | Итерация | Функционал | Статус | Дата |
|--------|----------|------------|--------|------|
| 1 | 1 | Базовый эхо-бот с конфигурацией | ✅ Завершено | 28.10.2025 |
| 1 | 2 | Интеграция с LLM | ✅ Завершено | 28.10.2025 |
| 1 | 3 | История диалогов | ✅ Завершено | 28.10.2025 |
| 1 | 4 | Финальная полировка | ✅ Завершено | 28.10.2025 |
| 2 | 5 | Индексация PDF с командами управления | ✅ Завершено | 07.11.2025 |
| 2 | 6 | Полноценный RAG с query transformation | ✅ Завершено | 07.11.2025 |
| 2 | 7 | Финальная полировка и документация | ✅ Завершено | 07.11.2025 |
| 3 | 8 | Рефакторинг RAG с отображением источников | ✅ Завершено | 12.11.2025 |
| 3 | 9 | Синтез тестовых датасетов | ✅ Завершено | 12.11.2025 |
| 3 | 10 | Система оценки качества через RAGAS | ✅ Завершено | 12.11.2025 |
| 3 | 11 | Финальная полировка и документация | ✅ Завершено | 12.11.2025 |
| 4 | 12 | Конфигурируемые embeddings (OpenAI + HuggingFace) | ✅ Завершено | 12.11.2025 |
| 4 | 13 | Hybrid Retrieval (Semantic + BM25) | ✅ Завершено | 12.11.2025 |
| 4 | 14 | Cross-Encoder Reranking | ✅ Завершено | 12.11.2025 |
| 4 | 15 | Финальная полировка и документация | ✅ Завершено | 12.11.2025 |

**Легенда статусов:**
- ⏳ Не начато
- 🚧 В работе
- ✅ Завершено
- ❌ Заблокировано

---

## 🚀 Спринт 1: Базовый LLM-бот (Завершено)

### Итерация 1: Базовый эхо-бот с конфигурацией

**Цель:** Запустить простейшего Telegram бота с конфигурацией через .env

- [x] Создать `pyproject.toml` с зависимостями: aiogram, openai, python-dotenv
- [x] Создать структуру папок: `src/`
- [x] Создать `.env.example` с шаблоном переменных
- [x] Создать `.gitignore` (`.env`, `__pycache__`, `.venv`)
- [x] Создать `Makefile` с командами: `install`, `run`
- [x] Создать базовый `README.md` с инструкцией по запуску
- [x] Создать `src/config.py` с классом Config и загрузкой из .env
- [x] Создать `src/bot.py` с инициализацией Bot и Dispatcher
- [x] Создать `src/handlers.py` с обработчиками `/start` и эхо-ответов
- [x] Добавить базовое логирование (старт бота, входящие сообщения)

**Как протестировать:**
- `uv sync` устанавливает зависимости
- Создать `.env` файл с TELEGRAM_TOKEN
- Запустить бота: `make run`
- Отправить `/start` → получить приветствие
- Отправить любой текст → получить его же обратно

---

### Итерация 2: Интеграция с LLM

**Цель:** Заменить эхо на реальные ответы от LLM

- [x] Создать `src/llm.py` с функцией `get_response(messages: list) -> str`
- [x] Инициализировать AsyncOpenAI клиент с настройками из config
- [x] Обработать ошибки при вызове LLM (try/except)
- [x] Обновить обработчик сообщений: отправлять запрос в LLM
- [x] Пока без истории - отправлять только текущее сообщение

**Как протестировать:**
- Отправить вопрос боту
- Получить осмысленный ответ от LLM
- Проверить, что ошибки сети обрабатываются корректно

---

### Итерация 3: История диалогов

**Цель:** Добавить контекст диалога, чтобы LLM помнил предыдущие сообщения

- [x] Создать глобальный словарь `chat_conversations: dict[int, list[dict]]`
- [x] При `/start` инициализировать историю с системным промптом
- [x] При новом сообщении добавлять его в историю чата
- [x] Передавать всю историю в `llm.get_response()`
- [x] Сохранять ответ LLM в историю

**Как протестировать:**
- Начать диалог: "Меня зовут Иван"
- Спросить: "Как меня зовут?"
- LLM должен ответить "Иван"
- Отправить `/start` и повторить вопрос - LLM не должен помнить имя

---

### Итерация 4: Финальная полировка

**Цель:** Довести бота до production-ready состояния

- [x] Улучшить сообщения об ошибках для пользователя
- [x] Добавить обработку edge cases (пустые сообщения, длинные тексты)
- [x] Проверить и дополнить README.md
- [x] Добавить примеры использования в README
- [x] Финальное тестирование всех сценариев

**Как протестировать:**
- Пройти все сценарии из docs/vision.md раздел "Сценарии работы"
- Проверить работу с несколькими пользователями одновременно
- Проверить корректность логов

---

## 🚀 Спринт 2: RAG-ассистент на базе LangChain

### Итерация 5: Индексация PDF с командами управления

**Цель:** Загрузить PDF-документы, разбить на чанки, создать векторное хранилище и добавить команды управления индексацией

- [x] Добавить зависимости в `pyproject.toml`: langchain, langchain-openai, langchain-community, langchain-core, langchain-text-splitters, pypdf
- [x] Обновить `config.py` - добавить MODEL_QUERY_TRANSFORM, EMBEDDING_MODEL, DATA_DIR
- [x] Создать `src/indexer.py` с функциями:
  - [x] `load_pdf_documents(data_dir)` - загрузка PDF через PyPDFLoader
  - [x] `split_documents(pages)` - разбиение через RecursiveCharacterTextSplitter (chunk_size=500)
  - [x] `create_vector_store(chunks)` - создание InMemoryVectorStore
  - [x] `reindex_all()` - асинхронная функция полной переиндексации
- [x] Создать `src/rag.py` с глобальной переменной `vector_store` и retriever
- [x] Обновить `bot.py` - вызвать индексацию при старте
- [x] Добавить в `handlers.py` команды `/index` и `/index_status`
- [x] Добавить логирование процесса индексации

**Как протестировать:**
- Запустить бота - должна пройти индексация PDF
- Проверить логи индексации
- Выполнить `/index_status` - увидеть количество документов
- Выполнить `/index` - переиндексировать документы

---

### Итерация 6: Полноценный RAG с query transformation и историей

**Цель:** Реализовать полную RAG-цепочку из референсного ноутбука с поддержкой истории диалога и уточняющих вопросов

- [x] Реализовать в `src/rag.py`:
  - [x] `format_chunks(chunks)` - форматирование чанков с метаданными
  - [x] Промпты в отдельных файлах (prompts/conversation_system.txt, prompts/query_transform.txt)
  - [x] conversational_answering_prompt - ChatPromptTemplate для диалога
  - [x] retrieval_query_transform_prompt - промпт для трансформации запроса
  - [x] retrieval_query_transformation_chain - цепочка трансформации
  - [x] rag_query_transform_chain - финальная RAG-цепочка
  - [x] `rag_answer(messages)` - асинхронная функция для получения ответа
- [x] Обновить `handlers.py`:
  - [x] Хранение истории сразу в LangChain messages (HumanMessage, AIMessage, SystemMessage)
  - [x] Вызывать `rag_answer()` для всех сообщений
  - [x] Убрана проверка длины сообщения
- [x] Интегрировать с существующей системой истории диалогов
- [x] Удалить неиспользуемый модуль llm.py

**Как протестировать:**
- Задать вопрос: "Какие условия кредита?" - получить ответ на основе документов
- Диалог с уточнением: "Какие вклады есть?" → "А проценты какие?"
- Вопрос вне контекста: "Какая погода?" - получить "Я не нашел ответа"
- Проверить, что история сохраняется и контекст учитывается

---

### Итерация 7: Финальная полировка и документация

**Цель:** Обработка edge cases, добавление команды /help, логирование в файл, финальная документация

- [x] Обработка ошибок:
  - [x] Валидация наличия PDF-файлов в data/
  - [x] Проверка инициализации векторного хранилища
  - [x] Корректная обработка ошибок индексации с try/except
  - [x] Обработка ошибок при вызове RAG с откатом истории
- [x] Добавить команду `/help` с описанием всех возможностей бота
- [x] Настроить логирование в файл:
  - [x] Добавить FileHandler в logging для записи в файл logs/bot.log
  - [x] Логировать все важные события: старт/стоп, индексация, вопросы, ошибки
- [x] Обновить README.md:
  - [x] Описание RAG-функционала
  - [x] Инструкции по добавлению документов
  - [x] Примеры использования
  - [x] Описание всех команд
  - [x] Примеры конфигурации для OpenRouter и Fireworks
- [x] Улучшить архитектуру:
  - [x] Вынести инициализацию retriever в rag.py
  - [x] Добавить RETRIEVER_K в конфиг

**Как протестировать:**
- Проверить команду `/help`
- Протестировать все edge cases
- Убедиться, что README актуален
- Пройти полный сценарий использования

---

---

## 🚀 Спринт 3: Мониторинг и оценка качества RAG

### Итерация 8: Рефакторинг RAG с отображением источников

**Цель:** Модернизировать RAG цепочку для возврата источников и добавить LangSmith трейсинг

- [x] Обновить `src/rag.py`:
  - [x] Изменить `get_rag_chain()` для возврата dict с `answer` и `documents`
  - [x] Добавить функцию `format_sources(documents)` для форматирования списка источников
  - [x] Обновить `rag_answer()` для работы с новой структурой
- [x] Обновить `src/handlers.py`:
  - [x] Модифицировать обработчик сообщений для работы с `answer` и `documents`
  - [x] Добавить форматирование и отображение источников если `SHOW_SOURCES=true`
  - [x] Форматировать компактно: "📚 Источники: file.pdf (стр. 3, 5)"
- [x] Обновить `src/config.py`:
  - [x] Добавить `SHOW_SOURCES` (default: False)
  - [x] Добавить `LANGSMITH_API_KEY`, `LANGSMITH_TRACING_V2`, `LANGSMITH_PROJECT`, `LANGSMITH_DATASET`
- [x] Обновить `env.example`:
  - [x] Добавить секцию LangSmith configuration
  - [x] Добавить `SHOW_SOURCES=false`
- [x] Добавить зависимость `langsmith` в `pyproject.toml`

**Как протестировать:**
- Запустить бота с `SHOW_SOURCES=false` - источники не показываются
- Установить `SHOW_SOURCES=true` - внизу ответов появляются источники
- Проверить что источники форматируются компактно с группировкой страниц

---

### Итерация 9: Синтез тестовых датасетов

**Цель:** Создать модуль для автоматического синтеза датасетов из документов

- [x] Создать директорию `datasets/`
- [x] Создать `src/dataset_synthesizer.py`:
  - [x] `load_and_sample_documents(data_dir, samples_per_file=2)` - загрузка и выборка чанков
  - [x] `synthesize_qa_pairs(chunks, llm_model)` - генерация QA пар через LLM
  - [x] `load_json_qa_pairs(data_dir, samples_per_file=2)` - загрузка готовых Q&A из JSON
  - [x] `save_dataset(qa_pairs, filepath)` - сохранение в JSON
  - [x] `upload_to_langsmith(dataset_path, dataset_name)` - загрузка с проверкой дубликатов
  - [x] `main()` - CLI интерфейс с аргументом `--upload`
- [x] Обновить `Makefile`:
  - [x] Добавить команду `dataset` для создания датасета
  - [x] Добавить команду `dataset-upload` для загрузки в LangSmith
- [x] Обновить `.gitignore` - игнорировать `datasets/*.json`

**Как протестировать:**
- Выполнить `make dataset` - создается `datasets/06-rag-qa-dataset.json`
- Проверить формат датасета (по 2 QA из PDF + по 2 из JSON)
- Выполнить `make dataset-upload` - датасет загружается в LangSmith
- Повторить `make dataset-upload` - не создается дубликат

---

### Итерация 10: Система оценки качества через RAGAS

**Цель:** Реализовать evaluation RAG системы с метриками RAGAS и интеграцией с LangSmith

- [x] Создать `src/evaluation.py`:
  - [x] `check_dataset_exists(dataset_name)` - проверка через LangSmith API
  - [x] `init_ragas_metrics()` - инициализация метрик (один раз)
  - [x] `evaluate_dataset(dataset_name)` - главная функция evaluation (подход из референса раздел 5)
    - [x] Шаг 1: Запуск эксперимента с blocking=False и сбор данных
    - [x] Шаг 2: RAGAS batch evaluation
    - [x] Шаг 3: Загрузка метрик как feedback в LangSmith
- [x] Инициализация RAGAS метрик (6 штук):
  - [x] Faithfulness
  - [x] ResponseRelevancy (answer_relevancy)
  - [x] AnswerCorrectness
  - [x] AnswerSimilarity
  - [x] ContextRecall
  - [x] ContextPrecision
- [x] Добавить зависимости в `pyproject.toml`: `ragas>=0.2.0`, `datasets>=3.0.0`
- [x] Обновить `src/handlers.py`:
  - [x] Добавить команду `/evaluate_dataset [name]`
  - [x] Показывать прогресс evaluation
  - [x] Отображать результаты метрик с эмодзи и описаниями

**Как протестировать:**
- Убедиться что датасет загружен в LangSmith (через `make dataset-upload`)
- Запустить `/evaluate_dataset` без аргументов - использует LANGSMITH_DATASET из конфига
- Запустить `/evaluate_dataset custom-dataset` - использует указанный датасет
- Проверить вывод метрик: 6 RAGAS метрик с цветовыми индикаторами
- Проверить в LangSmith UI что feedback загружен к runs

---

### Итерация 11: Финальная полировка и документация

**Цель:** Тестирование, обработка ошибок, обновление документации

- [x] Обработка ошибок:
  - [x] Валидация LANGSMITH_API_KEY при использовании evaluation
  - [x] Проверка доступности LangSmith API
  - [x] Обработка ошибок RAGAS (timeout, rate limits)
  - [x] Понятные сообщения пользователю при ошибках
  - [x] Проверка существования датасета перед evaluation
- [x] Обновить `README.md`:
  - [x] Описание режима отображения источников
  - [x] Инструкции по настройке LangSmith
  - [x] Команда `/evaluate_dataset`
  - [x] Команды `make dataset` и `make dataset-upload`
  - [x] Описание RAGAS метрик
  - [x] Обновлена структура проекта
  - [x] Добавлен технологический стек
- [x] Финальное тестирование:
  - [x] Работа RAG с источниками (вкл/выкл)
  - [x] Трейсинг в LangSmith UI
  - [x] Создание датасета
  - [x] Загрузка датасета
  - [x] Evaluation с отображением результатов
  - [x] Feedback в LangSmith
- [x] Логирование:
  - [x] Логировать начало/конец evaluation
  - [x] Логировать количество обработанных примеров
  - [x] Логировать ошибки при evaluation
- [x] Конфигурация:
  - [x] Вынесены RAGAS модели в config (RAGAS_LLM_MODEL, RAGAS_EMBEDDING_MODEL)

**Как протестировать:**
- Пройти полный цикл: создание датасета → загрузка → evaluation
- Проверить все edge cases (нет API ключа, несуществующий датасет, ошибки сети)
- Убедиться что README актуален и содержит все новые функции
- Проверить что логи информативны

---

---

## 🚀 Спринт 4: Advanced Hybrid RAG

### Итерация 12: Конфигурируемые embeddings (OpenAI + HuggingFace)

**Цель:** Добавить поддержку локальных HuggingFace embeddings как альтернативу OpenAI

- [x] Добавить зависимости: `langchain-huggingface`, `sentence-transformers`
- [x] Обновить `config.py`:
  - [x] `EMBEDDING_PROVIDER` (openai/huggingface, default: openai)
  - [x] `HUGGINGFACE_EMBEDDING_MODEL` (default: intfloat/multilingual-e5-base)
  - [x] `HUGGINGFACE_DEVICE` (cpu/cuda/mps, default: cpu)
- [x] Обновить `indexer.py`:
  - [x] `create_embeddings()` - фабрика для создания embeddings по провайдеру
  - [x] Обновить `create_vector_store()` использовать `create_embeddings()`
- [x] Обновить `env.example` - добавить секцию Embeddings Configuration
- [x] Тестирование:
  - [x] С OpenAI embeddings (текущее поведение)
  - [x] С HuggingFace embeddings (локальные)

**Как протестировать:**
- Запустить с `EMBEDDING_PROVIDER=openai` - работает как раньше
- Запустить с `EMBEDDING_PROVIDER=huggingface` - использует локальные embeddings
- Проверить что индексация и поиск работают в обоих режимах

---

### Итерация 13: Hybrid Retrieval (Semantic + BM25)

**Цель:** Реализовать гибридный поиск с комбинацией semantic и BM25

- [x] Добавить зависимость: `rank-bm25`, `langchain-classic`
- [x] Обновить `config.py`:
  - [x] `RETRIEVAL_MODE` (semantic/hybrid/hybrid_reranker, default: semantic)
  - [x] `SEMANTIC_RETRIEVER_K` (default: 10)
  - [x] `BM25_RETRIEVER_K` (default: 10)
  - [x] `ENSEMBLE_SEMANTIC_WEIGHT` (default: 0.5)
  - [x] `ENSEMBLE_BM25_WEIGHT` (default: 0.5)
- [x] Обновить `rag.py`:
  - [x] Глобальная переменная `chunks` для BM25
  - [x] `create_semantic_retriever()` - создание semantic retriever
  - [x] `create_bm25_retriever()` - создание BM25 retriever
  - [x] `create_hybrid_retriever()` - EnsembleRetriever (semantic + BM25)
  - [x] `create_retriever()` - фабрика по режиму (semantic/hybrid)
  - [x] Обновить `initialize_retriever()` использовать фабрику
- [x] Обновить `indexer.py`:
  - [x] `reindex_all()` возвращает (vector_store, chunks) для BM25
- [x] Обновить `bot.py`:
  - [x] Сохранять chunks при индексации в `rag.chunks`
- [x] Обновить `env.example`

**Как протестировать:**
- `RETRIEVAL_MODE=semantic` - работает как раньше
- `RETRIEVAL_MODE=hybrid` - использует Semantic + BM25
- Задать вопрос с точным термином - hybrid должен лучше найти
- Проверить `/index_status` показывает режим

---

### Итерация 14: Cross-Encoder Reranking

**Цель:** Добавить cross-encoder для переранжирования результатов hybrid retrieval

- [x] Зависимость `sentence-transformers` уже есть (из итерации 12)
- [x] Обновить `config.py`:
  - [x] `CROSS_ENCODER_MODEL` (default: cross-encoder/mmarco-mMiniLMv2-L12-H384-v1)
  - [x] `RERANKER_TOP_K` (default: 3)
- [x] Обновить `rag.py`:
  - [x] Глобальная переменная `cross_encoder` (lazy loading)
  - [x] `get_cross_encoder()` - ленивая инициализация cross-encoder
  - [x] `rerank_documents(query, documents, top_k)` - переранжирование
  - [x] Обновить `create_retriever()` для режима hybrid_reranker
- [x] Обновить `get_rag_chain()`:
  - [x] Для hybrid_reranker: ensemble_docs → rerank → documents → answer
  - [x] LCEL цепочка с промежуточным шагом reranking
- [x] Обновить `env.example`

**Как протестировать:**
- `RETRIEVAL_MODE=hybrid_reranker` - включает reranking
- Сравнить ответы между hybrid и hybrid_reranker на одном вопросе
- Проверить что возвращается RERANKER_TOP_K документов
- Логи должны показывать загрузку cross-encoder при первом использовании

---

### Итерация 15: Финальная полировка и документация

**Цель:** Тестирование всех режимов, обработка ошибок, обновление документации

- [x] Обработка ошибок:
  - [x] Валидация RETRIEVAL_MODE (только разрешенные значения)
  - [x] Валидация EMBEDDING_PROVIDER
  - [x] Обработка ошибок загрузки моделей HuggingFace
  - [x] Обработка ошибок инициализации cross-encoder
  - [x] Информативные логи при переключении режимов
- [x] Улучшения команд:
  - [x] `/index_status` показывает: retrieval_mode, embedding_provider, модели
  - [x] `/help` обновить с описанием новых режимов
- [x] Обновить `README.md`:
  - [x] Описание трех режимов retrieval
  - [x] Таблица с рекомендациями когда использовать каждый режим
  - [x] Инструкции по настройке HuggingFace embeddings
  - [x] Примеры конфигурации для каждого режима
  - [x] Требования к ресурсам (CPU/GPU, память)
  - [x] Обновленный раздел Configuration
- [x] Финальное тестирование:
  - [x] Все три режима retrieval
  - [x] Оба провайдера embeddings (OpenAI, HuggingFace)
  - [x] Переключение между режимами
  - [x] Evaluation на датасете для сравнения метрик
- [x] Логирование:
  - [x] При старте логировать: режим, провайдер, модели
  - [x] Логи инициализации каждого компонента
- [x] Дополнительно:
  - [x] Добавлены метрики ContextRecall и ContextPrecision (всего 6 RAGAS метрик)
  - [x] Исправлен ResponseRelevancy (был AnswerRelevancy)
  - [x] Причесан env.example с подробными комментариями

**Как протестировать:**
- Пройти полный цикл для каждой комбинации:
  - OpenAI + semantic
  - OpenAI + hybrid
  - OpenAI + hybrid_reranker
  - HuggingFace + semantic
  - HuggingFace + hybrid
  - HuggingFace + hybrid_reranker
- Запустить evaluation для сравнения метрик
- Проверить все edge cases
- Убедиться что README актуален

---

---

## 🏠 Домашние шаги (ДЗ-6)

### ДЗ-6: Эксперимент 1 — Semantic Baseline

**Цель:** Получить базовые метрики RAGAS в режиме `semantic`

- [ ] Убедиться что `RETRIEVAL_MODE=semantic` в `.env`
- [ ] Убедиться что датасет `06-rag-qa-dataset` загружен в LangSmith
- [ ] Запустить `/evaluate_dataset` и зафиксировать результаты

---

### ДЗ-6: Эксперимент 2 — Hybrid Retrieval

**Цель:** Сравнить метрики RAGAS при `RETRIEVAL_MODE=hybrid`

- [ ] Переключить `RETRIEVAL_MODE=hybrid` в `.env`
- [ ] Перезапустить бота
- [ ] Запустить `/evaluate_dataset` и сравнить с baseline

---

### ДЗ-6: Эксперимент 3 — Hybrid + Reranker

**Цель:** Сравнить метрики RAGAS при `RETRIEVAL_MODE=hybrid_reranker`

- [ ] Переключить `RETRIEVAL_MODE=hybrid_reranker` в `.env`
- [ ] Перезапустить бота
- [ ] Запустить `/evaluate_dataset` и сравнить со всеми предыдущими

---

### ДЗ-6: report.md

**Цель:** Задокументировать все эксперименты и выводы

- [ ] Создать `report.md` в корне проекта
- [ ] Описать конфигурации всех экспериментов
- [ ] Добавить таблицу с метриками RAGAS для каждого эксперимента
- [ ] Сформулировать вывод: какая конфигурация оказалась лучшей и почему

---

## 📝 Заметки

После завершения каждой итерации:
1. Обновить статус в таблице прогресса
2. Протестировать бота
3. Закоммитить изменения
4. Переходить к следующей итерации только после успешного теста

