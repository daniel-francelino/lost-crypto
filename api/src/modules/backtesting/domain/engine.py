"""Event-loop backtester.

Timeline per candle ``i`` (no look-ahead):
  1. signals produced after candle ``i-1`` closed are filled at the *open* of candle ``i``
     (plus slippage and fees);
  2. equity is marked at the close of candle ``i``;
  3. the strategy sees candle ``i`` (closed) and may emit signals for candle ``i+1``.
Signals emitted on the last candle can never be filled and are only counted.

A long position's stop-loss / take-profit (proposed by the strategy's entry signal) is checked
against each candle's low/high, exactly as the paper trader does; the stop wins when both
levels fall inside the same candle.

Fills use the same simulation as paper trading (``execution.domain.fills``). Sizing here is
deliberately trivial (buy with all cash, sell the whole position); in the live pipeline that
responsibility belongs to the risk module.
"""

from collections import deque
from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from modules.analytics.domain.metrics import round_trip_pnls
from modules.backtesting.domain.models import (
    BacktestConfig,
    BacktestOutcome,
    EmittedSignal,
    EquityPoint,
    FillTiming,
    InvalidBacktestConfig,
    RejectedSignal,
)
from modules.execution.domain.fills import (
    affordable_buy_quantity,
    simulate_market_fill,
    slipped_price,
)
from modules.execution.domain.normalizer import OrderRejected
from modules.execution.domain.orders import Fill
from modules.market_data.domain.models import Candle, MarketInfo
from modules.portfolio.domain.models import PortfolioState
from modules.risk_management.domain.models import (
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
from modules.strategies.domain.types import Side, Signal, StrategyContext


def run_backtest(
    config: BacktestConfig,
    candles: Sequence[Candle],
    market: MarketInfo,
    strategy: Strategy[Any],
    *,
    trade_from: datetime | None = None,
) -> BacktestOutcome:
    """``trade_from``: candles closing at or before it only warm the strategy up (no trading),
    as a bot does before its session started (used by the parity replay)."""
    if not candles:
        raise InvalidBacktestConfig("no candles to backtest")

    cash = config.initial_capital
    quantity = Decimal(0)
    fills: list[Fill] = []
    equity: list[EquityPoint] = []
    in_market: list[bool] = []
    rejected: list[RejectedSignal] = []
    emitted: list[EmittedSignal] = []
    state = strategy.initial_state()
    pending: tuple[Signal, ...] = ()
    stop_price: Decimal | None = None
    take_profit_price: Decimal | None = None
    guard = _RiskGuard(config) if config.risk is not None else None
    at_close = config.fill_timing is FillTiming.SIGNAL_CLOSE

    def execute(signal: Signal, reference: Decimal, when: datetime, candle: Candle) -> None:
        nonlocal cash, quantity, stop_price, take_profit_price
        try:
            if guard is not None:
                wanted = guard.size(signal, cash, quantity, reference, market, candle)
            elif signal.side is Side.BUY:
                if quantity > 0:
                    raise OrderRejected("already in position")
                price = slipped_price(Side.BUY, reference, config.slippage_bps)
                wanted = affordable_buy_quantity(cash, price, config.fee_rate, market)
            else:
                if quantity <= 0:
                    raise OrderRejected("no position to sell")
                wanted = quantity
            fill = simulate_market_fill(
                signal.side,
                wanted,
                reference,
                config.fee_rate,
                config.slippage_bps,
                market,
                when,
            )
        except OrderRejected as exc:
            rejected.append(RejectedSignal(when, signal.side, str(exc)))
            return
        if signal.side is Side.BUY:
            cash -= fill.notional + fill.fee
            quantity += fill.quantity
            stop_price, take_profit_price = signal.stop_loss, signal.take_profit
        else:
            cash += fill.notional - fill.fee
            quantity -= fill.quantity
        fills.append(fill)
        if guard is not None and signal.side is Side.SELL:
            guard.after_exit(fills, when)

    for candle in candles:
        trading = trade_from is None or candle.close_time > trade_from
        for signal in pending:
            if guard is not None and guard.paused is not None:
                rejected.append(RejectedSignal(candle.open_time, signal.side, guard_reason(guard)))
                continue
            execute(signal, candle.open, candle.open_time, candle)

        if guard is not None:
            guard.observe(candle)
        if quantity > 0:
            hit = check_protective_exit(candle, stop_price, take_profit_price)
            if hit is not None:
                slippage = config.slippage_bps if hit.reason is ExitReason.STOP_LOSS else Decimal(0)
                try:
                    exit_fill = simulate_market_fill(
                        Side.SELL,
                        quantity,
                        hit.trigger_price,
                        config.fee_rate,
                        slippage,
                        market,
                        candle.open_time,
                    )
                except OrderRejected as exc:
                    rejected.append(RejectedSignal(candle.open_time, Side.SELL, str(exc)))
                else:
                    cash += exit_fill.notional - exit_fill.fee
                    quantity -= exit_fill.quantity
                    fills.append(exit_fill)
                    if guard is not None:
                        guard.after_exit(fills, candle.open_time)
        if quantity <= 0:
            stop_price = take_profit_price = None

        if at_close:
            result = strategy.evaluate(StrategyContext(candle.symbol, candle, quantity), state)
            state = result.state
            if trading:
                for signal in result.signals:
                    emitted.append(EmittedSignal(candle.open_time, signal.side, signal.kind))
                    if guard is not None and guard.paused is not None:
                        rejected.append(
                            RejectedSignal(candle.close_time, signal.side, guard_reason(guard))
                        )
                        continue
                    execute(signal, candle.close, candle.close_time, candle)
            if quantity <= 0:
                stop_price = take_profit_price = None

        mark = cash + quantity * candle.close
        equity.append(EquityPoint(candle.close_time, mark))
        in_market.append(quantity > 0)
        if guard is not None and trading:
            guard.after_mark(mark, candle.close_time)

        if not at_close:
            result = strategy.evaluate(StrategyContext(candle.symbol, candle, quantity), state)
            state = result.state
            pending = result.signals if trading else ()
            emitted.extend(EmittedSignal(candle.open_time, s.side, s.kind) for s in pending)

    return BacktestOutcome(
        fills=fills,
        equity_curve=equity,
        in_market=in_market,
        rejected=rejected,
        final_cash=cash,
        final_quantity=quantity,
        first_price=candles[0].open,
        last_price=candles[-1].close,
        unfilled_signals=len(pending) if not at_close else 0,
        signals=emitted,
        paused=None if guard is None else guard.paused,
        sizing="risk_limits" if guard is not None else "all_in",
    )


def guard_reason(guard: "_RiskGuard") -> str:
    paused = guard.paused
    return f"bot paused: {paused[1]}" if paused is not None else "bot paused"


VOLUME_WINDOW = 20
_SIM_BOT = UUID(int=0)


class _RiskGuard:
    """The bot's risk module inside the backtest (book 1 ch. 5, O4): the same ``assess_signal``
    sizing and the same pauses (daily loss, drawdown, consecutive losses). Once paused, a bot
    takes no new signal until a human resumes it; its exchange stop still works, so protective
    exits keep running here too."""

    def __init__(self, config: BacktestConfig) -> None:
        if config.risk is None:
            raise ValueError("the risk guard needs risk limits")
        self.limits: RiskLimits = config.risk
        self.config = config
        self.paused: tuple[datetime, str] | None = None
        self._day: date | None = None
        self._day_start: Decimal = config.initial_capital
        self._last_mark: Decimal = config.initial_capital
        self._peak: Decimal = config.initial_capital
        self._volumes: deque[Decimal] = deque(maxlen=VOLUME_WINDOW)
        self._last_close: Decimal | None = None
        self._previous_close: Decimal | None = None
        self._last_open_time: datetime | None = None

    def observe(self, candle: Candle) -> None:
        self._volumes.append(candle.volume * candle.close)
        self._previous_close = self._last_close
        self._last_close = candle.close
        self._last_open_time = candle.open_time

    def _close_before(self, candle: Candle) -> Decimal | None:
        """The close that precedes ``candle``: with fills at the signal candle's close the candle
        was already observed, with fills at the next open it was not."""
        return (
            self._previous_close if self._last_open_time == candle.open_time else self._last_close
        )

    def size(
        self,
        signal: Signal,
        cash: Decimal,
        quantity: Decimal,
        reference: Decimal,
        market: MarketInfo,
        candle: Candle,
    ) -> Decimal:
        portfolio = PortfolioState(bot_id=_SIM_BOT, cash=cash, quantity=quantity)
        decision = assess_signal(
            signal,
            portfolio,
            reference,
            market,
            fee_rate=self.config.fee_rate,
            slippage_bps=self.config.slippage_bps,
            limits=self.limits,
            kill_switch_active=False,
            candle_range=candle_range_pct(candle.high, candle.low),
            avg_quote_volume=average_quote_volume(list(self._volumes)),
            close_jump=close_jump_pct(candle.close, self._close_before(candle)),
        )
        if not decision.approved or decision.quantity is None:
            raise OrderRejected(decision.reason or "rejected by risk")
        return decision.quantity

    def after_mark(self, equity: Decimal, at: datetime) -> None:
        day = at.date()
        if self._day is None:
            self._day = day
        elif day != self._day:
            self._day, self._day_start = day, self._last_mark
        self._last_mark = equity
        self._peak = max(self._peak, equity)
        if self.paused is not None:
            return
        if daily_loss_breached(equity, self._day_start, self.limits):
            self.paused = (at, "daily loss limit breached")
        elif drawdown_breached(equity, self._peak, self.limits):
            self.paused = (at, "max drawdown limit breached")

    def after_exit(self, fills: Sequence[Fill], at: datetime) -> None:
        if self.paused is None and consecutive_losses_breached(round_trip_pnls(fills), self.limits):
            self.paused = (at, "max consecutive losses reached")


def risk_report(outcome: BacktestOutcome) -> dict[str, Any]:
    """How the run was sized and what the bot's risk module refused (or why it paused)."""
    refusals: dict[str, int] = {}
    for item in outcome.rejected:
        refusals[item.reason] = refusals.get(item.reason, 0) + 1
    return {
        "sizing": outcome.sizing,
        "paused_at": None if outcome.paused is None else outcome.paused[0].isoformat(),
        "paused_reason": None if outcome.paused is None else outcome.paused[1],
        "refusals": refusals,
    }
