.PHONY: setup run clean help

help:
	@echo "Доступные команды:"
	@echo "  make setup  - Установить зависимости через uv"
	@echo "  make run    - Запустить CLI бот"
	@echo "  make clean  - Очистить временные файлы"

setup:
	@echo "Установка зависимостей..."
	uv sync
	@echo "✓ Зависимости установлены"
	@echo ""
	@echo "Не забудьте создать .env файл на основе .env.example"
	@echo "  cp .env.example .env"
	@echo "  # затем отредактируйте .env и добавьте ваш API ключ"

# Проверка .env без bash (cmd.exe на Windows ломается на `!` в `[ ! -f ... ]`).
ifneq ($(wildcard .env),)
run:
	uv run python src/bot.py
else
run:
	@echo "❌ Файл .env не найден!"
	@echo "Скопируйте .env.example в .env и добавьте ваш API ключ:"
	@echo "  copy .env.example .env   (PowerShell/cmd)"
	@echo "  cp .env.example .env     (Git Bash)"
	@exit 1
endif

clean:
	@echo "Очистка временных файлов..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
	@echo "✓ Очистка завершена"
