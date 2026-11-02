"""Keep Binance regular and special funding events at the same timestamp.

Revision ID: 0039
Revises: 0038
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0039"
down_revision: str | None = "0038"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "perpetual_funding_rates",
        sa.Column("rate_type", sa.Text(), server_default="regular", nullable=False),
    )
    op.drop_constraint(
        "pk_perpetual_funding_rates", "perpetual_funding_rates", type_="primary"
    )
    op.create_primary_key(
        "pk_perpetual_funding_rates",
        "perpetual_funding_rates",
        ["exchange", "symbol", "funding_time", "rate_type"],
    )
    op.create_check_constraint(
        "rate_type_valid",
        "perpetual_funding_rates",
        "rate_type IN ('regular', 'special')",
    )
    op.alter_column("perpetual_funding_rates", "rate_type", server_default=None)


def downgrade() -> None:
    op.drop_constraint(
        "rate_type_valid",
        "perpetual_funding_rates",
        type_="check",
    )
    op.drop_constraint(
        "pk_perpetual_funding_rates", "perpetual_funding_rates", type_="primary"
    )
    op.create_primary_key(
        "pk_perpetual_funding_rates",
        "perpetual_funding_rates",
        ["exchange", "symbol", "funding_time"],
    )
    op.drop_column("perpetual_funding_rates", "rate_type")
