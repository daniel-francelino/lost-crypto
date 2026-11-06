"""Multi-timeframe trend pullback: 1d trend picks the side, 4h confirms, 1h times the entry.

The bot runs on **1h** candles. The strategy builds the 4h and 1d bars itself from the 1h closes
(UTC buckets, like Binance), and only ever looks at *completed* higher-timeframe bars, so nothing
from the future leaks into a decision.

1. **Main trend (1d).** LONG when the last completed daily close is above its EMA and that EMA is
   rising; SHORT for the mirror image; otherwise there is no trend and the bot stays flat.
2. **Alignment (4h).** The last completed 4h close must be on the same side of its own EMA, with
   the EMA moving the same way. If the 4h disagrees, the move is not aligned and nothing is done.
3. **Entry (1h).** A pullback and its end: in an uptrend the previous 1h close was at or below the
   1h EMA and this one closes back above it (mirror for a short). Short entries need
   ``allow_short``.

Exit: the 4h or the 1d close ends up on the wrong side of its EMA (the looser condition than the
entry's, so the position is not shaken out by a flat EMA), or the protective stop is hit. The
stop sits ``atr_multiple`` average true ranges (1h) from the close. There is no profit target:
a trend follower is paid by the right tail.

Four free parameters, none meant to be swept: the EMA lengths are the usual ones and the slope
window is a constant. Needs about ``daily_ema_period + 4`` days of 1h candles before it signals.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Self

from modules.market_data.domain.models import Timeframe
from modules.strategies.domain.base import (
    InvalidStrategyParams,
    ParamSpec,
    Strategy,
    StrategyStyle,
    parse_numeric_params,
)
from modules.strategies.domain.trend_quality_breakout import true_range
from modules.strategies.domain.types import (
    Side,
    Signal,
    SignalKind,
    StrategyContext,
    StrategyResult,
)

ATR_PERIOD = 14
SLOPE_BARS = 3  # an EMA is "rising" when it is above its value this many bars ago
MAX_DAILY_EMA_PERIOD = 30
MAX_HISTORY_CANDLES = 1000  # one exchange page of 1h candles
_HOURS_4H = 4
_HOURS_1D = 24


@dataclass(frozen=True, slots=True)
class MtfTrendParams:
    daily_ema_period: int = 20
    h4_ema_period: int = 20
    entry_ema_period: int = 20
    atr_multiple: Decimal = Decimal(3)

    def __post_init__(self) -> None:
        if not (2 <= self.daily_ema_period <= MAX_DAILY_EMA_PERIOD):
            raise InvalidStrategyParams(
                f"daily_ema_period must be between 2 and {MAX_DAILY_EMA_PERIOD}"
            )
        if self.h4_ema_period < 2 or self.entry_ema_period < 2:
            raise InvalidStrategyParams("h4_ema_period and entry_ema_period must be >= 2")
        if self.atr_multiple <= 0:
            raise InvalidStrategyParams("atr_multiple must be > 0")


@dataclass(frozen=True, slots=True)
class _Ema:
    """EMA of a series of closes plus the last few values, to read its slope."""

    value: Decimal | None = None
    count: int = 0
    recent: tuple[Decimal, ...] = ()  # last SLOPE_BARS + 1 values, current included
    close: Decimal | None = None  # the close that produced ``value``

    def update(self, close: Decimal, period: int) -> "_Ema":
        if self.value is None:
            value = close
        elif self.count < period:
            # Seed with the plain average of the first ``period`` closes, then smooth.
            value = (self.value * self.count + close) / (self.count + 1)
        else:
            alpha = Decimal(2) / (period + 1)
            value = self.value + alpha * (close - self.value)
        return _Ema(value, self.count + 1, (*self.recent, value)[-(SLOPE_BARS + 1) :], close)

    def ready(self, period: int) -> bool:
        return self.count >= period + SLOPE_BARS and len(self.recent) == SLOPE_BARS + 1

    def side(self, period: int) -> int:
        """+1 close above the EMA, -1 below, 0 on the line or not warmed up."""
        if not self.ready(period) or self.value is None or self.close is None:
            return 0
        return (self.close > self.value) - (self.close < self.value)

    def trend(self, period: int) -> int:
        """Strict: close on one side of the EMA *and* the EMA moving that way."""
        side = self.side(period)
        if side == 0:
            return 0
        assert self.value is not None
        slope = self.value - self.recent[0]
        return side if (slope > 0) == (side > 0) and slope != 0 else 0


@dataclass(frozen=True, slots=True)
class _Bucket:
    """A higher-timeframe bar being assembled from 1h candles."""

    index: int | None = None  # hours since the epoch // bar length
    seen: int = 0  # 1h candles collected so far


@dataclass(frozen=True, slots=True)
class MtfTrendState:
    h1: _Ema = _Ema()
    h4: _Ema = _Ema()
    daily: _Ema = _Ema()
    h4_bucket: _Bucket = _Bucket()
    daily_bucket: _Bucket = _Bucket()
    previous_close: Decimal | None = None
    previous_h1_ema: Decimal | None = None
    ranges: tuple[Decimal, ...] = ()


def _ema_dump(ema: _Ema) -> dict[str, Any]:
    return {
        "value": None if ema.value is None else str(ema.value),
        "count": ema.count,
        "recent": [str(v) for v in ema.recent],
        "close": None if ema.close is None else str(ema.close),
    }


def _ema_load(raw: Mapping[str, Any]) -> _Ema:
    return _Ema(
        None if raw["value"] is None else Decimal(raw["value"]),
        int(raw["count"]),
        tuple(Decimal(v) for v in raw["recent"]),
        None if raw["close"] is None else Decimal(raw["close"]),
    )


def _advance(
    bucket: _Bucket, ema: _Ema, hours: int, hour_index: int, close: Decimal, period: int
) -> tuple[_Bucket, _Ema]:
    """Add one 1h candle to a higher-timeframe bar; close the bar on its last hour.

    A bar that did not start with its first hour (the history began mid-bar) or lost a candle
    is dropped, never half-counted."""
    index = hour_index // hours
    seen = bucket.seen + 1 if bucket.index == index else 1
    if bucket.index != index and hour_index % hours != 0:
        seen = 0  # joined mid-bar: this bar can never be complete
    bucket = _Bucket(index, seen)
    if (hour_index + 1) % hours == 0 and seen == hours:
        ema = ema.update(close, period)
    return bucket, ema


class MtfTrendPullbackStrategy(Strategy[MtfTrendState]):
    TYPE_KEY = "mtf_trend_pullback"
    STYLE = StrategyStyle.TREND
    NAME = "Multi-timeframe trend pullback (1d trend, 4h alignment, 1h entry)"
    DESCRIPTION = (
        "Run it on 1h candles. The daily trend picks LONG or SHORT, the 4h must agree, and the "
        "entry is the end of a 1h pullback in the trend's direction. Exits when the 4h or the "
        "daily trend turns, or at an ATR stop. Shorts need Futures with short enabled."
    )
    PARAMETERS = (
        ParamSpec(
            "daily_ema_period",
            "integer",
            20,
            f"EMA length on daily closes for the main trend (2-{MAX_DAILY_EMA_PERIOD})",
            2,
        ),
        ParamSpec("h4_ema_period", "integer", 20, "EMA length on 4h closes (alignment)", 2),
        ParamSpec("entry_ema_period", "integer", 20, "EMA length on 1h closes (pullback)", 2),
        ParamSpec(
            "atr_multiple",
            "number",
            3,
            f"Stop distance in 1h average true ranges of {ATR_PERIOD} candles (> 0)",
            Decimal("0.1"),
        ),
    )

    def __init__(self, params: MtfTrendParams) -> None:
        self.params = params

    @classmethod
    def from_params(cls, params: Mapping[str, Any]) -> Self:
        values = parse_numeric_params(
            params,
            integers=frozenset({"daily_ema_period", "h4_ema_period", "entry_ema_period"}),
            numbers=frozenset({"atr_multiple"}),
        )
        if "atr_multiple" in values and values["atr_multiple"] is None:
            raise InvalidStrategyParams("atr_multiple must be a number")
        strategy = cls(MtfTrendParams(**values))
        if strategy.required_history_candles() > MAX_HISTORY_CANDLES:
            raise InvalidStrategyParams(
                f"these EMA lengths need {strategy.required_history_candles()} 1h candles of "
                f"history; at most {MAX_HISTORY_CANDLES} fit in one exchange request"
            )
        return strategy

    def required_history_candles(self) -> int:
        """1h candles to feed before the first signal: the daily EMA is the slowest."""
        p = self.params
        days = p.daily_ema_period + SLOPE_BARS + 1  # +1: the first (partial) day is dropped
        h4_hours = (p.h4_ema_period + SLOPE_BARS + 1) * _HOURS_4H
        return max(days * _HOURS_1D, h4_hours, p.entry_ema_period) + _HOURS_1D

    def initial_state(self) -> MtfTrendState:
        return MtfTrendState()

    def serialize_state(self, state: MtfTrendState) -> dict[str, Any]:
        return {
            "h1": _ema_dump(state.h1),
            "h4": _ema_dump(state.h4),
            "daily": _ema_dump(state.daily),
            "h4_bucket": [state.h4_bucket.index, state.h4_bucket.seen],
            "daily_bucket": [state.daily_bucket.index, state.daily_bucket.seen],
            "previous_close": None if state.previous_close is None else str(state.previous_close),
            "previous_h1_ema": (
                None if state.previous_h1_ema is None else str(state.previous_h1_ema)
            ),
            "ranges": [str(r) for r in state.ranges],
        }

    def deserialize_state(self, raw: dict[str, Any]) -> MtfTrendState:
        return MtfTrendState(
            _ema_load(raw["h1"]),
            _ema_load(raw["h4"]),
            _ema_load(raw["daily"]),
            _Bucket(*raw["h4_bucket"]),
            _Bucket(*raw["daily_bucket"]),
            None if raw["previous_close"] is None else Decimal(raw["previous_close"]),
            None if raw["previous_h1_ema"] is None else Decimal(raw["previous_h1_ema"]),
            tuple(Decimal(r) for r in raw["ranges"]),
        )

    def evaluate(self, ctx: StrategyContext, state: MtfTrendState) -> StrategyResult[MtfTrendState]:
        candle = ctx.candle
        if candle.timeframe is not Timeframe.H1:
            raise InvalidStrategyParams(
                f"mtf_trend_pullback needs 1h candles, got {candle.timeframe.value}"
            )
        p = self.params
        hour_index = int(candle.open_time.timestamp()) // 3600
        h4_bucket, h4 = _advance(
            state.h4_bucket, state.h4, _HOURS_4H, hour_index, candle.close, p.h4_ema_period
        )
        daily_bucket, daily = _advance(
            state.daily_bucket,
            state.daily,
            _HOURS_1D,
            hour_index,
            candle.close,
            p.daily_ema_period,
        )
        h1 = state.h1.update(candle.close, p.entry_ema_period)
        previous_close = state.previous_close
        previous_h1_ema = state.previous_h1_ema
        ranges = (*state.ranges, true_range(candle.high, candle.low, previous_close))[-ATR_PERIOD:]
        new_state = MtfTrendState(
            h1,
            h4,
            daily,
            h4_bucket,
            daily_bucket,
            candle.close,
            h1.value,
            ranges,
        )

        signals: tuple[Signal, ...] = ()
        daily_trend = daily.trend(p.daily_ema_period)
        h4_trend = h4.trend(p.h4_ema_period)
        if ctx.is_flat:
            signals = self._entry(
                ctx, daily_trend, h4_trend, h1, previous_close, previous_h1_ema, ranges
            )
        else:
            signals = self._exit(ctx, daily.side(p.daily_ema_period), h4.side(p.h4_ema_period))
        return StrategyResult(signals, new_state)

    def _entry(
        self,
        ctx: StrategyContext,
        daily_trend: int,
        h4_trend: int,
        h1: _Ema,
        previous_close: Decimal | None,
        previous_h1_ema: Decimal | None,
        ranges: tuple[Decimal, ...],
    ) -> tuple[Signal, ...]:
        p = self.params
        if daily_trend == 0 or h4_trend != daily_trend:
            return ()
        if (
            h1.value is None
            or h1.count < p.entry_ema_period
            or previous_close is None
            or previous_h1_ema is None
            or len(ranges) < ATR_PERIOD
        ):
            return ()
        close = ctx.candle.close
        atr = sum(ranges, Decimal(0)) / len(ranges)
        if daily_trend > 0:
            resumed = previous_close <= previous_h1_ema and close > h1.value
            if not resumed:
                return ()
            stop = close - p.atr_multiple * atr
            return (
                Signal(
                    Side.BUY,
                    ctx.symbol,
                    SignalKind.ENTRY,
                    "1d and 4h trends up; 1h closed back above its EMA after a pullback",
                    stop_loss=stop if stop > 0 else None,
                ),
            )
        if not ctx.allow_short:
            return ()
        resumed = previous_close >= previous_h1_ema and close < h1.value
        if not resumed:
            return ()
        return (
            Signal(
                Side.SELL,
                ctx.symbol,
                SignalKind.ENTRY,
                "1d and 4h trends down; 1h closed back below its EMA after a bounce",
                stop_loss=close + p.atr_multiple * atr,
            ),
        )

    def _exit(self, ctx: StrategyContext, daily_side: int, h4_side: int) -> tuple[Signal, ...]:
        """Leave when the 4h or the daily close sits on the wrong side of its EMA."""
        wrong = -1 if ctx.is_long else 1
        if daily_side == wrong or h4_side == wrong:
            which = "daily" if daily_side == wrong else "4h"
            return (
                Signal(
                    Side.SELL if ctx.is_long else Side.BUY,
                    ctx.symbol,
                    SignalKind.EXIT,
                    f"the {which} close is on the wrong side of its EMA: the trend turned",
                ),
            )
        return ()
