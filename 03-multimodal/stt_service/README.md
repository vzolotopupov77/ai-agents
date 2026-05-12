# STT-сервис GigaAM-v3

Отдельный процесс для транскрибации голосовых сообщений (развёртывается на GPU-сервере).

## Требования

- Python 3.12+
- `ffmpeg` в PATH (`sudo apt install ffmpeg`)
- NVIDIA GPU + PyTorch с CUDA

## Установка

Модели **v3** есть только в репозитории GitHub; пакет с PyPI их не содержит.

```bash
cd stt_service
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip wheel

pip install torch==2.5.1+cu124 torchaudio==2.5.1+cu124 \
  --index-url https://download.pytorch.org/whl/cu124

pip install -r requirements.txt

# Если после этого torch снова без CUDA — повторите установку torch/torchaudio с индексом cu124 (см. комментарий в requirements.txt).
```

## Запуск

```bash
chmod +x start.sh
./start.sh
```

По умолчанию слушает `0.0.0.0:8765`.

Первый запуск скачивает веса модели с Hugging Face (~400+ MB).

## API

- `GET /health` → `{"status":"ok"}`
- `POST /transcribe` — multipart поле `file` с аудио → `{"text":"..."}`

## Ограничение GigaAM

Функция `.transcribe` рассчитана на фрагменты **до ~25 секунд**. Длинные голосовые — см. longform в документации GigaAM (не входит в MVP).
