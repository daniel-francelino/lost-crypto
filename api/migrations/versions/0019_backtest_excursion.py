"""store the maximum adverse excursion of a backtest's trades

Revision ID: 0019
Revises: 0018
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("backtest_runs", sa.Column("excursion", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("backtest_runs", "excursion")
