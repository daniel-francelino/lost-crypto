"""Advisory position sizing calculations. These values never alter an order."""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal, localcontext

MIN_KELLY_RETURNS = 100
_PRECISION = 40


@dataclass(frozen=True, slots=True)
class Suggestion:
    value: Decimal
    binding: str


def kelly_fraction(mean: Decimal, variance: Decimal) -> Decimal | None:
    if variance <= 0:
        return None
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        return mean / variance


def half_kelly(fraction: Decimal) -> Decimal:
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        return max(Decimal(0), fraction / 2)


def growth_rate(
    fraction: Decimal, mean: Decimal, variance: Decimal, risk_free: Decimal = Decimal(0)
) -> Decimal:
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        return risk_free + fraction * mean - variance * fraction**2 / 2


def worst_period_loss(returns: Sequence[Decimal]) -> Decimal | None:
    if len(returns) < 30:
        return None
    losses = [-value * 100 for value in returns if value < 0]
    return max(losses) if losses else None


def tail_cap(tolerable_loss_pct: Decimal, worst_loss_pct: Decimal | None) -> Decimal | None:
    if worst_loss_pct is None or worst_loss_pct <= 0:
        return None
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        return tolerable_loss_pct / worst_loss_pct


def suggest_fraction(
    configured_fraction: Decimal,
    half_kelly_f: Decimal | None,
    caps: Sequence[tuple[str, Decimal | None]],
) -> Suggestion:
    candidates = [("spot_limit", Decimal(1))]
    if half_kelly_f is not None:
        candidates.append(("half_kelly", max(Decimal(0), half_kelly_f)))
    candidates.extend((name, max(Decimal(0), cap)) for name, cap in caps if cap is not None)
    binding, limit = min(candidates, key=lambda item: item[1])
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        return Suggestion(min(Decimal(1), max(Decimal(0), configured_fraction) * limit), binding)
