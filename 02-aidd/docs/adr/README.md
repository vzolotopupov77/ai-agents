# Архитектурные решения (ADR)

Записи нумеруются последовательно: `NNNN-краткое-название.md`.

| № | Файл | Суть |
|---|------|------|
| 0001 | [0001-in-memory-dialogue-storage.md](./0001-in-memory-dialogue-storage.md) | История диалогов только в памяти процесса, без БД |
| 0002 | [0002-telegram-long-polling.md](./0002-telegram-long-polling.md) | Входящие обновления через long polling, без webhook |
| 0003 | [0003-openrouter-via-openai-sdk.md](./0003-openrouter-via-openai-sdk.md) | Доступ к моделям через OpenRouter официальным клиентом `openai` |
| 0004 | [0004-telegram-decoupled-from-llm-layer.md](./0004-telegram-decoupled-from-llm-layer.md) | Слой LLM не зависит от aiogram; граница — список сообщений и текст ответа |

Общее техническое видение: [../vision.md](../vision.md).
