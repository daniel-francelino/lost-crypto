"""Paper-trading cycle of one bot.

Each closed candle is processed in ONE database transaction: strategy evaluation, signal
records, risk decision, order + fills, portfolio, snapshot, strategy state and audit commit
together. The candle's ``bar_time`` is the idempotency key (via the deterministic client order
id and the persisted ``last_processed_bar_time``), so a crash or a repeated run can never place
the same order twice.
"""

import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from core.clock import Clock
from core.ids import IdGenerator
from modules.audit.models import AuditEvent
from modules.bots.domain.models import Bot, BotState
from modules.execution.application.ports import SignalRecord
from modules.execution.domain.fills import simulate_market_fill
from modules.execution.domain.normalizer import OrderRejected
from modules.execution.domain.orders import Order, make_client_order_id
from modules.market_data.application.ports import MarketDataSource
from modules.market_data.domain.models import Candle, MarketInfo, floor_to_timeframe
from modules.portfolio.domain.models import PortfolioSnapshot, PortfolioState
from modules.risk_management.domain.models import assess_signal, daily_loss_breached
from modules.strategies.domain.registry import StrategyRegistry
from modules.strategies.domain.types import Signal, Strategy, StrategyContext
from modules.trading.application.ports import TradingStore
from modules.trading.domain.models import WARMUP_CANDLES, TradingSession, max_signal_age

logger = logging.getLogger(__name__)

TradingStoreFactory = Callable[[], AbstractAsyncContextManager[TradingStore]]

CANDLE_CLOSE_GRACE = timedelta(seconds=2)  # let the exchange publish the closed candle
FETCH_LIMIT = 1000


class BotTrader:
    def __init__(
        self,
        stores: TradingStoreFactory,
        registry: StrategyRegistry,
        source: MarketDataSource,
        clock: Clock,
        ids: IdGenerator,
    ) -> None:
        self._stores = stores
        self._registry = registry
        self._source = source
        self._clock = clock
        self._ids = ids
        self._markets: dict[str, MarketInfo] = {}

    async def process(self, bot: Bot) -> None:
        """Process every newly closed candle of a running bot."""
        async with self._stores() as store:
            session = await store.sessions.get_active(bot.id)
        if session is None:
            return  # the supervisor creates the session when it starts the bot

        timeframe = bot.config.timeframe
        now = self._clock.now()
        last = session.last_processed_bar_time
        if last is not None:
            next_bar = last + timeframe.delta
            if now < next_bar + timeframe.delta + CANDLE_CLOSE_GRACE:
                return  # the next candle has not closed yet: no network call
            since = next_bar
        else:
            since = floor_to_timeframe(now, timeframe) - WARMUP_CANDLES * timeframe.delta

        fetched = await self._source.fetch_candles(bot.config.symbol, timeframe, since, FETCH_LIMIT)
        candles = sorted(
            (c for c in fetched if c.close_time <= now and (last is None or c.open_time > last)),
            key=lambda c: c.open_time,
        )
        if not candles:
            return

        market = await self._market(bot.config.symbol)
        strategy = self._registry.create(bot.config.strategy_type, bot.config.strategy_params)
        state = (
            strategy.deserialize_state(session.strategy_state)
            if session.strategy_state is not None
            else strategy.initial_state()
        )
        for candle in candles:
            state, paused = await self._process_candle(
                bot, session, strategy, state, candle, market
            )
            if paused:
                break

    async def _market(self, symbol: str) -> MarketInfo:
        if symbol not in self._markets:
            self._markets[symbol] = await self._source.fetch_market_info(symbol)
        return self._markets[symbol]

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

        async with self._stores() as store:
            portfolio = await store.portfolio.get(bot.id) or PortfolioState.new(
                bot.id, cfg.initial_capital
            )
            kill_switch = await store.flags.get_kill_switch()
            result = strategy.evaluate(
                StrategyContext(cfg.symbol, candle, portfolio.quantity), state
            )

            for signal in result.signals:
                if warmup:
                    continue
                if not fresh:
                    await self._record(store, bot, session, candle, signal, "discarded_stale", None)
                    continue
                decision = assess_signal(
                    signal,
                    portfolio,
                    candle.close,
                    market,
                    fee_rate=cfg.fee_rate,
                    slippage_bps=cfg.slippage_bps,
                    limits=cfg.risk,
                    kill_switch_active=kill_switch.active,
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
                await self._execute(
                    store, bot, session, signal, decision.quantity, candle, portfolio, market
                )

            breached = False
            if not warmup and fresh:
                breached = await self._snapshot_and_check_loss(
                    store, bot, session, candle, portfolio
                )
            await store.portfolio.save(portfolio)
            await store.sessions.save_progress(
                session.id, strategy.serialize_state(result.state), candle.open_time
            )
            if breached:
                await store.bots.set_desired(bot.id, BotState.PAUSED)
                await store.bots.set_observed(bot.id, BotState.PAUSED, "daily loss limit breached")
                await store.audit.add(
                    AuditEvent(
                        "risk.daily_loss_breached",
                        "bot",
                        str(bot.id),
                        actor="worker",
                        bot_id=bot.id,
                        payload={"max_daily_loss_pct": str(cfg.risk.max_daily_loss_pct)},
                    )
                )
            await store.commit()
        return result.state, breached

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

    async def _execute(
        self,
        store: TradingStore,
        bot: Bot,
        session: TradingSession,
        signal: Signal,
        quantity: Decimal,
        candle: Candle,
        portfolio: PortfolioState,
        market: MarketInfo,
    ) -> None:
        cfg = bot.config
        now = self._clock.now()
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
        fill = None
        try:
            # Paper venue: the reference price is the close of the signal candle.
            fill = simulate_market_fill(
                signal.side, quantity, candle.close, cfg.fee_rate, cfg.slippage_bps, market, now
            )
            order.apply_fill(fill)
        except OrderRejected as exc:
            order.reject(str(exc))

        if not await store.orders.add_if_absent(order):
            logger.warning("duplicate order %s ignored", order.client_order_id)
            return
        if fill is not None:
            portfolio.apply_fill(fill)
        await store.audit.add(
            AuditEvent(
                "order.filled" if fill is not None else "order.rejected",
                "order",
                str(order.id),
                actor="worker",
                bot_id=bot.id,
                payload={
                    "client_order_id": order.client_order_id,
                    "side": order.side.value,
                    "quantity": str(order.quantity),
                    "price": str(fill.price) if fill else None,
                    "fee": str(fill.fee) if fill else None,
                    "reason": order.reject_reason,
                },
            )
        )

    async def _snapshot_and_check_loss(
        self,
        store: TradingStore,
        bot: Bot,
        session: TradingSession,
        candle: Candle,
        portfolio: PortfolioState,
    ) -> bool:
        equity = portfolio.equity(candle.close)
        day_start = datetime.combine(candle.close_time.date(), datetime.min.time(), tzinfo=UTC)
        reference = (
            await store.portfolio.equity_at_or_before(bot.id, day_start)
            or await store.portfolio.first_snapshot_equity(bot.id)
            or bot.config.initial_capital
        )
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
        return daily_loss_breached(equity, reference, bot.config.risk)
