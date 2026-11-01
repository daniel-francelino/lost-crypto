from decimal import Decimal

from pydantic import BaseModel, Field

from modules.risk_management.domain.models import DrawdownAction, RiskLimits


class RiskLimitsIn(BaseModel):
    """A bot's risk limits; also accepted by backtests to size and pause exactly like the bot."""

    max_position_fraction: Decimal = Field(default=Decimal(1), gt=0, le=1)
    max_order_notional: Decimal | None = Field(default=None, gt=0)
    max_daily_loss_pct: Decimal | None = Field(default=Decimal(10), gt=0, le=100)
    max_drawdown_pct: Decimal | None = Field(default=None, gt=0, le=100)
    max_consecutive_losses: int | None = Field(default=None, ge=1)
    max_risk_per_trade_pct: Decimal | None = Field(default=None, gt=0, le=100)
    require_stop_loss: bool = False
    max_candle_range_pct: Decimal | None = Field(default=Decimal(25), gt=0)
    max_order_pct_of_volume: Decimal | None = Field(
        default=None,
        gt=0,
        le=100,
        description="Cap an order at this % of the average traded value of the last 20 "
        "candles (Chan's rule of thumb: ~1% of daily volume, for stocks). Null = off.",
    )

    max_close_jump_pct: Decimal | None = Field(
        default=None,
        gt=0,
        description="Refuse entries when the close moved more than this % from the previous "
        "close (a bad tick often looks like a jump). Exits are never refused. Null = off.",
    )

    drawdown_action: DrawdownAction = Field(
        default=DrawdownAction.PAUSE,
        description="What happens when max_drawdown_pct is breached: `pause` (resume by hand) or "
        "`stop` (ends the session; to start again, reset the portfolio with a reason, which also "
        "starts a new drawdown peak). The position is kept either way.",
    )

    def to_domain(self) -> RiskLimits:
        return RiskLimits(**self.model_dump())

    @classmethod
    def from_domain(cls, limits: RiskLimits) -> "RiskLimitsIn":
        return cls(
            max_position_fraction=limits.max_position_fraction,
            max_order_notional=limits.max_order_notional,
            max_daily_loss_pct=limits.max_daily_loss_pct,
            max_drawdown_pct=limits.max_drawdown_pct,
            max_consecutive_losses=limits.max_consecutive_losses,
            max_risk_per_trade_pct=limits.max_risk_per_trade_pct,
            require_stop_loss=limits.require_stop_loss,
            max_candle_range_pct=limits.max_candle_range_pct,
            max_order_pct_of_volume=limits.max_order_pct_of_volume,
            max_close_jump_pct=limits.max_close_jump_pct,
            drawdown_action=limits.drawdown_action,
        )
