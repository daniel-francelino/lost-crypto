from collections.abc import Callable, Mapping
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, replace
from datetime import timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from core.clock import Clock
from core.errors import ConflictError
from core.ids import IdGenerator
from modules.analytics.domain.metrics import Metrics, compute_metrics
from modules.audit.models import AuditEvent
from modules.backtesting.domain.models import EquityPoint
from modules.bots.application.errors import BotNameTaken, BotNotFound, InvalidBotConnection
from modules.bots.application.live import IssuedApproval, LiveService, Readiness
from modules.bots.application.ports import BotStore
from modules.bots.domain.changes import config_changes
from modules.bots.domain.interventions import (
    AFTER_DRAWDOWN_PCT,
    INTERVENTION_EVENTS,
    SYSTEM_INTERVENTION_EVENTS,
)
from modules.bots.domain.interventions import (
    summarize as summarize_interventions,
)
from modules.bots.domain.models import Bot, BotConfig, BotState, ExecutionMode
from modules.exchanges.application.registry import ExchangeRegistry
from modules.exchanges.domain.connections import ConnectionStatus, Environment
from modules.exchanges.domain.models import PositionSide, TradingProduct
from modules.execution.application.ports import SignalRecord
from modules.execution.domain.orders import Order
from modules.portfolio.domain.models import PortfolioState
from modules.portfolio.domain.perpetuals import PerpetualLedger
from modules.strategies.domain.registry import StrategyRegistry

BotStoreFactory = Callable[[], AbstractAsyncContextManager[BotStore]]


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
    product: TradingProduct = TradingProduct.SPOT
    position_side: PositionSide | None = None
    leverage: int = 1
    isolated_margin: Decimal = Decimal(0)
    reserved_margin: Decimal = Decimal(0)
    liquidation_price: Decimal | None = None
    funding_paid: Decimal = Decimal(0)
    funding_received: Decimal = Decimal(0)


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
    interventions_30d: int = 0


@dataclass(frozen=True, slots=True)
class PortfolioSummary:
    """Bots of one mode and quote currency added up. Amounts in different currencies are never
    mixed, and neither are real and simulated money."""

    mode: ExecutionMode
    quote_currency: str
    bots: int
    running: int
    open_positions: int
    initial_capital: Decimal
    equity: Decimal
    realized_pnl: Decimal
    fees_paid: Decimal

    @property
    def return_pct(self) -> Decimal:
        if self.initial_capital == 0:
            return Decimal(0)
        return (self.equity - self.initial_capital) / self.initial_capital * 100


def summarize(rows: list[tuple[BotOverview, Decimal]]) -> list[PortfolioSummary]:
    """Group overview rows (with each bot's initial capital) by mode and quote currency."""
    groups: dict[tuple[ExecutionMode, str], list[tuple[BotOverview, Decimal]]] = {}
    for row, capital in rows:
        quote = (
            "USDT"
            if row.bot.config.product is TradingProduct.LINEAR_PERPETUAL
            else row.bot.config.symbol.split("/")[-1]
        )
        groups.setdefault((row.bot.config.mode, quote), []).append((row, capital))
    return [
        PortfolioSummary(
            mode=mode,
            quote_currency=quote,
            bots=len(items),
            running=sum(1 for r, _ in items if r.bot.observed_state is BotState.RUNNING),
            open_positions=sum(1 for r, _ in items if r.in_position),
            initial_capital=sum((c for _, c in items), Decimal(0)),
            equity=sum((r.equity for r, _ in items), Decimal(0)),
            realized_pnl=sum((r.realized_pnl for r, _ in items), Decimal(0)),
            fees_paid=sum((r.fees_paid for r, _ in items), Decimal(0)),
        )
        for (mode, quote), items in sorted(
            groups.items(), key=lambda kv: (kv[0][0].value, kv[0][1])
        )
    ]


class BotService:
    """API-side bot use cases. Commands only change ``desired_state``; the worker acts on it."""

    def __init__(
        self,
        stores: BotStoreFactory,
        registry: StrategyRegistry,
        exchanges: ExchangeRegistry,
        clock: Clock,
        ids: IdGenerator,
        live: LiveService,
    ) -> None:
        self._stores = stores
        self._live = live
        self._registry = registry
        self._exchanges = exchanges
        self._clock = clock
        self._ids = ids

    def default_fee_rate(self, exchange: str) -> Decimal:
        """The exchange's taker fee: market orders are takers."""
        return self._exchanges.profile(exchange).fees.taker_rate

    async def create(self, config: BotConfig) -> Bot:
        if config.product is not TradingProduct.SPOT:
            raise ConflictError(
                "futures trading is not enabled: portfolio ledger and worker execution support "
                "must be completed first"
            )
        profile = self._exchanges.require(config.exchange, config.timeframe)
        if config.product not in profile.capabilities.products:
            raise ConflictError(
                f"{config.exchange} does not support {config.product.value} trading"
            )
        if config.leverage > profile.capabilities.max_leverage:
            raise ConflictError(
                f"{config.exchange} supports up to {profile.capabilities.max_leverage}x leverage"
            )
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

    async def update(
        self,
        bot_id: UUID,
        changes: Mapping[str, Any],
        *,
        allow_live: bool = False,
        actor: str = "api",
        reason: str | None = None,
    ) -> Bot:
        if changes.get("mode") is ExecutionMode.LIVE and not allow_live:
            raise ConflictError("use POST /bots/{id}/promote-to-live to switch a bot to live")
        async with self._stores() as store:
            bot = await self._get(store, bot_id)
            bot.ensure_editable()
            old_config = bot.config
            config = replace(old_config, **changes)
            if config.product is not TradingProduct.SPOT:
                raise ConflictError(
                    "futures trading is not enabled: portfolio ledger and worker execution "
                    "support must be completed first"
                )
            profile = self._exchanges.require(config.exchange, config.timeframe)
            if config.product not in profile.capabilities.products:
                raise ConflictError(
                    f"{config.exchange} does not support {config.product.value} trading"
                )
            if config.leverage > profile.capabilities.max_leverage:
                raise ConflictError(
                    f"{config.exchange} supports up to "
                    f"{profile.capabilities.max_leverage}x leverage"
                )
            self._registry.create(config.strategy_type, config.strategy_params)
            await self._check_connection(store, config)
            version = bot.config_version + 1
            if not await store.bots.update_config(bot_id, config, version):
                raise BotNameTaken(f"a bot named {config.name!r} already exists")
            await store.bots.set_live_approval(bot_id, None, None)  # a new version is unapproved
            await store.audit.add(
                self._event(
                    "bot.config_updated",
                    bot,
                    {
                        "fields": sorted(changes),
                        "version": version,
                        "changes": config_changes(old_config, config),
                        **({"reason": reason.strip()} if reason and reason.strip() else {}),
                    },
                    actor,
                )
            )
            await store.commit()
        bot.config, bot.config_version = config, version
        return bot

    @staticmethod
    async def _check_connection(store: BotStore, config: BotConfig) -> None:
        """A testnet bot must point at an active testnet connection of its own exchange."""
        if not config.mode.uses_exchange:
            return
        assert config.connection_id is not None  # guaranteed by BotConfig
        allowed_environments = (
            {Environment.LIVE}
            if config.mode is ExecutionMode.LIVE
            else (
                {Environment.DEMO}
                if config.product is TradingProduct.LINEAR_PERPETUAL
                else {Environment.DEMO, Environment.TESTNET}
            )
        )
        connection = await store.connections.get(config.connection_id)
        if connection is None:
            raise InvalidBotConnection("the exchange connection does not exist")
        if connection.status is not ConnectionStatus.ACTIVE:
            raise InvalidBotConnection(f"the exchange connection is {connection.status.value}")
        if connection.environment not in allowed_environments:
            expected = " or ".join(
                sorted(environment.value for environment in allowed_environments)
            )
            raise InvalidBotConnection(
                f"{config.mode.value} bots for {config.product.value} need a {expected} connection"
            )
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

    async def start(
        self, bot_id: UUID, confirmation_token: str | None = None, actor: str = "api"
    ) -> Bot:
        async with self._stores() as store:
            bot = await self._get(store, bot_id)
            await self._check_perpetual_owner(store, bot)
            if bot.config.mode is ExecutionMode.LIVE:
                await self._live.consume(store, bot, confirmation_token, actor)
            bot.request_start()
            await store.bots.set_desired(bot_id, bot.desired_state)
            await store.audit.add(self._event("bot.start_requested", bot, {}, actor))
            await store.commit()
        return bot

    @staticmethod
    async def _check_perpetual_owner(store: BotStore, bot: Bot) -> None:
        """Serialize starts by exchange connection, then enforce one active bot per contract.

        The connection row is the transaction lock shared by every start using the same
        account. This closes the race where two API requests both observe an unowned contract.
        """
        config = bot.config
        if config.product is not TradingProduct.LINEAR_PERPETUAL:
            return
        if config.connection_id is None:
            # Paper ledgers do not share exchange exposure. Exchange modes are validated by
            # BotConfig and always carry a connection id.
            return
        locked = await store.connections.lock(config.connection_id)
        if locked is None:
            raise InvalidBotConnection("the exchange connection does not exist")
        await BotService._check_connection(store, config)
        owner = await store.bots.find_active_perpetual_owner(
            config.connection_id, config.symbol, bot.id
        )
        if owner is not None:
            raise ConflictError(
                f"{config.exchange} {config.symbol} is already owned by active futures bot "
                f"{owner.config.name!r}; stop and fully close it before starting another"
            )

    async def live_readiness(self, bot_id: UUID) -> Readiness:
        _, readiness = await self._live.evaluate(bot_id)
        return readiness

    async def request_live_approval(
        self, bot_id: UUID, typed_name: str, actor: str
    ) -> IssuedApproval:
        return await self._live.request_approval(bot_id, typed_name, actor)

    async def promote_to_live(self, bot_id: UUID, connection_id: UUID) -> Bot:
        """Point a stopped bot at a live connection. It still needs readiness + an approval.

        The virtual portfolio restarts from the allocated capital (the real account is the
        source of truth now); the paper history that earned the promotion is kept.
        """
        bot = await self.get(bot_id)
        if bot.config.product is not TradingProduct.SPOT:
            raise ConflictError("live futures promotion is not enabled")
        async with self._stores() as store:
            current = await store.portfolio.get(bot_id)
        if current is not None and current.quantity > 0:
            raise ConflictError("close the open paper position before promoting to live")
        bot = await self.update(
            bot_id, {"mode": ExecutionMode.LIVE, "connection_id": connection_id}, allow_live=True
        )
        async with self._stores() as store:
            await store.portfolio.save(PortfolioState.new(bot_id, bot.config.initial_capital))
            await store.audit.add(
                self._event("live.promoted", bot, {"connection": str(connection_id)})
            )
            await store.commit()
        return bot

    async def pause(self, bot_id: UUID, *, reason: str | None = None, actor: str = "api") -> Bot:
        return await self._command(bot_id, "pause", Bot.request_pause, reason=reason, actor=actor)

    async def stop(self, bot_id: UUID, *, reason: str | None = None, actor: str = "api") -> Bot:
        current = await self.get(bot_id)
        if current.config.product is TradingProduct.LINEAR_PERPETUAL:
            async with self._stores() as store:
                bot = await self._get(store, bot_id)
                if bot.config.connection_id is not None:
                    await store.connections.lock(bot.config.connection_id)
                ledger = await store.perpetual_portfolio.get(bot_id)
                if ledger is not None and ledger.position is not None:
                    raise ConflictError(
                        "close the futures position before stopping the bot; the active bot "
                        "must retain ownership of its exchange symbol"
                    )
                if ledger is not None and ledger.reserved_margin > 0:
                    raise ConflictError("resolve pending futures orders before stopping the bot")
                if await store.orders.count_unresolved(bot_id):
                    raise ConflictError("resolve pending futures orders before stopping the bot")
                bot.request_stop()
                await store.bots.set_desired(bot_id, bot.desired_state)
                payload = {"reason": reason.strip()} if reason and reason.strip() else {}
                await store.audit.add(self._event("bot.stop_requested", bot, payload, actor))
                await store.bots.set_live_approval(bot_id, None, None)
                await store.commit()
            return bot
        bot = await self._command(bot_id, "stop", Bot.request_stop, reason=reason, actor=actor)
        async with self._stores() as store:  # stopping ends the live approval, whatever the mode
            await store.bots.set_live_approval(bot_id, None, None)
            await store.commit()
        return bot

    async def delete(self, bot_id: UUID, *, reason: str | None = None, actor: str = "api") -> None:
        """Delete a stopped bot and its history. Live bots are never deleted (their orders are
        the record of real money) and a bot with an open position must close it first."""
        async with self._stores() as store:
            bot = await self._get(store, bot_id)
            bot.ensure_editable()
            if bot.config.mode is ExecutionMode.LIVE:
                raise ConflictError("a live bot is kept for the record and cannot be deleted")
            perpetual = await store.perpetual_portfolio.get(bot_id)
            if perpetual is not None and perpetual.position is not None:
                raise ConflictError("close the open futures position before deleting the bot")
            if perpetual is not None and perpetual.reserved_margin > 0:
                raise ConflictError("resolve futures orders before deleting the bot")
            if await store.orders.count_unresolved(bot_id):
                raise ConflictError("resolve pending orders before deleting the bot")
            portfolio = await store.portfolio.get(bot_id)
            if portfolio is not None and portfolio.quantity > 0:
                raise ConflictError("close the open position before deleting the bot")
            payload: dict[str, Any] = {
                "name": bot.config.name,
                "strategy_type": bot.config.strategy_type,
                "symbol": bot.config.symbol,
                "mode": bot.config.mode.value,
                "orders": await store.orders.count_by_bot(bot_id),
            }
            if reason and reason.strip():
                payload["reason"] = reason.strip()
            await store.audit.add(self._event("bot.deleted", bot, payload, actor))
            await store.bots.delete(bot_id)
            await store.commit()

    async def reset_portfolio(
        self, bot_id: UUID, *, reason: str | None = None, actor: str = "api"
    ) -> None:
        """Restart the virtual portfolio from the initial capital (stopped bots only)."""
        async with self._stores() as store:
            bot = await self._get(store, bot_id)
            bot.ensure_editable()
            if bot.config.product is TradingProduct.LINEAR_PERPETUAL:
                ledger = await store.perpetual_portfolio.get(bot_id)
                if ledger is not None and ledger.position is not None:
                    raise ConflictError("close the open futures position before resetting")
                if ledger is not None and ledger.reserved_margin > 0:
                    raise ConflictError("resolve futures orders before resetting the portfolio")
                if await store.orders.count_unresolved(bot_id):
                    raise ConflictError("resolve pending orders before resetting the portfolio")
                await store.perpetual_portfolio.reset(bot_id, bot.config.initial_capital)
            else:
                await store.portfolio.reset(bot_id, bot.config.initial_capital)
            payload = {"reason": reason.strip()} if reason and reason.strip() else {}
            await store.audit.add(self._event("bot.portfolio_reset", bot, payload, actor))
            await store.commit()

    async def orders(
        self, bot_id: UUID, limit: int = 100, offset: int = 0
    ) -> tuple[list[Order], int]:
        async with self._stores() as store:
            await self._get(store, bot_id)
            orders = await store.orders.list_by_bot(bot_id, limit, offset)
            return orders, await store.orders.count_by_bot(bot_id)

    async def signals(
        self, bot_id: UUID, limit: int = 100, offset: int = 0
    ) -> tuple[list[SignalRecord], int]:
        async with self._stores() as store:
            await self._get(store, bot_id)
            signals = await store.signals.list_by_bot(bot_id, limit, offset)
            return signals, await store.signals.count_by_bot(bot_id)

    async def portfolio(self, bot_id: UUID) -> PortfolioView:
        async with self._stores() as store:
            bot = await self._get(store, bot_id)
            if bot.config.product is TradingProduct.LINEAR_PERPETUAL:
                ledger = await store.perpetual_portfolio.get(bot_id) or PerpetualLedger.new(
                    bot_id, bot.config.initial_capital
                )
                snapshots = await store.perpetual_portfolio.list_snapshots(bot_id, limit=1)
                mark = snapshots[-1].mark_price if snapshots else ledger.mark_price
                position = ledger.position
                return PortfolioView(
                    initial_capital=bot.config.initial_capital,
                    cash=ledger.wallet_balance,
                    quantity=position.quantity if position else Decimal(0),
                    avg_entry_price=position.entry_price if position else Decimal(0),
                    last_price=mark,
                    equity=ledger.equity(mark) if mark is not None else ledger.wallet_balance,
                    unrealized_pnl=(position.unrealized_pnl(mark)
                                    if position is not None and mark is not None else Decimal(0)),
                    realized_pnl=ledger.realized_pnl,
                    fees_paid=ledger.fees_paid,
                    stop_price=position.stop_price if position else None,
                    take_profit_price=position.take_profit_price if position else None,
                    reserved_cash=Decimal(0),
                    native_stop_active=False,
                    product=TradingProduct.LINEAR_PERPETUAL,
                    position_side=position.side if position else None,
                    leverage=position.leverage if position else bot.config.leverage,
                    isolated_margin=position.isolated_margin if position else Decimal(0),
                    reserved_margin=ledger.reserved_margin,
                    liquidation_price=ledger.exchange_liquidation_price or (
                        ledger.liquidation_estimate(ledger.maintenance_margin_rate)
                        if position is not None and ledger.maintenance_margin_rate > 0
                        else None
                    ),
                    funding_paid=ledger.funding_paid,
                    funding_received=ledger.funding_received,
                )
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
                    interventions_30d=await self._intervention_count(bot.id),
                )
            )
        return rows

    async def summary(self) -> list[PortfolioSummary]:
        """Totals across bots, so the dashboard never has to add money itself."""
        rows = await self.overview()
        return summarize([(row, row.bot.config.initial_capital) for row in rows])

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
            bar=bot.config.timeframe.delta,
            benchmark_prices=[s.price for s in snapshots],
            in_market=[s.quantity > 0 for s in snapshots],
        )

    async def equity_curve(self, bot_id: UUID, limit: int = 2000) -> list[EquityPoint]:
        async with self._stores() as store:
            bot = await self._get(store, bot_id)
            if bot.config.product is TradingProduct.LINEAR_PERPETUAL:
                snapshots = await store.perpetual_portfolio.list_snapshots(
                    bot_id, limit=limit
                )
                return [EquityPoint(s.taken_at, s.equity) for s in snapshots]
            spot_snapshots = await store.portfolio.list_snapshots(bot_id, limit=limit)
            return [EquityPoint(s.taken_at, s.equity) for s in spot_snapshots]

    async def _command(
        self,
        bot_id: UUID,
        name: str,
        transition: Callable[[Bot], None],
        *,
        reason: str | None = None,
        actor: str = "api",
    ) -> Bot:
        async with self._stores() as store:
            bot = await self._get(store, bot_id)
            transition(bot)
            await store.bots.set_desired(bot_id, bot.desired_state)
            payload = {"reason": reason.strip()} if reason and reason.strip() else {}
            await store.audit.add(self._event(f"bot.{name}_requested", bot, payload, actor))
            await store.commit()
        return bot

    @staticmethod
    async def _get(store: BotStore, bot_id: UUID) -> Bot:
        bot = await store.bots.get(bot_id)
        if bot is None:
            raise BotNotFound(str(bot_id))
        return bot

    async def _intervention_count(self, bot_id: UUID) -> int:
        async with self._stores() as store:
            return await store.audit.count_events(
                bot_id, INTERVENTION_EVENTS, since=self._clock.now() - timedelta(days=30)
            )

    async def interventions(self, bot_id: UUID, days: int = 30) -> dict[str, Any]:
        since = self._clock.now() - timedelta(days=days)
        async with self._stores() as store:
            await self._get(store, bot_id)
            events = await store.audit.list_events_since(bot_id, INTERVENTION_EVENTS, since, 100)
            contexts = {
                event.occurred_at: await store.portfolio.equity_context_at(
                    bot_id, event.occurred_at
                )
                for event in events
                if event.occurred_at is not None
            }
            system = {
                "kill_switch_activated": await store.audit.count_all(
                    None, SYSTEM_INTERVENTION_EVENTS[0], since
                ),
                "kill_switch_released": await store.audit.count_all(
                    None, SYSTEM_INTERVENTION_EVENTS[1], since
                ),
            }
            counts = {
                event_type: await store.audit.count_events(bot_id, (event_type,), since=since)
                for event_type in INTERVENTION_EVENTS
            }
        totals = summarize_interventions(events, contexts, AFTER_DRAWDOWN_PCT)
        totals["total"] = sum(counts.values())
        totals["by_type"] = counts
        return {
            "days": days,
            **totals,
            "drawdown_threshold_pct": str(AFTER_DRAWDOWN_PCT),
            "system": system,
        }

    @staticmethod
    def _event(
        event_type: str, bot: Bot, payload: dict[str, Any], actor: str = "api"
    ) -> AuditEvent:
        return AuditEvent(
            event_type, "bot", str(bot.id), actor=actor, bot_id=bot.id, payload=payload
        )
