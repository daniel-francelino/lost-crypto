from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from core.jobs import JobStatus
from modules.backtesting.domain.models import BacktestConfig, EquityPoint, Fill
from modules.market_data.application.ports import CandleRepository
from modules.market_data.domain.models import MarketInfo


@dataclass(slots=True)
class BacktestRun:
    id: UUID
    status: JobStatus
    config: BacktestConfig
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    data_hash: str | None = None
    candles_count: int | None = None
    market_info: MarketInfo | None = None
    metrics: dict[str, Any] | None = None
    error: str | None = None


class BacktestStore(Protocol):
    """One transaction scope for backtest runs, their results and the candles they read."""

    @property
    def candles(self) -> CandleRepository: ...

    async def add_run(self, run: BacktestRun) -> None: ...
    async def get_run(self, run_id: UUID) -> BacktestRun | None: ...
    async def list_runs(self, limit: int) -> list[BacktestRun]: ...
    async def claim_next_queued(self) -> BacktestRun | None: ...
    async def requeue_running(self) -> int: ...
    async def save_result(
        self,
        run_id: UUID,
        *,
        data_hash: str,
        candles_count: int,
        market_info: MarketInfo,
        metrics: dict[str, Any],
        equity_curve: list[EquityPoint],
        fills: list[Fill],
    ) -> None: ...
    async def mark_failed(self, run_id: UUID, error: str) -> None: ...
    async def list_trades(self, run_id: UUID) -> list[Fill]: ...
    async def get_equity_curve(self, run_id: UUID) -> list[EquityPoint] | None: ...
    async def commit(self) -> None: ...
