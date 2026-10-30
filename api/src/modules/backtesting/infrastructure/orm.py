from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
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


class BacktestSweepRow(Base):
    __tablename__ = "backtest_sweeps"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    strategy_type: Mapped[str] = mapped_column(Text)
    grid: Mapped[dict[str, Any]] = mapped_column(JSONB)
    skipped: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    run_count: Mapped[int] = mapped_column(Integer)


class BacktestRunRow(Base):
    __tablename__ = "backtest_runs"
    __table_args__ = (
        CheckConstraint("status IN ('queued','running','completed','failed')", name="status_valid"),
        Index("ix_backtest_runs_status_created_at", "status", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(Text)
    exchange: Mapped[str] = mapped_column(Text)
    symbol: Mapped[str] = mapped_column(Text)
    timeframe: Mapped[str] = mapped_column(Text)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    initial_capital: Mapped[Decimal] = mapped_column(MONEY)
    fee_rate: Mapped[Decimal] = mapped_column(MONEY)
    slippage_bps: Mapped[Decimal] = mapped_column(MONEY)
    seed: Mapped[int] = mapped_column(Integer)
    test_fraction: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    sweep_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("backtest_sweeps.id"), nullable=True
    )
    strategy_type: Mapped[str] = mapped_column(Text)
    strategy_params: Mapped[dict[str, Any]] = mapped_column(JSONB)
    market_info: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    data_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    candles_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    segments: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    equity_curve: Mapped[list[list[str]] | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BacktestTradeRow(Base):
    __tablename__ = "backtest_trades"
    __table_args__ = (UniqueConstraint("run_id", "seq"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("backtest_runs.id", ondelete="CASCADE"))
    seq: Mapped[int] = mapped_column(Integer)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    side: Mapped[str] = mapped_column(Text)
    quantity: Mapped[Decimal] = mapped_column(MONEY)
    price: Mapped[Decimal] = mapped_column(MONEY)
    fee: Mapped[Decimal] = mapped_column(MONEY)
