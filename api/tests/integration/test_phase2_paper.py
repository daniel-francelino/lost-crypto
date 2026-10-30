"""End-to-end paper trading against a real PostgreSQL (migrations applied).

The API is real; time and the exchange are simulated: a settable clock and a deterministic price
path. Prices (EMA 2/3 bot, hourly): flat 100, then 110/120/130 (cross up at hour 23 -> BUY) and
100/80/60 (cross down at hour 26 -> SELL).
"""

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import text

from container import Container, JobRunner, build_container, build_job_runner
from core.config import Settings
from factories import MARKET
from main import create_app
from modules.market_data.domain.models import Candle, MarketInfo, Timeframe

pytestmark = pytest.mark.integration

START = datetime(2024, 1, 1, tzinfo=UTC)
SYMBOL = "TST/USDT"
PATH = {23: 110, 24: 120, 25: 130, 26: 100, 27: 80, 28: 60}


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self.current = now

    def now(self) -> datetime:
        return self.current

    def advance(self, **kwargs: float) -> None:
        self.current += timedelta(**kwargs)


class PathSource:
    """Deterministic market: price(h) for the candle opening at START + h hours."""

    def __init__(self, clock: FakeClock) -> None:
        self.clock = clock

    @staticmethod
    def price(hour: int) -> Decimal:
        return Decimal(PATH.get(hour, 60 if hour > 28 else 100))

    async def fetch_candles(
        self, symbol: str, timeframe: Timeframe, since: datetime, limit: int
    ) -> list[Candle]:
        out: list[Candle] = []
        t = since
        while len(out) < limit and t <= self.clock.now():  # includes the in-progress candle
            close = self.price(int((t - START).total_seconds() // 3600))
            out.append(Candle(symbol, timeframe, t, close, close, close, close, Decimal(1)))
            t += timeframe.delta
        return out

    async def fetch_market_info(self, symbol: str) -> MarketInfo:
        return MARKET


class BrokenSource(PathSource):
    async def fetch_candles(self, *args: Any, **kwargs: Any) -> list[Candle]:
        raise ConnectionError("exchange unreachable")


@dataclass
class Env:
    http: httpx.AsyncClient
    clock: FakeClock
    make_runner: Callable[[type[PathSource]], JobRunner]

    async def create_bot(self, **overrides: Any) -> str:
        body = {
            "name": f"itest-{uuid4().hex[:8]}",
            "strategy_type": "ema_crossover",
            "strategy_params": {"fast_period": 2, "slow_period": 3},
            "symbol": SYMBOL,
            "timeframe": "1h",
            "initial_capital": "1000",
            "risk": {"max_daily_loss_pct": None},
            **overrides,
        }
        resp = await self.http.post("/api/v1/bots", json=body)
        assert resp.status_code == 201, resp.text
        return str(resp.json()["id"])

    async def command(self, bot_id: str, name: str) -> httpx.Response:
        return await self.http.post(f"/api/v1/bots/{bot_id}/{name}")

    async def bot(self, bot_id: str) -> dict[str, Any]:
        return dict((await self.http.get(f"/api/v1/bots/{bot_id}")).json())

    async def orders(self, bot_id: str) -> list[dict[str, Any]]:
        resp = await self.http.get(f"/api/v1/bots/{bot_id}/orders")
        return list(reversed(resp.json()))  # oldest first

    async def run_until(self, runner: JobRunner, hours_after_start: int) -> None:
        """Advance the clock hour by hour (5s after each close) running the worker each step."""
        target = START + timedelta(hours=hours_after_start, seconds=5)
        while self.clock.now() < target:
            self.clock.advance(hours=1)
            await runner.run_once()


async def _cleanup(container: Container) -> None:
    async with container.engine.begin() as conn:
        bots = "(SELECT id FROM bots WHERE name LIKE 'itest-%')"
        statements = [
            "DELETE FROM order_fills WHERE order_id IN "
            f"(SELECT id FROM orders WHERE bot_id IN {bots})",
            f"DELETE FROM orders WHERE bot_id IN {bots}",
            f"DELETE FROM trading_signals WHERE bot_id IN {bots}",
            f"DELETE FROM portfolio_snapshots WHERE bot_id IN {bots}",
            f"DELETE FROM bot_portfolios WHERE bot_id IN {bots}",
            f"DELETE FROM trading_sessions WHERE bot_id IN {bots}",
            f"DELETE FROM audit_events WHERE bot_id IN {bots}",
            "DELETE FROM bots WHERE name LIKE 'itest-%'",
            "DELETE FROM system_flags WHERE key = 'kill_switch'",
        ]
        for statement in statements:
            await conn.execute(text(statement))


@pytest.fixture
async def env() -> AsyncIterator[Env]:
    settings = Settings()  # type: ignore[call-arg]
    clock = FakeClock(START + timedelta(hours=20, seconds=5))
    app = create_app(settings)
    containers: list[Container] = []

    def make_runner(source_cls: type[PathSource] = PathSource) -> JobRunner:
        container = build_container(settings, clock=clock)
        containers.append(container)
        return build_job_runner(container, source_cls(clock))

    async with app.router.lifespan_context(app):
        api_container: Container = app.state.container
        await _cleanup(api_container)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
            yield Env(http, clock, make_runner)
        await _cleanup(api_container)
    for container in containers:
        await container.engine.dispose()


async def test_bot_trades_and_every_record_is_consistent(env: Env) -> None:
    runner = env.make_runner(PathSource)
    bot_id = await env.create_bot()
    assert (await env.command(bot_id, "start")).status_code == 202
    await runner.run_once()  # starts the session and warms the strategy up
    assert (await env.bot(bot_id))["observed_state"] == "running"

    await env.run_until(runner, 40)

    buy, sell = await env.orders(bot_id)
    assert (buy["side"], buy["status"], sell["side"], sell["status"]) == (
        "buy",
        "FILLED",
        "sell",
        "FILLED",
    )
    assert Decimal(buy["avg_fill_price"]) == Decimal(110) * Decimal("1.0005")  # 5 bps slippage
    assert Decimal(sell["avg_fill_price"]) == Decimal(100) * Decimal("0.9995")

    portfolio = (await env.http.get(f"/api/v1/bots/{bot_id}/portfolio")).json()
    assert Decimal(portfolio["quantity"]) == 0
    cash = Decimal(portfolio["cash"])
    assert cash < Decimal(1000)  # lost on this path, fees included
    assert Decimal(portfolio["equity"]) == cash
    assert Decimal(portfolio["realized_pnl"]) == cash - Decimal(1000)  # flat: pnl == cash change
    assert Decimal(portfolio["fees_paid"]) > 0

    perf = (await env.http.get(f"/api/v1/bots/{bot_id}/performance")).json()
    assert perf["round_trips"] == 1 and perf["fills"] == 2
    assert Decimal(perf["final_equity"]) == cash.quantize(Decimal("0.00000001"))

    signals = (await env.http.get(f"/api/v1/bots/{bot_id}/signals")).json()
    assert {s["decision"] for s in signals} == {"approved"} and len(signals) == 2
    equity = (await env.http.get(f"/api/v1/bots/{bot_id}/equity")).json()
    assert len(equity) == 20  # one snapshot per fresh candle closed after the session start

    events = (await env.http.get("/api/v1/audit-events", params={"bot_id": bot_id})).json()
    types = [e["event_type"] for e in events]
    for expected in ("bot.created", "bot.start_requested", "bot.started", "order.filled"):
        assert expected in types
    assert types.count("order.filled") == 2


async def test_rerunning_the_worker_never_duplicates_orders(env: Env) -> None:
    runner = env.make_runner(PathSource)
    bot_id = await env.create_bot()
    await env.command(bot_id, "start")
    await runner.run_once()
    await env.run_until(runner, 25)
    before = await env.orders(bot_id)
    assert len(before) == 1
    for _ in range(5):  # same clock: nothing new is due
        await runner.run_once()
    assert await env.orders(bot_id) == before


async def test_restarted_worker_resumes_without_duplicates_or_lost_state(env: Env) -> None:
    first = env.make_runner(PathSource)
    bot_id = await env.create_bot()
    await env.command(bot_id, "start")
    await first.run_once()
    await env.run_until(first, 25)  # BUY placed, then "crash"
    assert [o["side"] for o in await env.orders(bot_id)] == ["buy"]

    second = env.make_runner(PathSource)  # brand-new process: only the database survives
    await second.recover()
    await env.run_until(second, 40)

    assert [o["side"] for o in await env.orders(bot_id)] == ["buy", "sell"]


async def test_stale_signals_are_recorded_but_never_traded(env: Env) -> None:
    runner = env.make_runner(PathSource)
    bot_id = await env.create_bot()
    await env.command(bot_id, "start")
    await runner.run_once()
    env.clock.advance(hours=8)  # worker "was down": candles 20..27 arrive in one go
    await runner.run_once()

    assert await env.orders(bot_id) == []
    signals = (await env.http.get(f"/api/v1/bots/{bot_id}/signals")).json()
    assert [(s["side"], s["decision"]) for s in signals] == [("buy", "discarded_stale")]
    equity = (await env.http.get(f"/api/v1/bots/{bot_id}/equity")).json()
    assert len(equity) == 1  # only the fresh candle is snapshotted


async def test_pause_resume_and_stop(env: Env) -> None:
    runner = env.make_runner(PathSource)
    bot_id = await env.create_bot()
    await env.command(bot_id, "start")
    await runner.run_once()
    await env.command(bot_id, "pause")
    await runner.run_once()
    assert (await env.bot(bot_id))["observed_state"] == "paused"

    await env.command(bot_id, "start")  # resume keeps the same session
    await runner.run_once()
    assert (await env.bot(bot_id))["observed_state"] == "running"

    await env.run_until(runner, 24)  # BUY executed
    assert (await env.command(bot_id, "stop")).status_code == 202
    await runner.run_once()
    stopped = await env.bot(bot_id)
    assert (stopped["desired_state"], stopped["observed_state"]) == ("stopped", "stopped")
    portfolio = (await env.http.get(f"/api/v1/bots/{bot_id}/portfolio")).json()
    assert Decimal(portfolio["quantity"]) > 0  # the position survives the stop

    events = (await env.http.get("/api/v1/audit-events", params={"bot_id": bot_id})).json()
    types = {e["event_type"] for e in events}
    assert {"bot.paused", "bot.resumed", "bot.stopped"} <= types

    assert (await env.http.post(f"/api/v1/bots/{bot_id}/reset-portfolio")).status_code == 204
    reset = (await env.http.get(f"/api/v1/bots/{bot_id}/portfolio")).json()
    assert Decimal(reset["quantity"]) == 0 and Decimal(reset["cash"]) == Decimal(1000)


async def test_kill_switch_pauses_running_bots_and_blocks_new_entries(env: Env) -> None:
    runner = env.make_runner(PathSource)
    bot_id = await env.create_bot()
    await env.command(bot_id, "start")
    await runner.run_once()

    resp = await env.http.put("/api/v1/system/kill-switch", json={"active": True, "reason": "test"})
    assert resp.json()["active"] is True
    await runner.run_once()
    bot = await env.bot(bot_id)
    assert (bot["desired_state"], bot["observed_state"]) == ("paused", "paused")
    events = (await env.http.get("/api/v1/audit-events", params={"bot_id": bot_id})).json()
    assert "bot.paused_by_kill_switch" in {e["event_type"] for e in events}

    released = await env.http.put("/api/v1/system/kill-switch", json={"active": False})
    assert released.json()["active"] is False
    assert (await env.bot(bot_id))["observed_state"] == "paused"  # not resumed automatically


async def test_daily_loss_limit_pauses_the_bot(env: Env) -> None:
    runner = env.make_runner(PathSource)
    bot_id = await env.create_bot(risk={"max_daily_loss_pct": "5"})
    await env.command(bot_id, "start")
    await runner.run_once()
    await env.run_until(runner, 40)

    bot = await env.bot(bot_id)
    assert (bot["desired_state"], bot["observed_state"]) == ("paused", "paused")
    assert bot["last_error"] == "daily loss limit breached"
    events = (await env.http.get("/api/v1/audit-events", params={"bot_id": bot_id})).json()
    assert "risk.daily_loss_breached" in {e["event_type"] for e in events}


async def test_repeated_failures_put_the_bot_in_error_instead_of_looping_forever(
    env: Env,
) -> None:
    runner = env.make_runner(BrokenSource)
    bot_id = await env.create_bot()
    await env.command(bot_id, "start")
    for _ in range(6):
        env.clock.advance(minutes=2)  # past the exponential backoff
        await runner.run_once()

    bot = await env.bot(bot_id)
    assert (bot["desired_state"], bot["observed_state"]) == ("paused", "error")
    assert "exchange unreachable" in bot["last_error"]
    events = (await env.http.get("/api/v1/audit-events", params={"bot_id": bot_id})).json()
    assert "bot.error" in {e["event_type"] for e in events}


async def test_api_validation_and_state_rules(env: Env) -> None:
    http = env.http
    bot_id = await env.create_bot(name="itest-fixed-name")

    duplicate = {"name": "itest-fixed-name", "strategy_type": "ema_crossover"}
    assert (await http.post("/api/v1/bots", json=duplicate)).status_code == 409
    bad_params = {"name": "itest-bad", "strategy_type": "ema_crossover"}
    bad_params["strategy_params"] = {"fast_period": 30, "slow_period": 10}  # type: ignore[assignment]
    assert (await http.post("/api/v1/bots", json=bad_params)).status_code == 422
    unknown = {"name": "itest-unknown", "strategy_type": "nope"}
    assert (await http.post("/api/v1/bots", json=unknown)).status_code == 422
    live = {"name": "itest-live", "strategy_type": "ema_crossover", "mode": "live"}
    assert (await http.post("/api/v1/bots", json=live)).status_code == 422  # live is unavailable
    missing = "00000000-0000-0000-0000-000000000000"
    assert (await http.get(f"/api/v1/bots/{missing}")).status_code == 404

    assert (await env.command(bot_id, "pause")).status_code == 409  # not running
    assert (await env.command(bot_id, "stop")).status_code == 409  # already stopped
    patched = await http.patch(f"/api/v1/bots/{bot_id}", json={"initial_capital": "2500"})
    assert patched.status_code == 200 and patched.json()["config_version"] == 2

    await env.command(bot_id, "start")
    assert (await env.command(bot_id, "start")).status_code == 409  # already running
    assert (await http.patch(f"/api/v1/bots/{bot_id}", json={"name": "x"})).status_code == 409
