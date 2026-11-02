from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from modules.audit.models import AuditRepository
from modules.bots.domain.models import Bot, BotConfig, BotState
from modules.exchanges.application.connections import ConnectionRepository
from modules.execution.application.ports import OrderRepository, SignalRepository
from modules.portfolio.application.perpetual_ports import PerpetualPortfolioRepository
from modules.portfolio.application.ports import PortfolioRepository
from modules.trading.application.parity_store import ParityRepository


class BotRepository(Protocol):
    async def add(self, bot: Bot) -> bool:
        """Persist a new bot; False when the name is already taken."""
        ...

    async def get(self, bot_id: UUID) -> Bot | None: ...
    async def list_bots(self, limit: int) -> list[Bot]: ...
    async def list_active(self) -> list[Bot]:
        """Bots the worker must look at: anything not fully stopped, or asked to run."""
        ...

    async def update_config(self, bot_id: UUID, config: BotConfig, config_version: int) -> bool:
        """Persist a new configuration; False when the name collides with another bot."""
        ...

    async def set_desired(self, bot_id: UUID, state: BotState) -> None: ...
    async def set_observed(self, bot_id: UUID, state: BotState, error: str | None) -> None: ...
    async def heartbeat(self, bot_ids: list[UUID], at: datetime) -> None: ...
    async def set_live_approval(
        self, bot_id: UUID, config_version: int | None, at: datetime | None
    ) -> None:
        """Record (or with None, clear) the config version a human approved for live trading."""
        ...

    async def set_mode(self, bot_id: UUID, mode: str, connection_id: UUID | None) -> None: ...

    async def delete(self, bot_id: UUID) -> None:
        """Remove the bot with its orders, signals, sessions, portfolio, snapshots, approvals,
        parity runs and alerts. Audit events stay: they are the record that it existed."""
        ...


@dataclass(frozen=True, slots=True)
class LiveApproval:
    """A one-time permission to start a live bot, bound to one configuration version."""

    id: UUID
    bot_id: UUID
    config_version: int
    token_hash: str
    created_by: str
    created_at: datetime
    expires_at: datetime
    used_at: datetime | None = None


class LiveApprovalRepository(Protocol):
    async def supersede(self, bot_id: UUID, at: datetime) -> None:
        """Void every unused approval of the bot (a new request replaces the old ones)."""
        ...

    async def add(self, approval: LiveApproval) -> None: ...
    async def find(self, bot_id: UUID, token_hash: str) -> LiveApproval | None: ...
    async def mark_used(self, approval_id: UUID, at: datetime) -> None: ...


class BotStore(Protocol):
    """Transaction scope used by the API-side bot use cases."""

    @property
    def bots(self) -> BotRepository: ...
    @property
    def orders(self) -> OrderRepository: ...
    @property
    def signals(self) -> SignalRepository: ...
    @property
    def portfolio(self) -> PortfolioRepository: ...

    @property
    def perpetual_portfolio(self) -> PerpetualPortfolioRepository: ...
    @property
    def audit(self) -> AuditRepository: ...
    @property
    def connections(self) -> ConnectionRepository: ...
    @property
    def live_approvals(self) -> LiveApprovalRepository: ...
    @property
    def parity(self) -> ParityRepository: ...

    async def commit(self) -> None: ...
