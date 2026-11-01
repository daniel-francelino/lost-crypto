"""data quality: import counters, backtest gaps/quality, exchange listings

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-31 23:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = '0009'
down_revision: str | None = '0008'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('candle_import_jobs', sa.Column('candles_rejected', sa.Integer(), server_default='0', nullable=False))
    op.add_column('candle_import_jobs', sa.Column('candles_changed', sa.Integer(), server_default='0', nullable=False))
    op.add_column('candle_import_jobs', sa.Column('rejection_samples', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('backtest_runs', sa.Column('allow_gaps', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('backtest_runs', sa.Column('data_quality', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.create_table('exchange_listings',
    sa.Column('exchange', sa.Text(), nullable=False),
    sa.Column('symbol', sa.Text(), nullable=False),
    sa.Column('status', sa.Text(), nullable=False),
    sa.Column('first_seen', sa.DateTime(timezone=True), nullable=False),
    sa.Column('last_seen', sa.DateTime(timezone=True), nullable=False),
    sa.Column('delisted_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('exchange', 'symbol', name=op.f('pk_exchange_listings'))
    )


def downgrade() -> None:
    op.drop_table('exchange_listings')
    op.drop_column('backtest_runs', 'data_quality')
    op.drop_column('backtest_runs', 'allow_gaps')
    op.drop_column('candle_import_jobs', 'rejection_samples')
    op.drop_column('candle_import_jobs', 'candles_changed')
    op.drop_column('candle_import_jobs', 'candles_rejected')
