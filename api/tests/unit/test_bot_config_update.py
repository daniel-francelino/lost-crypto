from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest

from core.errors import ConflictError
from core.ids import UuidGenerator
from factories import T0
from modules.bots.application.service import (
    BotService,
    _ensure_flat_before_perpetual_config_update,
    _normalize_config_update,
)
from modules.bots.domain.models import Bot, BotConfig, BotState, ExecutionMode
from modules.exchanges.application.registry import ExchangeRegistry
from modules.exchanges.domain.connections import (
    ConnectionStatus,
    Environment,
    ExchangeConnection,
)
from modules.exchanges.domain.models import MarginMode, PositionSide, TradingProduct
from modules.exchanges.infrastructure.binance_usdm import BinanceUsdmExchange
from modules.market_data.domain.models import Timeframe
from modules.portfolio.domain.models import PortfolioState
from modules.portfolio.domain.perpetuals import PerpetualLedger
from modules.strategies.catalog import build_strategy_registry

D = Decimal


def _config(
    product: TradingProduct,
    *,
    mode: ExecutionMode = ExecutionMode.PAPER,
    connection_id=None,
) -> BotConfig:
    futures = product is TradingProduct.LINEAR_PERPETUAL
    return BotConfig(
        name="configuration guard",
        exchange="binance-usdm" if futures else "binance",
        strategy_type="mean_reversion_zscore",
        strategy_params={},
        symbol="BTC/USDT:USDT" if futures else "BTC/USDT",
        timeframe=Timeframe.H1,
        initial_capital=D("1000"),
        fee_rate=D("0.0005" if futures else "0.001"),
        slippage_bps=D("2"),
        mode=mode,
        connection_id=connection_id,
        product=product,
        leverage=2 if futures else 1,
        margin_mode=MarginMode.ISOLATED if futures else None,
    )


class _PerpetualStore:
    def __init__(self, ledger: PerpetualLedger | None = None) -> None:
        self.ledger = ledger

    async def get(self, bot_id):
        return self.ledger


class _SpotStore:
    def __init__(self, portfolio: PortfolioState | None = None) -> None:
        self.portfolio = portfolio

    async def get(self, bot_id):
        return self.portfolio


class _Orders:
    def __init__(self, unresolved: int = 0) -> None:
        self.unresolved = unresolved

    async def count_unresolved(self, bot_id) -> int:
        return self.unresolved


class _Store:
    def __init__(
        self,
        *,
        ledger: PerpetualLedger | None = None,
        portfolio: PortfolioState | None = None,
        unresolved: int = 0,
    ) -> None:
        self.perpetual_portfolio = _PerpetualStore(ledger)
        self.portfolio = _SpotStore(portfolio)
        self.orders = _Orders(unresolved)


class _ServiceStore(_Store):
    def __init__(self, bot: Bot, connection: ExchangeConnection) -> None:
        super().__init__()
        self.bot = bot
        self.connection = connection
        self.audit_events = []
        self.committed = False
        self.bots = self
        self.connections = self
        self.audit = self

    async def get(self, identifier):
        if identifier == self.bot.id:
            return self.bot
        if identifier == self.connection.id:
            return self.connection
        return None

    async def update_config(self, bot_id, config, config_version):
        self.bot.config = config
        self.bot.config_version = config_version
        return True

    async def set_live_approval(self, bot_id, config_version, at):
        self.bot.live_approved_config_version = config_version
        self.bot.live_approved_at = at

    async def add(self, event) -> None:
        self.audit_events.append(event)

    async def commit(self) -> None:
        self.committed = True


class _StoreContext:
    def __init__(self, store: _ServiceStore) -> None:
        self.store = store

    async def __aenter__(self):
        return self.store

    async def __aexit__(self, *args):
        return None


def test_paper_mode_update_keeps_futures_demo_connection_but_clears_spot_connection() -> None:
    connection_id = uuid4()
    futures = _config(
        TradingProduct.LINEAR_PERPETUAL,
        mode=ExecutionMode.TESTNET,
        connection_id=connection_id,
    )
    spot = _config(TradingProduct.SPOT, mode=ExecutionMode.TESTNET, connection_id=connection_id)

    futures_changes = _normalize_config_update(futures, {"mode": ExecutionMode.PAPER})
    spot_changes = _normalize_config_update(spot, {"mode": ExecutionMode.PAPER})

    assert replace(futures, **futures_changes).connection_id == connection_id
    assert replace(spot, **spot_changes).connection_id is None


@pytest.mark.asyncio
async def test_futures_config_update_is_refused_while_futures_position_is_open() -> None:
    config = _config(TradingProduct.LINEAR_PERPETUAL, connection_id=uuid4())
    ledger = PerpetualLedger.new(uuid4(), D("1000"))
    ledger.open_position(PositionSide.SHORT, D("1"), D("100"), leverage=2)

    with pytest.raises(ConflictError, match="close the open Futures position"):
        await _ensure_flat_before_perpetual_config_update(
            _Store(ledger=ledger), ledger.bot_id, config, config
        )


@pytest.mark.asyncio
async def test_futures_config_update_is_refused_while_margin_is_reserved() -> None:
    config = _config(TradingProduct.LINEAR_PERPETUAL, connection_id=uuid4())
    ledger = PerpetualLedger.new(uuid4(), D("1000"))
    ledger.reserve(D("100"))

    with pytest.raises(ConflictError, match="resolve pending Futures orders"):
        await _ensure_flat_before_perpetual_config_update(
            _Store(ledger=ledger), ledger.bot_id, config, config
        )


@pytest.mark.asyncio
async def test_spot_position_blocks_switching_bot_to_futures() -> None:
    spot = _config(TradingProduct.SPOT)
    futures = _config(TradingProduct.LINEAR_PERPETUAL, connection_id=uuid4())
    portfolio = PortfolioState.new(uuid4(), D("1000"))
    portfolio.quantity = D("0.01")

    with pytest.raises(ConflictError, match="close the open Spot position"):
        await _ensure_flat_before_perpetual_config_update(
            _Store(portfolio=portfolio), portfolio.bot_id, spot, futures
        )


@pytest.mark.asyncio
async def test_unresolved_orders_block_futures_configuration_update() -> None:
    config = _config(TradingProduct.LINEAR_PERPETUAL, connection_id=uuid4())
    bot_id = uuid4()

    with pytest.raises(ConflictError, match="resolve pending orders"):
        await _ensure_flat_before_perpetual_config_update(
            _Store(unresolved=1), bot_id, config, config
        )


@pytest.mark.asyncio
async def test_flat_bot_can_update_futures_configuration() -> None:
    config = _config(TradingProduct.LINEAR_PERPETUAL, connection_id=uuid4())
    bot_id = uuid4()

    await _ensure_flat_before_perpetual_config_update(_Store(), bot_id, config, config)


@pytest.mark.asyncio
async def test_service_update_to_paper_preserves_futures_demo_connection() -> None:
    connection_id = uuid4()
    config = _config(
        TradingProduct.LINEAR_PERPETUAL,
        mode=ExecutionMode.TESTNET,
        connection_id=connection_id,
    )
    bot = Bot(uuid4(), config, BotState.STOPPED, BotState.STOPPED, 3, T0, T0)
    bot.live_approved_config_version = 3
    bot.live_approved_at = T0
    connection = ExchangeConnection(
        connection_id,
        "binance-usdm",
        Environment.DEMO,
        "unit-test-demo",
        "1234",
        ConnectionStatus.ACTIVE,
        T0,
    )
    store = _ServiceStore(bot, connection)
    exchanges = ExchangeRegistry()
    exchanges.register(BinanceUsdmExchange)

    service = BotService(
        lambda: _StoreContext(store),
        build_strategy_registry(),
        exchanges,
        clock=type("Clock", (), {"now": lambda self: T0})(),
        ids=UuidGenerator(),
        live=object(),
    )
    updated = await service.update(bot.id, {"mode": ExecutionMode.PAPER})

    assert updated.config.mode is ExecutionMode.PAPER
    assert updated.config.connection_id == connection_id
    assert updated.config_version == 4
    assert updated.live_approved_config_version is None
    assert updated.live_approved_at is None
    assert not updated.has_live_approval
    assert store.committed
