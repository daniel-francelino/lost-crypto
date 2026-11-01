"""store backtest tail risk inputs

Revision ID: 0013
Revises: 0012
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "backtest_runs",
        sa.Column("tail_risk", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("backtest_runs", "tail_risk")
