"""What a backtest result rests on (book 1 ch. 3): data gaps, bad candles, outliers, sample size.

Everything here is reported with the run, never silently "fixed": dropping candles changes the
timeline, and real crashes look like outliers. Gaps above the limits refuse the run unless the
operator asks for it explicitly (``allow_gaps``).
"""

from collections.abc import Mapping, Sequence
from datetime import timedelta
from decimal import Decimal
from typing import Any

from modules.market_data.domain.models import Candle, FundingRate, RangeCoverage, Timeframe
from modules.market_data.domain.quality import (
    DEFAULT_OUTLIER_SIGMAS,
    candle_problems,
    find_outliers,
)
from modules.strategies.domain.base import ParamSpec

MAX_MISSING_SHARE = Decimal("0.01")  # more than 1% of the expected candles missing
MAX_GAP = timedelta(hours=24)  # or a single hole longer than a day
MAX_LISTED = 20
BARS_PER_PARAMETER = 252  # Chan's rule of thumb (p. 53), stated as experience, not theory
MIN_ROUND_TRIPS = 30  # our adaptation: trades, not bars, are the independent observations


def funding_coverage_report(
    mark_candles: Sequence[Candle], funding_rates: Sequence[FundingRate]
) -> dict[str, Any]:
    """Report observed funding coverage without claiming an unrecorded historical schedule.

    Binance can adjust funding intervals; historical rate rows do not identify the interval
    schedule effective between events. The engine rejects observed gaps over eight hours, while
    this report makes the remaining completeness limit visible to API consumers.
    """
    ordered = sorted(funding_rates, key=lambda rate: (rate.funding_time, rate.rate_type))
    event_times = sorted({rate.funding_time for rate in ordered})
    if not mark_candles:
        return {
            "status": "not_certified",
            "reason": "mark-price candles are unavailable",
            "event_count": len(ordered),
            "max_observed_gap_seconds": None,
        }
    start = mark_candles[0].open_time
    end = mark_candles[-1].close_time
    gaps = [event_times[0] - start] if event_times else [end - start]
    gaps.extend(event_times[index] - event_times[index - 1] for index in range(1, len(event_times)))
    if event_times:
        gaps.append(end - event_times[-1])
    max_gap = max(gaps, default=timedelta(0))
    return {
        "status": "not_certified",
        "reason": "historical funding interval schedule is not stored with rate observations",
        "event_count": len(ordered),
        "max_observed_gap_seconds": int(max_gap.total_seconds()),
        "maximum_gap_guard_hours": 8,
    }


def gap_problem(coverage: RangeCoverage, timeframe: Timeframe) -> str | None:
    """Why the gaps are too large to run silently, or None."""
    if coverage.expected == 0:
        return None
    share = Decimal(coverage.missing) / coverage.expected
    largest = coverage.largest_gap * timeframe.delta
    if share > MAX_MISSING_SHARE:
        return (
            f"{coverage.missing} of {coverage.expected} candles are missing in the range "
            f"({share * 100:.1f}%, limit {MAX_MISSING_SHARE * 100}%)"
        )
    if largest > MAX_GAP:
        return f"the largest gap is {largest} long (limit {MAX_GAP})"
    return None


def gaps_summary(coverage: RangeCoverage, timeframe: Timeframe, allowed: bool) -> dict[str, Any]:
    return {
        "expected": coverage.expected,
        "present": coverage.present,
        "missing": coverage.missing,
        "gap_count": len(coverage.gaps),
        "largest_gap_candles": coverage.largest_gap,
        "largest_gap_seconds": int((coverage.largest_gap * timeframe.delta).total_seconds()),
        "over_limit": gap_problem(coverage, timeframe) is not None,
        "allowed": allowed,
        "gaps": [
            {"start": g.start.isoformat(), "end": g.end.isoformat(), "missing": g.missing}
            for g in coverage.gaps[:MAX_LISTED]
        ],
    }


def candle_report(candles: Sequence[Candle], k: Decimal = DEFAULT_OUTLIER_SIGMAS) -> dict[str, Any]:
    invalid = [c for c in candles if candle_problems(c)]
    outliers = find_outliers(candles, k)
    return {
        "invalid_candles": len(invalid),
        "invalid_samples": [
            {
                "open_time": c.open_time.isoformat(),
                "problems": [p.value for p in candle_problems(c)],
            }
            for c in invalid[:MAX_LISTED]
        ],
        "outlier_sigmas": str(k),
        "outliers": len(outliers),
        "outlier_samples": [
            {
                "open_time": o.open_time.isoformat(),
                "return_pct": str(o.return_pct),
                "sigmas": str(o.sigmas),
            }
            for o in outliers[:MAX_LISTED]
        ],
    }


def free_parameters(specs: Sequence[ParamSpec], params: Mapping[str, Any]) -> int:
    """Parameters that actually shape the result: optional ones left empty do not count."""
    return sum(1 for spec in specs if params.get(spec.name, spec.default) is not None)


def sample_check(free: int, bars: int, round_trips: int) -> dict[str, Any]:
    min_bars = BARS_PER_PARAMETER * free
    return {
        "free_parameters": free,
        "bars": bars,
        "round_trips": round_trips,
        "min_bars": min_bars,
        "min_round_trips": MIN_ROUND_TRIPS,
        "meets_bar_rule": bars >= min_bars,
        "meets_trade_rule": round_trips >= MIN_ROUND_TRIPS,
    }
