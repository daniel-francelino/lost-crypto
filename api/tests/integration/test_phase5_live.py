"""Phase 5: every safeguard between a bot and real money, one test each.

The exchange is a simulated account, so no real order is ever sent; what is proven here is that the
system refuses, at every layer, to let a live bot trade unless each condition holds. APP_ENV is
``prod``, the live switch is on and all hard caps are set (``LIVE_SETTINGS``); each test breaks or
tightens exactly one thing. Hourly EMA 2/3 bots: BUY at hour 23 / SELL at 26 (the paper history),
then a second cycle, BUY at 33 / SELL at 36 (the live trades).
"""

from decimal import Decimal
from typing import Any

import pytest
from harness import LIVE_SETTINGS, TestnetEnv
from sqlalchemy import text

from core.config import AppEnv
from modules.exchanges.domain.connections import ApiPermissions
from modules.risk_management.domain.models import GlobalRiskLimits

pytestmark = pytest.mark.integration

LIVE_PATH = {
    23: 110, 24: 120, 25: 130, 26: 100, 27: 80, 28: 60, 29: 60, 30: 60, 31: 60, 32: 60,
    33: 100, 34: 120, 35: 130, 36: 100, 37: 80, 38: 60,
}  # fmt: skip
PARAMS = {"fast_period": 2, "slow_period": 3, "stop_loss_pct": 50}  # a stop that never fires
LIVE_RISK = {"require_stop_loss": True, "max_daily_loss_pct": 50}


async def _ready_bot(
    env: TestnetEnv,
    *,
    name: str = "itest-live-bot",
    risk: dict[str, Any] | None = None,
    paper_hours: int = 30,
) -> tuple[Any, str, str]:
    """A bot with paper history, stopped and pointed at a verified live connection."""
    assert env.sim is not None
    runner = env.make_runner(path=LIVE_PATH)
    connection = (await env.create_live_connection()).json()["id"]
    await runner.run_once()  # the worker verifies the key's permissions
    assert (await env.connection(connection))["status"] == "active"

    bot = await env.create_bot(name=name, strategy_params=PARAMS, risk=risk or LIVE_RISK)
    await env.command(bot, "start")
    await runner.run_once()
    await env.run_until(runner, paper_hours)
    await env.command(bot, "stop")
    await runner.run_once()
    promoted = await env.http.post(
        f"/api/v1/bots/{bot}/promote-to-live", json={"connection_id": connection}
    )
    assert promoted.status_code == 200 and promoted.json()["mode"] == "live", promoted.text
    return runner, bot, connection


async def _approve(env: TestnetEnv, bot: str, name: str = "itest-live-bot") -> str:
    response = await env.http.post(
        f"/api/v1/bots/{bot}/live-approvals", json={"confirm_name": name}
    )
    assert response.status_code == 201, response.text
    return str(response.json()["confirmation_token"])


async def _start_live(env: TestnetEnv, bot: str, runner: Any) -> None:
    token = await _approve(env, bot)
    started = await env.http.post(f"/api/v1/bots/{bot}/start", json={"confirmation_token": token})
    assert started.status_code == 202, started.text
    await runner.run_once()


# --- the keys -----------------------------------------------------------------------------------


async def test_live_keys_are_unusable_until_the_worker_verified_what_they_can_do(
    live_env: TestnetEnv,
) -> None:
    env, sim = live_env, live_env.sim
    assert sim is not None
    refused = await env.create_live_connection(confirm=False)
    assert refused.status_code == 422 and "confirm_real_money" in refused.json()["detail"]

    runner = env.make_runner()
    created = (await env.create_live_connection()).json()
    assert created["status"] == "pending" and created["environment"] == "live"

    bot = await env.create_bot()  # a bot cannot be pointed at a key nobody verified yet
    pending = await env.http.post(
        f"/api/v1/bots/{bot}/promote-to-live", json={"connection_id": created["id"]}
    )
    assert pending.status_code == 422 and "pending" in pending.json()["detail"]

    await runner.run_once()
    verified = await env.connection(created["id"])
    assert verified["status"] == "active" and verified["verified_at"]

    dangerous = [
        (ApiPermissions(True, True, True, False, True), "WITHDRAW"),
        (ApiPermissions(True, True, False, True, True), "transfer funds"),
        (ApiPermissions(True, True, False, False, False), "restricted to trusted IPs"),
        (ApiPermissions(True, False, False, False, True), "cannot trade"),
    ]
    for permissions, expected in dangerous:
        sim.permissions = permissions
        key = (await env.create_live_connection()).json()
        await runner.run_once()
        assert (await env.connection(key["id"]))["status"] == "invalid"
        events = (await env.http.get("/api/v1/audit-events", params={"limit": 20})).json()
        reasons = [
            e["payload"].get("reason", "")
            for e in events
            if e["event_type"] == "connection.invalid" and e["entity_id"] == key["id"]
        ]
        assert any(expected in reason for reason in reasons), (expected, reasons)

    sim.permissions = ApiPermissions(True, True, False, False, True)
    sim.fail_next("permissions", "auth")  # the exchange refuses the key outright
    rejected = (await env.create_live_connection()).json()
    await runner.run_once()
    assert (await env.connection(rejected["id"]))["status"] == "invalid"


# --- there is no shortcut into live -----------------------------------------------------------


async def test_a_bot_cannot_be_created_or_edited_straight_into_live(live_env: TestnetEnv) -> None:
    env = live_env
    runner = env.make_runner()
    connection = (await env.create_live_connection()).json()["id"]
    await runner.run_once()

    body = {"name": "itest-sneaky", "strategy_type": "ema_crossover", "mode": "live",
            "connection_id": connection}  # fmt: skip
    assert (await env.http.post("/api/v1/bots", json=body)).status_code == 422
    bot = await env.create_bot()
    patched = await env.http.patch(f"/api/v1/bots/{bot}", json={"mode": "live"})
    assert patched.status_code == 422  # the generic edit does not offer live at all

    testnet = await env.create_connection()  # a testnet connection cannot back a live bot
    wrong = await env.http.post(
        f"/api/v1/bots/{bot}/promote-to-live", json={"connection_id": testnet}
    )
    assert wrong.status_code == 422 and "live connection" in wrong.json()["detail"]

    await env.command(bot, "start")
    await env.http.get(f"/api/v1/bots/{bot}")
    running = await env.http.post(
        f"/api/v1/bots/{bot}/promote-to-live", json={"connection_id": connection}
    )
    assert running.status_code == 409  # only a stopped bot can be re-pointed at real money


# --- readiness --------------------------------------------------------------------------------


async def test_readiness_lists_every_unmet_condition(stack: Any) -> None:
    async with stack(
        **{**LIVE_SETTINGS, "live_min_paper_days": 30, "live_max_daily_loss": None}
    ) as env:
        _, bot, _ = await _ready_bot(env, risk={"max_daily_loss_pct": 50}, paper_hours=28)
        readiness = (await env.http.get(f"/api/v1/bots/{bot}/live-readiness")).json()
        failing = {c["name"] for c in readiness["checks"] if not c["ok"]}
        assert readiness["ready"] is False
        assert failing == {"hard caps", "risk limits", "paper history"}
        details = {c["name"]: c["detail"] for c in readiness["checks"]}
        assert "30 required" in details["paper history"]

        refused = await env.http.post(
            f"/api/v1/bots/{bot}/live-approvals", json={"confirm_name": "itest-live-bot"}
        )
        assert refused.status_code == 409 and "not ready" in refused.json()["detail"]


async def test_a_clean_bot_with_paper_history_is_ready(live_env: TestnetEnv) -> None:
    env = live_env
    _, bot, _ = await _ready_bot(env)
    readiness = (await env.http.get(f"/api/v1/bots/{bot}/live-readiness")).json()
    assert readiness["ready"] is True, readiness
    assert {c["name"] for c in readiness["checks"]} >= {
        "mode", "stopped", "environment", "hard caps", "live connection", "risk limits",
        "capital within caps", "paper history", "clean history",
    }  # fmt: skip


# --- the approval -----------------------------------------------------------------------------


async def test_approval_requires_the_typed_name_and_a_single_use_token(
    live_env: TestnetEnv,
) -> None:
    env = live_env
    runner, bot, _ = await _ready_bot(env)

    wrong_name = await env.http.post(
        f"/api/v1/bots/{bot}/live-approvals", json={"confirm_name": "itest-LIVE-bot"}
    )
    assert wrong_name.status_code == 422 and "exact name" in wrong_name.json()["detail"]

    no_token = await env.http.post(f"/api/v1/bots/{bot}/start")
    assert no_token.status_code == 422 and "confirmation_token" in no_token.json()["detail"]
    bad_token = await env.http.post(f"/api/v1/bots/{bot}/start", json={"confirmation_token": "x"})
    assert bad_token.status_code == 422

    token = await _approve(env, bot)
    started = await env.http.post(f"/api/v1/bots/{bot}/start", json={"confirmation_token": token})
    assert started.status_code == 202
    assert (await env.bot(bot))["live_approved"] is True
    await runner.run_once()
    assert (await env.bot(bot))["observed_state"] == "running"

    # Stopping ends the approval; the same token cannot be replayed; a new one is required.
    await env.command(bot, "stop")
    await runner.run_once()
    assert (await env.bot(bot))["live_approved"] is False
    replay = await env.http.post(f"/api/v1/bots/{bot}/start", json={"confirmation_token": token})
    assert replay.status_code == 422
    assert (await _start_live(env, bot, runner)) is None
    assert (await env.bot(bot))["observed_state"] == "running"


async def test_even_a_resume_after_a_pause_needs_a_fresh_approval(live_env: TestnetEnv) -> None:
    env = live_env
    runner, bot, _ = await _ready_bot(env)
    await _start_live(env, bot, runner)
    await env.command(bot, "pause")
    await runner.run_once()

    resume = await env.http.post(f"/api/v1/bots/{bot}/start")
    assert resume.status_code == 422  # real money never restarts on an old decision
    await env.command(bot, "stop")  # to be approvable again the bot must be stopped
    await runner.run_once()
    await _start_live(env, bot, runner)
    assert (await env.bot(bot))["observed_state"] == "running"


async def test_changing_the_bot_voids_a_pending_approval(live_env: TestnetEnv) -> None:
    env = live_env
    _, bot, _ = await _ready_bot(env)
    token = await _approve(env, bot)

    edit = await env.http.patch(f"/api/v1/bots/{bot}", json={"initial_capital": "900"})
    assert edit.status_code == 200 and edit.json()["config_version"] > 1

    outdated = await env.http.post(f"/api/v1/bots/{bot}/start", json={"confirmation_token": token})
    assert outdated.status_code == 422 and "outdated" in outdated.json()["detail"]


async def test_an_approval_expires(live_env: TestnetEnv) -> None:
    env = live_env
    assert env.api_container is not None
    _, bot, _ = await _ready_bot(env)
    token = await _approve(env, bot)
    async with env.api_container.engine.begin() as conn:
        await conn.execute(
            text("UPDATE live_approvals SET expires_at = now() - interval '1 second'"
                 " WHERE bot_id = :b"),
            {"b": bot},
        )  # fmt: skip
    expired = await env.http.post(f"/api/v1/bots/{bot}/start", json={"confirmation_token": token})
    assert expired.status_code == 422


# --- the worker does not trust the API ----------------------------------------------------------


async def test_the_worker_refuses_a_live_bot_started_behind_the_apis_back(
    live_env: TestnetEnv,
) -> None:
    env = live_env
    assert env.api_container is not None and env.sim is not None
    runner, bot, _ = await _ready_bot(env)
    async with env.api_container.engine.begin() as conn:  # bypass: no readiness, no token
        await conn.execute(
            text("UPDATE bots SET desired_state = 'running' WHERE id = :b"), {"b": bot}
        )
    await runner.run_once()

    state = await env.bot(bot)
    assert (state["desired_state"], state["observed_state"]) == ("paused", "error")
    assert "no valid live approval" in state["last_error"]
    assert env.sim.create_calls == []


async def test_every_safeguard_is_rechecked_on_every_worker_pass(live_env: TestnetEnv) -> None:
    env = live_env
    assert env.sim is not None
    runner, bot, _ = await _ready_bot(env)
    cases: list[tuple[dict[str, Any], str]] = [
        ({"live_trading_enabled": False}, "LIVE_TRADING_ENABLED"),
        ({"app_env": AppEnv.LOCAL}, "APP_ENV=prod"),
        ({"live_max_daily_loss": None}, "hard caps"),
    ]
    for overrides, expected in cases:
        await _start_live(env, bot, runner)  # a healthy worker starts it...
        assert (await env.bot(bot))["observed_state"] == "running"
        restarted = env.make_runner(**overrides)  # ...then a worker with one safeguard missing
        await restarted.run_once()
        state = await env.bot(bot)
        assert state["observed_state"] == "error" and expected in state["last_error"], expected
        await env.command(bot, "stop")
        await runner.run_once()
    assert env.sim.create_calls == []


# --- the hard caps ------------------------------------------------------------------------------


async def test_a_live_bot_trades_inside_the_hard_caps(live_env: TestnetEnv) -> None:
    env = live_env
    assert env.sim is not None
    runner, bot, connection = await _ready_bot(env)
    await _start_live(env, bot, runner)
    await env.run_until(runner, 40)

    orders = [o for o in await env.orders(bot) if o["order_type"] == "market"]
    buy = next(o for o in orders if o["side"] == "buy" and o["exchange_order_id"])
    live_orders = [o for o in orders if o["exchange_order_id"]]
    assert {(o["side"], o["status"]) for o in live_orders} == {
        ("buy", "FILLED"),
        ("sell", "FILLED"),
    }
    notional = Decimal(buy["quantity"]) * Decimal(buy["avg_fill_price"])
    assert notional <= 500  # LIVE_MAX_ORDER_NOTIONAL, although the bot has 1000 to spend
    assert {status for status, _ in await env.reconciliations(connection)} == {"ok"}
    assert {"live.promoted", "live.approval_requested", "live.activated"} <= await env.audit_types(
        bot
    )


async def test_the_executor_refuses_an_oversized_live_entry_even_if_risk_missed_it(
    live_env: TestnetEnv,
) -> None:
    env = live_env
    assert env.sim is not None
    runner, bot, _ = await _ready_bot(env)
    trader = runner._supervisor._trader  # type: ignore[attr-defined]
    trader._effective_limits = lambda b: (b.config.risk, GlobalRiskLimits())  # sizing bug
    await _start_live(env, bot, runner)
    await env.run_until(runner, 34)

    entries = [
        o for o in await env.orders(bot) if o["side"] == "buy" and o["order_type"] == "market"
    ]
    live_attempt = entries[-1]
    assert live_attempt["status"] == "REJECTED"
    assert env.sim.create_calls == []  # nothing was sent: the last line of defence held


async def test_losing_more_than_the_daily_cap_trips_the_global_kill_switch(
    live_env: TestnetEnv,
) -> None:
    env = live_env
    runner, bot, _ = await _ready_bot(env)
    await _start_live(env, bot, runner)
    tight = env.make_runner(live_max_daily_loss=Decimal("0.5"))  # fees alone exceed it
    await env.run_until(tight, 40)

    state = await env.bot(bot)
    assert (state["desired_state"], state["observed_state"]) == ("paused", "paused")
    assert state["last_error"] == "live daily loss cap reached"
    kill = (await env.http.get("/api/v1/system/kill-switch")).json()
    assert kill["active"] is True and kill["reason"] == "live daily loss cap reached"
    assert "risk.live_daily_loss_cap" in await env.audit_types(bot)


async def test_a_reconciliation_mismatch_on_a_live_account_trips_the_kill_switch(
    live_env: TestnetEnv,
) -> None:
    env = live_env
    assert env.sim is not None
    runner, bot, _ = await _ready_bot(env)
    await _start_live(env, bot, runner)
    await env.run_until(runner, 34)
    assert Decimal((await env.portfolio(bot))["quantity"]) > 0

    env.sim.balances["TST"] = Decimal("0.1")  # the coins are not where the books say
    await env.run_until(runner, 35)

    kill = (await env.http.get("/api/v1/system/kill-switch")).json()
    assert kill["active"] is True and "live connection" in kill["reason"]
    assert (await env.bot(bot))["last_error"] == "reconciliation mismatch"


async def test_viewers_cannot_touch_live_controls(live_env: TestnetEnv) -> None:
    """Live controls are state changes: they need the admin role (see test_auth_flow)."""
    env = live_env
    assert env.anonymous is not None
    _, bot, _ = await _ready_bot(env)
    body = {"confirm_name": "itest-live-bot"}
    assert (
        await env.anonymous.post(f"/api/v1/bots/{bot}/live-approvals", json=body)
    ).status_code == 401
    assert (await env.anonymous.get(f"/api/v1/bots/{bot}/live-readiness")).status_code == 401
