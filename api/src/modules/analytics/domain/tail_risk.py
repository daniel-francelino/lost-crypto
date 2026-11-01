"""Loss and return inputs stored with a backtest for inexpensive sizing advice reads."""

from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, localcontext
from itertools import pairwise
from typing import Any

from modules.analytics.domain.risk_ratios import MIN_RETURNS, periodic_returns
from modules.backtesting.domain.models import EquityPoint
from modules.market_data.domain.models import Candle

_PRECISION = 40


def _series(
    points: Sequence[tuple[datetime, Decimal]], bar: timedelta
) -> tuple[list[Decimal], int]:
    if len(points) < 2:
        return [], 0
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        result = periodic_returns([p[0] for p in points], [p[1] for p in points], bar)
    return result.returns, result.gaps


def _daily(points: Sequence[tuple[datetime, Decimal]]) -> list[tuple[datetime, Decimal]]:
    by_day: dict[date, tuple[datetime, Decimal]] = {}
    for moment, value in points:
        utc = moment.astimezone(UTC)
        by_day[utc.date()] = (utc, value)
    return [by_day[day] for day in sorted(by_day)]


def _dated_returns(
    points: Sequence[tuple[datetime, Decimal]], bar: timedelta
) -> list[tuple[Decimal, datetime]]:
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        return [
            (current[1] / previous[1] - 1, current[0])
            for previous, current in pairwise(points)
            if 0
            < int((current[0] - previous[0]).total_seconds()) * 2
            <= int(bar.total_seconds()) * 3
            and previous[1] > 0
        ]


def _loss_fields(points: Sequence[tuple[datetime, Decimal]], bar: timedelta) -> dict[str, Any]:
    returns = _dated_returns(points, bar)
    daily = _daily(points)
    day_returns = _dated_returns(daily, timedelta(days=1))
    bar_loss = min(returns, key=lambda item: item[0], default=None)
    day_loss = min(day_returns, key=lambda item: item[0], default=None)
    return {
        "worst_bar_loss_pct": str(-bar_loss[0] * 100)
        if bar_loss and bar_loss[0] < 0 and len(returns) >= MIN_RETURNS
        else None,
        "worst_bar_at": bar_loss[1].isoformat()
        if bar_loss and bar_loss[0] < 0 and len(returns) >= MIN_RETURNS
        else None,
        "worst_day_loss_pct": str(-day_loss[0] * 100)
        if day_loss and day_loss[0] < 0 and len(day_returns) >= MIN_RETURNS
        else None,
        "worst_day_at": day_loss[1].isoformat()
        if day_loss and day_loss[0] < 0 and len(day_returns) >= MIN_RETURNS
        else None,
    }


def tail_risk(
    equity_curve: Sequence[EquityPoint], candles: Sequence[Candle], bar: timedelta
) -> dict[str, Any]:
    strategy_points = [(point.time, point.equity) for point in equity_curve]
    asset_points = [(c.open_time + bar, c.close) for c in candles]
    strategy_returns, gaps = _series(strategy_points, bar)
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        mean = (
            sum(strategy_returns, Decimal(0)) / len(strategy_returns) if strategy_returns else None
        )
        variance = (
            sum(((r - mean) ** 2 for r in strategy_returns), Decimal(0))
            / (len(strategy_returns) - 1)
            if mean is not None and len(strategy_returns) > 1
            else None
        )
    asset_daily = _series(_daily(asset_points), timedelta(days=1))[0]
    strategy = _loss_fields(strategy_points, bar)
    asset = _loss_fields(asset_points, bar)
    return {
        "strategy": strategy,
        "asset": {
            "worst_bar_return_pct": strategy_loss_to_return(asset["worst_bar_loss_pct"]),
            "worst_bar_at": asset["worst_bar_at"],
            "worst_day_return_pct": strategy_loss_to_return(asset["worst_day_loss_pct"]),
            "worst_day_at": asset["worst_day_at"],
        },
        "kelly_inputs": {
            "mean": str(mean) if mean is not None else None,
            "variance": str(variance) if variance is not None else None,
            "returns": len(strategy_returns),
            "gaps": gaps,
        },
        "returns": len(strategy_returns),
        "days": len(asset_daily),
    }


def strategy_loss_to_return(value: str | None) -> str | None:
    return None if value is None else str(-Decimal(value))
