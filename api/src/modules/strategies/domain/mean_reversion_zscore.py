"""Mean reversion: z-score of the close against its recent window (long-only spot).

Buy when the close is ``entry_z`` standard deviations or more below the mean of the last
``lookback`` closes; sell when it is back to ``exit_z`` (default: the mean), after an optional
number of candles in the position, or at an optional stop. The window includes the current candle
and nothing else, so no future data is used. Nothing is emitted until the window is full or when
the window has no spread. The defaults are starting values of ours, not the book's.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, localcontext
from typing import Any, Self

from modules.strategies.domain.base import (
    InvalidStrategyParams,
    ParamSpec,
    Strategy,
    StrategyStyle,
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

_PRECISION = 40
MIN_LOOKBACK = 5


@dataclass(frozen=True, slots=True)
class MeanReversionParams:
    lookback: int = 20
    entry_z: Decimal = Decimal(2)
    exit_z: Decimal = Decimal(0)
    max_holding_candles: int | None = None
    stop_loss_pct: Decimal | None = None

    def __post_init__(self) -> None:
        validate_percent("stop_loss_pct", self.stop_loss_pct)
        if self.lookback < MIN_LOOKBACK:
            raise InvalidStrategyParams(f"lookback must be >= {MIN_LOOKBACK}")
        if self.entry_z <= 0:
            raise InvalidStrategyParams("entry_z must be greater than 0")
        if self.exit_z <= -self.entry_z:
            raise InvalidStrategyParams("exit_z must be greater than -entry_z")
        if self.max_holding_candles is not None and self.max_holding_candles < 1:
            raise InvalidStrategyParams("max_holding_candles must be >= 1")


@dataclass(frozen=True, slots=True)
class MeanReversionState:
    closes: tuple[Decimal, ...] = ()  # the last `lookback` closes, current candle included
    bars_held: int = 0


def z_score(window: Sequence[Decimal]) -> Decimal | None:
    """z of the last value against the whole window (population deviation); None if no spread."""
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        mean = sum(window, Decimal(0)) / len(window)
        variance = sum(((value - mean) ** 2 for value in window), Decimal(0)) / len(window)
        if variance == 0:
            return None
        return (window[-1] - mean) / variance.sqrt()


class MeanReversionZScoreStrategy(Strategy[MeanReversionState]):
    TYPE_KEY = "mean_reversion_zscore"
    NAME = "Z-score mean reversion"
    STYLE = StrategyStyle.MEAN_REVERSION
    DESCRIPTION = (
        "Long-only. Buys when the close is entry_z standard deviations below the mean of the "
        "last lookback closes and sells when it is back to exit_z (the mean by default)."
    )
    PARAMETERS = (
        ParamSpec("lookback", "integer", 20, "Candles in the window, current one included", 5),
        ParamSpec(
            "entry_z", "number", 2, "Buy at this many deviations below (> 0)", Decimal("0.1")
        ),
        ParamSpec("exit_z", "number", 0, "Sell when the z-score is back to this (> -entry_z)"),
        ParamSpec("max_holding_candles", "integer", None, "Optional: exit after N held candles", 1),
        ParamSpec(
            "stop_loss_pct", "number", None, "Optional stop-loss, % below the entry price (0-100)"
        ),
    )

    def __init__(self, params: MeanReversionParams) -> None:
        self.params = params

    @classmethod
    def from_params(cls, params: Mapping[str, Any]) -> Self:
        values = parse_numeric_params(
            params,
            integers=frozenset({"lookback"}),
            numbers=frozenset({"entry_z", "exit_z", "stop_loss_pct"}),
            optional_integers=frozenset({"max_holding_candles"}),
        )
        for name in ("entry_z", "exit_z"):
            if name in values and values[name] is None:
                raise InvalidStrategyParams(f"{name} must be a number")
        return cls(MeanReversionParams(**values))

    def initial_state(self) -> MeanReversionState:
        return MeanReversionState()

    def serialize_state(self, state: MeanReversionState) -> dict[str, Any]:
        return {"closes": [str(c) for c in state.closes], "bars_held": state.bars_held}

    def deserialize_state(self, raw: dict[str, Any]) -> MeanReversionState:
        return MeanReversionState(
            closes=tuple(Decimal(c) for c in raw["closes"]),
            bars_held=int(raw.get("bars_held", 0)),
        )

    def evaluate(
        self, ctx: StrategyContext, state: MeanReversionState
    ) -> StrategyResult[MeanReversionState]:
        p = self.params
        close = ctx.candle.close
        window = (*state.closes, close)[-p.lookback :]
        bars_held = next_bars_held(ctx.position_quantity, state.bars_held)
        new_state = MeanReversionState(window, bars_held)
        if len(window) < p.lookback:
            return StrategyResult((), new_state)

        z = z_score(window)
        signals: tuple[Signal, ...] = ()
        if z is not None and ctx.position_quantity <= 0 and z <= -p.entry_z:
            stop, _ = percent_below_above(close, p.stop_loss_pct, None)
            signals = (
                Signal(
                    Side.BUY,
                    ctx.symbol,
                    SignalKind.ENTRY,
                    f"z-score {z:.2f} <= -{p.entry_z} over {p.lookback} candles",
                    stop_loss=stop,
                ),
            )
        elif z is not None and ctx.position_quantity > 0 and z >= p.exit_z:
            signals = (
                Signal(
                    Side.SELL,
                    ctx.symbol,
                    SignalKind.EXIT,
                    f"z-score {z:.2f} is back to {p.exit_z}",
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
        return StrategyResult(signals, new_state)
