# ai-agents

Домашние работы по курсу **«AI-driven разработка ИИ-агентов»**.

Репозиторий курса: [aidialogs/llmstart-ai-agents](https://github.com/aidialogs/llmstart-ai-agents).

**Участник:** *Золотопупов Владимир*

## Модули курса


| Модуль | Название                                 | Статус | Реализованный бот |
| ------ | ---------------------------------------- | ------ | ----------------- |
| M01    | Основы LLM и стандартные API             | ✅     | CLI-бот (OpenRouter), [`01_llm_api`](01_llm_api/) |
| M02    | AI-driven разработка с Cursor            | ✅     | Telegram: карьерный коуч, [`02-aidd`](02-aidd/) |
| M03    | Мультимодальность и локальный запуск LLM | ✅     | Telegram: финансовый советник, фото/голос, [`03-multimodal`](03-multimodal/) |
| M04    | RAG с LangChain: от теории к практике    | ✅     | Telegram: RAG-ассистент Сбербанка (PDF + JSON, Query Transformation), [`04-rag-langchain`](04-rag-langchain/) |
| M05    | Мониторинг и оценка качества RAG-систем  | ✅     | Telegram: RAG + LangSmith трейсинг + RAGAS evaluation (6 метрик), [`05-monitoring-qa`](05-monitoring-qa/) |
| M06    | Advanced RAG                             | ✅     | Telegram: Advanced Hybrid RAG (Semantic / Hybrid / Hybrid+Reranker), [`06-advanced-rag`](06-advanced-rag/) |
| M07    | Агенты с LangChain и LangGraph           | ⬜     | — |
| M08    | Model Context Protocol (MCP)             | ⬜     | — |
| M09    | Безопасность агентных систем             | ⬜     | — |
| M10    | Оценка качества агентов                  | ⬜     | — |
| M11    | Мультиагентные системы                   | ⬜     | — |


Условные обозначения: ✅ выполнено · 🔄 в работе · ⬜ не начато.

## Структура репозитория

```text
.
├── README.md
├── 01_llm_api/       # M01 — CLI-бот, OpenRouter / OpenAI SDK
├── 02-aidd/          # M02 — Telegram + LLM (AI-driven, Cursor)
├── 03-multimodal/    # M03 — мультимодальность, VLM/STT, локальные модели
├── 04-rag-langchain/ # M04 — Telegram RAG-ассистент (LangChain, PDF+JSON)
├── 05-monitoring-qa/ # M05 — RAG + LangSmith мониторинг + RAGAS evaluation
├── 06-advanced-rag/  # M06 — Advanced Hybrid RAG (BM25 + Cross-encoder Reranker)
└── …                 # следующие модули — по мере прохождения
```

Детали запуска и условия заданий — в `README.md` каждой папки и в репозитории курса.

## Как запускать

Общий минимум: **Python 3.12**, **uv**, в каталоге модуля — `uv sync`, копирование `.env.example` → `.env`, далее команды из README модуля (`make setup` / `make run`, `uv run python -m aidd`, Docker — где описано).
