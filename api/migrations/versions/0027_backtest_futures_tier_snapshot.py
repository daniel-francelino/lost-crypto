"""Bind futures backtests to their account and snapshot leverage tiers.

Revision ID: 0027
Revises: 0026
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0027"
down_revision: str | None = "0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "backtest_runs",
        sa.Column("exchange_connection_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "backtest_runs",
        sa.Column("leverage_tiers", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "backtest_runs",
        sa.Column("leverage_tiers_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_backtest_runs_exchange_connection_id",
        "backtest_runs",
        "exchange_connections",
        ["exchange_connection_id"],
        ["id"],
    )
    op.create_check_constraint(
        "backtest_runs_connection_valid",
        "backtest_runs",
        "(product = 'spot' AND exchange_connection_id IS NULL) OR "
        "(product = 'linear_perpetual' AND exchange_connection_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("backtest_runs_connection_valid", "backtest_runs", type_="check")
    op.drop_constraint(
        "fk_backtest_runs_exchange_connection_id", "backtest_runs", type_="foreignkey"
    )
    op.drop_column("backtest_runs", "leverage_tiers")
    op.drop_column("backtest_runs", "leverage_tiers_at")
    op.drop_column("backtest_runs", "exchange_connection_id")
