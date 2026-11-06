"""Multi-timeframe trend pullback: 1d decides the side, 4h confirms, 1h times the entry."""

import math
from decimal import Decimal
from typing import Any

import pytest

from factories import make_candles
from modules.exchanges.domain.models import PositionSide
from modules.market_data.domain.models import Candle, Timeframe
from modules.market_data.domain.trend import TrendTrackerState
from modules.strategies.domain.base import InvalidStrategyParams
from modules.strategies.domain.mtf_trend_pullback import MtfTrendPullbackStrategy
from modules.strategies.domain.types import Side, Signal, SignalKind, StrategyContext
from modules.trading.domain.models import MAX_WARMUP_CANDLES, warmup_candles

SYMBOL = "BTC/USDT"


def _wavy(count: int, start: float, drift: float, amplitude: float = 8.0) -> list[str]:
    """Hourly closes: a steady drift plus a 10-hour wiggle, so the 1h price keeps crossing
    its EMA (pullbacks) while the higher timeframes trend."""
    return [
        f"{start + drift * i + amplitude * math.sin(2 * math.pi * i / 10):.2f}"
        for i in range(count)
    ]


def _run(
    candles: list[Candle], *, allow_short: bool = False, params: dict[str, Any] | None = None
) -> tuple[list[tuple[int, Signal]], TrendTrackerState]:
    strategy = MtfTrendPullbackStrategy.from_params(params or {})
    state = strategy.initial_state()
    quantity, side = Decimal(0), None
    emitted: list[tuple[int, Signal]] = []
    for i, candle in enumerate(candles):
        ctx = StrategyContext(SYMBOL, candle, quantity, side, allow_short)
        result = strategy.evaluate(ctx, state)
        state = result.state
        for signal in result.signals:
            emitted.append((i, signal))
            if signal.kind is SignalKind.ENTRY:
                quantity = Decimal(1)
                side = PositionSide.LONG if signal.side is Side.BUY else PositionSide.SHORT
            else:
                quantity, side = Decimal(0), None
    return emitted, state


def test_it_declares_the_history_it_needs() -> None:
    strategy = MtfTrendPullbackStrategy.from_params({})
    # 20 daily EMA + slope + the dropped partial day = 24 days, plus a day of margin.
    assert strategy.required_history_candles() == 24 * 24 + 24
    assert warmup_candles(0) == 300
    assert warmup_candles(strategy.required_history_candles()) == 600
    assert warmup_candles(10_000) == MAX_WARMUP_CANDLES


def test_params_that_need_more_history_than_one_request_are_rejected() -> None:
    with pytest.raises(InvalidStrategyParams):
        MtfTrendPullbackStrategy.from_params({"daily_ema_period": 31})
    with pytest.raises(InvalidStrategyParams):
        MtfTrendPullbackStrategy.from_params({"h4_ema_period": 400})
    with pytest.raises(InvalidStrategyParams):
        MtfTrendPullbackStrategy.from_params({"atr_multiple": 0})


def test_nothing_is_signalled_before_the_daily_ema_is_warm() -> None:
    candles = make_candles(_wavy(1200, 1000, 0.5))
    emitted, _ = _run(candles)
    assert emitted, "an uptrend with pullbacks must produce entries"
    assert emitted[0][0] >= 21 * 24  # 20 completed days + slope window


def test_an_uptrend_is_only_bought_with_a_stop_below() -> None:
    candles = make_candles(_wavy(1500, 1000, 0.5))
    emitted, _ = _run(candles, allow_short=True)
    entries = [(i, s) for i, s in emitted if s.kind is SignalKind.ENTRY]
    assert entries
    for i, signal in entries:
        assert signal.side is Side.BUY
        assert signal.stop_loss is not None
        assert signal.stop_loss < candles[i].close


def test_a_downtrend_is_shorted_with_a_stop_above_only_when_shorts_are_allowed() -> None:
    candles = make_candles(_wavy(1500, 3000, -0.5))
    assert _run(candles, allow_short=False)[0] == []
    emitted, _ = _run(candles, allow_short=True)
    entries = [(i, s) for i, s in emitted if s.kind is SignalKind.ENTRY]
    assert entries
    for i, signal in entries:
        assert signal.side is Side.SELL
        assert signal.stop_loss is not None
        assert signal.stop_loss > candles[i].close


def test_a_market_that_goes_nowhere_is_not_traded() -> None:
    assert _run(make_candles(["1000"] * 1500), allow_short=True)[0] == []


def test_a_long_exits_when_the_higher_timeframes_turn_down() -> None:
    up = _wavy(900, 1000, 0.5)
    last = float(up[-1])
    down = _wavy(600, last, -1.5)
    candles = make_candles(up + down)
    emitted, _ = _run(candles)
    exits = [(i, s) for i, s in emitted if s.kind is SignalKind.EXIT]
    assert exits
    assert exits[0][1].side is Side.SELL
    assert exits[0][0] >= 900  # not while the uptrend was healthy


def test_it_refuses_candles_that_are_not_hourly() -> None:
    strategy = MtfTrendPullbackStrategy.from_params({})
    candle = make_candles(["100"], timeframe=Timeframe.H4)[0]
    with pytest.raises(InvalidStrategyParams):
        strategy.evaluate(StrategyContext(SYMBOL, candle, Decimal(0)), strategy.initial_state())


def test_the_decision_never_depends_on_candles_after_it() -> None:
    candles = make_candles(_wavy(1500, 1000, 0.5))
    full, _ = _run(candles)
    cut = 1100
    partial, _ = _run(candles[:cut])
    assert [x for x in full if x[0] < cut] == partial
