"""``max_holding_candles``: the optional exit after N candles in a position (book 1 ch. 7)."""

from decimal import Decimal
from typing import Any

import pytest

from factories import make_candles
from modules.strategies.domain.base import InvalidStrategyParams, Strategy
from modules.strategies.domain.donchian_breakout import (
    DonchianBreakoutStrategy,
    DonchianParams,
)
from modules.strategies.domain.ema_crossover import EmaCrossoverParams, EmaCrossoverStrategy
from modules.strategies.domain.types import Side, StrategyContext

# warm-up, then a rise that keeps both strategies long with no signal of their own
RISING = [10, 10, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34]
FALLING = [*RISING, 5]


def _run(strategy: Strategy[Any], closes: list[int]) -> list[tuple[int, Side, str]]:
    state = strategy.initial_state()
    position = Decimal(0)
    out: list[tuple[int, Side, str]] = []
    for i, candle in enumerate(make_candles(closes)):
        result = strategy.evaluate(StrategyContext(candle.symbol, candle, position), state)
        state = result.state
        for signal in result.signals:
            out.append((i, signal.side, signal.reason))
            position = Decimal(1) if signal.side is Side.BUY else Decimal(0)
    return out


def _ema(max_hold: int | None) -> EmaCrossoverStrategy:
    return EmaCrossoverStrategy(EmaCrossoverParams(2, 3, max_holding_candles=max_hold))


def _donchian(max_hold: int | None) -> DonchianBreakoutStrategy:
    return DonchianBreakoutStrategy(DonchianParams(3, 2, max_holding_candles=max_hold))


@pytest.mark.parametrize("build", [_ema, _donchian])
def test_closes_the_position_exactly_after_n_held_candles(build: Any) -> None:
    signals = _run(build(3), RISING)
    entry = signals[0]
    assert entry[1] is Side.BUY
    exit_ = signals[1]
    assert exit_[1] is Side.SELL and exit_[0] == entry[0] + 3
    assert "holding limit of 3 candles" in exit_[2]


@pytest.mark.parametrize("build", [_ema, _donchian])
def test_without_the_parameter_the_position_is_kept(build: Any) -> None:
    signals = _run(build(None), RISING)
    assert [s[1] for s in signals] == [Side.BUY]


@pytest.mark.parametrize("build", [_ema, _donchian])
def test_it_enters_again_after_the_limit_when_the_strategy_asks(build: Any) -> None:
    sides = [s[1] for s in _run(build(2), RISING * 2)]
    assert sides[:2] == [Side.BUY, Side.SELL]
    assert sides.count(Side.BUY) >= 2


@pytest.mark.parametrize("build", [_ema, _donchian])
def test_a_strategy_exit_on_the_same_candle_wins_with_one_single_sell(build: Any) -> None:
    signals = _run(build(100), FALLING)
    sells = [s for s in signals if s[1] is Side.SELL]
    assert len(sells) == 1 and "holding limit" not in sells[0][2]
    limit_one = _run(build(1), FALLING)
    assert [s[1] for s in limit_one].count(Side.SELL) == len(
        [s for s in limit_one if s[1] is Side.BUY]
    )  # every entry is closed exactly once, never twice on the same candle


@pytest.mark.parametrize("build", [_ema, _donchian])
def test_the_count_survives_a_restart_through_the_serialized_state(build: Any) -> None:
    strategy = build(5)
    state = strategy.initial_state()
    position = Decimal(0)
    for candle in make_candles(RISING[:6]):
        result = strategy.evaluate(StrategyContext(candle.symbol, candle, position), state)
        state = result.state
        if result.signals:
            position = Decimal(1)
    restored = strategy.deserialize_state(strategy.serialize_state(state))
    assert restored == state
    assert strategy.serialize_state(state)["bars_held"] >= 1


def test_state_saved_before_the_parameter_existed_still_loads() -> None:
    ema = _ema(3).deserialize_state({"closes": [], "fast": "10", "slow": "9"})
    assert ema.bars_held == 0
    donchian = _donchian(3).deserialize_state({"history": [["11", "9"]]})
    assert donchian.bars_held == 0


@pytest.mark.parametrize("value", [0, -1])
def test_rejects_a_limit_below_one(value: int) -> None:
    with pytest.raises(InvalidStrategyParams):
        EmaCrossoverStrategy.from_params({"max_holding_candles": value})
    with pytest.raises(InvalidStrategyParams):
        DonchianBreakoutStrategy.from_params({"max_holding_candles": value})


def test_from_params_accepts_null_and_refuses_a_boolean() -> None:
    assert (
        EmaCrossoverStrategy.from_params({"max_holding_candles": None}).params.max_holding_candles
        is None
    )
    with pytest.raises(InvalidStrategyParams):
        EmaCrossoverStrategy.from_params({"max_holding_candles": True})
