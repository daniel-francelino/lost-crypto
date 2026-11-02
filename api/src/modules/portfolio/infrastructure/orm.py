from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
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


class PerpetualPortfolioRow(Base):
    """USDT collateral and one isolated linear position, never stored in spot cash/quantity."""

    __tablename__ = "bot_perpetual_portfolios"
    __table_args__ = (
        CheckConstraint(
            "wallet_balance >= 0 AND reserved_margin >= 0 AND reserved_margin <= wallet_balance",
            name="perpetual_wallet_valid",
        ),
        CheckConstraint(
            "fees_paid >= 0 AND funding_paid >= 0 AND funding_received >= 0",
            name="perpetual_charges_valid",
        ),
        CheckConstraint(
            "(position_side IS NULL AND quantity = 0 AND entry_price = 0 AND isolated_margin = 0) "
            "OR (position_side IN ('long','short') AND quantity > 0 AND entry_price > 0 "
            "AND isolated_margin > 0)",
            name="perpetual_position_valid",
        ),
        CheckConstraint("leverage BETWEEN 1 AND 10", name="perpetual_leverage_valid"),
        CheckConstraint(
            "maintenance_margin_rate >= 0 AND maintenance_margin_rate < 1",
            name="perpetual_maintenance_valid",
        ),
    )

    bot_id: Mapped[UUID] = mapped_column(ForeignKey("bots.id"), primary_key=True)
    wallet_balance: Mapped[Decimal] = mapped_column(MONEY)
    reserved_margin: Mapped[Decimal] = mapped_column(MONEY, server_default="0")
    realized_pnl: Mapped[Decimal] = mapped_column(MONEY, server_default="0")
    fees_paid: Mapped[Decimal] = mapped_column(MONEY, server_default="0")
    funding_paid: Mapped[Decimal] = mapped_column(MONEY, server_default="0")
    funding_received: Mapped[Decimal] = mapped_column(MONEY, server_default="0")
    position_side: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[Decimal] = mapped_column(MONEY, server_default="0")
    entry_price: Mapped[Decimal] = mapped_column(MONEY, server_default="0")
    leverage: Mapped[int] = mapped_column(Integer, server_default="1")
    isolated_margin: Mapped[Decimal] = mapped_column(MONEY, server_default="0")
    stop_price: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    take_profit_price: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    mark_price: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    marked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    mark_source: Mapped[str] = mapped_column(Text, server_default="exchange_mark_price")
    maintenance_margin_rate: Mapped[Decimal] = mapped_column(MONEY, server_default="0")
    stop_order_client_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    exchange_position_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    exchange_liquidation_price: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PerpetualLedgerEntryRow(Base):
    __tablename__ = "bot_perpetual_ledger_entries"
    __table_args__ = (
        Index("ix_perpetual_ledger_bot_time", "bot_id", "occurred_at"),
        UniqueConstraint("bot_id", "external_reference"),
        CheckConstraint("fee >= 0", name="perpetual_entry_fee_valid"),
        CheckConstraint(
            "side IS NULL OR side IN ('long','short')", name="perpetual_entry_side_valid"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    bot_id: Mapped[UUID] = mapped_column(ForeignKey("bots.id"))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    kind: Mapped[str] = mapped_column(Text)
    wallet_delta: Mapped[Decimal] = mapped_column(MONEY)
    isolated_margin_delta: Mapped[Decimal] = mapped_column(MONEY)
    reserved_margin_delta: Mapped[Decimal] = mapped_column(MONEY, server_default="0")
    realized_pnl_delta: Mapped[Decimal] = mapped_column(MONEY)
    fee: Mapped[Decimal] = mapped_column(MONEY)
    funding: Mapped[Decimal] = mapped_column(MONEY)
    quantity: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    side: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    source: Mapped[str] = mapped_column(Text)
    external_reference: Mapped[str | None] = mapped_column(Text, nullable=True)


class PerpetualPortfolioSnapshotRow(Base):
    __tablename__ = "perpetual_portfolio_snapshots"
    __table_args__ = (
        UniqueConstraint("bot_id", "taken_at"),
        Index("ix_perpetual_snapshots_bot_time", "bot_id", "taken_at"),
        CheckConstraint("mark_price > 0", name="perpetual_snapshot_mark_valid"),
        CheckConstraint(
            "(position_side IS NULL AND quantity = 0) OR "
            "(position_side IN ('long','short') AND quantity > 0)",
            name="perpetual_snapshot_position_valid",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    bot_id: Mapped[UUID] = mapped_column(ForeignKey("bots.id"))
    session_id: Mapped[UUID] = mapped_column(ForeignKey("trading_sessions.id"))
    taken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    mark_price: Mapped[Decimal] = mapped_column(MONEY)
    wallet_balance: Mapped[Decimal] = mapped_column(MONEY)
    isolated_margin: Mapped[Decimal] = mapped_column(MONEY)
    position_side: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[Decimal] = mapped_column(MONEY)
    entry_price: Mapped[Decimal] = mapped_column(MONEY)
    equity: Mapped[Decimal] = mapped_column(MONEY)
    unrealized_pnl: Mapped[Decimal] = mapped_column(MONEY)
    funding_paid: Mapped[Decimal] = mapped_column(MONEY)
    funding_received: Mapped[Decimal] = mapped_column(MONEY)
    mark_source: Mapped[str] = mapped_column(Text, server_default="exchange_mark_price")


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
