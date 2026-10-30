UV ?= uv
export PYTHONPATH := src
COMPOSE ?= docker compose

.DEFAULT_GOAL := help
.PHONY: help install up down restart logs ps db dev worker migrate revision \
        lint format typecheck test test-integration check openapi

help: ## Lista os comandos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-18s %s\n", $$1, $$2}'

install: ## Instala as dependências (uv sync)
	$(UV) sync

# --- Ambiente Docker ---------------------------------------------------------
up: ## Sobe postgres + api + worker (build incluso)
	$(COMPOSE) up -d --build
	@echo "API:     http://localhost:8000/api/v1/health"
	@echo "Swagger: http://localhost:8000/docs"

down: ## Derruba os containers (mantém o volume do banco)
	$(COMPOSE) down

restart: ## Reinicia api e worker
	$(COMPOSE) restart api worker

logs: ## Acompanha os logs (make logs S=worker para um serviço)
	$(COMPOSE) logs -f $(S)

ps: ## Status dos containers
	$(COMPOSE) ps

db: ## Sobe só o postgres (para rodar a API localmente)
	$(COMPOSE) up -d postgres

# --- Execução local (sem containers de api/worker) --------------------------
dev: ## API local com reload em http://localhost:8000 (requer: make db)
	$(UV) run uvicorn main:app --reload --port 8000

worker: ## Worker local (requer: make db)
	$(UV) run python -m worker

# --- Banco -------------------------------------------------------------------
migrate: ## Aplica as migrations (alembic upgrade head)
	$(UV) run alembic upgrade head

revision: ## Cria migration: make revision M="mensagem"
	$(UV) run alembic revision --autogenerate -m "$(M)"

# --- Qualidade ---------------------------------------------------------------
lint: ## ruff check + verificação de formato
	$(UV) run ruff check .
	$(UV) run ruff format --check .

format: ## Corrige lint e formata o código
	$(UV) run ruff check --fix .
	$(UV) run ruff format .

typecheck: ## mypy (strict)
	$(UV) run mypy

test: ## Testes unitários (não precisam de banco)
	$(UV) run pytest

test-integration: ## Testes de integração (requer: make db)
	$(UV) run pytest -m integration

check: lint typecheck test ## lint + tipos + testes unitários

# --- Documentação da API -----------------------------------------------------
openapi: ## Exporta o contrato OpenAPI para docs/openapi.json
	$(UV) run python -c "import json; from main import app; print(json.dumps(app.openapi(), indent=2))" > docs/openapi.json
	@echo "Gerado: docs/openapi.json"
