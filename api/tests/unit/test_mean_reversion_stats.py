"""Hurst exponent and variance ratio (book 2 ch. 2)."""

import math
import random
from decimal import Decimal

import pytest

from modules.analytics.domain.mean_reversion import (
    hurst,
    sample_every,
    variance_ratio,
)


def _prices(seed: int, n: int, phi: float | None = None, drift: float = 0.0) -> list[Decimal]:
    """phi=None: a random walk in log; phi<1: an AR(1) in log (mean-reverting)."""
    rng = random.Random(seed)
    x = 0.0
    out = []
    for _ in range(n):
        shock = rng.gauss(0, 0.01)
        x = x + shock + drift if phi is None else phi * x + shock
        out.append(Decimal(str(round(100 * math.exp(x), 8))))
    return out


def _trending(seed: int, n: int) -> list[Decimal]:
    """Persistent increments: a positively autocorrelated return process."""
    rng = random.Random(seed)
    x = 0.0
    step = 0.0
    out = []
    for _ in range(n):
        step = 0.8 * step + rng.gauss(0, 0.004)
        x += step
        out.append(Decimal(str(round(100 * math.exp(x), 8))))
    return out


def test_mean_reverting_series_has_hurst_below_half_and_ratio_below_one():
    series = _prices(1, 4000, phi=0.9)
    h = hurst(series)
    ratio = variance_ratio(series, 4)
    assert h is not None and h < Decimal("0.35")
    assert ratio is not None and ratio.ratio < Decimal("0.9") and ratio.z_stat < -3


def test_random_walk_is_close_to_half_and_to_one():
    for seed in range(5):
        series = _prices(10 + seed, 4000)
        h = hurst(series)
        ratio = variance_ratio(series, 4)
        assert h is not None and Decimal("0.4") < h < Decimal("0.6")
        assert ratio is not None and Decimal("0.8") < ratio.ratio < Decimal("1.2")


def test_trending_series_has_hurst_above_half_and_ratio_above_one():
    series = _trending(3, 4000)
    h = hurst(series)
    ratio = variance_ratio(series, 4)
    assert h is not None and h > Decimal("0.55")
    assert ratio is not None and ratio.ratio > Decimal("1.5") and ratio.z_stat > 3


def test_ratio_of_one_step_returns_is_not_asked_for():
    assert variance_ratio(_prices(1, 500), 1) is None


def test_short_constant_and_invalid_series_return_none_without_nan():
    assert hurst(_prices(2, 99)) is None
    assert variance_ratio(_prices(2, 99), 2) is None
    flat = [Decimal(100)] * 500
    assert hurst(flat) is None
    assert variance_ratio(flat, 2) is None
    broken = _prices(3, 500)
    broken[7] = Decimal(0)
    assert hurst(broken) is None
    assert variance_ratio(broken, 2) is None
    assert hurst(broken, log=False) is not None  # without the log a zero price is only a number


def test_hurst_needs_at_least_three_usable_lags():
    assert hurst(_prices(4, 5000), lags=(2, 4)) is None


def test_sample_every_keeps_one_in_k_and_rejects_zero():
    series = [Decimal(i) for i in range(10)]
    assert sample_every(series, 1) == series
    assert sample_every(series, 3) == [Decimal(0), Decimal(3), Decimal(6), Decimal(9)]
    with pytest.raises(ValueError):
        sample_every(series, 0)


def test_results_are_deterministic():
    series = _prices(5, 1000, phi=0.95)
    assert hurst(series) == hurst(series)
    assert variance_ratio(series, 4) == variance_ratio(series, 4)


def test_suggested_windows_are_whole_candles_around_the_half_life():
    from modules.analytics.domain.mean_reversion import suggested_windows

    assert suggested_windows(Decimal("13.51")) == [7, 14, 27]
    assert suggested_windows(Decimal("1.2")) == [2]  # never below 2, duplicates collapse
    assert suggested_windows(Decimal("3")) == [2, 3, 6]
