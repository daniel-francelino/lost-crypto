"""Book 1 ch. 5 (execution systems) against a real PostgreSQL: the bot keeps the candles it saw
and the price it decided at, its paper session replays through the backtester with no
unexplained difference, a seeded difference is caught, and a backtest can size like the bot."""

from decimal import Decimal
from typing import Any

import pytest
from harness import SYMBOL, Env, PathSource
from sqlalchemy import text

pytestmark = pytest.mark.integration


async def _paper_bot(env: Env) -> tuple[Any, str]:
    runner = env.make_runner(PathSource)
    bot = await env.create_bot()
    assert (await env.command(bot, "start")).status_code == 202
    await runner.run_once()
    await env.run_until(runner, 40)
    return runner, bot


async def _parity(env: Env, runner: Any, bot: str) -> dict[str, Any]:
    assert (await env.http.post(f"/api/v1/bots/{bot}/parity")).status_code == 202
    await runner.run_once()
    parity: dict[str, Any] = (await env.http.get(f"/api/v1/bots/{bot}/parity")).json()
    assert parity["status"] == "completed", parity["error"]
    return parity


async def test_paper_session_records_execution_and_matches_its_replay(env: Env) -> None:
    runner, bot = await _paper_bot(env)
    engine = env.containers[-1].engine

    async with engine.connect() as conn:
        stored = await conn.scalar(
            text("SELECT count(*) FROM candles WHERE symbol = :s"), {"s": SYMBOL}
        )
    assert stored and stored >= 40  # warm-up and session candles, as the bot saw them

    orders = (await env.http.get(f"/api/v1/bots/{bot}/orders")).json()
    assert orders and all(o["reference_price"] for o in orders)
    assert {Decimal(o["slippage_bps"]) for o in orders} == {Decimal("5.00")}  # paper = assumed
    quality = (await env.http.get(f"/api/v1/bots/{bot}/execution-quality")).json()
    assert quality["by_type"]["market"]["slippage_bps"]["mean"] == "5.00"
    assert quality["above_configured"] is False

    parity = await _parity(env, runner, bot)
    summary = parity["summary"]
    assert parity["unexplained"] == 0, summary["differences"]
    assert summary["verdict"] == "consistent" and summary["counts"]["match"] >= 2
    assert summary["bot_return_pct"] == summary["replay_return_pct"]
    assert summary["replay_equity"]

    steps = (await env.http.get(f"/api/v1/bots/{bot}/divergence")).json()
    assert [s["key"] for s in steps] == [
        "bugs", "trades", "costs", "liquidity", "snooping", "regime",
    ]  # fmt: skip
    assert steps[0]["state"] == "ok" and steps[2]["state"] == "ok"

    # Seed a divergence: the bot "forgets" a trade it made. The replay still makes it.
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "DELETE FROM trading_signals WHERE id = (SELECT id FROM trading_signals "
                "WHERE bot_id = :b AND decision = 'approved' ORDER BY bar_time LIMIT 1)"
            ),
            {"b": bot},
        )
    seeded = await _parity(env, runner, bot)
    assert seeded["unexplained"] >= 1
    assert seeded["summary"]["verdict"] == "differences"
    assert any(d["kind"] == "unexplained" for d in seeded["summary"]["differences"])
    steps = (await env.http.get(f"/api/v1/bots/{bot}/divergence")).json()
    assert steps[0]["state"] == "attention"


async def test_a_backtest_can_size_and_time_like_the_bot(env: Env) -> None:
    runner, _ = await _paper_bot(env)  # its stored candles feed the backtest
    candles = (
        await env.http.get(
            "/api/v1/market-data/coverage", params={"symbol": SYMBOL, "timeframe": "1h"}
        )
    ).json()
    assert candles["count"] > 0
    spec = {
        "symbol": SYMBOL,
        "timeframe": "1h",
        "start": candles["first"],
        "end": candles["last"],
        "strategy_type": "ema_crossover",
        "strategy_params": {"fast_period": 2, "slow_period": 3},
        "allow_gaps": True,
        "fill_timing": "signal_close",
        "risk": {"max_position_fraction": "0.5", "max_daily_loss_pct": None},
    }
    created = await env.http.post("/api/v1/backtests", json=spec)
    assert created.status_code == 202, created.text
    await runner.run_once()
    run = (await env.http.get(f"/api/v1/backtests/{created.json()['id']}")).json()
    assert run["status"] == "completed", run["error"]
    assert run["fill_timing"] == "signal_close"
    assert Decimal(run["risk"]["max_position_fraction"]) == Decimal("0.5")
    assert run["risk_report"]["sizing"] == "risk_limits"

    plain = await env.http.post("/api/v1/backtests", json={**spec, "risk": None})
    await runner.run_once()
    plain_run = (await env.http.get(f"/api/v1/backtests/{plain.json()['id']}")).json()
    assert plain_run["risk_report"]["sizing"] == "all_in"
    assert plain_run["risk"] is None
