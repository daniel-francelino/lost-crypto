"""Book 1 ch. 4 (setting up the business) against a real PostgreSQL: key permissions that change
after activation, positions exposed during an outage, worker liveness, clock skew, backups."""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from harness import TestnetEnv
from sqlalchemy import text
from test_phase5_live import _ready_bot, _start_live

from modules.exchanges.domain.connections import ApiPermissions
from modules.risk_management.infrastructure import backup

pytestmark = pytest.mark.integration

SAFE = ApiPermissions(True, True, False, False, True)
WITHDRAW = ApiPermissions(True, True, True, False, True)


async def _signals(env: TestnetEnv, bot: str) -> list[dict[str, Any]]:
    return list((await env.http.get(f"/api/v1/bots/{bot}/signals")).json())


async def test_a_key_that_later_allows_withdrawals_blocks_entries_not_exits(
    live_env: TestnetEnv,
) -> None:
    env, sim = live_env, live_env.sim
    assert sim is not None
    runner, bot, connection = await _ready_bot(env)
    checked = await env.connection(connection)
    assert checked["permissions"]["can_trade"] is True and checked["last_checked_at"]
    assert checked["permission_warning"] is None

    await _start_live(env, bot, runner)
    worker = env.containers[-1]  # the worker's resolver talks to the simulated exchange
    sim.permissions = WITHDRAW  # someone enables withdrawals on the exchange afterwards
    await worker.resolver.recheck(UUID(connection), require_ip_restriction=True)
    warned = await env.connection(connection)
    assert warned["status"] == "active"  # not invalid: exits must keep working
    assert "WITHDRAW" in warned["permission_warning"]
    assert warned["permissions"]["can_withdraw"] is True

    await env.run_until(runner, 40)
    rejected = [
        s
        for s in await _signals(env, bot)
        if s["decision"] == "rejected" and "permissions changed" in (s["decision_reason"] or "")
    ]
    assert rejected and all(s["side"] == "buy" for s in rejected)
    live_buys = [o for o in await env.orders(bot) if o["side"] == "buy" and o["exchange_order_id"]]
    assert live_buys == []

    readiness = (await env.http.get(f"/api/v1/bots/{bot}/live-readiness")).json()
    assert "permissions changed" in str(readiness)

    sim.permissions = SAFE
    await worker.resolver.recheck(UUID(connection), require_ip_restriction=True)
    assert (await env.connection(connection))["permission_warning"] is None
    missing = await env.http.post(f"/api/v1/exchange-connections/{uuid4()}/recheck")
    assert missing.status_code == 404
    types = {
        e["event_type"]
        for e in (await env.http.get("/api/v1/audit-events", params={"limit": 50})).json()
    }
    assert {"connection.permissions_changed", "connection.permissions_ok"} <= types


async def test_a_skewed_clock_blocks_new_live_entries(live_env: TestnetEnv) -> None:
    env, sim = live_env, live_env.sim
    assert sim is not None
    runner, bot, _ = await _ready_bot(env)
    sim.server_offset = timedelta(seconds=10)
    await _start_live(env, bot, runner)
    await env.run_until(runner, 40)

    status = (await env.http.get("/api/v1/system/status")).json()
    assert status["clock"]["skew_ms"] == 10_000
    assert status["clock"]["warning"] is True and status["clock"]["blocking_live"] is True
    reasons = [
        s["decision_reason"] or "" for s in await _signals(env, bot) if s["decision"] == "rejected"
    ]
    assert any("server clock" in r for r in reasons)


async def test_a_position_without_an_exchange_stop_is_reported(testnet_env: TestnetEnv) -> None:
    env, sim = testnet_env, testnet_env.sim
    assert sim is not None
    runner = env.make_runner(path={23: 110, 24: 110, 25: 110, 26: 110})
    connection = await env.create_connection()
    params = {"fast_period": 2, "slow_period": 3, "stop_loss_pct": 5}
    bot = await env.create_testnet_bot(connection, strategy_params=params)
    await env.command(bot, "start")
    await runner.run_once()
    sim.fail_next("create_stop", "reject")  # the exchange refuses the protective stop
    sim.fail_next("create_stop", "reject")
    await env.run_until(runner, 25)

    portfolio = await env.portfolio(bot)
    assert portfolio["native_stop_active"] is False
    status = (await env.http.get("/api/v1/system/status")).json()
    exposed = [p for p in status["unprotected_positions"] if p["bot_id"] == bot]
    assert len(exposed) == 1 and exposed[0]["mode"] == "testnet"


async def test_worker_health_for_an_external_monitor(testnet_env: TestnetEnv) -> None:
    env = testnet_env
    assert env.anonymous is not None and env.api_container is not None
    async with env.api_container.engine.begin() as conn:
        await conn.execute(text("DELETE FROM system_flags WHERE key = 'worker_heartbeat'"))
    down = await env.anonymous.get("/api/v1/health/worker")  # no login needed
    assert down.status_code == 503 and down.json()["status"] == "stale"

    async with env.api_container.trading_stores() as store:  # the API judges by its own clock
        await store.flags.set_worker_heartbeat(datetime.now(UTC))
        await store.commit()
    up = await env.anonymous.get("/api/v1/health/worker")
    assert up.status_code == 200 and up.json()["status"] == "ok"


async def test_backup_and_restore_check(tmp_path: Path, testnet_env: TestnetEnv) -> None:
    env = testnet_env
    assert env.api_container is not None
    url = os.environ["DATABASE_URL"]
    now = datetime.now(UTC)  # the API judges "overdue" by its own (real) clock
    made = await backup.backup(url, str(tmp_path), keep=2, now=now)
    assert made.ok, made.detail
    assert made.size_bytes and made.checksum and made.file

    checked = await backup.restore_check(url, made, now)
    assert checked.ok, checked.detail

    tampered = await backup.restore_check(
        url, made.__class__(**{**_fields(made), "checksum": "x"}), now
    )
    assert not tampered.ok and "checksum" in (tampered.detail or "")

    async with env.api_container.trading_stores() as store:
        await store.flags.add_backup_record(made)
        await store.flags.add_backup_record(checked)
        await store.commit()
    status = (await env.http.get("/api/v1/system/status")).json()
    assert status["backup"]["last_backup"]["ok"] is True
    assert status["backup"]["last_restore_check"]["ok"] is True
    assert status["backup"]["overdue"] is False

    for i in range(3):  # retention keeps the newest two dumps
        await backup.backup(url, str(tmp_path), keep=2, now=now + timedelta(minutes=i + 1))
    assert _dump_count(tmp_path) == 2


def _dump_count(directory: Path) -> int:
    return len(list(directory.glob("*.dump")))


def _fields(record: Any) -> dict[str, Any]:
    return {name: getattr(record, name) for name in record.__dataclass_fields__}
