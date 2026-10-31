"""THE exchange contract.

Every exchange integration is one class that implements this interface, in one file, and
returns exactly the value objects declared here. The rest of the system never sees an SDK, a
raw payload or an exchange name: it sees ``Exchange`` (or the narrower ``MarketDataSource`` /
``ExchangeGateway`` views of it).

Adding an exchange = a new subclass in ``exchanges/infrastructure/<name>.py`` + one line in
``exchanges/infrastructure/catalog.py``. Python refuses to instantiate a subclass that leaves
any method below unimplemented, and the contract tests check the behaviour.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import ClassVar

from modules.exchanges.application.ports import (
    Balance,
    MarketOrderRequest,
    StopOrderRequest,
    VenueOrder,
)
from modules.exchanges.domain.models import ExchangeCapabilities, ExchangeProfile
from modules.market_data.domain.models import Candle, MarketInfo, Timeframe


class Exchange(ABC):
    #: Static facts about the exchange (id, capabilities, default fees). Required.
    PROFILE: ClassVar[ExchangeProfile]

    @property
    def capabilities(self) -> ExchangeCapabilities:
        return self.PROFILE.capabilities

    # --- market data (public, no credentials) ------------------------------------------------

    @abstractmethod
    async def fetch_candles(
        self, symbol: str, timeframe: Timeframe, since: datetime, limit: int
    ) -> list[Candle]:
        """Candles with ``open_time >= since``, ascending, as ``Decimal`` OHLCV.

        May include the candle still in progress; callers filter on ``close_time``.
        Raises ``UnknownSymbolError`` for symbols the exchange does not list and
        ``TransientExchangeError`` for network/rate-limit problems.
        """

    @abstractmethod
    async def fetch_market_info(self, symbol: str) -> MarketInfo:
        """Trading rules for a symbol: lot size, tick size, minimum quantity and notional."""

    # --- trading (needs credentials once real orders are enabled) ----------------------------

    @abstractmethod
    async def create_market_order(self, request: MarketOrderRequest) -> VenueOrder:
        """Place a market order. Idempotent on ``request.client_order_id``: repeating the call
        returns the existing order, never a second one. Raises ``ExchangeRejected`` when the
        exchange refuses it and ``UnknownOutcome`` when it cannot tell whether the order was
        placed; the latter is resolved with ``fetch_order``, never by blindly retrying."""

    @abstractmethod
    async def fetch_order(self, symbol: str, client_order_id: str) -> VenueOrder | None:
        """The order with that client id, or None if the exchange has no such order."""

    @abstractmethod
    async def cancel_order(self, symbol: str, client_order_id: str) -> VenueOrder:
        """Cancel an open order. Raises ``UnknownOrder`` / ``ExchangeRejected``."""

    @abstractmethod
    async def create_stop_order(self, request: StopOrderRequest) -> VenueOrder:
        """Rest a protective sell on the exchange that fires at ``request.stop_price`` (market).

        Same idempotency and error rules as ``create_market_order``. Only call it when
        ``capabilities.native_stop_orders`` is true.
        """

    @abstractmethod
    async def fetch_open_orders(self, symbol: str) -> list[VenueOrder]:
        """Every order still open on the account for ``symbol`` (ours and foreign)."""

    @abstractmethod
    async def fetch_balances(self) -> dict[str, Balance]:
        """Account balances by asset (only assets holding something)."""

    # --- lifecycle ---------------------------------------------------------------------------

    @abstractmethod
    async def aclose(self) -> None:
        """Release network resources (sessions, sockets)."""
