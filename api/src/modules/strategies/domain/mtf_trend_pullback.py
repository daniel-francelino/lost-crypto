"""Multi-timeframe trend pullback: 1d trend picks the side, 4h confirms, 1h times the entry.

The bot runs on **1h** candles. The trend of each timeframe comes from the shared detector
``market_data.domain.trend`` (BULLISH / BEARISH / SIDEWAYS from EMA 20/50 on 1d and 4h, EMA 9/21
on 1h, completed bars only):

1. **Main trend (1d).** BULLISH means LONG, BEARISH means SHORT, SIDEWAYS means stay out. With
   ``daily_confirmation`` on, the daily trend must also pass the detector's four checks
   (EMA distance, slow-EMA slope, ADX, swing structure).
2. **Alignment (4h).** The 4h trend must be the same as the daily one.
3. **Entry (1h).** The short-term trend turns in the trade's direction: the 1h reading becomes
   BULLISH (price > EMA 9 > EMA 21) after not being so, i.e. the end of a pullback. Short entries
   need ``allow_short``.

Exit: the daily trend is no longer the trade's direction, or the 4h trend turned against it, or
the protective stop is hit. The stop sits ``atr_multiple`` 1h average true ranges from the
close. There is no profit target: a trend follower is paid by the right tail.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Self

from modules.market_data.domain.models import Timeframe
from modules.market_data.domain.trend import (
    DEFAULT_SETTINGS,
    Trend,
    TrendFrame,
    TrendReading,
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

MAX_HISTORY_CANDLES = 3000  # what the live bot is willing to fetch to warm up


@dataclass(frozen=True, slots=True)
class MtfTrendParams:
    atr_multiple: Decimal = Decimal(3)
    daily_confirmation: int = 0

    def __post_init__(self) -> None:
        if self.atr_multiple <= 0:
            raise InvalidStrategyParams("atr_multiple must be > 0")
        if self.daily_confirmation not in (0, 1):
            raise InvalidStrategyParams("daily_confirmation must be 0 or 1")


def _opposite(trend: Trend) -> Trend:
    return Trend.BEARISH if trend is Trend.BULLISH else Trend.BULLISH


class MtfTrendPullbackStrategy(Strategy[TrendTrackerState]):
    TYPE_KEY = "mtf_trend_pullback"
    STYLE = StrategyStyle.TREND
    NAME = "Multi-timeframe trend pullback (1d trend, 4h alignment, 1h entry)"
    DESCRIPTION = (
        "Run it on 1h candles. The daily trend (EMA 20/50) picks LONG or SHORT, the 4h trend "
        "must agree, and the entry is the 1h trend (EMA 9/21) turning in that direction. Exits "
        "when the daily trend ends or the 4h turns against the trade, or at an ATR stop. "
        "Shorts need Futures with short enabled."
    )
    PARAMETERS = (
        ParamSpec(
            "atr_multiple",
            "number",
            3,
            "Stop distance in 1h average true ranges of 14 candles (> 0)",
            Decimal("0.1"),
        ),
        ParamSpec(
            "daily_confirmation",
            "integer",
            0,
            "1 = also require the daily trend to pass the four confirmation checks",
            0,
        ),
    )

    def __init__(self, params: MtfTrendParams) -> None:
        self.params = params
        self._tracker = TrendTracker(
            Timeframe.H1,
            {
                frame: DEFAULT_SETTINGS[frame]
                for frame in (TrendFrame.D1, TrendFrame.H4, TrendFrame.H1)
            },
        )

    @classmethod
    def from_params(cls, params: Mapping[str, Any]) -> Self:
        values = parse_numeric_params(
            params,
            integers=frozenset({"daily_confirmation"}),
            numbers=frozenset({"atr_multiple"}),
        )
        if "atr_multiple" in values and values["atr_multiple"] is None:
            raise InvalidStrategyParams("atr_multiple must be a number")
        return cls(MtfTrendParams(**values))

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
            signals = self._exit(ctx, daily, h4)
        return StrategyResult(signals, new_state)

    def _entry(
        self, ctx: StrategyContext, daily: TrendReading, h4: TrendReading, h1: TrendReading
    ) -> tuple[Signal, ...]:
        direction = daily.trend
        if direction not in (Trend.BULLISH, Trend.BEARISH) or h4.trend is not direction:
            return ()
        if self.params.daily_confirmation and not daily.confirmed:
            return ()
        if h1.trend is not direction or h1.previous_trend is direction or h1.atr is None:
            return ()
        if h1.close is None:
            return ()
        distance = self.params.atr_multiple * h1.atr
        if direction is Trend.BULLISH:
            stop = h1.close - distance
            return (
                Signal(
                    Side.BUY,
                    ctx.symbol,
                    SignalKind.ENTRY,
                    "1d and 4h trends up; the 1h trend turned up after a pullback",
                    stop_loss=stop if stop > 0 else None,
                ),
            )
        if not ctx.allow_short:
            return ()
        return (
            Signal(
                Side.SELL,
                ctx.symbol,
                SignalKind.ENTRY,
                "1d and 4h trends down; the 1h trend turned down after a bounce",
                stop_loss=h1.close + distance,
            ),
        )

    def _exit(
        self, ctx: StrategyContext, daily: TrendReading, h4: TrendReading
    ) -> tuple[Signal, ...]:
        held = Trend.BULLISH if ctx.is_long else Trend.BEARISH
        if daily.trend is None or h4.trend is None:
            return ()
        if daily.trend is not held:
            reason = "the daily trend is no longer in the trade's direction"
        elif h4.trend is _opposite(held):
            reason = "the 4h trend turned against the trade"
        else:
            return ()
        return (
            Signal(Side.SELL if ctx.is_long else Side.BUY, ctx.symbol, SignalKind.EXIT, reason),
        )
