from datetime import datetime

from sqlalchemy import Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base


class SystemFlagRow(Base):
    """Global switches. Currently only ``kill_switch``."""

    __tablename__ = "system_flags"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    active: Mapped[bool] = mapped_column(Boolean)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
