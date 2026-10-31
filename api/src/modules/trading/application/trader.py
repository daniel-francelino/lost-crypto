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
from modules.exchanges.application.ports import ExchangeGateway, MarketOrderRequest
from modules.exchanges.application.registry import ExchangeRegistry
from modules.exchanges.errors import ExchangeRejected
from modules.execution.application.ports import SignalRecord
from modules.execution.domain.fills import slipped_price
from modules.execution.domain.orders import Order, make_client_order_id
from modules.execution.venues.paper import PaperExchangeGateway, StaticPriceFeed
from modules.market_data.domain.models import Candle, MarketInfo, floor_to_timeframe
from modules.portfolio.domain.models import InsufficientFunds, PortfolioSnapshot, PortfolioState
from modules.risk_management.domain.models import (
    GlobalExposure,
    GlobalRiskLimits,
    LiveLimits,
    RiskLimits,
    assess_signal,
    candle_range_pct,
    consecutive_losses_breached,
    daily_loss_breached,
    drawdown_breached,
)
from modules.risk_management.domain.stops import ExitReason, check_protective_exit
from modules.strategies.domain.base import Strategy
from modules.strategies.domain.registry import StrategyRegistry
from modules.strategies.domain.types import Side, Signal, SignalKind, StrategyContext
from modules.trading.application.orders import OrderExecutor
from modules.trading.application.ports import TradingStore
from modules.trading.domain.models import WARMUP_CANDLES, TradingSession, max_signal_age

logger = logging.getLogger(__name__)

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
        self._pending: list[UUID] = []  # orders created this candle, sent after the commit

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
        last = session.last_processed_bar_time
        if last is not None:
            next_bar = last + cfg.timeframe.delta
            if now < next_bar + cfg.timeframe.delta + CANDLE_CLOSE_GRACE:
                return  # the next candle has not closed yet: no network call
            since = next_bar
        else:
            since = floor_to_timeframe(now, cfg.timeframe) - WARMUP_CANDLES * cfg.timeframe.delta

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
        for candle in candles:
            state, paused = await self._process_candle(
                bot, session, strategy, state, candle, market
            )
            await self._submit_pending(bot)
            if paused:
                break

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
                await self._record(store, bot, session, candle, signal, "approved", None)
                filled = await self._execute(
                    store,
                    bot,
                    session,
                    signal,
                    decision.quantity,
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
                await store.bots.set_desired(bot.id, BotState.PAUSED)
                await store.bots.set_observed(bot.id, BotState.PAUSED, message)
                await store.audit.add(
                    AuditEvent(
                        event_type,
                        "bot",
                        str(bot.id),
                        actor="worker",
                        bot_id=bot.id,
                        payload={"reason": message},
                    )
                )
            await store.commit()
        return result.state, breach is not None

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
            planned_stop_price=signal.stop_loss if signal.side is Side.BUY else None,
            planned_take_profit_price=signal.take_profit if signal.side is Side.BUY else None,
        )
        try:
            OrderExecutor.reserve(
                order,
                portfolio,
                slipped_price(signal.side, reference_price, slippage_bps),
                cfg.fee_rate,
            )
        except InsufficientFunds as exc:
            logger.warning("order %s not created: %s", order.client_order_id, exc)
            return
        order.submit()
        if not await store.orders.add_if_absent(order):
            portfolio.release(order.reserved_cash, order.reserved_quantity)
            logger.warning("duplicate order %s ignored", order.client_order_id)
            return
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
