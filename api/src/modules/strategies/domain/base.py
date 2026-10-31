"""THE strategy contract.

A strategy is one class in one file that describes itself (key, name, parameters) and implements
this interface. It is a pure algorithm: no I/O, no clock, no persistence; its state is explicit,
returned from ``evaluate`` and (de)serialised so a bot can resume after a restart. The engine,
risk, bots and the API only ever see ``Strategy``.

Adding a strategy = a new file in ``strategies/domain/`` with a subclass + one line in
``strategies/catalog.py``. Python refuses to instantiate a subclass that leaves a method below
unimplemented, the registry refuses one that forgets its metadata, and the contract tests in
``tests/unit/test_strategy_contract.py`` check the behaviour of every registered strategy.
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, ClassVar, Self

from core.errors import DomainError
from modules.strategies.domain.types import StrategyContext, StrategyResult


class InvalidStrategyParams(DomainError):
    pass


@dataclass(frozen=True, slots=True)
class ParamSpec:
    """Documents one configurable parameter (shown by ``GET /strategies``)."""

    name: str
    type: str  # "integer" | "number"
    default: Any
    description: str
    minimum: int | None = None


class Strategy[StateT](ABC):
    #: Stable identifier stored in bots and backtests (snake_case). Required.
    TYPE_KEY: ClassVar[str]
    #: Human-readable name. Required.
    NAME: ClassVar[str]
    #: What it does, in a sentence or two. Required.
    DESCRIPTION: ClassVar[str]
    #: Every accepted parameter with its default. Required (may be empty).
    PARAMETERS: ClassVar[tuple[ParamSpec, ...]]

    @classmethod
    @abstractmethod
    def from_params(cls, params: Mapping[str, Any]) -> Self:
        """Build an instance from raw (JSON) parameters, applying defaults.

        Must raise ``InvalidStrategyParams`` for unknown keys, wrong types or invalid values.
        """

    @abstractmethod
    def initial_state(self) -> StateT:
        """State before any candle was seen."""

    @abstractmethod
    def evaluate(self, ctx: StrategyContext, state: StateT) -> StrategyResult[StateT]:
        """Look at one closed candle and return the signals plus the new state.

        Pure and deterministic: the same ``(ctx, state)`` always gives the same result, and
        ``state`` is never mutated. Emit no signals while warming up.
        """

    @abstractmethod
    def serialize_state(self, state: StateT) -> dict[str, Any]:
        """JSON-compatible form of the state (Decimals as strings)."""

    @abstractmethod
    def deserialize_state(self, raw: dict[str, Any]) -> StateT:
        """Inverse of ``serialize_state``."""


# --- helpers shared by strategy implementations -------------------------------------------


def parse_numeric_params(
    raw: Mapping[str, Any], *, integers: frozenset[str], numbers: frozenset[str]
) -> dict[str, Any]:
    """Validate the shape of raw params: known keys only, integers as ``int``, numbers as
    ``Decimal`` (or None). Range checks stay in the strategy's own params class."""
    unknown = set(raw) - integers - numbers
    if unknown:
        raise InvalidStrategyParams(f"unknown parameters: {sorted(unknown)}")
    values: dict[str, Any] = {}
    for key, value in raw.items():
        if isinstance(value, bool):
            raise InvalidStrategyParams(f"{key} must be a number")
        if key in integers:
            if not isinstance(value, int):
                raise InvalidStrategyParams(f"{key} must be an integer")
            values[key] = value
        elif value is None:
            values[key] = None
        else:
            try:
                values[key] = Decimal(str(value))
            except ArithmeticError:
                raise InvalidStrategyParams(f"{key} must be a number") from None
    return values


def percent_below_above(
    price: Decimal, stop_loss_pct: Decimal | None, take_profit_pct: Decimal | None
) -> tuple[Decimal | None, Decimal | None]:
    """(stop-loss, take-profit) price levels as percentages below / above ``price``."""
    stop = None if stop_loss_pct is None else price * (1 - stop_loss_pct / 100)
    target = None if take_profit_pct is None else price * (1 + take_profit_pct / 100)
    return stop, target


def validate_percent(name: str, value: Decimal | None) -> None:
    if value is not None and not (0 < value < 100):
        raise InvalidStrategyParams(f"{name} must be between 0 and 100 (exclusive)")
