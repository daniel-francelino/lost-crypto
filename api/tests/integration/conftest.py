from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta
from decimal import Decimal
from typing import Any

import httpx
import pytest
from cryptography.fernet import Fernet
from harness import (
    API_TOKEN,
    LIVE_SETTINGS,
    START,
    Env,
    FakeClock,
    PathSource,
    TestnetEnv,
    cleanup,
)

from container import Container, JobRunner, build_container, build_job_runner
from core.config import Settings
from fakes import fake_registry, sim_registry
from main import create_app
from simulated_exchange import SimulatedExchange


@pytest.fixture
async def env() -> AsyncIterator[Env]:
    settings = Settings()  # type: ignore[call-arg]
    clock = FakeClock(START + timedelta(hours=20, seconds=5))
    app = create_app(settings)
    containers: list[Container] = []

    def make_runner(
        source_cls: type[PathSource] = PathSource,
        *,
        path: dict[int, int] | None = None,
        **settings_overrides: Any,
    ) -> JobRunner:
        """A worker in its own 'process' (container) with a simulated exchange."""
        container = build_container(
            settings.model_copy(update=settings_overrides),
            clock=clock,
            exchanges=fake_registry(source_cls(clock, path)),
        )
        containers.append(container)
        return build_job_runner(container)

    async with app.router.lifespan_context(app):
        api_container: Container = app.state.container
        await cleanup(api_container)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
            yield Env(http, clock, make_runner, containers)
        await cleanup(api_container)
    for container in containers:
        await container.engine.dispose()


@asynccontextmanager
async def _testnet_stack(**overrides: Any) -> AsyncIterator[TestnetEnv]:
    master_key = Fernet.generate_key().decode()
    values: dict[str, Any] = {
        "api_token": API_TOKEN,
        "credential_master_keys": master_key,
        "testnet_trading_enabled": True,
        **overrides,
    }
    settings = Settings(**values)  # type: ignore[call-arg]
    clock = FakeClock(START + timedelta(hours=20, seconds=5))
    source = PathSource(clock)

    def price_now(symbol: str) -> Decimal:
        """The market price the simulated exchange fills at: the last closed candle's close."""
        return source.price(int((clock.now() - START).total_seconds() // 3600) - 1)

    sim = SimulatedExchange(
        source, clock, price_now, balances={"USDT": Decimal(100_000), "TST": Decimal(0)}
    )
    app = create_app(settings)
    containers: list[Container] = []

    def make_runner(
        source_cls: type[PathSource] = PathSource,
        *,
        path: dict[int, int] | None = None,
        **settings_overrides: Any,
    ) -> JobRunner:
        if path is not None:
            source.path = path
        container = build_container(
            settings.model_copy(update=settings_overrides),
            clock=clock,
            exchanges=sim_registry(sim),
        )
        containers.append(container)
        return build_job_runner(container)

    async with app.router.lifespan_context(app):
        api_container: Container = app.state.container
        await cleanup(api_container)
        transport = httpx.ASGITransport(app=app)
        headers = {"Authorization": f"Bearer {API_TOKEN}"}
        async with (
            httpx.AsyncClient(transport=transport, base_url="http://test", headers=headers) as http,
            httpx.AsyncClient(transport=transport, base_url="http://test") as anonymous,
        ):
            yield TestnetEnv(
                http,
                clock,
                make_runner,
                containers,
                sim=sim,
                anonymous=anonymous,
                api_container=api_container,
            )
        await cleanup(api_container)
    for container in containers:
        await container.engine.dispose()


@pytest.fixture
async def testnet_env() -> AsyncIterator[TestnetEnv]:
    async with _testnet_stack() as env:
        yield env


@pytest.fixture
async def live_env() -> AsyncIterator[TestnetEnv]:
    async with _testnet_stack(**LIVE_SETTINGS) as env:
        yield env


@pytest.fixture
def stack() -> Any:
    """``async with stack(**settings) as env``: a full stack with custom API settings."""
    return _testnet_stack
