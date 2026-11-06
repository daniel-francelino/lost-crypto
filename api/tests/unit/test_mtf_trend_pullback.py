"""Multi-timeframe trend pullback: 1d trend picks the side, 4h confirms, 1h times the entry."""

import math
import random
from decimal import Decimal
from typing import Any

import pytest

from factories import make_candles
from modules.exchanges.domain.models import PositionSide
from modules.market_data.domain.models import Candle, Timeframe
from modules.market_data.domain.trend import TrendFrame, TrendTracker, TrendTrackerState
from modules.strategies.domain.base import InvalidStrategyParams
from modules.strategies.domain.mtf_trend_pullback import MtfTrendPullbackStrategy
from modules.strategies.domain.types import Side, Signal, SignalKind, StrategyContext
from modules.trading.domain.models import MAX_WARMUP_CANDLES, warmup_candles

SYMBOL = "BTC/USDT"
WARM_CANDLES = 50 * 24  # the daily EMA 50 needs 50 completed days (the checks need 55)


def _market(count: int, start: float, drift: float, seed: int = 1) -> list[str]:
    """Hourly closes: a drift, a 12-day wave (pullbacks) and hourly noise."""
    rng = random.Random(seed)
    return [
        f"{start + drift * i + 60 * math.sin(2 * math.pi * i / (24 * 12)) + rng.gauss(0, 3):.2f}"
        for i in range(count)
    ]


def _run(
    candles: list[Candle], *, allow_short: bool = False, params: dict[str, Any] | None = None
) -> list[tuple[int, Signal]]:
    strategy = MtfTrendPullbackStrategy.from_params(params or {})
    state = strategy.initial_state()
    quantity, side = Decimal(0), None
    emitted: list[tuple[int, Signal]] = []
    for i, candle in enumerate(candles):
        result = strategy.evaluate(
            StrategyContext(SYMBOL, candle, quantity, side, allow_short), state
        )
        state = result.state
        for signal in result.signals:
            emitted.append((i, signal))
            if signal.kind is SignalKind.ENTRY:
                quantity = Decimal(1)
                side = PositionSide.LONG if signal.side is Side.BUY else PositionSide.SHORT
            else:
                quantity, side = Decimal(0), None
    return emitted


def test_it_declares_the_history_it_needs() -> None:
    strategy = MtfTrendPullbackStrategy.from_params({})
    assert strategy.required_history_candles() == (55 + 2) * 24
    assert warmup_candles(strategy.required_history_candles()) == 57 * 24
    assert warmup_candles(0) == 300
    assert warmup_candles(100_000) == MAX_WARMUP_CANDLES
    assert strategy.required_history_candles() <= MAX_WARMUP_CANDLES


@pytest.mark.parametrize(
    "params", [{"atr_multiple": 0}, {"daily_confirmation": 2}, {"daily_confirmation": 1.5}]
)
def test_params_are_validated(params: dict[str, Any]) -> None:
    with pytest.raises(InvalidStrategyParams):
        MtfTrendPullbackStrategy.from_params(params)


def test_nothing_is_signalled_before_the_daily_ema_is_warm() -> None:
    emitted = _run(make_candles(_market(24 * 330, 1000, 0.5)))
    assert emitted, "an uptrend with pullbacks must produce entries"
    assert emitted[0][0] >= WARM_CANDLES


def test_an_uptrend_is_only_bought_with_a_stop_below() -> None:
    candles = make_candles(_market(24 * 330, 1000, 0.5))
    entries = [(i, s) for i, s in _run(candles, allow_short=True) if s.kind is SignalKind.ENTRY]
    assert entries
    for i, signal in entries:
        assert signal.side is Side.BUY
        assert signal.stop_loss is not None and signal.stop_loss < candles[i].close


def test_a_downtrend_is_shorted_with_a_stop_above_only_when_shorts_are_allowed() -> None:
    candles = make_candles(_market(24 * 330, 6000, -0.5))
    assert _run(candles, allow_short=False) == []
    entries = [(i, s) for i, s in _run(candles, allow_short=True) if s.kind is SignalKind.ENTRY]
    assert entries
    for i, signal in entries:
        assert signal.side is Side.SELL
        assert signal.stop_loss is not None and signal.stop_loss > candles[i].close


def test_a_market_that_goes_nowhere_is_not_traded() -> None:
    assert _run(make_candles(["1000"] * 24 * 150), allow_short=True) == []


def test_a_long_exits_when_the_daily_trend_ends() -> None:
    up = _market(24 * 150, 1000, 0.5)
    down = _market(24 * 80, float(up[-1]), -2.0, seed=2)
    candles = make_candles(up + down)
    emitted = _run(candles)
    exits = [(i, s) for i, s in emitted if s.kind is SignalKind.EXIT]
    assert exits
    assert exits[0][1].side is Side.SELL
    assert exits[0][0] >= 24 * 100  # not while the uptrend was healthy


def test_daily_confirmation_only_enters_on_a_confirmed_daily_trend() -> None:
    candles = make_candles(_market(24 * 330, 1000, 0.5))
    emitted = _run(candles, params={"daily_confirmation": 1})
    tracker = TrendTracker(Timeframe.H1)
    state: TrendTrackerState = tracker.initial_state()
    entry_indexes = {i for i, s in emitted if s.kind is SignalKind.ENTRY}
    for i, candle in enumerate(candles):
        state = tracker.update(state, candle)
        if i in entry_indexes:
            assert tracker.read(state, TrendFrame.D1).confirmed


def test_it_refuses_candles_that_are_not_hourly() -> None:
    strategy = MtfTrendPullbackStrategy.from_params({})
    candle = make_candles(["100"], timeframe=Timeframe.H4)[0]
    with pytest.raises(InvalidStrategyParams):
        strategy.evaluate(StrategyContext(SYMBOL, candle, Decimal(0)), strategy.initial_state())


def test_the_decision_never_depends_on_candles_after_it() -> None:
    candles = make_candles(_market(24 * 330, 1000, 0.5))
    full = _run(candles)
    cut = 24 * 250
    assert [x for x in full if x[0] < cut] == _run(candles[:cut])
