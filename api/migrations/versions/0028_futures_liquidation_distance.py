"""Add the futures liquidation-distance risk buffer.

Revision ID: 0028
Revises: 0027
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0028"
down_revision: str | None = "0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "bots",
        sa.Column("min_liquidation_distance_pct", sa.Numeric(38, 18), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("bots", "min_liquidation_distance_pct")
