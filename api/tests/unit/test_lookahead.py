"""Truncation test for look-ahead (book 1 ch. 3, C7, pp. 52 and 59).

Chan's procedure: run on all the data and keep the positions (A); run on the data with the last
N periods removed and keep the positions (B); cut A to B's length: they must be identical. A
strategy (or an engine change) that peeks at the future fails, because removing the future
changes its past decisions. Runs for every strategy in the catalog, so a new strategy is covered
the day it is added.
"""

import math
from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any, ClassVar, Self

import pytest

from factories import MARKET, make_candles, make_config
from modules.backtesting.domain.engine import run_backtest
from modules.backtesting.domain.models import BacktestOutcome
from modules.market_data.domain.models import Candle
from modules.strategies.catalog import AVAILABLE_STRATEGIES
from modules.strategies.domain.base import Strategy, StrategyStyle
from modules.strategies.domain.types import (
    Side,
    Signal,
    SignalKind,
    StrategyContext,
    StrategyResult,
)

TRUNCATIONS = (10, 50, 100)
N_CANDLES = 600
# Strategies that read the daily trend from 1h candles warm up over weeks: give them 170 days.
SLOW_STRATEGIES = frozenset({"mtf_trend_pullback"})
SLOW_N_CANDLES = 4000


def _series(n: int = N_CANDLES) -> list[str]:
    """Trend, sideways chop and sharp drops, so every strategy enters and exits several times."""
    prices: list[str] = []
    for i in range(n):
        trend = i * 0.8 if i < n // 2 else (n // 2) * 0.8 - (i - n // 2) * 1.1
        chop = 40 * math.sin(i / 7) + 15 * math.sin(i / 2.3)
        crash = -120 if i % 97 in (0, 1, 2) else 0
        prices.append(str(round(1000 + trend + chop + crash, 2)))
    return prices


def _params_variants(strategy_cls: type[Strategy[Any]]) -> list[dict[str, Any]]:
    """Defaults, plus stop and target switched on when the strategy has them."""
    names = {p.name for p in strategy_cls.PARAMETERS}
    variants: list[dict[str, Any]] = [{}]
    if {"stop_loss_pct", "take_profit_pct"} <= names:
        variants.append({"stop_loss_pct": 3, "take_profit_pct": 6})
    elif "stop_loss_pct" in names:
        variants.append({"stop_loss_pct": 3})
    if "max_holding_candles" in names:
        variants.append({"max_holding_candles": 5})
    return variants


def _variant_id(params: dict[str, Any]) -> str:
    return "defaults" if not params else "-".join(sorted(params))


def _prefix(outcome: BacktestOutcome, cut: datetime, bars: int) -> tuple[Any, ...]:
    """What the run decided before ``cut``: fills, rejections and the position at each bar."""
    return (
        [f for f in outcome.fills if f.time < cut],
        [r for r in outcome.rejected if r.time < cut],
        outcome.in_market[:bars],
        outcome.equity_curve[:bars],
    )


def _assert_no_lookahead(make_strategy: Any, candles: Sequence[Candle]) -> None:
    config = make_config(fee_rate="0.001", slippage_bps="5", n_candles=len(candles))
    full = run_backtest(config, candles, MARKET, make_strategy())
    assert full.fills, "the series must make the strategy trade, or the test proves nothing"
    for removed in TRUNCATIONS:
        kept = len(candles) - removed
        cut = candles[kept].open_time
        short = run_backtest(config, candles[:kept], MARKET, make_strategy())
        assert _prefix(full, cut, kept) == _prefix(short, cut, kept), (
            f"decisions before the last {removed} candles changed when they were removed"
        )


CASES = [
    pytest.param(cls, params, id=f"{cls.TYPE_KEY}-{_variant_id(params)}")
    for cls in AVAILABLE_STRATEGIES
    for params in _params_variants(cls)
]


@pytest.mark.parametrize(("strategy_cls", "params"), CASES)
def test_catalog_strategies_do_not_look_ahead(
    strategy_cls: type[Strategy[Any]], params: dict[str, Any]
) -> None:
    n = SLOW_N_CANDLES if strategy_cls.TYPE_KEY in SLOW_STRATEGIES else N_CANDLES
    candles = make_candles(_series(n))
    _assert_no_lookahead(lambda: strategy_cls.from_params(params), candles)


class _FullSampleStrategy(Strategy[int]):
    """Control with Chan's classic leak: a threshold fitted on the *whole* sample.

    It buys below the mean of every close in the data set and sells above it, the way a
    regression or a z-score fitted on all the data would. Removing the last candles moves the
    mean, so past decisions change: the truncation test must catch it.
    """

    TYPE_KEY: ClassVar[str] = "full_sample_mean"
    NAME: ClassVar[str] = "Full-sample mean"
    DESCRIPTION: ClassVar[str] = "Leaks the future on purpose."
    PARAMETERS: ClassVar[tuple[Any, ...]] = ()
    STYLE: ClassVar[StrategyStyle] = StrategyStyle.MEAN_REVERSION

    def __init__(self, data: Sequence[Candle] = ()) -> None:
        closes = [c.close for c in data]
        self.mean = sum(closes, Decimal(0)) / len(closes) if closes else Decimal(0)

    @classmethod
    def from_params(cls, params: Mapping[str, Any]) -> Self:
        return cls()

    def initial_state(self) -> int:
        return 0

    def evaluate(self, ctx: StrategyContext, state: int) -> StrategyResult[int]:
        close = ctx.candle.close
        if close < self.mean and ctx.position_quantity <= 0:
            return StrategyResult((Signal(Side.BUY, ctx.symbol, SignalKind.ENTRY, "cheap"),), state)
        if close > self.mean and ctx.position_quantity > 0:
            return StrategyResult((Signal(Side.SELL, ctx.symbol, SignalKind.EXIT, "dear"),), state)
        return StrategyResult((), state)

    def serialize_state(self, state: int) -> dict[str, Any]:
        return {}

    def deserialize_state(self, raw: dict[str, Any]) -> int:
        return 0


def test_truncation_test_catches_a_full_sample_leak() -> None:
    candles = make_candles(_series())
    config = make_config(fee_rate="0.001", n_candles=len(candles))
    full = run_backtest(config, candles, MARKET, _FullSampleStrategy(candles))
    assert full.fills
    leaked = False
    for removed in TRUNCATIONS:
        kept = len(candles) - removed
        cut = candles[kept].open_time
        short = run_backtest(config, candles[:kept], MARKET, _FullSampleStrategy(candles[:kept]))
        leaked = leaked or _prefix(full, cut, kept) != _prefix(short, cut, kept)
    assert leaked, "the truncation test failed to detect a full-sample statistic"
