"""End-to-end Phase 1 flow against a real PostgreSQL (apply migrations first: alembic upgrade head).

Import candles -> query coverage -> queue backtests -> worker executes -> read results.
The exchange is replaced by a deterministic fake source; everything else is the real stack.
"""

import math
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx
import pytest
from sqlalchemy import text

from container import JobRunner, build_container, build_job_runner
from core.config import Settings
from factories import MARKET
from main import create_app
from modules.market_data.domain.models import Candle, MarketInfo, Timeframe

pytestmark = pytest.mark.integration

SYMBOL = "TST/USDT"
START = datetime(2024, 1, 1, tzinfo=UTC)
END = START + timedelta(hours=600)


class SyntheticSource:
    """Deterministic oscillating price series, so the EMA strategy trades several times."""

    async def fetch_candles(
        self, symbol: str, timeframe: Timeframe, since: datetime, limit: int
    ) -> list[Candle]:
        out: list[Candle] = []
        for i in range(limit):
            t = since + i * timeframe.delta
            hours = int((t - START).total_seconds() // 3600)
            close = Decimal(str(round(20_000 + 3_000 * math.sin(hours / 18), 2)))
            out.append(
                Candle(symbol, timeframe, t, close - 5, close + 10, close - 10, close, Decimal(3))
            )
        return out

    async def fetch_market_info(self, symbol: str) -> MarketInfo:
        return MarketInfo(
            symbol, MARKET.step_size, MARKET.tick_size, MARKET.min_quantity, Decimal(10)
        )


@pytest.fixture
async def stack() -> AsyncIterator[tuple[httpx.AsyncClient, JobRunner]]:
    settings = Settings()  # type: ignore[call-arg]
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        container = app.state.container
        await _cleanup(container)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, build_job_runner(build_container(settings), SyntheticSource())
        await _cleanup(container)


async def _cleanup(container: Any) -> None:
    async with container.engine.begin() as conn:
        for table in ("backtest_runs", "candle_import_jobs", "candles"):
            await conn.execute(text(f"DELETE FROM {table} WHERE symbol = :s"), {"s": SYMBOL})


async def _drain(runner: JobRunner) -> None:
    for _ in range(10):
        if not await runner.run_once():
            return
    raise AssertionError("job queue did not drain")


async def test_import_then_backtest_end_to_end(stack: tuple[httpx.AsyncClient, JobRunner]) -> None:
    client, runner = stack
    body = {"symbol": SYMBOL, "timeframe": "1h", "start": START.isoformat(), "end": END.isoformat()}

    # Backtesting without data is refused up front.
    bt = {**body, "strategy_type": "ema_crossover", "strategy_params": {}, "fee_rate": "0.001"}
    assert (await client.post("/api/v1/backtests", json=bt)).status_code == 422

    # Import (idempotent: running it twice must not duplicate anything).
    for _ in range(2):
        resp = await client.post("/api/v1/market-data/imports", json=body)
        assert resp.status_code == 202
        await _drain(runner)
        job = (await client.get(f"/api/v1/market-data/imports/{resp.json()['id']}")).json()
        assert job["status"] == "completed" and job["candles_imported"] == 600

    cov = (
        await client.get(
            "/api/v1/market-data/coverage", params={"symbol": SYMBOL, "timeframe": "1h"}
        )
    ).json()
    assert cov["count"] == 600 and cov["gaps"] == []

    # Invalid strategy parameters are rejected at creation time.
    bad = {**bt, "strategy_params": {"fast_period": 30, "slow_period": 10}}
    assert (await client.post("/api/v1/backtests", json=bad)).status_code == 422

    # Two identical runs must produce identical results (reproducibility).
    results = []
    for _ in range(2):
        resp = await client.post("/api/v1/backtests", json=bt)
        assert resp.status_code == 202 and resp.json()["status"] == "queued"
        await _drain(runner)
        results.append((await client.get(f"/api/v1/backtests/{resp.json()['id']}")).json())

    first, second = results
    assert first["status"] == "completed", first["error"]
    assert first["candles_count"] == 600 and first["data_hash"]
    assert first["metrics"]["round_trips"] >= 1
    assert first["metrics"]["fees_paid"] != "0.00000000"
    assert (first["data_hash"], first["metrics"]) == (second["data_hash"], second["metrics"])

    run_id = first["id"]
    trades = (await client.get(f"/api/v1/backtests/{run_id}/trades")).json()
    assert len(trades) == first["metrics"]["fills"]
    assert [t["side"] for t in trades[:2]] == ["buy", "sell"]
    equity = (await client.get(f"/api/v1/backtests/{run_id}/equity")).json()
    assert len(equity) == 600

    listing = (await client.get("/api/v1/backtests")).json()
    assert {r["id"] for r in listing} >= {first["id"], second["id"]}
    assert (
        await client.get("/api/v1/backtests/00000000-0000-0000-0000-000000000000")
    ).status_code == 404


async def test_failed_job_is_marked_failed_with_error(
    stack: tuple[httpx.AsyncClient, JobRunner],
) -> None:
    client, runner = stack

    class BrokenSource(SyntheticSource):
        async def fetch_candles(self, *args: Any, **kwargs: Any) -> list[Candle]:
            raise RuntimeError("exchange exploded")

    runner = build_job_runner(build_container(Settings()), BrokenSource())  # type: ignore[call-arg]
    body = {"symbol": SYMBOL, "timeframe": "1h", "start": START.isoformat(), "end": END.isoformat()}
    resp = await client.post("/api/v1/market-data/imports", json=body)
    await _drain(runner)
    job = (await client.get(f"/api/v1/market-data/imports/{resp.json()['id']}")).json()
    assert job["status"] == "failed" and "exchange exploded" in job["error"]
