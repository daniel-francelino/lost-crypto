"""Record collateral reservation changes in the immutable perpetual ledger.

Revision ID: 0032
Revises: 0031
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0032"
down_revision: str | None = "0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "bot_perpetual_ledger_entries",
        sa.Column("reserved_margin_delta", sa.Numeric(38, 18), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("bot_perpetual_ledger_entries", "reserved_margin_delta")
