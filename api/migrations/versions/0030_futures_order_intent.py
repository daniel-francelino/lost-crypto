"""Persist product and directional intent with each order.

Revision ID: 0030
Revises: 0029
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0030"
down_revision: str | None = "0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("product", sa.Text(), server_default="spot", nullable=False))
    op.add_column("orders", sa.Column("position_side", sa.Text(), nullable=True))
    op.add_column("orders", sa.Column("leverage", sa.Integer(), server_default="1", nullable=False))
    op.add_column(
        "orders", sa.Column("reduce_only", sa.Boolean(), server_default=sa.false(), nullable=False)
    )
    op.create_check_constraint(
        op.f("ck_orders_product_intent_valid"),
        "orders",
        "(product = 'spot' AND position_side IS NULL AND leverage = 1 AND NOT reduce_only) "
        "OR (product = 'linear_perpetual' AND position_side IN ('long','short') "
        "AND leverage BETWEEN 1 AND 10)",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_orders_product_intent_valid"), "orders", type_="check")
    op.drop_column("orders", "reduce_only")
    op.drop_column("orders", "leverage")
    op.drop_column("orders", "position_side")
    op.drop_column("orders", "product")
