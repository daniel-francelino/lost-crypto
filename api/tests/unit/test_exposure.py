"""Book 2 ch. 8, O1: growth and drawdown as a function of exposure."""

import random
from decimal import Decimal

import pytest

from modules.analytics.domain.exposure import (
    MAX_BOOTSTRAP_RETURNS,
    MAX_SIMULATIONS,
    MIN_RETURNS,
    bootstrap_drawdown,
    exposure_curve,
    fractions,
    growth_rate,
    max_drawdown_pct,
    ruin_fraction,
)
from modules.analytics.domain.sizing import growth_rate as gaussian_growth
from modules.analytics.domain.sizing import kelly_fraction

D = Decimal


def _returns(seed: int, n: int, mean: str, sd: str) -> list[Decimal]:
    rng = random.Random(seed)
    return [D(str(round(rng.gauss(float(mean), float(sd)), 6))) for _ in range(n)]


def test_fractions_are_evenly_spaced_and_end_at_one():
    assert fractions(4) == [D("0.25"), D("0.5"), D("0.75"), D(1)]
    with pytest.raises(ValueError):
        fractions(0)
    with pytest.raises(ValueError):
        fractions(1000)


def test_growth_is_the_mean_of_log_one_plus_f_r_by_hand():
    returns = [D("0.10"), D("-0.05")]
    expected = (D("1.05").ln() + D("0.975").ln()) / 2  # f = 0.5
    assert abs(growth_rate(returns, D("0.5")) - expected) < D("1e-20")  # type: ignore[operator]


def test_a_bar_that_wipes_the_account_out_has_no_growth_and_a_full_drawdown():
    assert growth_rate([D("0.1"), D("-0.6")], D(2)) is None  # 1 + 2 * -0.6 < 0
    assert max_drawdown_pct([D("0.1"), D("-0.6")], D(2)) == D(100)


def test_ruin_fraction_is_the_inverse_of_the_worst_return():
    assert ruin_fraction([D("0.1"), D("-0.25"), D("0.3")]) == D(4)
    assert ruin_fraction([D("0.1"), D("0.2")]) is None


def test_drawdown_is_zero_without_losses_and_grows_with_exposure():
    assert max_drawdown_pct([D("0.01")] * 40, D(1)) == 0
    returns = _returns(1, 400, "0.002", "0.02")
    drawdowns = [max_drawdown_pct(returns, f) for f in fractions(5)]
    assert drawdowns == sorted(drawdowns) and drawdowns[-1] > drawdowns[0]


def test_the_growth_peak_sits_at_the_analytic_optimum_of_a_two_point_return():
    # r = m + s and m - s in turn: mean m, variance s^2, so Kelly ~ m / s^2 = 5 and, exactly for
    # this two-point law, the optimum is m / (s^2 - m^2).
    m, s = D("0.002"), D("0.02")
    returns = [m + s, m - s] * 50
    exact = m / (s * s - m * m)
    grid = [D(i) / 4 for i in range(2, 33)]  # 0.5 .. 8
    best = max(grid, key=lambda f: growth_rate(returns, f) or D("-1e9"))
    assert abs(best - exact) <= D("0.25")
    mean = sum(returns, D(0)) / len(returns)
    variance = sum(((r - mean) ** 2 for r in returns), D(0)) / (len(returns) - 1)
    kelly = kelly_fraction(mean, variance)
    assert kelly is not None and abs(kelly - D(5)) < D("0.1")
    # growth falls on both sides of the peak, and the Gaussian formula agrees near f = 1
    assert growth_rate(returns, best) > growth_rate(returns, D("0.5"))  # type: ignore[operator]
    assert growth_rate(returns, D(8)) < growth_rate(returns, best)  # type: ignore[operator]
    assert abs((growth_rate(returns, D(1)) or D(0)) - gaussian_growth(D(1), mean, variance)) < D(
        "0.00001"
    )


def test_a_short_sample_is_refused_and_steps_are_validated():
    with pytest.raises(ValueError):
        exposure_curve([D("0.01")] * (MIN_RETURNS - 1), 5)
    with pytest.raises(ValueError):
        exposure_curve([D("0.01")] * 60, 0)


def test_the_curve_has_one_point_per_step_and_no_bootstrap_by_default():
    points = exposure_curve(_returns(3, 200, "0.001", "0.01"), 4)
    assert [p.fraction for p in points] == fractions(4)
    assert all(p.bootstrap_p50 is None and p.bootstrap_p95 is None for p in points)


def test_the_bootstrap_is_deterministic_with_the_same_seed_and_the_median_not_above_p95():
    returns = _returns(4, 300, "0.001", "0.02")
    first = bootstrap_drawdown(returns, D("0.5"), 50, seed=9)
    again = bootstrap_drawdown(returns, D("0.5"), 50, seed=9)
    other = bootstrap_drawdown(returns, D("0.5"), 50, seed=10)
    assert first == again and first[0] <= first[1]
    assert first != other


def test_simulations_and_the_resampled_length_are_capped():
    long = _returns(5, MAX_BOOTSTRAP_RETURNS + 500, "0.0005", "0.01")
    points = exposure_curve(long, 2, bootstrap=True, simulations=MAX_SIMULATIONS * 10, seed=1)
    assert all(p.bootstrap_p95 is not None for p in points)
    assert points[-1].bootstrap_p95 >= points[-1].bootstrap_p50  # type: ignore[operator]
