"""Trend detector: symbol registry, resumable state and the readings per timeframe.

Revision ID: 0040
Revises: 0039
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0040"
down_revision: str | None = "0039"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None

_TRENDS = "('bullish','bearish','sideways')"


def upgrade() -> None:
    op.create_table(
        "trend_symbols",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("exchange", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_trend_symbols"),
        sa.UniqueConstraint("exchange", "symbol", name="uq_trend_symbols_exchange"),
    )
    op.create_table(
        "trend_states",
        sa.Column("exchange", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("frame", sa.Text(), nullable=False),
        sa.Column("last_bar_open_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("settings_key", sa.Text(), nullable=False),
        sa.Column("state", postgresql.JSONB(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("exchange", "symbol", "frame", name="pk_trend_states"),
    )
    op.create_table(
        "trend_readings",
        sa.Column("exchange", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("frame", sa.Text(), nullable=False),
        sa.Column("bar_open_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("trend", sa.Text(), nullable=False),
        sa.Column("previous_trend", sa.Text(), nullable=True),
        sa.Column("close", sa.Numeric(38, 18), nullable=True),
        sa.Column("ema_fast", sa.Numeric(38, 18), nullable=True),
        sa.Column("ema_slow", sa.Numeric(38, 18), nullable=True),
        sa.Column("ema_distance_pct", sa.Numeric(38, 18), nullable=True),
        sa.Column("slow_slope_pct", sa.Numeric(38, 18), nullable=True),
        sa.Column("adx", sa.Numeric(38, 18), nullable=True),
        sa.Column("atr", sa.Numeric(38, 18), nullable=True),
        sa.Column("structure", sa.Text(), nullable=True),
        sa.Column("checks", postgresql.JSONB(), nullable=False),
        sa.Column("confirmed", sa.Boolean(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "exchange", "symbol", "frame", "bar_open_time", name="pk_trend_readings"
        ),
        sa.CheckConstraint(f"trend IN {_TRENDS}", name="ck_trend_readings_trend_valid"),
        sa.CheckConstraint(
            f"previous_trend IS NULL OR previous_trend IN {_TRENDS}",
            name="ck_trend_readings_previous_trend_valid",
        ),
        sa.CheckConstraint(
            f"structure IS NULL OR structure IN {_TRENDS}",
            name="ck_trend_readings_structure_valid",
        ),
    )


def downgrade() -> None:
    op.drop_table("trend_readings")
    op.drop_table("trend_states")
    op.drop_table("trend_symbols")
