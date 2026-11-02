"""Persist margin mode for backtest configurations and enforce product-specific margin rules.

Revision ID: 0023
Revises: 0022
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("backtest_runs", sa.Column("margin_mode", sa.Text(), nullable=True))
    op.create_check_constraint(
        "bots_margin_valid",
        "bots",
        "(product = 'spot' AND margin_mode IS NULL) OR "
        "(product = 'linear_perpetual' AND margin_mode = 'isolated')",
    )
    op.create_check_constraint(
        "backtest_margin_valid",
        "backtest_runs",
        "(product = 'spot' AND margin_mode IS NULL) OR "
        "(product = 'linear_perpetual' AND margin_mode = 'isolated')",
    )


def downgrade() -> None:
    op.drop_constraint("backtest_margin_valid", "backtest_runs", type_="check")
    op.drop_constraint("bots_margin_valid", "bots", type_="check")
    op.drop_column("backtest_runs", "margin_mode")
