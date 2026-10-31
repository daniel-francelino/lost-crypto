from decimal import Decimal

import pytest

from factories import make_candles
from modules.strategies.catalog import build_strategy_registry
from modules.strategies.domain.base import InvalidStrategyParams
from modules.strategies.domain.ema_crossover import (
    EmaCrossoverParams,
    EmaCrossoverStrategy,
)
from modules.strategies.domain.registry import UnknownStrategy
from modules.strategies.domain.types import Side, StrategyContext


def _signals(closes: list[int], fast: int = 2, slow: int = 3) -> list[tuple[int, Side]]:
    """Feed candles one by one, holding a position after BUY and flat after SELL."""
    strategy = EmaCrossoverStrategy(EmaCrossoverParams(fast, slow))
    state = strategy.initial_state()
    position = Decimal(0)
    emitted: list[tuple[int, Side]] = []
    for i, candle in enumerate(make_candles(closes)):
        result = strategy.evaluate(StrategyContext(candle.symbol, candle, position), state)
        state = result.state
        for signal in result.signals:
            emitted.append((i, signal.side))
            position = Decimal(1) if signal.side is Side.BUY else Decimal(0)
    return emitted


def test_no_signal_during_warm_up_nor_on_the_candle_that_completes_it() -> None:
    assert _signals([10, 20, 5]) == []  # 3 candles = slow_period: warm-up ends, nothing to cross


def test_buys_on_cross_up_and_sells_on_cross_down() -> None:
    #           warm-up      up-trend            down-trend
    closes = [10, 10, 10, 12, 14, 16, 18, 14, 8, 4]
    assert _signals(closes) == [(3, Side.BUY), (7, Side.SELL)]


def test_flat_market_never_signals() -> None:
    assert _signals([10] * 30) == []


def test_does_not_buy_again_while_in_position_nor_sell_when_flat() -> None:
    strategy = EmaCrossoverStrategy(EmaCrossoverParams(2, 3))
    state = strategy.initial_state()
    candles = make_candles([10, 10, 10, 12])
    for candle in candles[:3]:
        state = strategy.evaluate(StrategyContext("BTC/USDT", candle, Decimal(0)), state).state
    # Cross up happens on candle 4, but we already hold a position: no new entry.
    held = strategy.evaluate(StrategyContext("BTC/USDT", candles[3], Decimal(1)), state)
    assert held.signals == ()


def test_evaluate_is_deterministic_and_does_not_mutate_state() -> None:
    strategy = EmaCrossoverStrategy(EmaCrossoverParams(2, 3))
    state = strategy.initial_state()
    candle = make_candles([10])[0]
    ctx = StrategyContext("BTC/USDT", candle, Decimal(0))
    assert strategy.evaluate(ctx, state) == strategy.evaluate(ctx, state)
    assert state == strategy.initial_state()


@pytest.mark.parametrize(
    "raw",
    [
        {"fast_period": 21, "slow_period": 9},
        {"fast_period": 9, "slow_period": 9},
        {"fast_period": 1, "slow_period": 5},
        {"fast_period": "9"},
        {"fast_period": 9.5},
        {"fast_period": True},
        {"unknown": 1},
    ],
)
def test_invalid_params_are_rejected(raw: dict[str, object]) -> None:
    with pytest.raises(InvalidStrategyParams):
        EmaCrossoverStrategy.from_params(raw)


def test_registry_defaults_to_ema_9_21_and_rejects_unknown_types() -> None:
    registry = build_strategy_registry()
    strategy = registry.create("ema_crossover", {})
    assert strategy.params == EmaCrossoverParams(9, 21)
    with pytest.raises(UnknownStrategy):
        registry.create("nope", {})
