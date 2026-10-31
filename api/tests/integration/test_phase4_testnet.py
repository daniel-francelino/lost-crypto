"""Phase 4 end to end: credentials, real-exchange order lifecycle, reconciliation, native stops.

The API, database, vault and worker are real; the exchange is a simulated account that honours
the ``Exchange`` contract and can be made to time out, reject or revoke credentials. Hourly EMA
2/3 bots on the standard price path: BUY at hour 23, SELL at hour 26.
"""

from collections import Counter
from decimal import Decimal
from typing import Any

import pytest
from harness import API_KEY, API_SECRET, START, TestnetEnv
from sqlalchemy import text

pytestmark = pytest.mark.integration

STOP_PARAMS = {"fast_period": 2, "slow_period": 3, "stop_loss_pct": 5}


def _shape(orders: list[dict[str, Any]]) -> Counter[tuple[str, str, str]]:
    return Counter((o["order_type"], o["side"], o["status"]) for o in orders)


async def _started(env: TestnetEnv, runner: Any, **bot_overrides: Any) -> tuple[str, str]:
    connection = await env.create_connection()
    bot = await env.create_testnet_bot(connection, **bot_overrides)
    await env.command(bot, "start")
    await runner.run_once()
    return connection, bot


# --- credentials ------------------------------------------------------------------------------


async def test_credentials_are_stored_encrypted_and_never_returned(testnet_env: TestnetEnv) -> None:
    env = testnet_env
    assert env.anonymous is not None and env.api_container is not None
    body = {"label": "itest-secrets", "api_key": API_KEY, "api_secret": API_SECRET}

    created = await env.http.post("/api/v1/exchange-connections", json=body)
    assert created.status_code == 201
    assert API_KEY not in created.text and API_SECRET not in created.text
    connection = created.json()
    assert connection["api_key_hint"] == "...1234" and connection["status"] == "active"

    for response in (
        await env.http.get("/api/v1/exchange-connections"),
        await env.http.get(f"/api/v1/exchange-connections/{connection['id']}"),
        await env.http.get("/api/v1/audit-events"),  # the creation event must not leak either
    ):
        assert API_KEY not in response.text and API_SECRET not in response.text

    async with env.api_container.engine.connect() as conn:
        stored = (
            await conn.execute(
                text("SELECT credentials_encrypted FROM exchange_connections WHERE id = :i"),
                {"i": connection["id"]},
            )
        ).scalar_one()
    assert API_KEY.encode() not in bytes(stored) and API_SECRET.encode() not in bytes(stored)

    assert (await env.http.post("/api/v1/exchange-connections", json=body)).status_code == 409
    assert (await env.anonymous.get("/api/v1/exchange-connections")).status_code == 401
    assert (await env.anonymous.post("/api/v1/exchange-connections", json=body)).status_code == 401


async def test_testnet_bots_must_use_a_valid_active_connection(testnet_env: TestnetEnv) -> None:
    env = testnet_env
    base = {"name": "itest-validation", "strategy_type": "ema_crossover", "symbol": "TST/USDT"}

    no_connection = await env.http.post("/api/v1/bots", json={**base, "mode": "testnet"})
    assert no_connection.status_code == 422 and "connection" in no_connection.json()["detail"]
    unknown = {**base, "mode": "testnet", "connection_id": "00000000-0000-0000-0000-000000000000"}
    assert (await env.http.post("/api/v1/bots", json=unknown)).status_code == 422
    connection = await env.create_connection()
    paper_with_connection = {**base, "mode": "paper", "connection_id": connection}
    assert (await env.http.post("/api/v1/bots", json=paper_with_connection)).status_code == 422

    await env.http.post(f"/api/v1/exchange-connections/{connection}/disable")
    disabled = {**base, "mode": "testnet", "connection_id": connection}
    response = await env.http.post("/api/v1/bots", json=disabled)
    assert response.status_code == 422 and "disabled" in response.json()["detail"]


async def test_testnet_bots_need_the_explicit_worker_opt_in(testnet_env: TestnetEnv) -> None:
    env = testnet_env
    runner = env.make_runner(testnet_trading_enabled=False)
    _, bot = await _started(env, runner)

    state = await env.bot(bot)
    assert (state["desired_state"], state["observed_state"]) == ("paused", "error")
    assert "TESTNET_TRADING_ENABLED" in state["last_error"]
    await env.run_until(runner, 30)
    assert env.sim is not None and env.sim.create_calls == []


# --- the order lifecycle ----------------------------------------------------------------------


async def test_a_testnet_bot_trades_and_its_books_match_the_exchange(
    testnet_env: TestnetEnv,
) -> None:
    env = testnet_env
    assert env.sim is not None
    runner = env.make_runner()
    connection, bot = await _started(env, runner)
    await env.run_until(runner, 40)

    orders = await env.orders(bot)
    assert _shape(orders) == Counter(
        {("market", "buy", "FILLED"): 1, ("market", "sell", "FILLED"): 1}
    )
    assert all(o["exchange_order_id"] for o in orders)

    portfolio = await env.portfolio(bot)
    assert Decimal(portfolio["quantity"]) == 0 and Decimal(portfolio["reserved_cash"]) == 0
    # The bot's cash moved exactly like the exchange account's quote balance.
    assert Decimal(portfolio["cash"]) - 1000 == env.sim.balances["USDT"] - 100_000
    # Fees were paid in the base asset on the buy and in USDT on the sell.
    performance = (await env.http.get(f"/api/v1/bots/{bot}/performance")).json()
    assert Decimal(performance["fees_paid"]) > 0 and performance["round_trips"] == 1

    assert sorted(env.sim.create_calls) == sorted({*env.sim.create_calls})  # each id sent once
    assert len(env.sim.create_calls) == 2
    runs = await env.reconciliations(connection)
    assert runs and {status for status, _ in runs} == {"ok"}
    assert {"order.intent", "order.filled", "position.dust_written_off"} <= await env.audit_types(
        bot
    )


async def test_an_exchange_rejection_releases_the_reservation(testnet_env: TestnetEnv) -> None:
    env = testnet_env
    assert env.sim is not None
    runner = env.make_runner()
    env.sim.fail_next("create", "reject")
    _, bot = await _started(env, runner)
    await env.run_until(runner, 25)

    (order,) = await env.orders(bot)
    assert order["status"] == "REJECTED"
    portfolio = await env.portfolio(bot)
    assert Decimal(portfolio["reserved_cash"]) == 0 and Decimal(portfolio["quantity"]) == 0
    assert (await env.bot(bot))["observed_state"] == "running"  # a refusal is not an outage


async def test_a_timeout_after_the_exchange_accepted_the_order_never_duplicates_it(
    testnet_env: TestnetEnv,
) -> None:
    env = testnet_env
    assert env.sim is not None
    runner = env.make_runner()
    env.sim.fail_next("create", "timeout_after")
    _, bot = await _started(env, runner)
    await env.run_until(runner, 24)  # the BUY candle: the call "times out"

    (order,) = await env.orders(bot)
    assert order["status"] == "UNKNOWN"
    held = await env.portfolio(bot)
    assert Decimal(held["reserved_cash"]) > 0 and Decimal(held["quantity"]) == 0

    await runner.run_once()  # reconciliation looks the client id up and finds it filled
    (order,) = await env.orders(bot)
    assert order["status"] == "FILLED"
    settled = await env.portfolio(bot)
    assert Decimal(settled["reserved_cash"]) == 0 and Decimal(settled["quantity"]) > 0
    assert env.sim.create_calls.count(order["client_order_id"]) == 1  # sent once, never again


async def test_a_timeout_that_never_reached_the_exchange_is_aborted_after_the_wait(
    testnet_env: TestnetEnv,
) -> None:
    env = testnet_env
    assert env.sim is not None
    runner = env.make_runner()
    env.sim.fail_next("create", "timeout_before")
    _, bot = await _started(env, runner)
    await env.run_until(runner, 24)

    await runner.run_once()
    assert (await env.orders(bot))[0]["status"] == "UNKNOWN"  # not found yet, but too early to say

    env.clock.advance(seconds=31)  # past RECONCILE_ABSENT_AFTER_SECONDS
    await runner.run_once()
    (order,) = await env.orders(bot)
    assert order["status"] == "REJECTED"
    portfolio = await env.portfolio(bot)
    assert Decimal(portfolio["reserved_cash"]) == 0 and Decimal(portfolio["quantity"]) == 0
    assert env.sim.create_calls == [order["client_order_id"]]  # never re-sent behind our back


async def test_a_new_signal_is_not_acted_on_while_an_order_is_unresolved(
    testnet_env: TestnetEnv,
) -> None:
    env = testnet_env
    assert env.sim is not None
    # Up at 23 (BUY), down, then up again at 27: a second BUY signal arrives.
    runner = env.make_runner(
        path={23: 110, 24: 100, 25: 100, 26: 100, 27: 130}, reconcile_absent_after_seconds=10**9
    )
    env.sim.fail_next("create", "timeout_before")
    _, bot = await _started(env, runner)
    await env.run_until(runner, 29)

    signals = await env.signals(bot)
    assert [(s["side"], s["decision"]) for s in signals] == [
        ("buy", "approved"),
        ("buy", "rejected"),
    ]
    assert "unresolved" in signals[1]["decision_reason"]
    assert len(env.sim.create_calls) == 1  # the blocked signal sent nothing


async def test_a_crash_between_the_intent_and_the_call_is_cleaned_up_on_restart(
    testnet_env: TestnetEnv,
) -> None:
    env = testnet_env
    assert env.sim is not None
    first = env.make_runner()

    async def crash_before_sending(bot: Any) -> None:  # the process "dies" after the commit
        return None

    first._supervisor._trader._submit_pending = crash_before_sending  # type: ignore[attr-defined,method-assign]
    _, bot = await _started(env, first)
    await env.run_until(first, 24)
    (order,) = await env.orders(bot)
    assert order["status"] == "SUBMITTING"
    assert Decimal((await env.portfolio(bot))["reserved_cash"]) > 0

    second = env.make_runner()  # a new process: only the database survives
    env.clock.advance(seconds=31)
    await second.run_once()
    (order,) = await env.orders(bot)
    assert order["status"] == "REJECTED" and env.sim.create_calls == []
    assert Decimal((await env.portfolio(bot))["reserved_cash"]) == 0


async def test_restarting_the_worker_every_few_hours_never_duplicates_an_order(
    testnet_env: TestnetEnv,
) -> None:
    env = testnet_env
    assert env.sim is not None
    runner = env.make_runner()
    _, bot = await _started(env, runner)
    for _ in range(10):  # a brand-new worker every two hours
        runner = env.make_runner()
        await env.run_until(runner, int((env.clock.now() - START).total_seconds() // 3600) + 2)

    orders = await env.orders(bot)
    assert _shape(orders) == Counter(
        {("market", "buy", "FILLED"): 1, ("market", "sell", "FILLED"): 1}
    )
    assert len(env.sim.create_calls) == len(set(env.sim.create_calls)) == 2


async def test_rejected_credentials_stop_the_bot_and_mark_the_connection_invalid(
    testnet_env: TestnetEnv,
) -> None:
    env = testnet_env
    assert env.sim is not None
    runner = env.make_runner()
    env.sim.fail_next("create", "auth")
    connection, bot = await _started(env, runner)
    await env.run_until(runner, 25)

    state = await env.bot(bot)
    assert (state["desired_state"], state["observed_state"]) == ("paused", "error")
    assert "AuthenticationFailed" in state["last_error"]
    assert (await env.http.get(f"/api/v1/exchange-connections/{connection}")).json()[
        "status"
    ] == "invalid"
    (order,) = await env.orders(bot)
    assert order["status"] == "REJECTED"


# --- native stop-loss -------------------------------------------------------------------------


async def test_a_stop_that_fires_while_the_worker_is_down_is_picked_up_on_restart(
    testnet_env: TestnetEnv,
) -> None:
    env = testnet_env
    assert env.sim is not None
    # BUY at 110 -> stop at 104.5. The market falls to 90 at hour 26 while no worker is running.
    first = env.make_runner(path={23: 110, 24: 110, 25: 110, 26: 90, 27: 90})
    _, bot = await _started(env, first, strategy_params=STOP_PARAMS)
    await env.run_until(first, 25)

    guarded = await env.portfolio(bot)
    assert guarded["native_stop_active"] is True and Decimal(guarded["quantity"]) > 0
    (resting,) = env.sim.open_orders()
    assert resting.order_type == "stop_loss" and resting.stop_price == Decimal("104.5")

    env.clock.advance(hours=2)  # the worker is down; the exchange keeps working
    env.sim.tick()
    assert env.sim.open_orders() == []

    second = env.make_runner()
    await second.run_once()
    assert _shape(await env.orders(bot)) == Counter(
        {("market", "buy", "FILLED"): 1, ("stop_loss", "sell", "FILLED"): 1}
    )
    after = await env.portfolio(bot)
    assert Decimal(after["quantity"]) == 0 and after["native_stop_active"] is False
    assert Decimal(after["cash"]) - 1000 == env.sim.balances["USDT"] - 100_000
    assert env.sim.cancel_calls == []


async def test_a_strategy_exit_removes_the_resting_stop_before_selling(
    testnet_env: TestnetEnv,
) -> None:
    env = testnet_env
    assert env.sim is not None
    runner = env.make_runner()
    far_stop = {"fast_period": 2, "slow_period": 3, "stop_loss_pct": 50}  # never reached
    _, bot = await _started(env, runner, strategy_params=far_stop)
    await env.run_until(runner, 40)

    assert _shape(await env.orders(bot)) == Counter(
        {
            ("market", "buy", "FILLED"): 1,
            ("stop_loss", "sell", "CANCELED"): 1,
            ("market", "sell", "FILLED"): 1,
        }
    )
    assert len(env.sim.cancel_calls) == 1 and env.sim.open_orders() == []
    assert (await env.portfolio(bot))["native_stop_active"] is False


async def test_the_kill_switch_pauses_bots_but_leaves_their_stop_on_the_exchange(
    testnet_env: TestnetEnv,
) -> None:
    env = testnet_env
    assert env.sim is not None
    runner = env.make_runner()
    _, bot = await _started(env, runner, strategy_params=STOP_PARAMS)
    await env.run_until(runner, 25)
    assert len(env.sim.open_orders()) == 1

    await env.http.put("/api/v1/system/kill-switch", json={"active": True, "reason": "test"})
    await runner.run_once()
    state = await env.bot(bot)
    assert (state["desired_state"], state["observed_state"]) == ("paused", "paused")
    assert len(env.sim.open_orders()) == 1  # the stop keeps protecting the open position


# --- reconciliation ---------------------------------------------------------------------------


async def test_a_balance_shortfall_pauses_the_bots_and_is_recorded(testnet_env: TestnetEnv) -> None:
    env = testnet_env
    assert env.sim is not None
    runner = env.make_runner()
    connection, bot = await _started(env, runner)
    await env.run_until(runner, 25)  # holding a position
    assert Decimal((await env.portfolio(bot))["quantity"]) > 5

    env.sim.balances["TST"] = Decimal("0.5")  # someone moved the coins away
    await env.run_until(runner, 26)

    state = await env.bot(bot)
    assert (state["observed_state"], state["last_error"]) == ("paused", "reconciliation mismatch")
    status, details = (await env.reconciliations(connection))[-1]
    assert status == "mismatch"
    assert details["problems"][0]["kind"] == "balance_shortfall"
    assert details["problems"][0]["asset"] == "TST"
    assert "reconciliation.mismatch" in await env.audit_types(bot)


async def test_foreign_orders_are_ignored_unless_they_look_like_ours(
    testnet_env: TestnetEnv,
) -> None:
    env = testnet_env
    assert env.sim is not None
    runner = env.make_runner()
    connection, bot = await _started(env, runner)

    env.sim.place_foreign_order("manual-order-by-a-human")
    await env.run_until(runner, 23)
    assert (await env.bot(bot))["observed_state"] == "running"
    assert {status for status, _ in await env.reconciliations(connection)} == {"ok"}

    env.sim.place_foreign_order("lc-" + "f" * 32)  # our prefix, but we never created it
    await env.run_until(runner, 24)
    assert (await env.bot(bot))["observed_state"] == "paused"
    _, details = (await env.reconciliations(connection))[-1]
    assert details["problems"][0]["kind"] == "unknown_open_order"
