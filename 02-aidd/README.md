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

## Docker

Требования: **Docker**, **make** (или эквивалентные команды `docker`).

1. Подготовьте `.env` в корне репозитория (как для локального запуска). Файл в образ **не** вкладывается.

2. Сборка образа:

   ```bash
   make docker-build
   ```

   Имя образа по умолчанию: `aidd-bot`. Переопределение: `make docker-build IMAGE_NAME=my-bot`.

3. Запуск (передаёт переменные из `.env`):

   ```bash
   make docker-run
   ```

   Эквивалент: `docker run --rm --env-file .env aidd-bot`.
