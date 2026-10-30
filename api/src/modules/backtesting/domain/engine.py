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

from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from modules.backtesting.domain.models import (
    BacktestConfig,
    BacktestOutcome,
    EquityPoint,
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
from modules.risk_management.domain.stops import ExitReason, check_protective_exit
from modules.strategies.domain.types import Side, Signal, Strategy, StrategyContext


def run_backtest(
    config: BacktestConfig,
    candles: Sequence[Candle],
    market: MarketInfo,
    strategy: Strategy[Any],
) -> BacktestOutcome:
    if not candles:
        raise InvalidBacktestConfig("no candles to backtest")

    cash = config.initial_capital
    quantity = Decimal(0)
    fills: list[Fill] = []
    equity: list[EquityPoint] = []
    rejected: list[RejectedSignal] = []
    state = strategy.initial_state()
    pending: tuple[Signal, ...] = ()
    stop_price: Decimal | None = None
    take_profit_price: Decimal | None = None

    for candle in candles:
        for signal in pending:
            try:
                if signal.side is Side.BUY:
                    if quantity > 0:
                        raise OrderRejected("already in position")
                    price = slipped_price(Side.BUY, candle.open, config.slippage_bps)
                    wanted = affordable_buy_quantity(cash, price, config.fee_rate, market)
                else:
                    if quantity <= 0:
                        raise OrderRejected("no position to sell")
                    wanted = quantity
                fill = simulate_market_fill(
                    signal.side,
                    wanted,
                    candle.open,
                    config.fee_rate,
                    config.slippage_bps,
                    market,
                    candle.open_time,
                )
            except OrderRejected as exc:
                rejected.append(RejectedSignal(candle.open_time, signal.side, str(exc)))
                continue
            if signal.side is Side.BUY:
                cash -= fill.notional + fill.fee
                quantity += fill.quantity
                stop_price, take_profit_price = signal.stop_loss, signal.take_profit
            else:
                cash += fill.notional - fill.fee
                quantity -= fill.quantity
            fills.append(fill)

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
        if quantity <= 0:
            stop_price = take_profit_price = None

        equity.append(EquityPoint(candle.close_time, cash + quantity * candle.close))

        result = strategy.evaluate(StrategyContext(candle.symbol, candle, quantity), state)
        state = result.state
        pending = result.signals

    return BacktestOutcome(
        fills=fills,
        equity_curve=equity,
        rejected=rejected,
        final_cash=cash,
        final_quantity=quantity,
        first_price=candles[0].open,
        last_price=candles[-1].close,
        unfilled_signals=len(pending),
    )
