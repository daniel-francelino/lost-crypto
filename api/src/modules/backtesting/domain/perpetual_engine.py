"""Deterministic isolated-margin simulator for linear USDT perpetuals.

This engine intentionally accepts auxiliary series as required inputs. Callers must validate
their coverage and provenance before invoking it; missing mark/funding observations are never
filled from signal candles or the current funding rate.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from itertools import pairwise
from typing import Any
from uuid import UUID

from modules.backtesting.domain.models import (
    BacktestConfig,
    EmittedSignal,
    EquityPoint,
    FillTiming,
    InvalidBacktestConfig,
    RejectedSignal,
)
from modules.exchanges.domain.models import PositionSide, TradingProduct
from modules.execution.domain.fills import effective_slippage_bps, simulate_market_fill
from modules.execution.domain.normalizer import OrderRejected
from modules.execution.domain.orders import Fill
from modules.market_data.domain.models import Candle, FundingRate, MarketInfo
from modules.portfolio.domain.perpetuals import InvalidPerpetualPosition, PerpetualLedger
from modules.strategies.domain.base import Strategy
from modules.strategies.domain.types import Side, Signal, SignalKind, StrategyContext


@dataclass(frozen=True, slots=True)
class PerpetualBacktestOutcome:
    fills: list[Fill]
    equity_curve: list[EquityPoint]
    in_market: list[bool]
    rejected: list[RejectedSignal]
    final_cash: Decimal
    final_quantity: Decimal
    first_price: Decimal
    last_price: Decimal
    unfilled_signals: int
    signals: list[EmittedSignal]
    funding_paid: Decimal
    funding_received: Decimal
    liquidation_count: int
    liquidation_times: list[str]
    max_notional: Decimal


def run_perpetual_backtest(
    config: BacktestConfig,
    candles: Sequence[Candle],
    mark_candles: Sequence[Candle],
    funding_rates: Sequence[FundingRate],
    market: MarketInfo,
    strategy: Strategy[Any],
    *,
    maintenance_margin_rate: Decimal,
    liquidation_fee_rate: Decimal,
    trade_from: datetime | None = None,
) -> PerpetualBacktestOutcome:
    """Run with signal candles, separate mark candles, and event-time historical funding."""
    if config.product is not TradingProduct.LINEAR_PERPETUAL:
        raise InvalidBacktestConfig("perpetual engine requires linear_perpetual product")
    if config.risk is not None:
        raise InvalidBacktestConfig(
            "perpetual backtests with risk limits require the futures risk sizing model"
        )
    if not candles or len(candles) != len(mark_candles):
        raise InvalidBacktestConfig("signal and mark candles must have complete matching coverage")
    if any(
        signal.symbol != mark.symbol
        or signal.timeframe != mark.timeframe
        or signal.open_time != mark.open_time
        for signal, mark in zip(candles, mark_candles, strict=True)
    ):
        raise InvalidBacktestConfig("mark candles must align exactly with signal candles")
    if not 0 <= maintenance_margin_rate < 1 or not 0 <= liquidation_fee_rate < 1:
        raise InvalidBacktestConfig("maintenance and liquidation fee rates must be in [0, 1)")
    if any(rate.mark_price is None for rate in funding_rates):
        raise InvalidBacktestConfig("funding observations need their event-time mark price")

    ordered_funding = sorted(funding_rates, key=lambda item: item.funding_time)
    if any(
        item.funding_time <= mark_candles[0].open_time
        or item.funding_time > mark_candles[-1].close_time
        for item in ordered_funding
    ):
        raise InvalidBacktestConfig("funding observations fall outside the simulated range")
    if any(a.funding_time == b.funding_time for a, b in pairwise(ordered_funding)):
        raise InvalidBacktestConfig("duplicate funding timestamps are not allowed")
    funding_index = 0
    ledger = PerpetualLedger.new(UUID(int=0), config.initial_capital)
    fills: list[Fill] = []
    equity: list[EquityPoint] = []
    in_market: list[bool] = []
    rejected: list[RejectedSignal] = []
    emitted: list[EmittedSignal] = []
    liquidation_times: list[str] = []
    max_notional = Decimal(0)
    state = strategy.initial_state()
    pending: tuple[Signal, ...] = ()
    stop_price: Decimal | None = None
    take_profit_price: Decimal | None = None

    def bps(candle: Candle, notional: Decimal) -> Decimal:
        return effective_slippage_bps(
            config.slippage_model,
            config.slippage_bps,
            config.slippage_k_range,
            config.slippage_k_size,
            candle,
            notional,
        )

    def fill(signal: Signal, reference: Decimal, at: datetime, candle: Candle) -> None:
        nonlocal stop_price, take_profit_price, max_notional
        position = ledger.position
        is_entry = signal.kind is SignalKind.ENTRY
        side = PositionSide.LONG if signal.side is Side.BUY else PositionSide.SHORT
        if is_entry:
            if position is not None:
                rejected.append(RejectedSignal(at, signal.side, "already in a position"))
                return
            if side is PositionSide.SHORT and not config.allow_short:
                rejected.append(RejectedSignal(at, signal.side, "short entries are disabled"))
                return
            try:
                price_hint = reference * (
                    1 + config.slippage_bps / Decimal(10_000)
                    if signal.side is Side.BUY
                    else 1 - config.slippage_bps / Decimal(10_000)
                )
                budget = ledger.available_balance
                wanted = (
                    budget
                    * config.leverage
                    / (price_hint * (1 + config.fee_rate * config.leverage))
                )
                executed = simulate_market_fill(
                    signal.side, wanted, reference, config.fee_rate, bps(candle, budget), market, at
                )
                ledger.open_position(
                    side, executed.quantity, executed.price, config.leverage, executed.fee
                )
            except (InvalidPerpetualPosition, OrderRejected, ValueError) as exc:
                rejected.append(RejectedSignal(at, signal.side, str(exc)))
                return
            fills.append(executed)
            max_notional = max(max_notional, executed.notional)
            stop_price, take_profit_price = signal.stop_loss, signal.take_profit
            if side is PositionSide.SHORT and (
                (stop_price is not None and stop_price <= executed.price)
                or (take_profit_price is not None and take_profit_price >= executed.price)
            ):
                raise InvalidBacktestConfig("short protective levels are not mirrored correctly")
            if side is PositionSide.LONG and (
                (stop_price is not None and stop_price >= executed.price)
                or (take_profit_price is not None and take_profit_price <= executed.price)
            ):
                raise InvalidBacktestConfig("long protective levels are not on the correct side")
            return

        if position is None:
            rejected.append(RejectedSignal(at, signal.side, "no position to exit"))
            return
        if (position.side is PositionSide.LONG and signal.side is not Side.SELL) or (
            position.side is PositionSide.SHORT and signal.side is not Side.BUY
        ):
            rejected.append(
                RejectedSignal(at, signal.side, "exit direction would increase exposure")
            )
            return
        executed = simulate_market_fill(
            signal.side,
            position.quantity,
            reference,
            config.fee_rate,
            bps(candle, position.quantity * reference),
            market,
            at,
        )
        ledger.close_position(executed.quantity, executed.price, executed.fee)
        fills.append(executed)
        stop_price = take_profit_price = None

    for candle, mark in zip(candles, mark_candles, strict=True):
        trading = trade_from is None or candle.close_time > trade_from
        for signal in pending:
            fill(signal, candle.open, candle.open_time, candle)

        while (
            funding_index < len(ordered_funding)
            and ordered_funding[funding_index].funding_time <= mark.close_time
        ):
            event = ordered_funding[funding_index]
            if event.funding_time > mark.open_time and ledger.position is not None:
                assert event.mark_price is not None
                ledger.apply_funding(event.mark_price, event.rate)
                if ledger.position is None:
                    liquidation_times.append(event.funding_time.isoformat())
            funding_index += 1

        position = ledger.position
        if position is not None:
            liquidation_price = position.estimated_liquidation_price(maintenance_margin_rate)
            liq_hit = (
                mark.low <= liquidation_price
                if position.side is PositionSide.LONG
                else mark.high >= liquidation_price
            )
            if liq_hit:
                reference = (
                    max(mark.open, liquidation_price)
                    if position.side is PositionSide.LONG
                    else min(mark.open, liquidation_price)
                )
                fee = position.quantity * reference * liquidation_fee_rate
                ledger.liquidate(reference, fee)
                fills.append(
                    Fill(
                        time=candle.open_time,
                        side=Side.SELL if position.side is PositionSide.LONG else Side.BUY,
                        quantity=position.quantity,
                        price=reference,
                        fee=fee,
                    )
                )
                liquidation_times.append(candle.open_time.isoformat())
                stop_price = take_profit_price = None
            else:
                stop_hit = stop_price is not None and (
                    mark.low <= stop_price
                    if position.side is PositionSide.LONG
                    else mark.high >= stop_price
                )
                target_hit = take_profit_price is not None and (
                    mark.high >= take_profit_price
                    if position.side is PositionSide.LONG
                    else mark.low <= take_profit_price
                )
                if stop_hit or target_hit:
                    trigger = stop_price if stop_hit else take_profit_price
                    assert trigger is not None
                    crossed_open = (
                        mark.open <= trigger
                        if position.side is PositionSide.LONG and stop_hit
                        else mark.open >= trigger
                        if position.side is PositionSide.SHORT and stop_hit
                        else mark.open >= trigger
                        if position.side is PositionSide.LONG
                        else mark.open <= trigger
                    )
                    reference = mark.open if crossed_open else trigger
                    exit_side = Side.SELL if position.side is PositionSide.LONG else Side.BUY
                    executed = simulate_market_fill(
                        exit_side,
                        position.quantity,
                        reference,
                        config.fee_rate,
                        bps(candle, position.quantity * reference) if stop_hit else Decimal(0),
                        market,
                        candle.open_time,
                    )
                    ledger.close_position(executed.quantity, executed.price, executed.fee)
                    fills.append(executed)
                    stop_price = take_profit_price = None

        if config.fill_timing is FillTiming.SIGNAL_CLOSE and trading:
            result = strategy.evaluate(
                StrategyContext(
                    candle.symbol,
                    candle,
                    ledger.position.quantity if ledger.position else Decimal(0),
                    ledger.position.side if ledger.position else None,
                    config.allow_short,
                ),
                state,
            )
            state = result.state
            for signal in result.signals:
                emitted.append(EmittedSignal(candle.open_time, signal.side, signal.kind))
                fill(signal, candle.close, candle.close_time, candle)

        ledger.mark(mark.close, mark.close_time, maintenance_margin_rate)
        equity.append(EquityPoint(mark.close_time, ledger.equity(mark.close)))
        in_market.append(ledger.position is not None)

        if config.fill_timing is not FillTiming.SIGNAL_CLOSE:
            result = strategy.evaluate(
                StrategyContext(
                    candle.symbol,
                    candle,
                    ledger.position.quantity if ledger.position else Decimal(0),
                    ledger.position.side if ledger.position else None,
                    config.allow_short,
                ),
                state,
            )
            state = result.state
            pending = result.signals if trading else ()
            emitted.extend(
                EmittedSignal(candle.open_time, item.side, item.kind) for item in pending
            )
        else:
            pending = ()

    if funding_index < len(ordered_funding):
        raise InvalidBacktestConfig("funding data extends beyond the backtest candle range")
    final_position = ledger.position
    return PerpetualBacktestOutcome(
        fills=fills,
        equity_curve=equity,
        in_market=in_market,
        rejected=rejected,
        final_cash=ledger.wallet_balance,
        final_quantity=final_position.quantity if final_position else Decimal(0),
        first_price=mark_candles[0].open,
        last_price=mark_candles[-1].close,
        unfilled_signals=len(pending),
        signals=emitted,
        funding_paid=ledger.funding_paid,
        funding_received=ledger.funding_received,
        liquidation_count=len(liquidation_times),
        liquidation_times=liquidation_times,
        max_notional=max_notional,
    )
