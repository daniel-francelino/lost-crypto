from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base

MONEY = Numeric(38, 18)


class BotPortfolioRow(Base):
    """Virtual portfolio of a bot (cash + one position). Simplified from the balances/positions
    split of the conceptual model, which suffices for single-symbol spot bots."""

    __tablename__ = "bot_portfolios"

    bot_id: Mapped[UUID] = mapped_column(ForeignKey("bots.id"), primary_key=True)
    cash: Mapped[Decimal] = mapped_column(MONEY)
    quantity: Mapped[Decimal] = mapped_column(MONEY)
    avg_entry_price: Mapped[Decimal] = mapped_column(MONEY)
    realized_pnl: Mapped[Decimal] = mapped_column(MONEY)
    fees_paid: Mapped[Decimal] = mapped_column(MONEY)
    stop_price: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    take_profit_price: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    reserved_cash: Mapped[Decimal] = mapped_column(MONEY, server_default="0")
    reserved_quantity: Mapped[Decimal] = mapped_column(MONEY, server_default="0")
    stop_order_client_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PortfolioSnapshotRow(Base):
    __tablename__ = "portfolio_snapshots"
    __table_args__ = (
        UniqueConstraint("bot_id", "taken_at"),
        Index("ix_portfolio_snapshots_bot_id_taken_at", "bot_id", "taken_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    bot_id: Mapped[UUID] = mapped_column(ForeignKey("bots.id"))
    session_id: Mapped[UUID] = mapped_column(ForeignKey("trading_sessions.id"))
    taken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    price: Mapped[Decimal] = mapped_column(MONEY)
    cash: Mapped[Decimal] = mapped_column(MONEY)
    quantity: Mapped[Decimal] = mapped_column(MONEY)
    equity: Mapped[Decimal] = mapped_column(MONEY)
