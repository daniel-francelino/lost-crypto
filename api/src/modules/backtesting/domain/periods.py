"""Performance by calendar period (book 1 ch. 2, C9: judge a strategy by its recent years).

The run is not repeated: the equity curve and fills of the single run are cut by calendar year
(or by quarter when the whole run spans less than two years) and each slice gets the same
metrics as the full run. Each slice starts from the equity at the end of the previous one, so
compounding the slice returns gives the total return.
"""

from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any

from modules.analytics.domain.metrics import compute_metrics
from modules.backtesting.domain.models import BacktestConfig, BacktestOutcomeView
from modules.market_data.domain.models import Candle

_QUARTERS_BELOW = timedelta(days=730)


def _label(moment: datetime, quarterly: bool) -> str:
    if quarterly:
        return f"{moment.year}-T{(moment.month - 1) // 3 + 1}"
    return str(moment.year)


def _buckets(candles: Sequence[Candle], quarterly: bool) -> list[tuple[str, int, int]]:
    """``(label, first index, end index)`` of consecutive candles in the same period."""
    buckets: list[tuple[str, int, int]] = []
    start = 0
    current = _label(candles[0].open_time, quarterly)
    for index, candle in enumerate(candles):
        label = _label(candle.open_time, quarterly)
        if label != current:
            buckets.append((current, start, index))
            start, current = index, label
    buckets.append((current, start, len(candles)))
    return buckets


def compute_periods(
    config: BacktestConfig, candles: Sequence[Candle], outcome: BacktestOutcomeView
) -> dict[str, Any] | None:
    if len(candles) < 2:
        return None
    quarterly = candles[-1].close_time - candles[0].open_time < _QUARTERS_BELOW
    rows: list[dict[str, Any]] = []
    for label, first, end in _buckets(candles, quarterly):
        start_time = candles[first].open_time
        end_time = candles[end].open_time if end < len(candles) else None

        def inside(moment: datetime, start: datetime = start_time, stop: Any = end_time) -> bool:
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
                "label": label,
                "start": start_time.isoformat(),
                "end": candles[end - 1].close_time.isoformat(),
                "candles": end - first,
                "metrics": metrics.to_dict(),
            }
        )
    return {"granularity": "quarter" if quarterly else "year", "periods": rows}
