from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from core.errors import ConflictError
from factories import MARKET, T0
from modules.bots.domain.models import Bot, BotConfig, BotState, InvalidBotConfig
from modules.execution.domain.fills import simulate_market_fill
from modules.execution.domain.orders import (
    Fill,
    InvalidOrderTransition,
    Order,
    OrderStatus,
    make_client_order_id,
)
from modules.market_data.domain.models import Timeframe
from modules.portfolio.domain.models import InsufficientFunds, PortfolioState
from modules.risk_management.domain.models import (
    InvalidRiskLimits,
    RiskLimits,
    assess_signal,
    daily_loss_breached,
)
from modules.strategies.domain.types import Side, Signal, SignalKind
from modules.trading.domain.models import max_signal_age

BUY = Signal(Side.BUY, "BTC/USDT", SignalKind.ENTRY, "test")
SELL = Signal(Side.SELL, "BTC/USDT", SignalKind.EXIT, "test")
PRICE = Decimal(100)


def _order(side: Side = Side.BUY, quantity: str = "1") -> Order:
    return Order(
        id=uuid4(),
        bot_id=uuid4(),
        session_id=uuid4(),
        client_order_id="x",
        symbol="BTC/USDT",
        side=side,
        quantity=Decimal(quantity),
        bar_time=T0,
        created_at=T0,
    )


def _fill(side: Side, qty: str, price: str, fee: str = "0") -> Fill:
    return Fill(T0, side, Decimal(qty), Decimal(price), Decimal(fee))


# --- orders -------------------------------------------------------------------------------


def test_client_order_id_is_deterministic_per_bot_candle_and_side() -> None:
    bot = uuid4()
    first = make_client_order_id(bot, T0, Side.BUY)
    assert first == make_client_order_id(bot, T0, Side.BUY)
    assert first != make_client_order_id(bot, T0, Side.SELL)
    assert first != make_client_order_id(bot, T0 + timedelta(hours=1), Side.BUY)
    assert first != make_client_order_id(uuid4(), T0, Side.BUY)


def test_order_lifecycle_to_filled() -> None:
    order = _order()
    order.submit()
    order.apply_fill(_fill(Side.BUY, "1", "100"))
    assert order.status is OrderStatus.FILLED
    assert order.avg_fill_price == Decimal(100)


def test_partial_fills_accumulate_and_average_price() -> None:
    order = _order(quantity="2")
    order.submit()
    order.apply_fill(_fill(Side.BUY, "1", "100"))
    assert order.status is OrderStatus.PARTIALLY_FILLED
    order.apply_fill(_fill(Side.BUY, "1", "110"))
    assert order.status is OrderStatus.FILLED
    assert order.avg_fill_price == Decimal(105)


def test_order_state_machine_rejects_invalid_transitions() -> None:
    order = _order()
    with pytest.raises(InvalidOrderTransition):
        order.apply_fill(_fill(Side.BUY, "1", "100"))  # not submitted yet
    order.submit()
    order.reject("nope")
    with pytest.raises(InvalidOrderTransition):
        order.submit()  # terminal
    over = _order(quantity="1")
    over.submit()
    with pytest.raises(InvalidOrderTransition):
        over.apply_fill(_fill(Side.BUY, "2", "100"))


def test_simulated_fill_applies_slippage_and_fee() -> None:
    fill = simulate_market_fill(
        Side.BUY, Decimal("1.5"), PRICE, Decimal("0.001"), Decimal(10), MARKET, T0
    )
    assert fill.price == Decimal("100.1")
    assert fill.fee == fill.notional * Decimal("0.001")


# --- portfolio ----------------------------------------------------------------------------


def test_portfolio_round_trip_realized_pnl_is_net_of_fees() -> None:
    p = PortfolioState.new(uuid4(), Decimal(1000))
    p.apply_fill(_fill(Side.BUY, "9", "100", fee="1"))  # cost 901 incl. fee
    assert (p.cash, p.quantity) == (Decimal(99), Decimal(9))
    assert p.avg_entry_price == Decimal(901) / 9  # cost basis includes the buy fee
    p.apply_fill(_fill(Side.SELL, "9", "110", fee="1.1"))  # proceeds 990 - 1.1
    assert p.quantity == 0 and p.avg_entry_price == 0
    # the per-unit basis (901/9) is not exact in decimal, hence the tolerance
    assert abs(p.realized_pnl - (Decimal("988.9") - Decimal(901))) < Decimal("1e-20")
    assert p.cash == Decimal(99) + Decimal("988.9")
    assert p.fees_paid == Decimal("2.1")


def test_portfolio_rejects_overspending_and_overselling() -> None:
    p = PortfolioState.new(uuid4(), Decimal(100))
    with pytest.raises(InsufficientFunds):
        p.apply_fill(_fill(Side.BUY, "2", "100"))
    with pytest.raises(InsufficientFunds):
        p.apply_fill(_fill(Side.SELL, "1", "100"))


# --- risk ---------------------------------------------------------------------------------


def _assess(signal: Signal, portfolio: PortfolioState, **kwargs: object):  # type: ignore[no-untyped-def]
    params: dict[str, object] = {
        "fee_rate": Decimal("0.001"),
        "slippage_bps": Decimal(0),
        "limits": RiskLimits(),
        "kill_switch_active": False,
    }
    return assess_signal(signal, portfolio, PRICE, MARKET, **{**params, **kwargs})  # type: ignore[arg-type]


def test_buy_is_sized_to_cash_and_includes_fee() -> None:
    decision = _assess(BUY, PortfolioState.new(uuid4(), Decimal(1000)))
    assert decision.approved and decision.quantity is not None
    assert decision.quantity * PRICE * Decimal("1.001") <= Decimal(1000)
    assert decision.quantity % MARKET.step_size == 0


def test_position_fraction_and_order_notional_caps() -> None:
    wallet = PortfolioState.new(uuid4(), Decimal(1000))
    half = _assess(BUY, wallet, limits=RiskLimits(max_position_fraction=Decimal("0.5")))
    assert half.quantity is not None and half.quantity * PRICE <= Decimal(500)
    capped = _assess(BUY, wallet, limits=RiskLimits(max_order_notional=Decimal(200)))
    assert capped.quantity is not None and capped.quantity * PRICE <= Decimal(200)


def test_buy_rejected_when_kill_switch_in_position_or_below_minimum() -> None:
    wallet = PortfolioState.new(uuid4(), Decimal(1000))
    assert _assess(BUY, wallet, kill_switch_active=True).reason == "kill switch is active"
    held = PortfolioState(uuid4(), Decimal(500), quantity=Decimal(1))
    assert _assess(BUY, held).reason == "already in position"
    tiny = PortfolioState.new(uuid4(), Decimal(5))  # below the 10 min notional
    decision = _assess(BUY, tiny)
    assert not decision.approved and "minimum" in (decision.reason or "")


def test_exit_is_allowed_with_kill_switch_but_needs_a_position() -> None:
    held = PortfolioState(uuid4(), Decimal(0), quantity=Decimal("2"))
    decision = _assess(SELL, held, kill_switch_active=True)
    assert decision.approved and decision.quantity == Decimal(2)
    assert _assess(SELL, PortfolioState.new(uuid4(), Decimal(1000))).reason == "no position to sell"


def test_daily_loss_limit() -> None:
    limits = RiskLimits(max_daily_loss_pct=Decimal(5))
    assert not daily_loss_breached(Decimal(960), Decimal(1000), limits)
    assert daily_loss_breached(Decimal(950), Decimal(1000), limits)
    assert not daily_loss_breached(Decimal(1), Decimal(1000), RiskLimits(max_daily_loss_pct=None))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_position_fraction": Decimal(0)},
        {"max_position_fraction": Decimal("1.5")},
        {"max_order_notional": Decimal(0)},
        {"max_daily_loss_pct": Decimal(0)},
        {"max_daily_loss_pct": Decimal(101)},
    ],
)
def test_invalid_risk_limits(kwargs: dict[str, Decimal]) -> None:
    with pytest.raises(InvalidRiskLimits):
        RiskLimits(**kwargs)  # type: ignore[arg-type]


# --- bots ---------------------------------------------------------------------------------


def _bot(desired: BotState = BotState.STOPPED, observed: BotState = BotState.STOPPED) -> Bot:
    config = BotConfig(
        name="b",
        strategy_type="ema_crossover",
        strategy_params={},
        symbol="BTC/USDT",
        timeframe=Timeframe.H1,
        initial_capital=Decimal(1000),
        fee_rate=Decimal("0.001"),
        slippage_bps=Decimal(5),
    )
    return Bot(uuid4(), config, desired, observed, 1, T0, T0)


def test_bot_command_transitions() -> None:
    bot = _bot()
    bot.request_start()
    assert bot.desired_state is BotState.RUNNING
    with pytest.raises(ConflictError):
        bot.request_start()
    bot.request_pause()
    assert bot.desired_state is BotState.PAUSED
    with pytest.raises(ConflictError):
        bot.request_pause()
    bot.request_start()  # resume
    bot.request_stop()
    assert bot.desired_state is BotState.STOPPED
    with pytest.raises(ConflictError):
        _bot().request_stop()  # already fully stopped


def test_bot_is_editable_only_when_stopped() -> None:
    _bot().ensure_editable()
    _bot(observed=BotState.ERROR).ensure_editable()
    with pytest.raises(ConflictError):
        _bot(desired=BotState.RUNNING).ensure_editable()
    with pytest.raises(ConflictError):
        _bot(observed=BotState.RUNNING).ensure_editable()  # stop requested but not yet applied


def test_bot_config_validation_and_signal_age() -> None:
    with pytest.raises(InvalidBotConfig):
        BotConfig("", "s", {}, "BTC/USDT", Timeframe.H1, Decimal(1), Decimal(0), Decimal(0))
    with pytest.raises(InvalidBotConfig):
        BotConfig("n", "s", {}, "BTC/USDT", Timeframe.H1, Decimal(0), Decimal(0), Decimal(0))
    assert max_signal_age(Timeframe.M5) == timedelta(minutes=2, seconds=30)
    assert max_signal_age(Timeframe.D1) == timedelta(minutes=15)  # capped
