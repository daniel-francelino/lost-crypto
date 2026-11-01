"""Trend following: Donchian breakout filtered by noise, with a volatility stop (long-only spot).

Buy when the close breaks above the highest high of the previous ``entry_period`` candles *and*
the efficiency ratio of the last ``entry_period`` closes is at least ``er_min`` (a clean trend, not
noise). Sell when the close falls below the lowest low of the previous ``exit_period`` candles.
Every entry proposes a stop ``atr_multiple`` average true ranges below the close and **no profit
target**: a target or a tight stop cuts the long right tail that pays a trend follower.

The ATR window is fixed (``ATR_PERIOD``) and the efficiency window follows ``entry_period``, so
the strategy has five free parameters. ``er_min = 0`` turns the noise filter off.

``trail_atr_multiple`` (off by default) adds a trailing exit on the closes: sell when the close
falls ``trail_atr_multiple`` average true ranges below the highest close since entry. It is meant
to stop a long winner from giving its gain back before the exit channel notices (book 4 ch. 20),
and it only ever sells earlier than the channel does.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, localcontext
from itertools import pairwise
from typing import Any, Self

from modules.strategies.domain.base import (
    InvalidStrategyParams,
    ParamSpec,
    Strategy,
    StrategyStyle,
    next_bars_held,
    parse_numeric_params,
)
from modules.strategies.domain.types import (
    Side,
    Signal,
    SignalKind,
    StrategyContext,
    StrategyResult,
)

ATR_PERIOD = 20
_PRECISION = 40


def true_range(high: Decimal, low: Decimal, previous_close: Decimal | None) -> Decimal:
    """The widest of: the candle's range and its distance from the previous close."""
    if previous_close is None:
        return high - low
    return max(high - low, abs(high - previous_close), abs(low - previous_close))


def efficiency_ratio(closes: tuple[Decimal, ...]) -> Decimal | None:
    """|net change| / sum of |changes| over the window (1 = straight line, 0 = pure noise).

    None when fewer than two closes. A window with no movement at all counts as 0."""
    if len(closes) < 2:
        return None
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        path = sum((abs(b - a) for a, b in pairwise(closes)), Decimal(0))
        return abs(closes[-1] - closes[0]) / path if path > 0 else Decimal(0)


@dataclass(frozen=True, slots=True)
class TrendQualityParams:
    entry_period: int = 40
    exit_period: int = 20
    atr_multiple: Decimal = Decimal(3)
    er_min: Decimal = Decimal(0)
    trail_atr_multiple: Decimal | None = None

    def __post_init__(self) -> None:
        if self.entry_period < 2 or self.exit_period < 2:
            raise InvalidStrategyParams("entry_period and exit_period must be >= 2")
        if self.exit_period > self.entry_period:
            raise InvalidStrategyParams("exit_period must not exceed entry_period")
        if self.atr_multiple <= 0:
            raise InvalidStrategyParams("atr_multiple must be > 0")
        if not (0 <= self.er_min < 1):
            raise InvalidStrategyParams("er_min must be in [0, 1)")
        if self.trail_atr_multiple is not None and self.trail_atr_multiple <= 0:
            raise InvalidStrategyParams("trail_atr_multiple must be > 0")


@dataclass(frozen=True, slots=True)
class TrendQualityState:
    # (high, low) of the most recent candles, oldest first, current candle excluded.
    history: tuple[tuple[Decimal, Decimal], ...] = ()
    # Closes including the current one: entry_period + 1 of them are enough for the ER.
    closes: tuple[Decimal, ...] = ()
    # True ranges of the last ATR_PERIOD candles, current one included.
    ranges: tuple[Decimal, ...] = ()
    bars_held: int = 0
    # Highest close since the entry signal; None while flat.
    peak_close: Decimal | None = None


class TrendQualityBreakoutStrategy(Strategy[TrendQualityState]):
    TYPE_KEY = "trend_quality_breakout"
    STYLE = StrategyStyle.TREND
    NAME = "Trend quality breakout (trend following)"
    DESCRIPTION = (
        "Long-only. Buys a close above the highest high of the last entry_period candles when the "
        "efficiency ratio shows a clean trend, with a stop atr_multiple ATRs below and no profit "
        "target; sells a close below the lowest low of the last exit_period candles."
    )
    PARAMETERS = (
        ParamSpec("entry_period", "integer", 40, "Candles in the breakout-up channel", 2),
        ParamSpec("exit_period", "integer", 20, "Candles in the exit channel (<= entry_period)", 2),
        ParamSpec(
            "atr_multiple",
            "number",
            3,
            f"Stop distance in average true ranges of {ATR_PERIOD} candles (> 0)",
            Decimal("0.1"),
        ),
        ParamSpec(
            "er_min",
            "number",
            0,
            "Minimum efficiency ratio (0-1) of the last entry_period closes to enter; 0 = off",
            0,
        ),
        ParamSpec(
            "trail_atr_multiple",
            "number",
            None,
            "Optional trailing exit: sell when the close is this many ATRs below the highest "
            "close since entry",
            Decimal("0.1"),
        ),
    )

    def __init__(self, params: TrendQualityParams) -> None:
        self.params = params

    @classmethod
    def from_params(cls, params: Mapping[str, Any]) -> Self:
        values = parse_numeric_params(
            params,
            integers=frozenset({"entry_period", "exit_period"}),
            numbers=frozenset({"atr_multiple", "er_min", "trail_atr_multiple"}),
        )
        for name in ("atr_multiple", "er_min"):
            if name in values and values[name] is None:
                raise InvalidStrategyParams(f"{name} must be a number")
        return cls(TrendQualityParams(**values))

    def initial_state(self) -> TrendQualityState:
        return TrendQualityState()

    def serialize_state(self, state: TrendQualityState) -> dict[str, Any]:
        return {
            "history": [[str(high), str(low)] for high, low in state.history],
            "closes": [str(c) for c in state.closes],
            "ranges": [str(r) for r in state.ranges],
            "bars_held": state.bars_held,
            "peak_close": None if state.peak_close is None else str(state.peak_close),
        }

    def deserialize_state(self, raw: dict[str, Any]) -> TrendQualityState:
        return TrendQualityState(
            tuple((Decimal(h), Decimal(low)) for h, low in raw["history"]),
            tuple(Decimal(c) for c in raw["closes"]),
            tuple(Decimal(r) for r in raw["ranges"]),
            int(raw.get("bars_held", 0)),
            None if raw.get("peak_close") is None else Decimal(raw["peak_close"]),
        )

    def evaluate(
        self, ctx: StrategyContext, state: TrendQualityState
    ) -> StrategyResult[TrendQualityState]:
        candle = ctx.candle
        p = self.params
        previous_close = state.closes[-1] if state.closes else None
        ranges = (*state.ranges, true_range(candle.high, candle.low, previous_close))[-ATR_PERIOD:]
        closes = (*state.closes, candle.close)[-(p.entry_period + 1) :]
        bars_held = next_bars_held(ctx.position_quantity, state.bars_held)
        signals: tuple[Signal, ...] = ()
        peak = (
            max(state.peak_close if state.peak_close is not None else candle.close, candle.close)
            if ctx.position_quantity > 0
            else None
        )

        if len(state.history) >= p.entry_period:
            highest = max(high for high, _ in state.history[-p.entry_period :])
            lowest = min(low for _, low in state.history[-p.exit_period :])
            if candle.close > highest and ctx.position_quantity <= 0:
                signals = self._entry(ctx, closes, ranges, highest)
            elif candle.close < lowest and ctx.position_quantity > 0:
                signals = (
                    Signal(
                        Side.SELL,
                        ctx.symbol,
                        SignalKind.EXIT,
                        f"close broke below the {p.exit_period}-candle low ({lowest})",
                    ),
                )

        if not signals and peak is not None and p.trail_atr_multiple is not None:
            atr = sum(ranges, Decimal(0)) / len(ranges)
            level = peak - p.trail_atr_multiple * atr
            if len(state.history) >= p.entry_period and candle.close < level:
                signals = (
                    Signal(
                        Side.SELL,
                        ctx.symbol,
                        SignalKind.EXIT,
                        f"close fell below the trailing level ({level:.8f}) under the "
                        f"highest close ({peak})",
                    ),
                )
        if signals and signals[0].kind is SignalKind.ENTRY:
            peak = candle.close
        elif signals:
            peak = None

        keep = max(p.entry_period, p.exit_period)
        history = (*state.history, (candle.high, candle.low))[-keep:]
        return StrategyResult(signals, TrendQualityState(history, closes, ranges, bars_held, peak))

    def _entry(
        self,
        ctx: StrategyContext,
        closes: tuple[Decimal, ...],
        ranges: tuple[Decimal, ...],
        highest: Decimal,
    ) -> tuple[Signal, ...]:
        p = self.params
        ratio = efficiency_ratio(closes) if len(closes) > p.entry_period else None
        if p.er_min > 0 and (ratio is None or ratio < p.er_min):
            return ()
        close = ctx.candle.close
        atr = sum(ranges, Decimal(0)) / len(ranges)
        stop = close - p.atr_multiple * atr
        return (
            Signal(
                Side.BUY,
                ctx.symbol,
                SignalKind.ENTRY,
                f"close broke above the {p.entry_period}-candle high ({highest})",
                stop_loss=stop if stop > 0 else None,
            ),
        )
