"""Reconciles each bot's ``desired_state`` (set by the API) with what the worker is doing."""

import logging
from datetime import datetime, timedelta
from uuid import UUID

from core.clock import Clock
from core.ids import IdGenerator
from core.security.vault import VaultError, VaultNotConfigured
from modules.audit.models import AuditEvent
from modules.bots.domain.models import Bot, BotState, ExecutionMode
from modules.exchanges.application.connections import ConnectionResolver, InvalidConnection
from modules.exchanges.domain.connections import Environment
from modules.exchanges.domain.models import TradingProduct
from modules.exchanges.errors import AuthenticationFailed
from modules.risk_management.domain.models import KillSwitchState
from modules.strategies.domain.registry import StrategyRegistry
from modules.trading.application.orders import OrderExecutor
from modules.trading.application.perpetual_close import PerpetualCloseService
from modules.trading.application.reconciler import Reconciler
from modules.trading.application.trader import BotTrader, TradingStoreFactory
from modules.trading.domain.models import MAX_CONSECUTIVE_FAILURES, SessionStatus, TradingSession

logger = logging.getLogger(__name__)

_MAX_BACKOFF_SECONDS = 60
# Retrying cannot fix these: stop the bot and let the operator look.
_FATAL = (AuthenticationFailed, InvalidConnection, VaultError, VaultNotConfigured)


class BotSupervisor:
    """One pass per call: failures are isolated per bot so one bad bot never stops the others.

    Transient failures back off exponentially; after ``MAX_CONSECUTIVE_FAILURES`` the bot is
    put in the ``error`` state and paused instead of retrying forever.
    """

    def __init__(
        self,
        stores: TradingStoreFactory,
        trader: BotTrader,
        registry: StrategyRegistry,
        clock: Clock,
        ids: IdGenerator,
        *,
        resolver: ConnectionResolver | None = None,
        executor: OrderExecutor | None = None,
        reconciler: Reconciler | None = None,
        perpetual_closer: PerpetualCloseService | None = None,
        testnet_enabled: bool = False,
        futures_paper_enabled: bool = False,
        live_enabled: bool = False,
        is_production: bool = False,
        live_caps_configured: bool = False,
        live_require_ip_restriction: bool = True,
        reconcile_interval: timedelta = timedelta(seconds=60),
        stop_poll_interval: timedelta = timedelta(seconds=10),
    ) -> None:
        self._stores = stores
        self._trader = trader
        self._registry = registry
        self._clock = clock
        self._ids = ids
        self._failures: dict[UUID, int] = {}
        self._retry_at: dict[UUID, datetime] = {}
        self._resolver = resolver
        self._executor = executor
        self._reconciler = reconciler
        self._perpetual_closer = perpetual_closer
        self._testnet_enabled = testnet_enabled
        self._futures_paper_enabled = futures_paper_enabled
        self._live_enabled = live_enabled
        self._is_production = is_production
        self._live_caps_configured = live_caps_configured
        self._live_require_ip = live_require_ip_restriction
        self._reconcile_interval = reconcile_interval
        self._stop_poll_interval = stop_poll_interval
        self._last_reconcile: datetime | None = None
        self._last_stop_poll: datetime | None = None
        self._kill_close_retry_at: dict[UUID, datetime] = {}

    async def run_once(self) -> None:
        async with self._stores() as store:
            kill_switch = await store.flags.get_kill_switch()
            bots = await store.bots.list_active()
        if kill_switch.active:
            if kill_switch.close_futures_positions:
                async with self._stores() as store:
                    bots = await store.bots.list_bots(500)
            bots = await self._apply_kill_switch(bots, kill_switch)

        if self._resolver is not None:
            try:  # live keys stay unusable until we know what they may do
                await self._resolver.verify_pending(self._live_require_ip)
            except Exception:
                logger.exception("connection verification failed")
            try:  # and keys already active may have been changed on the exchange since
                await self._resolver.recheck_due(self._live_require_ip)
            except Exception:
                logger.exception("connection recheck failed")
        await self._housekeeping(bots)
        async with self._stores() as store:  # housekeeping may have paused or failed some bots
            bots = await store.bots.list_active()

        running: list[UUID] = []
        for bot in bots:
            try:
                await self._handle(bot)
                if bot.desired_state is BotState.RUNNING:
                    running.append(bot.id)
            except Exception as exc:
                await self._on_failure(bot, exc)
        async with self._stores() as store:
            now = self._clock.now()
            if running:
                await store.bots.heartbeat(running, now)
            await store.flags.set_worker_heartbeat(now)  # lets the API tell if the worker is alive
            await store.commit()

    async def _housekeeping(self, bots: list[Bot]) -> None:
        """Real-exchange upkeep that does not belong to any single candle.

        Settle orders of unknown outcome, notice stops that fired while we were away and, at
        a slower pace, compare the account with our books. Failures here are logged, never
        fatal: a flaky exchange must not stop the other bots.
        """
        if self._reconciler is None or self._executor is None:
            return
        now = self._clock.now()
        testnet = [
            b
            for b in bots
            if b.config.mode.uses_exchange and b.observed_state is not BotState.ERROR
        ]
        if not testnet:
            return
        try:
            await self._reconciler.resolve_pending()
            if (
                self._last_stop_poll is None
                or now - self._last_stop_poll >= self._stop_poll_interval
            ):
                self._last_stop_poll = now
                for bot in testnet:
                    try:
                        await self._executor.sync_native_stop(bot)
                    except Exception:
                        logger.exception("stop sync failed for bot %s", bot.id)
            if (
                self._last_reconcile is None
                or now - self._last_reconcile >= self._reconcile_interval
            ):
                self._last_reconcile = now
                await self._reconciler.reconcile_accounts()
        except Exception:
            logger.exception("exchange housekeeping failed")

    def _mode_problem(self, bot: Bot) -> str | None:
        """Why this bot may not trade right now. Evaluated on EVERY pass, not just at start:
        a worker restarted with a safeguard switched off must stop a bot that was already
        running, never keep trading it."""
        mode = bot.config.mode
        if bot.config.product is TradingProduct.LINEAR_PERPETUAL:
            if mode is not ExecutionMode.PAPER:
                return "USD-M Futures exchange order execution is not released"
            if not self._futures_paper_enabled:
                return "Futures paper is disabled (set FUTURES_PAPER_ENABLED=true on the worker)"
        if mode is ExecutionMode.TESTNET and not self._testnet_enabled:
            return (
                "demo/testnet trading is disabled (set TESTNET_TRADING_ENABLED=true on the worker)"
            )
        if mode is ExecutionMode.LIVE:
            if not self._live_enabled:
                return "live trading is disabled (LIVE_TRADING_ENABLED is not true on the worker)"
            if not self._is_production:
                return "live trading only runs with APP_ENV=prod"
            if not self._live_caps_configured:
                return (
                    "live hard caps are not configured (LIVE_MAX_ORDER_NOTIONAL, "
                    "LIVE_MAX_TOTAL_EXPOSURE, LIVE_MAX_DAILY_LOSS)"
                )
            if not bot.has_live_approval:
                return "no valid live approval for this configuration version"
        return None

    async def _handle(self, bot: Bot) -> None:
        if bot.desired_state is BotState.RUNNING:
            if problem := self._mode_problem(bot):
                await self._enter_error(bot, problem)
                return
            if bot.observed_state is not BotState.RUNNING and not await self._start(bot):
                return
            retry_at = self._retry_at.get(bot.id)
            if retry_at is not None and self._clock.now() < retry_at:
                return
            await self._trader.process(bot)
            self._failures.pop(bot.id, None)
            self._retry_at.pop(bot.id, None)
        elif bot.desired_state is BotState.PAUSED:
            # An ERROR observation is kept (with its message) until the user starts the bot again.
            if bot.observed_state not in (BotState.PAUSED, BotState.ERROR):
                await self._set_observed(bot, BotState.PAUSED, "bot.paused")
        elif bot.observed_state is not BotState.STOPPED:
            await self._stop(bot)

    async def _connection_problem(self, bot: Bot) -> str | None:
        """Why a real-exchange bot cannot get a working connection, or None. Checked on start."""
        if self._resolver is None or bot.config.connection_id is None:
            return f"{bot.config.mode.value} bot has no usable exchange connection"
        try:
            exchange = await self._resolver.exchange_for(bot.config.connection_id)
        except Exception as exc:
            return f"exchange connection unusable: {type(exc).__name__}: {exc}"
        if bot.config.mode is ExecutionMode.TESTNET and not exchange.capabilities.has_testnet:
            return f"{bot.config.exchange} has no testnet"
        environment = await self._resolver.environment_for(bot.config.connection_id)
        if bot.config.product is TradingProduct.LINEAR_PERPETUAL:
            if environment is not Environment.DEMO:
                return "Binance USD-M futures require a Binance Demo Mode connection"
            if not exchange.capabilities.has_demo:
                return f"{bot.config.exchange} has no Demo Mode API"
        if bot.config.product is TradingProduct.LINEAR_PERPETUAL:
            try:
                markets = await exchange.list_markets()
                market = next(
                    (
                        item
                        for item in markets
                        if item.symbol == bot.config.symbol
                        and item.product == TradingProduct.LINEAR_PERPETUAL.value
                        and item.settlement == "USDT"
                    ),
                    None,
                )
                if market is None or not market.active:
                    return "Futures symbol is not an active Binance USD-M USDT perpetual"
                await exchange.fetch_market_info(bot.config.symbol)
                max_notional = (
                    bot.config.initial_capital
                    * bot.config.risk.max_position_fraction
                    * bot.config.leverage
                )
                if bot.config.risk.max_order_notional is not None:
                    max_notional = min(max_notional, bot.config.risk.max_order_notional)
                tiers = await exchange.fetch_leverage_tiers(bot.config.symbol)
                if not any(tier.supports(max_notional, bot.config.leverage) for tier in tiers):
                    return "Binance Demo leverage tiers do not support the configured notional"
                await exchange.prepare_market_configuration(
                    product=bot.config.product,
                    symbol=bot.config.symbol,
                    leverage=bot.config.leverage,
                    margin_mode=bot.config.margin_mode,
                    max_notional=max_notional,
                )
            except Exception as exc:
                return f"Futures Demo market or account validation failed: {exc}"
        return None

    async def _enter_error(self, bot: Bot, message: str) -> None:
        async with self._stores() as store:
            await store.bots.set_desired(bot.id, BotState.PAUSED)
            await store.bots.set_observed(bot.id, BotState.ERROR, message)
            await store.audit.add(
                AuditEvent(
                    "bot.error",
                    "bot",
                    str(bot.id),
                    actor="worker",
                    bot_id=bot.id,
                    payload={"error": message},
                )
            )
            await store.commit()
        bot.desired_state, bot.observed_state = BotState.PAUSED, BotState.ERROR

    async def _start(self, bot: Bot) -> bool:
        """Start (or resume) the bot. False when it was refused and put in the error state."""
        self._registry.create(bot.config.strategy_type, bot.config.strategy_params)  # validates
        needs_connection = bot.config.mode.uses_exchange or (
            bot.config.product is TradingProduct.LINEAR_PERPETUAL
        )
        if needs_connection and (problem := await self._connection_problem(bot)):
            await self._enter_error(bot, problem)
            return False
        async with self._stores() as store:
            existing_session = await store.sessions.get_active(bot.id)
        execution_snapshot = None
        if bot.config.product is TradingProduct.LINEAR_PERPETUAL and existing_session is None:
            try:
                if self._resolver is None or bot.config.connection_id is None:
                    raise RuntimeError("Futures session has no Binance Demo connection")
                exchange = await self._resolver.exchange_for(bot.config.connection_id)
                tiers = await exchange.fetch_leverage_tiers(bot.config.symbol)
                if not tiers:
                    raise RuntimeError("Binance Demo returned no leverage tiers")
                execution_snapshot = {
                    "leverage_tiers": [
                        {
                            "tier": tier.tier,
                            "min_notional": str(tier.min_notional),
                            "max_notional": str(tier.max_notional),
                            "max_leverage": tier.max_leverage,
                            "maintenance_margin_rate": str(tier.maintenance_margin_rate),
                            "cumulative_maintenance_amount": str(
                                tier.cumulative_maintenance_amount
                            ),
                        }
                        for tier in tiers
                    ],
                    "leverage_tiers_at": self._clock.now().isoformat(),
                    "config_version": bot.config_version,
                }
            except Exception as exc:
                await self._enter_error(
                    bot,
                    f"could not pin Futures leverage tiers for this session: "
                    f"{type(exc).__name__}: {exc}",
                )
                return False
        resumed = bot.observed_state is BotState.PAUSED
        async with self._stores() as store:
            if await store.sessions.get_active(bot.id) is None:
                await store.sessions.add(
                    TradingSession(
                        id=self._ids.new_id(),
                        bot_id=bot.id,
                        config_version=bot.config_version,
                        status=SessionStatus.ACTIVE,
                        started_at=self._clock.now(),
                        mode=bot.config.mode.value,
                        execution_snapshot=execution_snapshot,
                    )
                )
            await store.bots.set_observed(bot.id, BotState.RUNNING, None)
            await store.audit.add(
                AuditEvent(
                    "bot.resumed" if resumed else "bot.started",
                    "bot",
                    str(bot.id),
                    actor="worker",
                    bot_id=bot.id,
                    payload={"config_version": bot.config_version, "mode": bot.config.mode.value},
                )
            )
            await store.commit()
        bot.observed_state = BotState.RUNNING
        if bot.config.mode.uses_exchange and self._reconciler and self._executor:
            # Catch up on anything that happened to our orders while the bot was not running.
            try:
                await self._reconciler.resolve_pending()
                await self._executor.sync_native_stop(bot)
            except Exception:
                logger.exception("start-up reconciliation failed for bot %s", bot.id)
        return True

    async def _stop(self, bot: Bot) -> None:
        async with self._stores() as store:
            session = await store.sessions.get_active(bot.id)
            if session is not None:
                await store.sessions.end(session.id, "stopped")
            await store.bots.set_observed(bot.id, BotState.STOPPED, None)
            await store.audit.add(
                AuditEvent("bot.stopped", "bot", str(bot.id), actor="worker", bot_id=bot.id)
            )
            await store.commit()
        self._failures.pop(bot.id, None)
        self._retry_at.pop(bot.id, None)

    async def _set_observed(self, bot: Bot, state: BotState, event: str) -> None:
        async with self._stores() as store:
            await store.bots.set_observed(bot.id, state, None)
            await store.audit.add(
                AuditEvent(event, "bot", str(bot.id), actor="worker", bot_id=bot.id)
            )
            await store.commit()

    async def _apply_kill_switch(self, bots: list[Bot], state: KillSwitchState) -> list[Bot]:
        async with self._stores() as store:
            for bot in bots:
                if bot.desired_state is BotState.RUNNING:
                    await store.bots.set_desired(bot.id, BotState.PAUSED)
                    await store.audit.add(
                        AuditEvent(
                            "bot.paused_by_kill_switch",
                            "bot",
                            str(bot.id),
                            actor="worker",
                            bot_id=bot.id,
                            payload={"reason": state.reason},
                        )
                    )
                    bot.desired_state = BotState.PAUSED
            await store.commit()
        if state.close_futures_positions:
            for bot in bots:
                if bot.config.product is TradingProduct.LINEAR_PERPETUAL:
                    await self._close_futures_for_kill_switch(bot, state)
        return bots

    async def _close_futures_for_kill_switch(self, bot: Bot, state: KillSwitchState) -> None:
        """Execute the separately opted-in, Demo-only Futures kill policy.

        Opening orders are canceled and their racing fills reconciled before the reduce-only
        close is submitted. Failures leave the existing exchange stop untouched and are retried.
        """
        if bot.config.mode not in (ExecutionMode.PAPER, ExecutionMode.TESTNET):
            return  # live remains blocked; never turn a global stop into an implicit live order
        if self._executor is None or self._perpetual_closer is None or self._resolver is None:
            return
        retry_at = self._kill_close_retry_at.get(bot.id)
        if retry_at is not None and self._clock.now() < retry_at:
            return
        try:
            async with self._stores() as store:
                ledger = await store.perpetual_portfolio.get(bot.id)
            if ledger is None or ledger.position is None:
                self._kill_close_retry_at.pop(bot.id, None)
                return
            if (
                bot.config.connection_id is None
                or (await self._resolver.environment_for(bot.config.connection_id))
                is not Environment.DEMO
            ):
                raise RuntimeError("Futures kill close is restricted to Binance Demo")
            if bot.config.mode is ExecutionMode.TESTNET:
                await self._executor.cancel_opening_perpetual_orders(bot)
            close_order = await self._perpetual_closer.close(
                bot.id,
                actor="worker",
                reason=f"kill switch: {state.reason or 'operator request'}",
            )
            if close_order.is_unresolved and bot.config.mode is ExecutionMode.TESTNET:
                await self._executor.resolve(bot, close_order)
                async with self._stores() as store:
                    close_order = await store.orders.get(close_order.id) or close_order
            if close_order.status.value != "FILLED":
                raise RuntimeError(
                    "Futures kill close is "
                    f"{close_order.status.value}; position remains under review"
                )
            async with self._stores() as store:
                await store.audit.add(
                    AuditEvent(
                        "system.kill_switch_futures_closed",
                        "bot",
                        str(bot.id),
                        actor="worker",
                        bot_id=bot.id,
                        payload={
                            "symbol": bot.config.symbol,
                            "mode": bot.config.mode.value,
                            "client_order_id": close_order.client_order_id,
                            "reason": state.reason,
                        },
                    )
                )
                await store.commit()
            self._kill_close_retry_at.pop(bot.id, None)
        except Exception as exc:
            self._kill_close_retry_at[bot.id] = self._clock.now() + timedelta(seconds=30)
            logger.exception("kill-switch Futures close failed for bot %s", bot.id)
            async with self._stores() as store:
                await store.audit.add(
                    AuditEvent(
                        "system.kill_switch_futures_close_failed",
                        "bot",
                        str(bot.id),
                        actor="worker",
                        bot_id=bot.id,
                        payload={"error_type": type(exc).__name__},
                    )
                )
                await store.commit()

    async def _on_failure(self, bot: Bot, exc: Exception) -> None:
        if isinstance(exc, _FATAL):
            logger.error("bot %s cannot continue: %s", bot.id, exc)
            await self._enter_error(bot, f"{type(exc).__name__}: {exc}"[:500])
            self._failures.pop(bot.id, None)
            self._retry_at.pop(bot.id, None)
            return
        count = self._failures.get(bot.id, 0) + 1
        self._failures[bot.id] = count
        logger.exception("bot %s failed (%d consecutive)", bot.id, count)
        if count < MAX_CONSECUTIVE_FAILURES:
            delay = min(_MAX_BACKOFF_SECONDS, 2**count)
            self._retry_at[bot.id] = self._clock.now() + timedelta(seconds=delay)
            return
        await self._enter_error(bot, f"{type(exc).__name__}: {exc}"[:500])
        self._failures.pop(bot.id, None)
        self._retry_at.pop(bot.id, None)
