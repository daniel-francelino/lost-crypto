from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from core.jobs import JobStatus
from modules.backtesting.domain.models import BacktestConfig, EquityPoint
from modules.execution.domain.orders import Fill
from modules.market_data.application.ports import CandleRepository, RegimeBreakRepository
from modules.market_data.domain.models import MarketInfo, Timeframe


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
    segments: dict[str, Any] | None = None  # train/test metrics when test_fraction is set
    periods: dict[str, Any] | None = None  # metrics by calendar year/quarter
    cost_ladder: dict[str, Any] | None = None  # when config.cost_sensitivity is set
    data_quality: dict[str, Any] | None = None  # gaps (at creation), invalid candles, outliers
    risk_report: dict[str, Any] | None = None  # sizing used, pause, refusals by reason
    tail_risk: dict[str, Any] | None = None
    regime: dict[str, Any] | None = None
    significance: dict[str, Any] | None = None
    break_metrics: dict[str, Any] | None = None
    excursion: dict[str, Any] | None = None
    sweep_id: UUID | None = None
    error: str | None = None


@dataclass(slots=True)
class BacktestSweep:
    """A grid of runs of one strategy over the same data, to compare parameter sets."""

    id: UUID
    created_at: datetime
    strategy_type: str
    grid: dict[str, list[Any]]
    skipped: list[dict[str, Any]]  # combinations the strategy rejected, with the reason
    run_count: int


class BacktestStore(Protocol):
    """One transaction scope for backtest runs, their results and the candles they read."""

    @property
    def candles(self) -> CandleRepository: ...

    @property
    def regime_breaks(self) -> RegimeBreakRepository: ...

    async def add_run(self, run: BacktestRun) -> None: ...
    async def get_run(self, run_id: UUID) -> BacktestRun | None: ...
    async def add_sweep(self, sweep: BacktestSweep) -> None: ...
    async def get_sweep(self, sweep_id: UUID) -> BacktestSweep | None: ...
    async def list_sweep_runs(self, sweep_id: UUID) -> list[BacktestRun]: ...
    async def list_runs(self, limit: int, offset: int = 0) -> list[BacktestRun]: ...
    async def count_runs(self) -> int: ...
    async def count_prior_trials(self, sweep: BacktestSweep, base: BacktestConfig) -> int:
        """Completed runs of the same strategy on overlapping data, created before ``sweep``
        and outside it: how many other tries the sweep's winner competed with."""
        ...

    async def count_prior_runs(self, run_id: UUID, config: BacktestConfig) -> int:
        """Other completed runs of the same strategy on overlapping data (any time): how many
        times this window has already been looked at (book 2 ch. 1, O5)."""
        ...

    async def matching_runs(
        self, exchange: str, symbol: str, timeframe: Timeframe, strategy_type: str, limit: int
    ) -> list[BacktestRun]:
        """Newest completed runs of this strategy on this market (the caller narrows further)."""
        ...

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
        segments: dict[str, Any] | None,
        periods: dict[str, Any] | None,
        cost_ladder: dict[str, Any] | None,
        data_quality: dict[str, Any] | None,
        risk_report: dict[str, Any] | None,
        tail_risk: dict[str, Any] | None,
        regime: dict[str, Any] | None,
        significance: dict[str, Any] | None,
        break_metrics: dict[str, Any] | None,
        excursion: dict[str, Any] | None,
        equity_curve: list[EquityPoint],
        fills: list[Fill],
    ) -> None: ...
    async def mark_failed(self, run_id: UUID, error: str) -> None: ...
    async def list_trades(self, run_id: UUID) -> list[Fill]: ...
    async def get_equity_curve(self, run_id: UUID) -> list[EquityPoint] | None: ...
    async def commit(self) -> None: ...
