"""Growth and drawdown as a function of exposure (Chan, book 2 ch. 8, C3-C5, pp. 172-180).

Given the per-bar returns of a backtest, scale them by an exposure ``f`` in ``(0, 1]`` (spot: never
above 1) and see what happens to the long-run growth rate ``g(f) = mean(ln(1 + f * r))`` and to the
worst drawdown. ``g`` rises, peaks near Kelly and then falls; the drawdown only grows with ``f``.
Kelly is an upper bound to be discounted, never a recommendation to size up: the curve is shown as
a band, not as an optimum.

A bootstrap (resampling the per-bar returns with replacement, with a seed) gives the simulated
counterpart. It keeps skew and kurtosis without fitting a distribution but destroys the
autocorrelation of the real series, which is said on the screen. Everything is ``Decimal``; the cost
of the bootstrap is capped by the limits below.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal, localcontext
from random import Random

MIN_RETURNS = 30
MAX_STEPS = 50
MAX_BOOTSTRAP_RETURNS = 5_000  # the last returns; longer series are cut to keep the run time sane
MAX_SIMULATIONS = 100
_PRECISION = 40
_PCT = Decimal(100)


@dataclass(frozen=True, slots=True)
class CurvePoint:
    fraction: Decimal
    growth: Decimal | None  # None: the exposure would have wiped the account out at some bar
    max_drawdown_pct: Decimal
    bootstrap_p50: Decimal | None = None
    bootstrap_p95: Decimal | None = None


def fractions(steps: int) -> list[Decimal]:
    """``steps`` exposures evenly spaced in (0, 1], the last one being 1."""
    if not 1 <= steps <= MAX_STEPS:
        raise ValueError(f"steps must be between 1 and {MAX_STEPS}")
    return [Decimal(i) / steps for i in range(1, steps + 1)]


def growth_rate(returns: Sequence[Decimal], fraction: Decimal) -> Decimal | None:
    """``mean(ln(1 + f r))``; ``None`` when ``1 + f r <= 0`` somewhere (ruin)."""
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        total = Decimal(0)
        for value in returns:
            scaled = 1 + fraction * value
            if scaled <= 0:
                return None
            total += scaled.ln()
        return total / len(returns)


def max_drawdown_pct(returns: Sequence[Decimal], fraction: Decimal) -> Decimal:
    """Worst peak-to-trough fall of the equity compounded with ``f * r`` per bar, in percent."""
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        equity = peak = Decimal(1)
        worst = Decimal(0)
        for value in returns:
            equity *= max(Decimal(0), 1 + fraction * value)
            peak = max(peak, equity)
            worst = max(worst, (peak - equity) / peak)
        return worst * _PCT


def ruin_fraction(returns: Sequence[Decimal]) -> Decimal | None:
    """The exposure ``1 / |worst return|`` above which one bar wipes the account out."""
    worst = min(returns, default=Decimal(0))
    return None if worst >= 0 else 1 / -worst


def _percentile(sorted_values: Sequence[Decimal], share: Decimal) -> Decimal:
    index = int((share * len(sorted_values)).to_integral_value(rounding="ROUND_CEILING")) - 1
    return sorted_values[max(0, min(index, len(sorted_values) - 1))]


def bootstrap_drawdown(
    returns: Sequence[Decimal], fraction: Decimal, simulations: int, seed: int
) -> tuple[Decimal, Decimal]:
    """The 50th and 95th percentile of the max drawdown over resampled series."""
    rng = Random(seed)
    length = len(returns)
    drawdowns = sorted(
        max_drawdown_pct([returns[rng.randrange(length)] for _ in range(length)], fraction)
        for _ in range(simulations)
    )
    return _percentile(drawdowns, Decimal("0.5")), _percentile(drawdowns, Decimal("0.95"))


def exposure_curve(
    returns: Sequence[Decimal],
    steps: int,
    *,
    bootstrap: bool = False,
    simulations: int = 100,
    seed: int = 0,
) -> list[CurvePoint]:
    """One point per exposure. Raises ``ValueError`` for a sample below ``MIN_RETURNS``."""
    if len(returns) < MIN_RETURNS:
        raise ValueError(f"at least {MIN_RETURNS} returns are needed")
    sample = list(returns[-MAX_BOOTSTRAP_RETURNS:])
    runs = min(max(simulations, 1), MAX_SIMULATIONS)
    points: list[CurvePoint] = []
    for fraction in fractions(steps):
        p50 = p95 = None
        if bootstrap:
            p50, p95 = bootstrap_drawdown(sample, fraction, runs, seed)
        points.append(
            CurvePoint(
                fraction,
                growth_rate(returns, fraction),
                max_drawdown_pct(returns, fraction),
                p50,
                p95,
            )
        )
    return points
