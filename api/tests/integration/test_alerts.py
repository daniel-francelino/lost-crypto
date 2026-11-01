"""In-app alerts and the live candle update, against real PostgreSQL and simulated time."""

from datetime import timedelta
from typing import Any

import pytest
from harness import START, SYMBOL, Env
from sqlalchemy import text

from container import Container

pytestmark = pytest.mark.integration

KILL = "/api/v1/system/kill-switch"


async def _alerts(env: Env, **params: Any) -> list[dict[str, Any]]:
    resp = await env.http.get("/api/v1/alerts", params=params)
    assert resp.status_code == 200, resp.text
    return list(resp.json())


async def _summary(env: Env) -> dict[str, int]:
    return dict((await env.http.get("/api/v1/alerts/summary")).json())


async def test_a_kill_switch_episode_is_one_alert_that_resolves_when_released(env: Env) -> None:
    runner = env.make_runner()
    await env.http.put(KILL, json={"active": True, "reason": "itest"})
    await runner.run_once()

    (alert,) = await _alerts(env)
    assert (alert["kind"], alert["severity"]) == ("kill_switch_active", "warning")
    assert "itest" in alert["message"] and alert["resolved_at"] is None
    assert await _summary(env) == {"unread": 1, "open": 1, "critical_open": 0}

    env.clock.advance(seconds=20)
    await runner.run_once()
    assert len(await _alerts(env)) == 1  # still the same episode

    await env.http.put(KILL, json={"active": False, "reason": "done"})
    env.clock.advance(seconds=20)
    await runner.run_once()
    (resolved,) = await _alerts(env)
    assert resolved["resolved_at"] is not None
    assert await _summary(env) == {"unread": 1, "open": 0, "critical_open": 0}


async def test_alerts_can_be_listed_filtered_marked_read_and_paged(env: Env) -> None:
    runner = env.make_runner()
    await env.http.put(KILL, json={"active": True})
    await runner.run_once()
    (alert,) = await _alerts(env, unread=True)

    resp = await env.http.get("/api/v1/alerts", params={"limit": 1})
    assert resp.headers["X-Total-Count"] == "1"
    assert await _alerts(env, severity="critical") == []

    marked = await env.http.post(f"/api/v1/alerts/{alert['id']}/read")
    assert marked.status_code == 204
    assert await _alerts(env, unread=True) == []
    assert (await _alerts(env))[0]["read_at"] is not None
    assert (await env.http.post("/api/v1/alerts/999999999/read")).status_code == 404

    env.clock.advance(seconds=1)
    assert (await env.http.post("/api/v1/alerts/read-all")).json() == {"marked": 0}


async def test_the_api_side_watcher_raises_worker_down_and_resolves_it(env: Env) -> None:
    runner = env.make_runner()
    api_side: Container = env.containers[-1]  # same code path the API process runs
    await api_side.alert_monitor.run_api_once()  # no heartbeat has ever been written

    (down,) = await _alerts(env, severity="critical")
    assert down["kind"] == "worker_down" and "never" in down["message"]
    assert (await _summary(env))["critical_open"] == 1
    audit = (
        await env.http.get("/api/v1/audit-events", params={"event_type": "alert.opened"})
    ).json()
    assert audit and audit[0]["entity_type"] == "alert"

    await runner.run_once()  # the worker writes its heartbeat
    env.clock.advance(seconds=20)
    await api_side.alert_monitor.run_api_once()
    (resolved,) = await _alerts(env, severity="critical")
    assert resolved["resolved_at"] is not None
    assert (await _summary(env))["critical_open"] == 0


async def test_a_stopped_worker_makes_the_running_bot_stale_and_alerts_on_it(env: Env) -> None:
    runner = env.make_runner(worker_stale_after_seconds=60.0)
    bot_id = await env.create_bot()
    await env.command(bot_id, "start")
    await runner.run_once()

    env.clock.advance(minutes=5)  # the bot's heartbeat is now old, and no pass touches it
    status = await env.containers[-1].status.system_status()
    assert [b.bot_id for b in status.stale_bots] == [bot_id]
    await env.containers[-1].alert_monitor.run_worker_if_due()

    alerts = await _alerts(env)
    assert [(a["kind"], a["bot_id"]) for a in alerts] == [("bot_stale", bot_id)]


async def _forget_series(env: Env) -> None:
    async with env.containers[-1].engine.begin() as conn:
        for table in ("candle_import_jobs", "candles"):
            await conn.execute(text(f"DELETE FROM {table} WHERE symbol = :s"), {"s": SYMBOL})


async def test_stored_candles_follow_the_exchange_when_the_update_is_on(env: Env) -> None:
    runner = env.make_runner(candle_update_enabled=True)
    await _forget_series(env)  # other scenarios leave candles of the same symbol behind
    body = {
        "symbol": SYMBOL,
        "timeframe": "1h",
        "start": START.isoformat(),
        "end": (START + timedelta(hours=12)).isoformat(),
    }
    assert (await env.http.post("/api/v1/market-data/imports", json=body)).status_code == 202
    try:
        for _ in range(3):
            await runner.run_once()  # the import job runs
        env.clock.advance(minutes=11)  # past the discovery interval: the series is now followed
        await runner.run_once()
        coverage = await env.http.get(
            "/api/v1/market-data/coverage", params={"symbol": SYMBOL, "timeframe": "1h"}
        )
        # now = START + 20h05s: the candles of hours 0..19 are closed, 20 is still open
        assert coverage.json()["count"] == 20 and coverage.json()["gaps"] == []

        env.clock.advance(hours=1)
        await runner.run_once()
        coverage = await env.http.get(
            "/api/v1/market-data/coverage", params={"symbol": SYMBOL, "timeframe": "1h"}
        )
        assert coverage.json()["count"] == 21
    finally:
        await _forget_series(env)
