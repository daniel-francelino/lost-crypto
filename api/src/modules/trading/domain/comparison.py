"""Realized Sharpe against the backtest's Sharpe (book 2 ch. 1, C4, p. 7).

Chan's experience, not a rule: most traders are satisfied when the live Sharpe is above half of
the backtest's. Short live samples are noisy, so below ``MIN_PERIODS`` returns no ratio is given.
"""

from dataclasses import dataclass
from decimal import Decimal

MIN_PERIODS = 30  # the same floor the risk ratios use
CHAN_MIN_RATIO = Decimal("0.5")
_Q = Decimal("0.0001")


@dataclass(frozen=True, slots=True)
class SharpeComparison:
    realized: Decimal | None
    backtest: Decimal | None
    realized_periods: int | None
    ratio: Decimal | None
    reason: str | None  # why there is no ratio


def compare_sharpe(
    realized: Decimal | None, backtest: Decimal | None, realized_periods: int | None
) -> SharpeComparison:
    if realized is None or realized_periods is None or realized_periods < MIN_PERIODS:
        return SharpeComparison(
            realized, backtest, realized_periods, None, "short live sample: no realized Sharpe yet"
        )
    if backtest is None:
        return SharpeComparison(
            realized, backtest, realized_periods, None, "the backtest has no Sharpe"
        )
    if backtest <= 0:
        return SharpeComparison(
            realized, backtest, realized_periods, None, "the backtest Sharpe is not positive"
        )
    return SharpeComparison(
        realized, backtest, realized_periods, (realized / backtest).quantize(_Q), None
    )
