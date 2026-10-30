"""Event-loop backtester.

Timeline per candle ``i`` (no look-ahead):
  1. signals produced after candle ``i-1`` closed are filled at the *open* of candle ``i``
     (plus slippage and fees);
  2. equity is marked at the close of candle ``i``;
  3. the strategy sees candle ``i`` (closed) and may emit signals for candle ``i+1``.
Signals emitted on the last candle can never be filled and are only counted.

Sizing here is deliberately trivial (buy with all cash, sell the whole position); in the live
pipeline that responsibility belongs to the risk module.
"""

from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from modules.backtesting.domain.models import (
    BacktestConfig,
    BacktestOutcome,
    EquityPoint,
    Fill,
    InvalidBacktestConfig,
    RejectedSignal,
)
from modules.execution.domain.normalizer import OrderRejected, normalize_quantity
from modules.market_data.domain.models import Candle, MarketInfo
from modules.strategies.domain.types import Side, Signal, Strategy, StrategyContext

_BPS = Decimal(10_000)


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
    slippage = config.slippage_bps / _BPS

    for candle in candles:
        for signal in pending:
            try:
                if signal.side is Side.BUY:
                    price = candle.open * (1 + slippage)
                    if quantity > 0:
                        raise OrderRejected("already in position")
                    affordable = cash / (price * (1 + config.fee_rate))
                    qty = normalize_quantity(affordable, price, market)
                    fee = qty * price * config.fee_rate
                    cash -= qty * price + fee
                    quantity += qty
                else:
                    price = candle.open * (1 - slippage)
                    if quantity <= 0:
                        raise OrderRejected("no position to sell")
                    qty = normalize_quantity(quantity, price, market)
                    fee = qty * price * config.fee_rate
                    cash += qty * price - fee
                    quantity -= qty
            except OrderRejected as exc:
                rejected.append(RejectedSignal(candle.open_time, signal.side, str(exc)))
                continue
            fills.append(Fill(candle.open_time, signal.side, qty, price, fee))

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
