from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api_router import api_router
from container import build_container
from core.config import Settings, get_settings
from core.logging import configure_logging

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
]


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

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
        version="0.2.0",
        description="Backend da plataforma Lost Crypto: dados de mercado, estratégias e backtests.",
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
    return app


app = create_app()
