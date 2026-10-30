from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Integer, Numeric, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base

MONEY = Numeric(38, 18)


class BotRow(Base):
    __tablename__ = "bots"
    __table_args__ = (
        UniqueConstraint("name"),
        CheckConstraint("desired_state IN ('stopped','running','paused')", name="desired_valid"),
        CheckConstraint(
            "observed_state IN ('stopped','running','paused','error')", name="observed_valid"
        ),
        CheckConstraint("mode IN ('paper')", name="mode_valid"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text)
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
    mode: Mapped[str] = mapped_column(Text)
    desired_state: Mapped[str] = mapped_column(Text)
    observed_state: Mapped[str] = mapped_column(Text)
    config_version: Mapped[int] = mapped_column(Integer)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
