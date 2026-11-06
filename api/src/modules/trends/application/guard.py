from core.symbols import SymbolNotRegistered
from modules.trends.application.detector import TrendStoreFactory


class RegistrySymbolGuard:
    """Lets a pair through only when it is in the symbol registry and active."""

    def __init__(self, stores: TrendStoreFactory) -> None:
        self._stores = stores

    async def require(self, exchange: str, symbol: str) -> None:
        async with self._stores() as store:
            found = await store.trends.find_symbol(exchange, symbol)
        if found is None or not found.active:
            raise SymbolNotRegistered(
                f"{symbol} is not in the symbol registry for {exchange}: "
                "register it on the Moedas screen first"
            )

    async def active_pairs(self) -> set[tuple[str, str]]:
        """(exchange, symbol) of every active registered pair."""
        async with self._stores() as store:
            return {
                (s.exchange, s.symbol) for s in await store.trends.list_symbols(active_only=True)
            }
