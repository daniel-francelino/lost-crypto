"""close-to-close jump limit on a bot's entries

Revision ID: 0016
Revises: 0015
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MONEY = sa.Numeric(38, 18)


def upgrade() -> None:
    op.add_column("bots", sa.Column("max_close_jump_pct", MONEY, nullable=True))


def downgrade() -> None:
    op.drop_column("bots", "max_close_jump_pct")
