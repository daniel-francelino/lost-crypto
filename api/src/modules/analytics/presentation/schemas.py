from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


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
    # Optional: results stored before these metrics existed do not have them (shown as n/a).
    sharpe_ratio: Decimal | None = Field(
        default=None,
        description="Annualised (365 days), risk-free rate 0. Null below 30 returns.",
    )
    sortino_ratio: Decimal | None = None
    information_ratio: Decimal | None = Field(
        default=None, description="Sharpe of the excess return over holding the same asset."
    )
    annualized_return_pct: Decimal | None = Field(
        default=None, description="Geometric; null for spans shorter than 30 days."
    )
    annualized_volatility_pct: Decimal | None = None
    exposure_pct: Decimal | None = Field(
        default=None, description="Share of bars with an open position."
    )
    return_periods: int | None = Field(
        default=None, description="Number of periodic returns behind the ratios."
    )
    return_gaps: int | None = Field(
        default=None, description="Steps skipped because the equity curve had a hole."
    )
    annualization_factor: Decimal | None = None
    max_drawdown_duration_seconds: int | None = Field(
        default=None, description="Longest time from a peak until equity was back at it."
    )
    max_drawdown_duration_bars: int | None = None
    max_drawdown_peak_at: datetime | None = None
    max_drawdown_trough_at: datetime | None = None
    current_drawdown_pct: Decimal | None = None
    drawdown_open: bool | None = Field(
        default=None, description="The curve ends below its high watermark (not recovered)."
    )
