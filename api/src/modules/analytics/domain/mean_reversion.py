"""Descriptive Ornstein-Uhlenbeck half-life estimate using Decimal-only OLS."""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal, localcontext
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
