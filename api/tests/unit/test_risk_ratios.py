"""Risk ratios and drawdown statistics (book 1 ch. 2, O1/O2)."""

import math
import statistics
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from modules.analytics.domain import risk_ratios
from modules.analytics.domain.metrics import compute_metrics, drawdown_stats
from modules.analytics.presentation.schemas import MetricsOut
from modules.backtesting.domain.models import EquityPoint

T0 = datetime(2024, 1, 1, tzinfo=UTC)
HOUR = timedelta(hours=1)
DAY = timedelta(days=1)


def _curve(values: list[float | int | str], step: timedelta = HOUR) -> list[EquityPoint]:
    return [EquityPoint(T0 + step * i, Decimal(str(v))) for i, v in enumerate(values)]


def _returns(pattern: list[str], repeat: int) -> list[Decimal]:
    return [Decimal(r) for r in pattern] * repeat


def test_annualization_uses_365_days() -> None:
    assert risk_ratios.annualization_factor(HOUR) == Decimal(8760)
    assert risk_ratios.annualization_factor(DAY) == Decimal(365)
    assert risk_ratios.annualization_factor(timedelta(minutes=5)) == Decimal(105120)


def test_sharpe_matches_an_independent_float_calculation() -> None:
    returns = _returns(["0.01", "-0.004", "0.002", "0.006", "-0.01"], 8)
    floats = [float(r) for r in returns]
    expected = math.sqrt(365) * statistics.mean(floats) / statistics.stdev(floats)
    got = risk_ratios.sharpe(returns, Decimal(365))
    assert got is not None
    assert abs(float(got) - expected) < 1e-9


def test_sharpe_is_scale_invariant() -> None:
    returns = _returns(["0.01", "-0.004", "0.002", "0.006", "-0.01"], 8)
    scaled = [r * 3 for r in returns]
    a = risk_ratios.sharpe(returns, Decimal(365))
    b = risk_ratios.sharpe(scaled, Decimal(365))
    assert a is not None and b is not None
    assert abs(a - b) < Decimal("1e-20")


def test_ratios_are_none_on_zero_variance_or_short_samples() -> None:
    flat = [Decimal("0.001")] * 40
    assert risk_ratios.sharpe(flat, Decimal(365)) is None
    assert risk_ratios.sortino(flat, Decimal(365)) is None  # no downside at all
    short = _returns(["0.01", "-0.01"], 10)
    assert risk_ratios.sharpe(short, Decimal(365)) is None
    assert risk_ratios.annualized_volatility_pct(short, Decimal(365)) is None


def test_sortino_uses_downside_deviation_over_all_periods() -> None:
    returns = _returns(["0.02", "-0.01", "0.01", "0.0"], 10)
    floats = [float(r) for r in returns]
    downside = math.sqrt(sum(min(r, 0.0) ** 2 for r in floats) / len(floats))
    expected = math.sqrt(365) * statistics.mean(floats) / downside
    got = risk_ratios.sortino(returns, Decimal(365))
    assert got is not None
    assert abs(float(got) - expected) < 1e-9


def test_information_ratio_is_zero_when_tracking_the_benchmark_exactly() -> None:
    returns = _returns(["0.01", "-0.004", "0.002"], 12)
    assert risk_ratios.information_ratio(returns, returns, Decimal(365)) is None  # no variance
    shifted = [r - Decimal("0.001") for r in returns]
    ir = risk_ratios.information_ratio(returns, shifted, Decimal(365))
    assert ir is None  # constant excess: zero variance, never infinity


def test_gaps_are_skipped_and_counted() -> None:
    times = [T0, T0 + HOUR, T0 + 2 * HOUR, T0 + 10 * HOUR, T0 + 11 * HOUR]
    values = [Decimal(100), Decimal(101), Decimal(102), Decimal(90), Decimal(91)]
    series = risk_ratios.periodic_returns(times, values, HOUR, values)
    assert series.gaps == 1
    assert len(series.returns) == 3  # the 102 -> 90 step across the hole is not a return
    assert series.benchmark == series.returns


def test_annualized_return_needs_a_month() -> None:
    assert risk_ratios.annualized_return_pct(Decimal(100), Decimal(110), DAY * 10) is None
    got = risk_ratios.annualized_return_pct(Decimal(100), Decimal(110), DAY * 365)
    assert got is not None and abs(got - Decimal(10)) < Decimal("1e-20")


def test_drawdown_without_any_drop() -> None:
    stats = drawdown_stats(_curve([100, 101, 102, 103]))
    assert stats.max_drawdown_pct == 0
    assert stats.max_duration_seconds == 0
    assert stats.open is False
    assert stats.peak_at is None


def test_recovered_drawdown_duration_runs_from_peak_to_recovery() -> None:
    stats = drawdown_stats(_curve([100, 110, 99, 105, 110, 111]))
    assert stats.max_drawdown_pct == Decimal(10)
    assert stats.max_duration_bars == 2  # 110 at t1, still below at t3, back at 110 at t4
    assert stats.max_duration_seconds == 2 * 3600
    assert stats.peak_at == T0 + HOUR
    assert stats.trough_at == T0 + 2 * HOUR
    assert stats.open is False
    assert stats.current_drawdown_pct == 0


def test_deepest_and_longest_drawdowns_are_reported_separately() -> None:
    # A sharp 20% drop that recovers in one bar, then a shallow 5% one lasting four bars.
    stats = drawdown_stats(_curve([100, 80, 100, 95, 96, 97, 98, 99, 101]))
    assert stats.max_drawdown_pct == Decimal(20)
    assert stats.trough_at == T0 + HOUR
    assert stats.max_duration_bars == 5  # peak at t2, still below at t7


def test_never_recovered_drawdown_is_open() -> None:
    stats = drawdown_stats(_curve([100, 120, 90, 95, 100]))
    assert stats.open is True
    assert stats.max_duration_bars == 3  # counts until the last point
    assert stats.max_drawdown_pct == Decimal(25)
    assert stats.current_drawdown_pct.quantize(Decimal("0.0001")) == Decimal("16.6667")


def _metrics(curve: list[EquityPoint], **extra: object) -> MetricsOut:
    metrics = compute_metrics(
        initial_capital=curve[0].equity,
        equity_curve=curve,
        fills=[],
        first_price=Decimal(1),
        last_price=Decimal(1),
        open_position=False,
        rejected_signals=0,
        **extra,  # type: ignore[arg-type]
    )
    return MetricsOut.model_validate(metrics.to_dict())


def test_compute_metrics_fills_ratios_only_when_the_bar_is_known() -> None:
    values = [100 + (i % 5) - (i % 3) + i * 0.1 for i in range(60)]
    curve = _curve(values, DAY)
    without = _metrics(curve)
    assert without.sharpe_ratio is None
    assert without.max_drawdown_duration_bars is not None  # drawdown needs no bar

    prices = [Decimal(100 + i) for i in range(60)]
    with_bar = _metrics(curve, bar=DAY, benchmark_prices=prices, in_market=[True, False] * 30)
    assert with_bar.sharpe_ratio is not None
    assert with_bar.information_ratio is not None
    assert with_bar.return_periods == 59
    assert with_bar.return_gaps == 0
    assert with_bar.annualization_factor == Decimal("365.0000")
    assert with_bar.exposure_pct == Decimal("50.0000")
    assert with_bar.annualized_return_pct is not None


def test_results_stored_before_the_new_metrics_still_validate() -> None:
    old = {
        "initial_capital": "1000",
        "final_equity": "1100",
        "net_pnl": "100",
        "total_return_pct": "10",
        "buy_and_hold_return_pct": "5",
        "max_drawdown_pct": "3",
        "fees_paid": "1",
        "fills": 2,
        "round_trips": 1,
        "win_rate_pct": "100",
        "profit_factor": None,
        "avg_trade_pnl": "100",
        "open_position": False,
        "rejected_signals": 0,
    }
    out = MetricsOut.model_validate(old)
    assert out.sharpe_ratio is None
    assert out.drawdown_open is None
