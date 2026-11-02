"""Metrics between the operator's named regime breaks (book 2 ch. 5, O1, pp. 129-130).

A backtest, a half-life or a hedge ratio fitted across a structural break may be meaningless, so
the one run is cut at every break that falls inside it and each stretch gets the same metrics as
the whole run, like ``periods.py`` does by year. The breaks are the operator's knowledge, not
detected: choosing them after seeing the results is a research freedom, so each snapshot keeps
when the break was registered.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from itertools import pairwise
from typing import Any

from modules.analytics.domain.metrics import compute_metrics
from modules.backtesting.domain.models import BacktestConfig, BacktestOutcomeView
from modules.market_data.domain.models import Candle

MIN_STRETCH_CANDLES = 2


@dataclass(frozen=True, slots=True)
class BreakRef:
    id: str
    name: str
    occurred_at: datetime
    created_at: datetime


def _cut_indexes(candles: Sequence[Candle], breaks: Sequence[BreakRef]) -> list[int]:
    """First candle at or after each break that lies strictly inside the data, once each."""
    indexes: set[int] = set()
    for brk in breaks:
        if not candles[0].open_time < brk.occurred_at <= candles[-1].open_time:
            continue
        index = next(i for i, c in enumerate(candles) if c.open_time >= brk.occurred_at)
        indexes.add(index)
    return sorted(indexes)


def _label(candles: Sequence[Candle], first: int, end: int, breaks: Sequence[BreakRef]) -> str:
    before = [b for b in breaks if b.occurred_at <= candles[first].open_time and first > 0]
    after = [b for b in breaks if candles[end - 1].open_time < b.occurred_at]
    if before and after:
        return f"entre {before[-1].name} e {after[0].name}"
    if before:
        return f"depois de {before[-1].name}"
    if after:
        return f"antes de {after[0].name}"
    return "tudo"


def compute_break_segments(
    config: BacktestConfig,
    candles: Sequence[Candle],
    outcome: BacktestOutcomeView,
    breaks: Sequence[BreakRef],
) -> dict[str, Any] | None:
    """``None`` when no break falls inside the run."""
    if len(candles) < 2 * MIN_STRETCH_CANDLES:
        return None
    ordered = sorted(
        (b for b in breaks if candles[0].open_time < b.occurred_at <= candles[-1].open_time),
        key=lambda b: b.occurred_at,
    )
    cuts = _cut_indexes(candles, ordered)
    if not cuts:
        return None
    edges = [0, *cuts, len(candles)]
    rows: list[dict[str, Any]] = []
    for first, end in pairwise(edges):
        if end - first < MIN_STRETCH_CANDLES:
            continue
        start_time = candles[first].open_time
        stop_time = candles[end].open_time if end < len(candles) else None

        def inside(moment: datetime, start: datetime = start_time, stop: Any = stop_time) -> bool:
            return moment >= start and (stop is None or moment < stop)

        initial = config.initial_capital if first == 0 else outcome.equity_curve[first - 1].equity
        metrics = compute_metrics(
            initial_capital=initial,
            equity_curve=outcome.equity_curve[first:end],
            fills=[f for f in outcome.fills if inside(f.time)],
            first_price=candles[first].open,
            last_price=candles[end - 1].close,
            open_position=outcome.in_market[end - 1],
            rejected_signals=sum(1 for r in outcome.rejected if inside(r.time)),
            bar=config.timeframe.delta,
            benchmark_prices=[c.close for c in candles[first:end]],
            in_market=outcome.in_market[first:end],
        )
        rows.append(
            {
                "label": _label(candles, first, end, ordered),
                "start": start_time.isoformat(),
                "end": candles[end - 1].close_time.isoformat(),
                "candles": end - first,
                "metrics": metrics.to_dict(),
            }
        )
    return {
        "breaks": [
            {
                "id": b.id,
                "name": b.name,
                "occurred_at": b.occurred_at.isoformat(),
                "created_at": b.created_at.isoformat(),
            }
            for b in ordered
        ],
        "segments": rows,
    }
