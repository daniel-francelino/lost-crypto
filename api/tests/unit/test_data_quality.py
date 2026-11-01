"""Candle integrity, gaps in a range, sample size and sweep robustness (book 1 ch. 3)."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from factories import T0, make_candles
from modules.backtesting.domain.data_quality import (
    candle_report,
    free_parameters,
    gap_problem,
    gaps_summary,
    sample_check,
)
from modules.backtesting.domain.robustness import Verdict, assess
from modules.market_data.domain.models import Timeframe, ceil_to_timeframe, range_coverage
from modules.market_data.domain.quality import (
    CandleProblem,
    candle_problems,
    find_outliers,
    returns_by_time,
)
from modules.strategies.domain.ema_crossover import EmaCrossoverStrategy

H = timedelta(hours=1)


def test_valid_candles_have_no_problems() -> None:
    assert all(candle_problems(c) == [] for c in make_candles([10, 11, 12, 11]))


def test_each_problem_is_detected() -> None:
    good = make_candles([10, 11])[1]
    cases = {
        CandleProblem.HIGH_BELOW_BODY: replace(good, high=Decimal("10.5")),
        CandleProblem.LOW_ABOVE_BODY: replace(good, low=Decimal("10.5")),
        CandleProblem.NON_POSITIVE_PRICE: replace(good, low=Decimal(0)),
        CandleProblem.NEGATIVE_VOLUME: replace(good, volume=Decimal(-1)),
        CandleProblem.MISALIGNED_TIME: replace(
            good, open_time=good.open_time + timedelta(minutes=7)
        ),
    }
    for problem, candle in cases.items():
        assert problem in candle_problems(candle), problem


def _wavy(n: int) -> list[str]:
    return [str(100 + (i % 5) - (i % 3)) for i in range(n)]


def test_outliers_flag_a_jump_and_nothing_on_a_calm_series() -> None:
    closes = _wavy(200)
    assert find_outliers(make_candles(closes)) == []
    closes[120] = "160"  # a bad tick: up 60% and straight back
    found = find_outliers(make_candles(closes))
    assert [o.open_time for o in found] == [T0 + 120 * H, T0 + 121 * H]
    assert all(o.sigmas > 4 for o in found)


def test_outliers_carry_the_reference_move() -> None:
    closes = _wavy(200)
    closes[120] = "160"
    candles = make_candles(closes)
    found = find_outliers(candles, reference=returns_by_time(candles))
    assert found[0].reference_return_pct == found[0].return_pct  # "the market" moved too


def test_outliers_skip_returns_across_a_gap() -> None:
    candles = make_candles(_wavy(200))
    jumped = [
        *candles[:100],
        *[
            replace(c, close=c.close * 2, open=c.open * 2, high=c.high * 2, low=c.low * 2)
            for c in candles[110:]
        ],
    ]
    assert all(o.open_time != candles[110].open_time for o in find_outliers(jumped))


def test_range_coverage_counts_edges_and_ignores_the_unfinished_candle() -> None:
    times = [T0 + i * H for i in range(10) if i not in (0, 4, 5)]
    now = T0 + 12 * H + timedelta(minutes=30)
    cov = range_coverage(times, Timeframe.H1, T0, T0 + 20 * H, now)
    assert cov.expected == 12  # candles 0..11 closed; 12 is still open; 13+ are in the future
    assert cov.present == 7
    assert [(g.start, g.missing) for g in cov.gaps] == [
        (T0, 1),
        (T0 + 4 * H, 2),
        (T0 + 10 * H, 2),
    ]
    assert cov.largest_gap == 2
    assert ceil_to_timeframe(T0 + timedelta(minutes=1), Timeframe.H1) == T0 + H


def test_gap_limits() -> None:
    full = range_coverage(
        [T0 + i * H for i in range(200)], Timeframe.H1, T0, T0 + 200 * H, T0 + 300 * H
    )
    assert gap_problem(full, Timeframe.H1) is None
    one = [T0 + i * H for i in range(200) if i != 50]
    small = range_coverage(one, Timeframe.H1, T0, T0 + 200 * H, T0 + 300 * H)
    assert gap_problem(small, Timeframe.H1) is None  # 0.5% missing, 1 h hole
    many = [T0 + i * H for i in range(200) if not 50 <= i < 54]
    over = range_coverage(many, Timeframe.H1, T0, T0 + 200 * H, T0 + 300 * H)
    assert "missing" in (gap_problem(over, Timeframe.H1) or "")
    day = datetime(2024, 1, 1, tzinfo=UTC)
    daily = [day + i * timedelta(days=1) for i in range(400) if i != 100]
    long_hole = range_coverage(
        daily, Timeframe.D1, day, day + timedelta(days=400), day + timedelta(days=500)
    )
    assert gap_problem(long_hole, Timeframe.D1) is None  # one missing day is not > 24 h
    summary = gaps_summary(over, Timeframe.H1, allowed=True)
    assert (summary["missing"], summary["over_limit"], summary["allowed"]) == (4, True, True)
    assert summary["largest_gap_seconds"] == 4 * 3600


def test_candle_report_counts_bad_candles() -> None:
    candles = make_candles(_wavy(100))
    candles[10] = replace(candles[10], high=candles[10].low - 1)
    report = candle_report(candles)
    assert report["invalid_candles"] == 1
    assert report["invalid_samples"][0]["problems"]


def test_free_parameters_ignore_optional_ones_left_empty() -> None:
    specs = EmaCrossoverStrategy.PARAMETERS
    assert free_parameters(specs, {}) == 2
    assert free_parameters(specs, {"stop_loss_pct": 3}) == 3
    check = sample_check(2, 400, 12)
    assert (check["min_bars"], check["meets_bar_rule"], check["meets_trade_rule"]) == (
        504,
        False,
        False,
    )


def _grid_scores(surface: dict[tuple[int, int], str]) -> list[tuple[dict[str, int], Decimal]]:
    rows = [({"fast": a, "slow": b}, Decimal(v)) for (a, b), v in surface.items()]
    return sorted(rows, key=lambda row: row[1], reverse=True)


GRID = {"fast": [5, 9, 12], "slow": [21, 34, 50]}


def test_isolated_peak_and_plateau() -> None:
    peak = {(a, b): "2" for a in GRID["fast"] for b in GRID["slow"]}
    peak[(9, 34)] = "40"
    result = assess(GRID, _grid_scores(peak))
    assert result.verdict is Verdict.PEAK
    assert result.neighbours == 4
    smooth = {
        (a, b): str(30 - abs(a - 9) - abs(b - 34) / 5) for a in GRID["fast"] for b in GRID["slow"]
    }
    assert assess(GRID, _grid_scores(smooth)).verdict is Verdict.PLATEAU


def test_unprofitable_and_too_small_grids() -> None:
    losing = {(a, b): "-1" for a in GRID["fast"] for b in GRID["slow"]}
    assert assess(GRID, _grid_scores(losing)).verdict is Verdict.UNPROFITABLE
    tiny = {"fast": [5, 9], "slow": [21]}
    rows = [({"fast": 9, "slow": 21}, Decimal(10)), ({"fast": 5, "slow": 21}, Decimal(9))]
    assert assess(tiny, rows).verdict is Verdict.INSUFFICIENT
    assert assess(GRID, []).verdict is Verdict.INSUFFICIENT
