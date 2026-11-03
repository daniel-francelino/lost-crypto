from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from factories import MARKET, T0, make_candles
from modules.bots.domain.models import Bot, BotConfig, BotState, ExecutionMode
from modules.exchanges.domain.models import MarginMode, PositionSide, TradingProduct
from modules.execution.domain.normalizer import OrderRejected
from modules.market_data.domain.models import Timeframe
from modules.portfolio.domain.perpetuals import PerpetualLedger
from modules.strategies.domain.types import Side, Signal, SignalKind
from modules.trading.application.perpetual_paper import PerpetualDemoTrader
from modules.trading.domain.models import SessionStatus, TradingSession

D = Decimal
SYMBOL = "BTC/USDT:USDT"


class _Clock:
    def now(self):
        return T0


class _Store:
    def __init__(self) -> None:
        self.orders = _Orders()
        self.perpetual_portfolio = _PerpetualPortfolio()
        self.audit = _Audit()


class _Orders:
    def __init__(self) -> None:
        self.added = []

    async def add_if_absent(self, order):
        self.added.append(order)
        return True


class _PerpetualPortfolio:
    def __init__(self) -> None:
        self.entries = []
        self.saved = None

    async def append_entry(self, entry):
        self.entries.append(entry)
        return True

    async def save(self, ledger):
        self.saved = ledger


class _Audit:
    def __init__(self) -> None:
        self.events = []

    async def add(self, event):
        self.events.append(event)


def _bot() -> Bot:
    return Bot(
        id=uuid4(),
        config=BotConfig(
            name="Binance Demo Perpetual",
            strategy_type="mean_reversion_zscore",
            strategy_params={},
            symbol=SYMBOL,
            timeframe=Timeframe.H1,
            initial_capital=D("1000"),
            fee_rate=D("0.001"),
            slippage_bps=D("5"),
            mode=ExecutionMode.TESTNET,
            exchange="binance-usdm",
            connection_id=uuid4(),
            product=TradingProduct.LINEAR_PERPETUAL,
            leverage=2,
            margin_mode=MarginMode.ISOLATED,
            allow_short=True,
        ),
        desired_state=BotState.RUNNING,
        observed_state=BotState.RUNNING,
        config_version=1,
        created_at=T0,
        updated_at=T0,
    )


def _trader() -> PerpetualDemoTrader:
    return PerpetualDemoTrader(
        stores=lambda: None,  # type: ignore[arg-type]
        strategies=None,  # type: ignore[arg-type]
        exchanges=None,  # type: ignore[arg-type]
        resolver=None,
        clock=_Clock(),  # type: ignore[arg-type]
        ids=SimpleNamespace(new_id=uuid4),  # type: ignore[arg-type]
        executor=object(),  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_demo_entry_commits_a_reserved_intent_without_a_simulated_fill() -> None:
    bot = _bot()
    session = TradingSession(
        uuid4(), bot.id, 1, SessionStatus.ACTIVE, T0, mode=ExecutionMode.TESTNET.value
    )
    candle = make_candles(["100"], symbol=SYMBOL)[0]
    signal = Signal(
        Side.BUY,
        SYMBOL,
        SignalKind.ENTRY,
        "test entry",
        stop_loss=D("90"),
        take_profit=D("120"),
    )
    ledger = PerpetualLedger.new(bot.id, D("1000"))
    store = _Store()
    trader = _trader()

    await trader._open(store, bot, session, candle, ledger, MARKET, signal, D("0.5"), [])

    order = store.orders.added[0]
    assert order.status.value == "SUBMITTING"
    assert order.fills == []
    assert order.position_side is PositionSide.LONG
    assert order.planned_stop_price == D("90")
    assert ledger.position is None
    assert ledger.reserved_margin > 0
    assert store.perpetual_portfolio.saved is ledger
    assert store.perpetual_portfolio.entries[0].source == "binance_demo_order_intent"
    assert trader._pending == [order.id]
    assert store.audit.events[0].event_type == "order.intent_created"


@pytest.mark.parametrize(
    ("side", "stop_loss", "take_profit", "message"),
    [
        (Side.BUY, None, D("120"), "require a protective stop loss"),
        (Side.BUY, D("110"), D("120"), "invalid Futures Demo protective levels"),
        (Side.BUY, D("90"), D("80"), "invalid Futures Demo protective levels"),
        (Side.SELL, D("100.001"), D("80"), "invalid Futures Demo protective levels"),
    ],
)
@pytest.mark.asyncio
async def test_demo_entry_rejects_missing_or_directionally_invalid_protection_before_intent(
    side: Side,
    stop_loss: Decimal | None,
    take_profit: Decimal | None,
    message: str,
) -> None:
    bot = _bot()
    session = TradingSession(
        uuid4(), bot.id, 1, SessionStatus.ACTIVE, T0, mode=ExecutionMode.TESTNET.value
    )
    candle = make_candles(["100"], symbol=SYMBOL)[0]
    signal = Signal(
        side,
        SYMBOL,
        SignalKind.ENTRY,
        "unprotected test entry",
        stop_loss=stop_loss,
        take_profit=take_profit,
    )
    ledger = PerpetualLedger.new(bot.id, D("1000"))
    store = _Store()
    trader = _trader()

    with pytest.raises(OrderRejected, match=message):
        await trader._open(store, bot, session, candle, ledger, MARKET, signal, D("0.5"), [])

    assert store.orders.added == []
    assert ledger.position is None
    assert ledger.reserved_margin == 0
    assert store.perpetual_portfolio.entries == []
    assert trader._pending == []


@pytest.mark.asyncio
async def test_demo_reduce_only_intent_keeps_position_until_exchange_fill() -> None:
    bot = _bot()
    session = TradingSession(
        uuid4(), bot.id, 1, SessionStatus.ACTIVE, T0, mode=ExecutionMode.TESTNET.value
    )
    candle = make_candles(["100"], symbol=SYMBOL)[0]
    ledger = PerpetualLedger.new(bot.id, D("1000"))
    ledger.open_position(
        PositionSide.SHORT,
        D("0.5"),
        D("100"),
        leverage=2,
        stop_price=D("110"),
        take_profit_price=D("80"),
    )
    store = _Store()
    trader = _trader()

    await trader._close(
        store,
        bot,
        session,
        candle,
        ledger,
        MARKET,
        D("0.25"),
        D("95"),
        D("0.001"),
        False,
        "strategy exit",
    )

    order = store.orders.added[0]
    assert order.status.value == "SUBMITTING"
    assert order.reduce_only
    assert order.side is Side.BUY
    assert order.quantity == D("0.25")
    assert order.fills == []
    assert ledger.position is not None and ledger.position.quantity == D("0.5")
    assert trader._pending == [order.id]
    assert store.perpetual_portfolio.entries == []
