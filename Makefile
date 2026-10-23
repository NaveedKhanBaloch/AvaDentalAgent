PYTHON ?= python3
PIP ?= pip

.PHONY: install api-install web-install up down test api-test web-test lint format

install: api-install web-install

api-install:
	cd apps/api && python3 -m venv .venv && . .venv/bin/activate && pip install -U pip && pip install -e .[dev]

web-install:
	cd apps/web && npm install

up:
	docker compose up --build

down:
	docker compose down

api-test:
	cd apps/api && . .venv/bin/activate && pytest -q

web-test:
	cd apps/web && npm run test:e2e

lint:
	cd apps/api && . .venv/bin/activate && ruff check . && black --check .
	cd apps/web && npm run lint

format:
	cd apps/api && . .venv/bin/activate && black .
	cd apps/web && npm run format

seed:
	cd apps/api && . .venv/bin/activate && python -m app.seed
