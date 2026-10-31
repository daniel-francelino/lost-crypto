from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base

MONEY = Numeric(38, 18)


class LiveApprovalRow(Base):
    __tablename__ = "live_approvals"
    __table_args__ = (Index("ix_live_approvals_bot_id_token_hash", "bot_id", "token_hash"),)

    id: Mapped[UUID] = mapped_column(primary_key=True)
    bot_id: Mapped[UUID] = mapped_column(ForeignKey("bots.id"))
    config_version: Mapped[int] = mapped_column(Integer)
    token_hash: Mapped[str] = mapped_column(Text)  # sha256 of the token, never the token
    created_by: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BotRow(Base):
    __tablename__ = "bots"
    __table_args__ = (
        UniqueConstraint("name"),
        CheckConstraint("desired_state IN ('stopped','running','paused')", name="desired_valid"),
        CheckConstraint(
            "observed_state IN ('stopped','running','paused','error')", name="observed_valid"
        ),
        CheckConstraint("mode IN ('paper','testnet','live')", name="mode_valid"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    exchange: Mapped[str] = mapped_column(Text, server_default="binance")
    exchange_connection_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("exchange_connections.id"), nullable=True
    )
    strategy_type: Mapped[str] = mapped_column(Text)
    strategy_params: Mapped[dict[str, Any]] = mapped_column(JSONB)
    symbol: Mapped[str] = mapped_column(Text)
    timeframe: Mapped[str] = mapped_column(Text)
    initial_capital: Mapped[Decimal] = mapped_column(MONEY)
    fee_rate: Mapped[Decimal] = mapped_column(MONEY)
    slippage_bps: Mapped[Decimal] = mapped_column(MONEY)
    max_position_fraction: Mapped[Decimal] = mapped_column(MONEY)
    max_order_notional: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    max_daily_loss_pct: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    max_drawdown_pct: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    max_consecutive_losses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_risk_per_trade_pct: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    require_stop_loss: Mapped[bool] = mapped_column(Boolean, server_default="false")
    max_candle_range_pct: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    mode: Mapped[str] = mapped_column(Text)
    desired_state: Mapped[str] = mapped_column(Text)
    observed_state: Mapped[str] = mapped_column(Text)
    config_version: Mapped[int] = mapped_column(Integer)
    live_approved_config_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    live_approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
