# MVP Telegram-бот + LLM

Стек и границы MVP — [docs/vision.md](docs/vision.md).

## Локальный запуск

Требования: **Python 3.12**, **uv**, **make** (опционально).

1. Установка зависимостей:

   ```bash
   uv sync
   ```

   или `make install`.

2. Переменные окружения: скопируйте [.env.example](.env.example) в `.env` и заполните значения (см. § «Конфигурация» в vision).

3. Запуск бота:

   ```bash
   uv run python -m aidd
   ```

   или `make run`.
