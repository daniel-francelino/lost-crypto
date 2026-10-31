from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api_router import api_router
from container import build_container
from core.config import Settings, get_settings
from core.errors import ConflictError, DomainError, NotFoundError
from core.logging import configure_logging
from core.security.auth import assert_secure_configuration
from core.security.vault import VaultNotConfigured

OPENAPI_TAGS = [
    {"name": "health", "description": "Liveness e readiness da API."},
    {"name": "strategies", "description": "Estratégias disponíveis e seus parâmetros."},
    {
        "name": "market-data",
        "description": "Importação (assíncrona, via worker) e consulta de candles históricos.",
    },
    {
        "name": "backtests",
        "description": "Execução (assíncrona, via worker) e resultados de backtests. "
        "Simulações em dados históricos — não são previsão de retorno.",
    },
    {
        "name": "bots",
        "description": "Bots de paper trading: configuração, comandos (start/pause/stop, "
        "executados pelo worker), ordens, portfólio virtual e performance. Sem dinheiro real.",
    },
    {
        "name": "system",
        "description": "Kill switch global: pausa todos os bots e bloqueia novas entradas.",
    },
    {"name": "audit", "description": "Trilha de auditoria append-only."},
    {
        "name": "exchange-connections",
        "description": "Credenciais de exchange (testnet), guardadas criptografadas e nunca "
        "devolvidas. Exige API_TOKEN configurado.",
    },
]

ErrorHandler = Callable[[Request, Exception], Awaitable[JSONResponse]]


def _error_handler(status_code: int) -> ErrorHandler:
    async def handle(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": str(exc)})

    return handle


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    assert_secure_configuration(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        container = build_container(settings)
        app.state.container = container
        app.state.engine = container.engine
        try:
            yield
        finally:
            await container.engine.dispose()

    app = FastAPI(
        title="Lost Crypto API",
        version="0.3.0",
        description=(
            "Backend da plataforma Lost Crypto: dados de mercado, estratégias, backtests "
            "e paper trading."
        ),
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)

    # Domain errors map to HTTP in one place (most specific class wins).
    app.add_exception_handler(NotFoundError, _error_handler(404))
    app.add_exception_handler(ConflictError, _error_handler(409))
    app.add_exception_handler(DomainError, _error_handler(422))
    app.add_exception_handler(VaultNotConfigured, _error_handler(503))
    return app


app = create_app()
