"""Persist isolated per-bot perpetual state, immutable ledger events, and marked snapshots.

Revision ID: 0026
Revises: 0025
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0026"
down_revision: str | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None

MONEY = sa.Numeric(38, 18)


def upgrade() -> None:
    op.create_table(
        "bot_perpetual_portfolios",
        sa.Column("bot_id", sa.Uuid(), nullable=False),
        sa.Column("wallet_balance", MONEY, nullable=False),
        sa.Column("reserved_margin", MONEY, server_default="0", nullable=False),
        sa.Column("realized_pnl", MONEY, server_default="0", nullable=False),
        sa.Column("fees_paid", MONEY, server_default="0", nullable=False),
        sa.Column("funding_paid", MONEY, server_default="0", nullable=False),
        sa.Column("funding_received", MONEY, server_default="0", nullable=False),
        sa.Column("position_side", sa.Text(), nullable=True),
        sa.Column("quantity", MONEY, server_default="0", nullable=False),
        sa.Column("entry_price", MONEY, server_default="0", nullable=False),
        sa.Column("leverage", sa.Integer(), server_default="1", nullable=False),
        sa.Column("isolated_margin", MONEY, server_default="0", nullable=False),
        sa.Column("mark_price", MONEY, nullable=True),
        sa.Column("marked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mark_source", sa.Text(), server_default="exchange_mark_price", nullable=False),
        sa.Column("maintenance_margin_rate", MONEY, server_default="0", nullable=False),
        sa.Column("exchange_position_id", sa.Text(), nullable=True),
        sa.Column("exchange_liquidation_price", MONEY, nullable=True),
        sa.Column("reconciled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "wallet_balance >= 0 AND reserved_margin >= 0 AND reserved_margin <= wallet_balance",
            name="perpetual_wallet_valid",
        ),
        sa.CheckConstraint(
            "fees_paid >= 0 AND funding_paid >= 0 AND funding_received >= 0",
            name="perpetual_charges_valid",
        ),
        sa.CheckConstraint(
            "(position_side IS NULL AND quantity = 0 AND entry_price = 0 AND isolated_margin = 0) "
            "OR (position_side IN ('long','short') AND quantity > 0 AND entry_price > 0 "
            "AND isolated_margin > 0)",
            name="perpetual_position_valid",
        ),
        sa.CheckConstraint("leverage BETWEEN 1 AND 10", name="perpetual_leverage_valid"),
        sa.CheckConstraint(
            "maintenance_margin_rate >= 0 AND maintenance_margin_rate < 1",
            name="perpetual_maintenance_valid",
        ),
        sa.ForeignKeyConstraint(["bot_id"], ["bots.id"]),
        sa.PrimaryKeyConstraint("bot_id"),
    )
    op.create_table(
        "bot_perpetual_ledger_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("bot_id", sa.Uuid(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("wallet_delta", MONEY, nullable=False),
        sa.Column("isolated_margin_delta", MONEY, nullable=False),
        sa.Column("realized_pnl_delta", MONEY, nullable=False),
        sa.Column("fee", MONEY, nullable=False),
        sa.Column("funding", MONEY, nullable=False),
        sa.Column("quantity", MONEY, nullable=True),
        sa.Column("side", sa.Text(), nullable=True),
        sa.Column("price", MONEY, nullable=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("external_reference", sa.Text(), nullable=True),
        sa.CheckConstraint("fee >= 0", name="perpetual_entry_fee_valid"),
        sa.CheckConstraint(
            "side IS NULL OR side IN ('long','short')", name="perpetual_entry_side_valid"
        ),
        sa.ForeignKeyConstraint(["bot_id"], ["bots.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bot_id", "external_reference"),
    )
    op.create_index(
        "ix_perpetual_ledger_bot_time", "bot_perpetual_ledger_entries", ["bot_id", "occurred_at"]
    )
    op.create_table(
        "perpetual_portfolio_snapshots",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("bot_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("taken_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("mark_price", MONEY, nullable=False),
        sa.Column("wallet_balance", MONEY, nullable=False),
        sa.Column("isolated_margin", MONEY, nullable=False),
        sa.Column("position_side", sa.Text(), nullable=True),
        sa.Column("quantity", MONEY, nullable=False),
        sa.Column("entry_price", MONEY, nullable=False),
        sa.Column("equity", MONEY, nullable=False),
        sa.Column("unrealized_pnl", MONEY, nullable=False),
        sa.Column("funding_paid", MONEY, nullable=False),
        sa.Column("funding_received", MONEY, nullable=False),
        sa.Column("mark_source", sa.Text(), server_default="exchange_mark_price", nullable=False),
        sa.CheckConstraint("mark_price > 0", name="perpetual_snapshot_mark_valid"),
        sa.CheckConstraint(
            "(position_side IS NULL AND quantity = 0) OR "
            "(position_side IN ('long','short') AND quantity > 0)",
            name="perpetual_snapshot_position_valid",
        ),
        sa.ForeignKeyConstraint(["bot_id"], ["bots.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["trading_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bot_id", "taken_at"),
    )
    op.create_index(
        "ix_perpetual_snapshots_bot_time",
        "perpetual_portfolio_snapshots",
        ["bot_id", "taken_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_perpetual_snapshots_bot_time", table_name="perpetual_portfolio_snapshots")
    op.drop_table("perpetual_portfolio_snapshots")
    op.drop_index("ix_perpetual_ledger_bot_time", table_name="bot_perpetual_ledger_entries")
    op.drop_table("bot_perpetual_ledger_entries")
    op.drop_table("bot_perpetual_portfolios")
