"""Book 4 ch. 1/8/20 + book 3 ch. 8: breakout, noise filter and ATR stop, no profit target."""

from decimal import Decimal
from typing import Any

import pytest

from factories import make_candles
from modules.exchanges.domain.models import PositionSide
from modules.strategies.domain.base import InvalidStrategyParams, StrategyStyle
from modules.strategies.domain.trend_quality_breakout import (
    ATR_PERIOD,
    TrendQualityBreakoutStrategy,
    efficiency_ratio,
    true_range,
)
from modules.strategies.domain.types import Side, Signal, SignalKind, StrategyContext

D = Decimal
SYMBOL = "BTC/USDT"


def _strategy(**params: Any) -> TrendQualityBreakoutStrategy:
    return TrendQualityBreakoutStrategy.from_params(params)


def _signals(strategy: TrendQualityBreakoutStrategy, closes: list[int]) -> list[tuple[int, Signal]]:
    state = strategy.initial_state()
    position = D(0)
    out: list[tuple[int, Signal]] = []
    for i, candle in enumerate(make_candles(closes)):
        result = strategy.evaluate(StrategyContext(SYMBOL, candle, position), state)
        state = result.state
        for signal in result.signals:
            out.append((i, signal))
            position = D(1) if signal.side is Side.BUY else D(0)
    return out


def _flat_then_rise(rise: list[int]) -> list[int]:
    return [100 + (i % 2) for i in range(10)] + rise


def test_it_is_a_trend_strategy_with_five_free_parameters():
    cls = TrendQualityBreakoutStrategy
    assert cls.STYLE is StrategyStyle.TREND
    assert [p.name for p in cls.PARAMETERS] == [
        "entry_period",
        "exit_period",
        "atr_multiple",
        "er_min",
        "trail_atr_multiple",
    ]


def test_true_range_uses_the_gap_from_the_previous_close():
    assert true_range(D(105), D(100), None) == 5
    assert true_range(D(105), D(103), D(100)) == 5  # gap up: high - previous close
    assert true_range(D(97), D(95), D(100)) == 5  # gap down: previous close - low
    assert true_range(D(105), D(95), D(100)) == 10  # the range itself


def test_efficiency_ratio_is_one_on_a_line_and_low_on_noise():
    assert efficiency_ratio(tuple(D(x) for x in (1, 2, 3, 4, 5))) == 1
    noisy = efficiency_ratio(tuple(D(x) for x in (1, 5, 1, 5, 2)))
    assert noisy is not None and abs(noisy - D(1) / 15) < D("1e-20")
    assert efficiency_ratio(tuple(D(x) for x in (5, 5, 5))) == 0
    assert efficiency_ratio((D(5),)) is None


def test_a_breakout_buys_with_an_atr_stop_and_no_target():
    strategy = _strategy(entry_period=10, exit_period=5, atr_multiple=2)
    [(index, signal)] = [
        s for s in _signals(strategy, _flat_then_rise([110, 120])) if s[1].kind is SignalKind.ENTRY
    ]
    assert index == 10 and signal.side is Side.BUY and signal.take_profit is None
    assert signal.stop_loss is not None and signal.stop_loss < D(110)


def test_the_stop_distance_scales_with_the_multiple():
    series = _flat_then_rise([110])
    narrow = _signals(_strategy(entry_period=10, exit_period=5, atr_multiple=1), series)[0][1]
    wide = _signals(_strategy(entry_period=10, exit_period=5, atr_multiple=4), series)[0][1]
    assert narrow.stop_loss is not None and wide.stop_loss is not None
    assert wide.stop_loss < narrow.stop_loss < D(110)


def test_a_breakout_out_of_noise_is_skipped_when_the_filter_is_on():
    noisy = [100, 120, 100, 120, 100, 120, 100, 120, 100, 119, 121]  # breaks 120 after a zig-zag
    assert [s for s in _signals(_strategy(entry_period=10, exit_period=5), noisy)] != []
    assert _signals(_strategy(entry_period=10, exit_period=5, er_min="0.5"), noisy) == []


def test_a_clean_trend_passes_the_filter():
    rise = [101 + 2 * i for i in range(12)]
    clean = _signals(_strategy(entry_period=10, exit_period=5, er_min="0.5"), rise)
    assert clean and clean[0][1].side is Side.BUY


def test_it_leaves_on_the_exit_channel_low():
    strategy = _strategy(entry_period=10, exit_period=5)
    series = [*_flat_then_rise([110, 120, 130, 140]), 99]
    kinds = [signal.kind for _, signal in _signals(strategy, series)]
    assert kinds == [SignalKind.ENTRY, SignalKind.EXIT]


def test_short_breakout_has_mirrored_stop_and_exit_does_not_reverse():
    strategy = _strategy(entry_period=10, exit_period=5)
    candles = make_candles([100, 101] * 5 + [90, 80, 103], symbol=SYMBOL)
    state = strategy.initial_state()
    position_side = None
    signals: list[tuple[int, Signal]] = []

    for index, candle in enumerate(candles):
        result = strategy.evaluate(
            StrategyContext(
                SYMBOL,
                candle,
                D(1) if position_side is PositionSide.SHORT else D(0),
                position_side=position_side,
                allow_short=True,
            ),
            state,
        )
        state = result.state
        if result.signals:
            signal = result.signals[0]
            signals.append((index, signal))
            position_side = (
                PositionSide.SHORT if signal.kind is SignalKind.ENTRY else None
            )

    assert [signal.kind for _, signal in signals] == [SignalKind.ENTRY, SignalKind.EXIT]
    entry_index, entry = signals[0]
    assert entry_index == 10 and entry.side is Side.SELL
    assert entry.stop_loss is not None and entry.stop_loss > candles[entry_index].close
    exit_index, exit_signal = signals[1]
    assert exit_index == 12 and exit_signal.side is Side.BUY


def test_no_signals_while_warming_up():
    assert _signals(_strategy(entry_period=10, exit_period=5), list(range(100, 110))) == []


def test_atr_window_is_a_constant_not_a_parameter():
    assert ATR_PERIOD == 20
    with pytest.raises(InvalidStrategyParams, match="unknown"):
        _strategy(atr_period=14)


@pytest.mark.parametrize(
    "params",
    [
        {"entry_period": 1},
        {"entry_period": 10, "exit_period": 11},
        {"atr_multiple": 0},
        {"er_min": 1},
        {"er_min": -0.1},
        {"er_min": None},
    ],
)
def test_invalid_parameters_are_refused(params: dict[str, Any]):
    with pytest.raises(InvalidStrategyParams):
        _strategy(**params)


def _rise_then_stall() -> list[int]:
    return [*_flat_then_rise([110 + 4 * i for i in range(8)]), 138, 136, 134, 132, 130]


def test_the_trailing_exit_is_off_by_default_and_sells_earlier_than_the_channel_when_on():
    plain = _signals(_strategy(entry_period=10, exit_period=10), _rise_then_stall())
    trailing = _signals(
        _strategy(entry_period=10, exit_period=10, trail_atr_multiple="1"), _rise_then_stall()
    )
    assert [s.kind for _, s in plain] == [SignalKind.ENTRY]  # the channel never breaks
    assert [s.kind for _, s in trailing] == [SignalKind.ENTRY, SignalKind.EXIT]
    assert "trailing" in trailing[1][1].reason


def test_a_wider_trailing_multiple_sells_later_or_never():
    series = _rise_then_stall()
    tight = _signals(_strategy(entry_period=10, exit_period=10, trail_atr_multiple="1"), series)
    wide = _signals(_strategy(entry_period=10, exit_period=10, trail_atr_multiple="20"), series)
    assert len(tight) == 2 and len(wide) == 1


def test_the_trailing_peak_survives_a_restart():
    strategy = _strategy(entry_period=10, exit_period=10, trail_atr_multiple="1")
    state = strategy.initial_state()
    position = D(0)
    for candle in make_candles(_flat_then_rise([110, 120, 130])):
        result = strategy.evaluate(StrategyContext(SYMBOL, candle, position), state)
        state = result.state
        if result.signals:
            position = D(1)
    reborn = strategy.deserialize_state(strategy.serialize_state(state))
    assert reborn == state and state.peak_close == D(130)


def test_trail_multiple_must_be_positive():
    with pytest.raises(InvalidStrategyParams):
        _strategy(trail_atr_multiple=0)
