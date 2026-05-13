# Отчёт по домашнему заданию модуля 4: RAG-ассистент на LangChain

**Проект:** RAG-ассистент Сбербанка (Telegram-бот)  
**Вариант:** Лайт  
**Дата:** 13.05.2026

---

## Описание проекта

Telegram-бот, отвечающий на вопросы по банковским документам с помощью RAG (Retrieval-Augmented Generation). Бот индексирует PDF-документы Сбербанка (условия потребительского кредита, условия по вкладам) и JSON FAQ по картам, после чего отвечает на вопросы пользователей, используя найденный контекст.

---

## Реализованные возможности

- [x] Индексация PDF-документов при старте (`PyPDFLoader` + `RecursiveCharacterTextSplitter`)
- [x] Векторное хранилище в памяти (`InMemoryVectorStore`)
- [x] RAG-цепочка с query transformation (учёт истории диалога при формировании поискового запроса)
- [x] Контекстный диалог — история в формате LangChain Messages
- [x] Команды бота: `/start`, `/help`, `/index`, `/index_status`
- [x] Логирование в консоль и файл `logs/bot.log`
- [x] **HW-1:** эксперименты с параметрами чанкинга (`chunk_size`, `chunk_overlap`)
- [x] **HW-2:** загрузка JSON FAQ (`sberbank_help_documents.json`) и объединённая индексация PDF + JSON
- [x] **HW-3:** сравнение трёх моделей эмбеддингов OpenRouter, автоматизированный скрипт сравнения

---

## Технологический стек

| Компонент | Технология |
|-----------|-----------|
| Язык | Python 3.11+ |
| Управление зависимостями | uv |
| Telegram Bot API | aiogram 3.x |
| RAG-фреймворк | LangChain (langchain, langchain-openai, langchain-community) |
| LLM-провайдер | OpenRouter (OpenAI-совместимый API) |
| Загрузка PDF | PyPDF |
| Векторное хранилище | InMemoryVectorStore (LangChain) |
| Конфигурация | python-dotenv |

### Используемые модели

| Назначение | Модель |
|-----------|--------|
| Генерация ответов (LLM) | `openai/gpt-oss-20b:free` |
| Query Transformation | `openai/gpt-oss-20b:free` |
| Эмбеддинги (production) | `openai/text-embedding-3-large` |

---

## HW-1: Эксперименты с чанкингом PDF

**Сплиттер:** `RecursiveCharacterTextSplitter` с сепараторами `["\n\n\n", "\n\n", "\n", ". ", " ", ""]`

**Тестовые вопросы:**
- Q1: «Какие условия потребительского кредита?»
- Q2: «Какие проценты по вкладам?»

### Результаты

| Параметры | Чанков | Q1 (кредит) | Q2 (вклады) |
|-----------|--------|------------|------------|
| `chunk_size=1500, chunk_overlap=150` | 132 | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| `chunk_size=800, chunk_overlap=100` | 246 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| `chunk_size=500, chunk_overlap=50` | 377 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

### Наблюдения

**chunk_size=1500:** широкий контекст, но релевантный фрагмент «тонет» в большом куске — ответы полные, но обобщённые, без конкретных продуктов и цифр.

**chunk_size=800 ← выбранный оптимум:** лучший баланс. Q1 — 5 структурированных пунктов с упоминанием закона № 353-ФЗ, ПСК, сторон; Q2 — перечислены конкретные продукты («Лучший % Лидер», «Лучший % Премьер», «Сбер Рядом» и др.) со ссылкой на страницы документа.

**chunk_size=500:** хорошо для тарифных списков (Q2 — 8 наименований вкладов), но дробит связные нарративные разделы: Q1 деградировал до 3 пунктов вместо 6.

### Выводы

- Оптимум: **`chunk_size=800, chunk_overlap=100`** (overlap ~12% от размера).
- Overlap 10% (50 при chunk=500) недостаточен — предложения на границах теряются.
- Для смешанного корпуса (нарративные PDF + тарифные таблицы) размер 800 даёт лучшее среднее качество.

---

## HW-2: JSON-датасет (вопросы про карты)

### Источник данных

Файл `data/sberbank_help_documents.json` — 212 записей Q&A по дебетовым и кредитным картам Сбербанка.

**Структура записи:**
```json
{
  "url": "https://www.sberbank.ru/...",
  "question": "Как заказать карту?",
  "answer": "...",
  "category": "Вопросы о дебетовых картах",
  "type": "individual_qa",
  "full_text": "Категория: ...\n\nВопрос: ...\n\nОтвет: ..."
}
```

### Реализация

Новый модуль `src/indexer_with_json.py` (оригинальный `indexer.py` не изменялся):

```python
def load_json_documents(data_dir: str) -> list:
    json_path = Path(data_dir) / "sberbank_help_documents.json"
    with open(json_path, encoding="utf-8") as f:
        records = json.load(f)
    return [
        Document(
            page_content=record["full_text"],      # поле full_text → page_content
            metadata={
                "source":   record.get("url", ""),
                "question": record.get("question", ""),
                "category": record.get("category", ""),
            },
        )
        for record in records
    ]
```

- Использован `json.load` (стандартная библиотека) — зависимость `jq` не нужна.
- Каждая Q&A запись → один `Document`; `full_text` содержит категорию, вопрос и ответ с разметкой `\n\n`.
- После загрузки записи прогоняются через тот же `split_documents()`, что и PDF-чанки.

**`reindex_all()` в `indexer_with_json.py`** объединяет оба источника:

```python
all_chunks = []
all_chunks.extend(split_documents(load_pdf_documents(config.DATA_DIR)))   # PDF: ~332 чанка
all_chunks.extend(split_documents(load_json_documents(config.DATA_DIR)))  # JSON: ~212 чанка
vector_store = create_vector_store(all_chunks)  # итого ~544 чанка
```

**Подключение к боту:** `import indexer_with_json as indexer` в `bot.py` и `handlers.py` (команда `/index`).

---

## HW-3: Сравнение моделей эмбеддингов

Эксперимент проводился скриптом `scripts/hw3_compare_embeddings.py`: один прогон строит `InMemoryVectorStore` трижды с разными моделями и выполняет `similarity_search` (top-3) по тем же вопросам. Индекс одинаков во всех трёх случаях (~544 чанка, PDF + JSON).

**Тестовые вопросы:**
- Q1: «Какие условия потребительского кредита?»
- Q2: «Какие проценты по вкладам?»
- Q3: «Как заказать карту?»

### Результаты retrieval

| Модель | Цена (OpenRouter) | Q1 (кредит) | Q2 (вклады) | Q3 (карты) |
|--------|-------------------|------------|------------|-----------|
| `openai/text-embedding-3-large` | $0.13/M | ✅ PDF ОУ кредита | ✅ PDF тарифы вкладов | ⚠️ смежный JSON по картам |
| `baai/bge-m3` | $0.01/M | ❌ FAQ кредитных карт (JSON) | ❌ FAQ карт, не PDF вкладов | ✅ JSON дебетовые карты |
| `qwen/qwen3-embedding-8b` | $0.01/M | ❌ FAQ карт (JSON) | ❌ JSON по картам | ⚠️ смесь ccards FAQ |

### Наблюдения

- **Baseline (`text-embedding-3-large`)** корректно разделяет тематики: PDF-вопросы находят PDF-источники, JSON FAQ используется для вопросов про карты. Цена: $0.13/M токенов.
- **`baai/bge-m3`** и **`qwen/qwen3-embedding-8b`** на смешанном корпусе (длинные PDF + короткий JSON FAQ) смешивают тематики — по словам «кредит» / «проценты» в топ-3 попадают JSON-записи про кредитные карты вместо PDF с общими условиями. Оба стоят $0.01/M — в **13 раз дешевле** baseline.

### Вывод

Для текущего бота без дополнительных mitigations рекомендуется **`openai/text-embedding-3-large`**. Переход на дешёвые multilingual-модели оправдан при добавлении rerankера или фильтрации по метаданным (`source`/`category`).

---

## Ссылки

- [README.md](README.md) — запуск, конфигурация, схемы потоков данных
- [docs/tasklist.md](docs/tasklist.md) — план разработки и детальные результаты экспериментов
- [docs/vision.md](docs/vision.md) — техническое видение и архитектура проекта

---

## Структура репозитория

```
src/
├── bot.py                  — точка входа
├── handlers.py             — обработчики команд и сообщений
├── rag.py                  — RAG-цепочки, query transformation
├── indexer.py              — базовая индексация PDF
├── indexer_with_json.py    — объединённая индексация PDF + JSON (активный)
└── config.py               — конфигурация из .env
data/
├── ouk_potrebitelskiy_kredit_lph.pdf
├── usl_r_vkladov.pdf
└── sberbank_help_documents.json   (212 Q&A)
scripts/
└── hw3_compare_embeddings.py      (HW-3: сравнение 3 моделей)
prompts/
├── conversation_system.txt
└── query_transform.txt
```
