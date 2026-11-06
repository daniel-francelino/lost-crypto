"""Market trend per timeframe: BULLISH, BEARISH or SIDEWAYS for 1h, 4h, 1d and 1w.

A pure utility (no I/O, no clock) meant to be shared by strategies, risk, bots and dashboards.
Feed it closed candles of one base timeframe (1h is typical) and it builds the 4h / 1d / 1w bars
itself, in UTC like Binance (weeks start on Monday 00:00 UTC). It only ever reads *completed*
bars, so a reading never contains the future.

How a frame is classified, from its last completed bar:

* ``ema``: EMA of the bar closes (seeded with the plain average of the first ``ema_period``).
* ``slope``: how far the EMA moved over the last ``SLOPE_BARS`` bars, measured in ATRs of that
  frame, so the same threshold means the same thing on BTC and on a small altcoin, on 1h and on
  1w.
* BULLISH: the close is above the EMA *and* the EMA rose by more than ``flat_band`` ATRs.
  BEARISH: the mirror image. Anything else, including a close on one side of an EMA that is not
  going anywhere, is SIDEWAYS.

A frame without enough completed bars has ``trend = None`` (unknown), which is not the same as
SIDEWAYS: callers decide what to do while warming up.

Two ways to use it::

    readings = analyze_trend(candles)                    # one shot, e.g. a dashboard or a report
    tracker = TrendTracker(Timeframe.H1)                 # incremental, e.g. inside a strategy
    state = tracker.update(state, candle)                # state is immutable and serialisable
    tracker.read(state, TrendFrame.D1).trend
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Any

from modules.market_data.domain.models import Candle, Timeframe

SLOPE_BARS = 3  # the EMA is compared with its own value this many bars ago
_WEEK_OFFSET_SECONDS = 4 * 86_400  # the epoch was a Thursday; weeks start on Monday


class Trend(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    SIDEWAYS = "sideways"


class TrendFrame(StrEnum):
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"

    @property
    def delta(self) -> timedelta:
        return _FRAME_DELTAS[self]

    @classmethod
    def parse(cls, text: str) -> "TrendFrame":
        """Accepts the values (``1h``) and plain words (``hour``, ``day``, ``week``)."""
        key = text.strip().lower()
        try:
            return _ALIASES[key]
        except KeyError:
            raise ValueError(f"unknown trend timeframe {text!r}") from None


_FRAME_DELTAS = {
    TrendFrame.H1: timedelta(hours=1),
    TrendFrame.H4: timedelta(hours=4),
    TrendFrame.D1: timedelta(days=1),
    TrendFrame.W1: timedelta(days=7),
}
_ALIASES = {
    **{frame.value: frame for frame in TrendFrame},
    "h1": TrendFrame.H1,
    "hour": TrendFrame.H1,
    "h4": TrendFrame.H4,
    "d1": TrendFrame.D1,
    "d": TrendFrame.D1,
    "day": TrendFrame.D1,
    "dia": TrendFrame.D1,
    "w1": TrendFrame.W1,
    "w": TrendFrame.W1,
    "week": TrendFrame.W1,
    "semana": TrendFrame.W1,
}


@dataclass(frozen=True, slots=True)
class TrendSettings:
    ema_period: int = 20
    atr_period: int = 14
    # |EMA change over SLOPE_BARS bars| must exceed this many ATRs to count as a trend.
    flat_band: Decimal = Decimal("0.25")

    def __post_init__(self) -> None:
        if self.ema_period < 2 or self.atr_period < 2:
            raise ValueError("ema_period and atr_period must be >= 2")
        if self.flat_band < 0:
            raise ValueError("flat_band must be >= 0")

    @property
    def bars_needed(self) -> int:
        """Completed bars before the frame can be read."""
        return max(self.ema_period + SLOPE_BARS, self.atr_period)


# A weekly EMA of 20 would need 140 days of history; 10 weeks is the same "few months" horizon.
DEFAULT_SETTINGS: Mapping[TrendFrame, TrendSettings] = {
    TrendFrame.H1: TrendSettings(),
    TrendFrame.H4: TrendSettings(),
    TrendFrame.D1: TrendSettings(),
    TrendFrame.W1: TrendSettings(ema_period=10),
}


def classify_trend(
    *, close: Decimal, ema: Decimal, slope: Decimal, atr: Decimal, flat_band: Decimal
) -> Trend:
    """The classification rule on its own (``slope`` = EMA now minus EMA ``SLOPE_BARS`` ago)."""
    if atr <= 0:
        return Trend.SIDEWAYS
    threshold = flat_band * atr
    if close > ema and slope > threshold:
        return Trend.BULLISH
    if close < ema and -slope > threshold:
        return Trend.BEARISH
    return Trend.SIDEWAYS


@dataclass(frozen=True, slots=True)
class TrendReading:
    frame: TrendFrame
    trend: Trend | None  # None: not enough completed bars yet
    bars: int  # completed bars seen so far
    close: Decimal | None = None
    previous_close: Decimal | None = None
    ema: Decimal | None = None
    previous_ema: Decimal | None = None
    atr: Decimal | None = None
    #: EMA change over SLOPE_BARS bars, in ATRs (positive = rising).
    slope_atr: Decimal | None = None

    @property
    def ready(self) -> bool:
        return self.trend is not None


@dataclass(frozen=True, slots=True)
class FrameState:
    # The bar being assembled from base candles.
    index: int | None = None
    seen: int = 0
    high: Decimal | None = None
    low: Decimal | None = None
    # Completed bars.
    bars: int = 0
    ema: Decimal | None = None
    recent: tuple[Decimal, ...] = ()  # last SLOPE_BARS + 1 EMA values, current included
    close: Decimal | None = None
    previous_close: Decimal | None = None
    ranges: tuple[Decimal, ...] = ()


@dataclass(frozen=True, slots=True)
class TrendTrackerState:
    frames: Mapping[TrendFrame, FrameState] = field(default_factory=dict)


def _true_range(high: Decimal, low: Decimal, previous_close: Decimal | None) -> Decimal:
    if previous_close is None:
        return high - low
    return max(high - low, abs(high - previous_close), abs(low - previous_close))


class TrendTracker:
    """Incremental trend reader over candles of one base timeframe."""

    def __init__(
        self, base: Timeframe, settings: Mapping[TrendFrame, TrendSettings] | None = None
    ) -> None:
        self.base = base
        self.settings = dict(DEFAULT_SETTINGS if settings is None else settings)
        if not self.settings:
            raise ValueError("at least one timeframe is needed")
        self._base_seconds = int(base.delta.total_seconds())
        self._length: dict[TrendFrame, int] = {}
        for frame in self.settings:
            if frame.delta < base.delta or frame.delta % base.delta != timedelta(0):
                raise ValueError(f"{frame.value} cannot be built from {base.value} candles")
            self._length[frame] = frame.delta // base.delta

    @property
    def frames(self) -> tuple[TrendFrame, ...]:
        return tuple(self.settings)

    def required_base_candles(self) -> int:
        """Base candles to feed before every frame can be read.

        Counts the bars each frame needs, one bar lost to a history that starts mid-bar and one
        bar of margin."""
        return max((s.bars_needed + 2) * self._length[f] for f, s in self.settings.items())

    def initial_state(self) -> TrendTrackerState:
        return TrendTrackerState({frame: FrameState() for frame in self.settings})

    def update(self, state: TrendTrackerState, candle: Candle) -> TrendTrackerState:
        """State after one more closed base candle (``state`` itself is never changed)."""
        if candle.timeframe is not self.base:
            raise ValueError(f"expected {self.base.value} candles, got {candle.timeframe.value}")
        timestamp = int(candle.open_time.timestamp())
        return TrendTrackerState(
            {
                frame: self._advance(
                    frame,
                    self.settings[frame],
                    state.frames.get(frame, FrameState()),
                    candle,
                    timestamp,
                )
                for frame in self.settings
            }
        )

    def read(self, state: TrendTrackerState, frame: TrendFrame) -> TrendReading:
        settings = self.settings[frame]
        fs = state.frames.get(frame, FrameState())
        warm = (
            fs.bars >= settings.bars_needed
            and len(fs.recent) == SLOPE_BARS + 1
            and len(fs.ranges) >= settings.atr_period
            and fs.ema is not None
            and fs.close is not None
        )
        if not warm or fs.ema is None or fs.close is None:
            return TrendReading(frame, None, fs.bars, fs.close, fs.previous_close, fs.ema)
        atr = sum(fs.ranges, Decimal(0)) / len(fs.ranges)
        slope = fs.ema - fs.recent[0]
        trend = classify_trend(
            close=fs.close, ema=fs.ema, slope=slope, atr=atr, flat_band=settings.flat_band
        )
        return TrendReading(
            frame,
            trend,
            fs.bars,
            fs.close,
            fs.previous_close,
            fs.ema,
            fs.recent[-2],
            atr,
            slope / atr if atr > 0 else Decimal(0),
        )

    def read_all(self, state: TrendTrackerState) -> dict[TrendFrame, TrendReading]:
        return {frame: self.read(state, frame) for frame in self.settings}

    # --- persistence ---------------------------------------------------------------------

    def serialize(self, state: TrendTrackerState) -> dict[str, Any]:
        return {frame.value: _dump(fs) for frame, fs in state.frames.items()}

    def deserialize(self, raw: Mapping[str, Any]) -> TrendTrackerState:
        return TrendTrackerState(
            {
                frame: _load(raw[frame.value]) if frame.value in raw else FrameState()
                for frame in self.settings
            }
        )

    # --- internals -----------------------------------------------------------------------

    def _advance(
        self,
        frame: TrendFrame,
        settings: TrendSettings,
        fs: FrameState,
        candle: Candle,
        timestamp: int,
    ) -> FrameState:
        frame_seconds = int(frame.delta.total_seconds())
        offset = _WEEK_OFFSET_SECONDS if frame is TrendFrame.W1 else 0
        index = (timestamp - offset) // frame_seconds
        starts_bar = (timestamp - offset) % frame_seconds == 0
        if fs.index == index and fs.high is not None and fs.low is not None:
            seen, high, low = fs.seen + 1, max(fs.high, candle.high), min(fs.low, candle.low)
        else:
            # A bar joined mid-way (history starting inside it) can never be complete: seen = 0.
            seen, high, low = (1 if starts_bar else 0), candle.high, candle.low
        last_of_bar = (timestamp + self._base_seconds - offset) % frame_seconds == 0
        if not (last_of_bar and seen == self._length[frame]):
            return FrameState(
                index,
                seen,
                high,
                low,
                fs.bars,
                fs.ema,
                fs.recent,
                fs.close,
                fs.previous_close,
                fs.ranges,
            )
        close = candle.close
        ranges = (*fs.ranges, _true_range(high, low, fs.close))[-settings.atr_period :]
        if fs.ema is None:
            ema = close
        elif fs.bars < settings.ema_period:
            ema = (fs.ema * fs.bars + close) / (fs.bars + 1)  # plain average while seeding
        else:
            ema = fs.ema + Decimal(2) / (settings.ema_period + 1) * (close - fs.ema)
        recent = (*fs.recent, ema)[-(SLOPE_BARS + 1) :]
        return FrameState(index, 0, None, None, fs.bars + 1, ema, recent, close, fs.close, ranges)


def _dump(fs: FrameState) -> dict[str, Any]:
    def text(value: Decimal | None) -> str | None:
        return None if value is None else str(value)

    return {
        "index": fs.index,
        "seen": fs.seen,
        "high": text(fs.high),
        "low": text(fs.low),
        "bars": fs.bars,
        "ema": text(fs.ema),
        "recent": [str(v) for v in fs.recent],
        "close": text(fs.close),
        "previous_close": text(fs.previous_close),
        "ranges": [str(v) for v in fs.ranges],
    }


def _load(raw: Mapping[str, Any]) -> FrameState:
    def number(value: str | None) -> Decimal | None:
        return None if value is None else Decimal(value)

    return FrameState(
        raw["index"],
        int(raw["seen"]),
        number(raw["high"]),
        number(raw["low"]),
        int(raw["bars"]),
        number(raw["ema"]),
        tuple(Decimal(v) for v in raw["recent"]),
        number(raw["close"]),
        number(raw["previous_close"]),
        tuple(Decimal(v) for v in raw["ranges"]),
    )


def analyze_trend(
    candles: Sequence[Candle], settings: Mapping[TrendFrame, TrendSettings] | None = None
) -> dict[TrendFrame, TrendReading]:
    """One-shot reading of every timeframe from closed candles (oldest first, one timeframe).

    Frames longer than the data allows come back with ``trend = None``."""
    if not candles:
        raise ValueError("no candles to analyze")
    tracker = TrendTracker(candles[0].timeframe, _usable(candles[0].timeframe, settings))
    state = tracker.initial_state()
    for candle in candles:
        state = tracker.update(state, candle)
    return tracker.read_all(state)


def _usable(
    base: Timeframe, settings: Mapping[TrendFrame, TrendSettings] | None
) -> dict[TrendFrame, TrendSettings]:
    """Default frames that the base timeframe can actually build (1h candles give all four)."""
    chosen = DEFAULT_SETTINGS if settings is None else settings
    return {f: s for f, s in chosen.items() if f.delta >= base.delta}
