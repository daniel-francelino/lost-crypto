"""Persist protective levels on isolated perpetual positions.

Revision ID: 0033
Revises: 0032
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0033"
down_revision: str | None = "0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("bot_perpetual_portfolios", sa.Column("stop_price", sa.Numeric(38, 18)))
    op.add_column("bot_perpetual_portfolios", sa.Column("take_profit_price", sa.Numeric(38, 18)))


def downgrade() -> None:
    op.drop_column("bot_perpetual_portfolios", "take_profit_price")
    op.drop_column("bot_perpetual_portfolios", "stop_price")
