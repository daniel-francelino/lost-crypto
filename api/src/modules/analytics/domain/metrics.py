"""Performance metrics as pure functions. Always net of fees."""

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from modules.analytics.domain import risk_ratios
from modules.backtesting.domain.models import EquityPoint
from modules.execution.domain.orders import Fill
from modules.strategies.domain.types import Side

_PCT = Decimal(100)
_Q_PCT = Decimal("0.0001")
_Q_MONEY = Decimal("0.00000001")
_Q_RATIO = Decimal("0.0001")


@dataclass(frozen=True, slots=True)
class Metrics:
    initial_capital: Decimal
    final_equity: Decimal
    net_pnl: Decimal
    total_return_pct: Decimal
    buy_and_hold_return_pct: Decimal  # benchmark: buy at the first open, hold to the last close
    max_drawdown_pct: Decimal
    fees_paid: Decimal
    fills: int
    round_trips: int
    win_rate_pct: Decimal | None
    profit_factor: Decimal | None  # gross profit / gross loss; None when there are no losses
    avg_trade_pnl: Decimal | None
    open_position: bool
    rejected_signals: int
    # Added for book 1 ch. 2 (O1, O2). Optional: runs stored before them do not have them.
    # Risk-adjusted ratios, annualised with 365 days (see ``risk_ratios``); None on short samples.
    sharpe_ratio: Decimal | None = None
    sortino_ratio: Decimal | None = None
    information_ratio: Decimal | None = None  # vs. holding the same asset
    annualized_return_pct: Decimal | None = None
    annualized_volatility_pct: Decimal | None = None
    exposure_pct: Decimal | None = None  # share of bars with an open position
    return_periods: int | None = None  # sample size behind the ratios
    return_gaps: int | None = None  # steps skipped because the curve had a hole
    annualization_factor: Decimal | None = None
    # Drawdown duration: from the peak until equity is back at it (or the end, if still open).
    max_drawdown_duration_seconds: int | None = None
    max_drawdown_duration_bars: int | None = None
    max_drawdown_peak_at: datetime | None = None  # peak and trough of the deepest drawdown
    max_drawdown_trough_at: datetime | None = None
    current_drawdown_pct: Decimal | None = None
    drawdown_open: bool | None = None  # the curve ends below its high watermark

    def to_dict(self) -> dict[str, Any]:
        def plain(value: Any) -> Any:
            if isinstance(value, Decimal):
                return str(value)
            if isinstance(value, datetime):
                return value.isoformat()
            return value

        return {k: plain(v) for k, v in asdict(self).items()}


@dataclass(frozen=True, slots=True)
class DrawdownStats:
    max_drawdown_pct: Decimal
    max_duration_seconds: int
    max_duration_bars: int
    peak_at: datetime | None
    trough_at: datetime | None
    current_drawdown_pct: Decimal
    open: bool


def drawdown_stats(equity_curve: Sequence[EquityPoint]) -> DrawdownStats:
    """Depth and duration of drawdowns (Chan p. 21), in one pass over the curve.

    The duration runs from a peak until equity is back at it; a drawdown still open at the end
    counts up to the last point and is reported as open, not recovered. The deepest and the
    longest drawdown are often different ones.
    """
    if not equity_curve:
        return DrawdownStats(Decimal(0), 0, 0, None, None, Decimal(0), False)
    peak = equity_curve[0].equity
    peak_index = 0
    worst = Decimal(0)
    worst_peak_at: datetime | None = None
    worst_trough_at: datetime | None = None
    longest = timedelta(0)
    longest_bars = 0
    for index, point in enumerate(equity_curve):
        if point.equity >= peak:
            peak, peak_index = point.equity, index
            continue
        if peak > 0:
            depth = (peak - point.equity) / peak
            if depth > worst:
                worst = depth
                worst_peak_at = equity_curve[peak_index].time
                worst_trough_at = point.time
        span = point.time - equity_curve[peak_index].time
        if span > longest:
            longest, longest_bars = span, index - peak_index
    last = equity_curve[-1].equity
    current = (peak - last) / peak if peak > 0 and last < peak else Decimal(0)
    return DrawdownStats(
        max_drawdown_pct=worst * _PCT,
        max_duration_seconds=int(longest.total_seconds()),
        max_duration_bars=longest_bars,
        peak_at=worst_peak_at,
        trough_at=worst_trough_at,
        current_drawdown_pct=current * _PCT,
        open=last < peak,
    )


def round_trip_pnls(fills: Sequence[Fill]) -> list[Decimal]:
    """PnL of each completed BUY→SELL pair, net of both fees."""
    pnls: list[Decimal] = []
    entry_cost: Decimal | None = None
    for fill in fills:
        if fill.side is Side.BUY:
            entry_cost = fill.notional + fill.total_fee
        elif entry_cost is not None:
            pnls.append(fill.notional - fill.total_fee - entry_cost)
            entry_cost = None
    return pnls


def compute_metrics(
    *,
    initial_capital: Decimal,
    equity_curve: Sequence[EquityPoint],
    fills: Sequence[Fill],
    first_price: Decimal,
    last_price: Decimal,
    open_position: bool,
    rejected_signals: int,
    bar: timedelta | None = None,
    benchmark_prices: Sequence[Decimal] | None = None,
    in_market: Sequence[bool] | None = None,
) -> Metrics:
    """``bar`` (the candle duration) enables the annualised ratios; ``benchmark_prices`` and
    ``in_market`` must be aligned with ``equity_curve`` (one entry per point)."""
    final_equity = equity_curve[-1].equity if equity_curve else initial_capital
    net_pnl = final_equity - initial_capital
    pnls = round_trip_pnls(fills)
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    gross_loss = -sum(losses, Decimal(0))
    drawdown = drawdown_stats(equity_curve)
    ratios = _ratio_fields(equity_curve, bar, benchmark_prices)
    exposure = (
        (Decimal(sum(1 for held in in_market if held)) / len(in_market) * _PCT).quantize(_Q_PCT)
        if in_market
        else None
    )

    return Metrics(
        initial_capital=initial_capital,
        final_equity=final_equity.quantize(_Q_MONEY),
        net_pnl=net_pnl.quantize(_Q_MONEY),
        total_return_pct=(net_pnl / initial_capital * _PCT).quantize(_Q_PCT),
        buy_and_hold_return_pct=((last_price / first_price - 1) * _PCT).quantize(_Q_PCT),
        max_drawdown_pct=drawdown.max_drawdown_pct.quantize(_Q_PCT),
        fees_paid=sum((f.total_fee for f in fills), Decimal(0)).quantize(_Q_MONEY),
        fills=len(fills),
        round_trips=len(pnls),
        win_rate_pct=(Decimal(len(wins)) / len(pnls) * _PCT).quantize(_Q_PCT) if pnls else None,
        profit_factor=(sum(wins, Decimal(0)) / gross_loss).quantize(_Q_PCT)
        if gross_loss > 0
        else None,
        avg_trade_pnl=(sum(pnls, Decimal(0)) / len(pnls)).quantize(_Q_MONEY) if pnls else None,
        open_position=open_position,
        rejected_signals=rejected_signals,
        exposure_pct=exposure,
        max_drawdown_duration_seconds=drawdown.max_duration_seconds,
        max_drawdown_duration_bars=drawdown.max_duration_bars,
        max_drawdown_peak_at=drawdown.peak_at,
        max_drawdown_trough_at=drawdown.trough_at,
        current_drawdown_pct=drawdown.current_drawdown_pct.quantize(_Q_PCT),
        drawdown_open=drawdown.open,
        **ratios,
    )


def _q(value: Decimal | None) -> Decimal | None:
    return None if value is None else value.quantize(_Q_RATIO)


def _ratio_fields(
    equity_curve: Sequence[EquityPoint],
    bar: timedelta | None,
    benchmark_prices: Sequence[Decimal] | None,
) -> dict[str, Any]:
    if bar is None or len(equity_curve) < 2:
        return {}
    if benchmark_prices is not None and len(benchmark_prices) != len(equity_curve):
        raise ValueError("benchmark_prices must be aligned with the equity curve")
    n_t = risk_ratios.annualization_factor(bar)
    series = risk_ratios.periodic_returns(
        [p.time for p in equity_curve], [p.equity for p in equity_curve], bar, benchmark_prices
    )
    returns = series.returns
    return {
        "sharpe_ratio": _q(risk_ratios.sharpe(returns, n_t)),
        "sortino_ratio": _q(risk_ratios.sortino(returns, n_t)),
        "information_ratio": _q(risk_ratios.information_ratio(returns, series.benchmark, n_t))
        if series.benchmark is not None
        else None,
        "annualized_return_pct": _q(
            risk_ratios.annualized_return_pct(
                equity_curve[0].equity,
                equity_curve[-1].equity,
                equity_curve[-1].time - equity_curve[0].time,
            )
        ),
        "annualized_volatility_pct": _q(risk_ratios.annualized_volatility_pct(returns, n_t)),
        "return_periods": len(returns),
        "return_gaps": series.gaps,
        "annualization_factor": n_t.quantize(_Q_RATIO),
    }
