import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api_router import api_router
from container import build_container
from core.config import Settings, get_settings
from core.errors import ConflictError, DomainError, NotFoundError
from core.logging import configure_logging
from core.pagination import TOTAL_COUNT_HEADER
from core.security.auth import assert_secure_configuration
from core.security.vault import VaultNotConfigured
from modules.auth.domain import AccountLocked, InvalidCredentials
from modules.auth.service import AuthNotConfigured

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
        "name": "alerts",
        "description": "Alertas de falha (worker parado, bot com erro, candles atrasados...), "
        "mostrados no app.",
    },
    {
        "name": "auth",
        "description": "Login, sessões (refresh token em cookie httpOnly) e usuários.",
    },
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


async def _unauthorized_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=401, content={"detail": str(exc)}, headers={"WWW-Authenticate": "Bearer"}
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    assert_secure_configuration(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        container = build_container(settings)
        app.state.container = container
        app.state.engine = container.engine
        watcher = (
            asyncio.create_task(container.alert_monitor.run_api_forever())
            if settings.alerts_api_evaluation_enabled
            else None
        )
        try:
            yield
        finally:
            if watcher is not None:
                watcher.cancel()
                with suppress(asyncio.CancelledError):
                    await watcher
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
        allow_credentials=True,  # the refresh-token cookie
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[TOTAL_COUNT_HEADER],
    )
    app.include_router(api_router)

    # Domain errors map to HTTP in one place (most specific class wins).
    app.add_exception_handler(NotFoundError, _error_handler(404))
    app.add_exception_handler(ConflictError, _error_handler(409))
    app.add_exception_handler(DomainError, _error_handler(422))
    app.add_exception_handler(VaultNotConfigured, _error_handler(503))
    app.add_exception_handler(AuthNotConfigured, _error_handler(503))
    app.add_exception_handler(AccountLocked, _error_handler(401))
    app.add_exception_handler(InvalidCredentials, _unauthorized_handler)
    return app


app = create_app()
