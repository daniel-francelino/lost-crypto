from collections.abc import Callable

from modules.exchanges.domain.models import ExchangeProfile
from modules.exchanges.errors import UnknownExchangeError, UnsupportedTimeframeError
from modules.market_data.application.ports import MarketDataSource
from modules.market_data.domain.models import Timeframe

MarketDataFactory = Callable[[], MarketDataSource]


class ExchangeRegistry:
    """Registry + factory of the exchanges the system can talk to.

    Adding an exchange means registering one profile and one adapter factory; nothing that
    consumes the registry changes.
    """

    def __init__(self) -> None:
        self._profiles: dict[str, ExchangeProfile] = {}
        self._factories: dict[str, MarketDataFactory] = {}
        self._sources: dict[str, MarketDataSource] = {}

    def register(self, profile: ExchangeProfile, market_data: MarketDataFactory) -> None:
        self._profiles[profile.exchange_id] = profile
        self._factories[profile.exchange_id] = market_data

    def exchange_ids(self) -> list[str]:
        return sorted(self._profiles)

    def profile(self, exchange_id: str) -> ExchangeProfile:
        try:
            return self._profiles[exchange_id]
        except KeyError:
            known = ", ".join(self.exchange_ids()) or "none"
            raise UnknownExchangeError(
                f"unknown exchange {exchange_id!r} (available: {known})"
            ) from None

    def require(self, exchange_id: str, timeframe: Timeframe) -> ExchangeProfile:
        """The profile, after checking the exchange offers the timeframe."""
        profile = self.profile(exchange_id)
        if timeframe not in profile.capabilities.timeframes:
            raise UnsupportedTimeframeError(f"{exchange_id} does not support {timeframe.value}")
        return profile

    def market_data(self, exchange_id: str) -> MarketDataSource:
        """The (lazily created, shared) market data adapter of an exchange."""
        self.profile(exchange_id)
        if exchange_id not in self._sources:
            self._sources[exchange_id] = self._factories[exchange_id]()
        return self._sources[exchange_id]

    async def aclose(self) -> None:
        for source in self._sources.values():
            close = getattr(source, "aclose", None)
            if close is not None:
                await close()
        self._sources.clear()
