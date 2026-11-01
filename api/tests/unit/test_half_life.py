import math
import random
from decimal import Decimal

from modules.analytics.domain.mean_reversion import half_life


def _ar1_prices(seed: int, n: int, phi: float, sigma: float = 0.01) -> list[Decimal]:
    """Prices whose log follows an AR(1): the textbook mean-reverting series."""
    rng = random.Random(seed)
    x = 0.0
    out = []
    for _ in range(n):
        x = phi * x + rng.gauss(0, sigma)
        out.append(Decimal(str(round(100 * math.exp(x), 8))))
    return out


def _random_walk(seed: int, n: int) -> list[Decimal]:
    rng = random.Random(seed)
    x = 0.0
    out = []
    for _ in range(n):
        x += rng.gauss(0, 0.01)
        out.append(Decimal(str(round(100 * math.exp(x), 8))))
    return out


def test_recovers_the_half_life_of_a_known_ar1_within_a_stated_tolerance():
    result = half_life(_ar1_prices(1, 5000, 0.95))
    assert result is not None and result.stationary
    # ln(2) / -ln(0.95) = 13.51 bars; the standard error of phi at n = 5000 allows about ±1.3.
    assert Decimal("12") < result.half_life_bars < Decimal("15.5")
    assert result.n == 5000 and result.slope < 0


def test_a_slower_reversion_has_a_longer_half_life():
    fast = half_life(_ar1_prices(2, 5000, 0.90))
    slow = half_life(_ar1_prices(2, 5000, 0.98))
    assert fast is not None and slow is not None
    assert fast.half_life_bars < slow.half_life_bars


def test_random_walks_are_almost_never_called_stationary():
    verdicts = [half_life(_random_walk(seed, 2000)) for seed in range(20)]
    stationary = sum(1 for v in verdicts if v is not None and v.stationary)
    assert stationary <= 3  # the 5% critical value; the seeds are fixed so this is stable


def test_a_pure_trend_has_no_mean_reversion():
    trend = [Decimal(str(round(100 * math.exp(0.01 * i), 8))) for i in range(300)]
    assert half_life(trend) is None


def test_short_constant_and_invalid_series_return_none():
    assert half_life(_ar1_prices(3, 99, 0.9)) is None
    assert half_life([Decimal(100)] * 500) is None
    with_zero = _ar1_prices(4, 300, 0.9)
    with_zero[10] = Decimal(0)
    assert half_life(with_zero) is None  # log of a non-positive price


def test_plain_prices_do_not_need_the_log():
    rng = random.Random(5)
    level = Decimal(0)
    series = []
    for _ in range(3000):
        level = level * Decimal("0.93") + Decimal(str(round(rng.gauss(0, 1), 6)))
        series.append(level)
    result = half_life(series, log=False)  # negative values are fine without the log
    assert result is not None and result.stationary
    assert Decimal("6") < result.half_life_bars < Decimal("12")  # ln(2) / -ln(0.93) = 9.55
