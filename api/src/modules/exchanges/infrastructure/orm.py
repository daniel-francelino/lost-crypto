from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base


class ExchangeConnectionRow(Base):
    __tablename__ = "exchange_connections"
    __table_args__ = (
        UniqueConstraint("exchange", "environment", "label"),
        CheckConstraint("environment IN ('testnet','live')", name="environment_valid"),
        CheckConstraint("status IN ('active','disabled','invalid','pending')", name="status_valid"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    exchange: Mapped[str] = mapped_column(Text)
    environment: Mapped[str] = mapped_column(Text)
    label: Mapped[str] = mapped_column(Text)
    credentials_encrypted: Mapped[bytes] = mapped_column(LargeBinary)  # Fernet token
    key_id: Mapped[str] = mapped_column(Text)  # which master key sealed it
    api_key_hint: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReconciliationRunRow(Base):
    __tablename__ = "reconciliation_runs"
    __table_args__ = (
        CheckConstraint("status IN ('ok','mismatch')", name="status_valid"),
        Index("ix_reconciliation_runs_connection_id_started_at", "connection_id", "started_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    connection_id: Mapped[UUID] = mapped_column(ForeignKey("exchange_connections.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB)
