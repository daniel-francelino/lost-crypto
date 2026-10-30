from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from modules.audit.models import AuditRepository
from modules.bots.application.ports import BotRepository
from modules.execution.application.ports import OrderRepository, SignalRepository
from modules.portfolio.application.ports import PortfolioRepository
from modules.risk_management.application.ports import SystemFlagsRepository
from modules.trading.domain.models import TradingSession


class SessionRepository(Protocol):
    async def get_active(self, bot_id: UUID) -> TradingSession | None: ...
    async def add(self, session: TradingSession) -> None: ...
    async def save_progress(
        self, session_id: UUID, strategy_state: dict[str, Any], last_bar_time: datetime
    ) -> None: ...
    async def end(self, session_id: UUID, reason: str) -> None: ...


class TradingStore(Protocol):
    """Transaction scope of the worker: everything one candle's processing touches.

    Order, fills, portfolio, snapshot, signals, strategy state and audit commit together,
    so a crash can never leave a fill without its bookkeeping (or the reverse).
    """

    @property
    def bots(self) -> BotRepository: ...
    @property
    def sessions(self) -> SessionRepository: ...
    @property
    def orders(self) -> OrderRepository: ...
    @property
    def signals(self) -> SignalRepository: ...
    @property
    def portfolio(self) -> PortfolioRepository: ...
    @property
    def flags(self) -> SystemFlagsRepository: ...
    @property
    def audit(self) -> AuditRepository: ...

    async def commit(self) -> None: ...
