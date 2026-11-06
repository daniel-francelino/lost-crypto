from collections.abc import Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from modules.market_data.application.ports import CandleRepository
from modules.market_data.domain.trend import TrendFrame
from modules.trends.domain.models import FrameProgress, TrendRecord, WatchedSymbol


class TrendRepository(Protocol):
    async def list_symbols(self, *, active_only: bool) -> list[WatchedSymbol]: ...

    async def get_symbol(self, symbol_id: UUID) -> WatchedSymbol | None: ...

    async def find_symbol(self, exchange: str, symbol: str) -> WatchedSymbol | None: ...

    async def add_symbol(self, symbol: WatchedSymbol) -> None: ...

    async def set_active(self, symbol_id: UUID, active: bool) -> bool:
        """False when the symbol does not exist."""
        ...

    async def get_progress(self, exchange: str, symbol: str) -> dict[TrendFrame, FrameProgress]: ...

    async def save_progress(
        self, exchange: str, symbol: str, progress: FrameProgress, now: datetime
    ) -> None: ...

    async def reset_frame(self, exchange: str, symbol: str, frame: TrendFrame) -> None:
        """Forget a frame's progress and readings (its settings changed)."""
        ...

    async def upsert_records(self, records: Sequence[TrendRecord]) -> int: ...

    async def latest(self, exchange: str, symbol: str) -> list[TrendRecord]:
        """The newest record of each timeframe."""
        ...

    async def history(
        self,
        exchange: str,
        symbol: str,
        frame: TrendFrame,
        limit: int,
        before: datetime | None = None,
    ) -> list[TrendRecord]:
        """Newest first."""
        ...


class TrendStore(Protocol):
    """One transaction scope for the detector: stored candles and the trend tables."""

    @property
    def candles(self) -> CandleRepository: ...

    @property
    def trends(self) -> TrendRepository: ...

    async def commit(self) -> None: ...
