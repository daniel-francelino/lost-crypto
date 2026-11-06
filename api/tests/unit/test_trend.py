"""Trend utility: bullish / bearish / sideways per timeframe (1h, 4h, 1d, 1w)."""

import json
import math
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from factories import make_candles
from modules.market_data.domain.models import Candle, Timeframe
from modules.market_data.domain.trend import (
    DEFAULT_SETTINGS,
    Trend,
    TrendFrame,
    TrendSettings,
    TrendTracker,
    analyze_trend,
    classify_trend,
)


def _wavy(count: int, start: float, drift: float, amplitude: float = 8.0) -> list[str]:
    return [
        f"{start + drift * i + amplitude * math.sin(2 * math.pi * i / 10):.2f}"
        for i in range(count)
    ]


def _feed(tracker: TrendTracker, candles: list[Candle]):  # type: ignore[no-untyped-def]
    state = tracker.initial_state()
    for candle in candles:
        state = tracker.update(state, candle)
    return state


# --- the rule ----------------------------------------------------------------------------------


def _rule(close: str, ema: str, slope: str, atr: str = "10", band: str = "0.5") -> Trend:
    return classify_trend(
        close=Decimal(close),
        ema=Decimal(ema),
        slope=Decimal(slope),
        atr=Decimal(atr),
        flat_band=Decimal(band),
    )


@pytest.mark.parametrize(
    ("close", "ema", "slope", "expected"),
    [
        ("105", "100", "8", Trend.BULLISH),  # above a rising EMA (8 > 0.5 * 10)
        ("95", "100", "-8", Trend.BEARISH),
        ("105", "100", "3", Trend.SIDEWAYS),  # EMA barely moving: not a trend
        ("95", "100", "-3", Trend.SIDEWAYS),
        ("95", "100", "8", Trend.SIDEWAYS),  # below a rising EMA: the two disagree
        ("105", "100", "-8", Trend.SIDEWAYS),
        ("100", "100", "8", Trend.SIDEWAYS),  # on the line
        ("105", "100", "5", Trend.SIDEWAYS),  # exactly on the band is still inside it
    ],
)
def test_the_rule_needs_price_and_ema_slope_to_agree(
    close: str, ema: str, slope: str, expected: Trend
) -> None:
    assert _rule(close, ema, slope) is expected


def test_the_band_is_measured_in_atrs_so_it_scales_with_volatility() -> None:
    assert _rule("105", "100", "8", atr="10") is Trend.BULLISH
    assert _rule("105", "100", "8", atr="30") is Trend.SIDEWAYS  # same move, a wilder market
    assert _rule("105", "100", "1", atr="0") is Trend.SIDEWAYS  # no range at all


def test_timeframes_accept_plain_words() -> None:
    assert TrendFrame.parse("week") is TrendFrame.W1
    assert TrendFrame.parse("dia") is TrendFrame.D1
    assert TrendFrame.parse(" 4H ") is TrendFrame.H4
    assert TrendFrame.parse("1h") is TrendFrame.H1
    with pytest.raises(ValueError):
        TrendFrame.parse("month")


def test_settings_are_validated() -> None:
    with pytest.raises(ValueError):
        TrendSettings(ema_period=1)
    with pytest.raises(ValueError):
        TrendSettings(flat_band=Decimal(-1))


# --- building higher-timeframe bars ---------------------------------------------------------


def test_bars_close_on_their_last_base_candle() -> None:
    tracker = TrendTracker(Timeframe.H1)
    state = tracker.initial_state()
    counts = []
    for candle in make_candles(["100"] * 49):  # 2024-01-01 00:00 UTC onwards
        state = tracker.update(state, candle)
        counts.append(
            (
                state.frames[TrendFrame.H4].bars,
                state.frames[TrendFrame.D1].bars,
                state.frames[TrendFrame.H1].bars,
            )
        )
    assert counts[22] == (5, 0, 23)  # 23:00 not yet in: the day is open
    assert counts[23] == (6, 1, 24)  # the day's last hour closes it
    assert counts[47] == (12, 2, 48)
    assert counts[48] == (12, 2, 49)  # first hour of day 3 closes nothing higher


def test_weeks_start_on_monday_utc() -> None:
    tracker = TrendTracker(Timeframe.H1)
    monday = datetime(2024, 1, 1, tzinfo=UTC)  # a Monday
    state = _feed(tracker, make_candles(["100"] * (7 * 24), start=monday))
    assert state.frames[TrendFrame.W1].bars == 1
    # The same number of candles starting on a Wednesday straddle two weeks: neither is complete.
    wednesday = datetime(2024, 1, 3, tzinfo=UTC)
    state = _feed(tracker, make_candles(["100"] * (7 * 24), start=wednesday))
    assert state.frames[TrendFrame.W1].bars == 0
    assert state.frames[TrendFrame.D1].bars == 7  # the days are still whole


def test_a_history_that_starts_mid_bar_never_counts_that_bar() -> None:
    tracker = TrendTracker(Timeframe.H1)
    start = datetime(2024, 1, 1, 5, tzinfo=UTC)  # 05:00: inside the first day and 4h bar
    state = _feed(tracker, make_candles(["100"] * 43, start=start))  # until 23:00 of day 2
    assert state.frames[TrendFrame.D1].bars == 1
    assert state.frames[TrendFrame.H4].bars == (43 - 3) // 4


def test_a_missing_candle_drops_the_bar_it_belongs_to() -> None:
    candles = make_candles(["100"] * 48)
    del candles[10]
    state = _feed(TrendTracker(Timeframe.H1), candles)
    assert state.frames[TrendFrame.D1].bars == 1


def test_weekly_bars_can_be_built_from_daily_candles() -> None:
    tracker = TrendTracker(Timeframe.D1, {TrendFrame.W1: TrendSettings(ema_period=2, atr_period=2)})
    state = _feed(tracker, make_candles(["100"] * 14, timeframe=Timeframe.D1))
    assert state.frames[TrendFrame.W1].bars == 2


def test_a_frame_shorter_than_the_base_is_refused() -> None:
    with pytest.raises(ValueError):
        TrendTracker(Timeframe.H4, {TrendFrame.H1: TrendSettings()})
    with pytest.raises(ValueError):
        TrendTracker(Timeframe.H1, {})
    tracker = TrendTracker(Timeframe.H1)
    with pytest.raises(ValueError):
        tracker.update(tracker.initial_state(), make_candles(["100"], timeframe=Timeframe.H4)[0])


def test_it_says_how_much_history_it_needs() -> None:
    assert TrendTracker(Timeframe.H1, {TrendFrame.D1: TrendSettings()}).required_base_candles() == (
        (23 + 2) * 24
    )
    assert TrendTracker(Timeframe.H1).required_base_candles() == (14 + 2) * 168  # the weekly frame


# --- readings ------------------------------------------------------------------------------


def test_a_frame_is_unknown_until_it_has_enough_completed_bars() -> None:
    tracker = TrendTracker(Timeframe.H1)
    state = _feed(tracker, make_candles(_wavy(24 * 10, 1000, 0.5)))
    daily = tracker.read(state, TrendFrame.D1)
    assert daily.trend is None
    assert not daily.ready
    assert daily.bars == 10
    assert tracker.read(state, TrendFrame.H1).ready  # 240 hourly bars are plenty


HIGHER_FRAMES = (TrendFrame.H4, TrendFrame.D1, TrendFrame.W1)  # 1h depends on the wiggle's phase


def test_an_uptrend_is_bullish_on_the_higher_timeframes() -> None:
    readings = analyze_trend(make_candles(_wavy(24 * 130, 1000, 0.5)))
    assert [readings[f].trend for f in HIGHER_FRAMES] == [Trend.BULLISH] * 3
    daily = readings[TrendFrame.D1]
    assert daily.ready and daily.slope_atr is not None and daily.slope_atr > Decimal("0.25")
    assert daily.close is not None and daily.ema is not None and daily.close > daily.ema


def test_a_downtrend_is_bearish_on_the_higher_timeframes() -> None:
    readings = analyze_trend(make_candles(_wavy(24 * 130, 3000, -0.5)))
    assert [readings[f].trend for f in HIGHER_FRAMES] == [Trend.BEARISH] * 3


def test_a_market_that_goes_nowhere_is_sideways() -> None:
    flat = [f"{1000 + 6 * math.sin(2 * math.pi * i / 7):.2f}" for i in range(24 * 130)]
    readings = analyze_trend(make_candles(flat))
    assert all(r.trend is Trend.SIDEWAYS for r in readings.values())


def test_timeframes_can_disagree() -> None:
    """A month-long rise followed by a few days of decline: the day and the hour part ways."""
    rising = _wavy(24 * 100, 1000, 0.5)
    falling = _wavy(24 * 6, float(rising[-1]), -2.5)
    readings = analyze_trend(make_candles(rising + falling))
    assert readings[TrendFrame.H1].trend is Trend.BEARISH
    assert readings[TrendFrame.W1].trend is Trend.BULLISH  # the week has not noticed yet


def test_unreachable_frames_are_left_out_of_a_one_shot_analysis() -> None:
    readings = analyze_trend(make_candles(["100"] * 30, timeframe=Timeframe.D1))
    assert set(readings) == {TrendFrame.D1, TrendFrame.W1}


def test_defaults_cover_the_four_requested_timeframes() -> None:
    assert set(DEFAULT_SETTINGS) == {TrendFrame.H1, TrendFrame.H4, TrendFrame.D1, TrendFrame.W1}


# --- purity and persistence -----------------------------------------------------------------


def test_a_reading_never_depends_on_later_candles() -> None:
    candles = make_candles(_wavy(24 * 130, 1000, 0.5))
    tracker = TrendTracker(Timeframe.H1)
    cut = 24 * 100
    partial = tracker.read_all(_feed(tracker, candles[:cut]))
    again = tracker.read_all(_feed(tracker, candles[:cut]))
    assert partial == again
    state = tracker.initial_state()
    for candle in candles[:cut]:
        state = tracker.update(state, candle)
    snapshot = tracker.serialize(state)
    tracker.update(state, candles[cut])
    assert tracker.serialize(state) == snapshot  # update returned a new state, state is intact


def test_state_survives_a_json_round_trip_and_continues_identically() -> None:
    candles = make_candles(_wavy(24 * 130, 1000, 0.5))
    tracker = TrendTracker(Timeframe.H1)
    straight = _feed(tracker, candles)

    half = _feed(tracker, candles[: 24 * 61 + 7])  # stopped in the middle of a day and a week
    saved = json.loads(json.dumps(tracker.serialize(half)))
    state = TrendTracker(Timeframe.H1).deserialize(saved)
    for candle in candles[24 * 61 + 7 :]:
        state = tracker.update(state, candle)

    assert tracker.read_all(state) == tracker.read_all(straight)
    assert tracker.serialize(state) == tracker.serialize(straight)
