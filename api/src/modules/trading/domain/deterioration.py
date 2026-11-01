"""Has a running bot left the range of its backtest? (book 2 ch. 4, O1; ch. 1, C4)

Two signals, both read only after ``MIN_PERIODS`` live returns, because short samples are noise:
the realized Sharpe is below half of the backtest's (Chan's experience, not a standard), or the
bot's current drawdown is deeper than the deepest one of the backtest. The result only informs;
nothing here pauses a bot.
"""

from dataclasses import dataclass
from decimal import Decimal

from modules.trading.domain.comparison import CHAN_MIN_RATIO, MIN_PERIODS, SharpeComparison


@dataclass(frozen=True, slots=True)
class Deterioration:
    sharpe_below_half: bool
    drawdown_above_backtest: bool


def deterioration(
    comparison: SharpeComparison,
    current_drawdown_pct: Decimal | None,
    backtest_max_drawdown_pct: Decimal | None,
) -> Deterioration | None:
    periods = comparison.realized_periods
    if periods is None or periods < MIN_PERIODS:
        return None
    sharpe_below = comparison.ratio is not None and comparison.ratio < CHAN_MIN_RATIO
    drawdown_above = (
        current_drawdown_pct is not None
        and backtest_max_drawdown_pct is not None
        and backtest_max_drawdown_pct > 0
        and current_drawdown_pct > backtest_max_drawdown_pct
    )
    if not (sharpe_below or drawdown_above):
        return None
    return Deterioration(sharpe_below, drawdown_above)
