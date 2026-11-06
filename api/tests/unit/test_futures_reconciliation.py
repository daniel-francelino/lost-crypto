from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from modules.audit.models import AuditEvent
from modules.bots.domain.models import Bot, BotConfig, BotState, ExecutionMode
from modules.exchanges.application.ports import ExchangePosition
from modules.exchanges.domain.models import MarginMode, PositionSide, TradingProduct
from modules.market_data.domain.models import Timeframe
from modules.trading.application.reconciler import Reconciler

NOW = datetime(2025, 1, 1, tzinfo=UTC)


@pytest.mark.asyncio
async def test_reconciliation_reads_and_flags_positions_on_unassigned_usdm_symbols() -> None:
    connection_id = uuid4()
    bot = Bot(
        id=uuid4(),
        config=BotConfig(
            name="BTC bot",
            strategy_type="mean_reversion_zscore",
            strategy_params={},
            symbol="BTC/USDT:USDT",
            timeframe=Timeframe.H1,
            initial_capital=Decimal("1000"),
            fee_rate=Decimal("0.001"),
            slippage_bps=Decimal("0"),
            mode=ExecutionMode.TESTNET,
            exchange="binance-usdm",
            connection_id=connection_id,
            product=TradingProduct.LINEAR_PERPETUAL,
            leverage=2,
            margin_mode=MarginMode.ISOLATED,
        ),
        desired_state=BotState.RUNNING,
        observed_state=BotState.RUNNING,
        config_version=1,
        created_at=NOW,
        updated_at=NOW,
    )
    remote_eth = ExchangePosition(
        symbol="ETH/USDT:USDT",
        side=PositionSide.LONG,
        quantity=Decimal("0.5"),
        entry_price=Decimal("2000"),
        mark_price=Decimal("2010"),
        unrealized_pnl=Decimal("5"),
        leverage=2,
        margin_mode=MarginMode.ISOLATED,
        isolated_margin=Decimal("500"),
        liquidation_price=Decimal("1000"),
        notional=Decimal("1005"),
    )
    observed_position_filter: list[list[str] | None] = []
    reconciliations: list[tuple[str, dict[str, object]]] = []
    audit_events: list[AuditEvent] = []
    bot_states: list[tuple[BotState, str | None]] = []

    class Exchange:
        async def fetch_balances(self) -> dict[str, object]:
            return {}

        async def fetch_positions(
            self, symbols: list[str] | None = None
        ) -> list[ExchangePosition]:
            observed_position_filter.append(symbols)
            return [remote_eth]

        async def fetch_open_orders(self, _symbol: str) -> list[object]:
            return [SimpleNamespace(client_order_id="manual-btc-order")]

        async def fetch_all_open_orders(self) -> list[object]:
            return [
                SimpleNamespace(
                    symbol="ETH/USDT:USDT", client_order_id="manual-eth-order"
                )
            ]

    class Resolver:
        async def exchange_for(self, _connection_id: object) -> Exchange:
            return Exchange()

    class Bots:
        async def list_bots(self, _limit: int) -> list[Bot]:
            return [bot]

        async def set_desired(self, _bot_id: object, state: BotState) -> None:
            bot_states.append((state, None))

        async def set_observed(
            self, _bot_id: object, state: BotState, error: str | None
        ) -> None:
            bot_states.append((state, error))

    class Orders:
        async def count_unresolved(self, _bot_id: object) -> int:
            return 0

        async def list_unresolved(self) -> list[object]:
            return []

        async def get_by_client_id(self, _bot_id: object, _client_order_id: str) -> None:
            return None

    class PerpetualPortfolio:
        async def get(self, _bot_id: object) -> None:
            return None

    class ReconciliationRepository:
        async def add(
            self,
            _connection_id: object,
            _started: datetime,
            status: str,
            details: dict[str, object],
        ) -> None:
            reconciliations.append((status, details))

    class Audit:
        async def add(self, event: AuditEvent) -> None:
            audit_events.append(event)

    async def commit() -> None:
        return None

    store = SimpleNamespace(
        bots=Bots(),
        orders=Orders(),
        perpetual_portfolio=PerpetualPortfolio(),
        reconciliations=ReconciliationRepository(),
        audit=Audit(),
        commit=commit,
    )

    @asynccontextmanager
    async def stores():
        yield store

    reconciler = Reconciler(
        stores,
        Resolver(),  # type: ignore[arg-type]
        object(),  # type: ignore[arg-type]
        SimpleNamespace(now=lambda: NOW),  # type: ignore[arg-type]
    )

    mismatches = await reconciler.reconcile_connection(
        connection_id, inspect_unowned_futures_orders=True
    )

    assert observed_position_filter == [None]
    assert mismatches == 3
    assert reconciliations[0][0] == "mismatch"
    assert reconciliations[0][1]["problems"] == [
        {
            "kind": "unowned_exchange_position",
            "symbol": "ETH/USDT:USDT",
            "side": "long",
            "quantity": "0.5",
        },
        {
            "kind": "unknown_open_order",
            "symbol": "BTC/USDT:USDT",
            "client_order_id": "manual-btc-order",
        },
        {
            "kind": "unknown_open_order",
            "symbol": "ETH/USDT:USDT",
            "client_order_id": "manual-eth-order",
        },
    ]
    assert bot_states[0][0] is BotState.PAUSED
    assert any(event.event_type == "reconciliation.mismatch" for event in audit_events)
