"""Allow Binance Demo Mode credentials as a distinct connection environment.

Revision ID: 0029
Revises: 0028
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0029"
down_revision: str | None = "0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("ck_exchange_connections_environment_valid"),
        "exchange_connections",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_exchange_connections_environment_valid"),
        "exchange_connections",
        "environment IN ('demo','testnet','live')",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_exchange_connections_environment_valid"),
        "exchange_connections",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_exchange_connections_environment_valid"),
        "exchange_connections",
        "environment IN ('testnet','live')",
    )
