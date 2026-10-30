"""Performance metrics as pure functions. Always net of fees."""

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any

from modules.backtesting.domain.models import EquityPoint
from modules.execution.domain.orders import Fill
from modules.strategies.domain.types import Side

_PCT = Decimal(100)
_Q_PCT = Decimal("0.0001")
_Q_MONEY = Decimal("0.00000001")


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

    def to_dict(self) -> dict[str, Any]:
        return {k: (str(v) if isinstance(v, Decimal) else v) for k, v in asdict(self).items()}


def max_drawdown_pct(equity_curve: Sequence[EquityPoint]) -> Decimal:
    peak = Decimal(0)
    worst = Decimal(0)
    for point in equity_curve:
        peak = max(peak, point.equity)
        if peak > 0:
            worst = max(worst, (peak - point.equity) / peak)
    return worst * _PCT


def round_trip_pnls(fills: Sequence[Fill]) -> list[Decimal]:
    """PnL of each completed BUY→SELL pair, net of both fees."""
    pnls: list[Decimal] = []
    entry_cost: Decimal | None = None
    for fill in fills:
        if fill.side is Side.BUY:
            entry_cost = fill.notional + fill.fee
        elif entry_cost is not None:
            pnls.append(fill.notional - fill.fee - entry_cost)
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
) -> Metrics:
    final_equity = equity_curve[-1].equity if equity_curve else initial_capital
    net_pnl = final_equity - initial_capital
    pnls = round_trip_pnls(fills)
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    gross_loss = -sum(losses, Decimal(0))

    return Metrics(
        initial_capital=initial_capital,
        final_equity=final_equity.quantize(_Q_MONEY),
        net_pnl=net_pnl.quantize(_Q_MONEY),
        total_return_pct=(net_pnl / initial_capital * _PCT).quantize(_Q_PCT),
        buy_and_hold_return_pct=((last_price / first_price - 1) * _PCT).quantize(_Q_PCT),
        max_drawdown_pct=max_drawdown_pct(equity_curve).quantize(_Q_PCT),
        fees_paid=sum((f.fee for f in fills), Decimal(0)).quantize(_Q_MONEY),
        fills=len(fills),
        round_trips=len(pnls),
        win_rate_pct=(Decimal(len(wins)) / len(pnls) * _PCT).quantize(_Q_PCT) if pnls else None,
        profit_factor=(sum(wins, Decimal(0)) / gross_loss).quantize(_Q_PCT)
        if gross_loss > 0
        else None,
        avg_trade_pnl=(sum(pnls, Decimal(0)) / len(pnls)).quantize(_Q_MONEY) if pnls else None,
        open_position=open_position,
        rejected_signals=rejected_signals,
    )
