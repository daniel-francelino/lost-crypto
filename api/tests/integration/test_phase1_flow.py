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
from fakes import fake_registry
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
            yield (
                client,
                build_job_runner(
                    build_container(settings, exchanges=fake_registry(SyntheticSource()))
                ),
            )
        await _cleanup(container)


async def _cleanup(container: Any) -> None:
    async with container.engine.begin() as conn:
        for table in ("backtest_runs", "candle_import_jobs", "candles"):
            await conn.execute(text(f"DELETE FROM {table} WHERE symbol = :s"), {"s": SYMBOL})
        await conn.execute(
            text(
                "DELETE FROM backtest_sweeps WHERE id NOT IN "
                "(SELECT sweep_id FROM backtest_runs WHERE sweep_id IS NOT NULL)"
            )
        )


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

    runner = build_job_runner(
        build_container(Settings(), exchanges=fake_registry(BrokenSource()))  # type: ignore[call-arg]
    )
    body = {"symbol": SYMBOL, "timeframe": "1h", "start": START.isoformat(), "end": END.isoformat()}
    resp = await client.post("/api/v1/market-data/imports", json=body)
    await _drain(runner)
    job = (await client.get(f"/api/v1/market-data/imports/{resp.json()['id']}")).json()
    assert job["status"] == "failed" and "exchange exploded" in job["error"]


async def _import_candles(client: httpx.AsyncClient, runner: JobRunner) -> dict[str, str]:
    body = {"symbol": SYMBOL, "timeframe": "1h", "start": START.isoformat(), "end": END.isoformat()}
    assert (await client.post("/api/v1/market-data/imports", json=body)).status_code == 202
    await _drain(runner)
    return body


async def test_train_test_split_reports_both_segments(
    stack: tuple[httpx.AsyncClient, JobRunner],
) -> None:
    client, runner = stack
    body = await _import_candles(client, runner)
    spec = {**body, "strategy_type": "ema_crossover", "test_fraction": "0.3"}
    resp = await client.post("/api/v1/backtests", json=spec)
    assert resp.status_code == 202
    await _drain(runner)

    run = (await client.get(f"/api/v1/backtests/{resp.json()['id']}")).json()
    assert run["status"] == "completed", run["error"]
    segments = run["segments"]
    assert Decimal(segments["test_fraction"]) == Decimal("0.3")
    assert segments["split_at"].startswith("2024-01-1")  # 70% of 600 hourly candles in
    assert segments["train"]["fills"] + segments["test"]["fills"] == run["metrics"]["fills"]
    assert Decimal(segments["test"]["initial_capital"]) > 0

    plain = await client.post("/api/v1/backtests", json={**body, "strategy_type": "ema_crossover"})
    await _drain(runner)
    assert (await client.get(f"/api/v1/backtests/{plain.json()['id']}")).json()["segments"] is None


async def test_parameter_sweep_ranks_runs_and_skips_invalid_combinations(
    stack: tuple[httpx.AsyncClient, JobRunner],
) -> None:
    client, runner = stack
    body = await _import_candles(client, runner)
    grid = {"fast_period": [3, 9], "slow_period": [5, 21, 2]}  # (9,5), (3,2), (9,2) are invalid
    spec = {**body, "strategy_type": "ema_crossover", "grid": grid, "test_fraction": "0.3"}
    resp = await client.post("/api/v1/backtests/sweeps", json=spec)
    assert resp.status_code == 202, resp.text
    assert resp.json()["run_count"] == 3 and len(resp.json()["skipped"]) == 3
    await _drain(runner)

    sweep = (await client.get(f"/api/v1/backtests/sweeps/{resp.json()['id']}")).json()
    assert (sweep["completed"], sweep["failed"], sweep["ranked_by"]) == (3, 0, "test_return_pct")
    scores = [Decimal(r["test_return_pct"]) for r in sweep["runs"]]
    assert scores == sorted(scores, reverse=True)  # best out-of-sample result first
    assert all(
        r["strategy_params"]["fast_period"] < r["strategy_params"]["slow_period"]
        for r in sweep["runs"]
    )

    ids = [r["id"] for r in sweep["runs"][:2]]
    compared = (await client.get("/api/v1/backtests/compare", params={"ids": ids})).json()
    assert [c["id"] for c in compared] == ids  # same order as requested
    assert all(c["sweep_id"] == sweep["id"] and c["segments"] for c in compared)

    without_split = {k: v for k, v in spec.items() if k != "test_fraction"}
    plain = (await client.post("/api/v1/backtests/sweeps", json=without_split)).json()
    assert plain["ranked_by"] == "total_return_pct" and "overfit" in plain["note"]


async def test_sweep_input_is_validated(stack: tuple[httpx.AsyncClient, JobRunner]) -> None:
    client, runner = stack
    body = await _import_candles(client, runner)
    base = {**body, "strategy_type": "ema_crossover"}
    huge = {"fast_period": list(range(2, 16)), "slow_period": list(range(20, 50))}  # 420 runs
    assert (
        await client.post("/api/v1/backtests/sweeps", json={**base, "grid": huge})
    ).status_code == 422
    unknown = {"grid": {"nonexistent": [1, 2]}}
    assert (
        await client.post("/api/v1/backtests/sweeps", json={**base, **unknown})
    ).status_code == 422
    missing = "00000000-0000-0000-0000-000000000000"
    assert (await client.get(f"/api/v1/backtests/sweeps/{missing}")).status_code == 404
