from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from modules.portfolio.domain.models import PortfolioSnapshot, PortfolioState


class PortfolioRepository(Protocol):
    async def get(self, bot_id: UUID) -> PortfolioState | None: ...
    async def save(self, state: PortfolioState) -> None: ...

    async def reset(self, bot_id: UUID, initial_capital: Decimal) -> None:
        """Restart the bot's portfolio from ``initial_capital`` and clear its snapshots."""
        ...

    async def add_snapshot(self, snapshot: PortfolioSnapshot) -> None: ...

    async def list_snapshots(
        self, bot_id: UUID, limit: int | None = None
    ) -> list[PortfolioSnapshot]:
        """Chronological. With ``limit``, the *latest* ``limit`` snapshots."""
        ...

    async def equity_at_or_before(self, bot_id: UUID, moment: datetime) -> Decimal | None: ...
    async def first_snapshot_equity(self, bot_id: UUID) -> Decimal | None: ...
    async def peak_equity(self, bot_id: UUID) -> Decimal | None: ...

    async def open_exposure(self) -> tuple[int, Decimal]:
        """(bots holding a position, total cost basis of those positions) across all bots."""
        ...
