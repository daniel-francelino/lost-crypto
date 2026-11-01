"""execution systems: execution record, volume cap, backtest risk/timing, parity runs

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-01 01:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = '0011'
down_revision: str | None = '0010'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MONEY = sa.Numeric(precision=38, scale=18)


def upgrade() -> None:
    op.add_column('orders', sa.Column('reference_price', MONEY, nullable=True))
    op.add_column('orders', sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('orders', sa.Column('first_fill_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('bots', sa.Column('max_order_pct_of_volume', MONEY, nullable=True))
    op.add_column('backtest_runs', sa.Column('fill_timing', sa.Text(), server_default='next_open', nullable=False))
    op.add_column('backtest_runs', sa.Column('risk_limits', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('backtest_runs', sa.Column('risk_report', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.create_table('parity_runs',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('bot_id', sa.Uuid(), nullable=False),
    sa.Column('session_id', sa.Uuid(), nullable=True),
    sa.Column('status', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('unexplained', sa.Integer(), nullable=True),
    sa.Column('summary', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('error', sa.Text(), nullable=True),
    sa.CheckConstraint("status IN ('queued','running','completed','failed')", name=op.f('ck_parity_runs_status_valid')),
    sa.ForeignKeyConstraint(['bot_id'], ['bots.id'], name=op.f('fk_parity_runs_bot_id_bots'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_parity_runs'))
    )
    op.create_index('ix_parity_runs_bot_id_created_at', 'parity_runs', ['bot_id', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_parity_runs_bot_id_created_at', table_name='parity_runs')
    op.drop_table('parity_runs')
    op.drop_column('backtest_runs', 'risk_report')
    op.drop_column('backtest_runs', 'risk_limits')
    op.drop_column('backtest_runs', 'fill_timing')
    op.drop_column('bots', 'max_order_pct_of_volume')
    op.drop_column('orders', 'first_fill_at')
    op.drop_column('orders', 'submitted_at')
    op.drop_column('orders', 'reference_price')
