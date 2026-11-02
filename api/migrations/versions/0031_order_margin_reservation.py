"""Persist collateral reserved for in-flight perpetual orders.

Revision ID: 0031
Revises: 0030
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0031"
down_revision: str | None = "0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("reserved_margin", sa.Numeric(38, 18), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("orders", "reserved_margin")
