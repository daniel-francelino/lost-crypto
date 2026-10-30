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
    stop_loss_pct: Decimal | None = None  # % below the entry candle's close
    take_profit_pct: Decimal | None = None  # % above the entry candle's close

    def __post_init__(self) -> None:
        for name in ("stop_loss_pct", "take_profit_pct"):
            value = getattr(self, name)
            if value is not None and not (0 < value < 100):
                raise InvalidStrategyParams(f"{name} must be between 0 and 100 (exclusive)")
        if self.fast_period < 2:
            raise InvalidStrategyParams("fast_period must be >= 2")
        if self.fast_period >= self.slow_period:
            raise InvalidStrategyParams("fast_period must be smaller than slow_period")

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "EmaCrossoverParams":
        unknown = set(raw) - {"fast_period", "slow_period", "stop_loss_pct", "take_profit_pct"}
        if unknown:
            raise InvalidStrategyParams(f"unknown parameters: {sorted(unknown)}")
        values: dict[str, Any] = {}
        for key, value in raw.items():
            if isinstance(value, bool):
                raise InvalidStrategyParams(f"{key} must be a number")
            if key.endswith("_period"):
                if not isinstance(value, int):
                    raise InvalidStrategyParams(f"{key} must be an integer")
                values[key] = value
            elif value is None:
                values[key] = None
            else:
                try:
                    values[key] = Decimal(str(value))
                except ArithmeticError:
                    raise InvalidStrategyParams(f"{key} must be a number") from None
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

    @staticmethod
    def _level(close: Decimal, pct: Decimal | None, direction: int) -> Decimal | None:
        return None if pct is None else close * (1 + direction * pct / 100)

    def serialize_state(self, state: EmaCrossoverState) -> dict[str, Any]:
        return {
            "closes": [str(c) for c in state.closes],
            "fast": None if state.fast is None else str(state.fast),
            "slow": None if state.slow is None else str(state.slow),
        }

    def deserialize_state(self, raw: dict[str, Any]) -> EmaCrossoverState:
        return EmaCrossoverState(
            closes=tuple(Decimal(c) for c in raw["closes"]),
            fast=None if raw["fast"] is None else Decimal(raw["fast"]),
            slow=None if raw["slow"] is None else Decimal(raw["slow"]),
        )

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
                    stop_loss=self._level(close, self.params.stop_loss_pct, -1),
                    take_profit=self._level(close, self.params.take_profit_pct, +1),
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
