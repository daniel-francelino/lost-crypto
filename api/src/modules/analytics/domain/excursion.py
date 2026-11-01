"""Maximum adverse excursion of each trade (Chan, book 2 ch. 8, C7, pp. 183-184).

How far did a trade go against its entry before it ended? A stop tighter than the deepest
excursion the strategy normally suffers fires on ordinary noise and silently changes the
backtest; for a mean-reversion strategy the book puts the stop beyond that excursion, only against
black swans. Computed after the run from the fills and the stored candles, so it needs no change
in the engine.

An excursion is measured from the entry fill price to the lowest low between the entry bar and
the exit bar, in percent, never negative. A trade that never dipped below its entry has 0.
"""

from bisect import bisect_right
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal, localcontext
from typing import Any

from modules.execution.domain.orders import Fill
from modules.market_data.domain.models import Candle
from modules.strategies.domain.types import Side

_PRECISION = 40
_PCT = Decimal(100)
WORST_LISTED = 5


def _bar_of(opens: Sequence[datetime], moment: datetime) -> int:
    return max(0, bisect_right(opens, moment) - 1)


def _quantile(sorted_values: Sequence[Decimal], share: Decimal) -> Decimal:
    """Nearest-rank quantile of an ascending list."""
    index = int((share * len(sorted_values)).to_integral_value(rounding="ROUND_CEILING")) - 1
    return sorted_values[max(0, min(index, len(sorted_values) - 1))]


def adverse_excursions(fills: Sequence[Fill], candles: Sequence[Candle]) -> dict[str, Any] | None:
    """The report stored with a run, or ``None`` when there is no completed trade."""
    if not candles:
        return None
    opens = [c.open_time for c in candles]
    trades: list[tuple[Decimal, datetime, datetime]] = []
    entry: Fill | None = None
    for fill in sorted(fills, key=lambda f: f.time):
        if fill.side is Side.BUY and entry is None:
            entry = fill
        elif fill.side is Side.SELL and entry is not None:
            first = _bar_of(opens, entry.time)
            last = max(first, _bar_of(opens, fill.time))
            lowest = min(c.low for c in candles[first : last + 1])
            with localcontext() as ctx:
                ctx.prec = _PRECISION
                depth = max(Decimal(0), (entry.price - lowest) / entry.price * _PCT)
            trades.append((depth, entry.time, fill.time))
            entry = None
    if not trades:
        return None
    ordered = sorted((depth for depth, _, _ in trades))
    worst = sorted(trades, key=lambda t: t[0], reverse=True)[:WORST_LISTED]
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        return {
            "trades": len(trades),
            "worst_pct": str(ordered[-1]),
            "median_pct": str(ordered[(len(ordered) - 1) // 2]),
            "p95_pct": str(_quantile(ordered, Decimal("0.95"))),
            "worst_trades": [
                {"entry_at": e.isoformat(), "exit_at": x.isoformat(), "pct": str(d)}
                for d, e, x in worst
            ],
        }
