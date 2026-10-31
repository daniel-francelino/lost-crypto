UV ?= uv
export PYTHONPATH := src
COMPOSE ?= docker compose

.DEFAULT_GOAL := help
.PHONY: help install up down restart logs ps db dev worker migrate revision \
        lint format typecheck test test-integration check openapi master-key test-testnet

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

# Roda em um banco separado (lostcrypto_test) para nunca tocar nos seus bots/dados de dev.
TEST_DB_URL ?= postgresql+asyncpg://lostcrypto:lostcrypto@localhost:5432/lostcrypto_test
test-integration: export DATABASE_URL := $(TEST_DB_URL)
test-integration: ## Testes de integração em banco separado (requer: make db)
	-$(COMPOSE) exec -T postgres psql -U lostcrypto -c "CREATE DATABASE lostcrypto_test"
	$(UV) run alembic upgrade head
	$(UV) run pytest -m integration

check: lint typecheck test ## lint + tipos + testes unitários

master-key: ## Gera uma chave Fernet para CREDENTIAL_MASTER_KEYS
	@$(UV) run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

test-testnet: ## Teste de fumaça na testnet REAL (exige TESTNET_API_KEY / TESTNET_API_SECRET)
	$(UV) run pytest tests/smoke -m smoke -s

# --- Documentação da API -----------------------------------------------------
openapi: ## Exporta o contrato OpenAPI para docs/openapi.json
	$(UV) run python -c "import json; from main import app; print(json.dumps(app.openapi(), indent=2))" > docs/openapi.json
	@echo "Gerado: docs/openapi.json"
