"""Book 1 ch. 5: fill timing, the bot's risk inside the backtest, the volume cap, parity
classification, execution quality and the divergence checklist."""

import math
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from factories import MARKET, T0, make_candles, make_config
from modules.backtesting.domain.engine import risk_report, run_backtest
from modules.backtesting.domain.models import FillTiming
from modules.execution.domain.orders import (
    Fill,
    Order,
    OrderStatus,
    latency_ms,
    realized_slippage_bps,
)
from modules.portfolio.domain.models import PortfolioState
from modules.risk_management.domain.models import (
    RiskLimits,
    assess_signal,
    average_quote_volume,
    limits_from_dict,
    limits_to_dict,
)
from modules.strategies.domain.ema_crossover import EmaCrossoverParams, EmaCrossoverStrategy
from modules.strategies.domain.types import Side, Signal, SignalKind
from modules.trading.domain.diagnosis import StepState, checklist, execution_quality
from modules.trading.domain.parity import BotSignal, ParityClass, ReplayEvent, compare

H = timedelta(hours=1)
NO_LIMITS = RiskLimits(max_daily_loss_pct=None, max_candle_range_pct=None)


def _strategy() -> EmaCrossoverStrategy:
    return EmaCrossoverStrategy(EmaCrossoverParams(3, 8))


def _wave(n: int = 300) -> list[str]:
    return [str(round(1000 + 150 * math.sin(i / 9) + i * 0.2, 2)) for i in range(n)]


def test_signal_close_fills_at_the_close_of_the_signal_candle() -> None:
    candles = make_candles(_wave())
    config = replace(make_config(), fill_timing=FillTiming.SIGNAL_CLOSE)
    outcome = run_backtest(config, candles, MARKET, _strategy())
    closes = {c.close_time: c.close for c in candles}
    assert outcome.fills
    assert all(f.time in closes and f.price == closes[f.time] for f in outcome.fills)
    assert outcome.unfilled_signals == 0
    assert outcome.signals  # emitted signals are recorded for the parity check


def test_risk_limits_that_never_act_change_nothing() -> None:
    candles = make_candles(_wave())
    plain = run_backtest(make_config(fee_rate="0.001"), candles, MARKET, _strategy())
    guarded = run_backtest(
        replace(make_config(fee_rate="0.001"), risk=NO_LIMITS), candles, MARKET, _strategy()
    )
    assert guarded.fills == plain.fills
    assert guarded.equity_curve == plain.equity_curve
    assert (guarded.sizing, plain.sizing) == ("risk_limits", "all_in")


def test_the_risk_guard_sizes_and_pauses_like_the_bot() -> None:
    candles = make_candles(_wave())
    half = replace(NO_LIMITS, max_position_fraction=Decimal("0.5"))
    sized = run_backtest(replace(make_config(), risk=half), candles, MARKET, _strategy())
    full = run_backtest(make_config(), candles, MARKET, _strategy())
    assert sized.fills[0].quantity < full.fills[0].quantity

    falling = make_candles([str(1000 - i * 4 + 30 * math.sin(i / 3)) for i in range(200)])
    tight = replace(NO_LIMITS, max_drawdown_pct=Decimal(2))
    paused = run_backtest(replace(make_config(), risk=tight), falling, MARKET, _strategy())
    assert paused.paused is not None and "drawdown" in paused.paused[1]
    report = risk_report(paused)
    assert report["paused_reason"] == paused.paused[1]
    assert any(reason.startswith("bot paused") for reason in report["refusals"])


def test_trade_from_only_warms_up() -> None:
    candles = make_candles(_wave())
    cut = candles[150].close_time
    outcome = run_backtest(make_config(), candles, MARKET, _strategy(), trade_from=cut)
    assert outcome.fills and all(f.time > cut for f in outcome.fills)


def test_volume_cap_limits_and_refuses() -> None:
    portfolio = PortfolioState(bot_id=uuid4(), cash=Decimal(1000))
    signal = Signal(Side.BUY, "BTC/USDT", SignalKind.ENTRY, "x")
    capped = replace(NO_LIMITS, max_order_pct_of_volume=Decimal(1))
    kwargs = {"fee_rate": Decimal(0), "slippage_bps": Decimal(0), "kill_switch_active": False}
    small = assess_signal(
        signal,
        portfolio,
        Decimal(100),
        MARKET,
        limits=capped,
        avg_quote_volume=Decimal(20_000),
        **kwargs,  # type: ignore[arg-type]
    )
    assert small.approved and small.quantity is not None and small.quantity * 100 <= 200
    tiny = assess_signal(
        signal,
        portfolio,
        Decimal(100),
        MARKET,
        limits=capped,
        avg_quote_volume=Decimal(500),
        **kwargs,  # type: ignore[arg-type]
    )
    assert not tiny.approved and "average volume" in (tiny.reason or "")
    assert average_quote_volume([Decimal(1)] * 4) is None
    assert average_quote_volume([Decimal(2)] * 5) == Decimal(2)


def test_risk_limits_round_trip() -> None:
    limits = RiskLimits(max_consecutive_losses=3, max_order_pct_of_volume=Decimal("1.5"))
    assert limits_from_dict(limits_to_dict(limits)) == limits


def _signal(
    hour: int,
    side: Side,
    decision: str = "approved",
    reason: str | None = None,
    price: str | None = "100",
) -> BotSignal:
    return BotSignal(
        T0 + hour * H, side, "x", decision, reason, None if price is None else Decimal(price)
    )


def _event(hour: int, side: Side, executed: bool = True, price: str = "100") -> ReplayEvent:
    return ReplayEvent(
        T0 + hour * H,
        side,
        executed,
        Decimal(price) if executed else None,
        None if executed else "refused",
    )


def test_parity_classification() -> None:
    times = {T0 + i * H for i in range(10)}
    diffs = compare(
        [
            _signal(1, Side.BUY),
            _signal(2, Side.SELL, price="101"),
            _signal(3, Side.BUY, "discarded_stale"),
            _signal(4, Side.BUY, "rejected", "a stop-loss is required"),
            _signal(5, Side.BUY),
            _signal(20, Side.BUY),
        ],
        [
            _event(1, Side.BUY),
            _event(2, Side.SELL, price="100.5"),
            _event(3, Side.BUY),
            _event(4, Side.BUY),
            _event(6, Side.SELL),
        ],
        times,
    )
    kinds = {(d.bar_time, d.side): d.kind for d in diffs}
    assert kinds[(T0 + H, Side.BUY)] is ParityClass.MATCH
    assert kinds[(T0 + 2 * H, Side.SELL)] is ParityClass.COST
    assert kinds[(T0 + 3 * H, Side.BUY)] is ParityClass.OPERATIONAL
    assert kinds[(T0 + 4 * H, Side.BUY)] is ParityClass.RISK
    assert kinds[(T0 + 5 * H, Side.BUY)] is ParityClass.UNEXPLAINED  # bot only
    assert kinds[(T0 + 6 * H, Side.SELL)] is ParityClass.UNEXPLAINED  # replay only
    assert kinds[(T0 + 20 * H, Side.BUY)] is ParityClass.DATA  # candle never stored


def _order(side: Side, ref: str, fill: str, seconds: int, kind: str = "market") -> Order:
    created = datetime(2026, 1, 1, tzinfo=UTC)
    order = Order(
        uuid4(),
        uuid4(),
        uuid4(),
        "c",
        "BTC/USDT",
        side,
        Decimal(1),
        created,
        created,
        order_type=kind,
        reference_price=Decimal(ref),
    )
    order.submit()
    order.apply_fill(
        Fill(created + timedelta(seconds=seconds), side, Decimal(1), Decimal(fill), Decimal(0))
    )
    return order


def test_realized_slippage_and_latency() -> None:
    buy = _order(Side.BUY, "100", "100.1", 2)
    sell = _order(Side.SELL, "100", "99.95", 1)
    assert realized_slippage_bps(buy) == Decimal(10)
    assert realized_slippage_bps(sell) == Decimal(5)
    assert latency_ms(buy) == 2000 and buy.status is OrderStatus.FILLED

    quality = execution_quality([buy, sell], Decimal(5))
    assert quality["by_type"]["market"]["slippage_bps"]["mean"] == "7.50"
    assert quality["above_configured"] is True
    assert execution_quality([sell], Decimal(5))["above_configured"] is False


def test_divergence_checklist_follows_the_book() -> None:
    parity = {
        "counts": {"match": 8, "unexplained": 0, "cost": 1},
        "replay_return_pct": "4",
        "simplified_return_pct": "-1",
    }
    steps = checklist(parity, execution_quality([], Decimal(5)), 2, (Decimal(-9), Decimal(-3)))
    states = {s.key: s.state for s in steps}
    assert [s.key for s in steps] == ["bugs", "trades", "costs", "liquidity", "snooping", "regime"]
    assert states["bugs"] is StepState.OK
    assert states["trades"] is StepState.ATTENTION
    assert states["costs"] is StepState.NO_DATA
    assert states["liquidity"] is StepState.ATTENTION
    assert states["snooping"] is StepState.ATTENTION  # collapses without the tuning
    assert states["regime"] is StepState.ATTENTION
    assert {s.state for s in checklist(None, {}, 0, None)} <= {StepState.NO_DATA, StepState.OK}


def test_a_daily_loss_pause_can_lift_at_the_next_utc_day() -> None:
    candles = make_candles(_wave())
    one_percent = replace(NO_LIMITS, max_daily_loss_pct=Decimal(1))
    stays = run_backtest(replace(make_config(), risk=one_percent), candles, MARKET, _strategy())
    lifts = run_backtest(
        replace(make_config(), risk=one_percent, resume_daily_pause=True),
        candles,
        MARKET,
        _strategy(),
    )
    assert stays.paused is not None and stays.paused[1] == "daily loss limit breached"
    assert len(lifts.fills) > len(stays.fills)
    assert len(lifts.rejected) < len(stays.rejected)


def test_resuming_daily_pauses_never_lifts_a_drawdown_pause() -> None:
    falling = make_candles([str(1000 - i * 4 + 30 * math.sin(i / 3)) for i in range(200)])
    tight = replace(NO_LIMITS, max_drawdown_pct=Decimal(2))
    outcome = run_backtest(
        replace(make_config(), risk=tight, resume_daily_pause=True), falling, MARKET, _strategy()
    )
    assert outcome.paused is not None and "drawdown" in outcome.paused[1]
