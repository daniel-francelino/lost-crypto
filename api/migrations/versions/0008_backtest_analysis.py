"""backtest analysis: cost ladder, periods, drawdown tolerance

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-31 21:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = '0008'
down_revision: str | None = '0007'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('backtest_runs', sa.Column('cost_sensitivity', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('backtest_runs', sa.Column('max_drawdown_tolerance_pct', sa.Numeric(precision=38, scale=18), nullable=True))
    op.add_column('backtest_runs', sa.Column('max_drawdown_tolerance_days', sa.Integer(), nullable=True))
    op.add_column('backtest_runs', sa.Column('periods', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('backtest_runs', sa.Column('cost_ladder', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('backtest_runs', 'cost_ladder')
    op.drop_column('backtest_runs', 'periods')
    op.drop_column('backtest_runs', 'max_drawdown_tolerance_days')
    op.drop_column('backtest_runs', 'max_drawdown_tolerance_pct')
    op.drop_column('backtest_runs', 'cost_sensitivity')
