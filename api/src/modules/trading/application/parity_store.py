from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID


@dataclass(slots=True)
class ParityRun:
    id: UUID
    bot_id: UUID
    session_id: UUID | None
    status: str  # queued | running | completed | failed
    created_at: datetime
    finished_at: datetime | None = None
    unexplained: int | None = None
    summary: dict[str, Any] | None = None
    error: str | None = None


class ParityRepository(Protocol):
    async def add(self, run: ParityRun) -> None: ...
    async def latest(self, bot_id: UUID) -> ParityRun | None: ...
    async def latest_completed(self, bot_id: UUID) -> ParityRun | None: ...
    async def claim_next_queued(self) -> ParityRun | None: ...
    async def finish(
        self,
        run_id: UUID,
        *,
        status: str,
        finished_at: datetime,
        session_id: UUID | None = None,
        unexplained: int | None = None,
        summary: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None: ...
