# Lost Crypto

Console de operação de bots de trading de cripto: backend em FastAPI (`api/`) e frontend em React/TanStack Start (`app/`).

## Subir tudo com Docker

Requer Docker com Compose v2.20+.

```bash
make up
```

Isso sobe postgres, api, worker e o app. Depois:

| Serviço | URL |
|---|---|
| App (frontend) | http://localhost:5173 |
| API | http://localhost:8000/api/v1/health |
| Swagger | http://localhost:8000/docs |

O `docker-compose.yml` da raiz inclui o de `api/` e usa o nome de projeto `api`, o mesmo do `make up` dentro de `api/`; por isso os dois operam nos mesmos containers e no mesmo volume do banco.

Outros comandos: `make help` lista todos (`down`, `logs`, `ps`, `restart`, `admin`, `check`).

### Login

O login do app exige `JWT_SECRET` na API (≥ 32 caracteres). Crie um `.env` em `api/` (o compose lê esse arquivo) e depois o primeiro admin:

```bash
cd api && make jwt-secret      # copie o valor para JWT_SECRET no api/.env
make up
make admin                     # pede a senha (≥ 12 caracteres)
```

### Migrations do banco

O compose não migra o banco sozinho. Em um banco novo ou depois de atualizar o código, rode `make migrate` (ou `docker compose exec api alembic upgrade head`). Sem isso a API responde 500 com `column ... does not exist`.

### Configuração do frontend

`VITE_API_BASE_URL` e `VITE_APP_ENV` são gravadas no bundle **no build** e são públicas. Para mudar, exporte as variáveis e reconstrua:

```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1 make up
```

A API precisa listar a origem do app em `CORS_ORIGINS` (o padrão já inclui `http://localhost:5173`).

## Desenvolvimento sem container para o app

```bash
cd api && make db && make dev   # API local
cd app && npm ci && npm run dev # app com hot reload em http://localhost:5173
```

## Documentação

- Backend: [api/README.md](api/README.md) e [api/docs/](api/docs/)
- Frontend: [app/docs/](app/docs/README.md), deploy em [app/docs/10-deployment.md](app/docs/10-deployment.md)
- Livros de estudo: [docs/books/](docs/books/)
