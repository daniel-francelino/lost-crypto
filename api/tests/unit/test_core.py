import asyncio
from datetime import UTC

import pytest

from core.clock import SystemClock
from core.config import AppEnv, Settings
from core.ids import UuidGenerator
from worker import run_worker


def test_system_clock_is_timezone_aware_utc() -> None:
    now = SystemClock().now()
    assert now.tzinfo is not None
    assert now.utcoffset() == UTC.utcoffset(None)


def test_uuid_generator_returns_unique_ids() -> None:
    gen = UuidGenerator()
    assert gen.new_id() != gen.new_id()


def test_live_trading_is_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LIVE_TRADING_ENABLED", raising=False)
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.live_trading_enabled is False
    assert settings.app_env == AppEnv.LOCAL


async def test_worker_stops_gracefully_when_signalled() -> None:
    settings = Settings(_env_file=None, worker_heartbeat_seconds=0.05)  # type: ignore[call-arg]
    stop = asyncio.Event()
    task = asyncio.create_task(run_worker(settings, stop, SystemClock()))
    await asyncio.sleep(0.1)
    stop.set()
    await asyncio.wait_for(task, timeout=1)
