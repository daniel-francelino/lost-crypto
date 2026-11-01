import json
from decimal import Decimal
from typing import Any

import pytest

from factories import make_candles
from modules.strategies.domain.base import InvalidStrategyParams, StrategyStyle
from modules.strategies.domain.mean_reversion_zscore import (
    MeanReversionParams,
    MeanReversionZScoreStrategy,
    z_score,
)
from modules.strategies.domain.types import Side, StrategyContext

D = Decimal


def _strategy(**kw: Any) -> MeanReversionZScoreStrategy:
    return MeanReversionZScoreStrategy(MeanReversionParams(**kw))


def _run(strategy: MeanReversionZScoreStrategy, closes: list[int | str]):
    state = strategy.initial_state()
    position = D(0)
    out: list[tuple[int, Side, str]] = []
    for i, candle in enumerate(make_candles(closes)):
        result = strategy.evaluate(StrategyContext(candle.symbol, candle, position), state)
        state = result.state
        for signal in result.signals:
            out.append((i, signal.side, signal.reason))
            position = D(1) if signal.side is Side.BUY else D(0)
    return out, state


def test_z_score_matches_a_hand_calculation():
    window = [
        D(10),
        D(12),
        D(11),
        D(13),
        D(4),
    ]  # mean 10, squared deviations 0+4+1+9+36 = 50, variance 10
    z = z_score(window)
    assert z is not None and abs(z - D(-6) / D(10).sqrt()) < D("1e-20")


def test_a_window_without_spread_gives_no_z_score_and_no_signal():
    assert z_score([D(5)] * 6) is None
    out, _ = _run(_strategy(lookback=5), [100] * 30)
    assert out == []


def test_no_signal_until_the_window_is_full():
    out, state = _run(_strategy(lookback=5, entry_z=D("0.5")), [100, 100, 100, 90])
    assert out == [] and len(state.closes) == 4


def test_enters_exactly_at_the_entry_threshold_and_not_just_above_it():
    # window 100,100,100,100,x: mean/deviation make z = -2 at x = 100 - 2 * sd(x)
    closes_hit: list[int | str] = [100, 100, 100, 100, 50]
    z = z_score([D(c) for c in closes_hit])
    assert z is not None
    at = _strategy(lookback=5, entry_z=-z)  # threshold exactly at this z
    above = _strategy(lookback=5, entry_z=-z + D("0.0001"))
    assert [s for _, s, _ in _run(at, closes_hit)[0]] == [Side.BUY]
    assert _run(above, closes_hit)[0] == []


def test_exits_when_the_z_score_is_back_to_the_exit_level():
    closes: list[int | str] = [100, 100, 100, 100, 50, 60, 80, 100, 110]
    out, _ = _run(_strategy(lookback=5), closes)
    sides = [(i, s) for i, s, _ in out]
    assert sides[0] == (4, Side.BUY) and sides[1][1] is Side.SELL
    assert "back to" in out[1][2]


def test_a_stricter_exit_level_holds_the_position_longer():
    closes: list[int | str] = [100, 100, 100, 100, 50, 60, 70, 80, 90, 100, 110, 120]
    mean_exit, _ = _run(_strategy(lookback=5, exit_z=D(0)), closes)
    late_exit, _ = _run(_strategy(lookback=5, exit_z=D("1.5")), closes)
    sell_at = lambda out: next((i for i, s, _ in out if s is Side.SELL), 10**6)  # noqa: E731
    assert sell_at(late_exit) >= sell_at(mean_exit)


def test_holding_limit_closes_a_position_that_never_reverts():
    closes: list[int | str] = [100, 100, 100, 100, 50, 49, 48, 47, 46, 45, 44]
    out, _ = _run(_strategy(lookback=5, max_holding_candles=3), closes)
    buy = next(i for i, s, _ in out if s is Side.BUY)
    sell = next((i, r) for i, s, r in out if s is Side.SELL)
    assert sell[0] == buy + 3 and "holding limit of 3" in sell[1]


def test_stop_level_is_a_percentage_below_the_entry_close():
    strategy = _strategy(lookback=5, stop_loss_pct=D(10))
    state = strategy.initial_state()
    entry = None
    for candle in make_candles([100, 100, 100, 100, 50]):
        result = strategy.evaluate(StrategyContext(candle.symbol, candle, D(0)), state)
        state = result.state
        if result.signals:
            entry = result.signals[0]
    assert entry is not None and entry.stop_loss == D(45) and entry.take_profit is None


def test_state_round_trips_through_json_and_old_state_without_bars_held_loads():
    strategy = _strategy(lookback=5)
    _, state = _run(strategy, [100, 101, 99, 100, 98, 97])
    restored = strategy.deserialize_state(json.loads(json.dumps(strategy.serialize_state(state))))
    assert restored == state and len(state.closes) == 5
    assert strategy.deserialize_state({"closes": ["1", "2"]}).bars_held == 0


@pytest.mark.parametrize(
    "raw",
    [
        {"lookback": 4},
        {"lookback": "20"},
        {"entry_z": 0},
        {"entry_z": -1},
        {"entry_z": None},
        {"exit_z": None},
        {"entry_z": 1, "exit_z": -1},
        {"entry_z": 1, "exit_z": -2},
        {"max_holding_candles": 0},
        {"stop_loss_pct": 0},
        {"stop_loss_pct": 100},
        {"lookback": True},
        {"unknown": 1},
    ],
)
def test_invalid_parameters_are_refused(raw: dict[str, Any]) -> None:
    with pytest.raises(InvalidStrategyParams):
        MeanReversionZScoreStrategy.from_params(raw)


def test_defaults_are_ours_and_the_style_is_mean_reversion():
    strategy = MeanReversionZScoreStrategy.from_params({})
    assert (strategy.params.lookback, strategy.params.entry_z, strategy.params.exit_z) == (
        20,
        D(2),
        D(0),
    )
    assert MeanReversionZScoreStrategy.STYLE is StrategyStyle.MEAN_REVERSION
    assert len(MeanReversionZScoreStrategy.PARAMETERS) == 5  # the limit before "too many"
