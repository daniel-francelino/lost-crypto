"""Risk-adjusted ratios from an equity curve, as pure ``Decimal`` functions.

Convention (book 1 ch. 3 O1, our crypto adaptation): crypto trades every day, so a year has
``N_T = 365 days / bar`` periods (8,760 for 1h candles, 365 for 1d). The risk-free rate is 0:
the strategies are spot, long-only and unfunded, and Chan subtracts it only when there is a
financing cost. Every ratio is ``None`` when the sample is too short to mean anything.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, localcontext

MIN_RETURNS = 30  # below this many periodic returns the ratios are reported as None
MIN_ANNUALIZE_SPAN = timedelta(days=30)
_YEAR = Decimal(365 * 86_400)
_GAP_TOLERANCE = Decimal("1.5")  # a step longer than 1.5 bars is a gap, not one return
_PRECISION = 40


@dataclass(frozen=True, slots=True)
class ReturnSeries:
    """Periodic returns of a curve; steps across a gap are dropped and counted."""

    returns: list[Decimal]
    benchmark: list[Decimal] | None  # aligned with ``returns`` when prices were given
    gaps: int


def annualization_factor(bar: timedelta) -> Decimal:
    return _YEAR / Decimal(int(bar.total_seconds()))


def periodic_returns(
    times: Sequence[datetime],
    values: Sequence[Decimal],
    bar: timedelta,
    benchmark_prices: Sequence[Decimal] | None = None,
) -> ReturnSeries:
    limit = Decimal(int(bar.total_seconds())) * _GAP_TOLERANCE
    returns: list[Decimal] = []
    bench: list[Decimal] = []
    gaps = 0
    for i in range(1, len(values)):
        step = Decimal(int((times[i] - times[i - 1]).total_seconds()))
        if step > limit:
            gaps += 1
            continue
        if values[i - 1] <= 0:
            continue
        returns.append(values[i] / values[i - 1] - 1)
        if benchmark_prices is not None:
            previous = benchmark_prices[i - 1]
            bench.append(benchmark_prices[i] / previous - 1 if previous > 0 else Decimal(0))
    return ReturnSeries(returns, bench if benchmark_prices is not None else None, gaps)


def _mean(values: Sequence[Decimal]) -> Decimal:
    return sum(values, Decimal(0)) / len(values)


def _sample_std(values: Sequence[Decimal]) -> Decimal:
    mean = _mean(values)
    variance = sum(((v - mean) ** 2 for v in values), Decimal(0)) / (len(values) - 1)
    return variance.sqrt()


def _ratio(numerator: Decimal, denominator: Decimal, n_t: Decimal) -> Decimal | None:
    if denominator == 0:
        return None
    return n_t.sqrt() * numerator / denominator


def sharpe(returns: Sequence[Decimal], n_t: Decimal) -> Decimal | None:
    """``sqrt(N_T) * mean / sample std`` of the periodic returns (risk-free rate 0)."""
    if len(returns) < MIN_RETURNS:
        return None
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        return _ratio(_mean(returns), _sample_std(returns), n_t)


def sortino(returns: Sequence[Decimal], n_t: Decimal) -> Decimal | None:
    """Like Sharpe, with the downside deviation (target 0, over *all* periods) as risk."""
    if len(returns) < MIN_RETURNS:
        return None
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        downside = (
            sum((min(r, Decimal(0)) ** 2 for r in returns), Decimal(0)) / len(returns)
        ).sqrt()
        return _ratio(_mean(returns), downside, n_t)


def information_ratio(
    returns: Sequence[Decimal], benchmark: Sequence[Decimal], n_t: Decimal
) -> Decimal | None:
    """Sharpe of the excess returns over the benchmark (here: holding the same asset)."""
    if len(returns) < MIN_RETURNS or len(benchmark) != len(returns):
        return None
    excess = [r - b for r, b in zip(returns, benchmark, strict=True)]
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        return _ratio(_mean(excess), _sample_std(excess), n_t)


def annualized_volatility_pct(returns: Sequence[Decimal], n_t: Decimal) -> Decimal | None:
    if len(returns) < MIN_RETURNS:
        return None
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        return _sample_std(returns) * n_t.sqrt() * 100


def annualized_return_pct(first: Decimal, last: Decimal, elapsed: timedelta) -> Decimal | None:
    """Geometric: ``(last / first) ^ (1 year / elapsed) - 1``.

    ``None`` for spans shorter than ``MIN_ANNUALIZE_SPAN``: compounding a few days of
    returns into a yearly figure produces numbers that look precise and mean nothing.
    """
    if elapsed < MIN_ANNUALIZE_SPAN or first <= 0 or last <= 0:
        return None
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        return ((last / first) ** (_YEAR / Decimal(int(elapsed.total_seconds()))) - 1) * 100
