COMPOSE ?= docker compose

.DEFAULT_GOAL := help
.PHONY: help up down restart logs ps build migrate admin check

help: ## Lista os comandos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-18s %s\n", $$1, $$2}'

up: ## Sobe tudo (postgres + api + worker + app) com build
	$(COMPOSE) up -d --build
	@echo "App:     http://localhost:5173"
	@echo "API:     http://localhost:8000/api/v1/health"
	@echo "Swagger: http://localhost:8000/docs"

down: ## Derruba os containers (mantém o volume do banco)
	$(COMPOSE) down

build: ## Reconstrói as imagens sem subir
	$(COMPOSE) build

restart: ## Reinicia api, worker e app
	$(COMPOSE) restart api worker app

logs: ## Acompanha os logs (make logs S=app para um serviço)
	$(COMPOSE) logs -f $(S)

ps: ## Status dos containers
	$(COMPOSE) ps

migrate: ## Aplica as migrations do banco no container da api (rode após atualizar o código)
	$(COMPOSE) exec api alembic upgrade head

admin: ## Cria o primeiro usuário admin (pede a senha; exige JWT_SECRET definido)
	$(COMPOSE) exec api python -m manage create-user admin --role admin

check: ## Qualidade do backend e do frontend
	$(MAKE) -C api check
	cd app && npm run lint && npm run typecheck && npm run test && npm run build
