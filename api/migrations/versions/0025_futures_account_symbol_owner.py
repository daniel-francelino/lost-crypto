"""Enforce one futures bot owner per exchange account and perpetual symbol.

Revision ID: 0025
Revises: 0024
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0025"
down_revision: str | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_index(
        "uq_bots_futures_connection_symbol",
        "bots",
        ["exchange_connection_id", "symbol"],
        unique=True,
        postgresql_where=(
            "product = 'linear_perpetual' AND exchange_connection_id IS NOT NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index("uq_bots_futures_connection_symbol", table_name="bots")
