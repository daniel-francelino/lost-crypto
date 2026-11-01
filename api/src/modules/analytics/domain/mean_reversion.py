"""Descriptive Ornstein-Uhlenbeck half-life estimate using Decimal-only OLS."""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, localcontext
from itertools import pairwise

_PRECISION = 40
_MIN_POINTS = 100
_DF_CRITICAL_5PCT = Decimal("-2.86")


@dataclass(frozen=True, slots=True)
class HalfLife:
    n: int
    slope: Decimal
    t_stat: Decimal
    half_life_bars: Decimal
    stationary: bool


def half_life(series: Sequence[Decimal], *, log: bool = True) -> HalfLife | None:
    """Fit Δy = a + b*y[-1] + error; return None when mean reversion is not estimated."""
    if len(series) < _MIN_POINTS or (log and any(value <= 0 for value in series)):
        return None
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        values = [value.ln() for value in series] if log else list(series)
        x_values = values[:-1]
        changes = [current - previous for previous, current in pairwise(values)]
        n = len(changes)
        x_mean = sum(x_values, Decimal(0)) / n
        y_mean = sum(changes, Decimal(0)) / n
        centered_x = [value - x_mean for value in x_values]
        sxx = sum((value * value for value in centered_x), Decimal(0))
        if sxx == 0:
            return None
        slope = (
            sum((x * (y - y_mean) for x, y in zip(centered_x, changes, strict=True)), Decimal(0))
            / sxx
        )
        phi = Decimal(1) + slope
        if slope >= 0 or not Decimal(0) < phi < Decimal(1):
            return None
        intercept = y_mean - slope * x_mean
        residuals = [y - intercept - slope * x for x, y in zip(x_values, changes, strict=True)]
        residual_variance = sum((value * value for value in residuals), Decimal(0)) / (n - 2)
        if residual_variance <= 0:
            return None
        standard_error = (residual_variance / sxx).sqrt()
        if standard_error == 0:
            return None
        t_stat = slope / standard_error
        half_life_bars = Decimal(2).ln() / -phi.ln()
        return HalfLife(
            n=len(series),
            slope=slope,
            t_stat=t_stat,
            half_life_bars=half_life_bars,
            stationary=t_stat <= _DF_CRITICAL_5PCT,
        )


HURST_LAGS = (2, 4, 8, 16, 32)
VARIANCE_RATIO_LAGS = (2, 4, 8)


@dataclass(frozen=True, slots=True)
class VarianceRatio:
    lag: int
    ratio: Decimal
    z_stat: Decimal  # homoskedastic Lo-MacKinlay; crypto volatility clusters, so it is optimistic


def sample_every(series: Sequence[Decimal], step: int) -> list[Decimal]:
    """One value per ``step`` candles: overlapping short candles are not independent samples
    (book 2 ch. 2, p. 43)."""
    if step < 1:
        raise ValueError("step must be at least 1")
    return list(series[::step])


def _transform(series: Sequence[Decimal], log: bool) -> list[Decimal] | None:
    if log and any(value <= 0 for value in series):
        return None
    return [value.ln() for value in series] if log else list(series)


def _variance(values: Sequence[Decimal]) -> Decimal | None:
    if len(values) < 2:
        return None
    mean = sum(values, Decimal(0)) / len(values)
    return sum(((v - mean) ** 2 for v in values), Decimal(0)) / (len(values) - 1)


def _lagged_differences(values: Sequence[Decimal], lag: int) -> list[Decimal]:
    return [values[i + lag] - values[i] for i in range(len(values) - lag)]


def variance_ratio(
    series: Sequence[Decimal], lag: int, *, log: bool = True
) -> VarianceRatio | None:
    """``Var(y[t] - y[t-q]) / (q * Var(y[t] - y[t-1]))``: below 1 reverts, 1 is a random walk,
    above 1 trends. ``None`` for a short or degenerate series."""
    if lag < 2 or len(series) < _MIN_POINTS:
        return None
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        values = _transform(series, log)
        if values is None:
            return None
        one = _variance(_lagged_differences(values, 1))
        many = _variance(_lagged_differences(values, lag))
        if one is None or many is None or one == 0:
            return None
        ratio = many / (lag * one)
        n = Decimal(len(values) - 1)
        spread = (Decimal(2 * (2 * lag - 1) * (lag - 1)) / (3 * lag * n)).sqrt()
        return VarianceRatio(lag, ratio, (ratio - 1) / spread)


def hurst(
    series: Sequence[Decimal], lags: Sequence[int] = HURST_LAGS, *, log: bool = True
) -> Decimal | None:
    """Slope of ``ln Var(y[t+tau] - y[t])`` on ``ln tau``, halved (book 2 ch. 2, p. 45).
    ``H < 0.5`` reverts, ``0.5`` is a random walk, ``> 0.5`` trends."""
    usable = [lag for lag in lags if lag >= 1 and len(series) >= max(_MIN_POINTS, 4 * lag)]
    if len(usable) < 3:
        return None
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        values = _transform(series, log)
        if values is None:
            return None
        points: list[tuple[Decimal, Decimal]] = []
        for lag in usable:
            variance = _variance(_lagged_differences(values, lag))
            if variance is None or variance <= 0:
                return None
            points.append((Decimal(lag).ln(), variance.ln()))
        x_mean = sum((x for x, _ in points), Decimal(0)) / len(points)
        y_mean = sum((y for _, y in points), Decimal(0)) / len(points)
        sxx = sum(((x - x_mean) ** 2 for x, _ in points), Decimal(0))
        if sxx == 0:
            return None
        slope = sum(((x - x_mean) * (y - y_mean) for x, y in points), Decimal(0)) / sxx
        return slope / 2


WINDOW_MULTIPLES = (Decimal("0.5"), Decimal(1), Decimal(2))
_MIN_WINDOW = 2


def suggested_windows(half_life_bars: Decimal) -> list[int]:
    """Look-back windows around the half-life (0.5x, 1x, 2x), whole candles, at least 2.
    A starting range for a search, not a recommendation (book 2 ch. 2, p. 47)."""
    windows = {
        max(_MIN_WINDOW, int((half_life_bars * multiple).to_integral_value(rounding=ROUND_HALF_UP)))
        for multiple in WINDOW_MULTIPLES
    }
    return sorted(windows)
