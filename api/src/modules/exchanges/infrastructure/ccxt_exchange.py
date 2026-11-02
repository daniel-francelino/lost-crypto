"""Shared base for exchanges integrated through CCXT (Template Method).

It implements the parts of the ``Exchange`` contract that are identical for every CCXT exchange
(candle conversion, retries, error translation, order handling, generic market rules). A
concrete exchange subclasses it, declares its ``PROFILE`` and overrides only the hooks where it
differs. This is the only module that imports ``ccxt``. An exchange that does not use CCXT
subclasses ``Exchange`` directly instead.

Writes (orders) are never retried here: a failure that may have reached the exchange raises
``UnknownOutcome`` and the caller resolves it by looking the order up by its client id.
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
from modules.exchanges.application.ports import (
    Balance,
    MarketOrderRequest,
    StopOrderRequest,
    VenueOrder,
)
from modules.exchanges.domain.connections import ApiPermissions, Credentials
from modules.exchanges.errors import (
    AuthenticationFailed,
    ExchangeConfigurationError,
    ExchangeError,
    ExchangeRejected,
    NotAuthenticated,
    RateLimited,
    TransientExchangeError,
    UnknownOrder,
    UnknownOutcome,
    UnknownSymbolError,
)
from modules.exchanges.infrastructure.ccxt_orders import (
    parse_balances,
    parse_order,
    raw_fills_as_trades,
)
from modules.market_data.domain.models import Candle, ListedMarket, MarketInfo, Timeframe

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 4
_BASE_DELAY_SECONDS = 1.0
_USED_WEIGHT_HEADER = "x-mbx-used-weight-1m"
_USED_WEIGHT_WARN = 3000  # half of Binance's 6000/min IP budget


class CcxtExchange(Exchange):
    CCXT_EXCHANGE_ID = "binance"

    def __init__(
        self,
        client: Any | None = None,
        credentials: Credentials | None = None,
        sandbox: bool = False,
    ) -> None:
        self._authenticated = credentials is not None
        if client is None:
            config: dict[str, Any] = {"enableRateLimit": True}
            if credentials is not None:
                config.update(apiKey=credentials.api_key, secret=credentials.api_secret)
            client = getattr(ccxt_async, self.CCXT_EXCHANGE_ID)(config)
            if sandbox:
                client.set_sandbox_mode(True)  # the exchange's test environment, fake money
            # An adapter serves exactly one environment. Verify the client really points where
            # it was asked to, so real money can never be reached through a "testnet" adapter
            # (or fake orders sent to production by mistake).
            if ("testnet" in str(client.urls.get("api"))) != sandbox:
                raise ExchangeConfigurationError(
                    f"{self.PROFILE.exchange_id}: client environment does not match "
                    f"sandbox={sandbox}"
                )
        self._client: Any = client

    # --- hooks a concrete exchange may override ----------------------------------------------

    def parse_market(self, symbol: str, market: dict[str, Any]) -> MarketInfo | None:
        """Exact trading rules from the exchange's raw CCXT market dict, if it exposes them.

        Return None to fall back to CCXT's generic ``precision`` / ``limits``.
        """
        return None

    def is_supported_market(self, market: dict[str, Any]) -> bool:
        return bool(market.get("spot"))

    def client_order_params(self, client_order_id: str) -> dict[str, Any]:
        """Extra order params carrying our client order id (exchanges name it differently)."""
        return {"newClientOrderId": client_order_id}

    def lookup_params(self, client_order_id: str) -> dict[str, Any]:
        """Params to find/cancel an order by our client order id."""
        return {"origClientOrderId": client_order_id}

    def stop_order_type(self, request: StopOrderRequest) -> str:
        return "STOP_LOSS"

    def stop_order_params(self, request: StopOrderRequest) -> dict[str, Any]:
        return {}

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

    async def fetch_server_time(self) -> datetime:
        """The exchange's clock (to measure the local clock's skew)."""
        millis = await self._call(self._client.fetch_time)
        return datetime.fromtimestamp(int(millis) / 1000, UTC)

    async def list_markets(self) -> list[ListedMarket]:
        """Supported spot or linear-perpetual instruments from this exchange's catalog."""
        await self._call(self._client.load_markets)
        return [
            ListedMarket(
                symbol=str(m["symbol"]),
                active=bool(m.get("active")),
                product=("linear_perpetual" if m.get("swap") and m.get("linear") else "spot"),
                base=str(m["base"]) if m.get("base") else None,
                quote=str(m["quote"]) if m.get("quote") else None,
                settlement=str(m["settle"]) if m.get("settle") else None,
                contract_size=Decimal(str(m.get("contractSize") or 1)),
            )
            for m in self._client.markets.values()
            if self.is_supported_market(m)
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

    # --- trading (authenticated) -------------------------------------------------------------

    async def create_market_order(self, request: MarketOrderRequest) -> VenueOrder:
        self._require_authentication()
        if request.product not in self.capabilities.products:
            raise ExchangeRejected(
                f"{self.PROFILE.exchange_id} does not support {request.product.value} orders"
            )
        if request.leverage > self.capabilities.max_leverage:
            raise ExchangeRejected(
                f"leverage {request.leverage}x exceeds this exchange adapter's "
                f"{self.capabilities.max_leverage}x limit"
            )
        await self.prepare_market_order(request)
        params = self.client_order_params(request.client_order_id)
        params.update(self.market_order_params(request))
        try:
            raw = await self._client.create_order(
                request.symbol, "market", request.side.value, float(request.quantity), None, params
            )
        except ccxt.InvalidOrder as exc:
            if _is_duplicate(exc):  # idempotent: the first attempt did reach the exchange
                existing = await self.fetch_order(request.symbol, request.client_order_id)
                if existing is not None:
                    return existing
            raise ExchangeRejected(str(exc)) from exc
        except ccxt.BaseError as exc:
            raise self._write_error(exc) from exc
        return await self._complete(raw, request.symbol)

    async def prepare_market_order(self, request: MarketOrderRequest) -> None:
        return None

    def market_order_params(self, request: MarketOrderRequest) -> dict[str, Any]:
        return {}

    async def create_stop_order(self, request: StopOrderRequest) -> VenueOrder:
        self._require_authentication()
        if request.product not in self.capabilities.products:
            raise ExchangeRejected(
                f"{self.PROFILE.exchange_id} does not support {request.product.value} stops"
            )
        params = self.client_order_params(request.client_order_id)
        params["stopPrice"] = float(request.stop_price)
        params.update(self.stop_order_params(request))
        try:
            raw = await self._client.create_order(
                request.symbol,
                self.stop_order_type(request),
                request.side.value,
                float(request.quantity),
                None,
                params,
            )
        except ccxt.InvalidOrder as exc:
            if _is_duplicate(exc):
                existing = await self.fetch_order(request.symbol, request.client_order_id)
                if existing is not None:
                    return existing
            raise ExchangeRejected(str(exc)) from exc
        except ccxt.BaseError as exc:
            raise self._write_error(exc) from exc
        return await self._complete(raw, request.symbol)

    async def fetch_order(self, symbol: str, client_order_id: str) -> VenueOrder | None:
        self._require_authentication()
        try:
            raw = await self._call(
                lambda: self._client.fetch_order(
                    client_order_id, symbol, self.lookup_params(client_order_id)
                )
            )
        except ccxt.OrderNotFound:
            return None
        return await self._complete(raw, symbol)

    async def cancel_order(self, symbol: str, client_order_id: str) -> VenueOrder:
        self._require_authentication()
        try:
            raw = await self._client.cancel_order(
                client_order_id, symbol, self.lookup_params(client_order_id)
            )
        except ccxt.OrderNotFound as exc:
            raise UnknownOrder(client_order_id) from exc
        except ccxt.BaseError as exc:
            raise self._write_error(exc) from exc
        raw = {**raw, "status": raw.get("status") or "canceled"}
        return parse_order(raw, symbol, trades=[])

    async def fetch_open_orders(self, symbol: str) -> list[VenueOrder]:
        self._require_authentication()
        raws = await self._call(lambda: self._client.fetch_open_orders(symbol))
        return [parse_order(raw, symbol, trades=[]) for raw in raws]

    async def fetch_balances(self) -> dict[str, Balance]:
        self._require_authentication()
        return parse_balances(await self._call(self._client.fetch_balance))

    async def fetch_api_permissions(self) -> ApiPermissions:
        self._require_authentication()
        raise ExchangeError(
            f"{self.PROFILE.exchange_id}: reading API key permissions is not implemented"
        )

    async def aclose(self) -> None:
        await self._client.close()

    # --- internals ---------------------------------------------------------------------------

    def _require_authentication(self) -> None:
        if not self._authenticated:
            raise NotAuthenticated(
                f"{self.PROFILE.exchange_id}: this integration has no credentials"
            )

    async def _complete(self, raw: dict[str, Any], symbol: str) -> VenueOrder:
        """Parse an order, fetching its executions when the response did not embed them."""
        trades = raw.get("trades") or raw_fills_as_trades(
            (raw.get("info") or {}).get("fills") or [], symbol.partition("/")[2]
        )
        if not trades and _to_decimal(raw.get("filled")) > 0:
            trades = await self._call(
                lambda: self._client.fetch_my_trades(symbol, None, None, {"orderId": raw["id"]})
            )
        return parse_order(raw, symbol, trades=trades)

    @staticmethod
    def _write_error(exc: ccxt.BaseError) -> ExchangeError:
        """Classify a failed order write. Anything that might have reached the exchange is an
        unknown outcome; only provable refusals are permanent."""
        if isinstance(exc, ccxt.AuthenticationError):  # includes PermissionDenied
            return AuthenticationFailed(str(exc))
        if isinstance(exc, ccxt.RateLimitExceeded | ccxt.DDoSProtection):
            return TransientExchangeError(f"rate limited, order not placed: {exc}")
        if isinstance(exc, ccxt.InsufficientFunds | ccxt.BadRequest | ccxt.BadSymbol):
            return ExchangeRejected(str(exc))
        return UnknownOutcome(f"{type(exc).__name__}: {exc}")

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
                result = await operation()
            except (ccxt.RateLimitExceeded, ccxt.DDoSProtection) as exc:
                # Never retry a 429/418 on a timer of ours: only the exchange's Retry-After counts.
                raise RateLimited(str(exc), self._retry_after()) from exc
            except ccxt.NetworkError as exc:
                if attempt == _MAX_ATTEMPTS:
                    raise TransientExchangeError(str(exc)) from exc
                delay = _BASE_DELAY_SECONDS * 2 ** (attempt - 1)
                logger.warning("transient exchange error (attempt %d): %s", attempt, exc)
                await asyncio.sleep(delay)
            except ccxt.OrderNotFound:
                raise
            except ccxt.AuthenticationError as exc:
                raise AuthenticationFailed(str(exc)) from exc
            except ccxt.BadSymbol as exc:
                raise UnknownSymbolError(str(exc)) from exc
            except ccxt.BaseError as exc:
                raise ExchangeError(str(exc)) from exc
            else:
                self._watch_used_weight()
                return result
        raise AssertionError("unreachable")  # pragma: no cover

    def _response_headers(self) -> dict[str, str]:
        headers = getattr(self._client, "last_response_headers", None)
        if not isinstance(headers, dict):
            return {}
        return {str(k).lower(): str(v) for k, v in headers.items()}

    def _retry_after(self) -> float | None:
        raw = self._response_headers().get("retry-after")
        try:
            return float(raw) if raw is not None else None
        except ValueError:
            return None

    def _watch_used_weight(self) -> None:
        raw = self._response_headers().get(_USED_WEIGHT_HEADER)
        if raw is not None and raw.isdigit() and int(raw) >= _USED_WEIGHT_WARN:
            logger.warning(
                "%s: used request weight %s in the last minute", self.PROFILE.exchange_id, raw
            )


def _is_duplicate(exc: Exception) -> bool:
    return "duplicate" in str(exc).lower()


def _to_decimal(value: Any) -> Decimal:
    return Decimal(str(value)) if value not in (None, "") else Decimal(0)
