"""Persist fractional strategy exits with their signal audit record.

Revision ID: 0038
Revises: 0037
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0038"
down_revision: str | None = "0037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "trading_signals",
        sa.Column("exit_fraction", sa.Numeric(38, 18), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("trading_signals", "exit_fraction")
