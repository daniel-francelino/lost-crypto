from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base

MONEY = Numeric(38, 18)


class CandleRow(Base):
    __tablename__ = "candles"

    exchange: Mapped[str] = mapped_column(Text, primary_key=True)
    symbol: Mapped[str] = mapped_column(Text, primary_key=True)
    timeframe: Mapped[str] = mapped_column(Text, primary_key=True)
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    open: Mapped[Decimal] = mapped_column(MONEY)
    high: Mapped[Decimal] = mapped_column(MONEY)
    low: Mapped[Decimal] = mapped_column(MONEY)
    close: Mapped[Decimal] = mapped_column(MONEY)
    volume: Mapped[Decimal] = mapped_column(MONEY)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PerpetualMarkCandleRow(Base):
    __tablename__ = "perpetual_mark_candles"

    exchange: Mapped[str] = mapped_column(Text, primary_key=True)
    symbol: Mapped[str] = mapped_column(Text, primary_key=True)
    timeframe: Mapped[str] = mapped_column(Text, primary_key=True)
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    open: Mapped[Decimal] = mapped_column(MONEY)
    high: Mapped[Decimal] = mapped_column(MONEY)
    low: Mapped[Decimal] = mapped_column(MONEY)
    close: Mapped[Decimal] = mapped_column(MONEY)
    volume: Mapped[Decimal] = mapped_column(MONEY)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PerpetualFundingRateRow(Base):
    __tablename__ = "perpetual_funding_rates"
    __table_args__ = (
        CheckConstraint("rate_type IN ('regular', 'special')", name="rate_type_valid"),
    )

    exchange: Mapped[str] = mapped_column(Text, primary_key=True)
    symbol: Mapped[str] = mapped_column(Text, primary_key=True)
    funding_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    rate_type: Mapped[str] = mapped_column(Text, primary_key=True, server_default="regular")
    rate: Mapped[Decimal] = mapped_column(MONEY)
    mark_price: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class CandleImportJobRow(Base):
    __tablename__ = "candle_import_jobs"
    __table_args__ = (
        CheckConstraint("status IN ('queued','running','completed','failed')", name="status_valid"),
        Index("ix_candle_import_jobs_status_created_at", "status", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    exchange: Mapped[str] = mapped_column(Text)
    symbol: Mapped[str] = mapped_column(Text)
    timeframe: Mapped[str] = mapped_column(Text)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text)
    candles_imported: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    candles_rejected: Mapped[int] = mapped_column(Integer, server_default="0")
    candles_changed: Mapped[int] = mapped_column(Integer, server_default="0")
    rejection_samples: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)


class ExchangeListingRow(Base):
    """Point-in-time record of which pairs an exchange listed (book 1 ch. 3, O10)."""

    __tablename__ = "exchange_listings"

    exchange: Mapped[str] = mapped_column(Text, primary_key=True)
    symbol: Mapped[str] = mapped_column(Text, primary_key=True)
    status: Mapped[str] = mapped_column(Text)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    delisted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RegimeBreakRow(Base):
    """A structural break named by the operator (book 2 ch. 5). Never edited, only deleted."""

    __tablename__ = "regime_breaks"
    __table_args__ = (UniqueConstraint("name", "occurred_at", name="uq_regime_breaks_name_at"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    exchange: Mapped[str | None] = mapped_column(Text, nullable=True)
    symbol: Mapped[str | None] = mapped_column(Text, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
