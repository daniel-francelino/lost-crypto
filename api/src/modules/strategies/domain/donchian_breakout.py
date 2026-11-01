"""Trend following: Donchian channel breakout (long-only spot).

Buy when the close breaks above the highest high of the previous ``entry_period`` candles;
sell when the close falls below the lowest low of the previous ``exit_period`` candles. The
channels are built from *previous* candles only, so a candle never compares against itself.
No signals are emitted until ``entry_period`` candles have been seen.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Self

from modules.strategies.domain.base import (
    InvalidStrategyParams,
    ParamSpec,
    Strategy,
    next_bars_held,
    parse_numeric_params,
    percent_below_above,
    validate_percent,
)
from modules.strategies.domain.types import (
    Side,
    Signal,
    SignalKind,
    StrategyContext,
    StrategyResult,
)


@dataclass(frozen=True, slots=True)
class DonchianParams:
    entry_period: int = 20
    exit_period: int = 10
    stop_loss_pct: Decimal | None = None
    take_profit_pct: Decimal | None = None
    max_holding_candles: int | None = None

    def __post_init__(self) -> None:
        validate_percent("stop_loss_pct", self.stop_loss_pct)
        validate_percent("take_profit_pct", self.take_profit_pct)
        if self.entry_period < 2 or self.exit_period < 2:
            raise InvalidStrategyParams("entry_period and exit_period must be >= 2")
        if self.exit_period > self.entry_period:
            raise InvalidStrategyParams("exit_period must not exceed entry_period")
        if self.max_holding_candles is not None and self.max_holding_candles < 1:
            raise InvalidStrategyParams("max_holding_candles must be >= 1")


@dataclass(frozen=True, slots=True)
class DonchianState:
    # (high, low) of the most recent candles, oldest first, current candle excluded.
    history: tuple[tuple[Decimal, Decimal], ...] = ()
    bars_held: int = 0


class DonchianBreakoutStrategy(Strategy[DonchianState]):
    TYPE_KEY = "donchian_breakout"
    NAME = "Donchian Breakout (trend following)"
    DESCRIPTION = (
        "Long-only. Buys a close above the highest high of the last entry_period candles and "
        "sells a close below the lowest low of the last exit_period candles."
    )
    PARAMETERS = (
        ParamSpec("entry_period", "integer", 20, "Candles in the breakout-up channel", 2),
        ParamSpec("exit_period", "integer", 10, "Candles in the exit channel (<= entry_period)", 2),
        ParamSpec(
            "stop_loss_pct", "number", None, "Optional stop-loss, % below the entry price (0-100)"
        ),
        ParamSpec("max_holding_candles", "integer", None, "Optional: exit after N held candles", 1),
        ParamSpec(
            "take_profit_pct",
            "number",
            None,
            "Optional take-profit, % above the entry price (0-100)",
        ),
    )

    def __init__(self, params: DonchianParams) -> None:
        self.params = params

    @classmethod
    def from_params(cls, params: Mapping[str, Any]) -> Self:
        values = parse_numeric_params(
            params,
            integers=frozenset({"entry_period", "exit_period"}),
            numbers=frozenset({"stop_loss_pct", "take_profit_pct"}),
            optional_integers=frozenset({"max_holding_candles"}),
        )
        return cls(DonchianParams(**values))

    def initial_state(self) -> DonchianState:
        return DonchianState()

    def serialize_state(self, state: DonchianState) -> dict[str, Any]:
        return {
            "history": [[str(high), str(low)] for high, low in state.history],
            "bars_held": state.bars_held,
        }

    def deserialize_state(self, raw: dict[str, Any]) -> DonchianState:
        return DonchianState(
            tuple((Decimal(h), Decimal(low)) for h, low in raw["history"]),
            int(raw.get("bars_held", 0)),
        )

    def evaluate(self, ctx: StrategyContext, state: DonchianState) -> StrategyResult[DonchianState]:
        candle = ctx.candle
        p = self.params
        history = state.history
        bars_held = next_bars_held(ctx.position_quantity, state.bars_held)
        signals: tuple[Signal, ...] = ()

        if len(history) >= p.entry_period:
            highest = max(high for high, _ in history[-p.entry_period :])
            lowest = min(low for _, low in history[-p.exit_period :])
            if candle.close > highest and ctx.position_quantity <= 0:
                stop, target = percent_below_above(candle.close, p.stop_loss_pct, p.take_profit_pct)
                signals = (
                    Signal(
                        Side.BUY,
                        ctx.symbol,
                        SignalKind.ENTRY,
                        f"close broke above the {p.entry_period}-candle high ({highest})",
                        stop_loss=stop,
                        take_profit=target,
                    ),
                )
            elif candle.close < lowest and ctx.position_quantity > 0:
                signals = (
                    Signal(
                        Side.SELL,
                        ctx.symbol,
                        SignalKind.EXIT,
                        f"close broke below the {p.exit_period}-candle low ({lowest})",
                    ),
                )

        if (
            not signals
            and ctx.position_quantity > 0
            and p.max_holding_candles is not None
            and bars_held >= p.max_holding_candles
        ):
            signals = (
                Signal(
                    Side.SELL,
                    ctx.symbol,
                    SignalKind.EXIT,
                    f"holding limit of {p.max_holding_candles} candles reached",
                ),
            )

        keep = max(p.entry_period, p.exit_period)
        new_history = (*history, (candle.high, candle.low))[-keep:]
        return StrategyResult(signals, DonchianState(new_history, bars_held))
