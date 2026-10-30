"""Trend following: EMA crossover (long-only spot).

Buy when the fast EMA crosses above the slow EMA; sell when it crosses back below.
EMAs are seeded with the SMA of their first ``period`` closes, then updated incrementally.
No signal is emitted on the warm-up candles, nor on the candle where warm-up completes (a
cross needs a previous reading to compare against).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from core.errors import DomainError
from modules.strategies.domain.types import (
    Side,
    Signal,
    SignalKind,
    StrategyContext,
    StrategyResult,
)

TYPE_KEY = "ema_crossover"


class InvalidStrategyParams(DomainError):
    pass


@dataclass(frozen=True, slots=True)
class EmaCrossoverParams:
    fast_period: int = 9
    slow_period: int = 21

    def __post_init__(self) -> None:
        if self.fast_period < 2:
            raise InvalidStrategyParams("fast_period must be >= 2")
        if self.fast_period >= self.slow_period:
            raise InvalidStrategyParams("fast_period must be smaller than slow_period")

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "EmaCrossoverParams":
        unknown = set(raw) - {"fast_period", "slow_period"}
        if unknown:
            raise InvalidStrategyParams(f"unknown parameters: {sorted(unknown)}")
        values: dict[str, int] = {}
        for key, value in raw.items():
            if isinstance(value, bool) or not isinstance(value, int):
                raise InvalidStrategyParams(f"{key} must be an integer")
            values[key] = value
        return cls(**values)


@dataclass(frozen=True, slots=True)
class EmaCrossoverState:
    closes: tuple[Decimal, ...] = ()  # warm-up buffer; unused once EMAs exist
    fast: Decimal | None = None
    slow: Decimal | None = None


def _sma(values: Sequence[Decimal]) -> Decimal:
    return sum(values, Decimal(0)) / len(values)


def _ema_series_end(closes: Sequence[Decimal], period: int) -> Decimal:
    alpha = Decimal(2) / (period + 1)
    ema = _sma(closes[:period])
    for close in closes[period:]:
        ema = alpha * close + (1 - alpha) * ema
    return ema


class EmaCrossoverStrategy:
    def __init__(self, params: EmaCrossoverParams) -> None:
        self.params = params
        self._alpha_fast = Decimal(2) / (params.fast_period + 1)
        self._alpha_slow = Decimal(2) / (params.slow_period + 1)

    def initial_state(self) -> EmaCrossoverState:
        return EmaCrossoverState()

    def evaluate(
        self, ctx: StrategyContext, state: EmaCrossoverState
    ) -> StrategyResult[EmaCrossoverState]:
        close = ctx.candle.close

        if state.fast is None or state.slow is None:
            closes = (*state.closes, close)
            if len(closes) < self.params.slow_period:
                return StrategyResult((), EmaCrossoverState(closes=closes))
            fast = _ema_series_end(closes, self.params.fast_period)
            slow = _ema_series_end(closes, self.params.slow_period)
            return StrategyResult((), EmaCrossoverState(fast=fast, slow=slow))

        previous_diff = state.fast - state.slow
        fast = self._alpha_fast * close + (1 - self._alpha_fast) * state.fast
        slow = self._alpha_slow * close + (1 - self._alpha_slow) * state.slow
        diff = fast - slow

        signals: tuple[Signal, ...] = ()
        if previous_diff <= 0 < diff and ctx.position_quantity <= 0:
            signals = (
                Signal(
                    Side.BUY,
                    ctx.symbol,
                    SignalKind.ENTRY,
                    f"EMA{self.params.fast_period} crossed above EMA{self.params.slow_period}",
                ),
            )
        elif previous_diff >= 0 > diff and ctx.position_quantity > 0:
            signals = (
                Signal(
                    Side.SELL,
                    ctx.symbol,
                    SignalKind.EXIT,
                    f"EMA{self.params.fast_period} crossed below EMA{self.params.slow_period}",
                ),
            )
        return StrategyResult(signals, EmaCrossoverState(fast=fast, slow=slow))
