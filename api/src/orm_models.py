"""Imports every module's ORM models so they register on ``Base.metadata`` (for Alembic)."""

import modules.audit.orm
import modules.auth.orm
import modules.backtesting.infrastructure.orm
import modules.bots.infrastructure.orm
import modules.exchanges.infrastructure.orm
import modules.execution.infrastructure.orm
import modules.market_data.infrastructure.orm
import modules.notifications.infrastructure.orm
import modules.portfolio.infrastructure.orm
import modules.risk_management.infrastructure.orm
import modules.trading.infrastructure.orm
import modules.trends.infrastructure.orm

__all__ = [
    "modules",
]
