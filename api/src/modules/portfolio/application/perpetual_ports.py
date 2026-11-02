from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from modules.portfolio.domain.perpetual_ledger import (
    PerpetualLedgerEntry,
    PerpetualPortfolioSnapshot,
)
from modules.portfolio.domain.perpetuals import PerpetualLedger


class PerpetualPortfolioRepository(Protocol):
    async def get(self, bot_id: UUID) -> PerpetualLedger | None: ...

    async def save(self, ledger: PerpetualLedger) -> None: ...

    async def append_entry(self, entry: PerpetualLedgerEntry) -> bool:
        """Append once by event id; False if the same event was already committed."""
        ...

    async def list_entries(
        self, bot_id: UUID, start: datetime | None = None, end: datetime | None = None
    ) -> list[PerpetualLedgerEntry]: ...

    async def add_snapshot(self, snapshot: PerpetualPortfolioSnapshot) -> None: ...

    async def list_snapshots(
        self, bot_id: UUID, limit: int | None = None
    ) -> list[PerpetualPortfolioSnapshot]: ...

    async def reset(self, bot_id: UUID, initial_capital: Decimal) -> None: ...
