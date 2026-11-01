"""Is the average return distinguishable from zero? Gaussian test from Chan (book 2, ch. 1).

Null hypothesis: the true mean return is zero. Test statistic: ``mean / std * sqrt(n)`` of the
periodic returns, i.e. the per-bar Sharpe times ``sqrt(n)``. Under normality it is compared with
the one-sided critical values below. Crypto returns have fat tails and autocorrelation, so the
statistic tends to be optimistic; it says nothing about whether the strategy will work.
"""

from collections.abc import Sequence
from decimal import Decimal, localcontext

from modules.analytics.domain import risk_ratios

_PRECISION = 40

# (p-value, critical value), strictest first (book 2, ch. 1, p. 17).
CRITICAL_VALUES: tuple[tuple[Decimal, Decimal], ...] = (
    (Decimal("0.001"), Decimal("3.091")),
    (Decimal("0.01"), Decimal("2.326")),
    (Decimal("0.05"), Decimal("1.645")),
    (Decimal("0.10"), Decimal("1.282")),
)


def sharpe_t_stat(returns: Sequence[Decimal]) -> Decimal | None:
    """``per-bar Sharpe * sqrt(n)``; ``None`` below ``risk_ratios.MIN_RETURNS`` returns."""
    per_bar = risk_ratios.sharpe(returns, Decimal(1))
    if per_bar is None:
        return None
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        return per_bar * Decimal(len(returns)).sqrt()


def significance_level(t_stat: Decimal) -> Decimal | None:
    """The strictest p-value of the table that ``t_stat`` reaches, or ``None`` below 0.10."""
    for p_value, critical in CRITICAL_VALUES:
        if t_stat >= critical:
            return p_value
    return None
