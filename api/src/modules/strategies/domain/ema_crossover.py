"""Trend following: EMA crossover (long-only spot).

Buy when the fast EMA crosses above the slow EMA; sell when it crosses back below.
EMAs are seeded with the SMA of their first ``period`` closes, then updated incrementally.
No signal is emitted on the warm-up candles, nor on the candle where warm-up completes (a
cross needs a previous reading to compare against).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Self

from modules.strategies.domain.base import (
    InvalidStrategyParams,
    ParamSpec,
    Strategy,
    StrategyStyle,
    next_bars_held,
    parse_numeric_params,
    percent_below_above,
    validate_percent,
)
from modules.strategies.domain.types import (
    Side,
    Signal,
    SignalKind,
    StrategyContext,
    StrategyResult,
)


@dataclass(frozen=True, slots=True)
class EmaCrossoverParams:
    fast_period: int = 9
    slow_period: int = 21
    stop_loss_pct: Decimal | None = None  # % below the entry candle's close
    take_profit_pct: Decimal | None = None  # % above the entry candle's close
    max_holding_candles: int | None = None

    def __post_init__(self) -> None:
        validate_percent("stop_loss_pct", self.stop_loss_pct)
        validate_percent("take_profit_pct", self.take_profit_pct)
        if self.fast_period < 2:
            raise InvalidStrategyParams("fast_period must be >= 2")
        if self.fast_period >= self.slow_period:
            raise InvalidStrategyParams("fast_period must be smaller than slow_period")
        if self.max_holding_candles is not None and self.max_holding_candles < 1:
            raise InvalidStrategyParams("max_holding_candles must be >= 1")


@dataclass(frozen=True, slots=True)
class EmaCrossoverState:
    closes: tuple[Decimal, ...] = ()  # warm-up buffer; unused once EMAs exist
    fast: Decimal | None = None
    slow: Decimal | None = None
    bars_held: int = 0


def _sma(values: Sequence[Decimal]) -> Decimal:
    return sum(values, Decimal(0)) / len(values)


def _ema_series_end(closes: Sequence[Decimal], period: int) -> Decimal:
    alpha = Decimal(2) / (period + 1)
    ema = _sma(closes[:period])
    for close in closes[period:]:
        ema = alpha * close + (1 - alpha) * ema
    return ema


class EmaCrossoverStrategy(Strategy[EmaCrossoverState]):
    TYPE_KEY = "ema_crossover"
    STYLE = StrategyStyle.TREND
    NAME = "EMA Crossover (trend following)"
    DESCRIPTION = (
        "Long-only. Buys when the fast EMA crosses above the slow EMA and sells when it "
        "crosses back below."
    )
    PARAMETERS = (
        ParamSpec("fast_period", "integer", 9, "Fast EMA", 2),
        ParamSpec("slow_period", "integer", 21, "Slow EMA (must be greater than fast_period)", 3),
        ParamSpec(
            "stop_loss_pct", "number", None, "Optional stop-loss, % below the entry price (0-100)"
        ),
        ParamSpec("max_holding_candles", "integer", None, "Optional: exit after N held candles", 1),
        ParamSpec(
            "take_profit_pct",
            "number",
            None,
            "Optional take-profit, % above the entry price (0-100)",
        ),
    )

    def __init__(self, params: EmaCrossoverParams) -> None:
        self.params = params
        self._alpha_fast = Decimal(2) / (params.fast_period + 1)
        self._alpha_slow = Decimal(2) / (params.slow_period + 1)

    @classmethod
    def from_params(cls, params: Mapping[str, Any]) -> Self:
        values = parse_numeric_params(
            params,
            integers=frozenset({"fast_period", "slow_period"}),
            numbers=frozenset({"stop_loss_pct", "take_profit_pct"}),
            optional_integers=frozenset({"max_holding_candles"}),
        )
        return cls(EmaCrossoverParams(**values))

    def initial_state(self) -> EmaCrossoverState:
        return EmaCrossoverState()

    def serialize_state(self, state: EmaCrossoverState) -> dict[str, Any]:
        return {
            "closes": [str(c) for c in state.closes],
            "fast": None if state.fast is None else str(state.fast),
            "slow": None if state.slow is None else str(state.slow),
            "bars_held": state.bars_held,
        }

    def deserialize_state(self, raw: dict[str, Any]) -> EmaCrossoverState:
        return EmaCrossoverState(
            closes=tuple(Decimal(c) for c in raw["closes"]),
            fast=None if raw["fast"] is None else Decimal(raw["fast"]),
            slow=None if raw["slow"] is None else Decimal(raw["slow"]),
            bars_held=int(raw.get("bars_held", 0)),
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
        bars_held = next_bars_held(ctx.position_quantity, state.bars_held)
        if previous_diff <= 0 < diff and ctx.position_quantity <= 0:
            stop, target = percent_below_above(
                close, self.params.stop_loss_pct, self.params.take_profit_pct
            )
            signals = (
                Signal(
                    Side.BUY,
                    ctx.symbol,
                    SignalKind.ENTRY,
                    f"EMA{self.params.fast_period} crossed above EMA{self.params.slow_period}",
                    stop_loss=stop,
                    take_profit=target,
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
        if (
            not signals
            and ctx.position_quantity > 0
            and self.params.max_holding_candles is not None
            and bars_held >= self.params.max_holding_candles
        ):
            signals = (
                Signal(
                    Side.SELL,
                    ctx.symbol,
                    SignalKind.EXIT,
                    f"holding limit of {self.params.max_holding_candles} candles reached",
                ),
            )
        return StrategyResult(signals, EmaCrossoverState(fast=fast, slow=slow, bars_held=bars_held))
