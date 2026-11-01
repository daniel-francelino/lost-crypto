"""Periods, cost ladder and the new config fields (book 1 ch. 2, O4, O5, O7)."""

import math
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from factories import MARKET, make_candles, make_config
from modules.analytics.domain.metrics import compute_metrics
from modules.backtesting.domain.cost_ladder import MULTIPLIERS, break_even, run_cost_ladder
from modules.backtesting.domain.engine import run_backtest
from modules.backtesting.domain.models import InvalidBacktestConfig
from modules.backtesting.domain.periods import compute_periods
from modules.market_data.domain.models import Timeframe
from modules.strategies.domain.ema_crossover import EmaCrossoverParams, EmaCrossoverStrategy


def _strategy() -> EmaCrossoverStrategy:
    return EmaCrossoverStrategy(EmaCrossoverParams(3, 8))


def _wave(n: int, period: float = 15.0) -> list[str]:
    return [str(round(1000 + 200 * math.sin(i / period) + i * 0.3, 2)) for i in range(n)]


def test_engine_reports_when_a_position_was_held() -> None:
    candles = make_candles(_wave(200))
    outcome = run_backtest(make_config(), candles, MARKET, _strategy())
    assert len(outcome.in_market) == len(outcome.equity_curve)
    assert any(outcome.in_market) and not all(outcome.in_market)


def test_periods_split_by_year_and_compound_to_the_total() -> None:
    start = datetime(2023, 3, 1, tzinfo=UTC)
    candles = make_candles(_wave(900), timeframe=Timeframe.D1, start=start)
    config = replace(make_config(fee_rate="0.001"), timeframe=Timeframe.D1)
    outcome = run_backtest(config, candles, MARKET, _strategy())
    result = compute_periods(config, candles, outcome)

    assert result is not None and result["granularity"] == "year"
    assert [p["label"] for p in result["periods"]] == ["2023", "2024", "2025"]
    assert sum(p["candles"] for p in result["periods"]) == len(candles)
    total = Decimal(1)
    for period in result["periods"]:
        total *= 1 + Decimal(period["metrics"]["total_return_pct"]) / 100
    final = outcome.equity_curve[-1].equity / config.initial_capital
    assert abs(total - final) < Decimal("0.00001")
    fills = sum(p["metrics"]["fills"] for p in result["periods"])
    assert fills == len(outcome.fills)


def test_short_runs_are_split_by_quarter() -> None:
    candles = make_candles(_wave(24 * 200))  # 200 days of hourly candles from 2024-01-01
    outcome = run_backtest(make_config(), candles, MARKET, _strategy())
    result = compute_periods(make_config(), candles, outcome)
    assert result is not None and result["granularity"] == "quarter"
    assert [p["label"] for p in result["periods"]] == ["2024-T1", "2024-T2", "2024-T3"]


def test_period_with_a_regime_break_shows_opposite_signs() -> None:
    up = [str(1000 + i) for i in range(366)]  # 2024: steady rise
    down = [str(1366 - i) for i in range(1, 366)]  # 2025: steady fall
    start = datetime(2024, 1, 1, tzinfo=UTC)
    candles = make_candles(up + down, timeframe=Timeframe.D1, start=start)
    config = replace(make_config(), timeframe=Timeframe.D1)
    outcome = run_backtest(config, candles, MARKET, _strategy())
    result = compute_periods(config, candles, outcome)
    assert result is not None
    bh = [Decimal(p["metrics"]["buy_and_hold_return_pct"]) for p in result["periods"]]
    assert bh[0] > 0 > bh[1]


def test_cost_ladder_level_one_equals_the_main_run() -> None:
    candles = make_candles(_wave(400))
    config = replace(make_config(fee_rate="0.001", slippage_bps="5"), cost_sensitivity=True)
    ladder = run_cost_ladder(config, candles, MARKET, _strategy)

    outcome = run_backtest(config, candles, MARKET, _strategy())
    main = compute_metrics(
        initial_capital=config.initial_capital,
        equity_curve=outcome.equity_curve,
        fills=outcome.fills,
        first_price=outcome.first_price,
        last_price=outcome.last_price,
        open_position=outcome.final_quantity > 0,
        rejected_signals=len(outcome.rejected),
    )
    levels = {Decimal(level["multiplier"]): level for level in ladder["levels"]}
    assert list(levels) == list(MULTIPLIERS)
    assert Decimal(levels[Decimal(1)]["net_pnl"]) == main.net_pnl
    assert Decimal(levels[Decimal(0)]["fees_paid"]) == 0
    assert Decimal(levels[Decimal(3)]["cost_per_side_bps"]) == Decimal(45)  # 3 x (10 + 5)
    assert Decimal(levels[Decimal(0)]["net_pnl"]) > Decimal(levels[Decimal(3)]["net_pnl"])


def _levels(*pnls: str) -> list[dict[str, str]]:
    return [{"multiplier": str(m), "net_pnl": p} for m, p in zip(MULTIPLIERS, pnls, strict=True)]


def test_break_even_is_interpolated_where_pnl_changes_sign() -> None:
    status, multiplier = break_even(_levels("100", "60", "20", "-20", "-60", "-140"))
    assert status == "found" and multiplier == Decimal("1.25")  # halfway between 1 and 1.5
    assert break_even(_levels("-1", "-2", "-3", "-4", "-5", "-6")) == ("never_profitable", None)
    assert break_even(_levels("9", "8", "7", "6", "5", "4")) == ("above_max", None)


def test_new_config_fields_are_validated() -> None:
    base = make_config(fee_rate="0.001")
    with pytest.raises(InvalidBacktestConfig):
        replace(make_config(), cost_sensitivity=True)  # zero costs: nothing to scale
    with pytest.raises(InvalidBacktestConfig):
        replace(base, fee_rate=Decimal("0.4"), cost_sensitivity=True)  # 3x would be >= 100%
    for bad in ({"max_drawdown_tolerance_pct": Decimal(0)}, {"max_drawdown_tolerance_days": 0}):
        with pytest.raises(InvalidBacktestConfig):
            replace(base, **bad)  # type: ignore[arg-type]
    ok = replace(base, max_drawdown_tolerance_pct=Decimal(20), max_drawdown_tolerance_days=60)
    assert ok.max_drawdown_tolerance_days == 60
