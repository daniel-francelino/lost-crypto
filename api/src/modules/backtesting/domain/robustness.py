"""Is a sweep's winner a plateau or an isolated peak? (book 1 ch. 3, C8 and C10, pp. 52-60)

Chan: a model that only works at the exact optimum is overfit; vary the parameters and prefer a
choice whose neighbours also work, or split capital across parameter sets. Here the winner is
compared with its grid neighbours (one step up or down in each parameter), and the spread of
the whole grid is summarised. No formal multiple-testing correction (PSR/DSR, PBO come later).
"""

import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any

PEAK_BELOW = Decimal("0.5")  # neighbours averaging under half the winner's score: a peak
MIN_VALUES_PER_PARAMETER = 3
_Q = Decimal("0.0001")


class Verdict(StrEnum):
    PLATEAU = "plateau"
    PEAK = "peak"
    UNPROFITABLE = "unprofitable"  # even the winner does not make money: nothing to protect
    INSUFFICIENT = "insufficient"  # grid too small (or too few results) to tell


@dataclass(frozen=True, slots=True)
class Robustness:
    verdict: Verdict
    winner_score: Decimal | None
    neighbours: int
    neighbour_mean: Decimal | None
    neighbour_min: Decimal | None
    neighbour_ratio: Decimal | None  # neighbour mean / winner score
    profitable_share: Decimal | None  # share of scored combinations above zero
    median: Decimal | None
    top3_mean: Decimal | None
    scored: int


def _key(params: Mapping[str, Any], names: Sequence[str]) -> tuple[Any, ...]:
    return tuple(params.get(name) for name in names)


def _neighbour_keys(winner: tuple[Any, ...], axes: Sequence[list[Any]]) -> list[tuple[Any, ...]]:
    keys: list[tuple[Any, ...]] = []
    for dim, axis in enumerate(axes):
        if winner[dim] not in axis:
            continue
        index = axis.index(winner[dim])
        for step in (-1, 1):
            if 0 <= index + step < len(axis):
                neighbour = list(winner)
                neighbour[dim] = axis[index + step]
                keys.append(tuple(neighbour))
    return keys


def _mean(values: Sequence[Decimal]) -> Decimal:
    return (sum(values, Decimal(0)) / len(values)).quantize(_Q)


def assess(
    grid: Mapping[str, Sequence[Any]],
    scored: Sequence[tuple[Mapping[str, Any], Decimal]],
) -> Robustness:
    """``scored``: (parameters, score) of each completed run, best first (the winner first)."""
    names = sorted(grid)
    axes = [sorted(set(grid[name])) for name in names]
    scores = [score for _, score in scored]
    if not scored:
        return Robustness(Verdict.INSUFFICIENT, None, 0, None, None, None, None, None, None, 0)
    winner_params, winner = scored[0]
    by_key = {_key(params, names): score for params, score in scored}
    around = [by_key[k] for k in _neighbour_keys(_key(winner_params, names), axes) if k in by_key]
    ordered = sorted(scores, reverse=True)
    profitable = Decimal(sum(1 for s in scores if s > 0)) / len(scores)
    neighbour_mean = _mean(around) if around else None
    ratio = (
        (neighbour_mean / winner).quantize(_Q)
        if neighbour_mean is not None and winner > 0
        else None
    )
    too_small = all(len(axis) < MIN_VALUES_PER_PARAMETER for axis in axes) or not around
    if winner <= 0:
        verdict = Verdict.UNPROFITABLE
    elif too_small or ratio is None:
        verdict = Verdict.INSUFFICIENT
    else:
        verdict = Verdict.PEAK if ratio < PEAK_BELOW else Verdict.PLATEAU
    return Robustness(
        verdict=verdict,
        winner_score=winner,
        neighbours=len(around),
        neighbour_mean=neighbour_mean,
        neighbour_min=min(around) if around else None,
        neighbour_ratio=ratio,
        profitable_share=(profitable * 100).quantize(_Q),
        median=Decimal(statistics.median(scores)).quantize(_Q),
        top3_mean=_mean(ordered[:3]),
        scored=len(scores),
    )
