from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from modules.audit.models import AuditRepository
from modules.bots.application.ports import BotRepository
from modules.exchanges.application.connections import ConnectionRepository
from modules.execution.application.ports import OrderRepository, SignalRepository
from modules.market_data.application.ports import CandleRepository
from modules.portfolio.application.ports import PortfolioRepository
from modules.risk_management.application.ports import SystemFlagsRepository
from modules.trading.application.parity_store import ParityRepository
from modules.trading.domain.models import TradingSession


class SessionRepository(Protocol):
    async def get_active(self, bot_id: UUID) -> TradingSession | None: ...
    async def add(self, session: TradingSession) -> None: ...
    async def save_progress(
        self, session_id: UUID, strategy_state: dict[str, Any], last_bar_time: datetime
    ) -> None: ...
    async def end(self, session_id: UUID, reason: str) -> None: ...
    async def latest(self, bot_id: UUID, mode: str | None = None) -> TradingSession | None: ...


class ReconciliationRepository(Protocol):
    async def add(
        self, connection_id: UUID, started_at: datetime, status: str, details: dict[str, Any]
    ) -> None: ...

    async def latest(self, connection_id: UUID) -> tuple[datetime, str, dict[str, Any]] | None: ...


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
    @property
    def connections(self) -> ConnectionRepository: ...
    @property
    def reconciliations(self) -> ReconciliationRepository: ...
    @property
    def candles(self) -> CandleRepository: ...
    @property
    def parity(self) -> ParityRepository: ...

    async def commit(self) -> None: ...
