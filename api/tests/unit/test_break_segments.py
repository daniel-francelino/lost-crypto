"""Book 2 ch. 5, O1: metrics between the operator's named breaks."""

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

from factories import MARKET, T0, make_candles, make_config
from modules.analytics.domain.metrics import compute_metrics
from modules.backtesting.domain.break_segments import (
    MIN_STRETCH_CANDLES,
    BreakRef,
    compute_break_segments,
)
from modules.backtesting.domain.engine import run_backtest
from modules.strategies.domain.ema_crossover import EmaCrossoverParams, EmaCrossoverStrategy

HOUR = timedelta(hours=1)
CLOSES = [100 + (i % 7) * 3 - (i // 25) * 2 + (10 if i % 31 < 5 else 0) for i in range(120)]


def _run():
    candles = make_candles(CLOSES)
    config = replace(make_config(fee_rate="0.001", n_candles=len(CLOSES)))
    outcome = run_backtest(config, candles, MARKET, EmaCrossoverStrategy(EmaCrossoverParams(3, 8)))
    return config, candles, outcome


def _break(name: str, hours: int, registered: int = 0) -> BreakRef:
    return BreakRef(name, name, T0 + hours * HOUR, T0 + registered * HOUR)


def test_no_break_inside_the_run_gives_nothing():
    config, candles, outcome = _run()
    assert compute_break_segments(config, candles, outcome, []) is None
    outside = [_break("before", -5), _break("after", 500), _break("on-first", 0)]
    assert compute_break_segments(config, candles, outcome, outside) is None


def test_one_break_makes_two_stretches_with_the_direct_metrics_of_each():
    config, candles, outcome = _run()
    block = compute_break_segments(config, candles, outcome, [_break("crash", 60)])
    assert block is not None
    left, right = block["segments"]
    assert (left["candles"], right["candles"]) == (60, 60)
    direct_left = compute_metrics(
        initial_capital=config.initial_capital,
        equity_curve=outcome.equity_curve[:60],
        fills=[f for f in outcome.fills if f.time < candles[60].open_time],
        first_price=candles[0].open,
        last_price=candles[59].close,
        open_position=outcome.in_market[59],
        rejected_signals=0,
        bar=config.timeframe.delta,
        benchmark_prices=[c.close for c in candles[:60]],
        in_market=outcome.in_market[:60],
    )
    assert left["metrics"] == direct_left.to_dict()
    assert Decimal(right["metrics"]["initial_capital"]) == outcome.equity_curve[59].equity


def test_two_breaks_make_three_stretches_that_cover_the_run_without_overlap():
    config, candles, outcome = _run()
    block = compute_break_segments(
        config,
        candles,
        outcome,
        [_break("b", 80), _break("a", 30)],  # out of order on purpose
    )
    assert block is not None
    stretches = block["segments"]
    assert [s["candles"] for s in stretches] == [30, 50, 40]
    assert sum(s["candles"] for s in stretches) == len(candles)
    assert [b["name"] for b in block["breaks"]] == ["a", "b"]
    labels = [s["label"] for s in stretches]
    assert labels == ["antes de a", "entre a e b", "depois de b"]


def test_a_stretch_too_short_to_measure_is_left_out():
    config, candles, outcome = _run()
    block = compute_break_segments(config, candles, outcome, [_break("late", 119)])
    assert block is not None
    assert all(s["candles"] >= MIN_STRETCH_CANDLES for s in block["segments"])
    assert [s["candles"] for s in block["segments"]] == [119]


def test_the_snapshot_keeps_when_each_break_was_registered():
    config, candles, outcome = _run()
    block = compute_break_segments(config, candles, outcome, [_break("crash", 60, registered=500)])
    assert block is not None
    [snapshot] = block["breaks"]
    assert snapshot["created_at"] > snapshot["occurred_at"]  # registered after the event
    assert snapshot["id"] == "crash"


def test_a_break_exactly_at_a_candle_open_starts_that_candles_stretch():
    config, candles, outcome = _run()
    block = compute_break_segments(config, candles, outcome, [_break("on-candle", 40)])
    assert block is not None
    assert [s["candles"] for s in block["segments"]] == [40, 80]
    assert block["segments"][1]["start"] == candles[40].open_time.isoformat()


def test_a_run_too_short_for_two_stretches_is_skipped():
    candles = make_candles([100, 101, 102])
    config = make_config(n_candles=3)
    outcome = run_backtest(config, candles, MARKET, EmaCrossoverStrategy(EmaCrossoverParams(2, 3)))
    assert compute_break_segments(config, candles, outcome, [_break("x", 1)]) is None
