"""Multi-timeframe trend pullback: 1d trend picks the side, 4h confirms, 1h times the entry.

The bot runs on **1h** candles. The trend of each timeframe comes from the shared utility
``market_data.domain.trend`` (BULLISH / BEARISH / SIDEWAYS, only from completed bars).

1. **Main trend (1d).** BULLISH means LONG, BEARISH means SHORT, SIDEWAYS means stay out.
2. **Alignment (4h).** The 4h trend must be the same as the daily one.
3. **Entry (1h).** A pullback and its end: in an uptrend the previous 1h close was at or below the
   1h EMA and this one closes back above it (mirror for a short). Short entries need
   ``allow_short``.

Exit: the 4h or the 1d close ends up on the wrong side of its EMA (a looser condition than the
entry's, so a flattening EMA alone does not shake the position out), or the protective stop is
hit. The stop sits ``atr_multiple`` average true ranges (1h) from the close. There is no profit
target: a trend follower is paid by the right tail.

Four free parameters, none meant to be swept: the EMA lengths are the usual ones.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Self

from modules.market_data.domain.models import Timeframe
from modules.market_data.domain.trend import (
    Trend,
    TrendFrame,
    TrendReading,
    TrendSettings,
    TrendTracker,
    TrendTrackerState,
)
from modules.strategies.domain.base import (
    InvalidStrategyParams,
    ParamSpec,
    Strategy,
    StrategyStyle,
    parse_numeric_params,
)
from modules.strategies.domain.types import (
    Side,
    Signal,
    SignalKind,
    StrategyContext,
    StrategyResult,
)

ATR_PERIOD = 14
MAX_DAILY_EMA_PERIOD = 30
MAX_HISTORY_CANDLES = 1000  # one exchange page of 1h candles


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


def _above_below(reading: TrendReading) -> int:
    """+1 close above the EMA, -1 below, 0 on the line or still warming up."""
    if reading.close is None or reading.ema is None or not reading.ready:
        return 0
    return (reading.close > reading.ema) - (reading.close < reading.ema)


class MtfTrendPullbackStrategy(Strategy[TrendTrackerState]):
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
        self._tracker = TrendTracker(
            Timeframe.H1,
            {
                TrendFrame.H1: TrendSettings(params.entry_ema_period, ATR_PERIOD),
                TrendFrame.H4: TrendSettings(params.h4_ema_period),
                TrendFrame.D1: TrendSettings(params.daily_ema_period),
            },
        )

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
        return self._tracker.required_base_candles()

    def initial_state(self) -> TrendTrackerState:
        return self._tracker.initial_state()

    def serialize_state(self, state: TrendTrackerState) -> dict[str, Any]:
        return self._tracker.serialize(state)

    def deserialize_state(self, raw: dict[str, Any]) -> TrendTrackerState:
        return self._tracker.deserialize(raw)

    def evaluate(
        self, ctx: StrategyContext, state: TrendTrackerState
    ) -> StrategyResult[TrendTrackerState]:
        if ctx.candle.timeframe is not Timeframe.H1:
            raise InvalidStrategyParams(
                f"mtf_trend_pullback needs 1h candles, got {ctx.candle.timeframe.value}"
            )
        new_state = self._tracker.update(state, ctx.candle)
        daily = self._tracker.read(new_state, TrendFrame.D1)
        h4 = self._tracker.read(new_state, TrendFrame.H4)
        if ctx.is_flat:
            h1 = self._tracker.read(new_state, TrendFrame.H1)
            signals = self._entry(ctx, daily, h4, h1)
        else:
            signals = self._exit(ctx, _above_below(daily), _above_below(h4))
        return StrategyResult(signals, new_state)

    def _entry(
        self, ctx: StrategyContext, daily: TrendReading, h4: TrendReading, h1: TrendReading
    ) -> tuple[Signal, ...]:
        if daily.trend in (None, Trend.SIDEWAYS) or h4.trend is not daily.trend:
            return ()
        if (
            h1.ema is None
            or h1.previous_ema is None
            or h1.close is None
            or h1.previous_close is None
            or h1.atr is None
        ):
            return ()
        distance = self.params.atr_multiple * h1.atr
        if daily.trend is Trend.BULLISH:
            if not (h1.previous_close <= h1.previous_ema and h1.close > h1.ema):
                return ()
            stop = h1.close - distance
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
        if not (h1.previous_close >= h1.previous_ema and h1.close < h1.ema):
            return ()
        return (
            Signal(
                Side.SELL,
                ctx.symbol,
                SignalKind.ENTRY,
                "1d and 4h trends down; 1h closed back below its EMA after a bounce",
                stop_loss=h1.close + distance,
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
