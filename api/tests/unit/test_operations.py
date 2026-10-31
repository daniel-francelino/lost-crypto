"""Pure pieces of book 1 ch. 4: clock skew, backup comparison, permissions round trip."""

import json
from datetime import UTC, datetime, timedelta

from modules.exchanges.domain.connections import (
    ApiPermissions,
    permissions_from_dict,
    permissions_to_dict,
)
from modules.risk_management.infrastructure.backup import _compare, libpq_url
from modules.trading.application.operations import skew_ms
from modules.trading.application.status import _clock_status

T = datetime(2026, 1, 1, tzinfo=UTC)


def test_skew_uses_the_middle_of_the_round_trip() -> None:
    sent, received = T, T + timedelta(milliseconds=200)
    assert skew_ms(sent, received, T + timedelta(milliseconds=100)) == 0
    assert skew_ms(sent, received, T - timedelta(seconds=2)) == 2100  # local clock ahead
    assert skew_ms(sent, received, T + timedelta(seconds=3)) == -2900


def test_clock_status_thresholds() -> None:
    assert _clock_status(None).skew_ms is None
    ok = _clock_status((300, T))
    assert (ok.warning, ok.blocking_live) == (False, False)
    warn = _clock_status((-1500, T))
    assert (warn.warning, warn.blocking_live) == (True, False)
    block = _clock_status((6000, T))
    assert (block.warning, block.blocking_live) == (True, True)


def test_restore_comparison() -> None:
    recorded = json.loads(json.dumps({"bots": 3, "orders": 10, "alembic:0010": 0}))
    assert _compare(recorded, {"bots": 3, "orders": 12, "alembic:0010": 0}) == []
    problems = _compare(recorded, {"bots": 2, "orders": 10, "alembic:0009": 0})
    assert any("schema version" in p for p in problems)
    assert any(p.startswith("bots:") for p in problems)


def test_libpq_url_drops_the_driver() -> None:
    url = libpq_url("postgresql+asyncpg://u:p@db:5432/main", "scratch")
    assert url == "postgresql://u:p@db:5432/scratch"


def test_permissions_round_trip() -> None:
    permissions = ApiPermissions(True, True, False, True, False)
    assert permissions_from_dict(permissions_to_dict(permissions)) == permissions
