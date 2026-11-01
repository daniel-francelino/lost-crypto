from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.jobs import JobStatus
from modules.backtesting.application.ports import BacktestRun, BacktestSweep
from modules.backtesting.domain.models import BacktestConfig, EquityPoint, FillTiming
from modules.backtesting.infrastructure.orm import (
    BacktestRunRow,
    BacktestSweepRow,
    BacktestTradeRow,
)
from modules.execution.domain.orders import Fill
from modules.market_data.domain.models import MarketInfo, Timeframe
from modules.market_data.infrastructure.repository import SqlAlchemyCandleRepository
from modules.risk_management.domain.models import limits_from_dict, limits_to_dict
from modules.strategies.domain.types import Side


def _market_to_json(market: MarketInfo) -> dict[str, str]:
    return {
        "symbol": market.symbol,
        "step_size": str(market.step_size),
        "tick_size": str(market.tick_size),
        "min_quantity": str(market.min_quantity),
        "min_notional": str(market.min_notional),
    }


def _market_from_json(raw: dict[str, Any]) -> MarketInfo:
    return MarketInfo(
        symbol=raw["symbol"],
        step_size=Decimal(raw["step_size"]),
        tick_size=Decimal(raw["tick_size"]),
        min_quantity=Decimal(raw["min_quantity"]),
        min_notional=Decimal(raw["min_notional"]),
    )


def _to_run(row: BacktestRunRow) -> BacktestRun:
    return BacktestRun(
        id=row.id,
        status=JobStatus(row.status),
        config=BacktestConfig(
            exchange=row.exchange,
            symbol=row.symbol,
            timeframe=Timeframe(row.timeframe),
            start=row.start_at,
            end=row.end_at,
            initial_capital=row.initial_capital,
            fee_rate=row.fee_rate,
            slippage_bps=row.slippage_bps,
            strategy_type=row.strategy_type,
            strategy_params=row.strategy_params,
            seed=row.seed,
            test_fraction=row.test_fraction,
            cost_sensitivity=row.cost_sensitivity,
            max_drawdown_tolerance_pct=row.max_drawdown_tolerance_pct,
            max_drawdown_tolerance_days=row.max_drawdown_tolerance_days,
            allow_gaps=row.allow_gaps,
            fill_timing=FillTiming(row.fill_timing),
            risk=limits_from_dict(row.risk_limits) if row.risk_limits else None,
        ),
        created_at=row.created_at,
        started_at=row.started_at,
        finished_at=row.finished_at,
        data_hash=row.data_hash,
        candles_count=row.candles_count,
        market_info=_market_from_json(row.market_info) if row.market_info else None,
        metrics=row.metrics,
        segments=row.segments,
        periods=row.periods,
        cost_ladder=row.cost_ladder,
        data_quality=row.data_quality,
        risk_report=row.risk_report,
        sweep_id=row.sweep_id,
        error=row.error,
    )


class SqlAlchemyBacktestStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.candles = SqlAlchemyCandleRepository(session)

    async def add_run(self, run: BacktestRun) -> None:
        c = run.config
        self._session.add(
            BacktestRunRow(
                id=run.id,
                status=run.status.value,
                exchange=c.exchange,
                symbol=c.symbol,
                timeframe=c.timeframe.value,
                start_at=c.start,
                end_at=c.end,
                initial_capital=c.initial_capital,
                fee_rate=c.fee_rate,
                slippage_bps=c.slippage_bps,
                seed=c.seed,
                test_fraction=c.test_fraction,
                cost_sensitivity=c.cost_sensitivity,
                max_drawdown_tolerance_pct=c.max_drawdown_tolerance_pct,
                max_drawdown_tolerance_days=c.max_drawdown_tolerance_days,
                allow_gaps=c.allow_gaps,
                fill_timing=c.fill_timing.value,
                risk_limits=limits_to_dict(c.risk) if c.risk else None,
                data_quality=run.data_quality,
                sweep_id=run.sweep_id,
                strategy_type=c.strategy_type,
                strategy_params=dict(c.strategy_params),
                created_at=run.created_at,
            )
        )
        await self._session.flush()

    async def get_run(self, run_id: UUID) -> BacktestRun | None:
        row = await self._session.get(BacktestRunRow, run_id)
        return _to_run(row) if row else None

    async def add_sweep(self, sweep: BacktestSweep) -> None:
        self._session.add(
            BacktestSweepRow(
                id=sweep.id,
                created_at=sweep.created_at,
                strategy_type=sweep.strategy_type,
                grid=sweep.grid,
                skipped=sweep.skipped,
                run_count=sweep.run_count,
            )
        )
        await self._session.flush()

    async def get_sweep(self, sweep_id: UUID) -> BacktestSweep | None:
        row = await self._session.get(BacktestSweepRow, sweep_id)
        if row is None:
            return None
        return BacktestSweep(
            id=row.id,
            created_at=row.created_at,
            strategy_type=row.strategy_type,
            grid=row.grid,
            skipped=row.skipped,
            run_count=row.run_count,
        )

    async def list_sweep_runs(self, sweep_id: UUID) -> list[BacktestRun]:
        result = await self._session.execute(
            select(BacktestRunRow)
            .where(BacktestRunRow.sweep_id == sweep_id)
            .order_by(BacktestRunRow.created_at)
        )
        return [_to_run(r) for r in result.scalars()]

    async def count_runs(self) -> int:
        result = await self._session.execute(select(func.count()).select_from(BacktestRunRow))
        return int(result.scalar_one())

    async def count_prior_trials(self, sweep: BacktestSweep, base: BacktestConfig) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(BacktestRunRow)
            .where(
                BacktestRunRow.status == JobStatus.COMPLETED.value,
                BacktestRunRow.strategy_type == base.strategy_type,
                BacktestRunRow.exchange == base.exchange,
                BacktestRunRow.symbol == base.symbol,
                BacktestRunRow.timeframe == base.timeframe.value,
                BacktestRunRow.start_at < base.end,
                BacktestRunRow.end_at > base.start,
                BacktestRunRow.created_at < sweep.created_at,
                or_(BacktestRunRow.sweep_id.is_(None), BacktestRunRow.sweep_id != sweep.id),
            )
        )
        return int(result.scalar_one())

    async def list_runs(self, limit: int, offset: int = 0) -> list[BacktestRun]:
        result = await self._session.execute(
            select(BacktestRunRow)
            .order_by(BacktestRunRow.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [_to_run(r) for r in result.scalars()]

    async def claim_next_queued(self) -> BacktestRun | None:
        result = await self._session.execute(
            select(BacktestRunRow)
            .where(BacktestRunRow.status == JobStatus.QUEUED.value)
            .order_by(BacktestRunRow.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        row.status = JobStatus.RUNNING.value
        row.started_at = func.now()
        await self._session.flush()
        await self._session.refresh(row)
        return _to_run(row)

    async def requeue_running(self) -> int:
        result = await self._session.execute(
            update(BacktestRunRow)
            .where(BacktestRunRow.status == JobStatus.RUNNING.value)
            .values(status=JobStatus.QUEUED.value)
        )
        return int(result.rowcount or 0)  # type: ignore[attr-defined]

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
        equity_curve: list[EquityPoint],
        fills: list[Fill],
    ) -> None:
        await self._session.execute(
            update(BacktestRunRow)
            .where(BacktestRunRow.id == run_id)
            .values(
                status=JobStatus.COMPLETED.value,
                data_hash=data_hash,
                candles_count=candles_count,
                market_info=_market_to_json(market_info),
                metrics=metrics,
                segments=segments,
                periods=periods,
                cost_ladder=cost_ladder,
                data_quality=data_quality,
                risk_report=risk_report,
                equity_curve=[[p.time.isoformat(), str(p.equity)] for p in equity_curve],
                finished_at=func.now(),
            )
        )
        self._session.add_all(
            BacktestTradeRow(
                run_id=run_id,
                seq=i,
                time=f.time,
                side=f.side.value,
                quantity=f.quantity,
                price=f.price,
                fee=f.fee,
            )
            for i, f in enumerate(fills)
        )

    async def mark_failed(self, run_id: UUID, error: str) -> None:
        await self._session.execute(
            update(BacktestRunRow)
            .where(BacktestRunRow.id == run_id)
            .values(status=JobStatus.FAILED.value, error=error, finished_at=func.now())
        )

    async def list_trades(self, run_id: UUID) -> list[Fill]:
        result = await self._session.execute(
            select(BacktestTradeRow)
            .where(BacktestTradeRow.run_id == run_id)
            .order_by(BacktestTradeRow.seq)
        )
        return [Fill(r.time, Side(r.side), r.quantity, r.price, r.fee) for r in result.scalars()]

    async def get_equity_curve(self, run_id: UUID) -> list[EquityPoint] | None:
        result = await self._session.execute(
            select(BacktestRunRow.equity_curve).where(BacktestRunRow.id == run_id)
        )
        raw = result.scalar_one_or_none()
        if raw is None:
            return None
        return [EquityPoint(datetime.fromisoformat(t), Decimal(v)) for t, v in raw]

    async def commit(self) -> None:
        await self._session.commit()
