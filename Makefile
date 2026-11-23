# 1heavy — tareas de desarrollo. `make help` para ver todas.
SHELL := /bin/bash
API   := apps/api
WEB   := apps/web
PY    := $(API)/.venv/bin
COMPOSE := docker compose -f infra/docker-compose.yml --env-file infra/.env

.DEFAULT_GOAL := help
.PHONY: help setup env up up-deps down logs dev-api dev-web test test-api test-web lint fmt typecheck build ci clean

help: ## Lista los comandos disponibles
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

env: ## Crea infra/.env y apps/api/.env desde los ejemplos (no sobrescribe)
	@test -f infra/.env || cp infra/.env.example infra/.env
	@test -f $(API)/.env || cp $(API)/.env.example $(API)/.env

setup: env ## Instala dependencias de API (venv py3.12) y web, y hooks de pre-commit
	test -d $(API)/.venv || python3.12 -m venv $(API)/.venv
	$(PY)/pip install -q --upgrade pip
	$(PY)/pip install -q -e "$(API)[dev]"
	cd $(WEB) && npm ci
	-$(PY)/pip install -q pre-commit && $(PY)/pre-commit install

up: env ## Levanta todo el stack en Docker (db, redis, mautic, evolution, api, web)
	$(COMPOSE) up -d --build

up-deps: env ## Levanta sólo dependencias (db, redis, mautic, evolution) para desarrollar en local
	$(COMPOSE) up -d db redis mautic_db mautic evolution

down: ## Detiene el stack
	$(COMPOSE) down

logs: ## Logs del stack (make logs s=api)
	$(COMPOSE) logs -f $(s)

dev-api: ## API con recarga en caliente (http://localhost:8000/docs)
	cd $(API) && .venv/bin/uvicorn oneheavy.main:app_factory --factory --reload --port 8000

dev-web: ## Frontend Vite (http://localhost:5173)
	cd $(WEB) && npm run dev -- --port 5173

test: test-api test-web ## Todas las pruebas

test-api: ## Pruebas backend con cobertura
	cd $(API) && .venv/bin/python -m pytest --cov --cov-report=term-missing

test-web: ## Pruebas frontend
	cd $(WEB) && npm test --if-present

lint: ## Linters (ruff + eslint)
	cd $(API) && .venv/bin/ruff check src tests && .venv/bin/ruff format --check src tests
	cd $(WEB) && npm run lint

fmt: ## Formatea el código
	cd $(API) && .venv/bin/ruff check --fix src tests && .venv/bin/ruff format src tests

typecheck: ## mypy + tsc
	cd $(API) && .venv/bin/mypy
	cd $(WEB) && npx tsc --noEmit -p tsconfig.app.json

build: ## Build de producción del frontend
	cd $(WEB) && npm run build

ci: lint typecheck test build ## Lo mismo que corre GitHub Actions

clean: ## Borra cachés y artefactos
	rm -rf $(API)/.pytest_cache $(API)/.mypy_cache $(API)/.ruff_cache $(API)/.coverage $(WEB)/dist
