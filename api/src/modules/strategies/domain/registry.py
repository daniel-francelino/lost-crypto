from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from core.errors import DomainError
from modules.strategies.domain import ema_crossover
from modules.strategies.domain.types import Strategy


class UnknownStrategy(DomainError):
    pass


@dataclass(frozen=True, slots=True)
class ParamSpec:
    name: str
    type: str
    default: Any
    description: str
    minimum: int | None = None


@dataclass(frozen=True, slots=True)
class StrategyDefinition:
    type_key: str
    name: str
    description: str
    parameters: tuple[ParamSpec, ...]
    factory: Callable[[Mapping[str, Any]], Strategy[Any]]


class StrategyRegistry:
    def __init__(self, definitions: list[StrategyDefinition]) -> None:
        self._definitions = {d.type_key: d for d in definitions}

    def list(self) -> list[StrategyDefinition]:
        return list(self._definitions.values())

    def get(self, type_key: str) -> StrategyDefinition:
        try:
            return self._definitions[type_key]
        except KeyError:
            raise UnknownStrategy(f"unknown strategy: {type_key!r}") from None

    def create(self, type_key: str, params: Mapping[str, Any]) -> Strategy[Any]:
        """Build a fresh strategy instance (validates ``params``)."""
        return self.get(type_key).factory(params)


def default_registry() -> StrategyRegistry:
    defaults = ema_crossover.EmaCrossoverParams()
    return StrategyRegistry(
        [
            StrategyDefinition(
                type_key=ema_crossover.TYPE_KEY,
                name="EMA Crossover (trend following)",
                description=(
                    "Long-only. Buys when the fast EMA crosses above the slow EMA and "
                    "sells when it crosses back below."
                ),
                parameters=(
                    ParamSpec("fast_period", "integer", defaults.fast_period, "Fast EMA", 2),
                    ParamSpec(
                        "slow_period",
                        "integer",
                        defaults.slow_period,
                        "Slow EMA (must be greater than fast_period)",
                        3,
                    ),
                ),
                factory=lambda raw: ema_crossover.EmaCrossoverStrategy(
                    ema_crossover.EmaCrossoverParams.from_mapping(raw)
                ),
            )
        ]
    )
