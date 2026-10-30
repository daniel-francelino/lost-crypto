from collections.abc import Callable

from modules.exchanges.application.exchange import Exchange
from modules.exchanges.domain.models import ExchangeProfile
from modules.exchanges.errors import (
    ExchangeConfigurationError,
    UnknownExchangeError,
    UnsupportedTimeframeError,
)
from modules.market_data.application.ports import MarketDataSource
from modules.market_data.domain.models import Timeframe


class ExchangeRegistry:
    """Registry + factory of the enabled exchanges.

    It holds exchange *classes* so their static profile is readable without creating a
    network client (the API only needs profiles to validate requests); the instance is built
    lazily, once, the first time it is used.
    """

    def __init__(self) -> None:
        self._profiles: dict[str, ExchangeProfile] = {}
        self._factories: dict[str, Callable[[], Exchange]] = {}
        self._instances: dict[str, Exchange] = {}

    def register(
        self, exchange_cls: type[Exchange], factory: Callable[[], Exchange] | None = None
    ) -> None:
        profile = getattr(exchange_cls, "PROFILE", None)
        if not isinstance(profile, ExchangeProfile):
            raise ExchangeConfigurationError(
                f"{exchange_cls.__name__} must define PROFILE = ExchangeProfile(...)"
            )
        self._profiles[profile.exchange_id] = profile
        self._factories[profile.exchange_id] = factory or exchange_cls

    def exchange_ids(self) -> list[str]:
        return sorted(self._profiles)

    def profile(self, exchange_id: str) -> ExchangeProfile:
        try:
            return self._profiles[exchange_id]
        except KeyError:
            known = ", ".join(self.exchange_ids()) or "none"
            raise UnknownExchangeError(
                f"unknown or disabled exchange {exchange_id!r} (enabled: {known})"
            ) from None

    def require(self, exchange_id: str, timeframe: Timeframe) -> ExchangeProfile:
        """The profile, after checking the exchange offers the timeframe."""
        profile = self.profile(exchange_id)
        if timeframe not in profile.capabilities.timeframes:
            raise UnsupportedTimeframeError(f"{exchange_id} does not support {timeframe.value}")
        return profile

    def exchange(self, exchange_id: str) -> Exchange:
        """The (lazily created, shared) integration for an exchange."""
        self.profile(exchange_id)
        if exchange_id not in self._instances:
            self._instances[exchange_id] = self._factories[exchange_id]()
        return self._instances[exchange_id]

    def market_data(self, exchange_id: str) -> MarketDataSource:
        """The read-only market data view of an exchange."""
        return self.exchange(exchange_id)

    async def aclose(self) -> None:
        for exchange in self._instances.values():
            await exchange.aclose()
        self._instances.clear()
