from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base


class SystemFlagRow(Base):
    """Global switches. Currently only ``kill_switch``."""

    __tablename__ = "system_flags"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    active: Mapped[bool] = mapped_column(Boolean)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class BackupRunRow(Base):
    """Database backups and restore checks (book 1 ch. 4, O4). A backup only counts as good
    once a restore check of it succeeded."""

    __tablename__ = "backups"
    __table_args__ = (CheckConstraint("kind IN ('backup','restore_check')", name="kind_valid"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(Text)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ok: Mapped[bool] = mapped_column(Boolean)
    file: Mapped[str | None] = mapped_column(Text, nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    checksum: Mapped[str | None] = mapped_column(Text, nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
