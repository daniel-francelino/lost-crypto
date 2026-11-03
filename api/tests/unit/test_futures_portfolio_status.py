from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from modules.bots.application.service import BotService
from modules.bots.domain.models import Bot, BotConfig, BotState, ExecutionMode
from modules.exchanges.domain.models import MarginMode, PositionSide, TradingProduct
from modules.execution.domain.orders import OrderStatus
from modules.market_data.domain.models import Timeframe
from modules.portfolio.domain.perpetuals import PerpetualLedger

D = Decimal
NOW = datetime(2026, 11, 3, tzinfo=UTC)


class _Repository:
    def __init__(self, bot: Bot, ledger: PerpetualLedger, stop_status: OrderStatus | None) -> None:
        self.bot = bot
        self.ledger = ledger
        self.stop_status = stop_status
        self.stop_lookups = 0

    async def get_bot(self, bot_id):
        return self.bot if bot_id == self.bot.id else None

    async def get_ledger(self, bot_id):
        return self.ledger if bot_id == self.bot.id else None

    async def list_snapshots(self, bot_id, limit=None):
        return []

    async def get_by_client_id(self, bot_id, client_order_id):
        self.stop_lookups += 1
        if (
            bot_id != self.bot.id
            or client_order_id != self.ledger.stop_order_client_id
            or self.stop_status is None
        ):
            return None
        return type("StopOrder", (), {"status": self.stop_status})()


class _Bots:
    def __init__(self, repository: _Repository) -> None:
        self.repository = repository

    async def get(self, bot_id):
        return await self.repository.get_bot(bot_id)


class _Portfolio:
    def __init__(self, repository: _Repository) -> None:
        self.repository = repository

    async def get(self, bot_id):
        return await self.repository.get_ledger(bot_id)

    async def list_snapshots(self, bot_id, limit=None):
        return await self.repository.list_snapshots(bot_id, limit)


class _Orders:
    def __init__(self, repository: _Repository) -> None:
        self.repository = repository

    async def get_by_client_id(self, bot_id, client_order_id):
        return await self.repository.get_by_client_id(bot_id, client_order_id)


class _Store:
    def __init__(self, repository: _Repository) -> None:
        self.bots = _Bots(repository)
        self.perpetual_portfolio = _Portfolio(repository)
        self.orders = _Orders(repository)


class _StoreContext:
    def __init__(self, store: _Store) -> None:
        self.store = store

    async def __aenter__(self) -> _Store:
        return self.store

    async def __aexit__(self, *args) -> None:
        return None


def _service(repository: _Repository) -> BotService:
    service = object.__new__(BotService)
    service._stores = lambda: _StoreContext(_Store(repository))
    return service


def _bot(mode: ExecutionMode) -> Bot:
    bot_id = uuid4()
    config = BotConfig(
        name="Futures position status",
        strategy_type="mean_reversion_zscore",
        strategy_params={},
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.H1,
        initial_capital=D("1000"),
        fee_rate=D("0.0005"),
        slippage_bps=D(0),
        mode=mode,
        exchange="binance-usdm",
        connection_id=uuid4(),
        product=TradingProduct.LINEAR_PERPETUAL,
        leverage=2,
        margin_mode=MarginMode.ISOLATED,
    )
    return Bot(bot_id, config, BotState.RUNNING, BotState.RUNNING, 1, NOW, NOW)


def _ledger(bot: Bot) -> PerpetualLedger:
    ledger = PerpetualLedger.new(bot.id, D("1000"))
    ledger.open_position(
        PositionSide.LONG,
        D("0.01"),
        D("100000"),
        2,
        stop_price=D("95000"),
    )
    ledger.stop_order_client_id = "futures-stop"
    ledger.mark_price = D("101000")
    return ledger


@pytest.mark.parametrize(
    ("mode", "stop_status", "expected"),
    [
        (ExecutionMode.TESTNET, OrderStatus.OPEN, True),
        (ExecutionMode.TESTNET, OrderStatus.PARTIALLY_FILLED, True),
        (ExecutionMode.TESTNET, OrderStatus.CANCELED, False),
        (ExecutionMode.PAPER, OrderStatus.OPEN, False),
    ],
)
async def test_portfolio_reports_only_a_current_demo_stop_as_native(
    mode: ExecutionMode,
    stop_status: OrderStatus,
    expected: bool,
) -> None:
    bot = _bot(mode)
    repository = _Repository(bot, _ledger(bot), stop_status)

    portfolio = await _service(repository).portfolio(bot.id)

    assert portfolio.product is TradingProduct.LINEAR_PERPETUAL
    assert portfolio.native_stop_active is expected
    assert repository.stop_lookups == (1 if mode is ExecutionMode.TESTNET else 0)


async def test_portfolio_marks_a_missing_demo_stop_as_not_confirmed() -> None:
    bot = _bot(ExecutionMode.TESTNET)
    repository = _Repository(bot, _ledger(bot), None)

    portfolio = await _service(repository).portfolio(bot.id)

    assert portfolio.quantity == D("0.01")
    assert portfolio.native_stop_active is False


async def test_portfolio_identifies_exchange_reported_liquidation_price() -> None:
    bot = _bot(ExecutionMode.TESTNET)
    ledger = _ledger(bot)
    ledger.exchange_liquidation_price = D("51000")
    repository = _Repository(bot, ledger, None)

    portfolio = await _service(repository).portfolio(bot.id)

    assert portfolio.liquidation_price == D("51000")
    assert portfolio.liquidation_price_source == "exchange_reported"
