"""Book 1 ch. 3 against a real PostgreSQL: bad candles, gaps, outliers, robustness, listings."""

import math
from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx
import pytest
from harness import START as PATH_START
from harness import Env, PathSource
from sqlalchemy import text

from container import JobRunner, build_container, build_job_runner
from core.config import Settings
from factories import MARKET
from fakes import FakeExchange
from main import create_app
from modules.exchanges.application.registry import ExchangeRegistry
from modules.market_data.application.listings import ListingRecorder
from modules.market_data.domain.models import Candle, ListedMarket, MarketInfo, Timeframe

pytestmark = pytest.mark.integration

SYMBOL = "DQ/USDT"
START = datetime(2024, 3, 1, tzinfo=UTC)
END = START + timedelta(hours=600)
MISSING = set(range(250, 280))  # a 30-hour hole: over both limits (1% and 24 h)
BAD = 200  # high below the close: never stored
SPIKE = 400  # one-candle jump: an outlier to review, not an error


class FlawedSource:
    """Oscillating prices with a hole, a malformed candle and a spike."""

    def __init__(self) -> None:
        self.bump = Decimal(0)  # changes one stored candle on re-import
        self.markets: list[ListedMarket] = []

    async def fetch_candles(
        self, symbol: str, timeframe: Timeframe, since: datetime, limit: int
    ) -> list[Candle]:
        out: list[Candle] = []
        for i in range(limit):
            t = since + i * timeframe.delta
            hour = int((t - START).total_seconds() // 3600)
            if hour in MISSING:
                continue
            close = Decimal(str(round(20_000 + 3_000 * math.sin(hour / 18), 2)))
            if hour == SPIKE:
                close *= 2
            if hour == 10:
                close += self.bump
            candle = Candle(
                symbol, timeframe, t, close - 5, close + 10, close - 10, close, Decimal(3)
            )
            out.append(replace(candle, high=close - 50) if hour == BAD else candle)
        return out

    async def fetch_market_info(self, symbol: str) -> MarketInfo:
        return MarketInfo(
            symbol, MARKET.step_size, MARKET.tick_size, MARKET.min_quantity, Decimal(10)
        )


class ListingExchange(FakeExchange):
    def __init__(self, source: FlawedSource) -> None:
        super().__init__(source)
        self.flawed = source

    async def list_markets(self) -> list[ListedMarket]:
        return self.flawed.markets


@pytest.fixture
async def stack() -> AsyncIterator[tuple[httpx.AsyncClient, JobRunner, FlawedSource, Any]]:
    settings = Settings()  # type: ignore[call-arg]
    source = FlawedSource()
    registry = ExchangeRegistry()
    registry.register(ListingExchange, lambda: ListingExchange(source))
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        await _cleanup(app.state.container)
        container = build_container(settings, exchanges=registry)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, build_job_runner(container), source, container
        await _cleanup(app.state.container)


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
        await conn.execute(text("DELETE FROM exchange_listings WHERE symbol LIKE 'DQ%'"))


async def _drain(runner: JobRunner) -> None:
    for _ in range(20):
        if not await runner.run_once():
            return
    raise AssertionError("job queue did not drain")


BODY = {"symbol": SYMBOL, "timeframe": "1h", "start": START.isoformat(), "end": END.isoformat()}


async def _import(client: httpx.AsyncClient, runner: JobRunner) -> dict[str, Any]:
    resp = await client.post("/api/v1/market-data/imports", json=BODY)
    await _drain(runner)
    job: dict[str, Any] = (
        await client.get(f"/api/v1/market-data/imports/{resp.json()['id']}")
    ).json()
    return job


async def test_bad_candles_are_not_stored_and_changes_are_counted(stack: Any) -> None:
    client, runner, source, _ = stack
    job = await _import(client, runner)
    assert job["status"] == "completed", job["error"]
    assert job["candles_rejected"] == 1 and job["candles_changed"] == 0
    assert job["rejection_samples"][0]["problems"] == ["high_below_body"]
    assert job["candles_imported"] == 600 - len(MISSING) - 1

    source.bump = Decimal(7)
    again = await _import(client, runner)
    assert again["candles_changed"] == 1  # the exchange now reports hour 10 differently


async def test_coverage_in_range_and_gap_guard(stack: Any) -> None:
    client, runner, _, _ = stack
    await _import(client, runner)
    cov = (
        await client.get(
            "/api/v1/market-data/coverage",
            params={
                "symbol": SYMBOL,
                "timeframe": "1h",
                "start": BODY["start"],
                "end": BODY["end"],
            },
        )
    ).json()
    assert cov["in_range"]["missing"] == len(MISSING) + 1  # the hole plus the rejected candle
    assert cov["in_range"]["largest_gap"] == len(MISSING)

    spec = {**BODY, "strategy_type": "ema_crossover"}
    refused = await client.post("/api/v1/backtests", json=spec)
    assert refused.status_code == 422 and "allow_gaps" in refused.text

    resp = await client.post("/api/v1/backtests", json={**spec, "allow_gaps": True})
    assert resp.status_code == 202, resp.text
    await _drain(runner)
    run = (await client.get(f"/api/v1/backtests/{resp.json()['id']}")).json()
    assert run["status"] == "completed", run["error"]
    quality = run["data_quality"]
    assert quality["gaps"]["missing"] == len(MISSING) + 1 and quality["gaps"]["allowed"] is True
    assert quality["gaps"]["over_limit"] is True
    assert quality["invalid_candles"] == 0  # rejected at import already
    assert quality["outliers"] >= 1
    assert quality["sample"]["free_parameters"] == 2
    assert quality["sample"]["bars"] == run["candles_count"]
    assert run["metrics"]["return_gaps"] >= 1


async def test_outlier_report_and_sweep_robustness(stack: Any) -> None:
    client, runner, _, _ = stack
    await _import(client, runner)
    found = (
        await client.get(
            "/api/v1/market-data/outliers",
            params={
                "symbol": SYMBOL,
                "timeframe": "1h",
                "start": BODY["start"],
                "end": BODY["end"],
            },
        )
    ).json()
    spike = (START + timedelta(hours=SPIKE)).isoformat().replace("+00:00", "Z")
    assert spike in [o["open_time"] for o in found]
    assert all(Decimal(o["sigmas"]) > 4 for o in found)

    grid = {"fast_period": [3, 5, 9], "slow_period": [13, 21, 34]}
    spec = {
        **BODY,
        "strategy_type": "ema_crossover",
        "allow_gaps": True,
        "grid": grid,
        "test_fraction": "0.3",
    }
    sweep = (await client.post("/api/v1/backtests/sweeps", json=spec)).json()
    await _drain(runner)
    result = (await client.get(f"/api/v1/backtests/sweeps/{sweep['id']}")).json()
    robustness = result["robustness"]
    assert robustness["verdict"] in {"plateau", "peak", "unprofitable", "insufficient"}
    assert robustness["metric"] == "train_return_pct"
    assert robustness["scored"] == result["completed"]


async def test_listing_snapshots_record_delistings(stack: Any) -> None:
    client, _, source, container = stack
    source.markets = [ListedMarket("DQA/USDT", True), ListedMarket("DQB/USDT", True)]
    recorder = ListingRecorder(container.import_stores, container.exchanges, container.clock)
    assert await recorder.run_due()
    assert not await recorder.run_due()  # once a day
    source.markets = [ListedMarket("DQA/USDT", False)]
    later = ListingRecorder(container.import_stores, container.exchanges, container.clock)
    await later.run_due()
    rows = {
        r["symbol"]: r
        for r in (await client.get("/api/v1/market-data/listings")).json()
        if r["symbol"].startswith("DQ")
    }
    assert rows["DQA/USDT"]["status"] == "inactive"
    assert rows["DQB/USDT"]["status"] == "delisted" and rows["DQB/USDT"]["delisted_at"]

    source.markets = []  # an empty answer must not delist everything
    await ListingRecorder(container.import_stores, container.exchanges, container.clock).run_due()
    after = (await client.get("/api/v1/market-data/listings", params={"symbol": "DQA/USDT"})).json()
    assert after[0]["status"] == "inactive"


async def test_strategy_catalog_reports_parameter_count(stack: Any) -> None:
    client, _, _, _ = stack
    strategies = (await client.get("/api/v1/strategies")).json()
    ema = next(s for s in strategies if s["type_key"] == "ema_crossover")
    assert ema["parameter_count"] == 4 and ema["too_many_parameters"] is False


class InvalidCandleSource(PathSource):
    """Hour 25 comes back malformed (high below the close)."""

    async def fetch_candles(
        self, symbol: str, timeframe: Timeframe, since: datetime, limit: int
    ) -> list[Candle]:
        candles = await super().fetch_candles(symbol, timeframe, since, limit)
        bad = PATH_START + timedelta(hours=25)
        return [replace(c, high=c.close - 1) if c.open_time == bad else c for c in candles]


async def test_trader_skips_an_invalid_candle_and_audits_it(env: Env) -> None:
    runner = env.make_runner(InvalidCandleSource)
    bot_id = await env.create_bot()
    assert (await env.command(bot_id, "start")).status_code == 202
    await runner.run_once()
    await env.run_until(runner, 40)

    events = (await env.http.get("/api/v1/audit-events", params={"bot_id": bot_id})).json()
    skipped = [e for e in events if e["event_type"] == "data.invalid_candle"]
    assert len(skipped) == 1
    assert skipped[0]["payload"]["problems"] == ["high_below_body"]
    equity = (await env.http.get(f"/api/v1/bots/{bot_id}/equity")).json()
    assert len(equity) == 19  # the bad candle got no snapshot; later candles were processed
    assert (await env.bot(bot_id))["observed_state"] == "running"
