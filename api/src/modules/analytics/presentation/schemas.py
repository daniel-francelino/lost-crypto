from decimal import Decimal

from pydantic import BaseModel


class MetricsOut(BaseModel):
    initial_capital: Decimal
    final_equity: Decimal
    net_pnl: Decimal
    total_return_pct: Decimal
    buy_and_hold_return_pct: Decimal
    max_drawdown_pct: Decimal
    fees_paid: Decimal
    fills: int
    round_trips: int
    win_rate_pct: Decimal | None
    profit_factor: Decimal | None
    avg_trade_pnl: Decimal | None
    open_position: bool
    rejected_signals: int
