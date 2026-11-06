"""Trend utility: bullish / bearish / sideways per timeframe, with its four confirmations."""

import json
import math
from collections import Counter
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from factories import make_candles
from modules.market_data.domain.models import Candle, Timeframe
from modules.market_data.domain.trend import (
    DEFAULT_SETTINGS,
    Bar,
    FrameTrend,
    IndicatorState,
    Trend,
    TrendFrame,
    TrendReading,
    TrendSettings,
    TrendTracker,
    TrendTrackerState,
    analyze_trend,
    build_bars,
    classify_trend,
)

T0 = datetime(2024, 1, 1, tzinfo=UTC)  # a Monday, 00:00 UTC
SMALL = TrendSettings(fast=2, slow=4, min_distance_pct=Decimal("1"), adx_period=2, slope_bars=1)


def _cycle(count: int, start: float, drift: float, amplitude: float, period: int) -> list[str]:
    """Hourly closes: a drift plus a slow wave, so a trend has pullbacks like a real one."""
    return [
        f"{start + drift * i + amplitude * math.sin(2 * math.pi * i / period):.2f}"
        for i in range(count)
    ]


def _bars(closes: list[float], spread: float = 1.0) -> list[Bar]:
    return [
        Bar(
            T0 + timedelta(days=i),
            Decimal(str(closes[max(i - 1, 0)])),
            Decimal(str(c + spread)),
            Decimal(str(c - spread)),
            Decimal(str(c)),
        )
        for i, c in enumerate(closes)
    ]


def _run(engine: FrameTrend, bars: list[Bar]) -> tuple[IndicatorState, list[TrendReading]]:
    state, readings = engine.initial_state(), []
    for bar in bars:
        state = engine.update(state, bar)
        readings.append(engine.read(state))
    return state, readings


def _shares(readings: list[TrendReading]) -> dict[Trend, float]:
    known = [r.trend for r in readings if r.trend is not None]
    counts = Counter(known)
    return {t: counts[t] / len(known) for t in Trend}


def _feed(tracker: TrendTracker, candles: list[Candle]) -> TrendTrackerState:
    state = tracker.initial_state()
    for candle in candles:
        state = tracker.update(state, candle)
    return state


# --- the rule ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("close", "fast", "slow", "expected"),
    [
        ("110", "105", "100", Trend.BULLISH),
        ("90", "95", "100", Trend.BEARISH),
        ("102", "105", "100", Trend.SIDEWAYS),  # price below the fast EMA: a pullback
        ("98", "95", "100", Trend.SIDEWAYS),
        ("110", "95", "100", Trend.SIDEWAYS),  # EMAs crossed against the price
        ("100", "105", "100", Trend.SIDEWAYS),  # equal is not aligned
        ("105", "105", "100", Trend.SIDEWAYS),
    ],
)
def test_the_rule_needs_price_fast_and_slow_in_order(
    close: str, fast: str, slow: str, expected: Trend
) -> None:
    assert classify_trend(close=Decimal(close), fast=Decimal(fast), slow=Decimal(slow)) is expected


def test_defaults_follow_the_requested_averages_per_timeframe() -> None:
    assert {f: (s.fast, s.slow) for f, s in DEFAULT_SETTINGS.items()} == {
        TrendFrame.W1: (20, 50),
        TrendFrame.D1: (20, 50),
        TrendFrame.H4: (20, 50),
        TrendFrame.H1: (9, 21),
    }
    assert DEFAULT_SETTINGS[TrendFrame.D1].adx_min == 25


def test_timeframes_accept_plain_words() -> None:
    assert TrendFrame.parse("week") is TrendFrame.W1
    assert TrendFrame.parse("dia") is TrendFrame.D1
    assert TrendFrame.parse(" 4H ") is TrendFrame.H4
    assert TrendFrame.parse("1h") is TrendFrame.H1
    with pytest.raises(ValueError):
        TrendFrame.parse("month")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"fast": 1},
        {"fast": 30, "slow": 20},
        {"min_distance_pct": Decimal(-1)},
        {"adx_period": 1},
        {"slope_bars": 0},
        {"swing_window": 0},
    ],
)
def test_settings_are_validated(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        TrendSettings(**kwargs)  # type: ignore[arg-type]


# --- indicators ---------------------------------------------------------------------------------


def test_emas_are_seeded_with_the_plain_average_then_smoothed() -> None:
    engine = FrameTrend(TrendFrame.D1, TrendSettings(fast=3, slow=5))
    state, _ = _run(engine, _bars([1, 2, 3]))
    assert state.ema_fast == 2  # average of the first three closes
    state, _ = _run(engine, _bars([1, 2, 3, 4]))
    assert state.ema_fast == 3  # 2 + 2/(3+1) * (4 - 2)


def test_atr_is_the_average_true_range() -> None:
    engine = FrameTrend(TrendFrame.D1, TrendSettings(fast=2, slow=4, adx_period=3))
    _, readings = _run(engine, _bars([100] * 12, spread=5))  # every bar spans 10
    assert readings[-1].atr == 10


def test_adx_is_high_in_a_trend_and_low_in_a_chop() -> None:
    engine = FrameTrend(TrendFrame.D1)
    _, trending = _run(engine, _bars([100 + 3 * i for i in range(120)]))
    _, choppy = _run(engine, _bars([100 + (4 if i % 2 else -4) for i in range(120)]))
    assert trending[-1].adx is not None and trending[-1].adx > 40
    assert choppy[-1].adx is not None and choppy[-1].adx < 20


def test_swing_structure_reads_higher_highs_and_higher_lows() -> None:
    zigzag_up = [10, 12, 14, 12, 10, 12, 14, 16, 18, 16, 14, 16, 18, 20, 22, 20, 18, 20, 22, 24]
    engine = FrameTrend(TrendFrame.D1, SMALL)
    _, up = _run(engine, _bars([float(x) for x in zigzag_up]))
    _, down = _run(engine, _bars([float(100 - x) for x in zigzag_up]))
    assert up[-1].structure is Trend.BULLISH
    assert down[-1].structure is Trend.BEARISH
    _, early = _run(engine, _bars([10.0, 12.0, 14.0, 12.0, 10.0, 12.0]))
    assert early[-1].structure is None  # fewer than two swing highs and lows


def test_a_swing_is_only_known_after_its_confirmation_bars() -> None:
    engine = FrameTrend(TrendFrame.D1, SMALL)
    state, _ = _run(engine, _bars([10.0, 12.0, 14.0, 12.0]))  # the peak at 14 has 1 bar after it
    assert state.swing_highs == ()
    state, _ = _run(engine, _bars([10.0, 12.0, 14.0, 12.0, 10.0]))
    assert state.swing_highs == (Decimal("15.0"),)


# --- classification and confirmation -------------------------------------------------------------


def test_a_frame_is_unknown_until_it_has_its_slow_ema() -> None:
    _, readings = _run(FrameTrend(TrendFrame.D1), _bars([100.0 + i for i in range(60)]))
    assert readings[48].trend is None and not readings[48].ready
    assert readings[49].trend is not None  # the 50th bar


def test_an_uptrend_is_mostly_bullish_and_gets_confirmed() -> None:
    candles = make_candles(_cycle(24 * 330, 1000, 0.5, 60, 24 * 12))
    bars = build_bars(candles, TrendFrame.D1)
    _, readings = _run(FrameTrend(TrendFrame.D1), bars)
    shares = _shares(readings)
    assert shares[Trend.BULLISH] > 0.6 and shares[Trend.BEARISH] < 0.05
    assert any(r.confirmed for r in readings)
    confirmed = next(r for r in readings if r.confirmed)
    assert confirmed.trend is Trend.BULLISH
    assert set(confirmed.checks) == {"distance", "slope", "adx", "structure"}
    assert confirmed.ema_distance_pct is not None and confirmed.ema_distance_pct > 0
    assert confirmed.slow_slope_pct is not None and confirmed.slow_slope_pct > 0


def test_a_downtrend_is_mostly_bearish() -> None:
    candles = make_candles(_cycle(24 * 330, 6000, -0.5, 60, 24 * 12))
    _, readings = _run(FrameTrend(TrendFrame.D1), build_bars(candles, TrendFrame.D1))
    shares = _shares(readings)
    assert shares[Trend.BEARISH] > 0.6 and shares[Trend.BULLISH] < 0.05
    assert any(r.confirmed and r.trend is Trend.BEARISH for r in readings)


def test_a_flat_market_is_not_confirmed_as_a_trend() -> None:
    flat = [f"{1000 + 20 * math.sin(2 * math.pi * i / (24 * 9)):.2f}" for i in range(24 * 330)]
    _, readings = _run(FrameTrend(TrendFrame.D1), build_bars(make_candles(flat), TrendFrame.D1))
    assert not any(r.confirmed for r in readings)
    assert _shares(readings)[Trend.SIDEWAYS] > 0.3


def test_sideways_readings_carry_no_checks() -> None:
    _, readings = _run(FrameTrend(TrendFrame.D1), _bars([100.0] * 60))
    assert readings[-1].trend is Trend.SIDEWAYS
    assert readings[-1].checks == {} and not readings[-1].confirmed


def test_confirmation_fails_when_one_check_fails() -> None:
    settings = TrendSettings(fast=2, slow=4, min_distance_pct=Decimal(50), adx_period=2)
    engine = FrameTrend(TrendFrame.D1, settings)
    _, readings = _run(engine, _bars([100.0 + 2 * i for i in range(30)]))
    last = readings[-1]
    assert last.trend is Trend.BULLISH
    assert last.checks["distance"] is False  # the EMAs are nowhere near 50% apart
    assert last.checks["slope"] is True and last.checks["adx"] is True
    assert not last.confirmed


def test_the_previous_trend_is_kept_for_change_detection() -> None:
    closes = [100.0 + 2 * i for i in range(60)] + [220.0 - 6 * i for i in range(30)]
    _, readings = _run(FrameTrend(TrendFrame.D1), _bars(closes))
    ended = [r for r in readings if r.trend is Trend.SIDEWAYS and r.previous_trend is Trend.BULLISH]
    assert ended, "the rally ending must show as bullish -> sideways"


# --- building bars from candles ------------------------------------------------------------------


def test_candles_are_merged_into_ohlc_bars_in_utc() -> None:
    candles = make_candles(["10", "14", "8", "12", "20"], opens=["9", "10", "14", "8", "12"])
    (bar,) = build_bars(candles, TrendFrame.H4)
    assert bar.open_time == T0
    assert (bar.open, bar.close) == (Decimal("9"), Decimal("12"))
    assert bar.high == max(c.high for c in candles[:4])
    assert bar.low == min(c.low for c in candles[:4])


def test_bars_close_on_their_last_base_candle() -> None:
    tracker = TrendTracker(Timeframe.H1)
    state, counts = tracker.initial_state(), []
    for candle in make_candles(["100"] * 49):
        state = tracker.update(state, candle)
        counts.append({f: fs.indicators.bars for f, fs in state.frames.items()})
    assert counts[22][TrendFrame.D1] == 0 and counts[22][TrendFrame.H4] == 5
    assert counts[23][TrendFrame.D1] == 1 and counts[23][TrendFrame.H4] == 6
    assert counts[47][TrendFrame.D1] == 2
    assert counts[48][TrendFrame.D1] == 2  # first hour of day 3 closes nothing higher


def test_weeks_start_on_monday_utc() -> None:
    monday = datetime(2024, 1, 1, tzinfo=UTC)
    assert len(build_bars(make_candles(["100"] * 168, start=monday), TrendFrame.W1)) == 1
    wednesday = datetime(2024, 1, 3, tzinfo=UTC)  # the same candles straddle two weeks
    assert build_bars(make_candles(["100"] * 168, start=wednesday), TrendFrame.W1) == []
    assert len(build_bars(make_candles(["100"] * 168, start=wednesday), TrendFrame.D1)) == 7


def test_a_history_that_starts_mid_bar_never_counts_that_bar() -> None:
    start = datetime(2024, 1, 1, 5, tzinfo=UTC)
    candles = make_candles(["100"] * 43, start=start)  # 05:00 of day 1 .. 23:00 of day 2
    assert len(build_bars(candles, TrendFrame.D1)) == 1
    assert len(build_bars(candles, TrendFrame.H4)) == (43 - 3) // 4


def test_a_missing_candle_drops_the_bar_it_belongs_to() -> None:
    candles = make_candles(["100"] * 48)
    del candles[10]
    assert len(build_bars(candles, TrendFrame.D1)) == 1


def test_weekly_bars_can_be_built_from_daily_candles() -> None:
    bars = build_bars(make_candles(["100"] * 14, timeframe=Timeframe.D1), TrendFrame.W1)
    assert len(bars) == 2


def test_a_frame_shorter_than_the_base_is_refused() -> None:
    with pytest.raises(ValueError):
        TrendTracker(Timeframe.H4, {TrendFrame.H1: TrendSettings()})
    with pytest.raises(ValueError):
        TrendTracker(Timeframe.H1, {})
    tracker = TrendTracker(Timeframe.H1)
    with pytest.raises(ValueError):
        tracker.update(tracker.initial_state(), make_candles(["100"], timeframe=Timeframe.H4)[0])


def test_it_says_how_much_history_it_needs() -> None:
    daily_only = TrendTracker(Timeframe.H1, {TrendFrame.D1: DEFAULT_SETTINGS[TrendFrame.D1]})
    assert daily_only.required_base_candles() == (55 + 2) * 24
    assert TrendTracker(Timeframe.H1).required_base_candles() == (55 + 2) * 168  # the weekly frame


# --- the tracker ---------------------------------------------------------------------------------


def test_tracker_and_one_shot_analysis_agree_with_the_engine() -> None:
    candles = make_candles(_cycle(24 * 200, 1000, 0.5, 60, 24 * 12))
    readings = analyze_trend(candles)
    _, from_bars = _run(FrameTrend(TrendFrame.D1), build_bars(candles, TrendFrame.D1))
    assert readings[TrendFrame.D1] == from_bars[-1]
    assert readings[TrendFrame.W1].trend is None  # 28 weeks of history: not warm yet


def test_one_shot_analysis_leaves_out_frames_the_base_cannot_build() -> None:
    readings = analyze_trend(make_candles(["100"] * 30, timeframe=Timeframe.D1))
    assert set(readings) == {TrendFrame.D1, TrendFrame.W1}


def test_a_reading_never_depends_on_later_candles() -> None:
    candles = make_candles(_cycle(24 * 200, 1000, 0.5, 60, 24 * 12))
    tracker = TrendTracker(Timeframe.H1)
    cut = 24 * 150
    state = _feed(tracker, candles[:cut])
    snapshot = tracker.serialize(state)
    tracker.update(state, candles[cut])
    assert tracker.serialize(state) == snapshot  # update returned a new state


def test_state_survives_a_json_round_trip_and_continues_identically() -> None:
    candles = make_candles(_cycle(24 * 200, 1000, 0.5, 60, 24 * 12))
    tracker = TrendTracker(Timeframe.H1)
    straight = _feed(tracker, candles)

    half = _feed(tracker, candles[: 24 * 101 + 7])  # stopped in the middle of a day and a week
    saved = json.loads(json.dumps(tracker.serialize(half)))
    state = TrendTracker(Timeframe.H1).deserialize(saved)
    for candle in candles[24 * 101 + 7 :]:
        state = tracker.update(state, candle)

    assert tracker.read_all(state) == tracker.read_all(straight)
    assert tracker.serialize(state) == tracker.serialize(straight)
