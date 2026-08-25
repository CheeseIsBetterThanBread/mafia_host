PYTHON ?= python3
VENV ?= .venv
ENV_FILE ?= .env
VENV_PYTHON := $(VENV)/bin/python
VENV_PIP := $(VENV)/bin/pip
DEPS_STAMP := $(VENV)/.deps-installed

.DEFAULT_GOAL := help

.PHONY: help format check-format setup install run test docker-build docker-up docker-down

help:
	@printf "Доступные команды:\\n"
	@printf "  make setup        - создать .env при отсутствии и установить зависимости\\n"
	@printf "  make run          - запустить бота локально из .venv\\n"
	@printf "  make test         - запустить unit-тесты\\n"
	@printf "  make docker-build - собрать Docker-образ\\n"
	@printf "  make docker-up    - запустить через docker compose\\n"
	@printf "  make docker-down  - остановить docker compose\\n"

$(VENV_PYTHON):
	$(PYTHON) -m venv $(VENV)

$(DEPS_STAMP): requirements.txt | $(VENV_PYTHON)
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -r requirements.txt
	@touch $(DEPS_STAMP)

format: $(DEPS_STAMP)
	$(VENV_PYTHON) -m black .

check-format: $(DEPS_STAMP)
	$(VENV_PYTHON) -m black --check .

setup: $(DEPS_STAMP)
	@if [ ! -f "$(ENV_FILE)" ]; then cp .env.example "$(ENV_FILE)"; fi
	@printf "Проверьте $(ENV_FILE) и заполните реальные значения перед запуском.\\n"

install: $(DEPS_STAMP)

run: $(DEPS_STAMP)
	@if [ ! -f "$(ENV_FILE)" ]; then printf "Создайте $(ENV_FILE) из .env.example\\n" >&2; exit 1; fi
	$(VENV_PYTHON) bot.py

test: | $(VENV_PYTHON)
	$(VENV_PYTHON) -m pytest tests/ -v

coverage: | $(VENV_PYTHON)
    $(VENV_PYTHON) -m pytest tests/ --cov=. --cov-report=html

docker-build:
	docker build -t mafia-bot .

docker-up:
	@if [ ! -f "$(ENV_FILE)" ]; then printf "Создайте $(ENV_FILE) из .env.example\\n" >&2; exit 1; fi
	docker compose up --build -d

docker-down:
	docker compose down