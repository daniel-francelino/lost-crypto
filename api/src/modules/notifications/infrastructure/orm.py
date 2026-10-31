from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base


class AlertRow(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        CheckConstraint("severity IN ('warning','critical')", name="severity_valid"),
        # At most one open alert per episode key.
        Index(
            "uq_alerts_open_dedupe_key",
            "dedupe_key",
            unique=True,
            postgresql_where=text("resolved_at IS NULL"),
        ),
        Index("ix_alerts_opened_at", "opened_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(Text)
    dedupe_key: Mapped[str] = mapped_column(Text)
    message: Mapped[str] = mapped_column(Text)
    bot_id: Mapped[UUID | None] = mapped_column(nullable=True)  # no FK: alerts outlive bots
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
