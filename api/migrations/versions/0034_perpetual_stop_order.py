"""Track the active native protective order for each perp position.

Revision ID: 0034
Revises: 0033
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0034"
down_revision: str | None = "0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "bot_perpetual_portfolios",
        sa.Column("stop_order_client_id", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("bot_perpetual_portfolios", "stop_order_client_id")
