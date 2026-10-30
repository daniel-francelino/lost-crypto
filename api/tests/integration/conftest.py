from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Any

import httpx
import pytest
from harness import START, Env, FakeClock, PathSource, cleanup

from container import Container, JobRunner, build_container, build_job_runner
from core.config import Settings
from fakes import fake_registry
from main import create_app


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
