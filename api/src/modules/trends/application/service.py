"""API side of the trend detector: the symbol registry and reading what the detector stored."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from core.clock import Clock
from core.errors import ConflictError, DomainError, NotFoundError
from core.ids import IdGenerator
from modules.exchanges.application.registry import ExchangeRegistry
from modules.exchanges.errors import UnknownSymbolError
from modules.market_data.domain.trend import TrendFrame
from modules.trends.application.detector import TrendStoreFactory
from modules.trends.domain.models import TrendRecord, WatchedSymbol, normalize_symbol


class InvalidTrendSymbol(DomainError):
    pass


@dataclass(frozen=True, slots=True)
class SymbolTrends:
    """A registered symbol with the newest reading of each of its timeframes."""

    symbol: WatchedSymbol
    readings: list[TrendRecord]


class TrendService:
    def __init__(
        self,
        stores: TrendStoreFactory,
        exchanges: ExchangeRegistry,
        clock: Clock,
        ids: IdGenerator,
        in_use: Callable[[str, str], Awaitable[bool]] | None = None,
    ) -> None:
        self._in_use = in_use
        self._stores = stores
        self._exchanges = exchanges
        self._clock = clock
        self._ids = ids

    async def add_symbol(self, exchange: str, symbol: str) -> WatchedSymbol:
        """Register a pair for the detector (``BTCUSDT`` and ``BTC/USDT:USDT`` both work).

        The exchange must list it. A pair that was switched off is switched back on."""
        self._exchanges.profile(exchange)  # unknown or disabled exchange: a clear error
        unified = normalize_symbol(exchange, symbol)
        try:
            await self._exchanges.market_data(exchange).fetch_market_info(unified)
        except UnknownSymbolError:
            raise InvalidTrendSymbol(f"{exchange} does not list {unified!r}") from None
        async with self._stores() as store:
            existing = await store.trends.find_symbol(exchange, unified)
            if existing is not None:
                if existing.active:
                    raise ConflictError(f"{unified} is already followed on {exchange}")
                await store.trends.set_active(existing.id, True)
                await store.commit()
                return WatchedSymbol(
                    existing.id, existing.exchange, existing.symbol, True, existing.created_at
                )
            created = WatchedSymbol(self._ids.new_id(), exchange, unified, True, self._clock.now())
            await store.trends.add_symbol(created)
            await store.commit()
            return created

    async def list_symbols(self) -> list[WatchedSymbol]:
        async with self._stores() as store:
            return await store.trends.list_symbols(active_only=False)

    async def set_active(self, symbol_id: UUID, active: bool) -> WatchedSymbol:
        if not active and self._in_use is not None:
            current = await self._get(symbol_id)
            if await self._in_use(current.exchange, current.symbol):
                raise ConflictError(
                    f"{current.symbol} is used by a bot that is not stopped: stop it first"
                )
        async with self._stores() as store:
            if not await store.trends.set_active(symbol_id, active):
                raise NotFoundError(f"trend symbol {symbol_id} does not exist")
            await store.commit()
            found = await store.trends.get_symbol(symbol_id)
        assert found is not None
        return found

    async def _get(self, symbol_id: UUID) -> WatchedSymbol:
        async with self._stores() as store:
            found = await store.trends.get_symbol(symbol_id)
        if found is None:
            raise NotFoundError(f"trend symbol {symbol_id} does not exist")
        return found

    async def latest(
        self, exchange: str | None = None, symbol: str | None = None
    ) -> list[SymbolTrends]:
        """The newest reading of every timeframe, for the active symbols (or the one asked)."""
        async with self._stores() as store:
            symbols = [
                s
                for s in await store.trends.list_symbols(active_only=symbol is None)
                if (exchange is None or s.exchange == exchange)
                and (symbol is None or s.symbol == normalize_symbol(s.exchange, symbol))
            ]
            return [
                SymbolTrends(s, await store.trends.latest(s.exchange, s.symbol)) for s in symbols
            ]

    async def history(
        self,
        exchange: str,
        symbol: str,
        frame: TrendFrame,
        limit: int,
        before: datetime | None = None,
    ) -> list[TrendRecord]:
        async with self._stores() as store:
            return await store.trends.history(
                exchange, normalize_symbol(exchange, symbol), frame, limit, before
            )
