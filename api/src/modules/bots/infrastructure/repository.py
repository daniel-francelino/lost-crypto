from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from modules.bots.domain.models import Bot, BotConfig, BotState, ExecutionMode
from modules.bots.infrastructure.orm import BotRow
from modules.market_data.domain.models import Timeframe
from modules.risk_management.domain.models import RiskLimits


def _to_bot(row: BotRow) -> Bot:
    return Bot(
        id=row.id,
        config=BotConfig(
            name=row.name,
            exchange=row.exchange,
            strategy_type=row.strategy_type,
            strategy_params=row.strategy_params,
            symbol=row.symbol,
            timeframe=Timeframe(row.timeframe),
            initial_capital=row.initial_capital,
            fee_rate=row.fee_rate,
            slippage_bps=row.slippage_bps,
            risk=RiskLimits(
                max_position_fraction=row.max_position_fraction,
                max_order_notional=row.max_order_notional,
                max_daily_loss_pct=row.max_daily_loss_pct,
                max_drawdown_pct=row.max_drawdown_pct,
                max_consecutive_losses=row.max_consecutive_losses,
                max_risk_per_trade_pct=row.max_risk_per_trade_pct,
                require_stop_loss=row.require_stop_loss,
                max_candle_range_pct=row.max_candle_range_pct,
            ),
            mode=ExecutionMode(row.mode),
        ),
        desired_state=BotState(row.desired_state),
        observed_state=BotState(row.observed_state),
        config_version=row.config_version,
        created_at=row.created_at,
        updated_at=row.updated_at,
        last_heartbeat_at=row.last_heartbeat_at,
        last_error=row.last_error,
    )


def _config_values(config: BotConfig) -> dict[str, object]:
    return {
        "name": config.name,
        "exchange": config.exchange,
        "strategy_type": config.strategy_type,
        "strategy_params": dict(config.strategy_params),
        "symbol": config.symbol,
        "timeframe": config.timeframe.value,
        "initial_capital": config.initial_capital,
        "fee_rate": config.fee_rate,
        "slippage_bps": config.slippage_bps,
        "max_position_fraction": config.risk.max_position_fraction,
        "max_order_notional": config.risk.max_order_notional,
        "max_daily_loss_pct": config.risk.max_daily_loss_pct,
        "max_drawdown_pct": config.risk.max_drawdown_pct,
        "max_consecutive_losses": config.risk.max_consecutive_losses,
        "max_risk_per_trade_pct": config.risk.max_risk_per_trade_pct,
        "require_stop_loss": config.risk.require_stop_loss,
        "max_candle_range_pct": config.risk.max_candle_range_pct,
        "mode": config.mode.value,
    }


class SqlAlchemyBotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, bot: Bot) -> bool:
        self._session.add(
            BotRow(
                id=bot.id,
                desired_state=bot.desired_state.value,
                observed_state=bot.observed_state.value,
                config_version=bot.config_version,
                created_at=bot.created_at,
                updated_at=bot.updated_at,
                **_config_values(bot.config),
            )
        )
        try:
            await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            return False
        return True

    async def get(self, bot_id: UUID) -> Bot | None:
        row = await self._session.get(BotRow, bot_id)
        return _to_bot(row) if row else None

    async def list_bots(self, limit: int) -> list[Bot]:
        result = await self._session.execute(
            select(BotRow).order_by(BotRow.created_at.desc()).limit(limit)
        )
        return [_to_bot(r) for r in result.scalars()]

    async def list_active(self) -> list[Bot]:
        result = await self._session.execute(
            select(BotRow)
            .where(
                or_(
                    BotRow.desired_state != BotState.STOPPED.value,
                    BotRow.observed_state.notin_([BotState.STOPPED.value, BotState.ERROR.value]),
                )
            )
            .order_by(BotRow.created_at)
        )
        return [_to_bot(r) for r in result.scalars()]

    async def update_config(self, bot_id: UUID, config: BotConfig, config_version: int) -> bool:
        try:
            await self._session.execute(
                update(BotRow)
                .where(BotRow.id == bot_id)
                .values(
                    config_version=config_version, updated_at=func.now(), **_config_values(config)
                )
            )
            await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            return False
        return True

    async def set_desired(self, bot_id: UUID, state: BotState) -> None:
        await self._session.execute(
            update(BotRow)
            .where(BotRow.id == bot_id)
            .values(desired_state=state.value, updated_at=func.now())
        )

    async def set_observed(self, bot_id: UUID, state: BotState, error: str | None) -> None:
        await self._session.execute(
            update(BotRow)
            .where(BotRow.id == bot_id)
            .values(observed_state=state.value, last_error=error, updated_at=func.now())
        )

    async def heartbeat(self, bot_ids: list[UUID], at: datetime) -> None:
        await self._session.execute(
            update(BotRow).where(BotRow.id.in_(bot_ids)).values(last_heartbeat_at=at)
        )
