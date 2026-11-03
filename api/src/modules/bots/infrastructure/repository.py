from datetime import datetime
from uuid import UUID

from sqlalchemy import exists, func, or_, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from modules.bots.application.ports import LiveApproval
from modules.bots.domain.models import Bot, BotConfig, BotState, ExecutionMode
from modules.bots.infrastructure.orm import BotRow, LiveApprovalRow
from modules.exchanges.domain.models import MarginMode, TradingProduct
from modules.execution.domain.orders import OrderStatus
from modules.execution.infrastructure.orm import OrderRow
from modules.market_data.domain.models import Timeframe
from modules.portfolio.infrastructure.orm import PerpetualPortfolioRow
from modules.risk_management.domain.models import DrawdownAction, RiskLimits


def _to_bot(row: BotRow) -> Bot:
    return Bot(
        id=row.id,
        config=BotConfig(
            name=row.name,
            exchange=row.exchange,
            strategy_type=row.strategy_type,
            strategy_params=row.strategy_params,
            symbol=row.symbol,
            product=TradingProduct(row.product),
            leverage=row.leverage,
            margin_mode=MarginMode(row.margin_mode) if row.margin_mode else None,
            allow_short=row.allow_short,
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
                min_liquidation_distance_pct=row.min_liquidation_distance_pct,
                require_stop_loss=row.require_stop_loss,
                max_candle_range_pct=row.max_candle_range_pct,
                max_order_pct_of_volume=row.max_order_pct_of_volume,
                max_close_jump_pct=row.max_close_jump_pct,
                drawdown_action=DrawdownAction(row.drawdown_action),
            ),
            mode=ExecutionMode(row.mode),
            connection_id=row.exchange_connection_id,
        ),
        desired_state=BotState(row.desired_state),
        observed_state=BotState(row.observed_state),
        config_version=row.config_version,
        created_at=row.created_at,
        updated_at=row.updated_at,
        last_heartbeat_at=row.last_heartbeat_at,
        last_error=row.last_error,
        live_approved_config_version=row.live_approved_config_version,
        live_approved_at=row.live_approved_at,
    )


def _config_values(config: BotConfig) -> dict[str, object]:
    return {
        "name": config.name,
        "exchange": config.exchange,
        "strategy_type": config.strategy_type,
        "strategy_params": dict(config.strategy_params),
        "symbol": config.symbol,
        "product": config.product.value,
        "leverage": config.leverage,
        "margin_mode": config.margin_mode.value if config.margin_mode else None,
        "allow_short": config.allow_short,
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
        "min_liquidation_distance_pct": config.risk.min_liquidation_distance_pct,
        "require_stop_loss": config.risk.require_stop_loss,
        "max_candle_range_pct": config.risk.max_candle_range_pct,
        "max_order_pct_of_volume": config.risk.max_order_pct_of_volume,
        "max_close_jump_pct": config.risk.max_close_jump_pct,
        "drawdown_action": config.risk.drawdown_action.value,
        "mode": config.mode.value,
        "exchange_connection_id": config.connection_id,
    }


_DELETE_STATEMENTS = (
    "DELETE FROM order_fills WHERE order_id IN (SELECT id FROM orders WHERE bot_id = :bot)",
    "DELETE FROM orders WHERE bot_id = :bot",
    "DELETE FROM trading_signals WHERE bot_id = :bot",
    "DELETE FROM portfolio_snapshots WHERE bot_id = :bot",
    "DELETE FROM bot_portfolios WHERE bot_id = :bot",
    "DELETE FROM perpetual_portfolio_snapshots WHERE bot_id = :bot",
    "DELETE FROM bot_perpetual_ledger_entries WHERE bot_id = :bot",
    "DELETE FROM bot_perpetual_portfolios WHERE bot_id = :bot",
    "DELETE FROM live_approvals WHERE bot_id = :bot",
    "DELETE FROM parity_runs WHERE bot_id = :bot",
    "DELETE FROM trading_sessions WHERE bot_id = :bot",
    "DELETE FROM alerts WHERE bot_id = :bot",
    "DELETE FROM bots WHERE id = :bot",
)


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

    async def list_connection_bots(self, connection_id: UUID) -> list[Bot]:
        result = await self._session.execute(
            select(BotRow)
            .where(BotRow.exchange_connection_id == connection_id)
            .order_by(BotRow.created_at.desc())
        )
        return [_to_bot(r) for r in result.scalars()]

    async def list_active(self) -> list[Bot]:
        result = await self._session.execute(
            select(BotRow)
            .where(
                or_(
                    BotRow.desired_state != BotState.STOPPED.value,
                    # An errored bot whose stop was requested must still be settled to 'stopped'.
                    BotRow.observed_state != BotState.STOPPED.value,
                )
            )
            .order_by(BotRow.created_at)
        )
        return [_to_bot(r) for r in result.scalars()]

    async def find_active_perpetual_owner(
        self, connection_id: UUID, symbol: str, exclude_bot_id: UUID
    ) -> Bot | None:
        open_exposure = exists(
            select(1).where(
                PerpetualPortfolioRow.bot_id == BotRow.id,
                or_(
                    PerpetualPortfolioRow.quantity > 0,
                    PerpetualPortfolioRow.reserved_margin > 0,
                ),
            )
        )
        unresolved_orders = exists(
            select(1).where(
                OrderRow.bot_id == BotRow.id,
                OrderRow.product == TradingProduct.LINEAR_PERPETUAL.value,
                OrderRow.status.in_(
                    [
                        OrderStatus.INTENT.value,
                        OrderStatus.SUBMITTING.value,
                        OrderStatus.OPEN.value,
                        OrderStatus.PARTIALLY_FILLED.value,
                        OrderStatus.UNKNOWN.value,
                    ]
                ),
            )
        )
        result = await self._session.execute(
            select(BotRow)
            .where(
                BotRow.id != exclude_bot_id,
                BotRow.exchange_connection_id == connection_id,
                BotRow.symbol == symbol,
                BotRow.product == TradingProduct.LINEAR_PERPETUAL.value,
                or_(
                    BotRow.desired_state != BotState.STOPPED.value,
                    BotRow.observed_state != BotState.STOPPED.value,
                    open_exposure,
                    unresolved_orders,
                ),
            )
            .order_by(BotRow.created_at)
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return _to_bot(row) if row else None

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

    async def set_live_approval(
        self, bot_id: UUID, config_version: int | None, at: datetime | None
    ) -> None:
        await self._session.execute(
            update(BotRow)
            .where(BotRow.id == bot_id)
            .values(live_approved_config_version=config_version, live_approved_at=at)
        )

    async def set_mode(self, bot_id: UUID, mode: str, connection_id: UUID | None) -> None:
        await self._session.execute(
            update(BotRow)
            .where(BotRow.id == bot_id)
            .values(mode=mode, exchange_connection_id=connection_id, updated_at=func.now())
        )

    async def delete(self, bot_id: UUID) -> None:
        for statement in _DELETE_STATEMENTS:
            await self._session.execute(text(statement), {"bot": bot_id})

    async def heartbeat(self, bot_ids: list[UUID], at: datetime) -> None:
        await self._session.execute(
            update(BotRow).where(BotRow.id.in_(bot_ids)).values(last_heartbeat_at=at)
        )


class SqlAlchemyLiveApprovalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def supersede(self, bot_id: UUID, at: datetime) -> None:
        await self._session.execute(
            update(LiveApprovalRow)
            .where(LiveApprovalRow.bot_id == bot_id, LiveApprovalRow.used_at.is_(None))
            .values(used_at=at)
        )

    async def add(self, approval: LiveApproval) -> None:
        self._session.add(
            LiveApprovalRow(
                id=approval.id,
                bot_id=approval.bot_id,
                config_version=approval.config_version,
                token_hash=approval.token_hash,
                created_by=approval.created_by,
                created_at=approval.created_at,
                expires_at=approval.expires_at,
            )
        )
        await self._session.flush()

    async def find(self, bot_id: UUID, token_hash: str) -> LiveApproval | None:
        result = await self._session.execute(
            select(LiveApprovalRow).where(
                LiveApprovalRow.bot_id == bot_id, LiveApprovalRow.token_hash == token_hash
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return LiveApproval(
            row.id,
            row.bot_id,
            row.config_version,
            row.token_hash,
            row.created_by,
            row.created_at,
            row.expires_at,
            row.used_at,
        )

    async def mark_used(self, approval_id: UUID, at: datetime) -> None:
        await self._session.execute(
            update(LiveApprovalRow).where(LiveApprovalRow.id == approval_id).values(used_at=at)
        )
