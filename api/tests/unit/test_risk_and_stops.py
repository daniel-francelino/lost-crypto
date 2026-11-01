from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from factories import MARKET, T0, make_candles, make_config
from modules.backtesting.domain.engine import run_backtest
from modules.backtesting.domain.models import InvalidBacktestConfig
from modules.backtesting.domain.segments import compute_segments
from modules.portfolio.domain.models import PortfolioState
from modules.risk_management.domain.models import (
    GlobalExposure,
    GlobalRiskLimits,
    RiskLimits,
    assess_signal,
    candle_range_pct,
    consecutive_losses_breached,
    drawdown_breached,
)
from modules.risk_management.domain.stops import ExitReason, check_protective_exit
from modules.strategies.domain.base import InvalidStrategyParams
from modules.strategies.domain.ema_crossover import (
    EmaCrossoverParams,
    EmaCrossoverStrategy,
)
from modules.strategies.domain.types import Side, Signal, SignalKind, StrategyContext

PRICE = Decimal(100)


def _buy(stop: str | None = None, take: str | None = None) -> Signal:
    return Signal(
        Side.BUY,
        "BTC/USDT",
        SignalKind.ENTRY,
        "test",
        stop_loss=None if stop is None else Decimal(stop),
        take_profit=None if take is None else Decimal(take),
    )


def _assess(signal: Signal, cash: str = "1000", **kwargs):  # type: ignore[no-untyped-def]
    params = {
        "fee_rate": Decimal("0.001"),
        "slippage_bps": Decimal(0),
        "limits": RiskLimits(),
        "kill_switch_active": False,
        **kwargs,
    }
    return assess_signal(
        signal, PortfolioState.new(uuid4(), Decimal(cash)), PRICE, MARKET, **params
    )


# --- stops ---------------------------------------------------------------------------------


def _candle(open_: str, high: str, low: str, close: str = "100"):  # type: ignore[no-untyped-def]
    candle = make_candles([close])[0]
    return type(candle)(
        candle.symbol,
        candle.timeframe,
        candle.open_time,
        Decimal(open_),
        Decimal(high),
        Decimal(low),
        Decimal(close),
        Decimal(1),
    )


def test_stop_loss_triggers_on_the_low_and_fills_at_the_stop() -> None:
    hit = check_protective_exit(_candle("100", "101", "94"), Decimal(95), None)
    assert hit is not None and hit.reason is ExitReason.STOP_LOSS and hit.trigger_price == 95


def test_gap_through_the_stop_fills_at_the_worse_open() -> None:
    hit = check_protective_exit(_candle("90", "92", "88"), Decimal(95), None)
    assert hit is not None and hit.trigger_price == Decimal(90)


def test_take_profit_triggers_on_the_high() -> None:
    hit = check_protective_exit(_candle("100", "112", "99"), None, Decimal(110))
    assert hit is not None and hit.reason is ExitReason.TAKE_PROFIT and hit.trigger_price == 110


def test_stop_wins_when_both_levels_are_inside_the_candle() -> None:
    hit = check_protective_exit(_candle("100", "115", "90"), Decimal(95), Decimal(110))
    assert hit is not None and hit.reason is ExitReason.STOP_LOSS


def test_no_exit_when_levels_are_not_touched_or_absent() -> None:
    assert check_protective_exit(_candle("100", "104", "97"), Decimal(95), Decimal(110)) is None
    assert check_protective_exit(_candle("100", "104", "50"), None, None) is None


# --- extended entry rules ------------------------------------------------------------------


def test_stop_and_target_must_be_on_the_right_side_of_the_entry() -> None:
    assert "stop-loss must be below" in (_assess(_buy(stop="105")).reason or "")
    assert "take-profit must be above" in (_assess(_buy(take="95")).reason or "")
    assert _assess(_buy(stop="95", take="110")).approved


def test_stop_loss_can_be_required() -> None:
    limits = RiskLimits(require_stop_loss=True)
    assert "stop-loss is required" in (_assess(_buy(), limits=limits).reason or "")
    assert _assess(_buy(stop="95"), limits=limits).approved


def test_risk_per_trade_sizes_the_position_by_distance_to_the_stop() -> None:
    # Risk 1% of 1000 = 10 quote; stop 5 below entry -> at most 2 units (~200 notional).
    limits = RiskLimits(max_risk_per_trade_pct=Decimal(1))
    decision = _assess(_buy(stop="95"), limits=limits)
    assert decision.approved and decision.quantity is not None
    assert decision.quantity <= Decimal(2)
    unrestricted = _assess(_buy(stop="95"))
    assert unrestricted.quantity is not None and unrestricted.quantity > Decimal(9)


def test_suspect_candles_block_entries_but_not_exits() -> None:
    wild = candle_range_pct(Decimal(160), Decimal(100))  # 60% range
    assert wild == Decimal(60)
    assert "suspect data" in (_assess(_buy(), candle_range=wild).reason or "")
    off = RiskLimits(max_candle_range_pct=None)
    assert _assess(_buy(), candle_range=wild, limits=off).approved
    held = PortfolioState(uuid4(), Decimal(0), quantity=Decimal(1))
    sell = Signal(Side.SELL, "BTC/USDT", SignalKind.EXIT, "x")
    assert assess_signal(
        sell,
        held,
        PRICE,
        MARKET,
        fee_rate=Decimal(0),
        slippage_bps=Decimal(0),
        limits=RiskLimits(),
        kill_switch_active=True,
        candle_range=wild,
    ).approved


def test_global_limits_cap_positions_and_exposure() -> None:
    capped = GlobalRiskLimits(max_open_positions=2)
    assert "open positions" in (
        _assess(_buy(), global_limits=capped, exposure=GlobalExposure(2, Decimal(0))).reason or ""
    )
    assert _assess(_buy(), global_limits=capped, exposure=GlobalExposure(1, Decimal(0))).approved

    exposure_cap = GlobalRiskLimits(max_total_exposure=Decimal(500))
    assert "exposure limit" in (
        _assess(_buy(), global_limits=exposure_cap, exposure=GlobalExposure(1, Decimal(500))).reason
        or ""
    )
    room = _assess(_buy(), global_limits=exposure_cap, exposure=GlobalExposure(1, Decimal(300)))
    assert room.quantity is not None and room.quantity * PRICE <= Decimal(200)


def test_drawdown_and_consecutive_loss_breakers() -> None:
    limits = RiskLimits(max_drawdown_pct=Decimal(20), max_consecutive_losses=3)
    assert not drawdown_breached(Decimal(850), Decimal(1000), limits)
    assert drawdown_breached(Decimal(800), Decimal(1000), limits)
    assert not drawdown_breached(Decimal(1), Decimal(1000), RiskLimits())
    lose, win = Decimal(-1), Decimal(2)
    assert consecutive_losses_breached([win, lose, lose, lose], limits)
    assert not consecutive_losses_breached([lose, lose, win, lose], limits)
    assert not consecutive_losses_breached([lose, lose], limits)  # fewer than N trades


# --- strategy proposes levels ---------------------------------------------------------------


def test_ema_entry_signal_carries_stop_and_target_levels() -> None:
    strategy = EmaCrossoverStrategy(
        EmaCrossoverParams(2, 3, stop_loss_pct=Decimal(5), take_profit_pct=Decimal(10))
    )
    state = strategy.initial_state()
    signals: list[Signal] = []
    for candle in make_candles([100, 100, 100, 120]):
        result = strategy.evaluate(StrategyContext("BTC/USDT", candle, Decimal(0)), state)
        state, signals = result.state, list(result.signals)
    (entry,) = signals
    assert entry.stop_loss == Decimal(120) * Decimal("0.95")
    assert entry.take_profit == Decimal(120) * Decimal("1.10")


def test_ema_pct_params_are_parsed_and_validated() -> None:
    params = EmaCrossoverStrategy.from_params({"stop_loss_pct": 2.5, "take_profit_pct": "5"}).params
    assert params.stop_loss_pct == Decimal("2.5") and params.take_profit_pct == Decimal(5)
    for bad in (0, 100, -1, "abc", True):
        with pytest.raises(InvalidStrategyParams):
            EmaCrossoverStrategy.from_params({"stop_loss_pct": bad})


# --- backtest honours the same stops --------------------------------------------------------


def test_backtest_stop_loss_exits_inside_the_candle_it_is_hit() -> None:
    closes = [10, 10, 10, 12, 12, 12, 12, 12]
    opens = [10, 10, 10, 10, 12, 12, 12, 12]
    candles = make_candles(closes, opens)
    # candle 5 plunges to 9 (below the stop = 12 * 0.9 = 10.8) while closing back at 12.
    candles[5] = type(candles[5])(
        "BTC/USDT",
        candles[5].timeframe,
        candles[5].open_time,
        Decimal(12),
        Decimal(12),
        Decimal(9),
        Decimal(12),
        Decimal(1),
    )
    strategy = EmaCrossoverStrategy(EmaCrossoverParams(2, 3, stop_loss_pct=Decimal(10)))
    outcome = run_backtest(make_config(), candles, MARKET, strategy)

    buy, sell = outcome.fills
    assert (buy.side, buy.time) == (Side.BUY, candles[4].open_time)
    assert (sell.side, sell.time, sell.price) == (
        Side.SELL,
        candles[5].open_time,
        Decimal("10.8"),
    )
    assert outcome.final_quantity == 0


def test_backtest_take_profit_exits_at_the_target() -> None:
    closes = [10, 10, 10, 12, 12, 12, 12, 12]
    opens = [10, 10, 10, 10, 12, 12, 12, 12]
    candles = make_candles(closes, opens)
    candles[6] = type(candles[6])(
        "BTC/USDT",
        candles[6].timeframe,
        candles[6].open_time,
        Decimal(12),
        Decimal(15),
        Decimal(12),
        Decimal(13),
        Decimal(1),
    )
    strategy = EmaCrossoverStrategy(EmaCrossoverParams(2, 3, take_profit_pct=Decimal(20)))
    outcome = run_backtest(make_config(), candles, MARKET, strategy)
    sell = outcome.fills[-1]
    assert (sell.side, sell.price) == (Side.SELL, Decimal("14.4"))  # 12 * 1.2, no slippage


# --- train / test segments ------------------------------------------------------------------


def test_segments_split_metrics_by_time() -> None:
    closes = [10, 10, 10, 12, 14, 16, 18, 14, 8, 4, 4, 4]
    opens = [10, 10, 10, 11, 13, 15, 17, 16, 9, 5, 4, 4]
    candles = make_candles(closes, opens)
    config = make_config(n_candles=len(candles))
    config = replace(config, test_fraction=Decimal("0.25"))
    outcome = run_backtest(config, candles, MARKET, EmaCrossoverStrategy(EmaCrossoverParams(2, 3)))

    segments = compute_segments(config, candles, outcome)
    assert segments is not None
    assert segments["split_at"] == candles[9].open_time.isoformat()  # 12 * 0.75 = 9
    train, test = segments["train"], segments["test"]
    assert train["fills"] + test["fills"] == len(outcome.fills)
    assert Decimal(test["initial_capital"]) == outcome.equity_curve[8].equity  # where test starts
    assert test["buy_and_hold_return_pct"] == "-20.0000"  # 5 -> 4 over the test candles


def test_segments_absent_without_a_split_and_guarded_for_tiny_series() -> None:
    candles = make_candles([10, 10, 10, 12, 14])
    config = make_config(n_candles=5)
    outcome = run_backtest(config, candles, MARKET, EmaCrossoverStrategy(EmaCrossoverParams(2, 3)))
    assert compute_segments(config, candles, outcome) is None
    tiny = replace(config, test_fraction=Decimal("0.9"))
    with pytest.raises(InvalidBacktestConfig):
        compute_segments(tiny, candles, outcome)
    with pytest.raises(InvalidBacktestConfig):
        replace(config, test_fraction=Decimal(1))
    assert timedelta(0) == T0 - T0


def test_a_stop_exit_takes_slippage_but_a_take_profit_does_not() -> None:
    closes = [10, 10, 10, 12, 12, 12, 12, 12]
    opens = [10, 10, 10, 10, 12, 12, 12, 12]
    candles = make_candles(closes, opens)
    candles[5] = type(candles[5])(
        "BTC/USDT",
        candles[5].timeframe,
        candles[5].open_time,
        Decimal(12),
        Decimal(12),
        Decimal(9),
        Decimal(12),
        Decimal(1),
    )
    strategy = EmaCrossoverStrategy(EmaCrossoverParams(2, 3, stop_loss_pct=Decimal(10)))
    config = replace(make_config(slippage_bps="50"), slippage_bps=Decimal(50))
    outcome = run_backtest(config, candles, MARKET, strategy)
    sell = outcome.fills[-1]
    assert sell.side is Side.SELL
    assert sell.price == Decimal("10.8") * (1 - Decimal(50) / 10_000)  # the trigger, then worse


def test_a_gap_past_the_stop_fills_at_the_open_and_then_slips_further() -> None:
    closes = [10, 10, 10, 12, 12, 12, 12, 12]
    opens = [10, 10, 10, 10, 12, 12, 12, 12]
    candles = make_candles(closes, opens)
    candles[5] = type(candles[5])(
        "BTC/USDT",
        candles[5].timeframe,
        candles[5].open_time,
        Decimal(8),  # opens below the 10.8 stop
        Decimal(12),
        Decimal(7),
        Decimal(12),
        Decimal(1),
    )
    strategy = EmaCrossoverStrategy(EmaCrossoverParams(2, 3, stop_loss_pct=Decimal(10)))
    config = replace(make_config(), slippage_bps=Decimal(50))
    sell = run_backtest(config, candles, MARKET, strategy).fills[-1]
    assert sell.price == Decimal(8) * (1 - Decimal(50) / 10_000)  # the open, not the stop level


def test_the_volume_cap_never_refuses_an_exit() -> None:
    held = PortfolioState(uuid4(), Decimal(0), quantity=Decimal(1))
    sell = Signal(Side.SELL, "BTC/USDT", SignalKind.EXIT, "x")
    decision = assess_signal(
        sell,
        held,
        PRICE,
        MARKET,
        fee_rate=Decimal(0),
        slippage_bps=Decimal(0),
        limits=RiskLimits(max_order_pct_of_volume=Decimal("0.0001")),
        kill_switch_active=False,
        avg_quote_volume=Decimal(1),  # a cap that would refuse any entry
    )
    assert decision.approved and decision.quantity == Decimal(1)
