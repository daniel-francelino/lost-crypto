"""Paper execution for Binance USD-M isolated USDT perpetuals.

Every candle, funding settlement, fill, ledger event, snapshot and strategy checkpoint is
committed in one transaction. Signal candles and exchange mark-price candles are separate inputs;
missing mark or funding observations stop processing instead of silently falling back to Spot.
"""

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from datetime import datetime, timedelta
from decimal import Decimal
from itertools import pairwise
from typing import Any
from uuid import UUID

from core.clock import Clock
from core.errors import ConflictError
from core.ids import IdGenerator
from modules.analytics.domain.metrics import round_trip_pnls
from modules.audit.models import AuditEvent
from modules.bots.domain.models import Bot, BotState, ExecutionMode
from modules.exchanges.application.connections import ConnectionResolver
from modules.exchanges.application.registry import ExchangeRegistry
from modules.exchanges.domain.connections import Environment
from modules.exchanges.domain.models import LeverageTier, PositionSide, TradingProduct
from modules.execution.application.ports import SignalRecord
from modules.execution.domain.fills import simulate_market_fill
from modules.execution.domain.normalizer import OrderRejected, normalize_quantity, round_price
from modules.execution.domain.orders import Fill, Order, make_client_order_id
from modules.market_data.domain.models import (
    Candle,
    FundingRate,
    MarketInfo,
    Timeframe,
    floor_to_timeframe,
)
from modules.market_data.domain.quality import candle_problems
from modules.portfolio.domain.perpetual_ledger import (
    PerpetualLedgerEntry,
    PerpetualLedgerEventKind,
    PerpetualPortfolioSnapshot,
)
from modules.portfolio.domain.perpetuals import (
    InvalidPerpetualPosition,
    LinearPerpetualPosition,
    PerpetualLedger,
)
from modules.risk_management.domain.models import (
    average_quote_volume,
    consecutive_losses_breached,
    daily_loss_breached,
    drawdown_breached,
)
from modules.risk_management.domain.perpetual import size_linear_perpetual_entry
from modules.strategies.domain.base import Strategy
from modules.strategies.domain.registry import StrategyRegistry
from modules.strategies.domain.types import Side, Signal, SignalKind, StrategyContext
from modules.trading.application.orders import OrderExecutor
from modules.trading.application.ports import TradingStore
from modules.trading.domain.models import TradingSession, max_signal_age, warmup_candles

TradingStoreFactory = Callable[[], AbstractAsyncContextManager[TradingStore]]
_TIER_CACHE_AGE = timedelta(minutes=30)
_FUNDING_PAGE = 1000
_VOLUME_WINDOW = 20
# Same grace as the spot trader (kept local: trader.py imports this module): the exchange needs a
# moment to publish a closed candle, and a still-forming last kline must never be processed.
_CANDLE_CLOSE_GRACE = timedelta(seconds=2)


class _PerpetualTrader:
    def __init__(
        self,
        stores: TradingStoreFactory,
        strategies: StrategyRegistry,
        exchanges: ExchangeRegistry,
        resolver: ConnectionResolver | None,
        clock: Clock,
        ids: IdGenerator,
        executor: OrderExecutor | None = None,
    ) -> None:
        self._stores = stores
        self._strategies = strategies
        self._exchanges = exchanges
        self._resolver = resolver
        self._clock = clock
        self._ids = ids
        self._executor = executor
        self._pending: list[UUID] = []
        self._tier_cache: dict[tuple[UUID, str], tuple[datetime, list[LeverageTier]]] = {}

    async def process(self, bot: Bot, session: TradingSession, now: datetime) -> None:
        cfg = bot.config
        if cfg.mode not in (ExecutionMode.PAPER, ExecutionMode.TESTNET):
            raise ConflictError("live Futures exchange execution is not enabled")
        if cfg.mode is ExecutionMode.TESTNET and self._executor is None:
            raise ConflictError("Futures Demo requires a configured OrderExecutor")
        if cfg.product is not TradingProduct.LINEAR_PERPETUAL:
            raise ValueError("perpetual paper trader requires a linear perpetual bot")
        if cfg.connection_id is None or self._resolver is None:
            raise ConflictError("Futures paper mode requires an active Binance Demo connection")
        if await self._resolver.environment_for(cfg.connection_id) is not Environment.DEMO:
            raise ConflictError("Futures paper mode requires a Binance Demo connection")

        last = session.last_processed_bar_time
        if last is not None and now < last + 2 * cfg.timeframe.delta + _CANDLE_CLOSE_GRACE:
            return  # the next candle has not closed yet: no network call (2 s polls add up)
        strategy = self._strategies.create(cfg.strategy_type, cfg.strategy_params)
        since = (
            last + cfg.timeframe.delta
            if last is not None
            else _floor(now, cfg.timeframe)
            - warmup_candles(strategy.required_history_candles()) * cfg.timeframe.delta
        )
        source = self._exchanges.market_data(cfg.exchange)
        raw_candles = await source.fetch_candles(cfg.symbol, cfg.timeframe, since, 1000)
        candles = sorted(
            (
                c
                for c in raw_candles
                if c.close_time + _CANDLE_CLOSE_GRACE <= now
                and (last is None or c.open_time > last)
            ),
            key=lambda c: c.open_time,
        )
        if not candles:
            return
        if any(c.symbol != cfg.symbol or c.timeframe is not cfg.timeframe for c in candles):
            raise ConflictError("signal candle identity does not match the Futures bot")
        if any(candle_problems(candle) for candle in candles):
            raise ConflictError("signal candle data failed quality checks; Futures cycle stopped")
        if any(
            later.open_time - earlier.open_time != cfg.timeframe.delta
            for earlier, later in pairwise(candles)
        ):
            raise ConflictError("signal candle history has a gap; Futures cycle stopped")
        fetch_marks = getattr(source, "fetch_mark_candles", None)
        fetch_funding = getattr(source, "fetch_funding_rates", None)
        if not callable(fetch_marks) or (
            cfg.mode is ExecutionMode.PAPER and not callable(fetch_funding)
        ):
            raise ConflictError("USD-M adapter must provide mark candles and paper funding history")
        mark_candles = await fetch_marks(cfg.symbol, cfg.timeframe, since, 1000)
        marks = {mark.open_time: mark for mark in mark_candles}
        if any(candle.open_time not in marks for candle in candles):
            raise ConflictError(
                "mark-price candle coverage is incomplete; Futures paper cycle stopped"
            )
        aligned_marks = [marks[candle.open_time] for candle in candles]
        if any(candle_problems(mark) for mark in aligned_marks):
            raise ConflictError(
                "mark-price candle data failed quality checks; Futures cycle stopped"
            )
        if any(
            mark.symbol != candle.symbol
            or mark.timeframe is not candle.timeframe
            or mark.open_time != candle.open_time
            for candle, mark in zip(candles, aligned_marks, strict=True)
        ):
            raise ConflictError("mark-price candles do not align with signal candles")

        start = (
            last + cfg.timeframe.delta + timedelta(milliseconds=1)
            if last is not None
            else candles[0].open_time
        )
        end = candles[-1].close_time
        rates = (
            await self._funding_history(fetch_funding, cfg.symbol, start, end)
            if cfg.mode is ExecutionMode.PAPER
            else []
        )
        if any(rate.symbol != cfg.symbol for rate in rates):
            raise ConflictError("funding history symbol does not match the Futures bot")
        if any(rate.mark_price is None for rate in rates):
            raise ConflictError("funding history lacks event-time mark prices; cycle stopped")
        if len({(rate.funding_time, rate.rate_type) for rate in rates}) != len(rates):
            raise ConflictError("funding history contains duplicate event types at one timestamp")

        market = await source.fetch_market_info(cfg.symbol)
        tiers = await self._leverage_tiers(bot, now)
        await self._store_inputs(bot, candles, aligned_marks, rates)
        state = (
            strategy.deserialize_state(session.strategy_state)
            if session.strategy_state is not None
            else strategy.initial_state()
        )
        funding_index = 0
        for candle, mark in zip(candles, aligned_marks, strict=True):
            candle_rates: list[FundingRate] = []
            while (
                funding_index < len(rates)
                and rates[funding_index].funding_time <= candle.close_time
            ):
                if rates[funding_index].funding_time >= candle.open_time:
                    candle_rates.append(rates[funding_index])
                funding_index += 1
            self._pending = []
            state, paused = await self._process_candle(
                bot, session, strategy, state, candle, mark, candle_rates, market, tiers, now
            )
            if self._pending:
                if self._executor is None:
                    raise ConflictError("Futures Demo order executor is unavailable")
                pending, self._pending = self._pending, []
                for order_id in pending:
                    await self._executor.submit(bot, order_id)
            if paused:
                break

    async def _leverage_tiers(self, bot: Bot, now: datetime) -> list[LeverageTier]:
        connection_id = bot.config.connection_id
        if connection_id is None or self._resolver is None:
            raise ConflictError("Futures leverage tiers require a Binance Demo connection")
        key = (connection_id, bot.config.symbol)
        cached = self._tier_cache.get(key)
        if cached is not None and now - cached[0] < _TIER_CACHE_AGE:
            return cached[1]
        exchange = await self._resolver.exchange_for(connection_id)
        tiers = await exchange.fetch_leverage_tiers(bot.config.symbol)
        if not tiers:
            raise ConflictError(
                "Binance Demo returned no leverage tier for the configured leverage"
            )
        self._tier_cache[key] = (now, tiers)
        return tiers

    @staticmethod
    async def _funding_history(
        fetch_funding: Any,
        symbol: str,
        start: datetime,
        end: datetime,
    ) -> list[FundingRate]:
        """Page every funding event needed for this candle batch; never silently truncate."""
        events: dict[tuple[datetime, str], FundingRate] = {}
        cursor = start
        while cursor <= end:
            page = await fetch_funding(symbol, cursor, _FUNDING_PAGE)
            if not page:
                break
            ordered = sorted(page, key=lambda rate: (rate.funding_time, rate.rate_type))
            for rate in ordered:
                if start <= rate.funding_time <= end:
                    key = (rate.funding_time, rate.rate_type)
                    if key in events:
                        raise ConflictError("funding history contains duplicate event types")
                    events[key] = rate
            newest = ordered[-1].funding_time
            if newest < cursor:
                raise ConflictError("funding history pagination moved backwards")
            if len(page) < _FUNDING_PAGE or newest >= end:
                break
            next_cursor = newest + timedelta(milliseconds=1)
            if next_cursor <= cursor:
                raise ConflictError("funding history pagination made no progress")
            cursor = next_cursor
        return [events[key] for key in sorted(events)]

    async def _store_inputs(
        self,
        bot: Bot,
        candles: list[Candle],
        marks: list[Candle],
        rates: list[FundingRate],
    ) -> None:
        async with self._stores() as store:
            await store.candles.upsert_many(bot.config.exchange, candles)
            await store.perpetual_data.upsert_mark_candles(bot.config.exchange, marks)
            await store.perpetual_data.upsert_funding_rates(bot.config.exchange, rates)
            await store.commit()

    async def _process_candle(
        self,
        bot: Bot,
        session: TradingSession,
        strategy: Strategy[Any],
        state: Any,
        candle: Candle,
        mark: Candle,
        funding_rates: list[FundingRate],
        market: MarketInfo,
        tiers: list[LeverageTier],
        now: datetime,
    ) -> tuple[Any, bool]:
        cfg = bot.config
        warmup = candle.close_time <= session.started_at
        fresh = now - candle.close_time <= max_signal_age(cfg.timeframe)
        async with self._stores() as store:
            ledger = await store.perpetual_portfolio.get(bot.id) or PerpetualLedger.new(
                bot.id, cfg.initial_capital
            )
            latest_bot = await store.bots.get(bot.id)
            if latest_bot is None or latest_bot.desired_state is not BotState.RUNNING:
                return state, True
            risk_history = await store.perpetual_portfolio.list_snapshots(bot.id)
            exited = False
            for rate in funding_rates:
                if ledger.position is None:
                    continue
                assert rate.mark_price is not None
                funding_reference = (
                    f"funding:{cfg.symbol}:{rate.funding_time.isoformat()}:{rate.rate_type}"
                )
                if await store.perpetual_portfolio.has_entry(bot.id, funding_reference):
                    continue
                before = ledger.position
                funding_tier = _tier_for(tiers, before.quantity * rate.mark_price)
                ledger.mark(
                    rate.mark_price,
                    rate.funding_time,
                    funding_tier.maintenance_margin_rate,
                    source="binance_funding_event_mark_price",
                )
                wallet_before = ledger.wallet_balance
                margin_before = before.isolated_margin
                realized_before = ledger.realized_pnl
                fees_before = ledger.fees_paid
                payment = ledger.apply_funding(
                    rate.mark_price,
                    rate.rate,
                    liquidation_fee_rate=cfg.fee_rate,
                    cumulative_maintenance_amount=funding_tier.cumulative_maintenance_amount,
                    check_maintenance_margin=True,
                )
                event_kind = (
                    PerpetualLedgerEventKind.LIQUIDATED
                    if ledger.position is None
                    else PerpetualLedgerEventKind.FUNDING_SETTLED
                )
                await store.perpetual_portfolio.append_entry(
                    PerpetualLedgerEntry(
                        id=self._ids.new_id(),
                        bot_id=bot.id,
                        occurred_at=rate.funding_time,
                        kind=event_kind,
                        wallet_delta=ledger.wallet_balance - wallet_before,
                        isolated_margin_delta=(
                            -margin_before
                            if ledger.position is None
                            else ledger.position.isolated_margin - margin_before
                        ),
                        realized_pnl_delta=ledger.realized_pnl - realized_before,
                        fee=ledger.fees_paid - fees_before,
                        funding=payment,
                        quantity=before.quantity,
                        side=before.side,
                        price=rate.mark_price,
                        source="binance_funding_history",
                        external_reference=funding_reference,
                    )
                )
                if ledger.position is None:
                    exited = True
                    await self._record_forced_close(
                        store,
                        bot,
                        session,
                        candle,
                        before.side,
                        before.quantity,
                        rate.mark_price,
                        cfg.fee_rate,
                        "funding liquidation",
                        rate.funding_time,
                    )

            position = ledger.position
            active_tier = (
                _tier_for(tiers, position.quantity * mark.close) if position is not None else None
            )
            ledger.mark(
                mark.close,
                mark.close_time,
                active_tier.maintenance_margin_rate if active_tier else Decimal(0),
                source="binance_exchange_mark_price",
            )

            if position is not None and active_tier is not None:
                liq_price = position.estimated_liquidation_price(
                    active_tier.maintenance_margin_rate,
                    active_tier.cumulative_maintenance_amount,
                )
                liq_hit = cfg.mode is ExecutionMode.PAPER and (
                    mark.low <= liq_price
                    if position.side is PositionSide.LONG
                    else mark.high >= liq_price
                )
                if liq_hit:
                    reference = (
                        min(mark.open, liq_price)
                        if position.side is PositionSide.LONG
                        else max(mark.open, liq_price)
                    )
                    await self._close(
                        store,
                        bot,
                        session,
                        candle,
                        ledger,
                        market,
                        position.quantity,
                        reference,
                        cfg.fee_rate,
                        True,
                        "mark-price liquidation",
                    )
                    exited = True
                else:
                    stop_hit = position.stop_price is not None and (
                        mark.low <= position.stop_price
                        if position.side is PositionSide.LONG
                        else mark.high >= position.stop_price
                    )
                    target_hit = position.take_profit_price is not None and (
                        mark.high >= position.take_profit_price
                        if position.side is PositionSide.LONG
                        else mark.low <= position.take_profit_price
                    )
                    if stop_hit or target_hit:
                        trigger = position.stop_price if stop_hit else position.take_profit_price
                        assert trigger is not None
                        crossed = (
                            mark.open <= trigger
                            if position.side is PositionSide.LONG and stop_hit
                            else mark.open >= trigger
                            if position.side is PositionSide.SHORT and stop_hit
                            else mark.open >= trigger
                            if position.side is PositionSide.LONG
                            else mark.open <= trigger
                        )
                        reference = mark.open if crossed else trigger
                        await self._close(
                            store,
                            bot,
                            session,
                            candle,
                            ledger,
                            market,
                            position.quantity,
                            reference,
                            cfg.fee_rate,
                            False,
                            "protective stop" if stop_hit else "take profit",
                        )
                        exited = True

            signals = strategy.evaluate(
                StrategyContext(
                    candle.symbol,
                    candle,
                    ledger.position.quantity if ledger.position else Decimal(0),
                    ledger.position.side if ledger.position else None,
                    cfg.allow_short,
                ),
                state,
            )
            state = signals.state
            paused = False
            if not warmup:
                blocked_reason = None
                if not fresh:
                    blocked_reason = "signal candle is stale"
                elif await store.orders.count_unresolved(bot.id):
                    blocked_reason = "an earlier order is unresolved"

                volumes = await store.candles.get_range(
                    cfg.exchange,
                    cfg.symbol,
                    cfg.timeframe,
                    candle.open_time - cfg.timeframe.delta * _VOLUME_WINDOW,
                    candle.close_time,
                )
                quote_volumes = [item.volume * item.close for item in volumes]
                avg_volume = average_quote_volume(quote_volumes)
                previous_close = volumes[-2].close if len(volumes) > 1 else None
                kill = await store.flags.get_kill_switch()
                for signal in signals.signals:
                    position = ledger.position
                    if signal.kind is SignalKind.EXIT:
                        if position is None:
                            decision = "exit signal ignored while flat"
                        elif signal.side is not (
                            Side.SELL if position.side is PositionSide.LONG else Side.BUY
                        ):
                            decision = "exit direction would increase exposure"
                        else:
                            exit_quantity = position.quantity
                            if signal.exit_fraction is not None:
                                exit_quantity *= signal.exit_fraction
                            try:
                                await self._close(
                                    store,
                                    bot,
                                    session,
                                    candle,
                                    ledger,
                                    market,
                                    exit_quantity,
                                    candle.close,
                                    cfg.fee_rate,
                                    False,
                                    signal.reason,
                                )
                            except (InvalidPerpetualPosition, OrderRejected, ValueError) as exc:
                                await self._signal(
                                    store, bot, session, candle, signal, "rejected", str(exc)
                                )
                                continue
                            await self._signal(
                                store, bot, session, candle, signal, "approved", None
                            )
                            exited = True
                            continue
                        await self._signal(
                            store, bot, session, candle, signal, "rejected", decision
                        )
                        continue

                    if blocked_reason is not None:
                        await self._signal(
                            store, bot, session, candle, signal, "rejected", blocked_reason
                        )
                        continue
                    if exited:
                        await self._signal(
                            store,
                            bot,
                            session,
                            candle,
                            signal,
                            "rejected",
                            "entry after an exit on the same candle is blocked",
                        )
                        continue
                    if ledger.position is not None:
                        await self._signal(
                            store, bot, session, candle, signal, "rejected", "position already open"
                        )
                        continue
                    try:
                        quantity = size_linear_perpetual_entry(
                            signal,
                            equity=ledger.equity(mark.close),
                            available_collateral=ledger.available_balance,
                            reference_price=candle.close,
                            leverage=cfg.leverage,
                            fee_rate=cfg.fee_rate,
                            slippage_bps=cfg.slippage_bps,
                            limits=cfg.risk,
                            candle=candle,
                            average_quote_volume=avg_volume,
                            leverage_tiers=tiers,
                            allow_short=cfg.allow_short,
                            kill_switch_active=kill.active,
                            previous_close=previous_close,
                        )
                        await self._open(
                            store, bot, session, candle, ledger, market, signal, quantity, tiers
                        )
                    except (InvalidPerpetualPosition, OrderRejected, ValueError) as exc:
                        await self._signal(
                            store, bot, session, candle, signal, "rejected", str(exc)
                        )
                    else:
                        await self._signal(store, bot, session, candle, signal, "approved", None)

            ledger.mark(
                mark.close,
                mark.close_time,
                _tier_for(tiers, ledger.position.quantity * mark.close).maintenance_margin_rate
                if ledger.position is not None
                else Decimal(0),
                source="binance_exchange_mark_price",
            )
            position = ledger.position
            await store.perpetual_portfolio.save(ledger)
            if not warmup:
                await store.perpetual_portfolio.add_snapshot(
                    PerpetualPortfolioSnapshot(
                        bot_id=bot.id,
                        session_id=session.id,
                        taken_at=mark.close_time,
                        mark_price=mark.close,
                        wallet_balance=ledger.wallet_balance,
                        isolated_margin=position.isolated_margin if position else Decimal(0),
                        position_side=position.side if position else None,
                        quantity=position.quantity if position else Decimal(0),
                        entry_price=position.entry_price if position else Decimal(0),
                        equity=ledger.equity(mark.close),
                        unrealized_pnl=position.unrealized_pnl(mark.close)
                        if position
                        else Decimal(0),
                        funding_paid=ledger.funding_paid,
                        funding_received=ledger.funding_received,
                        mark_source="binance_exchange_mark_price",
                    )
                )
            await store.sessions.save_progress(
                session.id, strategy.serialize_state(state), candle.open_time
            )
            paused = (
                await self._check_risk(store, bot, ledger, mark, exited, risk_history)
                if not warmup and fresh
                else False
            )
            await store.commit()
        return state, paused

    async def _signal(
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

    async def _open(
        self,
        store: TradingStore,
        bot: Bot,
        session: TradingSession,
        candle: Candle,
        ledger: PerpetualLedger,
        market: MarketInfo,
        signal: Signal,
        quantity: Decimal,
        tiers: list[LeverageTier],
    ) -> None:
        cfg = bot.config
        side = PositionSide.LONG if signal.side is Side.BUY else PositionSide.SHORT
        if cfg.mode is ExecutionMode.TESTNET:
            if self._executor is None:
                raise ConflictError("Futures Demo order executor is unavailable")
            quantity = normalize_quantity(quantity, candle.close, market)
            if signal.stop_loss is None:
                raise OrderRejected("Binance USD-M Demo entries require a protective stop loss")
            stop_price = round_price(signal.stop_loss, market)
            try:
                # Validate the directional stop and target before persisting an intent or
                # sending an exchange order. A bad stop discovered after a fill would leave
                # the real position open without native protection.
                LinearPerpetualPosition(
                    side=side,
                    quantity=quantity,
                    entry_price=candle.close,
                    leverage=cfg.leverage,
                    isolated_margin=quantity * candle.close / cfg.leverage,
                    stop_price=stop_price,
                    take_profit_price=signal.take_profit,
                )
            except InvalidPerpetualPosition as exc:
                raise OrderRejected(f"invalid Futures Demo protective levels: {exc}") from exc
            order = Order(
                id=self._ids.new_id(),
                bot_id=bot.id,
                session_id=session.id,
                client_order_id=make_client_order_id(bot.id, candle.open_time, signal.side),
                symbol=cfg.symbol,
                side=signal.side,
                quantity=quantity,
                bar_time=candle.open_time,
                created_at=self._clock.now(),
                product=TradingProduct.LINEAR_PERPETUAL,
                position_side=side,
                leverage=cfg.leverage,
                reference_price=candle.close,
                planned_stop_price=stop_price,
                planned_take_profit_price=signal.take_profit,
            )
            OrderExecutor.reserve_perpetual(order, ledger, candle.close, cfg.fee_rate)
            order.submit()
            if not await store.orders.add_if_absent(order):
                raise ConflictError("duplicate Binance Demo entry intent for this candle")
            if order.reserved_margin:
                await store.perpetual_portfolio.append_entry(
                    PerpetualLedgerEntry(
                        id=self._ids.new_id(),
                        bot_id=bot.id,
                        occurred_at=self._clock.now(),
                        kind=PerpetualLedgerEventKind.MARGIN_RESERVED,
                        reserved_margin_delta=order.reserved_margin,
                        source="binance_demo_order_intent",
                        external_reference=f"order:{order.client_order_id}:margin-reserve",
                    )
                )
            await store.perpetual_portfolio.save(ledger)
            self._pending.append(order.id)
            await store.audit.add(
                AuditEvent(
                    "order.intent_created",
                    "order",
                    str(order.id),
                    actor="worker",
                    bot_id=bot.id,
                    payload={
                        "product": "linear_perpetual",
                        "mode": cfg.mode.value,
                        "client_order_id": order.client_order_id,
                        "position_side": side.value,
                        "quantity": str(quantity),
                        "reference_price": str(candle.close),
                    },
                )
            )
            return
        fill = simulate_market_fill(
            signal.side,
            quantity,
            candle.close,
            cfg.fee_rate,
            cfg.slippage_bps,
            market,
            candle.close_time,
        )
        try:
            tier = _tier_for(tiers, fill.notional, cfg.leverage)
        except ConflictError as exc:
            raise OrderRejected(str(exc)) from exc
        order = Order(
            id=self._ids.new_id(),
            bot_id=bot.id,
            session_id=session.id,
            client_order_id=make_client_order_id(bot.id, candle.open_time, signal.side),
            symbol=cfg.symbol,
            side=signal.side,
            quantity=fill.quantity,
            bar_time=candle.open_time,
            created_at=self._clock.now(),
            product=TradingProduct.LINEAR_PERPETUAL,
            position_side=side,
            leverage=cfg.leverage,
            reference_price=candle.close,
            planned_stop_price=signal.stop_loss,
            planned_take_profit_price=signal.take_profit,
        )
        order.submit()
        order.apply_fill(fill)
        ledger.open_position(
            side,
            fill.quantity,
            fill.price,
            cfg.leverage,
            fill.total_fee,
            signal.stop_loss,
            signal.take_profit,
        )
        ledger.mark(candle.close, candle.close_time, tier.maintenance_margin_rate)
        inserted = await store.orders.add_if_absent(order)
        if not inserted:
            raise ConflictError("duplicate Futures paper order for this candle")
        await store.perpetual_portfolio.append_entry(
            PerpetualLedgerEntry(
                id=self._ids.new_id(),
                bot_id=bot.id,
                occurred_at=fill.time,
                kind=PerpetualLedgerEventKind.POSITION_OPENED,
                wallet_delta=-(fill.notional / cfg.leverage + fill.total_fee),
                isolated_margin_delta=fill.notional / cfg.leverage,
                fee=fill.total_fee,
                quantity=fill.quantity,
                side=side,
                price=fill.price,
                source="paper_fill",
                external_reference=f"paper:{order.client_order_id}:fill",
            )
        )
        await store.audit.add(
            AuditEvent(
                "order.filled",
                "order",
                str(order.id),
                actor="worker",
                bot_id=bot.id,
                payload={
                    "product": "linear_perpetual",
                    "client_order_id": order.client_order_id,
                    "side": signal.side.value,
                    "position_side": side.value,
                    "quantity": str(fill.quantity),
                    "price": str(fill.price),
                    "fee": str(fill.total_fee),
                },
            )
        )

    async def _close(
        self,
        store: TradingStore,
        bot: Bot,
        session: TradingSession,
        candle: Candle,
        ledger: PerpetualLedger,
        market: MarketInfo,
        quantity: Decimal,
        reference: Decimal,
        fee_rate: Decimal,
        liquidated: bool,
        reason: str,
    ) -> None:
        position = ledger.position
        if position is None:
            return
        side = Side.SELL if position.side is PositionSide.LONG else Side.BUY
        if bot.config.mode is ExecutionMode.TESTNET:
            if self._executor is None:
                raise ConflictError("Futures Demo order executor is unavailable")
            quantity = normalize_quantity(quantity, reference, market)
            order = Order(
                id=self._ids.new_id(),
                bot_id=bot.id,
                session_id=session.id,
                client_order_id=make_client_order_id(bot.id, candle.open_time, side),
                symbol=bot.config.symbol,
                side=side,
                quantity=quantity,
                bar_time=candle.open_time,
                created_at=self._clock.now(),
                product=TradingProduct.LINEAR_PERPETUAL,
                position_side=position.side,
                leverage=position.leverage,
                reduce_only=True,
                reference_price=reference,
            )
            OrderExecutor.reserve_perpetual(order, ledger, reference, fee_rate)
            order.submit()
            if not await store.orders.add_if_absent(order):
                raise ConflictError("duplicate Binance Demo reduce-only intent for this candle")
            self._pending.append(order.id)
            await store.audit.add(
                AuditEvent(
                    "order.intent_created",
                    "order",
                    str(order.id),
                    actor="worker",
                    bot_id=bot.id,
                    payload={
                        "product": "linear_perpetual",
                        "mode": bot.config.mode.value,
                        "reduce_only": True,
                        "reason": reason,
                        "client_order_id": order.client_order_id,
                        "position_side": position.side.value,
                        "quantity": str(quantity),
                        "reference_price": str(reference),
                    },
                )
            )
            return
        fill = simulate_market_fill(
            side,
            quantity,
            reference,
            fee_rate,
            bot.config.slippage_bps if liquidated or "stop" in reason else Decimal(0),
            market,
            candle.close_time,
        )
        released = position.isolated_margin * fill.quantity / position.quantity
        realized = ledger.close_position(fill.quantity, fill.price, fill.total_fee)
        order = Order(
            id=self._ids.new_id(),
            bot_id=bot.id,
            session_id=session.id,
            client_order_id=f"lc-{self._ids.new_id().hex}",
            symbol=bot.config.symbol,
            side=side,
            quantity=fill.quantity,
            bar_time=candle.open_time,
            created_at=self._clock.now(),
            product=TradingProduct.LINEAR_PERPETUAL,
            position_side=position.side,
            leverage=position.leverage,
            reduce_only=True,
            reference_price=reference,
        )
        order.submit()
        order.apply_fill(fill)
        if not await store.orders.add_if_absent(order):
            raise ConflictError("duplicate Futures paper close order")
        await store.perpetual_portfolio.append_entry(
            PerpetualLedgerEntry(
                id=self._ids.new_id(),
                bot_id=bot.id,
                occurred_at=fill.time,
                kind=PerpetualLedgerEventKind.LIQUIDATED
                if liquidated
                else PerpetualLedgerEventKind.POSITION_REDUCED,
                wallet_delta=released + realized,
                isolated_margin_delta=-released,
                realized_pnl_delta=realized,
                fee=fill.total_fee,
                quantity=fill.quantity,
                side=position.side,
                price=fill.price,
                source="paper_fill",
                external_reference=f"paper:{order.client_order_id}:fill",
            )
        )
        await store.audit.add(
            AuditEvent(
                "futures.position_liquidated" if liquidated else "order.filled",
                "order",
                str(order.id),
                actor="worker",
                bot_id=bot.id,
                payload={
                    "product": "linear_perpetual",
                    "reason": reason,
                    "client_order_id": order.client_order_id,
                    "side": side.value,
                    "quantity": str(fill.quantity),
                    "price": str(fill.price),
                    "fee": str(fill.total_fee),
                },
            )
        )

    async def _record_forced_close(
        self,
        store: TradingStore,
        bot: Bot,
        session: TradingSession,
        candle: Candle,
        position_side: PositionSide,
        quantity: Decimal,
        price: Decimal,
        fee_rate: Decimal,
        reason: str,
        at: datetime,
    ) -> None:
        side = Side.SELL if position_side is PositionSide.LONG else Side.BUY
        fill = Fill(at, side, quantity, price, quantity * price * fee_rate)
        order = Order(
            id=self._ids.new_id(),
            bot_id=bot.id,
            session_id=session.id,
            client_order_id=f"lc-{self._ids.new_id().hex}",
            symbol=bot.config.symbol,
            side=side,
            quantity=quantity,
            bar_time=candle.open_time,
            created_at=self._clock.now(),
            product=TradingProduct.LINEAR_PERPETUAL,
            position_side=position_side,
            leverage=bot.config.leverage,
            reduce_only=True,
            reference_price=price,
        )
        order.submit()
        order.apply_fill(fill)
        if await store.orders.add_if_absent(order):
            await store.audit.add(
                AuditEvent(
                    "futures.position_liquidated",
                    "order",
                    str(order.id),
                    actor="worker",
                    bot_id=bot.id,
                    payload={
                        "reason": reason,
                        "client_order_id": order.client_order_id,
                        "price": str(price),
                        "quantity": str(quantity),
                    },
                )
            )

    async def _check_risk(
        self,
        store: TradingStore,
        bot: Bot,
        ledger: PerpetualLedger,
        mark: Candle,
        exited: bool,
        snapshots: list[PerpetualPortfolioSnapshot],
    ) -> bool:
        cfg = bot.config
        equity = ledger.equity(mark.close)
        same_day = [
            snapshot for snapshot in snapshots if snapshot.taken_at.date() == mark.close_time.date()
        ]
        prior = [
            snapshot for snapshot in snapshots if snapshot.taken_at.date() < mark.close_time.date()
        ]
        day_start = (
            same_day[0].equity if same_day else (prior[-1].equity if prior else cfg.initial_capital)
        )
        peak = max((snapshot.equity for snapshot in snapshots), default=cfg.initial_capital)
        risk_event = None
        if daily_loss_breached(equity, day_start, cfg.risk):
            risk_event = ("risk.daily_loss_breached", "daily loss limit breached")
        elif drawdown_breached(equity, max(peak, cfg.initial_capital), cfg.risk):
            risk_event = ("risk.drawdown_breached", "max drawdown limit breached")
        elif exited and consecutive_losses_breached(
            round_trip_pnls(await store.orders.list_fills(bot.id)), cfg.risk
        ):
            risk_event = ("risk.consecutive_losses", "max consecutive losses reached")
        if risk_event is None:
            return False
        event, message = risk_event
        action = (
            "stop"
            if cfg.risk.drawdown_action.value == "stop" and event == "risk.drawdown_breached"
            else "pause"
        )
        state = BotState.STOPPED if action == "stop" else BotState.PAUSED
        await store.bots.set_desired(bot.id, state)
        await store.bots.set_observed(bot.id, state, message)
        await store.audit.add(
            AuditEvent(
                event,
                "bot",
                str(bot.id),
                actor="worker",
                bot_id=bot.id,
                payload={"reason": message, "action": action, "equity": str(equity)},
            )
        )
        return True


class PerpetualPaperTrader(_PerpetualTrader):
    """Isolated-perpetual simulator; paper fills never reach an exchange."""

    async def process(self, bot: Bot, session: TradingSession, now: datetime) -> None:
        if bot.config.mode is not ExecutionMode.PAPER:
            raise ConflictError("PerpetualPaperTrader only accepts paper-mode bots")
        await super().process(bot, session, now)


class PerpetualDemoTrader(_PerpetualTrader):
    """USD-M Demo execution path sharing signal/risk logic, not the paper fill adapter."""

    async def process(self, bot: Bot, session: TradingSession, now: datetime) -> None:
        if bot.config.mode is not ExecutionMode.TESTNET:
            raise ConflictError("PerpetualDemoTrader only accepts Binance Demo bots")
        if self._executor is None:
            raise ConflictError("Perpetual Demo requires an OrderExecutor")
        await super().process(bot, session, now)


def _floor(at: datetime, timeframe: Timeframe) -> datetime:
    return floor_to_timeframe(at, timeframe)


def _tier_for(
    tiers: list[LeverageTier], notional: Decimal, leverage: int | None = None
) -> LeverageTier:
    tier = next(
        (
            item
            for item in tiers
            if item.min_notional <= notional < item.max_notional
            and (leverage is None or item.max_leverage >= leverage)
        ),
        None,
    )
    if tier is None:
        detail = f" at {leverage}x" if leverage is not None else ""
        raise ConflictError(f"no Binance leverage tier covers notional {notional}{detail}")
    return tier
