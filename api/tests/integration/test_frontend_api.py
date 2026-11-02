"""What the frontend relies on besides the trading flows: totals, paging, capabilities."""

from decimal import Decimal
from uuid import uuid4

import pytest
from harness import Env

pytestmark = pytest.mark.integration


async def test_summary_adds_bots_per_mode_and_quote_currency(env: Env) -> None:
    await env.create_bot(initial_capital="1000")
    await env.create_bot(initial_capital="500")

    overview = await env.http.get("/api/v1/bots/overview")
    assert overview.status_code == 200
    assert {row["mode"] for row in overview.json()} <= {"paper", "testnet", "live"}

    response = await env.http.get("/api/v1/bots/summary")
    assert response.status_code == 200
    groups = {(g["mode"], g["quote_currency"]): g for g in response.json()}
    paper = groups[("paper", "USDT")]
    assert paper["bots"] >= 2 and paper["running"] == 0 and paper["open_positions"] == 0
    assert Decimal(paper["initial_capital"]) >= Decimal(1500)
    assert Decimal(paper["equity"]) == Decimal(paper["initial_capital"])  # nothing traded yet
    assert Decimal(paper["return_pct"]) == 0


async def test_lists_expose_their_total_and_a_window(env: Env) -> None:
    bot_id = await env.create_bot()
    for command in ("start", "pause", "stop"):
        assert (await env.command(bot_id, command)).status_code == 202

    everything = await env.http.get("/api/v1/audit-events", params={"bot_id": bot_id})
    total = int(everything.headers["X-Total-Count"])
    assert total == len(everything.json()) >= 4  # created + the three commands

    window = await env.http.get(
        "/api/v1/audit-events", params={"bot_id": bot_id, "limit": 2, "offset": 1}
    )
    assert int(window.headers["X-Total-Count"]) == total
    assert window.json() == everything.json()[1:3]  # same order, skipping the newest

    kind = everything.json()[0]["event_type"]
    expected = sum(1 for e in everything.json() if e["event_type"] == kind)
    of_one_kind = await env.http.get(
        "/api/v1/audit-events", params={"bot_id": bot_id, "event_type": kind}
    )
    assert int(of_one_kind.headers["X-Total-Count"]) == len(of_one_kind.json()) == expected

    for path in ("orders", "signals"):
        empty = await env.http.get(f"/api/v1/bots/{bot_id}/{path}", params={"offset": 5})
        assert empty.status_code == 200 and empty.json() == []
        assert empty.headers["X-Total-Count"] == "0"

    runs = await env.http.get("/api/v1/backtests", params={"limit": 1})
    assert runs.status_code == 200 and int(runs.headers["X-Total-Count"]) >= len(runs.json())


async def test_a_negative_offset_is_a_validation_error(env: Env) -> None:
    response = await env.http.get("/api/v1/audit-events", params={"offset": -1})
    assert response.status_code == 422


async def test_capabilities_say_why_live_is_not_available(env: Env) -> None:
    response = await env.http.get("/api/v1/system/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert body["live_available"] is False and body["live_trading_enabled"] is False
    assert len(body["live_blockers"]) >= 1
    assert "binance" in body["exchanges"] and "ema_crossover" in body["strategies"]
    assert body["live_approval_minutes"] <= 15
    assert "secret" not in response.text.lower()


async def test_a_stopped_bot_can_be_deleted_and_the_audit_trail_remembers_it(env: Env) -> None:
    bot_id = await env.create_bot(name="to-delete")

    assert (await env.http.delete(f"/api/v1/bots/{uuid4()}")).status_code == 404

    assert (await env.command(bot_id, "start")).status_code == 202
    running = await env.http.delete(f"/api/v1/bots/{bot_id}")
    assert running.status_code == 409  # stop it first

    assert (await env.command(bot_id, "stop")).status_code == 202
    gone = await env.http.request(
        "DELETE", f"/api/v1/bots/{bot_id}", json={"reason": "cleaning up tests"}
    )
    assert gone.status_code == 204
    assert (await env.http.get(f"/api/v1/bots/{bot_id}")).status_code == 404
    assert bot_id not in {b["id"] for b in (await env.http.get("/api/v1/bots")).json()}

    events = (await env.http.get("/api/v1/audit-events", params={"bot_id": bot_id})).json()
    deleted = [e for e in events if e["event_type"] == "bot.deleted"]
    assert len(deleted) == 1
    assert deleted[0]["payload"]["name"] == "to-delete"
    assert deleted[0]["payload"]["reason"] == "cleaning up tests"
