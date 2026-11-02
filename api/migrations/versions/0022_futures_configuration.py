"""Persist product and leverage configuration for bots and backtests.

Revision ID: 0022
Revises: 0021
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    for table in ("bots", "backtest_runs"):
        op.add_column(table, sa.Column("product", sa.Text(), nullable=False, server_default="spot"))
        op.add_column(
            table, sa.Column("leverage", sa.Integer(), nullable=False, server_default="1")
        )
        op.add_column(
            table, sa.Column("allow_short", sa.Boolean(), nullable=False, server_default="false")
        )
    op.add_column("bots", sa.Column("margin_mode", sa.Text(), nullable=True))
    op.create_check_constraint(
        "bots_product_valid", "bots", "product IN ('spot','linear_perpetual')"
    )
    op.create_check_constraint(
        "bots_leverage_valid",
        "bots",
        "leverage BETWEEN 1 AND 10 AND (product != 'spot' OR leverage = 1)",
    )
    op.create_check_constraint(
        "bots_short_valid", "bots", "product != 'spot' OR allow_short = false"
    )
    op.create_check_constraint(
        "backtest_product_valid", "backtest_runs", "product IN ('spot','linear_perpetual')"
    )
    op.create_check_constraint(
        "backtest_leverage_valid",
        "backtest_runs",
        "leverage BETWEEN 1 AND 10 AND (product != 'spot' OR leverage = 1)",
    )
    op.create_check_constraint(
        "backtest_short_valid", "backtest_runs", "product != 'spot' OR allow_short = false"
    )


def downgrade() -> None:
    for table, constraints in (
        ("bots", ("bots_short_valid", "bots_leverage_valid", "bots_product_valid")),
        (
            "backtest_runs",
            ("backtest_short_valid", "backtest_leverage_valid", "backtest_product_valid"),
        ),
    ):
        for name in constraints:
            op.drop_constraint(name, table, type_="check")
    op.drop_column("bots", "margin_mode")
    for table in ("bots", "backtest_runs"):
        op.drop_column(table, "allow_short")
        op.drop_column(table, "leverage")
        op.drop_column(table, "product")
