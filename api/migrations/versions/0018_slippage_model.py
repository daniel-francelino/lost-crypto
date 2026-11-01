"""optional slippage model of a backtest (book 2 ch. 7)

Revision ID: 0018
Revises: 0017
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MONEY = sa.Numeric(38, 18)


def upgrade() -> None:
    op.add_column(
        "backtest_runs",
        sa.Column("slippage_model", sa.Text(), nullable=False, server_default="fixed"),
    )
    op.add_column("backtest_runs", sa.Column("slippage_k_range", MONEY, nullable=True))
    op.add_column("backtest_runs", sa.Column("slippage_k_size", MONEY, nullable=True))


def downgrade() -> None:
    op.drop_column("backtest_runs", "slippage_k_size")
    op.drop_column("backtest_runs", "slippage_k_range")
    op.drop_column("backtest_runs", "slippage_model")
