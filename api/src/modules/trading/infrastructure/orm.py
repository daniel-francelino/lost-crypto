from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base


class TradingSessionRow(Base):
    __tablename__ = "trading_sessions"
    __table_args__ = (
        CheckConstraint("status IN ('active','ended')", name="status_valid"),
        # A bot has at most one active session: the single-writer guarantee.
        Index(
            "uq_trading_sessions_active_bot",
            "bot_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    bot_id: Mapped[UUID] = mapped_column(ForeignKey("bots.id"))
    config_version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    strategy_state: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    last_processed_bar_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
