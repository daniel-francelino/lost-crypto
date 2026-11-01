"""Lagged-return correlation grid for time-series momentum (Chan, book 2 ch. 6, C2, pp. 134-137).

For each ``(lookback, holding)`` pair the past return over ``lookback`` candles is correlated with
the next return over ``holding`` candles, taking non-overlapping samples. A grid is many tests at
once, so the answer is given against a Bonferroni-corrected level: the grid is a map of where
momentum might exist, not a ranking to pick the best cell from. Correlation is not tradable
profit: it pays no costs.

All arithmetic is ``Decimal``. The one ``float`` is the normal quantile of the corrected level
(``statistics.NormalDist``), a statistics constant that never touches money.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal, localcontext
from statistics import NormalDist

MAX_CELLS = 100
MIN_PAIRS = 10  # below this the correlation says nothing
ALPHA = Decimal("0.05")
_PRECISION = 40


@dataclass(frozen=True, slots=True)
class GridCell:
    lookback: int
    holding: int
    n: int
    correlation: Decimal | None
    z_stat: Decimal | None  # Fisher z of the correlation: atanh(r) * sqrt(n - 3)
    significant_corrected: bool | None
    reason: str | None


def pair_count(length: int, lookback: int, holding: int) -> int:
    """Non-overlapping samples: one every ``max(lookback, holding)`` candles."""
    step = max(lookback, holding)
    last_start = length - 1 - holding
    return 0 if last_start < lookback else (last_start - lookback) // step + 1


def _pearson(xs: Sequence[Decimal], ys: Sequence[Decimal]) -> Decimal | None:
    n = len(xs)
    mean_x = sum(xs, Decimal(0)) / n
    mean_y = sum(ys, Decimal(0)) / n
    sxx = sum(((x - mean_x) ** 2 for x in xs), Decimal(0))
    syy = sum(((y - mean_y) ** 2 for y in ys), Decimal(0))
    if sxx == 0 or syy == 0:
        return None
    sxy = sum(((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True)), Decimal(0))
    return sxy / (sxx * syy).sqrt()


def critical_z(alpha: Decimal) -> Decimal:
    """Two-sided critical value of the standard normal at level ``alpha``."""
    return Decimal(str(NormalDist().inv_cdf(1 - float(alpha) / 2)))


def _cell(closes: Sequence[Decimal], lookback: int, holding: int, critical: Decimal) -> GridCell:
    step = max(lookback, holding)
    count = pair_count(len(closes), lookback, holding)
    if count < MIN_PAIRS:
        return GridCell(lookback, holding, count, None, None, None, "too few independent samples")
    starts = [lookback + i * step for i in range(count)]
    past = [closes[t] / closes[t - lookback] - 1 for t in starts]
    future = [closes[t + holding] / closes[t] - 1 for t in starts]
    r = _pearson(past, future)
    if r is None or abs(r) >= 1:
        return GridCell(lookback, holding, count, None, None, None, "no spread in the returns")
    z = ((1 + r) / (1 - r)).ln() / 2 * Decimal(count - 3).sqrt()
    return GridCell(lookback, holding, count, r, z, abs(z) >= critical, None)


def lagged_return_grid(
    closes: Sequence[Decimal], lookbacks: Sequence[int], holdings: Sequence[int]
) -> tuple[list[GridCell], Decimal, Decimal]:
    """The cells, the corrected level ``0.05 / cells`` and its critical z."""
    if any(value < 1 for value in (*lookbacks, *holdings)):
        raise ValueError("lookbacks and holdings must be at least 1")
    cells = len(lookbacks) * len(holdings)
    if not 1 <= cells <= MAX_CELLS:
        raise ValueError(f"the grid must have between 1 and {MAX_CELLS} cells")
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        alpha = ALPHA / cells
        critical = critical_z(alpha)
        return (
            [_cell(closes, lb, hd, critical) for lb in lookbacks for hd in holdings],
            alpha,
            critical,
        )
