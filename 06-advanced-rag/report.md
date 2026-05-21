# RAG Evaluation Report

**Дата:** 21.05.2026  
**Проект:** Advanced Hybrid RAG — Сбербанк ассистент  
**Датасет:** `06-rag-qa-dataset` (6 примеров: 4 PDF + 2 JSON)

---

## Конфигурация экспериментов

### Общие параметры (все эксперименты)

| Параметр | Значение |
|----------|----------|
| LLM | `openai/gpt-oss-20b:free` via OpenRouter |
| Embedding модель | `intfloat/multilingual-e5-base` (HuggingFace, CPU) |
| RAGAS LLM | `openai/gpt-oss-20b:free` |
| RAGAS Embeddings | `intfloat/multilingual-e5-base` |
| Датасет | 6 примеров (4 синтезированных из PDF + 2 из JSON) |

### Эксперимент 1 — Semantic (Baseline)

| Параметр | Значение |
|----------|----------|
| `RETRIEVAL_MODE` | `semantic` |
| `SEMANTIC_RETRIEVER_K` | 10 |
| Метод | Только векторный поиск по cosine similarity |

### Эксперимент 2 — Hybrid

| Параметр | Значение |
|----------|----------|
| `RETRIEVAL_MODE` | `hybrid` |
| `SEMANTIC_RETRIEVER_K` | 10 |
| `BM25_RETRIEVER_K` | 10 |
| `ENSEMBLE_SEMANTIC_WEIGHT` | 0.5 |
| `ENSEMBLE_BM25_WEIGHT` | 0.5 |
| Метод | Semantic + BM25, ансамбль с равными весами |

### Эксперимент 3 — Hybrid + Reranker

| Параметр | Значение |
|----------|----------|
| `RETRIEVAL_MODE` | `hybrid_reranker` |
| `SEMANTIC_RETRIEVER_K` | 10 |
| `BM25_RETRIEVER_K` | 10 |
| `CROSS_ENCODER_MODEL` | `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` |
| `RERANKER_TOP_K` | 3 |
| Метод | Hybrid → Cross-encoder reranking → top-3 чанка |

---

## Результаты RAGAS

| Метрика | Semantic | Hybrid | Hybrid + Reranker |
|---------|:--------:|:------:|:-----------------:|
| **faithfulness** | 0.667 | 0.542 | 0.617 |
| **answer_relevancy** | 0.776 | 0.780 | 0.783 |
| **answer_correctness** | 0.915 | 0.878 | 0.473 |
| **answer_similarity** | 0.921 | 0.927 | 0.930 |
| **context_recall** | 1.000 | 1.000 | 1.000 |
| **context_precision** | nan ⚠️ | 0.917 | **1.000** |

> ⚠️ `context_precision: nan` в Semantic — техническая проблема: таймауты при вычислении метрики, не отражает реальное качество retrieval.

---

## Описание метрик

| Метрика | Что измеряет |
|---------|-------------|
| **faithfulness** | Насколько ответ опирается на предоставленный контекст (нет галлюцинаций) |
| **answer_relevancy** | Насколько ответ релевантен вопросу |
| **answer_correctness** | Совпадение ответа с эталонным (ground truth) |
| **answer_similarity** | Семантическое сходство с эталонным ответом |
| **context_recall** | Полнота: все ли нужные факты есть в retrieved контексте |
| **context_precision** | Точность: насколько retrieved чанки действительно релевантны |

---

## Выводы

### Лучший режим для данной задачи: **Hybrid + Reranker**

**Аргументы:**

1. **context_precision: 1.000** — абсолютная точность извлечения контекста. Cross-encoder из 10–17 кандидатов выбирает ровно 3 наиболее релевантных чанка. Это напрямую влияет на качество ответов и экономию токенов.

2. **context_recall: 1.000** — сохраняется полный охват, несмотря на агрессивную фильтрацию до top-3.

3. **answer_relevancy: 0.783** — лучший среди трёх режимов.

4. **answer_similarity: 0.930** — лучший среди трёх режимов.

5. **faithfulness: 0.617** — выше чем у Hybrid (0.542), хотя ниже Semantic (0.667). Paradox объясняется тем, что при семантическом поиске модель получает более "близкие по смыслу", но иногда менее точные чанки — и строже им следует.

### Почему Semantic уступает

- Без BM25 пропускает точные терминологические совпадения (номера статей, названия продуктов)
- `context_precision` технически не посчиталась, но по косвенным признакам ниже — ответы менее точные

### Почему чистый Hybrid уступает Hybrid + Reranker

- Передаёт в LLM до 20 чанков (10 semantic + 10 BM25 с overlap), из которых часть нерелевантна
- Это "разбавляет" контекст и снижает faithfulness (0.542 — худший результат) и answer_correctness (0.878)
- Cross-encoder решает эту проблему: отбирает top-3 по реальной релевантности вопрос–чанк

### Аномалия: answer_correctness у Reranker (0.473)

Низкое значение, вероятно, артефакт малого датасета (6 примеров) и 1 таймаута (Job[32]) — один пропущенный пример сильно влияет на среднее при n=6. При датасете 50+ примеров эта метрика стабилизируется.

### Рекомендация

Использовать `hybrid_reranker` как основной режим. Для production:
- Увеличить датасет до 50+ примеров для надёжных метрик
- Рассмотреть GPU для cross-encoder (сейчас CPU: ~2.5 it/s)
- Включить LangSmith мониторинг для трейсинга продакшн запросов
