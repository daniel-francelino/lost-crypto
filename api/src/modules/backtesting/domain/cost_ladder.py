"""Cost sensitivity (book 1 ch. 2, C7): the same run at several cost levels, and its break-even.

Chan's ES example goes from Sharpe ~3 to ~-3 with one basis point of extra cost. Here the whole
engine is re-run at each level, because the strategy sees its position and the buy size depends
on collateral, so reusing the signals of the base run would not be exact. Perpetual runs also
scale the liquidation fee proxy with the taker fee. Fill realism (market impact, limit-order
queues) does not change.
"""

from collections.abc import Callable, Sequence
from dataclasses import replace
from decimal import Decimal
from itertools import pairwise
from typing import Any

from modules.analytics.domain.metrics import compute_metrics
from modules.backtesting.domain.engine import run_backtest
from modules.backtesting.domain.models import (
    MAX_COST_MULTIPLIER,
    BacktestConfig,
    BacktestOutcome,
)
from modules.backtesting.domain.perpetual_engine import (
    PerpetualBacktestOutcome,
    run_perpetual_backtest,
)
from modules.exchanges.domain.models import TradingProduct
from modules.market_data.domain.models import Candle, FundingRate, MarketInfo
from modules.strategies.domain.base import Strategy

MULTIPLIERS: tuple[Decimal, ...] = (
    *(Decimal(m) for m in ("0", "0.5", "1", "1.5", "2")),
    Decimal(MAX_COST_MULTIPLIER),
)
MAX_CANDLES = 50_000  # the ladder costs one engine run per level
_BPS = Decimal(10_000)
_Q = Decimal("0.0001")


def _level(
    config: BacktestConfig,
    candles: Sequence[Candle],
    market: MarketInfo,
    strategy: Strategy[Any],
    multiplier: Decimal,
    mark_candles: Sequence[Candle],
    funding_rates: Sequence[FundingRate],
) -> dict[str, Any]:
    scaled = replace(
        config,
        fee_rate=config.fee_rate * multiplier,
        slippage_bps=config.slippage_bps * multiplier,
        cost_sensitivity=False,  # a level is a plain run (and may have zero cost)
    )
    outcome: BacktestOutcome | PerpetualBacktestOutcome
    if scaled.product is TradingProduct.LINEAR_PERPETUAL:
        outcome = run_perpetual_backtest(
            scaled,
            candles,
            mark_candles,
            funding_rates,
            market,
            strategy,
            liquidation_fee_rate=scaled.fee_rate,
        )
    else:
        outcome = run_backtest(scaled, candles, market, strategy)
    metrics = compute_metrics(
        initial_capital=config.initial_capital,
        equity_curve=outcome.equity_curve,
        fills=outcome.fills,
        first_price=outcome.first_price,
        last_price=outcome.last_price,
        open_position=outcome.final_quantity > 0,
        rejected_signals=len(outcome.rejected),
        bar=config.timeframe.delta,
        benchmark_prices=[c.close for c in candles],
        in_market=outcome.in_market,
    )
    level = {
        "multiplier": str(multiplier),
        "fee_rate": str(scaled.fee_rate),
        "slippage_bps": str(scaled.slippage_bps),
        "cost_per_side_bps": str((scaled.fee_rate * _BPS + scaled.slippage_bps).quantize(_Q)),
        "net_pnl": str(metrics.net_pnl),
        "total_return_pct": str(metrics.total_return_pct),
        "sharpe_ratio": None if metrics.sharpe_ratio is None else str(metrics.sharpe_ratio),
        "round_trips": metrics.round_trips,
        "fees_paid": str(metrics.fees_paid),
    }
    if isinstance(outcome, PerpetualBacktestOutcome):
        level.update(
            funding_paid=str(outcome.funding_paid),
            funding_received=str(outcome.funding_received),
            liquidation_fee_rate=str(scaled.fee_rate),
            liquidation_count=outcome.liquidation_count,
            maximum_notional=str(outcome.max_notional),
            minimum_liquidation_distance_pct=(
                None
                if outcome.min_liquidation_distance_pct is None
                else str(outcome.min_liquidation_distance_pct)
            ),
            leverage=scaled.leverage,
        )
    return level


def break_even(levels: Sequence[dict[str, Any]]) -> tuple[str, Decimal | None]:
    """Where net PnL crosses zero, by linear interpolation between two levels.

    Returns ``("found", multiplier)``, ``("never_profitable", None)`` when even zero cost loses,
    or ``("above_max", None)`` when the run is still profitable at the highest level tried.
    """
    pnls = [(Decimal(level["multiplier"]), Decimal(level["net_pnl"])) for level in levels]
    if pnls[0][1] <= 0:
        return "never_profitable", None
    for (m0, p0), (m1, p1) in pairwise(pnls):
        if p0 > 0 >= p1:
            return "found", (m0 + (m1 - m0) * p0 / (p0 - p1)).quantize(_Q)
    return "above_max", None


def run_cost_ladder(
    config: BacktestConfig,
    candles: Sequence[Candle],
    market: MarketInfo,
    new_strategy: Callable[[], Strategy[Any]],
    mark_candles: Sequence[Candle] = (),
    funding_rates: Sequence[FundingRate] = (),
) -> dict[str, Any]:
    if config.product is TradingProduct.LINEAR_PERPETUAL and (
        len(mark_candles) != len(candles) or any(rate.mark_price is None for rate in funding_rates)
    ):
        raise ValueError("futures cost sensitivity requires complete mark and funding data")
    levels = [
        _level(
            config,
            candles,
            market,
            new_strategy(),
            multiplier,
            mark_candles,
            funding_rates,
        )
        for multiplier in MULTIPLIERS
    ]
    status, multiplier = break_even(levels)
    base_cost = config.fee_rate * _BPS + config.slippage_bps
    return {
        "levels": levels,
        "break_even_status": status,
        "break_even_multiplier": None if multiplier is None else str(multiplier),
        "break_even_cost_per_side_bps": None
        if multiplier is None
        else str((base_cost * multiplier).quantize(_Q)),
        "note": "Fee and slippage change; futures also scale the liquidation fee proxy. "
        "Market impact and missed limit fills are not modelled.",
    }
