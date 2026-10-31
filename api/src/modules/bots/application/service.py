from collections.abc import Callable, Mapping
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Any
from uuid import UUID

from core.clock import Clock
from core.errors import ConflictError, DomainError, NotFoundError
from core.ids import IdGenerator
from modules.analytics.domain.metrics import Metrics, compute_metrics
from modules.audit.models import AuditEvent
from modules.backtesting.domain.models import EquityPoint
from modules.bots.application.ports import BotStore
from modules.bots.domain.models import Bot, BotConfig, BotState, ExecutionMode
from modules.exchanges.application.registry import ExchangeRegistry
from modules.exchanges.domain.connections import ConnectionStatus, Environment
from modules.execution.application.ports import SignalRecord
from modules.execution.domain.orders import Order
from modules.portfolio.domain.models import PortfolioState
from modules.strategies.domain.registry import StrategyRegistry

BotStoreFactory = Callable[[], AbstractAsyncContextManager[BotStore]]


class BotNotFound(NotFoundError):
    pass


class BotNameTaken(ConflictError):
    pass


class InvalidBotConnection(DomainError):
    pass


@dataclass(frozen=True, slots=True)
class PortfolioView:
    initial_capital: Decimal
    cash: Decimal
    quantity: Decimal
    avg_entry_price: Decimal
    last_price: Decimal | None  # close of the last processed candle
    equity: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    fees_paid: Decimal
    stop_price: Decimal | None
    take_profit_price: Decimal | None
    reserved_cash: Decimal
    native_stop_active: bool


@dataclass(frozen=True, slots=True)
class BotOverview:
    """One row of the side-by-side comparison of bots."""

    bot: Bot
    equity: Decimal
    return_pct: Decimal
    realized_pnl: Decimal
    fees_paid: Decimal
    in_position: bool
    last_price: Decimal | None


class BotService:
    """API-side bot use cases. Commands only change ``desired_state``; the worker acts on it."""

    def __init__(
        self,
        stores: BotStoreFactory,
        registry: StrategyRegistry,
        exchanges: ExchangeRegistry,
        clock: Clock,
        ids: IdGenerator,
    ) -> None:
        self._stores = stores
        self._registry = registry
        self._exchanges = exchanges
        self._clock = clock
        self._ids = ids

    def default_fee_rate(self, exchange: str) -> Decimal:
        """The exchange's taker fee: market orders are takers."""
        return self._exchanges.profile(exchange).fees.taker_rate

    async def create(self, config: BotConfig) -> Bot:
        self._exchanges.require(config.exchange, config.timeframe)
        self._registry.create(config.strategy_type, config.strategy_params)  # validates
        now = self._clock.now()
        bot = Bot(
            id=self._ids.new_id(),
            config=config,
            desired_state=BotState.STOPPED,
            observed_state=BotState.STOPPED,
            config_version=1,
            created_at=now,
            updated_at=now,
        )
        async with self._stores() as store:
            await self._check_connection(store, config)
            if not await store.bots.add(bot):
                raise BotNameTaken(f"a bot named {config.name!r} already exists")
            await store.audit.add(self._event("bot.created", bot, {"name": config.name}))
            await store.commit()
        return bot

    async def update(self, bot_id: UUID, changes: Mapping[str, Any]) -> Bot:
        async with self._stores() as store:
            bot = await self._get(store, bot_id)
            bot.ensure_editable()
            config = replace(bot.config, **changes)
            self._exchanges.require(config.exchange, config.timeframe)
            self._registry.create(config.strategy_type, config.strategy_params)
            await self._check_connection(store, config)
            version = bot.config_version + 1
            if not await store.bots.update_config(bot_id, config, version):
                raise BotNameTaken(f"a bot named {config.name!r} already exists")
            await store.audit.add(
                self._event(
                    "bot.config_updated", bot, {"fields": sorted(changes), "version": version}
                )
            )
            await store.commit()
        bot.config, bot.config_version = config, version
        return bot

    @staticmethod
    async def _check_connection(store: BotStore, config: BotConfig) -> None:
        """A testnet bot must point at an active testnet connection of its own exchange."""
        if config.mode is not ExecutionMode.TESTNET:
            return
        assert config.connection_id is not None  # guaranteed by BotConfig
        connection = await store.connections.get(config.connection_id)
        if connection is None:
            raise InvalidBotConnection("the exchange connection does not exist")
        if connection.status is not ConnectionStatus.ACTIVE:
            raise InvalidBotConnection(f"the exchange connection is {connection.status.value}")
        if connection.environment is not Environment.TESTNET:
            raise InvalidBotConnection("testnet bots need a testnet connection")
        if connection.exchange != config.exchange:
            raise InvalidBotConnection(
                f"the connection is for {connection.exchange}, the bot trades on {config.exchange}"
            )

    async def get(self, bot_id: UUID) -> Bot:
        async with self._stores() as store:
            return await self._get(store, bot_id)

    async def list_bots(self, limit: int = 100) -> list[Bot]:
        async with self._stores() as store:
            return await store.bots.list_bots(limit)

    async def start(self, bot_id: UUID) -> Bot:
        return await self._command(bot_id, "start", Bot.request_start)

    async def pause(self, bot_id: UUID) -> Bot:
        return await self._command(bot_id, "pause", Bot.request_pause)

    async def stop(self, bot_id: UUID) -> Bot:
        return await self._command(bot_id, "stop", Bot.request_stop)

    async def reset_portfolio(self, bot_id: UUID) -> None:
        """Restart the virtual portfolio from the initial capital (stopped bots only)."""
        async with self._stores() as store:
            bot = await self._get(store, bot_id)
            bot.ensure_editable()
            await store.portfolio.reset(bot_id, bot.config.initial_capital)
            await store.audit.add(self._event("bot.portfolio_reset", bot, {}))
            await store.commit()

    async def orders(self, bot_id: UUID, limit: int = 100) -> list[Order]:
        async with self._stores() as store:
            await self._get(store, bot_id)
            return await store.orders.list_by_bot(bot_id, limit)

    async def signals(self, bot_id: UUID, limit: int = 100) -> list[SignalRecord]:
        async with self._stores() as store:
            await self._get(store, bot_id)
            return await store.signals.list_by_bot(bot_id, limit)

    async def portfolio(self, bot_id: UUID) -> PortfolioView:
        async with self._stores() as store:
            bot = await self._get(store, bot_id)
            state = await store.portfolio.get(bot_id) or PortfolioState.new(
                bot_id, bot.config.initial_capital
            )
            latest = await store.portfolio.list_snapshots(bot_id, limit=1)
        price = latest[0].price if latest else None
        has_position = state.quantity > 0 and price is not None
        return PortfolioView(
            initial_capital=bot.config.initial_capital,
            cash=state.cash,
            quantity=state.quantity,
            avg_entry_price=state.avg_entry_price,
            last_price=price,
            equity=state.equity(price) if price is not None else state.cash,
            unrealized_pnl=(price - state.avg_entry_price) * state.quantity
            if has_position and price is not None
            else Decimal(0),
            realized_pnl=state.realized_pnl,
            fees_paid=state.fees_paid,
            stop_price=state.stop_price,
            take_profit_price=state.take_profit_price,
            reserved_cash=state.reserved_cash,
            native_stop_active=state.stop_order_client_id is not None,
        )

    async def overview(self) -> list[BotOverview]:
        """All bots with their current equity and return, to compare strategies side by side."""
        rows: list[BotOverview] = []
        for bot in await self.list_bots(500):
            view = await self.portfolio(bot.id)
            capital = view.initial_capital
            rows.append(
                BotOverview(
                    bot=bot,
                    equity=view.equity,
                    return_pct=(view.equity - capital) / capital * 100,
                    realized_pnl=view.realized_pnl,
                    fees_paid=view.fees_paid,
                    in_position=view.quantity > 0,
                    last_price=view.last_price,
                )
            )
        return rows

    async def performance(self, bot_id: UUID) -> Metrics | None:
        """Same metrics as backtests, from the bot's snapshots and fills (net of fees)."""
        async with self._stores() as store:
            bot = await self._get(store, bot_id)
            snapshots = await store.portfolio.list_snapshots(bot_id)
            fills = await store.orders.list_fills(bot_id)
            rejected = await store.signals.count_rejected(bot_id)
            state = await store.portfolio.get(bot_id)
        if not snapshots:
            return None
        return compute_metrics(
            initial_capital=bot.config.initial_capital,
            equity_curve=[EquityPoint(s.taken_at, s.equity) for s in snapshots],
            fills=fills,
            first_price=snapshots[0].price,
            last_price=snapshots[-1].price,
            open_position=state is not None and state.quantity > 0,
            rejected_signals=rejected,
        )

    async def equity_curve(self, bot_id: UUID, limit: int = 2000) -> list[EquityPoint]:
        async with self._stores() as store:
            await self._get(store, bot_id)
            snapshots = await store.portfolio.list_snapshots(bot_id, limit=limit)
        return [EquityPoint(s.taken_at, s.equity) for s in snapshots]

    async def _command(self, bot_id: UUID, name: str, transition: Callable[[Bot], None]) -> Bot:
        async with self._stores() as store:
            bot = await self._get(store, bot_id)
            transition(bot)
            await store.bots.set_desired(bot_id, bot.desired_state)
            await store.audit.add(self._event(f"bot.{name}_requested", bot, {}))
            await store.commit()
        return bot

    @staticmethod
    async def _get(store: BotStore, bot_id: UUID) -> Bot:
        bot = await store.bots.get(bot_id)
        if bot is None:
            raise BotNotFound(str(bot_id))
        return bot

    @staticmethod
    def _event(event_type: str, bot: Bot, payload: dict[str, Any]) -> AuditEvent:
        return AuditEvent(
            event_type, "bot", str(bot.id), actor="api", bot_id=bot.id, payload=payload
        )
