"""operations: key permission checks, backups

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-01 00:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = '0010'
down_revision: str | None = '0009'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('exchange_connections', sa.Column('permissions', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('exchange_connections', sa.Column('status_reason', sa.Text(), nullable=True))
    op.add_column('exchange_connections', sa.Column('last_checked_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('exchange_connections', sa.Column('permission_warning', sa.Text(), nullable=True))
    op.create_table('backups',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('kind', sa.Text(), nullable=False),
    sa.Column('at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('ok', sa.Boolean(), nullable=False),
    sa.Column('file', sa.Text(), nullable=True),
    sa.Column('size_bytes', sa.BigInteger(), nullable=True),
    sa.Column('checksum', sa.Text(), nullable=True),
    sa.Column('detail', sa.Text(), nullable=True),
    sa.CheckConstraint("kind IN ('backup','restore_check')", name=op.f('ck_backups_kind_valid')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_backups'))
    )


def downgrade() -> None:
    op.drop_table('backups')
    op.drop_column('exchange_connections', 'permission_warning')
    op.drop_column('exchange_connections', 'last_checked_at')
    op.drop_column('exchange_connections', 'status_reason')
    op.drop_column('exchange_connections', 'permissions')
