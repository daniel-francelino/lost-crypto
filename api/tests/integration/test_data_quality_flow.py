"""Book 1 ch. 3 against a real PostgreSQL: bad candles, gaps, outliers, robustness, listings."""

import math
from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

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
    assert (
        ema["parameter_count"] == 5 and ema["too_many_parameters"] is False
    )  # 4 + max_holding_candles


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


async def test_prior_runs_counts_other_looks_at_the_same_window(stack: Any) -> None:
    client, runner, _, _ = stack
    await _import(client, runner)
    spec = {"strategy_type": "ema_crossover", "allow_gaps": True, "symbol": SYMBOL}
    early = {"start": START.isoformat(), "end": (START + timedelta(hours=100)).isoformat()}
    late = {
        "start": (START + timedelta(hours=300)).isoformat(),
        "end": (START + timedelta(hours=400)).isoformat(),
    }
    ids = []
    for window in (early, early, late):
        resp = await client.post("/api/v1/backtests", json={**spec, "timeframe": "1h", **window})
        assert resp.status_code == 202, resp.text
        ids.append(resp.json()["id"])
    await _drain(runner)

    detail = [(await client.get(f"/api/v1/backtests/{i}")).json() for i in ids]
    assert [d["status"] for d in detail] == ["completed"] * 3
    assert detail[0]["prior_runs"] == 1  # the other early run; the late one does not overlap
    assert detail[1]["prior_runs"] == 1
    assert detail[2]["prior_runs"] == 0
    listed = (await client.get("/api/v1/backtests")).json()
    assert all(item["prior_runs"] is None for item in listed)  # only the detail pays the query


async def test_backtest_comparison_finds_the_equivalent_run(stack: Any) -> None:
    client, runner, _, container = stack
    await _import(client, runner)
    params = {"fast_period": 3, "slow_period": 13}
    spec = {**BODY, "strategy_type": "ema_crossover", "strategy_params": params, "allow_gaps": True}
    run_id = (await client.post("/api/v1/backtests", json=spec)).json()["id"]
    await _drain(runner)
    bot = await client.post(
        "/api/v1/bots",
        json={
            "name": "dq-comparison",
            "strategy_type": "ema_crossover",
            "strategy_params": params,
            "symbol": SYMBOL,
            "timeframe": "1h",
            "initial_capital": "1000",
            "risk": {"max_daily_loss_pct": None},
        },
    )
    assert bot.status_code == 201, bot.text
    bot_id = bot.json()["id"]
    try:
        found = await client.get(f"/api/v1/bots/{bot_id}/backtest-comparison")
        assert found.status_code == 200, found.text
        body = found.json()
        assert body["run_id"] == run_id and body["ratio"] is None
        assert body["min_periods"] == 30 and body["chan_min_ratio"] == "0.5"
        assert body["reason"] and "short live sample" in body["reason"]  # the bot never ran

        other = {**params, "slow_period": 21}
        none = await client.post(
            "/api/v1/bots",
            json={
                "name": "dq-comparison-2",
                "strategy_type": "ema_crossover",
                "strategy_params": other,
                "symbol": SYMBOL,
                "timeframe": "1h",
                "initial_capital": "1000",
                "risk": {"max_daily_loss_pct": None},
            },
        )
        unmatched = (
            await client.get(f"/api/v1/bots/{none.json()['id']}/backtest-comparison")
        ).json()
        assert unmatched["run_id"] is None and "no completed backtest" in unmatched["reason"]

        missing = await client.get(f"/api/v1/bots/{uuid4()}/backtest-comparison")
        assert missing.status_code == 404
    finally:
        async with container.engine.begin() as conn:
            await conn.execute(text("DELETE FROM bots WHERE name LIKE 'dq-comparison%'"))


async def test_run_stores_the_random_entries_test_and_it_is_repeatable(stack: Any) -> None:
    client, runner, _, _ = stack
    await _import(client, runner)
    spec = {
        **BODY,
        "strategy_type": "ema_crossover",
        "strategy_params": {"fast_period": 3, "slow_period": 13},
        "allow_gaps": True,
        "seed": 5,
    }
    ids = [(await client.post("/api/v1/backtests", json=spec)).json()["id"] for _ in range(2)]
    await _drain(runner)
    blocks = []
    for run_id in ids:
        run = (await client.get(f"/api/v1/backtests/{run_id}")).json()
        assert run["status"] == "completed", run["error"]
        blocks.append(run["significance"]["random_entries"])
    # The oscillating series makes only a handful of trades, below the minimum: the block says
    # so instead of a misleading number (the available path is covered in unit tests).
    assert blocks[0]["available"] is False and "fewer than" in blocks[0]["reason"]
    assert blocks[0]["fraction"] is None
    assert blocks[0] == blocks[1]


async def test_half_life_endpoint_shape_and_validation(stack: Any) -> None:
    client, runner, _, _ = stack
    await _import(client, runner)
    params = {"symbol": SYMBOL, "timeframe": "1h", "start": BODY["start"], "end": BODY["end"]}
    found = await client.get("/api/v1/market-data/half-life", params=params)
    assert found.status_code == 200, found.text
    body = found.json()
    assert (
        body["n"] > 100
        and body["log_prices"] is True
        and "Estimativa descritiva" in body["warning"]
    )
    assert body["gaps"] >= 1  # the hole of the flawed series is reported, not hidden
    assert (
        body["sample_every"] == 1 and "hurst" in body and isinstance(body["variance_ratios"], list)
    )
    assert {r["lag"] for r in body["variance_ratios"]} <= {2, 4, 8}
    assert isinstance(body["suggested_windows"], list)
    sampled = (
        await client.get("/api/v1/market-data/half-life", params={**params, "sample_every": 4})
    ).json()
    assert sampled["sample_every"] == 4 and sampled["n"] <= body["n"] // 4 + 1
    zero = await client.get("/api/v1/market-data/half-life", params={**params, "sample_every": 0})
    assert zero.status_code == 422
    bad = await client.get(
        "/api/v1/market-data/half-life",
        params={**params, "start": BODY["end"], "end": BODY["start"]},
    )
    assert bad.status_code == 422


async def _signals_with_jump_limit(env: Env, limit: str | None) -> list[dict[str, Any]]:
    runner = env.make_runner()
    risk: dict[str, Any] = {"max_daily_loss_pct": None, "max_close_jump_pct": limit}
    bot_id = await env.create_bot(risk=risk)
    stored = (await env.bot(bot_id))["risk"]["max_close_jump_pct"]
    assert (stored is None) == (limit is None)
    assert (await env.command(bot_id, "start")).status_code == 202
    await runner.run_once()
    await env.run_until(runner, 40)
    return await env.signals(bot_id)


async def test_trader_refuses_an_entry_after_a_close_jump_above_the_limit(env: Env) -> None:
    signals = await _signals_with_jump_limit(env, "5")  # the entry candle closes 100 -> 110
    buys = [s for s in signals if s["side"] == "buy"]
    assert buys and buys[0]["decision"] == "rejected"
    assert "close moved 10.0%" in buys[0]["decision_reason"]


@pytest.mark.parametrize("limit", ["15", None])
async def test_trader_enters_when_the_jump_is_inside_the_limit_or_the_limit_is_off(
    env: Env, limit: str | None
) -> None:
    signals = await _signals_with_jump_limit(env, limit)
    assert [s["decision"] for s in signals if s["side"] == "buy"] == ["approved"]


async def test_mean_reversion_runs_end_to_end_and_the_catalog_lists_its_style(stack: Any) -> None:
    client, runner, _, _ = stack
    catalog = {s["type_key"]: s for s in (await client.get("/api/v1/strategies")).json()}
    zscore = catalog["mean_reversion_zscore"]
    assert zscore["style"] == "mean_reversion" and catalog["ema_crossover"]["style"] == "trend"
    assert zscore["parameter_count"] == 5 and zscore["too_many_parameters"] is False
    entry = next(p for p in zscore["parameters"] if p["name"] == "entry_z")
    assert entry["minimum"] == 0.1 and entry["default"] in (2, "2")

    await _import(client, runner)
    spec = {
        **BODY,
        "strategy_type": "mean_reversion_zscore",
        "strategy_params": {"lookback": 20, "entry_z": 1.5},
        "allow_gaps": True,
    }
    run_id = (await client.post("/api/v1/backtests", json=spec)).json()["id"]
    await _drain(runner)
    run = (await client.get(f"/api/v1/backtests/{run_id}")).json()
    assert run["status"] == "completed", run["error"]
    assert run["metrics"]["round_trips"] >= 1
    bad = await client.post("/api/v1/backtests", json={**spec, "strategy_params": {"lookback": 3}})
    assert bad.status_code == 422


async def test_notes_are_audit_events_for_bots_and_backtests(stack: Any) -> None:
    client, runner, _, container = stack
    await _import(client, runner)
    spec = {**BODY, "strategy_type": "ema_crossover", "allow_gaps": True}
    run_id = (await client.post("/api/v1/backtests", json=spec)).json()["id"]
    await _drain(runner)
    bot = await client.post(
        "/api/v1/bots",
        json={
            "name": "dq-notes",
            "strategy_type": "ema_crossover",
            "symbol": SYMBOL,
            "timeframe": "1h",
            "initial_capital": "1000",
            "risk": {"max_daily_loss_pct": None},
        },
    )
    bot_id = bot.json()["id"]
    try:
        script = "<script>alert(1)</script> pausado: o regime mudou"
        for path in (f"/api/v1/bots/{bot_id}/notes", f"/api/v1/backtests/{run_id}/notes"):
            created = await client.post(path, json={"text": f"  {script}  "})
            assert created.status_code == 201 and created.json()["text"] == script
            assert (await client.post(path, json={"text": "   "})).status_code == 422
            assert (await client.post(path, json={"text": "x" * 2001})).status_code == 422
        for entity in (bot_id, run_id):
            listed = (
                await client.get(
                    "/api/v1/audit-events", params={"event_type": "note.added", "entity_id": entity}
                )
            ).json()
            assert [e["payload"]["text"] for e in listed] == [script]
            assert listed[0]["actor"] and listed[0]["entity_id"] == entity
        assert listed[0]["entity_type"] == "backtest" and listed[0]["bot_id"] is None
        total = await client.get(
            "/api/v1/audit-events", params={"event_type": "note.added", "entity_id": bot_id}
        )
        assert total.headers["X-Total-Count"] == "1"
        unknown = uuid4()
        for path in (f"/api/v1/bots/{unknown}/notes", f"/api/v1/backtests/{unknown}/notes"):
            assert (await client.post(path, json={"text": "x"})).status_code == 404
    finally:
        async with container.engine.begin() as conn:
            await conn.execute(text("DELETE FROM audit_events WHERE event_type = 'note.added'"))
            await conn.execute(text("DELETE FROM bots WHERE name = 'dq-notes'"))


async def test_regime_breaks_are_named_deleted_audited_and_cut_the_backtest(stack: Any) -> None:
    client, runner, _, container = stack
    await _import(client, runner)
    when = (START + timedelta(hours=150)).isoformat()
    try:
        created = await client.post(
            "/api/v1/market-data/regime-breaks",
            json={"name": "dq-crash", "occurred_at": when, "symbol": SYMBOL, "note": "spike"},
        )
        assert created.status_code == 201, created.text
        brk = created.json()
        assert brk["created_by"] and brk["exchange"] is None and brk["symbol"] == SYMBOL
        again = await client.post(
            "/api/v1/market-data/regime-breaks", json={"name": "dq-crash", "occurred_at": when}
        )
        assert again.status_code == 409
        for bad in ({"name": "", "occurred_at": when}, {"name": "x", "occurred_at": "2024-01-01"}):
            assert (
                await client.post("/api/v1/market-data/regime-breaks", json=bad)
            ).status_code == 422
        listed = (
            await client.get("/api/v1/market-data/regime-breaks", params={"symbol": SYMBOL})
        ).json()
        assert [b["name"] for b in listed if b["name"].startswith("dq-")] == ["dq-crash"]
        other = (
            await client.get("/api/v1/market-data/regime-breaks", params={"symbol": "ETH/USDT"})
        ).json()
        assert "dq-crash" not in [b["name"] for b in other]  # scoped to another symbol

        spec = {**BODY, "strategy_type": "ema_crossover", "allow_gaps": True}
        run_id = (await client.post("/api/v1/backtests", json=spec)).json()["id"]
        await _drain(runner)
        run = (await client.get(f"/api/v1/backtests/{run_id}")).json()
        assert run["status"] == "completed", run["error"]
        block = run["break_metrics"]
        assert [b["name"] for b in block["breaks"]] == ["dq-crash"]
        assert block["breaks"][0]["created_at"] <= run["created_at"]
        assert len(block["segments"]) == 2
        assert sum(s["candles"] for s in block["segments"]) == run["candles_count"]

        events = (
            await client.get("/api/v1/audit-events", params={"event_type": "regime_break.created"})
        ).json()
        assert any(e["entity_id"] == brk["id"] for e in events)

        assert (
            await client.delete(f"/api/v1/market-data/regime-breaks/{brk['id']}")
        ).status_code == 204
        assert (
            await client.delete(f"/api/v1/market-data/regime-breaks/{brk['id']}")
        ).status_code == 404
        # the finished run keeps its snapshot even after the break is gone
        again = (await client.get(f"/api/v1/backtests/{run_id}")).json()
        assert again["break_metrics"]["breaks"][0]["name"] == "dq-crash"
        none_run = (await client.post("/api/v1/backtests", json=spec)).json()["id"]
        await _drain(runner)
        assert (await client.get(f"/api/v1/backtests/{none_run}")).json()["break_metrics"] is None
    finally:
        async with container.engine.begin() as conn:
            await conn.execute(text("DELETE FROM regime_breaks WHERE name LIKE 'dq-%'"))
            await conn.execute(
                text("DELETE FROM audit_events WHERE event_type LIKE 'regime_break.%'")
            )


async def test_momentum_grid_endpoint_shape_corrected_level_and_validation(stack: Any) -> None:
    client, runner, _, _ = stack
    await _import(client, runner)
    params = {"symbol": SYMBOL, "timeframe": "1h", "start": BODY["start"], "end": BODY["end"]}
    found = await client.get(
        "/api/v1/market-data/momentum-grid",
        params={**params, "lookbacks": "1,5", "holdings": "1,5,10"},
    )
    assert found.status_code == 200, found.text
    body = found.json()
    assert len(body["cells"]) == 6 and body["candles"] > 100 and body["gaps"] >= 1
    assert abs(Decimal(body["alpha_corrected"]) - Decimal("0.05") / 6) < Decimal("1e-12")
    assert Decimal(body["critical_z"]) > Decimal("1.96") and "Descritivo" in body["warning"]
    first = body["cells"][0]
    assert {"lookback", "holding", "n", "correlation", "z_stat", "significant_corrected"} <= set(
        first
    )
    for bad in (
        {"lookbacks": "a,b"},
        {"lookbacks": ""},
        {"lookbacks": "0"},
        {
            "lookbacks": ",".join(str(i) for i in range(1, 12)),
            "holdings": ",".join(map(str, range(1, 12))),
        },
    ):
        resp = await client.get("/api/v1/market-data/momentum-grid", params={**params, **bad})
        assert resp.status_code == 422, bad
    inverted = {**params, "start": BODY["end"], "end": BODY["start"]}
    assert (
        await client.get("/api/v1/market-data/momentum-grid", params=inverted)
    ).status_code == 422


async def test_start_offset_sweep_shifts_each_run_and_is_not_a_robustness_axis(stack: Any) -> None:
    client, runner, _, _ = stack
    await _import(client, runner)
    spec = {**BODY, "strategy_type": "ema_crossover", "allow_gaps": True}
    sweep = await client.post(
        "/api/v1/backtests/sweeps", json={**spec, "grid": {"start_offset_days": [0, 3, 7]}}
    )
    assert sweep.status_code == 202, sweep.text
    body = sweep.json()
    assert body["run_count"] == 3 and body["robustness"] is None
    starts = sorted(r["start"] for r in body["runs"])
    first = datetime.fromisoformat(starts[0].replace("Z", "+00:00"))
    assert [(datetime.fromisoformat(s.replace("Z", "+00:00")) - first).days for s in starts] == [
        0,
        3,
        7,
    ]
    await _drain(runner)
    done = (await client.get(f"/api/v1/backtests/sweeps/{body['id']}")).json()
    assert done["completed"] == 3 and len(done["runs"]) == 3

    mixed = await client.post(
        "/api/v1/backtests/sweeps",
        json={
            **spec,
            "grid": {"fast_period": [3, 5], "slow_period": [13], "start_offset_days": [0, 2, 4]},
        },
    )
    assert mixed.status_code == 202 and mixed.json()["run_count"] == 6

    for bad in ([-1], [0, 0], list(range(26)), ["3"], [True], [], [4000]):
        resp = await client.post(
            "/api/v1/backtests/sweeps", json={**spec, "grid": {"start_offset_days": bad}}
        )
        assert resp.status_code == 422, bad
    plain = await client.post(
        "/api/v1/backtests/sweeps",
        json={**spec, "grid": {"fast_period": [3, 5], "slow_period": [13]}},
    )
    assert plain.status_code == 202 and len({r["start"] for r in plain.json()["runs"]}) == 1


async def test_the_slippage_model_is_stored_and_only_worsens_the_result(stack: Any) -> None:
    client, runner, _, _ = stack
    await _import(client, runner)
    base = {
        **BODY,
        "strategy_type": "ema_crossover",
        "strategy_params": {"fast_period": 3, "slow_period": 13},
        "allow_gaps": True,
    }
    plain = (await client.post("/api/v1/backtests", json=base)).json()
    assert plain["slippage_model"] == "fixed" and plain["slippage_k_range"] == "0"
    heavy = (
        await client.post(
            "/api/v1/backtests",
            json={
                **base,
                "slippage_model": "volatility_size",
                "slippage_k_range": "0.5",
                "slippage_k_size": "0.5",
            },
        )
    ).json()
    assert heavy["slippage_model"] == "volatility_size" and heavy["slippage_k_range"] == "0.5"
    await _drain(runner)
    runs = [(await client.get(f"/api/v1/backtests/{r['id']}")).json() for r in (plain, heavy)]
    assert [r["status"] for r in runs] == ["completed", "completed"], runs[0]["error"]
    assert Decimal(runs[1]["metrics"]["final_equity"]) <= Decimal(
        runs[0]["metrics"]["final_equity"]
    )
    assert runs[1]["slippage_model"] == "volatility_size"
    assert Decimal(runs[1]["slippage_k_size"]) == Decimal("0.5")  # the column keeps 18 decimals
    assert Decimal(runs[0]["slippage_k_range"]) == 0
    for bad in ({"slippage_k_range": "-1"}, {"slippage_model": "nope"}):
        assert (await client.post("/api/v1/backtests", json={**base, **bad})).status_code == 422


async def test_run_stores_the_adverse_excursion_of_its_trades(stack: Any) -> None:
    client, runner, _, _ = stack
    await _import(client, runner)
    spec = {
        **BODY,
        "strategy_type": "ema_crossover",
        "strategy_params": {"fast_period": 3, "slow_period": 13},
        "allow_gaps": True,
    }
    run_id = (await client.post("/api/v1/backtests", json=spec)).json()["id"]
    await _drain(runner)
    run = (await client.get(f"/api/v1/backtests/{run_id}")).json()
    assert run["status"] == "completed", run["error"]
    block = run["excursion"]
    assert block["trades"] == run["metrics"]["round_trips"] >= 1
    assert Decimal(block["worst_pct"]) >= Decimal(block["median_pct"]) >= 0
    assert Decimal(block["worst_pct"]) >= Decimal(block["p95_pct"]) >= Decimal(block["median_pct"])
    assert Decimal(block["worst_trades"][0]["pct"]) == Decimal(block["worst_pct"])


async def test_exposure_curve_endpoint_shape_errors_and_determinism(stack: Any) -> None:
    client, runner, _, _ = stack
    await _import(client, runner)
    spec = {
        **BODY,
        "strategy_type": "ema_crossover",
        "strategy_params": {"fast_period": 3, "slow_period": 13},
        "allow_gaps": True,
    }
    run_id = (await client.post("/api/v1/backtests", json=spec)).json()["id"]
    queued = (await client.post("/api/v1/backtests", json=spec)).json()["id"]
    assert (await client.get(f"/api/v1/backtests/{queued}/exposure-curve")).status_code == 409
    await _drain(runner)

    found = await client.get(f"/api/v1/backtests/{run_id}/exposure-curve", params={"steps": 4})
    assert found.status_code == 200, found.text
    body = found.json()
    assert [Decimal(p["fraction"]) for p in body["points"]] == [
        Decimal("0.25"),
        Decimal("0.5"),
        Decimal("0.75"),
        Decimal(1),
    ]
    drawdowns = [Decimal(p["max_drawdown_pct"]) for p in body["points"]]
    assert drawdowns == sorted(drawdowns)
    assert body["returns"] > 30 and body["bootstrap_returns"] is None
    assert any("teto" in w for w in body["warnings"]) and Decimal(body["configured_fraction"]) == 1
    assert all(p["bootstrap_p95"] is None for p in body["points"])

    boot_params = {"steps": 2, "bootstrap": "true", "simulations": 20, "seed": 3}
    first = (
        await client.get(f"/api/v1/backtests/{run_id}/exposure-curve", params=boot_params)
    ).json()
    again = (
        await client.get(f"/api/v1/backtests/{run_id}/exposure-curve", params=boot_params)
    ).json()
    assert first == again and first["bootstrap_returns"] > 0
    assert all(Decimal(p["bootstrap_p95"]) >= Decimal(p["bootstrap_p50"]) for p in first["points"])

    for bad in ({"steps": 0}, {"steps": 51}, {"simulations": 0}, {"simulations": 5000}):
        resp = await client.get(f"/api/v1/backtests/{run_id}/exposure-curve", params=bad)
        assert resp.status_code == 422, bad
    missing = await client.get(f"/api/v1/backtests/{uuid4()}/exposure-curve")
    assert missing.status_code == 404


@pytest.mark.parametrize(
    ("action", "desired", "budget_event"), [("stop", "stopped", True), ("pause", "paused", False)]
)
async def test_a_drawdown_breach_stops_or_pauses_as_configured(
    env: Env, action: str, desired: str, budget_event: bool
) -> None:
    runner = env.make_runner()
    risk = {"max_daily_loss_pct": None, "max_drawdown_pct": "10", "drawdown_action": action}
    bot_id = await env.create_bot(risk=risk)
    assert (await env.bot(bot_id))["risk"]["drawdown_action"] == action
    assert (await env.command(bot_id, "start")).status_code == 202
    await runner.run_once()
    await env.run_until(runner, 40)  # the price falls from 130 to 100 at hour 26: about -23%

    bot = await env.bot(bot_id)
    assert bot["desired_state"] == desired and bot["observed_state"] == desired
    events = await env.audit_types(bot_id)
    assert "risk.drawdown_breached" in events
    assert ("risk.budget_exhausted" in events) is budget_event
    portfolio = (await env.http.get(f"/api/v1/bots/{bot_id}/portfolio")).json()
    assert portfolio["quantity"] is not None  # the position is kept either way


async def test_only_usdt_pairs_are_offered_and_accepted(stack: Any) -> None:
    client, _, _, _ = stack
    offered = (await client.get("/api/v1/market-data/symbols")).json()
    assert offered and all(item["quote"] == "USDT" for item in offered)
    assert {"BTC/USDT", "ETH/USDT"} <= {item["symbol"] for item in offered}

    window = {"start": START.isoformat(), "end": END.isoformat()}
    other_quote = {"symbol": "ETH/BTC", **window}
    assert (await client.post("/api/v1/market-data/imports", json=other_quote)).status_code == 422
    backtest = {"strategy_type": "ema_crossover", **other_quote}
    assert (await client.post("/api/v1/backtests", json=backtest)).status_code == 422
    bot = {"name": "x", "strategy_type": "ema_crossover", "symbol": "ETH/BTC"}
    assert (await client.post("/api/v1/bots", json=bot)).status_code == 422
