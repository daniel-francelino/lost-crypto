"""Shared base for exchanges integrated through CCXT (Template Method).

It implements the parts of the ``Exchange`` contract that are identical for every CCXT exchange
(candle conversion, retries, error translation, generic market rules). A concrete exchange
subclasses it, declares its ``PROFILE`` and overrides only the hooks where it differs. This is
the only module that imports ``ccxt``. An exchange that does not use CCXT subclasses
``Exchange`` directly instead.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import ccxt
import ccxt.async_support as ccxt_async

from modules.exchanges.application.exchange import Exchange
from modules.exchanges.application.ports import MarketOrderRequest, VenueOrder
from modules.exchanges.errors import (
    ExchangeError,
    TradingNotEnabled,
    TransientExchangeError,
    UnknownSymbolError,
)
from modules.market_data.domain.models import Candle, MarketInfo, Timeframe

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 4
_BASE_DELAY_SECONDS = 1.0


class CcxtExchange(Exchange):
    """Public market data over CCXT. Real order placement is disabled until it is built behind
    credentials, the vault and reconciliation (Phase 4)."""

    def __init__(self, client: Any | None = None) -> None:
        # Public data only: no credentials are read or accepted here.
        self._client: Any = client or getattr(ccxt_async, self.PROFILE.exchange_id)(
            {"enableRateLimit": True}
        )

    # --- hooks a concrete exchange may override ----------------------------------------------

    def parse_market(self, symbol: str, market: dict[str, Any]) -> MarketInfo | None:
        """Exact trading rules from the exchange's raw CCXT market dict, if it exposes them.

        Return None to fall back to CCXT's generic ``precision`` / ``limits``.
        """
        return None

    # --- market data -------------------------------------------------------------------------

    async def fetch_candles(
        self, symbol: str, timeframe: Timeframe, since: datetime, limit: int
    ) -> list[Candle]:
        since_ms = int(since.timestamp() * 1000)
        rows = await self._call(
            lambda: self._client.fetch_ohlcv(symbol, timeframe.value, since_ms, limit)
        )
        return [
            Candle(
                symbol=symbol,
                timeframe=timeframe,
                open_time=datetime.fromtimestamp(int(r[0]) / 1000, UTC),
                open=Decimal(str(r[1])),
                high=Decimal(str(r[2])),
                low=Decimal(str(r[3])),
                close=Decimal(str(r[4])),
                volume=Decimal(str(r[5])),
            )
            for r in rows
        ]

    async def fetch_market_info(self, symbol: str) -> MarketInfo:
        await self._call(self._client.load_markets)
        try:
            market = self._client.market(symbol)
        except ccxt.BadSymbol as exc:
            raise UnknownSymbolError(f"unknown symbol: {symbol}") from exc
        exact = self.parse_market(symbol, market)
        if exact is not None:
            return exact
        limits = market.get("limits") or {}
        return MarketInfo(
            symbol=symbol,
            step_size=self._increment((market.get("precision") or {}).get("amount")),
            tick_size=self._increment((market.get("precision") or {}).get("price")),
            min_quantity=Decimal(str((limits.get("amount") or {}).get("min") or 0)),
            min_notional=Decimal(str((limits.get("cost") or {}).get("min") or 0)),
        )

    # --- trading: not enabled yet ------------------------------------------------------------

    async def create_market_order(self, request: MarketOrderRequest) -> VenueOrder:
        raise TradingNotEnabled(f"real orders on {self.PROFILE.exchange_id} are not enabled yet")

    async def fetch_order(self, symbol: str, client_order_id: str) -> VenueOrder | None:
        raise TradingNotEnabled(f"real orders on {self.PROFILE.exchange_id} are not enabled yet")

    async def cancel_order(self, symbol: str, client_order_id: str) -> VenueOrder:
        raise TradingNotEnabled(f"real orders on {self.PROFILE.exchange_id} are not enabled yet")

    async def aclose(self) -> None:
        await self._client.close()

    # --- internals ---------------------------------------------------------------------------

    def _increment(self, precision: Any) -> Decimal:
        if precision is None:
            raise ExchangeError("exchange did not report market precision")
        mode = self._client.precisionMode
        if mode == ccxt.TICK_SIZE:
            return Decimal(str(precision))
        if mode == ccxt.DECIMAL_PLACES:
            return Decimal(1).scaleb(-int(precision))
        raise ExchangeError(f"unsupported precision mode: {mode}")

    async def _call[T](self, operation: Callable[[], Awaitable[T]]) -> T:
        """Run a read call, retrying transient failures with exponential backoff.

        Only used for idempotent reads; order writes must never be retried this way.
        """
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                return await operation()
            except (ccxt.NetworkError, ccxt.RateLimitExceeded) as exc:
                if attempt == _MAX_ATTEMPTS:
                    raise TransientExchangeError(str(exc)) from exc
                delay = _BASE_DELAY_SECONDS * 2 ** (attempt - 1)
                logger.warning("transient exchange error (attempt %d): %s", attempt, exc)
                await asyncio.sleep(delay)
            except ccxt.BadSymbol as exc:
                raise UnknownSymbolError(str(exc)) from exc
            except ccxt.BaseError as exc:
                raise ExchangeError(str(exc)) from exc
        raise AssertionError("unreachable")  # pragma: no cover
