from datetime import datetime
from decimal import Decimal
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
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base

MONEY = Numeric(38, 18)


class OrderRow(Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("bot_id", "client_order_id"),
        CheckConstraint("filled_quantity >= 0 AND filled_quantity <= quantity", name="fill_bounds"),
        CheckConstraint(
            "(product = 'spot' AND position_side IS NULL AND leverage = 1 AND NOT reduce_only) "
            "OR (product = 'linear_perpetual' AND position_side IN ('long','short') "
            "AND leverage BETWEEN 1 AND 10)",
            name="product_intent_valid",
        ),
        Index("ix_orders_bot_id_created_at", "bot_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    bot_id: Mapped[UUID] = mapped_column(ForeignKey("bots.id"))
    session_id: Mapped[UUID] = mapped_column(ForeignKey("trading_sessions.id"))
    client_order_id: Mapped[str] = mapped_column(Text)
    symbol: Mapped[str] = mapped_column(Text)
    side: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(Text, default="market")
    quantity: Mapped[Decimal] = mapped_column(MONEY)
    filled_quantity: Mapped[Decimal] = mapped_column(MONEY)
    avg_fill_price: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    status: Mapped[str] = mapped_column(Text)
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    exchange_order_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    stop_price: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    reserved_cash: Mapped[Decimal] = mapped_column(MONEY, server_default="0")
    reserved_quantity: Mapped[Decimal] = mapped_column(MONEY, server_default="0")
    reserved_margin: Mapped[Decimal] = mapped_column(MONEY, server_default="0")
    product: Mapped[str] = mapped_column(Text, server_default="spot")
    position_side: Mapped[str | None] = mapped_column(Text, nullable=True)
    leverage: Mapped[int] = mapped_column(Integer, server_default="1")
    reduce_only: Mapped[bool] = mapped_column(Boolean, server_default="false")
    planned_stop_price: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    planned_take_profit_price: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    bar_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reference_price: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_fill_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OrderFillRow(Base):
    __tablename__ = "order_fills"
    __table_args__ = (UniqueConstraint("order_id", "venue_trade_id"),)

    id: Mapped[UUID] = mapped_column(primary_key=True)
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    venue_trade_id: Mapped[str] = mapped_column(Text)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    side: Mapped[str] = mapped_column(Text)
    quantity: Mapped[Decimal] = mapped_column(MONEY)
    price: Mapped[Decimal] = mapped_column(MONEY)
    fee: Mapped[Decimal] = mapped_column(MONEY)
    fee_base: Mapped[Decimal] = mapped_column(MONEY, server_default="0")


class TradingSignalRow(Base):
    __tablename__ = "trading_signals"
    __table_args__ = (Index("ix_trading_signals_bot_id_created_at", "bot_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(primary_key=True)
    session_id: Mapped[UUID] = mapped_column(ForeignKey("trading_sessions.id"))
    bot_id: Mapped[UUID] = mapped_column(ForeignKey("bots.id"))
    bar_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    side: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    decision: Mapped[str] = mapped_column(Text)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
