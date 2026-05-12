# Telegram-бот: персональный финансовый советник + LLM

Идея и цели — [docs/idea.md](docs/idea.md). Стек, модель данных и конфигурация — [docs/vision.md](docs/vision.md). План и статус итераций — [docs/tasklist.md](docs/tasklist.md).

Бот ведёт **диалог** с моделью через **OpenAI-совместимый** клиент (OpenRouter, Ollama и др.; задаётся `LLM_BASE_URL` и `LLM_API_KEY` в `.env`) и по плану развития — **учёт доходов и расходов** в памяти процесса. Роль и тон задаются **`SYSTEM_PROMPT`** в `.env`; пример переменных — [.env.example](.env.example).

## Возможности сейчас

- **`/start`** — приветствие финансового советника (без вызова LLM).
- **`/report`** — текстовый отчёт по накопленным операциям: баланс, доходы/расходы, разбивка по категориям и типам (**без** вызова LLM). При пустом учёте сообщает, что операций нет.
- **Текстовые сообщения** — извлечение транзакций и совет в одном вызове LLM (structured output); при успешном разборе — запись в учёт и подтверждение. История диалога — с лимитом `MAX_HISTORY_MESSAGES`.
- **Фото чеков** — загрузка снимка, вызов VLM (`VLM_MODEL`), тот же формат JSON; запись в учёт или ответ без записи.
- **Голосовые сообщения** — при заданном `STT_BASE_URL` вызов STT-микросервиса GigaAM-v3 ([stt_service/README.md](stt_service/README.md)), далее тот же сценарий, что и для текста. Без URL — ответ «не поддерживаются».

Данные учёта и история чата **только в памяти**; перезапуск процесса всё обнуляет.

## Локальный запуск

Требования: **Python 3.12**, **uv**, **make** (опционально).

1. Установка зависимостей:

   ```bash
   uv sync
   ```

   или `make install`.

2. Переменные окружения: скопируйте [.env.example](.env.example) в `.env` и заполните значения (подробнее в vision, раздел «Конфигурация»). Опционально: `STT_BASE_URL` — URL FastAPI GigaAM (см. [stt_service/README.md](stt_service/README.md)).

3. Запуск бота:

   ```bash
   uv run python -m aidd
   ```

   или `make run`.

## Ответы в Telegram

- Один фрагмент текста не длиннее **4096** символов (лимит API Telegram); более длинный ответ модели **режется на несколько сообщений**.
- Включён **`parse_mode=HTML`**: типичная разметка из ответа модели (`#` заголовки, `**жирный**`, `*курсив*`, ссылки `[подпись](https://…)`, строки с `>`, таблицы `|…|`) преобразуется в читаемый вид; теги `<br>` из ответа модели заменяются переносами строк. Если Telegram отклонит разметку, отправляется **запасной вариант** без HTML.
- Отчёт **`/report`** отправляется обычным текстом без этой конвертации.
- Реализация — в [`src/aidd/handlers.py`](src/aidd/handlers.py).

## GPU-сервер (195.209.210.184)

Сервер используется для Ollama (LLM/VLM) и GigaAM-v3 STT-сервиса. Оба процесса должны быть запущены перед стартом бота.

### Требования

- SSH-ключ: `~/.ssh/zva-test-server-084115-vzolotoy.pem`
- Пользователь: `ubuntu`

### Проверка состояния

```bash
ssh -i ~/.ssh/zva-test-server-084115-vzolotoy.pem ubuntu@195.209.210.184 \
  'systemctl is-active ollama && ollama list && curl -s localhost:8765/health && nvidia-smi --query-gpu=name,memory.used,utilization.gpu --format=csv,noheader'
```

### Управление Ollama

Ollama запущена как **systemd-сервис** и стартует автоматически при перезагрузке ВМ.

```bash
# Статус
ssh ... 'systemctl status ollama'

# Рестарт
ssh ... 'sudo systemctl restart ollama'

# Список загруженных моделей
ssh ... 'ollama list'

# Загрузить дополнительную модель
ssh ... 'ollama pull <model>'
```

API доступен публично: `http://195.209.210.184:11434/v1` (OpenAI-совместимый).

### Управление STT-сервисом

STT-сервис **не управляется systemd** — запущен через `nohup`. При перезагрузке ВМ нужно запустить вручную.

```bash
# Проверка
curl http://195.209.210.184:8765/health

# Рестарт (если упал или после обновления кода)
ssh -i ~/.ssh/zva-test-server-084115-vzolotoy.pem ubuntu@195.209.210.184 \
  'pkill -f "uvicorn main:app" || true; cd ~/stt_service && nohup .venv/bin/uvicorn main:app --host 0.0.0.0 --port 8765 >> ~/stt_service/stt.log 2>&1 &'

# Просмотр логов
ssh ... 'tail -f ~/stt_service/stt.log'
```

> **Первый старт** после перезагрузки ВМ занимает ~30–60 секунд: GigaAM-v3 загружает веса (~650 MB) в VRAM.

### Обновление кода STT-сервиса

```bash
# 1. Скопировать изменённые файлы
scp -i ~/.ssh/zva-test-server-084115-vzolotoy.pem stt_service/*.py ubuntu@195.209.210.184:~/stt_service/

# 2. Перезапустить сервис (команда выше)
```

### Переменные окружения бота

Для подключения бота к сервисам на ВМ укажите в `.env`:

```dotenv
LLM_BASE_URL=http://195.209.210.184:11434/v1
VLM_BASE_URL=http://195.209.210.184:11434/v1
STT_BASE_URL=http://195.209.210.184:8765
```

### Подробности

- Настройка Ollama, модели, CUDA — [stt_service/README.md](stt_service/README.md)
- Архитектурное решение — [docs/adr/0006-stt-gigaam-v3-microservice.md](docs/adr/0006-stt-gigaam-v3-microservice.md)

## Docker

Требования: **Docker**, **make** (или эквивалентные команды `docker`).

1. Подготовьте `.env` в корне каталога `03-multimodal` (как для локального запуска). Файл в образ **не** вкладывается.

2. Сборка образа (из каталога `03-multimodal`):

   ```bash
   make docker-build
   ```

   Имя образа по умолчанию: `aidd-bot`. Переопределение: `make docker-build IMAGE_NAME=my-bot`.

3. Запуск (передаёт переменные из `.env`):

   ```bash
   make docker-run
   ```

   Эквивалент: `docker run --rm --env-file .env aidd-bot`.
