"""Candle data quality (book 1 ch. 3, C4, pp. 42-43).

Two checks. ``candle_problems`` rejects candles that cannot be right (a high below the close, a
negative price...). ``find_outliers`` *flags* returns beyond ``k`` standard deviations: Chan
inspects those by hand and keeps them only if news or a market-wide move explains them. Here the
move of a reference pair at the same time stands in for "the whole market moved" (our
adaptation). Outliers are never dropped: crashes are real and dropping candles changes the
timeline.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, localcontext
from enum import StrEnum
from itertools import pairwise

from modules.market_data.domain.models import Candle

DEFAULT_OUTLIER_SIGMAS = Decimal(4)
MIN_RETURNS_FOR_OUTLIERS = 30
_PRECISION = 40


class CandleProblem(StrEnum):
    NON_POSITIVE_PRICE = "non_positive_price"
    NEGATIVE_VOLUME = "negative_volume"
    HIGH_BELOW_BODY = "high_below_body"  # high < max(open, close)
    LOW_ABOVE_BODY = "low_above_body"  # low > min(open, close)
    MISALIGNED_TIME = "misaligned_time"  # open_time not on the timeframe grid


def candle_problems(candle: Candle) -> list[CandleProblem]:
    problems: list[CandleProblem] = []
    prices = (candle.open, candle.high, candle.low, candle.close)
    if any(price <= 0 for price in prices):
        problems.append(CandleProblem.NON_POSITIVE_PRICE)
    if candle.volume < 0:
        problems.append(CandleProblem.NEGATIVE_VOLUME)
    if candle.high < max(candle.open, candle.close):
        problems.append(CandleProblem.HIGH_BELOW_BODY)
    if candle.low > min(candle.open, candle.close):
        problems.append(CandleProblem.LOW_ABOVE_BODY)
    step = int(candle.timeframe.delta.total_seconds())
    if candle.open_time.tzinfo is None or int(candle.open_time.timestamp()) % step != 0:
        problems.append(CandleProblem.MISALIGNED_TIME)
    return problems


@dataclass(frozen=True, slots=True)
class Outlier:
    open_time: datetime
    close: Decimal
    return_pct: Decimal
    sigmas: Decimal
    reference_return_pct: Decimal | None  # same-time move of the reference pair, if known


def find_outliers(
    candles: Sequence[Candle],
    k: Decimal = DEFAULT_OUTLIER_SIGMAS,
    reference: Mapping[datetime, Decimal] | None = None,
) -> list[Outlier]:
    """Close-to-close returns beyond ``k`` sample standard deviations of the whole range.

    ``reference`` maps open_time to the reference pair's return (fraction) for the same candle.
    Returns across a missing candle are skipped (a gap is not a move).
    """
    steps: list[tuple[Candle, Decimal]] = []
    for previous, current in pairwise(candles):
        if current.open_time - previous.open_time != current.timeframe.delta:
            continue
        if previous.close > 0:
            steps.append((current, current.close / previous.close - 1))
    if len(steps) < MIN_RETURNS_FOR_OUTLIERS:
        return []
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        returns = [r for _, r in steps]
        mean = sum(returns, Decimal(0)) / len(returns)
        variance = sum(((r - mean) ** 2 for r in returns), Decimal(0)) / (len(returns) - 1)
        std = variance.sqrt()
        if std == 0:
            return []
        found: list[Outlier] = []
        for candle, ret in steps:
            sigmas = abs(ret - mean) / std
            if sigmas <= k:
                continue
            ref = None if reference is None else reference.get(candle.open_time)
            found.append(
                Outlier(
                    open_time=candle.open_time,
                    close=candle.close,
                    return_pct=(ret * 100).quantize(Decimal("0.0001")),
                    sigmas=sigmas.quantize(Decimal("0.01")),
                    reference_return_pct=None
                    if ref is None
                    else (ref * 100).quantize(Decimal("0.0001")),
                )
            )
    return found


def returns_by_time(candles: Sequence[Candle]) -> dict[datetime, Decimal]:
    """Close-to-close return (fraction) of each candle, keyed by open_time (for ``reference``)."""
    out: dict[datetime, Decimal] = {}
    for previous, current in pairwise(candles):
        if current.open_time - previous.open_time == current.timeframe.delta and previous.close:
            out[current.open_time] = current.close / previous.close - 1
    return out
