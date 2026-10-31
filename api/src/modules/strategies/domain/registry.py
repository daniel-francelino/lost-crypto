import re
from collections.abc import Mapping, Sequence
from typing import Any

from core.errors import DomainError, LostCryptoError
from modules.strategies.domain.base import ParamSpec, Strategy


class UnknownStrategy(DomainError):
    pass


class StrategyConfigurationError(LostCryptoError):
    """A strategy class is misdeclared or the catalog selection is wrong."""


_KEY = re.compile(r"^[a-z][a-z0-9_]*$")


class StrategyRegistry:
    """Registry + factory of strategy classes, keyed by their ``TYPE_KEY``."""

    def __init__(self, strategies: Sequence[type[Strategy[Any]]] = ()) -> None:
        self._classes: dict[str, type[Strategy[Any]]] = {}
        for strategy_cls in strategies:
            self.register(strategy_cls)

    def register(self, strategy_cls: type[Strategy[Any]]) -> None:
        name = strategy_cls.__name__
        key = getattr(strategy_cls, "TYPE_KEY", None)
        if not isinstance(key, str) or not _KEY.match(key):
            raise StrategyConfigurationError(f"{name}.TYPE_KEY must be a snake_case string")
        for attribute in ("NAME", "DESCRIPTION"):
            value = getattr(strategy_cls, attribute, None)
            if not isinstance(value, str) or not value.strip():
                raise StrategyConfigurationError(f"{name}.{attribute} must be a non-empty string")
        parameters = getattr(strategy_cls, "PARAMETERS", None)
        if not isinstance(parameters, tuple) or not all(
            isinstance(p, ParamSpec) for p in parameters
        ):
            raise StrategyConfigurationError(f"{name}.PARAMETERS must be a tuple of ParamSpec")
        if key in self._classes:
            raise StrategyConfigurationError(f"duplicate strategy key {key!r}")
        self._classes[key] = strategy_cls

    def list(self) -> list[type[Strategy[Any]]]:
        return list(self._classes.values())

    def get(self, type_key: str) -> type[Strategy[Any]]:
        try:
            return self._classes[type_key]
        except KeyError:
            known = ", ".join(sorted(self._classes)) or "none"
            raise UnknownStrategy(f"unknown strategy: {type_key!r} (available: {known})") from None

    def create(self, type_key: str, params: Mapping[str, Any]) -> Strategy[Any]:
        """Build a fresh, validated strategy instance."""
        return self.get(type_key).from_params(params)
