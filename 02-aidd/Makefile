IMAGE_NAME ?= aidd-bot

.PHONY: install run docker-build docker-run

install:
	uv sync

run:
	uv run python -m aidd

docker-build:
	docker build -t $(IMAGE_NAME) .

docker-run:
	docker run --rm --env-file .env $(IMAGE_NAME)
