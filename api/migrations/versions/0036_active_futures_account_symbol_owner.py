"""Allow stopped Futures bots to reuse an account/symbol pair.

Revision ID: 0036
Revises: 0035
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0036"
down_revision: str | None = "0035"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None


_INDEX = "uq_bots_futures_connection_symbol"


def upgrade() -> None:
    op.drop_index(_INDEX, table_name="bots")
    op.create_index(
        _INDEX,
        "bots",
        ["exchange_connection_id", "symbol"],
        unique=True,
        postgresql_where=sa.text(
            "product = 'linear_perpetual' AND exchange_connection_id IS NOT NULL "
            "AND (desired_state <> 'stopped' OR observed_state <> 'stopped')"
        ),
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DO $$ BEGIN "
            "IF EXISTS (SELECT 1 FROM bots "
            "WHERE product = 'linear_perpetual' AND exchange_connection_id IS NOT NULL "
            "GROUP BY exchange_connection_id, symbol HAVING count(*) > 1) THEN "
            "RAISE EXCEPTION 'cannot restore the all-bots Futures uniqueness index while "
            "duplicate stopped bots exist; remove duplicates before downgrading'; "
            "END IF; END $$"
        )
    )
    op.drop_index(_INDEX, table_name="bots")
    op.create_index(
        _INDEX,
        "bots",
        ["exchange_connection_id", "symbol"],
        unique=True,
        postgresql_where=sa.text(
            "product = 'linear_perpetual' AND exchange_connection_id IS NOT NULL"
        ),
    )
