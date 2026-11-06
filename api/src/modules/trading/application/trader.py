"""Paper-trading cycle of one bot.

Each closed candle is processed in ONE database transaction: protective exits, strategy
evaluation, signal records, risk decision, order + fills, portfolio, snapshot, strategy state
and audit commit together. The candle's ``bar_time`` is the idempotency key (via the
deterministic client order id and the persisted ``last_processed_bar_time``), so a crash or a
repeated run can never place the same order twice.

Orders go through the ``ExchangeGateway`` port (here the paper venue), so moving a bot to
another venue or exchange does not touch this flow.
"""

import logging
from collections import deque
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from core.clock import Clock
from core.ids import IdGenerator
from modules.analytics.domain.metrics import round_trip_pnls
from modules.audit.models import AuditEvent
from modules.bots.domain.models import Bot, BotState, ExecutionMode
from modules.exchanges.application.connections import ConnectionResolver
from modules.exchanges.application.ports import ExchangeGateway, MarketOrderRequest
from modules.exchanges.application.registry import ExchangeRegistry
from modules.exchanges.domain.models import PositionSide, TradingProduct
from modules.exchanges.errors import ExchangeRejected
from modules.execution.application.ports import SignalRecord
from modules.execution.domain.fills import slipped_price
from modules.execution.domain.orders import Order, make_client_order_id
from modules.execution.venues.paper import PaperExchangeGateway, StaticPriceFeed
from modules.market_data.domain.models import Candle, MarketInfo, floor_to_timeframe
from modules.market_data.domain.quality import CandleProblem, candle_problems
from modules.portfolio.domain.models import InsufficientFunds, PortfolioSnapshot, PortfolioState
from modules.portfolio.domain.perpetual_ledger import (
    PerpetualLedgerEntry,
    PerpetualLedgerEventKind,
)
from modules.portfolio.domain.perpetuals import InvalidPerpetualPosition
from modules.risk_management.domain.models import (
    DrawdownAction,
    GlobalExposure,
    GlobalRiskLimits,
    LiveLimits,
    RiskLimits,
    assess_signal,
    average_quote_volume,
    candle_range_pct,
    close_jump_pct,
    consecutive_losses_breached,
    daily_loss_breached,
    drawdown_breached,
)
from modules.risk_management.domain.stops import ExitReason, check_protective_exit
from modules.strategies.domain.base import Strategy
from modules.strategies.domain.registry import StrategyRegistry
from modules.strategies.domain.types import Side, Signal, SignalKind, StrategyContext
from modules.trading.application.orders import OrderExecutor
from modules.trading.application.perpetual_paper import PerpetualDemoTrader, PerpetualPaperTrader
from modules.trading.application.ports import TradingStore
from modules.trading.domain.models import TradingSession, max_signal_age, warmup_candles

logger = logging.getLogger(__name__)

VOLUME_WINDOW = 20  # candles averaged for the volume cap
MAX_LIVE_CLOCK_SKEW_MS = 5000  # beyond this the worker opens no new live positions
CLOCK_SKEW_FRESH = timedelta(minutes=10)  # an older measurement is not trusted either way

TradingStoreFactory = Callable[[], AbstractAsyncContextManager[TradingStore]]

CANDLE_CLOSE_GRACE = timedelta(seconds=2)  # let the exchange publish the closed candle
FETCH_LIMIT = 1000

# (audit event type, bot.last_error text) of a risk limit that pauses the bot
Breach = tuple[str, str]


class _CachedRules:
    """Market rules for the paper gateway, served from the trader's cache."""

    def __init__(self, trader: "BotTrader", exchange: str) -> None:
        self._trader = trader
        self._exchange = exchange

    async def fetch_market_info(self, symbol: str) -> MarketInfo:
        return await self._trader.market_info(self._exchange, symbol)


class BotTrader:
    def __init__(
        self,
        stores: TradingStoreFactory,
        registry: StrategyRegistry,
        exchanges: ExchangeRegistry,
        clock: Clock,
        ids: IdGenerator,
        global_limits: GlobalRiskLimits | None = None,
        executor: OrderExecutor | None = None,
        live_limits: LiveLimits | None = None,
        resolver: ConnectionResolver | None = None,
    ) -> None:
        self._stores = stores
        self._registry = registry
        self._exchanges = exchanges
        self._clock = clock
        self._ids = ids
        self._global_limits = global_limits or GlobalRiskLimits()
        self._markets: dict[tuple[str, str], MarketInfo] = {}
        self._prices = StaticPriceFeed()
        self._executor = executor
        self._live_limits = live_limits or LiveLimits()
        self._perpetual_paper = (
            PerpetualPaperTrader(stores, registry, exchanges, resolver, clock, ids)
            if resolver is not None
            else None
        )
        self._perpetual_demo = (
            PerpetualDemoTrader(stores, registry, exchanges, resolver, clock, ids, executor)
            if resolver is not None
            else None
        )
        self._pending: list[UUID] = []  # orders created this candle, sent after the commit
        # Recent traded value (volume x close) per bot, for the volume cap (book 1 ch. 5, O5).
        self._volumes: dict[UUID, deque[Decimal]] = {}
        self._avg_volume: Decimal | None = None
        self._close_jump: Decimal | None = None
        self._last_closes: dict[UUID, Decimal] = {}

    async def market_info(self, exchange: str, symbol: str) -> MarketInfo:
        key = (exchange, symbol)
        if key not in self._markets:
            self._markets[key] = await self._exchanges.market_data(exchange).fetch_market_info(
                symbol
            )
        return self._markets[key]

    async def process(self, bot: Bot) -> None:
        """Process every newly closed candle of a running bot."""
        cfg = bot.config
        async with self._stores() as store:
            session = await store.sessions.get_active(bot.id)
        if session is None:
            return  # the supervisor creates the session when it starts the bot

        now = self._clock.now()
        if cfg.product is TradingProduct.LINEAR_PERPETUAL:
            if cfg.mode is ExecutionMode.PAPER:
                if self._perpetual_paper is None:
                    raise RuntimeError(
                        "Futures paper trading needs a configured Demo data resolver"
                    )
                await self._perpetual_paper.process(bot, session, now)
            elif cfg.mode is ExecutionMode.TESTNET:
                if self._perpetual_demo is None:
                    raise RuntimeError("Futures Demo trading is not configured on this worker")
                await self._perpetual_demo.process(bot, session, now)
            else:
                raise RuntimeError("live Futures trading is disabled")
            return

        last = session.last_processed_bar_time
        if last is not None:
            next_bar = last + cfg.timeframe.delta
            if now < next_bar + cfg.timeframe.delta + CANDLE_CLOSE_GRACE:
                return  # the next candle has not closed yet: no network call
            since = next_bar
        else:
            required = self._registry.create(
                cfg.strategy_type, cfg.strategy_params
            ).required_history_candles()
            since = floor_to_timeframe(now, cfg.timeframe) - warmup_candles(required) * (
                cfg.timeframe.delta
            )

        source = self._exchanges.market_data(cfg.exchange)
        fetched = await source.fetch_candles(cfg.symbol, cfg.timeframe, since, FETCH_LIMIT)
        candles = sorted(
            (c for c in fetched if c.close_time <= now and (last is None or c.open_time > last)),
            key=lambda c: c.open_time,
        )
        if not candles:
            return

        market = await self.market_info(cfg.exchange, cfg.symbol)
        strategy = self._registry.create(cfg.strategy_type, cfg.strategy_params)
        state = (
            strategy.deserialize_state(session.strategy_state)
            if session.strategy_state is not None
            else strategy.initial_state()
        )
        await self._store_candles(bot, [c for c in candles if not candle_problems(c)])
        window = self._volumes.setdefault(bot.id, deque(maxlen=VOLUME_WINDOW))
        for candle in candles:
            problems = candle_problems(candle)
            if problems:
                await self._skip_invalid_candle(bot, session, strategy, state, candle, problems)
                continue
            self._close_jump = close_jump_pct(candle.close, self._last_closes.get(bot.id))
            self._last_closes[bot.id] = candle.close
            window.append(candle.volume * candle.close)
            self._avg_volume = average_quote_volume(list(window))
            state, paused = await self._process_candle(
                bot, session, strategy, state, candle, market
            )
            await self._submit_pending(bot)
            if paused:
                break

    async def _store_candles(self, bot: Bot, candles: list[Candle]) -> None:
        """Keep every candle the bot decided on (book 1 ch. 5, O2): the parity replay needs
        exactly what the bot saw. A stored candle the exchange now reports differently is
        overwritten, like an import, and the change is audited."""
        if not candles:
            return
        cfg = bot.config
        async with self._stores() as store:
            first, last = candles[0].open_time, candles[-1].open_time + cfg.timeframe.delta
            stored = {
                c.open_time: c
                for c in await store.candles.get_range(
                    cfg.exchange, cfg.symbol, cfg.timeframe, first, last
                )
            }
            changed = [
                c.open_time.isoformat()
                for c in candles
                if (old := stored.get(c.open_time)) is not None
                and (old.open, old.high, old.low, old.close, old.volume)
                != (c.open, c.high, c.low, c.close, c.volume)
            ]
            await store.candles.upsert_many(cfg.exchange, candles)
            if changed:
                await store.audit.add(
                    AuditEvent(
                        "data.candle_changed",
                        "bot",
                        str(bot.id),
                        actor="worker",
                        bot_id=bot.id,
                        payload={"open_times": changed[:20], "count": len(changed)},
                    )
                )
            await store.commit()

    async def _skip_invalid_candle(
        self,
        bot: Bot,
        session: TradingSession,
        strategy: Strategy[Any],
        state: Any,
        candle: Candle,
        problems: list[CandleProblem],
    ) -> None:
        """A malformed candle never reaches the strategy (book 1 ch. 3, C4). The bar is marked
        processed, so it is not fetched again, and the skip is audited."""
        async with self._stores() as store:
            await store.sessions.save_progress(
                session.id, strategy.serialize_state(state), candle.open_time
            )
            await store.audit.add(
                AuditEvent(
                    "data.invalid_candle",
                    "bot",
                    str(bot.id),
                    actor="worker",
                    bot_id=bot.id,
                    payload={
                        "open_time": candle.open_time.isoformat(),
                        "problems": [p.value for p in problems],
                    },
                )
            )
            await store.commit()
        logger.warning("bot %s skipped invalid candle %s: %s", bot.id, candle.open_time, problems)

    async def _submit_pending(self, bot: Bot) -> None:
        """Phase 2 for real-exchange bots: send the intents the candle transaction created."""
        pending, self._pending = self._pending, []
        if not pending:
            return
        if self._executor is None:
            raise RuntimeError("testnet bots need an OrderExecutor")
        for order_id in pending:
            await self._executor.submit(bot, order_id)

    async def _process_candle(
        self,
        bot: Bot,
        session: TradingSession,
        strategy: Strategy[Any],
        state: Any,
        candle: Candle,
        market: MarketInfo,
    ) -> tuple[Any, bool]:
        cfg = bot.config
        now = self._clock.now()
        # Candles closed before the session began only warm the strategy up: nothing is
        # recorded or traded. Later candles processed too late are "stale": state only.
        warmup = candle.close_time <= session.started_at
        fresh = now - candle.close_time <= max_signal_age(cfg.timeframe)
        self._pending = []

        async with self._stores() as store:
            portfolio = await store.portfolio.get(bot.id) or PortfolioState.new(
                bot.id, cfg.initial_capital
            )
            kill_switch = await store.flags.get_kill_switch()
            sold = False
            is_live = cfg.mode is ExecutionMode.LIVE
            limits, global_limits = self._effective_limits(bot)
            # Real exchanges: never stack a new order on one whose outcome is still unknown.
            blocked = cfg.mode.uses_exchange and await store.orders.count_unresolved(bot.id) > 0

            # 1. Protective exits. Allowed even on stale candles: a native exchange stop would
            #    have fired regardless of whether the worker was running.
            if not warmup and not blocked and portfolio.available_quantity > 0:
                # A stop resting on the exchange is the authority; only the target is watched here.
                native_stop = portfolio.stop_order_client_id is not None
                hit = check_protective_exit(
                    candle,
                    None if native_stop else portfolio.stop_price,
                    portfolio.take_profit_price,
                )
                if hit is not None:
                    exit_signal = Signal(
                        Side.SELL,
                        cfg.symbol,
                        SignalKind.EXIT,
                        f"{hit.reason.value} triggered at {hit.trigger_price}",
                    )
                    await self._record(store, bot, session, candle, exit_signal, "approved", None)
                    # A stop is a market order (adverse slippage); a target is a limit order.
                    slippage = (
                        cfg.slippage_bps if hit.reason is ExitReason.STOP_LOSS else Decimal(0)
                    )
                    sold = await self._execute(
                        store,
                        bot,
                        session,
                        exit_signal,
                        portfolio.available_quantity,
                        candle,
                        hit.trigger_price,
                        slippage,
                        portfolio,
                        now,
                    )

            # 2. Strategy.
            result = strategy.evaluate(
                StrategyContext(cfg.symbol, candle, portfolio.quantity), state
            )
            for signal in result.signals:
                if warmup:
                    continue
                if not fresh:
                    await self._record(store, bot, session, candle, signal, "discarded_stale", None)
                    continue
                if is_live and not self._live_limits.complete:
                    await self._record(
                        store,
                        bot,
                        session,
                        candle,
                        signal,
                        "rejected",
                        "live hard caps are missing",
                    )
                    continue
                if blocked:
                    await self._record(
                        store,
                        bot,
                        session,
                        candle,
                        signal,
                        "rejected",
                        "an earlier order is still unresolved (waiting for reconciliation)",
                    )
                    continue
                entry_block = (
                    await self._entry_block(store, bot, now) if signal.side is Side.BUY else None
                )
                if entry_block is not None:  # exits are never blocked by these checks
                    await self._record(store, bot, session, candle, signal, "rejected", entry_block)
                    continue
                decision = assess_signal(
                    signal,
                    portfolio,
                    candle.close,
                    market,
                    fee_rate=cfg.fee_rate,
                    slippage_bps=cfg.slippage_bps,
                    limits=limits,
                    kill_switch_active=kill_switch.active,
                    candle_range=candle_range_pct(candle.high, candle.low),
                    global_limits=global_limits,
                    exposure=await self._exposure(store, signal, global_limits, is_live),
                    avg_quote_volume=self._avg_volume,
                    close_jump=self._close_jump,
                )
                if not decision.approved or decision.quantity is None:
                    await self._record(
                        store, bot, session, candle, signal, "rejected", decision.reason
                    )
                    await store.audit.add(
                        AuditEvent(
                            "signal.rejected",
                            "bot",
                            str(bot.id),
                            actor="worker",
                            bot_id=bot.id,
                            payload={"side": signal.side.value, "reason": decision.reason},
                        )
                    )
                    continue
                order_quantity = decision.quantity
                if signal.exit_fraction is not None:
                    order_quantity *= signal.exit_fraction
                await self._record(store, bot, session, candle, signal, "approved", None)
                filled = await self._execute(
                    store,
                    bot,
                    session,
                    signal,
                    order_quantity,
                    candle,
                    candle.close,
                    cfg.slippage_bps,
                    portfolio,
                    now,
                )
                if filled and signal.side is Side.BUY:
                    portfolio.stop_price = signal.stop_loss
                    portfolio.take_profit_price = signal.take_profit
                sold = sold or (filled and signal.side is Side.SELL)

            # 3. Bookkeeping and risk circuit breakers.
            breach: Breach | None = None
            if not warmup and fresh:
                breach = await self._snapshot_and_check(store, bot, session, candle, portfolio)
            if breach is None and sold and not warmup:
                pnls = round_trip_pnls(await store.orders.list_fills(bot.id))
                if consecutive_losses_breached(pnls, cfg.risk):
                    breach = ("risk.consecutive_losses", "max consecutive losses reached")

            await store.portfolio.save(portfolio)
            await store.sessions.save_progress(
                session.id, strategy.serialize_state(result.state), candle.open_time
            )
            if breach is not None:
                event_type, message = breach
                if event_type == "risk.live_daily_loss_cap":
                    # Real money lost past the hard cap: stop everything, not just this bot.
                    await store.flags.set_kill_switch(True, message)
                ends_session = (
                    event_type == "risk.drawdown_breached"
                    and cfg.risk.drawdown_action is DrawdownAction.STOP
                )
                if ends_session:
                    # The supervisor settles the session (desired stopped, observed not yet).
                    await store.bots.set_desired(bot.id, BotState.STOPPED)
                else:
                    await store.bots.set_desired(bot.id, BotState.PAUSED)
                    await store.bots.set_observed(bot.id, BotState.PAUSED, message)
                for kind in (event_type, *(("risk.budget_exhausted",) if ends_session else ())):
                    await store.audit.add(
                        AuditEvent(
                            kind,
                            "bot",
                            str(bot.id),
                            actor="worker",
                            bot_id=bot.id,
                            payload={
                                "reason": message,
                                "action": "stop" if ends_session else "pause",
                            },
                        )
                    )
            await store.commit()
        return result.state, breach is not None

    async def _entry_block(self, store: TradingStore, bot: Bot, now: datetime) -> str | None:
        """Operational reasons to refuse a NEW position (book 1 ch. 4, O1 and O5)."""
        cfg = bot.config
        if cfg.mode.uses_exchange and cfg.connection_id is not None:
            connection = await store.connections.get(cfg.connection_id)
            if connection is not None and connection.permission_warning:
                return f"exchange key permissions changed: {connection.permission_warning}"
        if cfg.mode is ExecutionMode.LIVE:
            skew = await store.flags.get_clock_skew()
            fresh = skew is not None and now - skew[1] <= CLOCK_SKEW_FRESH
            if fresh and skew is not None and abs(skew[0]) > MAX_LIVE_CLOCK_SKEW_MS:
                return (
                    f"server clock is {skew[0]} ms off the exchange "
                    f"(limit {MAX_LIVE_CLOCK_SKEW_MS} ms): sync it (NTP)"
                )
        return None

    def _effective_limits(self, bot: Bot) -> tuple[RiskLimits, GlobalRiskLimits]:
        """The bot's own limits, tightened by the operator's hard caps when it trades real money."""
        cfg = bot.config
        if cfg.mode is not ExecutionMode.LIVE:
            return cfg.risk, self._global_limits
        caps = self._live_limits
        notionals = [n for n in (cfg.risk.max_order_notional, caps.max_order_notional) if n]
        limits = replace(cfg.risk, max_order_notional=min(notionals) if notionals else None)
        return limits, GlobalRiskLimits(
            max_open_positions=self._global_limits.max_open_positions,
            max_total_exposure=caps.max_total_exposure,
        )

    async def _exposure(
        self, store: TradingStore, signal: Signal, limits: GlobalRiskLimits, live: bool
    ) -> GlobalExposure:
        if signal.side is not Side.BUY or (
            limits.max_open_positions is None and limits.max_total_exposure is None
        ):
            return GlobalExposure()
        count, notional = await store.portfolio.open_exposure("live" if live else None)
        return GlobalExposure(count, notional)

    async def _record(
        self,
        store: TradingStore,
        bot: Bot,
        session: TradingSession,
        candle: Candle,
        signal: Signal,
        decision: str,
        reason: str | None,
    ) -> None:
        await store.signals.add(
            SignalRecord(
                id=self._ids.new_id(),
                session_id=session.id,
                bot_id=bot.id,
                bar_time=candle.open_time,
                side=signal.side,
                kind=signal.kind,
                exit_fraction=signal.exit_fraction,
                reason=signal.reason,
                decision=decision,
                decision_reason=reason,
                created_at=self._clock.now(),
            )
        )

    def _gateway(self, bot: Bot, slippage_bps: Decimal) -> ExchangeGateway:
        """The venue for this bot's mode. Only the paper venue exists for now."""
        cfg = bot.config
        return PaperExchangeGateway(
            self._exchanges.profile(cfg.exchange).capabilities,
            _CachedRules(self, cfg.exchange),
            self._prices,
            cfg.fee_rate,
            slippage_bps,
        )

    async def _execute(
        self,
        store: TradingStore,
        bot: Bot,
        session: TradingSession,
        signal: Signal,
        quantity: Decimal,
        candle: Candle,
        reference_price: Decimal,
        slippage_bps: Decimal,
        portfolio: PortfolioState,
        now: datetime,
    ) -> bool:
        """Place a market order via the gateway; True when it filled and the portfolio moved.

        On a real exchange nothing fills inside this transaction: an intent is recorded and
        sent afterwards, so this returns False there (the executor applies the result).
        """
        cfg = bot.config
        if cfg.mode.uses_exchange:
            await self._create_intent(
                store,
                bot,
                session,
                signal,
                quantity,
                candle,
                reference_price,
                slippage_bps,
                portfolio,
                now,
            )
            return False
        order = Order(
            id=self._ids.new_id(),
            bot_id=bot.id,
            session_id=session.id,
            client_order_id=make_client_order_id(bot.id, candle.open_time, signal.side),
            symbol=cfg.symbol,
            side=signal.side,
            quantity=quantity,
            bar_time=candle.open_time,
            created_at=now,
            reference_price=reference_price,
            submitted_at=now,  # the paper venue fills in the same step
        )
        order.submit()
        self._prices.set(cfg.symbol, reference_price, now)
        try:
            venue_order = await self._gateway(bot, slippage_bps).create_market_order(
                MarketOrderRequest(order.client_order_id, cfg.symbol, signal.side, quantity)
            )
            for fill in venue_order.fills:
                order.apply_fill(fill)
        except ExchangeRejected as exc:
            order.reject(str(exc))

        if not await store.orders.add_if_absent(order):
            logger.warning("duplicate order %s ignored", order.client_order_id)
            return False
        filled = bool(order.fills)
        for fill in order.fills:
            portfolio.apply_fill(fill)
        last_fill = order.fills[-1] if order.fills else None
        await store.audit.add(
            AuditEvent(
                "order.filled" if filled else "order.rejected",
                "order",
                str(order.id),
                actor="worker",
                bot_id=bot.id,
                payload={
                    "client_order_id": order.client_order_id,
                    "side": order.side.value,
                    "quantity": str(order.quantity),
                    "price": str(last_fill.price) if last_fill else None,
                    "fee": str(last_fill.fee) if last_fill else None,
                    "reason": order.reject_reason,
                },
            )
        )
        return filled

    async def _create_intent(
        self,
        store: TradingStore,
        bot: Bot,
        session: TradingSession,
        signal: Signal,
        quantity: Decimal,
        candle: Candle,
        reference_price: Decimal,
        slippage_bps: Decimal,
        portfolio: PortfolioState,
        now: datetime,
    ) -> None:
        """Phase 1: persist the order as SUBMITTING and reserve its capital (no network)."""
        cfg = bot.config
        position_side: PositionSide | None = None
        reduce_only = False
        ledger = None
        if cfg.product is TradingProduct.LINEAR_PERPETUAL:
            ledger = await store.perpetual_portfolio.get(bot.id)
            if ledger is None:
                raise RuntimeError("perpetual portfolio has not been initialized")
            position = ledger.position
            if signal.kind is SignalKind.EXIT:
                if position is None:
                    logger.warning("ignoring futures exit without an open position for %s", bot.id)
                    return
                position_side = position.side
                expected_side = Side.SELL if position.side is PositionSide.LONG else Side.BUY
                if signal.side is not expected_side:
                    logger.warning(
                        "ignoring futures exit that would increase exposure for %s", bot.id
                    )
                    return
                quantity = min(quantity, position.quantity)
                reduce_only = True
            else:
                if position is not None:
                    logger.warning(
                        "ignoring futures entry while a position is already open for %s", bot.id
                    )
                    return
                position_side = PositionSide.LONG if signal.side is Side.BUY else PositionSide.SHORT
                if position_side is PositionSide.SHORT and not cfg.allow_short:
                    logger.warning("ignoring short entry while shorting is disabled for %s", bot.id)
                    return
        order = Order(
            id=self._ids.new_id(),
            bot_id=bot.id,
            session_id=session.id,
            client_order_id=make_client_order_id(bot.id, candle.open_time, signal.side),
            symbol=cfg.symbol,
            side=signal.side,
            quantity=quantity,
            bar_time=candle.open_time,
            created_at=now,
            product=cfg.product,
            position_side=position_side,
            leverage=cfg.leverage,
            reduce_only=reduce_only,
            planned_stop_price=(signal.stop_loss if signal.kind is SignalKind.ENTRY else None),
            planned_take_profit_price=(
                signal.take_profit if signal.kind is SignalKind.ENTRY else None
            ),
            reference_price=reference_price,
        )
        try:
            reserve_price = slipped_price(signal.side, reference_price, slippage_bps)
            if cfg.product is TradingProduct.LINEAR_PERPETUAL:
                assert ledger is not None
                OrderExecutor.reserve_perpetual(order, ledger, reserve_price, cfg.fee_rate)
            else:
                OrderExecutor.reserve(order, portfolio, reserve_price, cfg.fee_rate)
        except (InsufficientFunds, InvalidPerpetualPosition, ValueError) as exc:
            logger.warning("order %s not created: %s", order.client_order_id, exc)
            return
        order.submit()
        if not await store.orders.add_if_absent(order):
            if cfg.product is TradingProduct.SPOT:
                portfolio.release(order.reserved_cash, order.reserved_quantity)
            logger.warning("duplicate order %s ignored", order.client_order_id)
            return
        if ledger is not None and order.reserved_margin:
            inserted = await store.perpetual_portfolio.append_entry(
                PerpetualLedgerEntry(
                    id=self._ids.new_id(),
                    bot_id=bot.id,
                    occurred_at=now,
                    kind=PerpetualLedgerEventKind.MARGIN_RESERVED,
                    reserved_margin_delta=order.reserved_margin,
                    source="worker_order_intent",
                    external_reference=f"order:{order.client_order_id}:margin-reserve",
                )
            )
            if not inserted:
                raise RuntimeError("duplicate perpetual margin reservation event")
            await store.perpetual_portfolio.save(ledger)
        self._pending.append(order.id)
        await store.audit.add(
            AuditEvent(
                "order.intent",
                "order",
                str(order.id),
                actor="worker",
                bot_id=bot.id,
                payload={
                    "client_order_id": order.client_order_id,
                    "side": order.side.value,
                    "quantity": str(order.quantity),
                    "product": order.product.value,
                    "position_side": order.position_side.value if order.position_side else None,
                    "leverage": order.leverage,
                    "reduce_only": order.reduce_only,
                },
            )
        )

    async def _snapshot_and_check(
        self,
        store: TradingStore,
        bot: Bot,
        session: TradingSession,
        candle: Candle,
        portfolio: PortfolioState,
    ) -> Breach | None:
        limits = bot.config.risk
        equity = portfolio.equity(candle.close)
        day_start = datetime.combine(candle.close_time.date(), datetime.min.time(), tzinfo=UTC)
        reference = (
            await store.portfolio.equity_at_or_before(bot.id, day_start)
            or await store.portfolio.first_snapshot_equity(bot.id)
            or bot.config.initial_capital
        )
        peak = max(await store.portfolio.peak_equity(bot.id) or equity, equity)
        await store.portfolio.add_snapshot(
            PortfolioSnapshot(
                bot_id=bot.id,
                session_id=session.id,
                taken_at=candle.close_time,
                price=candle.close,
                cash=portfolio.cash,
                quantity=portfolio.quantity,
                equity=equity,
            )
        )
        cap = self._live_limits.max_daily_loss
        if bot.config.mode is ExecutionMode.LIVE and cap is not None and reference - equity >= cap:
            return "risk.live_daily_loss_cap", "live daily loss cap reached"
        if daily_loss_breached(equity, reference, limits):
            return "risk.daily_loss_breached", "daily loss limit breached"
        if drawdown_breached(equity, peak, limits):
            return "risk.drawdown_breached", "max drawdown limit breached"
        return None
