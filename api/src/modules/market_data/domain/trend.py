"""Market trend per timeframe: BULLISH, BEARISH or SIDEWAYS for 1h, 4h, 1d and 1w.

A pure utility (no I/O, no clock) shared by strategies, risk, bots, the trend detector and
dashboards. Feed it closed candles of one base timeframe (1h is typical) and it builds the 4h /
1d / 1w bars itself, in UTC like Binance (weeks start on Monday 00:00 UTC). It only ever reads
*completed* bars, so a reading never contains the future.

**The rule** (two EMAs of the bar closes, per timeframe):

* BULLISH:  close > fast EMA > slow EMA
* BEARISH:  close < fast EMA < slow EMA
* SIDEWAYS: any other order (no alignment, or a transition)

Defaults: 1w, 1d and 4h use EMA 20 / 50; 1h uses EMA 9 / 21. Every length is a parameter.

**Confirmation** of a directional trend, four independent checks (each True / False, or None
while its data is warming up). ``TrendReading.confirmed`` needs all four:

* ``distance``: the fast and slow EMAs are at least ``min_distance_pct`` % apart;
* ``slope``: the slow EMA moved in the trend's direction over the last ``slope_bars`` bars;
* ``adx``: Wilder's ADX is at least ``adx_min`` (the trend has strength);
* ``structure``: the last two swing highs and lows are both higher (bullish) / lower (bearish).
  A swing needs ``swing_window`` bars on each side, so it is only known that many bars later.

A frame with fewer than ``slow`` completed bars has ``trend = None`` (unknown, not the same as
SIDEWAYS): callers decide what to do while warming up.

Two ways to use it::

    readings = analyze_trend(candles)                    # one shot, e.g. a report
    tracker = TrendTracker(Timeframe.H1)                 # incremental, e.g. inside a strategy
    state = tracker.update(state, candle)                # state is immutable and serialisable
    tracker.read(state, TrendFrame.D1).trend

``FrameTrend`` is the per-timeframe engine underneath: it works on ``Bar`` objects, so a series
of bars that did not come from candles (a test, a simulation) can be classified too.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Any

from modules.market_data.domain.models import Candle, Timeframe

_WEEK_OFFSET_SECONDS = 4 * 86_400  # the epoch was a Thursday; weeks start on Monday
_ZERO = Decimal(0)
_HUNDRED = Decimal(100)


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
        try:
            return _ALIASES[text.strip().lower()]
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
    fast: int = 20
    slow: int = 50
    min_distance_pct: Decimal = Decimal("1.0")  # EMA gap needed to confirm, in % of the slow EMA
    adx_min: Decimal = Decimal(25)
    adx_period: int = 14  # also the ATR period
    slope_bars: int = 5
    swing_window: int = 2

    def __post_init__(self) -> None:
        if not (2 <= self.fast < self.slow):
            raise ValueError("EMA lengths must satisfy 2 <= fast < slow")
        if self.min_distance_pct < 0 or self.adx_min < 0:
            raise ValueError("min_distance_pct and adx_min must be >= 0")
        if self.adx_period < 2 or self.slope_bars < 1 or self.swing_window < 1:
            raise ValueError("adx_period >= 2, slope_bars >= 1 and swing_window >= 1 are required")

    @property
    def bars_needed(self) -> int:
        """Completed bars before every number of a reading is available."""
        return max(self.slow + self.slope_bars, 2 * self.adx_period + 1)


# EMA 20/50 on the long frames, 9/21 on the short one. The distance gates grow with the frame
# because a bigger bar moves more; they are starting points that the validation study checks.
DEFAULT_SETTINGS: Mapping[TrendFrame, TrendSettings] = {
    TrendFrame.W1: TrendSettings(20, 50, Decimal("3.0")),
    TrendFrame.D1: TrendSettings(20, 50, Decimal("1.5")),
    TrendFrame.H4: TrendSettings(20, 50, Decimal("0.7")),
    TrendFrame.H1: TrendSettings(9, 21, Decimal("0.3")),
}


def classify_trend(*, close: Decimal, fast: Decimal, slow: Decimal) -> Trend:
    """The rule on its own."""
    if close > fast > slow:
        return Trend.BULLISH
    if close < fast < slow:
        return Trend.BEARISH
    return Trend.SIDEWAYS


@dataclass(frozen=True, slots=True)
class Bar:
    """A completed bar of one timeframe."""

    open_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal


@dataclass(frozen=True, slots=True)
class TrendReading:
    frame: TrendFrame
    trend: Trend | None  # None: not enough completed bars yet
    previous_trend: Trend | None
    bars: int  # completed bars seen so far
    bar_open_time: datetime | None  # the last completed bar
    close: Decimal | None = None
    ema_fast: Decimal | None = None
    ema_slow: Decimal | None = None
    ema_distance_pct: Decimal | None = None  # (fast - slow) / slow, in %; signed
    slow_slope_pct: Decimal | None = None  # slow EMA change over ``slope_bars`` bars, in %
    adx: Decimal | None = None
    atr: Decimal | None = None
    structure: Trend | None = None  # from the last two swing highs and lows
    #: distance / slope / adx / structure → True, False or None (unknown). Empty when SIDEWAYS.
    checks: Mapping[str, bool | None] = field(default_factory=dict)

    @property
    def ready(self) -> bool:
        return self.trend is not None

    @property
    def confirmed(self) -> bool:
        """A directional trend that passes all four checks."""
        return bool(self.checks) and all(value is True for value in self.checks.values())

    @property
    def is_directional(self) -> bool:
        return self.trend in (Trend.BULLISH, Trend.BEARISH)


@dataclass(frozen=True, slots=True)
class IndicatorState:
    bars: int = 0
    last_open_time: datetime | None = None
    close: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    ema_fast: Decimal | None = None
    ema_slow: Decimal | None = None
    slow_recent: tuple[Decimal, ...] = ()  # last slope_bars + 1 slow EMA values
    trend: Trend | None = None
    previous_trend: Trend | None = None
    # Wilder smoothing for ATR / ADX.
    diffs: int = 0  # bars that had a previous bar to compare with
    tr_sum: Decimal = _ZERO
    pdm_sum: Decimal = _ZERO
    mdm_sum: Decimal = _ZERO
    dx_count: int = 0
    dx_sum: Decimal = _ZERO
    adx: Decimal | None = None
    # Swing structure.
    window: tuple[tuple[Decimal, Decimal], ...] = ()  # (high, low) of the last 2w+1 bars
    swing_highs: tuple[Decimal, ...] = ()  # last two
    swing_lows: tuple[Decimal, ...] = ()


def _ema(value: Decimal | None, count: int, period: int, close: Decimal) -> Decimal:
    if value is None:
        return close
    if count < period:  # seed with the plain average of the first ``period`` closes
        return (value * count + close) / (count + 1)
    return value + Decimal(2) / (period + 1) * (close - value)


class FrameTrend:
    """Trend engine of one timeframe, working bar by bar."""

    def __init__(self, frame: TrendFrame, settings: TrendSettings | None = None) -> None:
        self.frame = frame
        self.settings = DEFAULT_SETTINGS[frame] if settings is None else settings

    def initial_state(self) -> IndicatorState:
        return IndicatorState()

    def update(self, s: IndicatorState, bar: Bar) -> IndicatorState:
        """State after one more completed bar (``s`` is never changed)."""
        cfg = self.settings
        ema_fast = _ema(s.ema_fast, s.bars, cfg.fast, bar.close)
        ema_slow = _ema(s.ema_slow, s.bars, cfg.slow, bar.close)
        recent = (*s.slow_recent, ema_slow)[-(cfg.slope_bars + 1) :]
        bars = s.bars + 1
        trend = (
            classify_trend(close=bar.close, fast=ema_fast, slow=ema_slow)
            if bars >= cfg.slow
            else None
        )

        n = cfg.adx_period
        diffs, tr_sum, pdm_sum, mdm_sum = s.diffs, s.tr_sum, s.pdm_sum, s.mdm_sum
        dx_count, dx_sum, adx = s.dx_count, s.dx_sum, s.adx
        if s.close is not None and s.high is not None and s.low is not None:
            true_range = max(bar.high - bar.low, abs(bar.high - s.close), abs(bar.low - s.close))
            up, down = bar.high - s.high, s.low - bar.low
            pdm = up if up > down and up > 0 else _ZERO
            mdm = down if down > up and down > 0 else _ZERO
            diffs += 1
            if diffs <= n:
                tr_sum, pdm_sum, mdm_sum = tr_sum + true_range, pdm_sum + pdm, mdm_sum + mdm
            else:
                tr_sum = tr_sum - tr_sum / n + true_range
                pdm_sum = pdm_sum - pdm_sum / n + pdm
                mdm_sum = mdm_sum - mdm_sum / n + mdm
            if diffs >= n and tr_sum > 0:
                pdi, mdi = _HUNDRED * pdm_sum / tr_sum, _HUNDRED * mdm_sum / tr_sum
                dx = _HUNDRED * abs(pdi - mdi) / (pdi + mdi) if pdi + mdi > 0 else _ZERO
                if dx_count < n:
                    dx_count, dx_sum = dx_count + 1, dx_sum + dx
                    if dx_count == n:
                        adx = dx_sum / n
                elif adx is not None:
                    adx = (adx * (n - 1) + dx) / n

        w = cfg.swing_window
        window = (*s.window, (bar.high, bar.low))[-(2 * w + 1) :]
        highs, lows = s.swing_highs, s.swing_lows
        if len(window) == 2 * w + 1:
            centre = window[w]
            others = (*window[:w], *window[w + 1 :])
            if all(centre[0] > high for high, _ in others):
                highs = (*highs, centre[0])[-2:]
            if all(centre[1] < low for _, low in others):
                lows = (*lows, centre[1])[-2:]

        return IndicatorState(
            bars, bar.open_time, bar.close, bar.high, bar.low, ema_fast, ema_slow, recent,
            trend, s.trend, diffs, tr_sum, pdm_sum, mdm_sum, dx_count, dx_sum, adx, window,
            highs, lows,
        )  # fmt: skip

    def read(self, s: IndicatorState) -> TrendReading:
        cfg = self.settings
        if s.trend is None or s.ema_fast is None or s.ema_slow is None or s.close is None:
            return TrendReading(
                self.frame, None, None, s.bars, s.last_open_time, s.close, s.ema_fast, s.ema_slow
            )
        distance = (s.ema_fast - s.ema_slow) / s.ema_slow * _HUNDRED if s.ema_slow != 0 else None
        slope = None
        if s.bars >= cfg.slow + cfg.slope_bars and len(s.slow_recent) == cfg.slope_bars + 1:
            base = s.slow_recent[0]
            slope = (s.ema_slow - base) / base * _HUNDRED if base != 0 else None
        atr = s.tr_sum / cfg.adx_period if s.diffs >= cfg.adx_period else None
        structure = self._structure(s)
        checks: dict[str, bool | None] = {}
        if s.trend is not Trend.SIDEWAYS:
            up = s.trend is Trend.BULLISH
            checks = {
                "distance": None if distance is None else abs(distance) >= cfg.min_distance_pct,
                "slope": None if slope is None else (slope > 0 if up else slope < 0),
                "adx": None if s.adx is None else s.adx >= cfg.adx_min,
                "structure": None if structure is None else structure is s.trend,
            }
        return TrendReading(
            self.frame, s.trend, s.previous_trend, s.bars, s.last_open_time, s.close, s.ema_fast,
            s.ema_slow, distance, slope, s.adx, atr, structure, checks,
        )  # fmt: skip

    @staticmethod
    def _structure(s: IndicatorState) -> Trend | None:
        if len(s.swing_highs) < 2 or len(s.swing_lows) < 2:
            return None
        higher_high, higher_low = (
            s.swing_highs[1] > s.swing_highs[0],
            s.swing_lows[1] > s.swing_lows[0],
        )
        lower_high, lower_low = (
            s.swing_highs[1] < s.swing_highs[0],
            s.swing_lows[1] < s.swing_lows[0],
        )
        if higher_high and higher_low:
            return Trend.BULLISH
        if lower_high and lower_low:
            return Trend.BEARISH
        return Trend.SIDEWAYS


# --- building bars from candles -------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Bucket:
    """A higher-timeframe bar being assembled from base candles."""

    index: int | None = None
    seen: int = 0  # base candles collected; stays below the bar length for a partial bar
    open: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None


def _geometry(frame: TrendFrame) -> tuple[int, int]:
    """(bar length in seconds, UTC offset of the first bar)."""
    return int(frame.delta.total_seconds()), _WEEK_OFFSET_SECONDS if frame is TrendFrame.W1 else 0


def add_candle(
    bucket: Bucket, candle: Candle, frame: TrendFrame, base_seconds: int
) -> tuple[Bucket, Bar | None]:
    """Add one closed candle to a bar; returns the bar when this candle completes it.

    A bar that began before the history did, or that lost a candle, is dropped, never
    half-counted."""
    length_seconds, offset = _geometry(frame)
    timestamp = int(candle.open_time.timestamp())
    index = (timestamp - offset) // length_seconds
    if bucket.index == index and bucket.high is not None and bucket.low is not None:
        seen = bucket.seen + 1
        opened, high, low = bucket.open, max(bucket.high, candle.high), min(bucket.low, candle.low)
    else:
        starts_bar = (timestamp - offset) % length_seconds == 0
        seen, opened, high, low = (1 if starts_bar else 0), candle.open, candle.high, candle.low
    complete = (timestamp + base_seconds - offset) % length_seconds == 0 and seen == (
        length_seconds // base_seconds
    )
    if not complete or opened is None:
        return Bucket(index, seen, opened, high, low), None
    start = datetime.fromtimestamp(index * length_seconds + offset, UTC)
    return Bucket(index, 0), Bar(start, opened, high, low, candle.close)


def build_bars(candles: Sequence[Candle], frame: TrendFrame) -> list[Bar]:
    """Every completed ``frame`` bar of a candle series (oldest first, one timeframe)."""
    if not candles:
        return []
    base = candles[0].timeframe
    _check_buildable(frame, base)
    bucket, bars = Bucket(), []
    for candle in candles:
        bucket, bar = add_candle(bucket, candle, frame, int(base.delta.total_seconds()))
        if bar is not None:
            bars.append(bar)
    return bars


def _check_buildable(frame: TrendFrame, base: Timeframe) -> None:
    if frame.delta < base.delta or frame.delta % base.delta != timedelta(0):
        raise ValueError(f"{frame.value} cannot be built from {base.value} candles")


# --- incremental multi-timeframe tracker ----------------------------------------------------


@dataclass(frozen=True, slots=True)
class FrameState:
    bucket: Bucket = Bucket()
    indicators: IndicatorState = IndicatorState()


@dataclass(frozen=True, slots=True)
class TrendTrackerState:
    frames: Mapping[TrendFrame, FrameState] = field(default_factory=dict)


class TrendTracker:
    """Incremental trend reader over candles of one base timeframe."""

    def __init__(
        self, base: Timeframe, settings: Mapping[TrendFrame, TrendSettings] | None = None
    ) -> None:
        self.base = base
        chosen = DEFAULT_SETTINGS if settings is None else settings
        if not chosen:
            raise ValueError("at least one timeframe is needed")
        self._engines = {frame: FrameTrend(frame, cfg) for frame, cfg in chosen.items()}
        self._base_seconds = int(base.delta.total_seconds())
        for frame in self._engines:
            _check_buildable(frame, base)

    @property
    def frames(self) -> tuple[TrendFrame, ...]:
        return tuple(self._engines)

    def settings_of(self, frame: TrendFrame) -> TrendSettings:
        return self._engines[frame].settings

    def required_base_candles(self) -> int:
        """Base candles to feed before every frame can be read completely.

        Counts the bars each frame needs, one bar lost to a history that starts mid-bar and one
        bar of margin."""
        return max(
            (engine.settings.bars_needed + 2) * (engine.frame.delta // self.base.delta)
            for engine in self._engines.values()
        )

    def initial_state(self) -> TrendTrackerState:
        return TrendTrackerState({frame: FrameState() for frame in self._engines})

    def update(self, state: TrendTrackerState, candle: Candle) -> TrendTrackerState:
        """State after one more closed base candle (``state`` itself is never changed)."""
        if candle.timeframe is not self.base:
            raise ValueError(f"expected {self.base.value} candles, got {candle.timeframe.value}")
        frames: dict[TrendFrame, FrameState] = {}
        for frame, engine in self._engines.items():
            current = state.frames.get(frame, FrameState())
            bucket, bar = add_candle(current.bucket, candle, frame, self._base_seconds)
            indicators = (
                current.indicators if bar is None else engine.update(current.indicators, bar)
            )
            frames[frame] = FrameState(bucket, indicators)
        return TrendTrackerState(frames)

    def read(self, state: TrendTrackerState, frame: TrendFrame) -> TrendReading:
        return self._engines[frame].read(state.frames.get(frame, FrameState()).indicators)

    def read_all(self, state: TrendTrackerState) -> dict[TrendFrame, TrendReading]:
        return {frame: self.read(state, frame) for frame in self._engines}

    # --- persistence ---------------------------------------------------------------------

    def serialize(self, state: TrendTrackerState) -> dict[str, Any]:
        return {
            frame.value: {"bucket": _dump_bucket(fs.bucket), "indicators": _dump(fs.indicators)}
            for frame, fs in state.frames.items()
        }

    def deserialize(self, raw: Mapping[str, Any]) -> TrendTrackerState:
        frames: dict[TrendFrame, FrameState] = {}
        for frame in self._engines:
            item = raw.get(frame.value)
            frames[frame] = (
                FrameState()
                if item is None
                else FrameState(_load_bucket(item["bucket"]), _load(item["indicators"]))
            )
        return TrendTrackerState(frames)


def analyze_trend(
    candles: Sequence[Candle], settings: Mapping[TrendFrame, TrendSettings] | None = None
) -> dict[TrendFrame, TrendReading]:
    """One-shot reading of every timeframe from closed candles (oldest first, one timeframe).

    Frames the base timeframe cannot build are left out; frames with too little history come
    back with ``trend = None``."""
    if not candles:
        raise ValueError("no candles to analyze")
    base = candles[0].timeframe
    chosen = DEFAULT_SETTINGS if settings is None else settings
    tracker = TrendTracker(base, {f: s for f, s in chosen.items() if f.delta >= base.delta})
    state = tracker.initial_state()
    for candle in candles:
        state = tracker.update(state, candle)
    return tracker.read_all(state)


# --- (de)serialisation helpers --------------------------------------------------------------


def _text(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _num(value: str | None) -> Decimal | None:
    return None if value is None else Decimal(value)


def _dump_bucket(b: Bucket) -> dict[str, Any]:
    return {
        "index": b.index, "seen": b.seen, "open": _text(b.open), "high": _text(b.high),
        "low": _text(b.low),
    }  # fmt: skip


def _load_bucket(raw: Mapping[str, Any]) -> Bucket:
    return Bucket(raw["index"], int(raw["seen"]), _num(raw["open"]), _num(raw["high"]),
                  _num(raw["low"]))  # fmt: skip


def _dump(s: IndicatorState) -> dict[str, Any]:
    return {
        "bars": s.bars,
        "last_open_time": None if s.last_open_time is None else s.last_open_time.isoformat(),
        "close": _text(s.close), "high": _text(s.high), "low": _text(s.low),
        "ema_fast": _text(s.ema_fast), "ema_slow": _text(s.ema_slow),
        "slow_recent": [str(v) for v in s.slow_recent],
        "trend": None if s.trend is None else s.trend.value,
        "previous_trend": None if s.previous_trend is None else s.previous_trend.value,
        "diffs": s.diffs, "tr_sum": str(s.tr_sum), "pdm_sum": str(s.pdm_sum),
        "mdm_sum": str(s.mdm_sum), "dx_count": s.dx_count, "dx_sum": str(s.dx_sum),
        "adx": _text(s.adx),
        "window": [[str(h), str(low)] for h, low in s.window],
        "swing_highs": [str(v) for v in s.swing_highs],
        "swing_lows": [str(v) for v in s.swing_lows],
    }  # fmt: skip


def _load(raw: Mapping[str, Any]) -> IndicatorState:
    def trend(value: str | None) -> Trend | None:
        return None if value is None else Trend(value)

    opened = raw["last_open_time"]
    return IndicatorState(
        int(raw["bars"]),
        None if opened is None else datetime.fromisoformat(opened),
        _num(raw["close"]), _num(raw["high"]), _num(raw["low"]),
        _num(raw["ema_fast"]), _num(raw["ema_slow"]),
        tuple(Decimal(v) for v in raw["slow_recent"]),
        trend(raw["trend"]), trend(raw["previous_trend"]),
        int(raw["diffs"]), Decimal(raw["tr_sum"]), Decimal(raw["pdm_sum"]),
        Decimal(raw["mdm_sum"]), int(raw["dx_count"]), Decimal(raw["dx_sum"]), _num(raw["adx"]),
        tuple((Decimal(h), Decimal(low)) for h, low in raw["window"]),
        tuple(Decimal(v) for v in raw["swing_highs"]),
        tuple(Decimal(v) for v in raw["swing_lows"]),
    )  # fmt: skip
