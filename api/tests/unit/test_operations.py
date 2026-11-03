"""Pure pieces of book 1 ch. 4: clock skew, backup comparison, permissions round trip."""

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from modules.exchanges.domain.connections import (
    ApiPermissions,
    permissions_from_dict,
    permissions_to_dict,
)
from modules.exchanges.domain.models import TradingProduct
from modules.execution.domain.orders import OrderStatus
from modules.risk_management.infrastructure.backup import _compare, libpq_url
from modules.trading.application.operations import skew_ms
from modules.trading.application.status import StatusService, _clock_status

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


async def test_open_futures_position_without_an_active_exchange_stop_is_reported() -> None:
    bot_id = uuid4()
    bot = SimpleNamespace(
        id=bot_id,
        config=SimpleNamespace(
            mode=SimpleNamespace(uses_exchange=True, value="testnet"),
            product=TradingProduct.LINEAR_PERPETUAL,
            name="Demo BTC",
            symbol="BTC/USDT:USDT",
        ),
    )
    position = SimpleNamespace(quantity=Decimal("0.02"), stop_price=Decimal("59000"))
    ledger = SimpleNamespace(position=position, stop_order_client_id="stop-1")

    class PerpetualPortfolio:
        async def get(self, requested_bot_id):
            return ledger

    class Orders:
        async def get_by_client_id(self, requested_bot_id, client_order_id):
            return SimpleNamespace(status=OrderStatus.REJECTED)

    store = SimpleNamespace(perpetual_portfolio=PerpetualPortfolio(), orders=Orders())

    unprotected = await StatusService._unprotected(store, [bot])

    assert len(unprotected) == 1
    assert unprotected[0].bot_id == str(bot_id)
    assert unprotected[0].quantity == Decimal("0.02")
    assert unprotected[0].stop_price == Decimal("59000")


async def test_open_futures_position_with_an_active_native_stop_is_not_reported() -> None:
    bot = SimpleNamespace(
        id=uuid4(),
        config=SimpleNamespace(
            mode=SimpleNamespace(uses_exchange=True, value="testnet"),
            product=TradingProduct.LINEAR_PERPETUAL,
            name="Demo BTC",
            symbol="BTC/USDT:USDT",
        ),
    )
    ledger = SimpleNamespace(
        position=SimpleNamespace(quantity=Decimal("0.02"), stop_price=Decimal("59000")),
        stop_order_client_id="stop-1",
    )

    class PerpetualPortfolio:
        async def get(self, requested_bot_id):
            return ledger

    class Orders:
        async def get_by_client_id(self, requested_bot_id, client_order_id):
            return SimpleNamespace(status=OrderStatus.OPEN)

    store = SimpleNamespace(perpetual_portfolio=PerpetualPortfolio(), orders=Orders())

    assert await StatusService._unprotected(store, [bot]) == []


async def test_open_futures_position_with_a_partially_filled_native_stop_is_not_reported() -> None:
    bot = SimpleNamespace(
        id=uuid4(),
        config=SimpleNamespace(
            mode=SimpleNamespace(uses_exchange=True, value="testnet"),
            product=TradingProduct.LINEAR_PERPETUAL,
            name="Demo BTC",
            symbol="BTC/USDT:USDT",
        ),
    )
    ledger = SimpleNamespace(
        position=SimpleNamespace(quantity=Decimal("0.02"), stop_price=Decimal("59000")),
        stop_order_client_id="stop-1",
    )

    class PerpetualPortfolio:
        async def get(self, requested_bot_id):
            return ledger

    class Orders:
        async def get_by_client_id(self, requested_bot_id, client_order_id):
            return SimpleNamespace(status=OrderStatus.PARTIALLY_FILLED)

    store = SimpleNamespace(perpetual_portfolio=PerpetualPortfolio(), orders=Orders())

    assert await StatusService._unprotected(store, [bot]) == []
