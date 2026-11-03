from datetime import timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest

from core.ids import UuidGenerator
from factories import T0
from modules.bots.domain.models import Bot, BotConfig, BotState, ExecutionMode
from modules.exchanges.application.ports import VenueOrder
from modules.exchanges.domain.models import MarginMode, PositionSide, TradingProduct
from modules.exchanges.errors import UnknownOutcome
from modules.execution.domain.orders import Fill, Order, OrderStatus
from modules.market_data.domain.models import MarketInfo, Timeframe
from modules.portfolio.domain.perpetual_ledger import PerpetualLedgerEntry
from modules.portfolio.domain.perpetuals import PerpetualLedger
from modules.risk_management.domain.models import RiskLimits
from modules.strategies.domain.types import Side
from modules.trading.application.orders import OrderExecutor

D = Decimal


class _PerpetualPortfolio:
    def __init__(self, ledger: PerpetualLedger) -> None:
        self.ledger = ledger
        self.entries: list[PerpetualLedgerEntry] = []

    async def get(self, bot_id) -> PerpetualLedger:
        return self.ledger

    async def save(self, ledger: PerpetualLedger) -> None:
        self.ledger = ledger

    async def append_entry(self, entry: PerpetualLedgerEntry) -> bool:
        self.entries.append(entry)
        return True


class _Orders:
    def __init__(self, order: Order) -> None:
        self.order = order
        self.applied_fills: list[Fill] = []

    async def update(self, order: Order, fills: list[Fill]) -> None:
        self.order = order
        self.applied_fills.extend(fills)

    async def get_by_client_id(self, bot_id, client_order_id: str) -> Order | None:
        return self.order if self.order.client_order_id == client_order_id else None

    async def get(self, order_id):
        return self.order if self.order.id == order_id else None


class _Store:
    def __init__(self, ledger: PerpetualLedger, order: Order) -> None:
        self.perpetual_portfolio = _PerpetualPortfolio(ledger)
        self.portfolio = self
        self.orders = _Orders(order)
        self.bots = self
        self.audit = self
        self.events: list[Any] = []
        self.desired_state: BotState | None = None
        self.observed_state: BotState | None = None
        self.observed_error: str | None = None

    async def set_desired(self, bot_id, state: BotState) -> None:
        self.desired_state = state

    async def set_observed(self, bot_id, state: BotState, error: str | None) -> None:
        self.observed_state = state
        self.observed_error = error

    async def commit(self) -> None:
        return None

    async def add(self, event: Any) -> None:
        self.events.append(event)

    async def get(self, _bot_id):
        return None


class _StoreContext:
    def __init__(self, store: _Store) -> None:
        self.store = store

    async def __aenter__(self) -> _Store:
        return self.store

    async def __aexit__(self, *args: object) -> None:
        return None


class _Clock:
    @staticmethod
    def now():
        return T0


class _Resolver:
    def __init__(self, exchange: Any) -> None:
        self.exchange = exchange

    async def exchange_for(self, _connection_id):
        return self.exchange


class _AmbiguousExchange:
    def __init__(self) -> None:
        self.submissions = 0

    async def create_market_order(self, _request) -> None:
        self.submissions += 1
        raise UnknownOutcome("response timed out after request submission")


def _executor(store: _Store) -> OrderExecutor:
    def factory():
        return _StoreContext(store)

    return OrderExecutor(
        factory,
        resolver=None,  # type: ignore[arg-type]
        clock=_Clock(),  # type: ignore[arg-type]
        ids=UuidGenerator(),
        absent_after=timedelta(seconds=30),
    )


def _bot() -> Bot:
    config = BotConfig(
        name="test futures bot",
        strategy_type="ema_crossover",
        strategy_params={"fast_period": 2, "slow_period": 3},
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.H1,
        initial_capital=D("1000"),
        fee_rate=D("0.001"),
        slippage_bps=D(0),
        mode=ExecutionMode.TESTNET,
        exchange="binance-usdm",
        connection_id=uuid4(),
        product=TradingProduct.LINEAR_PERPETUAL,
        leverage=2,
        margin_mode=MarginMode.ISOLATED,
        risk=RiskLimits(),
    )
    return Bot(uuid4(), config, BotState.RUNNING, BotState.RUNNING, 1, T0, T0)


def _order(bot: Bot) -> Order:
    order = Order(
        id=uuid4(),
        bot_id=bot.id,
        session_id=uuid4(),
        client_order_id="futures-partial-entry",
        symbol=bot.config.symbol,
        side=Side.BUY,
        quantity=D("1"),
        bar_time=T0,
        created_at=T0,
        product=TradingProduct.LINEAR_PERPETUAL,
        position_side=PositionSide.LONG,
        leverage=2,
        status=OrderStatus.SUBMITTING,
        reserved_margin=D("51"),
        planned_stop_price=D("90"),
        reference_price=D("100"),
    )
    return order


@pytest.mark.asyncio
async def test_executor_rejects_legacy_live_futures_order_before_exchange_call() -> None:
    bot = _bot()
    # Simulate an inconsistent legacy DB row. BotConfig correctly refuses this mode in normal
    # construction, so bypass the frozen config guard to exercise the executor boundary itself.
    object.__setattr__(bot.config, "mode", ExecutionMode.LIVE)
    order = _order(bot)
    ledger = PerpetualLedger.new(bot.id, D("1000"))
    ledger.reserve(order.reserved_margin)
    store = _Store(ledger, order)
    executor = _executor(store)

    await executor.submit(bot, order.id)

    assert order.status is OrderStatus.REJECTED
    assert order.reject_reason == "USD-M Futures live order execution is not enabled"
    assert ledger.reserved_margin == 0
    assert store.events[-1].event_type == "risk.futures_live_execution_blocked"


@pytest.mark.asyncio
async def test_ambiguous_futures_order_keeps_reservation_and_is_not_resubmitted() -> None:
    bot = _bot()
    order = _order(bot)
    ledger = PerpetualLedger.new(bot.id, D("1000"))
    ledger.reserve(order.reserved_margin)
    store = _Store(ledger, order)
    exchange = _AmbiguousExchange()
    executor = OrderExecutor(
        lambda: _StoreContext(store),  # type: ignore[arg-type]
        resolver=_Resolver(exchange),  # type: ignore[arg-type]
        clock=_Clock(),  # type: ignore[arg-type]
        ids=UuidGenerator(),
        absent_after=timedelta(seconds=30),
    )

    await executor.submit(bot, order.id)
    await executor.submit(bot, order.id)

    assert exchange.submissions == 1
    assert order.status is OrderStatus.UNKNOWN
    assert ledger.reserved_margin == D("51")
    assert ledger.position is None
    assert [event.event_type for event in store.events] == ["order.unknown"]


def _venue(order: Order, status: OrderStatus, fills: tuple[Fill, ...]) -> VenueOrder:
    return VenueOrder(
        client_order_id=order.client_order_id,
        exchange_order_id="venue-1",
        symbol=order.symbol,
        side=order.side,
        quantity=order.quantity,
        status=status,
        filled_quantity=sum((fill.quantity for fill in fills), D(0)),
        fills=fills,
    )


@pytest.mark.asyncio
async def test_partial_futures_fills_dedupe_and_release_margin() -> None:
    bot = _bot()
    order = _order(bot)
    ledger = PerpetualLedger.new(bot.id, D("1000"))
    ledger.reserve(order.reserved_margin)
    store = _Store(ledger, order)
    executor = _executor(store)
    fill_one = Fill(T0, Side.BUY, D("0.5"), D("100"), D("0.1"), trade_id="trade-1")
    fill_two = Fill(
        T0 + timedelta(seconds=1), Side.BUY, D("0.25"), D("100"), D("0.05"), trade_id="trade-2"
    )

    await executor._apply_perpetual_fills(
        store, bot, order, _venue(order, OrderStatus.PARTIALLY_FILLED, (fill_one,))
    )
    assert order.status is OrderStatus.PARTIALLY_FILLED
    assert order.filled_quantity == D("0.5")
    assert order.reserved_margin == D("25.9")
    assert ledger.reserved_margin == D("25.9")
    assert ledger.position is not None and ledger.position.quantity == D("0.5")

    # The exchange repeats the first execution in its cumulative fill list. Trade ID dedupe
    # applies only the newly reported partial fill.
    cumulative_fills = (fill_one, fill_two)
    await executor._apply_perpetual_fills(
        store, bot, order, _venue(order, OrderStatus.PARTIALLY_FILLED, cumulative_fills)
    )
    assert order.filled_quantity == D("0.75")
    assert order.reserved_margin == D("13.35")
    assert ledger.position is not None and ledger.position.quantity == D("0.75")
    assert [fill.trade_id for fill in store.orders.applied_fills] == ["trade-1", "trade-2"]

    await executor._apply_perpetual_fills(
        store, bot, order, _venue(order, OrderStatus.CANCELED, cumulative_fills)
    )
    assert order.status is OrderStatus.CANCELED
    assert order.reserved_margin == ledger.reserved_margin == 0
    assert ledger.position is not None and ledger.position.quantity == D("0.75")
    releases = [entry for entry in store.perpetual_portfolio.entries if entry.reserved_margin_delta]
    assert [entry.reserved_margin_delta for entry in releases] == [
        D("-25.1"),
        D("-12.55"),
        D("-13.35"),
    ]


@pytest.mark.asyncio
async def test_cumulative_partial_close_fills_release_margin_and_realize_pnl_once() -> None:
    bot = _bot()
    ledger = PerpetualLedger.new(bot.id, D("1000"))
    ledger.open_position(PositionSide.LONG, D("2"), D("100"), leverage=2)
    order = Order(
        id=uuid4(),
        bot_id=bot.id,
        session_id=uuid4(),
        client_order_id="futures-partial-close",
        symbol=bot.config.symbol,
        side=Side.SELL,
        quantity=D("2"),
        bar_time=T0,
        created_at=T0,
        product=TradingProduct.LINEAR_PERPETUAL,
        position_side=PositionSide.LONG,
        leverage=2,
        reduce_only=True,
        status=OrderStatus.SUBMITTING,
    )
    store = _Store(ledger, order)
    executor = _executor(store)
    first = Fill(T0, Side.SELL, D("0.4"), D("110"), D("0.2"), trade_id="close-1")
    second = Fill(
        T0 + timedelta(seconds=1),
        Side.SELL,
        D("0.6"),
        D("90"),
        D("0.3"),
        trade_id="close-2",
    )

    await executor._apply_perpetual_fills(
        store, bot, order, _venue(order, OrderStatus.PARTIALLY_FILLED, (first,))
    )
    assert ledger.position is not None
    assert ledger.position.quantity == D("1.6")
    assert ledger.position.isolated_margin == D("80")
    assert ledger.wallet_balance == D("923.8")
    assert ledger.realized_pnl == D("3.8")

    await executor._apply_perpetual_fills(
        store,
        bot,
        order,
        _venue(order, OrderStatus.PARTIALLY_FILLED, (first, second)),
    )

    assert order.status is OrderStatus.PARTIALLY_FILLED
    assert order.filled_quantity == D("1.0")
    assert ledger.position is not None
    assert ledger.position.quantity == D("1.0")
    assert ledger.position.isolated_margin == D("50")
    assert ledger.wallet_balance == D("947.5")
    assert ledger.realized_pnl == D("-2.5")
    assert [fill.trade_id for fill in store.orders.applied_fills] == ["close-1", "close-2"]
    close_entries = [
        entry
        for entry in store.perpetual_portfolio.entries
        if entry.kind.value == "position_reduced"
    ]
    assert [entry.isolated_margin_delta for entry in close_entries] == [D("-20"), D("-30")]
    assert [entry.realized_pnl_delta for entry in close_entries] == [D("3.8"), D("-6.3")]


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel_confirmed", [True, False])
async def test_partial_close_replaces_the_native_stop_with_updated_quantity(
    monkeypatch: pytest.MonkeyPatch, cancel_confirmed: bool
) -> None:
    bot = _bot()
    old_stop_id = "futures-old-stop"
    ledger = PerpetualLedger.new(bot.id, D("1000"))
    ledger.open_position(
        PositionSide.LONG,
        D("0.75"),
        D("100"),
        leverage=2,
        stop_price=D("90"),
    )
    ledger.stop_order_client_id = old_stop_id
    store = _Store(ledger, _order(bot))
    store.orders.order = Order(
        id=uuid4(),
        bot_id=bot.id,
        session_id=uuid4(),
        client_order_id=old_stop_id,
        symbol=bot.config.symbol,
        side=Side.SELL,
        quantity=D("1"),
        bar_time=T0,
        created_at=T0,
        product=TradingProduct.LINEAR_PERPETUAL,
        position_side=PositionSide.LONG,
        leverage=2,
        reduce_only=True,
        status=OrderStatus.OPEN,
        order_type="stop_loss",
        stop_price=D("90"),
    )
    executor = _executor(store)
    canceled: list[str] = []
    replacements: list[str] = []

    async def cancel_stale_stop(bot_arg, exchange, client_order_id: str) -> bool:
        assert bot_arg.id == bot.id
        canceled.append(client_order_id)
        if cancel_confirmed:
            ledger.stop_order_client_id = None  # terminal cancel confirmed by the venue
        return False

    async def replace_stop(bot_arg, entry_client_order_id: str) -> None:
        assert bot_arg.id == bot.id
        replacements.append(entry_client_order_id)

    monkeypatch.setattr(executor, "_cancel_native_stop", cancel_stale_stop)
    monkeypatch.setattr(executor, "ensure_native_stop", replace_stop)

    resized = await executor._resize_perpetual_stop(
        bot,
        exchange=object(),  # cancel/replace behavior is asserted through the stubs above
        market=MarketInfo(
            bot.config.symbol,
            step_size=D("0.01"),
            tick_size=D("0.01"),
            min_quantity=D("0.01"),
            min_notional=D("5"),
        ),
    )

    assert resized is True
    assert canceled == [old_stop_id]
    if cancel_confirmed:
        assert len(replacements) == 1
        assert replacements[0] != old_stop_id
        assert store.desired_state is None
    else:
        assert replacements == []
        assert store.desired_state is BotState.PAUSED
        assert store.observed_state is BotState.PAUSED
        assert store.observed_error == (
            "Binance did not confirm cancellation of the outdated Futures stop"
        )


@pytest.mark.asyncio
async def test_rejected_futures_stop_is_rearmed_while_position_remains_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bot = _bot()
    stop_id = "futures-rejected-stop"
    ledger = PerpetualLedger.new(bot.id, D("1000"))
    ledger.open_position(PositionSide.LONG, D("1"), D("100"), 2, stop_price=D("90"))
    ledger.stop_order_client_id = stop_id
    order = Order(
        id=uuid4(),
        bot_id=bot.id,
        session_id=uuid4(),
        client_order_id=stop_id,
        symbol=bot.config.symbol,
        side=Side.SELL,
        quantity=D("1"),
        bar_time=T0,
        created_at=T0,
        product=TradingProduct.LINEAR_PERPETUAL,
        position_side=PositionSide.LONG,
        leverage=2,
        reduce_only=True,
        status=OrderStatus.OPEN,
        order_type="stop_loss",
        stop_price=D("90"),
    )
    store = _Store(ledger, order)
    executor = _executor(store)
    venue = _venue(order, OrderStatus.REJECTED, ())

    class Exchange:
        async def fetch_order(self, symbol: str, client_order_id: str):
            assert symbol == bot.config.symbol and client_order_id == stop_id
            return venue

    async def get_exchange(bot_arg):
        assert bot_arg.id == bot.id
        return Exchange()

    async def min_quantity(bot_arg):
        return D("0.01")

    replacements: list[str] = []

    async def rearm(bot_arg, entry_client_order_id: str) -> None:
        replacements.append(entry_client_order_id)

    monkeypatch.setattr(executor, "_exchange", get_exchange)
    monkeypatch.setattr(executor, "_min_quantity", min_quantity)
    monkeypatch.setattr(executor, "ensure_native_stop", rearm)

    await executor.sync_native_stop(bot)

    assert order.status is OrderStatus.REJECTED
    assert ledger.position is not None
    assert ledger.stop_order_client_id is None
    assert replacements == [stop_id]
