from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, Numeric, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base

NUMBER = Numeric(38, 18)
_TRENDS = "('bullish','bearish','sideways')"


class TrendSymbolRow(Base):
    """The symbol registry: which pairs the trend detector follows."""

    __tablename__ = "trend_symbols"
    __table_args__ = (UniqueConstraint("exchange", "symbol"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    exchange: Mapped[str] = mapped_column(Text)
    symbol: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TrendStateRow(Base):
    """Where the detector stopped for one (symbol, timeframe), and the state to resume from."""

    __tablename__ = "trend_states"

    exchange: Mapped[str] = mapped_column(Text, primary_key=True)
    symbol: Mapped[str] = mapped_column(Text, primary_key=True)
    frame: Mapped[str] = mapped_column(Text, primary_key=True)
    last_bar_open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    settings_key: Mapped[str] = mapped_column(Text)
    state: Mapped[dict[str, Any]] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TrendReadingRow(Base):
    """The trend of one bar of one timeframe, with the indicators behind it."""

    __tablename__ = "trend_readings"
    __table_args__ = (
        CheckConstraint(f"trend IN {_TRENDS}", name="trend_valid"),
        CheckConstraint(
            f"previous_trend IS NULL OR previous_trend IN {_TRENDS}", name="previous_trend_valid"
        ),
        CheckConstraint(f"structure IS NULL OR structure IN {_TRENDS}", name="structure_valid"),
    )

    exchange: Mapped[str] = mapped_column(Text, primary_key=True)
    symbol: Mapped[str] = mapped_column(Text, primary_key=True)
    frame: Mapped[str] = mapped_column(Text, primary_key=True)
    bar_open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    trend: Mapped[str] = mapped_column(Text)
    previous_trend: Mapped[str | None] = mapped_column(Text, nullable=True)
    close: Mapped[Decimal | None] = mapped_column(NUMBER, nullable=True)
    ema_fast: Mapped[Decimal | None] = mapped_column(NUMBER, nullable=True)
    ema_slow: Mapped[Decimal | None] = mapped_column(NUMBER, nullable=True)
    ema_distance_pct: Mapped[Decimal | None] = mapped_column(NUMBER, nullable=True)
    slow_slope_pct: Mapped[Decimal | None] = mapped_column(NUMBER, nullable=True)
    adx: Mapped[Decimal | None] = mapped_column(NUMBER, nullable=True)
    atr: Mapped[Decimal | None] = mapped_column(NUMBER, nullable=True)
    structure: Mapped[str | None] = mapped_column(Text, nullable=True)
    checks: Mapped[dict[str, Any]] = mapped_column(JSONB)
    confirmed: Mapped[bool] = mapped_column(Boolean)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
