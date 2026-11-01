"""Book 2 ch. 3, O5: refuse entries when the close jumped from the previous close."""

from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest

from factories import MARKET, make_candles, make_config
from modules.backtesting.domain.engine import run_backtest
from modules.backtesting.domain.models import FillTiming
from modules.portfolio.domain.models import PortfolioState
from modules.risk_management.domain.models import (
    InvalidRiskLimits,
    RiskLimits,
    assess_signal,
    close_jump_pct,
    limits_from_dict,
    limits_to_dict,
)
from modules.strategies.domain.types import Side, Signal, SignalKind
from reference_ema_crossover import EmaCrossoverParams, EmaCrossoverStrategy

PRICE = Decimal(100)
LIMITS = RiskLimits(max_close_jump_pct=Decimal(10))


def _signal(side: Side) -> Signal:
    kind = SignalKind.ENTRY if side is Side.BUY else SignalKind.EXIT
    return Signal(side, "BTC/USDT", kind, "test")


def _assess(side: Side = Side.BUY, *, limits: RiskLimits = LIMITS, **kwargs):  # type: ignore[no-untyped-def]
    held = Decimal(1) if side is Side.SELL else Decimal(0)
    portfolio = PortfolioState(uuid4(), Decimal(1000), quantity=held)
    return assess_signal(
        _signal(side),
        portfolio,
        PRICE,
        MARKET,
        fee_rate=Decimal(0),
        slippage_bps=Decimal(0),
        limits=limits,
        kill_switch_active=False,
        **kwargs,
    )


def test_jump_is_the_absolute_percent_move_and_none_without_a_previous_close():
    assert close_jump_pct(Decimal(120), Decimal(100)) == Decimal(20)
    assert close_jump_pct(Decimal(80), Decimal(100)) == Decimal(20)  # drops count too
    assert close_jump_pct(Decimal(100), None) is None
    assert close_jump_pct(Decimal(100), Decimal(0)) is None


def test_an_entry_above_the_limit_is_refused_with_the_reason():
    decision = _assess(close_jump=Decimal(25))
    assert not decision.approved
    assert "close moved 25.0%" in (decision.reason or "") and "suspect data" in decision.reason


def test_an_entry_at_or_below_the_limit_is_accepted():
    assert _assess(close_jump=Decimal(10)).approved
    assert _assess(close_jump=Decimal(3)).approved


def test_exits_are_never_refused_by_a_jump():
    assert _assess(Side.SELL, close_jump=Decimal(90)).approved


def test_off_by_default_and_without_a_previous_close_nothing_changes():
    assert _assess(limits=RiskLimits(), close_jump=Decimal(90)).approved
    assert _assess(close_jump=None).approved


def test_limit_must_be_positive():
    with pytest.raises(InvalidRiskLimits):
        RiskLimits(max_close_jump_pct=Decimal(0))
    with pytest.raises(InvalidRiskLimits):
        RiskLimits(max_close_jump_pct=Decimal(-5))


def test_limit_survives_the_json_round_trip_used_by_backtests_and_change_diffs():
    assert limits_from_dict(limits_to_dict(LIMITS)).max_close_jump_pct == Decimal(10)
    assert limits_from_dict(limits_to_dict(RiskLimits())).max_close_jump_pct is None


def _backtest(limits: RiskLimits, timing: FillTiming):
    closes = [10, 10, 10, 11, 12, 13, 14, 15, 16, 17]
    config = replace(make_config(), risk=limits, fill_timing=timing)
    strategy = EmaCrossoverStrategy(EmaCrossoverParams(2, 3))
    return run_backtest(config, make_candles(closes), MARKET, strategy)


@pytest.mark.parametrize("timing", [FillTiming.NEXT_OPEN, FillTiming.SIGNAL_CLOSE])
def test_backtest_refuses_the_entry_after_a_jump_and_logs_it(timing: FillTiming):
    # the entry candle closes 10 -> 11 (10%): a 5% limit refuses it, a 50% limit does not
    strict = _backtest(RiskLimits(max_close_jump_pct=Decimal(5)), timing)
    loose = _backtest(RiskLimits(max_close_jump_pct=Decimal(50)), timing)
    assert any("close moved" in r.reason for r in strict.rejected)
    assert not any("close moved" in r.reason for r in loose.rejected)
    assert len(loose.fills) >= 1


def test_backtest_without_the_limit_is_unchanged():
    off = _backtest(RiskLimits(), FillTiming.NEXT_OPEN)
    default = _backtest(RiskLimits(max_close_jump_pct=None), FillTiming.NEXT_OPEN)
    assert off.fills == default.fills and not off.rejected
