from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from core.ids import UuidGenerator
from modules.backtesting.domain.models import BacktestConfig, FillTiming
from modules.backtesting.domain.perpetual_engine import run_perpetual_backtest
from modules.bots.domain.models import Bot, BotConfig, BotState, ExecutionMode
from modules.exchanges.domain.models import LeverageTier, MarginMode, TradingProduct
from modules.execution.domain.orders import Order
from modules.market_data.domain.models import Candle, MarketInfo, Timeframe
from modules.portfolio.domain.perpetual_ledger import (
    PerpetualLedgerEntry,
    PerpetualPortfolioSnapshot,
)
from modules.portfolio.domain.perpetuals import PerpetualLedger
from modules.risk_management.domain.models import KillSwitchState, RiskLimits
from modules.strategies.catalog import build_strategy_registry
from modules.trading.application.perpetual_paper import PerpetualPaperTrader
from modules.trading.domain.models import SessionStatus, TradingSession

D = Decimal
START = datetime(2024, 1, 1, tzinfo=UTC)
SYMBOL = "BTC/USDT:USDT"
TIERS = [LeverageTier(1, D("0"), D("1000000"), 10, D("0.005"))]
MARKET = MarketInfo(SYMBOL, D("0.001"), D("0.01"), D("0.001"), D("5"))


class _Portfolio:
    def __init__(self) -> None:
        self.ledger: PerpetualLedger | None = None
        self.entries: list[PerpetualLedgerEntry] = []
        self.snapshots: list[PerpetualPortfolioSnapshot] = []

    async def get(self, bot_id):
        return self.ledger

    async def save(self, ledger: PerpetualLedger) -> None:
        self.ledger = ledger

    async def list_snapshots(self, bot_id):
        return list(self.snapshots)

    async def append_entry(self, entry: PerpetualLedgerEntry) -> bool:
        self.entries.append(entry)
        return True

    async def has_entry(self, bot_id, external_reference: str) -> bool:
        return any(item.external_reference == external_reference for item in self.entries)

    async def add_snapshot(self, snapshot: PerpetualPortfolioSnapshot) -> None:
        self.snapshots.append(snapshot)


class _Orders:
    def __init__(self) -> None:
        self.items: list[Order] = []

    async def count_unresolved(self, bot_id) -> int:
        return 0

    async def add_if_absent(self, order: Order) -> bool:
        if any(item.client_order_id == order.client_order_id for item in self.items):
            return False
        self.items.append(order)
        return True

    async def list_fills(self, bot_id):
        return [fill for order in self.items for fill in order.fills]


class _Candles:
    def __init__(self, candles: list[Candle]) -> None:
        self.items = candles

    async def get_range(self, exchange, symbol, timeframe, start, end):
        return [
            candle
            for candle in self.items
            if start <= candle.open_time and candle.close_time <= end
        ]


class _BotRepository:
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    async def get(self, bot_id):
        return self.bot

    async def set_desired(self, bot_id, state: BotState) -> None:
        self.bot.desired_state = state

    async def set_observed(self, bot_id, state: BotState, error) -> None:
        self.bot.observed_state = state


class _Sessions:
    async def save_progress(self, session_id, strategy_state, last_bar_time) -> None:
        return None


class _Signals:
    def __init__(self) -> None:
        self.items = []

    async def add(self, signal) -> None:
        self.items.append(signal)


class _Audit:
    async def add(self, event) -> None:
        return None


class _Flags:
    async def get_kill_switch(self) -> KillSwitchState:
        return KillSwitchState()


class _Store:
    def __init__(self, bot: Bot, candles: list[Candle]) -> None:
        self.perpetual_portfolio = _Portfolio()
        self.orders = _Orders()
        self.bots = _BotRepository(bot)
        self.candles = _Candles(candles)
        self.sessions = _Sessions()
        self.signals = _Signals()
        self.audit = _Audit()
        self.flags = _Flags()

    async def commit(self) -> None:
        return None


class _Clock:
    def __init__(self) -> None:
        self.current = START

    def now(self) -> datetime:
        return self.current


def _candles(closes: list[str]) -> list[Candle]:
    candles: list[Candle] = []
    for index, raw_close in enumerate(closes):
        close = D(raw_close)
        open_ = D(closes[index - 1]) if index else close
        candles.append(
            Candle(
                SYMBOL,
                Timeframe.M5,
                START + index * Timeframe.M5.delta,
                open_,
                max(open_, close),
                min(open_, close),
                close,
                D("1000"),
            )
        )
    return candles


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("strategy_type", "strategy_params", "allow_short", "closes"),
    [
        (
            "mean_reversion_zscore",
            {"lookback": 5, "entry_z": 1},
            False,
            ["100", "100", "100", "100", "90", "94", "98"],
        ),
        (
            "mean_reversion_zscore",
            {"lookback": 5, "entry_z": 1},
            True,
            ["100", "100", "100", "100", "110", "106", "102"],
        ),
        (
            "trend_quality_breakout",
            {"entry_period": 2, "exit_period": 2, "atr_multiple": 2},
            False,
            ["100", "101", "102", "105", "106", "99"],
        ),
        (
            "trend_quality_breakout",
            {"entry_period": 2, "exit_period": 2, "atr_multiple": 2},
            True,
            ["100", "99", "98", "95", "94", "101"],
        ),
    ],
)
async def test_futures_paper_worker_matches_signal_close_replay(
    strategy_type: str,
    strategy_params: dict[str, int],
    allow_short: bool,
    closes: list[str],
) -> None:
    candles = _candles(closes)
    bot_id = uuid4()
    config = BotConfig(
        name="Golden Futures paper",
        exchange="binance-usdm",
        strategy_type=strategy_type,
        strategy_params=strategy_params,
        symbol=SYMBOL,
        timeframe=Timeframe.M5,
        initial_capital=D("1000"),
        fee_rate=D("0.001"),
        slippage_bps=D("0"),
        mode=ExecutionMode.PAPER,
        connection_id=uuid4(),
        product=TradingProduct.LINEAR_PERPETUAL,
        leverage=2,
        margin_mode=MarginMode.ISOLATED,
        allow_short=allow_short,
        risk=RiskLimits(max_daily_loss_pct=None, max_candle_range_pct=None),
    )
    bot = Bot(bot_id, config, BotState.RUNNING, BotState.RUNNING, 1, START, START)
    session = TradingSession(
        uuid4(), bot_id, 1, SessionStatus.ACTIVE, candles[0].close_time, mode="paper"
    )
    store = _Store(bot, candles)

    @asynccontextmanager
    async def stores():
        yield store

    clock = _Clock()
    worker = PerpetualPaperTrader(
        stores,
        build_strategy_registry(),
        exchanges=None,  # type: ignore[arg-type]
        resolver=None,
        clock=clock,  # type: ignore[arg-type]
        ids=UuidGenerator(),
    )
    strategy = build_strategy_registry().create(config.strategy_type, config.strategy_params)
    state = strategy.initial_state()
    for candle in candles:
        clock.current = candle.close_time + timedelta(seconds=5)
        state, paused = await worker._process_candle(
            bot,
            session,
            strategy,
            state,
            candle,
            candle,
            [],
            MARKET,
            TIERS,
            clock.now(),
        )
        assert not paused

    backtest_config = BacktestConfig(
        exchange=config.exchange,
        symbol=config.symbol,
        timeframe=config.timeframe,
        start=candles[0].open_time,
        end=candles[-1].close_time,
        initial_capital=config.initial_capital,
        fee_rate=config.fee_rate,
        slippage_bps=config.slippage_bps,
        strategy_type=config.strategy_type,
        strategy_params=config.strategy_params,
        fill_timing=FillTiming.SIGNAL_CLOSE,
        risk=config.risk,
        product=config.product,
        leverage=config.leverage,
        margin_mode=config.margin_mode,
        allow_short=config.allow_short,
        connection_id=config.connection_id,
        leverage_tiers=tuple(TIERS),
        leverage_tiers_at=START,
    )
    replay = run_perpetual_backtest(
        backtest_config,
        candles,
        candles,
        [],
        MARKET,
        build_strategy_registry().create(config.strategy_type, config.strategy_params),
        liquidation_fee_rate=config.fee_rate,
        trade_from=session.started_at,
    )

    worker_signals = [
        (item.bar_time, item.side, item.kind)
        for item in store.signals.items
    ]
    replay_signals = [(item.bar_time, item.side, item.kind) for item in replay.signals]
    assert worker_signals == replay_signals

    worker_fills = [
        (fill.time, fill.side, fill.quantity, fill.price, fill.total_fee)
        for order in store.orders.items
        for fill in order.fills
    ]
    replay_fills = [
        (fill.time, fill.side, fill.quantity, fill.price, fill.total_fee) for fill in replay.fills
    ]
    assert worker_fills == replay_fills
    assert store.perpetual_portfolio.ledger is not None
    assert (
        store.perpetual_portfolio.ledger.equity(candles[-1].close) == replay.equity_curve[-1].equity
    )
