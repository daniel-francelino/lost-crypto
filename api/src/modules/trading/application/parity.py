"""Bot vs backtest parity (book 1 ch. 5, O3): replay a bot's latest session through the backtester
on the candles the bot stored, with the bot's fill timing and risk limits, and classify every
difference (see ``trading.domain.parity``). Read-only: it never touches the bot.
"""

import asyncio
import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from core.clock import Clock
from core.errors import DomainError, NotFoundError
from core.ids import IdGenerator
from modules.backtesting.domain.engine import run_backtest
from modules.backtesting.domain.models import (
    BacktestConfig,
    BacktestOutcome,
    BacktestOutcomeView,
    FillTiming,
)
from modules.backtesting.domain.perpetual_engine import (
    PerpetualBacktestOutcome,
    run_perpetual_backtest,
)
from modules.bots.domain.models import Bot
from modules.exchanges.domain.models import LeverageTier, TradingProduct
from modules.market_data.domain.models import Candle, FundingRate, MarketInfo, floor_to_timeframe
from modules.strategies.domain.registry import StrategyRegistry
from modules.trading.application.parity_store import ParityRun
from modules.trading.application.ports import TradingStore
from modules.trading.domain.models import TradingSession, warmup_candles
from modules.trading.domain.parity import (
    BotSignal,
    Difference,
    ParityClass,
    ReplayEvent,
    bar_of_fill,
    compare,
)

if TYPE_CHECKING:
    from modules.exchanges.application.registry import ExchangeRegistry

logger = logging.getLogger(__name__)

TradingStoreFactory = Callable[[], AbstractAsyncContextManager[TradingStore]]

MAX_RECORDS = 20_000  # signals/orders read for one session
MAX_LISTED = 200  # differences kept in the summary
MAX_CURVE_POINTS = 500
_PCT = Decimal(100)
_Q = Decimal("0.0001")


class ParityNotFound(NotFoundError):
    pass


class ParityUnavailable(DomainError):
    pass


class ParityService:
    """API side: queue a parity run and read the latest one."""

    def __init__(self, stores: TradingStoreFactory, clock: Clock, ids: IdGenerator) -> None:
        self._stores = stores
        self._clock = clock
        self._ids = ids

    async def request(self, bot_id: UUID) -> ParityRun:
        async with self._stores() as store:
            if await store.bots.get(bot_id) is None:
                raise ParityNotFound(f"bot {bot_id} not found")
            if await store.sessions.latest(bot_id) is None:
                raise ParityUnavailable("the bot has not run yet: nothing to compare")
            current = await store.parity.latest(bot_id)
            if current is not None and current.status in ("queued", "running"):
                return current
            run = ParityRun(self._ids.new_id(), bot_id, None, "queued", self._clock.now())
            await store.parity.add(run)
            await store.commit()
        return run

    async def latest(self, bot_id: UUID) -> ParityRun | None:
        async with self._stores() as store:
            if await store.bots.get(bot_id) is None:
                raise ParityNotFound(f"bot {bot_id} not found")
            return await store.parity.latest(bot_id)


class ParityExecutor:
    """Worker side: run queued parity jobs."""

    def __init__(
        self,
        stores: TradingStoreFactory,
        registry: StrategyRegistry,
        exchanges: "ExchangeRegistry",
        clock: Clock,
    ) -> None:
        self._stores = stores
        self._registry = registry
        self._exchanges = exchanges
        self._clock = clock

    async def run_next(self) -> bool:
        async with self._stores() as store:
            run = await store.parity.claim_next_queued()
            await store.commit()
        if run is None:
            return False
        try:
            session_id, summary = await self._execute(run)
        except Exception as exc:
            logger.exception("parity run %s failed", run.id)
            async with self._stores() as store:
                await store.parity.finish(
                    run.id,
                    status="failed",
                    finished_at=self._clock.now(),
                    error=f"{type(exc).__name__}: {exc}"[:500],
                )
                await store.commit()
        else:
            async with self._stores() as store:
                await store.parity.finish(
                    run.id,
                    status="completed",
                    finished_at=self._clock.now(),
                    session_id=session_id,
                    unexplained=int(summary["counts"].get(ParityClass.UNEXPLAINED.value, 0)),
                    summary=summary,
                )
                await store.commit()
        return True

    async def _execute(self, run: ParityRun) -> tuple[UUID, dict[str, Any]]:
        async with self._stores() as store:
            bot = await store.bots.get(run.bot_id)
            if bot is None:
                raise ParityUnavailable("the bot no longer exists")
            session = await store.sessions.latest(bot.id)
            if session is None or session.last_processed_bar_time is None:
                raise ParityUnavailable("the bot has not processed any candle yet")
            cfg = bot.config
            delta = cfg.timeframe.delta
            required = self._registry.create(
                cfg.strategy_type, cfg.strategy_params
            ).required_history_candles()
            warm_start = floor_to_timeframe(session.started_at, cfg.timeframe) - (
                warmup_candles(required) * delta
            )
            end = session.last_processed_bar_time + delta
            candles = await store.candles.get_range(
                cfg.exchange, cfg.symbol, cfg.timeframe, warm_start, end
            )
            mark_candles: list[Candle] = []
            funding_rates: list[FundingRate] = []
            execution_snapshot = session.execution_snapshot
            if cfg.product is TradingProduct.LINEAR_PERPETUAL:
                if bot.config_version != session.config_version:
                    raise ParityUnavailable(
                        "the bot configuration changed after this Futures session; "
                        "historical config replay is unavailable"
                    )
                if execution_snapshot is None:
                    raise ParityUnavailable(
                        "this Futures session has no pinned leverage-tier snapshot; "
                        "start a new session before requesting parity"
                    )
                if execution_snapshot.get("config_version") != session.config_version:
                    raise ParityUnavailable(
                        "Futures session configuration snapshot is inconsistent"
                    )
                mark_candles = await store.perpetual_data.get_mark_candles(
                    cfg.exchange, cfg.symbol, cfg.timeframe, warm_start, end
                )
                funding_rates = await store.perpetual_data.get_funding_rates(
                    cfg.exchange, cfg.symbol, warm_start, end
                )
                prior = [
                    snapshot
                    for snapshot in await store.perpetual_portfolio.list_snapshots(bot.id)
                    if snapshot.taken_at <= session.started_at
                ]
                prior.sort(key=lambda snapshot: snapshot.taken_at)
                capital = prior[-1].equity if prior else cfg.initial_capital
            else:
                capital = (
                    await store.portfolio.equity_at_or_before(bot.id, session.started_at)
                    or cfg.initial_capital
                )
            signals = [
                s
                for s in await store.signals.list_by_bot(bot.id, MAX_RECORDS)
                if s.session_id == session.id
            ]
            orders = [
                o
                for o in await store.orders.list_by_bot(bot.id, MAX_RECORDS)
                if o.session_id == session.id and o.order_type == "market"
            ]
            snapshots = await store.portfolio.list_snapshots(bot.id)
        if not candles:
            raise ParityUnavailable(
                "no stored candles for the session; the bot saves them as it runs"
            )
        market = await self._exchanges.market_data(cfg.exchange).fetch_market_info(cfg.symbol)
        tiers: tuple[LeverageTier, ...] = ()
        tiers_at = None
        if cfg.product is TradingProduct.LINEAR_PERPETUAL:
            assert execution_snapshot is not None
            tiers = tuple(
                LeverageTier(
                    tier=int(item["tier"]),
                    min_notional=Decimal(item["min_notional"]),
                    max_notional=Decimal(item["max_notional"]),
                    max_leverage=int(item["max_leverage"]),
                    maintenance_margin_rate=Decimal(item["maintenance_margin_rate"]),
                    cumulative_maintenance_amount=Decimal(
                        item.get("cumulative_maintenance_amount", "0")
                    ),
                )
                for item in execution_snapshot.get("leverage_tiers", [])
            )
            tiers_at = datetime.fromisoformat(execution_snapshot["leverage_tiers_at"])
            if not tiers:
                raise ParityUnavailable("Futures session has an empty leverage-tier snapshot")
        config = _replay_config(bot, candles, end, capital, tiers, tiers_at)
        strategy = self._registry.create(cfg.strategy_type, cfg.strategy_params)
        outcome: BacktestOutcome | PerpetualBacktestOutcome
        if cfg.product is TradingProduct.LINEAR_PERPETUAL:
            outcome = await asyncio.to_thread(
                run_perpetual_backtest,
                config,
                candles,
                mark_candles,
                funding_rates,
                market,
                strategy,
                liquidation_fee_rate=cfg.fee_rate,
                trade_from=session.started_at,
            )
        else:
            outcome = await asyncio.to_thread(
                run_backtest, config, candles, market, strategy, trade_from=session.started_at
            )
        simplified = await asyncio.to_thread(
            self._simplified,
            bot,
            config,
            candles,
            market,
            session,
            mark_candles,
            funding_rates,
        )
        fill_prices = {
            (o.bar_time, o.side): o.avg_fill_price for o in orders if o.avg_fill_price is not None
        }
        bot_signals = [
            BotSignal(
                s.bar_time,
                s.side,
                s.reason,
                s.decision,
                s.decision_reason,
                fill_prices.get((s.bar_time, s.side)),
            )
            for s in signals
        ]
        differences = compare(
            bot_signals,
            _replay_events(outcome, candles, delta),
            {c.open_time for c in candles},
        )
        session_snapshots = [s for s in snapshots if s.session_id == session.id]
        bot_return = (
            None if not session_snapshots else _return_pct(capital, session_snapshots[-1].equity)
        )
        traded = [p for p in outcome.equity_curve if p.time > session.started_at]
        return session.id, _summary(
            session,
            differences,
            candles,
            bot_return,
            _return_pct(capital, traded[-1].equity) if traded else None,
            simplified,
            traded,
        )

    def _simplified(
        self,
        bot: Bot,
        config: BacktestConfig,
        candles: list[Candle],
        market: MarketInfo,
        session: TradingSession,
        mark_candles: list[Candle],
        funding_rates: list[FundingRate],
    ) -> Decimal | None:
        """The same replay with the strategy's default parameters and no stop/target: Chan's
        check for data-snooping (if the result collapses without the tuning, suspect it)."""
        cfg = bot.config
        defaults = {
            spec.name: spec.default
            for spec in self._registry.get(cfg.strategy_type).PARAMETERS
            if spec.default is not None
        }
        if defaults == {k: v for k, v in cfg.strategy_params.items() if v is not None}:
            return None  # already the plain version
        strategy = self._registry.create(cfg.strategy_type, defaults)
        outcome: BacktestOutcome | PerpetualBacktestOutcome
        if cfg.product is TradingProduct.LINEAR_PERPETUAL:
            outcome = run_perpetual_backtest(
                config,
                candles,
                mark_candles,
                funding_rates,
                market,
                strategy,
                liquidation_fee_rate=cfg.fee_rate,
                trade_from=session.started_at,
            )
        else:
            outcome = run_backtest(config, candles, market, strategy, trade_from=session.started_at)
        traded = [p for p in outcome.equity_curve if p.time > session.started_at]
        return _return_pct(config.initial_capital, traded[-1].equity) if traded else None


def _replay_config(
    bot: Bot,
    candles: list[Candle],
    end: Any,
    capital: Decimal,
    leverage_tiers: tuple[LeverageTier, ...] = (),
    leverage_tiers_at: datetime | None = None,
) -> BacktestConfig:
    cfg = bot.config
    return BacktestConfig(
        exchange=cfg.exchange,
        symbol=cfg.symbol,
        timeframe=cfg.timeframe,
        start=candles[0].open_time,
        end=end,
        initial_capital=capital,
        fee_rate=cfg.fee_rate,
        slippage_bps=cfg.slippage_bps,
        strategy_type=cfg.strategy_type,
        strategy_params=cfg.strategy_params,
        fill_timing=FillTiming.SIGNAL_CLOSE,
        risk=cfg.risk,
        product=cfg.product,
        leverage=cfg.leverage,
        margin_mode=cfg.margin_mode,
        allow_short=cfg.allow_short,
        connection_id=cfg.connection_id,
        leverage_tiers=leverage_tiers,
        leverage_tiers_at=leverage_tiers_at,
    )


def _replay_events(
    outcome: BacktestOutcomeView, candles: list[Candle], step: Any
) -> list[ReplayEvent]:
    closes = {c.close_time for c in candles}
    events = [
        ReplayEvent(bar_of_fill(f.time, closes, step), f.side, True, f.price, None)
        for f in outcome.fills
    ]
    events.extend(
        ReplayEvent(bar_of_fill(r.time, closes, step), r.side, False, None, r.reason)
        for r in outcome.rejected
    )
    return events


def _return_pct(start: Decimal, end: Decimal) -> Decimal | None:
    return None if start <= 0 else ((end / start - 1) * _PCT).quantize(_Q)


def _summary(
    session: TradingSession,
    differences: list[Difference],
    candles: list[Candle],
    bot_return: Decimal | None,
    replay_return: Decimal | None,
    simplified_return: Decimal | None,
    curve: list[Any],
) -> dict[str, Any]:
    counts: dict[str, int] = {kind.value: 0 for kind in ParityClass}
    for diff in differences:
        counts[diff.kind.value] += 1
    unexplained = counts[ParityClass.UNEXPLAINED.value]
    step = max(1, len(curve) // MAX_CURVE_POINTS)
    listed = [d for d in differences if d.kind is not ParityClass.MATCH][:MAX_LISTED]
    return {
        "session_id": str(session.id),
        "session_mode": session.mode,
        "period_start": session.started_at.isoformat(),
        "period_end": None
        if session.last_processed_bar_time is None
        else session.last_processed_bar_time.isoformat(),
        "candles": len(candles),
        "fill_timing": FillTiming.SIGNAL_CLOSE.value,
        "counts": counts,
        "verdict": "consistent" if unexplained == 0 else "differences",
        "differences": [
            {
                "bar_time": d.bar_time.isoformat(),
                "side": d.side.value,
                "kind": d.kind.value,
                "bot": d.bot,
                "replay": d.replay,
            }
            for d in listed
        ],
        "bot_return_pct": None if bot_return is None else str(bot_return),
        "replay_return_pct": None if replay_return is None else str(replay_return),
        "simplified_return_pct": None if simplified_return is None else str(simplified_return),
        "replay_equity": [[p.time.isoformat(), str(p.equity)] for p in curve[::step]],
    }
