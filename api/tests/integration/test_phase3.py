"""Phase 3 against real PostgreSQL: protective exits, risk circuit breakers, global limits,
exchange defaults, system status and the bots overview. Hourly EMA 2/3 bots on simulated prices.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from harness import START, Env

pytestmark = pytest.mark.integration

STOP_PARAMS = {"fast_period": 2, "slow_period": 3, "stop_loss_pct": 1}


async def test_stop_loss_exits_at_the_stop_before_any_strategy_signal(env: Env) -> None:
    # BUY at hour 23 (close 110) -> stop = 110 * 0.99 = 108.9; hour 24 trades at 108.
    runner = env.make_runner(path={23: 110, 24: 108})
    bot_id = await env.create_bot(strategy_params=STOP_PARAMS)
    await env.command(bot_id, "start")
    await runner.run_once()

    await env.run_until(runner, 24)  # processes the BUY candle
    portfolio = (await env.http.get(f"/api/v1/bots/{bot_id}/portfolio")).json()
    assert Decimal(portfolio["stop_price"]) == Decimal("108.9")
    assert portfolio["take_profit_price"] is None

    await env.run_until(runner, 30)
    buy, sell = await env.orders(bot_id)
    assert (buy["side"], sell["side"], sell["status"]) == ("buy", "sell", "FILLED")
    assert sell["bar_time"] == (START + timedelta(hours=24)).isoformat().replace("+00:00", "Z")
    assert Decimal(sell["avg_fill_price"]) == Decimal(108) * Decimal("0.9995")  # gap: open, slipped

    signals = await env.signals(bot_id)
    assert [s["side"] for s in signals] == ["buy", "sell"]
    assert signals[1]["reason"].startswith("stop_loss triggered")
    assert "order.filled" in await env.audit_types(bot_id)

    after = (await env.http.get(f"/api/v1/bots/{bot_id}/portfolio")).json()
    assert Decimal(after["quantity"]) == 0 and after["stop_price"] is None


async def test_take_profit_exits_at_the_target_without_slippage(env: Env) -> None:
    runner = env.make_runner(path={23: 110, 24: 120})
    params = {"fast_period": 2, "slow_period": 3, "take_profit_pct": 5}  # target 115.5
    bot_id = await env.create_bot(strategy_params=params)
    await env.command(bot_id, "start")
    await runner.run_once()
    await env.run_until(runner, 30)

    _, sell = await env.orders(bot_id)
    assert sell["side"] == "sell" and Decimal(sell["avg_fill_price"]) == Decimal("115.5")
    assert (await env.signals(bot_id))[1]["reason"].startswith("take_profit triggered")


async def test_entries_without_a_required_stop_are_rejected(env: Env) -> None:
    runner = env.make_runner()
    bot_id = await env.create_bot(risk={"require_stop_loss": True, "max_daily_loss_pct": None})
    await env.command(bot_id, "start")
    await runner.run_once()
    await env.run_until(runner, 30)

    assert await env.orders(bot_id) == []
    (signal,) = await env.signals(bot_id)
    assert signal["decision"] == "rejected"
    assert "stop-loss is required" in signal["decision_reason"]


async def test_consecutive_losses_pause_the_bot(env: Env) -> None:
    runner = env.make_runner()  # default path: one losing round trip (110 -> 100)
    bot_id = await env.create_bot(risk={"max_consecutive_losses": 1, "max_daily_loss_pct": None})
    await env.command(bot_id, "start")
    await runner.run_once()
    await env.run_until(runner, 40)

    bot = await env.bot(bot_id)
    assert (bot["desired_state"], bot["observed_state"]) == ("paused", "paused")
    assert bot["last_error"] == "max consecutive losses reached"
    assert "risk.consecutive_losses" in await env.audit_types(bot_id)


async def test_drawdown_limit_pauses_the_bot(env: Env) -> None:
    runner = env.make_runner()
    bot_id = await env.create_bot(risk={"max_drawdown_pct": 5, "max_daily_loss_pct": None})
    await env.command(bot_id, "start")
    await runner.run_once()
    await env.run_until(runner, 40)

    bot = await env.bot(bot_id)
    assert bot["observed_state"] == "paused"
    assert bot["last_error"] == "max drawdown limit breached"
    assert "risk.drawdown_breached" in await env.audit_types(bot_id)


async def test_global_limit_of_open_positions_applies_across_bots(env: Env) -> None:
    runner = env.make_runner(risk_max_open_positions=1)
    first = await env.create_bot()
    second = await env.create_bot()
    for bot_id in (first, second):
        await env.command(bot_id, "start")
    await runner.run_once()
    await env.run_until(runner, 25)  # both bots get the same BUY signal at hour 23

    orders = {bot_id: await env.orders(bot_id) for bot_id in (first, second)}
    assert len(orders[first]) == 1 and orders[second] == []  # the first bot took the only slot
    (blocked,) = await env.signals(second)
    assert blocked["decision"] == "rejected"
    assert "global limit of open positions" in blocked["decision_reason"]


async def test_exchange_defaults_and_validation(env: Env) -> None:
    bot_id = await env.create_bot()
    bot = await env.bot(bot_id)
    assert bot["exchange"] == "binance"
    assert Decimal(bot["fee_rate"]) == Decimal("0.001")  # the exchange's taker fee

    custom = await env.create_bot(fee_rate="0.00075")
    assert Decimal((await env.bot(custom))["fee_rate"]) == Decimal("0.00075")

    body = {"name": "itest-unknown-exchange", "strategy_type": "ema_crossover", "exchange": "ftx"}
    created = await env.http.post("/api/v1/bots", json=body)
    assert created.status_code == 422 and "unknown or disabled exchange" in created.json()["detail"]

    window = {"start": "2024-01-01T00:00:00Z", "end": "2024-01-02T00:00:00Z"}
    backtest = {"strategy_type": "ema_crossover", "exchange": "ftx", **window}
    assert (await env.http.post("/api/v1/backtests", json=backtest)).status_code == 422
    imports = {"exchange": "ftx", **window}
    assert (await env.http.post("/api/v1/market-data/imports", json=imports)).status_code == 422


async def test_overview_compares_bots_side_by_side(env: Env) -> None:
    runner = env.make_runner()
    winner_ish = await env.create_bot()
    idle = await env.create_bot()
    await env.command(winner_ish, "start")
    await runner.run_once()
    await env.run_until(runner, 40)

    overview = {row["id"]: row for row in (await env.http.get("/api/v1/bots/overview")).json()}
    traded, untouched = overview[winner_ish], overview[idle]
    assert Decimal(traded["return_pct"]) < 0 and traded["in_position"] is False
    assert Decimal(traded["fees_paid"]) > 0
    assert Decimal(untouched["return_pct"]) == 0 and untouched["observed_state"] == "stopped"


async def test_status_reports_worker_liveness_and_stale_bots(env: Env) -> None:
    runner = env.make_runner()
    bot_id = await env.create_bot()
    await env.command(bot_id, "start")
    await runner.run_once()
    status_service = env.containers[-1].status  # same (simulated) clock as the worker

    fresh = await status_service.system_status()
    assert fresh.worker.alive and fresh.stale_bots == []
    assert fresh.bots_by_state.get("running", 0) >= 1 and fresh.exchanges == ["binance"]

    env.clock.advance(minutes=5)  # the worker stops advancing
    stale = await status_service.system_status()
    assert not stale.worker.alive
    assert bot_id in {b.bot_id for b in stale.stale_bots}

    api = (await env.http.get("/api/v1/system/status")).json()  # shape of the HTTP contract
    assert set(api) == {
        "worker",
        "kill_switch",
        "bots_by_state",
        "stale_bots",
        "exchanges",
        "unprotected_positions",  # book 1 ch. 4
        "clock",
        "backup",
    }
