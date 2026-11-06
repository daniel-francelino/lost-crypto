"""The symbol registry as a rule for the rest of the system.

Only pairs the operator registered (``trends`` module) may be used by bots, backtests and
candle imports. Services depend on this small contract, not on the registry module.
"""

from typing import Protocol

from core.errors import DomainError


class SymbolNotRegistered(DomainError):
    pass


class SymbolGuard(Protocol):
    async def require(self, exchange: str, symbol: str) -> None:
        """Raise ``SymbolNotRegistered`` unless the pair is registered and active."""
        ...


class AllowAnySymbol:
    """No registry in force (tests, or ``SYMBOL_REGISTRY_ENFORCED=false``)."""

    async def require(self, exchange: str, symbol: str) -> None:
        return None
