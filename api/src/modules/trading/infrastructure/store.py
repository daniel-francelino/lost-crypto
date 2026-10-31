from sqlalchemy.ext.asyncio import AsyncSession

from modules.audit.repository import SqlAlchemyAuditRepository
from modules.auth.repository import SqlAlchemyRefreshTokenRepository, SqlAlchemyUserRepository
from modules.bots.infrastructure.repository import (
    SqlAlchemyBotRepository,
    SqlAlchemyLiveApprovalRepository,
)
from modules.exchanges.infrastructure.repository import (
    SqlAlchemyConnectionRepository,
    SqlAlchemyReconciliationRepository,
)
from modules.execution.infrastructure.repository import (
    SqlAlchemyOrderRepository,
    SqlAlchemySignalRepository,
)
from modules.notifications.infrastructure.repository import SqlAlchemyAlertRepository
from modules.portfolio.infrastructure.repository import SqlAlchemyPortfolioRepository
from modules.risk_management.infrastructure.repository import SqlAlchemySystemFlagsRepository
from modules.trading.infrastructure.repository import SqlAlchemySessionRepository


class SqlAlchemyStore:
    """One session/transaction exposing every repository the bot use cases need.

    It structurally satisfies both ``BotStore`` (API side) and ``TradingStore`` (worker side),
    plus the ports of the kill switch and audit services.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.bots = SqlAlchemyBotRepository(session)
        self.sessions = SqlAlchemySessionRepository(session)
        self.orders = SqlAlchemyOrderRepository(session)
        self.signals = SqlAlchemySignalRepository(session)
        self.portfolio = SqlAlchemyPortfolioRepository(session)
        self.flags = SqlAlchemySystemFlagsRepository(session)
        self.audit = SqlAlchemyAuditRepository(session)
        self.connections = SqlAlchemyConnectionRepository(session)
        self.reconciliations = SqlAlchemyReconciliationRepository(session)
        self.users = SqlAlchemyUserRepository(session)
        self.live_approvals = SqlAlchemyLiveApprovalRepository(session)
        self.refresh_tokens = SqlAlchemyRefreshTokenRepository(session)
        self.alerts = SqlAlchemyAlertRepository(session)

    async def commit(self) -> None:
        await self._session.commit()
