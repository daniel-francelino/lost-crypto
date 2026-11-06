"""Binance USDⓈ-M perpetual integration, isolated from the Binance Spot adapter."""

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import suppress
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from modules.exchanges.application.ports import (
    ExchangePosition,
    FundingIncome,
    MarketOrderRequest,
    StopOrderRequest,
    VenueOrder,
)
from modules.exchanges.domain.connections import ApiPermissions
from modules.exchanges.domain.models import (
    ExchangeCapabilities,
    ExchangeProfile,
    FeeSchedule,
    MarginMode,
    OrderType,
    PositionSide,
    TradingProduct,
)
from modules.exchanges.errors import ExchangeError, ExchangeRejected
from modules.exchanges.infrastructure.ccxt_exchange import CcxtExchange
from modules.exchanges.infrastructure.ccxt_orders import parse_order
from modules.market_data.domain.models import Candle, FundingRate, MarketInfo, MarkPrice, Timeframe

BINANCE_USDM_ID = "binance-usdm"
MAX_LEVERAGE = 10
USER_STREAM_KEEPALIVE_SECONDS = 30 * 60

BINANCE_USDM_PROFILE = ExchangeProfile(
    capabilities=ExchangeCapabilities(
        exchange_id=BINANCE_USDM_ID,
        name="Binance USD-M Perpetual",
        order_types=frozenset({OrderType.MARKET, OrderType.STOP_LOSS}),
        native_stop_orders=True,
        max_client_order_id_length=36,
        has_testnet=True,
        timeframes=frozenset(Timeframe),
        products=frozenset({TradingProduct.LINEAR_PERPETUAL}),
        max_leverage=MAX_LEVERAGE,
        has_demo=True,  # demo-fapi.binance.com, Futures Demo keys
    ),
    fees=FeeSchedule(maker_rate=Decimal("0.0002"), taker_rate=Decimal("0.0005")),
)


class BinanceUsdmExchange(CcxtExchange):
    PROFILE = BINANCE_USDM_PROFILE
    CCXT_EXCHANGE_ID = "binanceusdm"

    def is_supported_market(self, market: dict[str, Any]) -> bool:
        return bool(
            market.get("swap")
            and market.get("linear")
            and market.get("settle") == "USDT"
            and market.get("active")
        )

    def parse_market(self, symbol: str, market: dict[str, Any]) -> MarketInfo | None:
        filters = {
            item["filterType"]: item for item in (market.get("info") or {}).get("filters", [])
        }
        lot = filters.get("LOT_SIZE")
        price = filters.get("PRICE_FILTER")
        notional = filters.get("MIN_NOTIONAL") or filters.get("NOTIONAL")
        if lot is None or price is None:
            return None
        return MarketInfo(
            symbol=symbol,
            step_size=Decimal(lot["stepSize"]),
            tick_size=Decimal(price["tickSize"]),
            min_quantity=Decimal(lot["minQty"]),
            min_notional=Decimal(
                (notional or {}).get("notional", (notional or {}).get("minNotional", "0"))
            ),
        )

    async def fetch_market_info(self, symbol: str) -> MarketInfo:
        """Return trading rules only for an active USDT-settled linear perpetual."""
        info = await super().fetch_market_info(symbol)
        market = self._client.market(symbol)
        if not self.is_supported_market(market):
            raise ExchangeRejected(f"{symbol} is not an active USDT linear perpetual")
        if market.get("symbol") != symbol:
            raise ExchangeRejected("USD-M market lookup returned a different instrument")
        return info

    async def fetch_mark_price(self, symbol: str) -> MarkPrice:
        raw = await self._call(lambda: self._client.fetch_mark_price(symbol))
        # CCXT 4.5 returns the ticker structure with "markPrice"; the raw premiumIndex payload
        # keeps the same field in "info". Never fall back to "last": it is not the mark price.
        info = raw.get("info")
        value = raw.get("markPrice") or raw.get("mark")
        if value is None and isinstance(info, dict):
            value = info.get("markPrice")
        timestamp = raw.get("timestamp") or (info.get("time") if isinstance(info, dict) else None)
        if value is None or timestamp is None:
            raise ExchangeRejected(f"{symbol}: the exchange did not return a mark price")
        return MarkPrice(
            symbol=symbol,
            price=Decimal(str(value)),
            timestamp=datetime.fromtimestamp(int(timestamp) / 1000, UTC),
        )

    async def fetch_mark_candles(
        self, symbol: str, timeframe: Timeframe, since: datetime, limit: int
    ) -> list[Candle]:
        rows = await self._call(
            lambda: self._client.fetch_ohlcv(
                symbol, timeframe.value, int(since.timestamp() * 1000), limit, {"price": "mark"}
            )
        )
        return [
            Candle(
                symbol=symbol,
                timeframe=timeframe,
                open_time=datetime.fromtimestamp(int(row[0]) / 1000, UTC),
                open=Decimal(str(row[1])),
                high=Decimal(str(row[2])),
                low=Decimal(str(row[3])),
                close=Decimal(str(row[4])),
                volume=Decimal(str(row[5])),
            )
            for row in rows
        ]

    async def fetch_funding_rates(
        self, symbol: str, since: datetime, limit: int
    ) -> list[FundingRate]:
        rows = await self._call(
            lambda: self._client.fetch_funding_rate_history(
                symbol, int(since.timestamp() * 1000), limit
            )
        )
        return [
            FundingRate(
                symbol=symbol,
                rate=Decimal(str(row["fundingRate"])),
                funding_time=datetime.fromtimestamp(int(row["timestamp"]) / 1000, UTC),
                mark_price=(
                    Decimal(str(row["markPrice"])) if row.get("markPrice") is not None else None
                ),
                rate_type=(
                    "special"
                    if isinstance(row.get("info"), dict)
                    and str(row["info"].get("rateType", "")).lower() == "special"
                    else "regular"
                ),
            )
            for row in rows
            if row.get("fundingRate") is not None and row.get("timestamp") is not None
        ]

    async def stream_user_events(self) -> AsyncIterator[dict[str, object]]:
        """Stream authenticated USD-M Demo account events from Binance's private endpoint.

        The key is renewed every 30 minutes. A disconnect or expired key ends this iterator so
        the worker can reconcile through REST before opening a replacement stream.
        """
        if not self._demo:
            raise ExchangeRejected("USD-M private user streams are enabled only for Binance Demo")
        self._require_authentication()
        await self._call(self._client.fetch_time)
        session = getattr(self._client, "session", None)
        if session is None or session.closed:
            raise ExchangeError("Binance HTTP session is unavailable for the private stream")

        response = await self._call(self._client.fapiPrivatePostListenKey)
        listen_key = response.get("listenKey") if isinstance(response, dict) else None
        if not isinstance(listen_key, str) or not listen_key:
            raise ExchangeError("Binance did not return a USD-M user stream listen key")
        url = f"wss://demo-fstream.binance.com/private/ws/{listen_key}"

        async def keepalive() -> None:
            # Renew on a clock, not only when the stream is idle: active accounts can emit
            # events continuously and otherwise let the 60-minute listen key expire.
            while True:
                await asyncio.sleep(USER_STREAM_KEEPALIVE_SECONDS)
                await self._call(
                    lambda: self._client.fapiPrivatePutListenKey({"listenKey": listen_key})
                )

        keepalive_task: asyncio.Task[None] | None = None
        try:
            async with session.ws_connect(url, heartbeat=30) as websocket:
                keepalive_task = asyncio.create_task(keepalive())
                while True:
                    try:
                        message = await asyncio.wait_for(websocket.receive(), timeout=30 * 60)
                    except TimeoutError:
                        if keepalive_task.done():
                            await keepalive_task
                        continue
                    if keepalive_task.done():
                        await keepalive_task
                    message_type = getattr(message.type, "name", str(message.type))
                    if message_type == "TEXT":
                        try:
                            payload = json.loads(message.data)
                        except (TypeError, json.JSONDecodeError) as exc:
                            raise ExchangeError(
                                "Binance sent malformed private stream JSON"
                            ) from exc
                        if not isinstance(payload, dict):
                            raise ExchangeError("Binance sent an unexpected private stream payload")
                        event = payload.get("event", payload)
                        if not isinstance(event, dict):
                            raise ExchangeError("Binance sent a malformed private stream event")
                        yield event
                        if event.get("e") == "listenKeyExpired":
                            return
                    elif message_type in {"CLOSE", "CLOSED", "CLOSING", "ERROR"}:
                        raise ExchangeError("Binance USD-M private stream disconnected")
        except asyncio.CancelledError:
            raise
        finally:
            if keepalive_task is not None:
                keepalive_task.cancel()
                with suppress(asyncio.CancelledError):
                    await keepalive_task
            # Avoid accumulating live listen keys across worker restarts and reconnects.
            with suppress(Exception):
                await self._call(
                    lambda: self._client.fapiPrivateDeleteListenKey({"listenKey": listen_key})
                )

    async def fetch_api_permissions(self) -> ApiPermissions:
        self._require_authentication()
        if self._demo or self._sandbox:
            # SAPI key restrictions are only available on Binance mainnet. CCXT keeps the
            # SAPI URL on the production host for USD-M Demo clients, so never make this call
            # with Demo/Testnet credentials. Environment health is checked through USD-M reads.
            raise ExchangeRejected(
                "Binance API key restrictions are unavailable in Demo/Testnet; "
                "use an environment-scoped USD-M account read"
            )
        raw = await self._call(lambda: self._client.sapiGetAccountApiRestrictions())
        return ApiPermissions(
            can_read=bool(raw.get("enableReading")),
            can_trade=bool(raw.get("enableFutures")),
            can_withdraw=bool(raw.get("enableWithdrawals")),
            can_transfer=bool(
                raw.get("enableInternalTransfer") or raw.get("permitsUniversalTransfer")
            ),
            ip_restricted=bool(raw.get("ipRestrict")),
            can_trade_derivatives=bool(raw.get("enableFutures")),
        )

    async def _configured_leverage(self, symbol: str) -> int | None:
        configuration = await self._call(lambda: self._client.fetch_margin_mode(symbol))
        info = configuration.get("info") if isinstance(configuration, dict) else None
        return _optional_integer(info.get("leverage")) if isinstance(info, dict) else None

    async def fetch_positions(self, symbols: list[str] | None = None) -> list[ExchangePosition]:
        """Read non-zero USD-M positions and normalize Binance/CCXT account fields."""
        self._require_authentication()
        raws = await self._call(lambda: self._client.fetch_positions(symbols))
        positions: list[ExchangePosition] = []
        configured_leverage: dict[str, int | None] = {}
        for raw in raws:
            info = raw.get("info") or {}
            contracts = _optional_decimal(raw.get("contracts"))
            if contracts is None:
                contracts = abs(_optional_decimal(info.get("positionAmt")) or Decimal(0))
            else:
                contracts = abs(contracts)
            if contracts <= 0:
                continue
            raw_side = raw.get("side")
            if raw_side not in (PositionSide.LONG.value, PositionSide.SHORT.value):
                amount = _optional_decimal(info.get("positionAmt"))
                if amount is None or amount == 0:
                    raise ExchangeError("Binance USD-M returned an open position without a side")
                raw_side = PositionSide.LONG.value if amount > 0 else PositionSide.SHORT.value
            raw_margin_mode = raw.get("marginMode")
            try:
                margin_mode = MarginMode(raw_margin_mode) if raw_margin_mode is not None else None
            except ValueError:
                raise ExchangeError(
                    "Binance USD-M returned an unknown position margin mode"
                ) from None
            isolated_margin = (
                _optional_decimal(info.get("isolatedWallet"))
                if margin_mode is MarginMode.ISOLATED
                else None
            )
            if isolated_margin is None and margin_mode is MarginMode.ISOLATED:
                isolated_margin = _optional_decimal(raw.get("initialMargin"))
            symbol = str(raw.get("symbol") or "")
            leverage = _optional_integer(raw.get("leverage"))
            if leverage is None and symbol:
                # Position Information V3 (the CCXT default) no longer returns "leverage". It is
                # a symbol setting, so read it from the symbol's configuration. Without it every
                # remote position looks different from the ledger and the reconciler pauses bots.
                if symbol not in configured_leverage:
                    configured_leverage[symbol] = await self._configured_leverage(symbol)
                leverage = configured_leverage[symbol]
            positions.append(
                ExchangePosition(
                    symbol=symbol,
                    side=PositionSide(raw_side),
                    quantity=contracts,
                    entry_price=_positive_decimal(raw.get("entryPrice")),
                    mark_price=_positive_decimal(raw.get("markPrice")),
                    unrealized_pnl=_optional_decimal(raw.get("unrealizedPnl")) or Decimal(0),
                    leverage=leverage,
                    margin_mode=margin_mode,
                    isolated_margin=isolated_margin,
                    liquidation_price=_positive_decimal(raw.get("liquidationPrice")),
                    notional=_positive_decimal(raw.get("notional")),
                )
            )
        return positions

    async def fetch_funding_income(
        self, symbol: str, start: datetime, end: datetime, limit: int = 1000
    ) -> list[FundingIncome]:
        """Read Binance's settled USD-M FUNDING_FEE income, preserving its signed amount.

        Binance exposes this via GET /fapi/v1/income. CCXT normalizes the ledger row while
        retaining the original signed ``income`` and ``tranId`` in ``info``.
        """
        if start.tzinfo is None or end.tzinfo is None or end < start:
            raise ValueError("funding income range must be ordered and timezone-aware")
        if not 1 <= limit <= 1000:
            raise ValueError("funding income page size must be between 1 and 1000")
        self._require_authentication()
        await self._call(self._client.load_markets)
        try:
            market_id = str(self._client.market(symbol)["id"])
        except (KeyError, TypeError) as exc:
            raise ExchangeRejected(f"unknown Binance USD-M symbol {symbol}") from exc
        rows = await self._call(
            lambda: self._client.fetch_ledger(
                "USDT",
                int(start.timestamp() * 1000),
                limit,
                {
                    "subType": "linear",
                    "until": int(end.timestamp() * 1000),
                    "incomeType": "FUNDING_FEE",
                    "symbol": market_id,
                },
            )
        )
        result: list[FundingIncome] = []
        for row in rows:
            info = row.get("info") or {}
            if info.get("incomeType") != "FUNDING_FEE":
                continue
            raw_symbol = info.get("symbol")
            raw_amount = info.get("income")
            raw_id = info.get("tranId")
            raw_time = info.get("time")
            if raw_symbol != market_id or raw_amount is None or raw_id is None or raw_time is None:
                raise ExchangeError("Binance USD-M returned a malformed funding income row")
            amount = _optional_decimal(raw_amount)
            if amount is None:
                raise ExchangeError("Binance USD-M returned an empty funding income amount")
            occurred_at = datetime.fromtimestamp(int(raw_time) / 1000, UTC)
            if start <= occurred_at <= end:
                result.append(
                    FundingIncome(
                        transaction_id=str(raw_id),
                        symbol=symbol,
                        asset=str(info.get("asset") or row.get("code") or "USDT"),
                        amount=amount,
                        occurred_at=occurred_at,
                    )
                )
        return sorted(result, key=lambda item: (item.occurred_at, item.transaction_id))

    async def prepare_market_order(self, request: MarketOrderRequest) -> None:
        if request.product is not TradingProduct.LINEAR_PERPETUAL:
            raise ExchangeRejected("Binance USD-M accepts only linear perpetual orders")
        if request.margin_mode is not MarginMode.ISOLATED:
            raise ExchangeRejected("Binance USD-M bots currently require isolated margin")
        if request.leverage > self.capabilities.max_leverage:
            raise ExchangeRejected("leverage exceeds the Binance USD-M adapter limit")

    async def prepare_market_configuration(
        self,
        product: TradingProduct,
        symbol: str,
        leverage: int,
        margin_mode: MarginMode | None,
        max_notional: Decimal | None = None,
        allow_existing_exposure: bool = False,
    ) -> None:
        if product is not TradingProduct.LINEAR_PERPETUAL:
            raise ExchangeRejected("Binance USD-M accepts only linear perpetual markets")
        if margin_mode is not MarginMode.ISOLATED:
            raise ExchangeRejected("Binance USD-M requires isolated margin")
        if not 1 <= leverage <= self.capabilities.max_leverage:
            raise ExchangeRejected(
                f"leverage must be between 1x and {self.capabilities.max_leverage}x"
            )
        await self._call(self._client.load_markets)
        try:
            market = self._client.market(symbol)
        except Exception as exc:
            raise ExchangeRejected(f"unknown Binance USD-M perpetual symbol {symbol}") from exc
        if not self.is_supported_market(market):
            raise ExchangeRejected(f"{symbol} is not an active USDT linear perpetual")
        tiers = await self.fetch_leverage_tiers(symbol)
        notional = max_notional if max_notional is not None else Decimal(0)
        supported_tier = next(
            (
                tier
                for tier in tiers
                if (
                    tier.max_leverage >= leverage
                    and (notional == 0 or tier.supports(notional, leverage))
                )
            ),
            None,
        )
        if supported_tier is None:
            raise ExchangeRejected(
                f"Binance leverage tiers do not support {leverage}x at notional {notional}"
            )
        if self._demo or self._sandbox:
            # Binance Demo/Testnet does not use the production SAPI restrictions endpoint. The
            # account read and the following isolated/leverage configuration calls validate the
            # credentials against the same USD-M environment as the orders.
            await self._call(lambda: self._client.fetch_balance({"type": "future"}))
        else:
            permissions = await self.fetch_api_permissions()
            if not permissions.can_read or not permissions.can_trade_derivatives:
                raise ExchangeRejected("API key must have read and Binance Futures trading access")
        multi_assets_mode = await self._call(self._client.fapiPrivateGetMultiAssetsMargin)
        enabled = (
            multi_assets_mode.get("multiAssetsMargin")
            if isinstance(multi_assets_mode, dict)
            else None
        )
        if not isinstance(enabled, bool):
            raise ExchangeError("Binance did not confirm the USD-M collateral mode")
        if enabled:
            raise ExchangeRejected(
                "Binance USD-M Multi-Assets Mode is unsupported; use Single-Asset Mode"
            )
        position_mode = await self._call(self._client.fetch_position_mode)
        if position_mode.get("hedged"):
            raise ExchangeRejected("Binance USD-M account must use one-way position mode")
        if not allow_existing_exposure:
            positions = await self._call(lambda: self._client.fetch_positions([symbol]))
            if any(Decimal(str(position.get("contracts") or 0)) != 0 for position in positions):
                raise ExchangeRejected(
                    f"close the existing {symbol} futures position before starting this bot"
                )
            orders = await self.fetch_open_orders(symbol)
            if orders:
                raise ExchangeRejected(f"cancel existing {symbol} futures orders before starting")

        current_margin = await self._call(lambda: self._client.fetch_margin_mode(symbol))
        if allow_existing_exposure and current_margin.get("marginMode") != "isolated":
            raise ExchangeRejected(
                f"Binance position is not configured for isolated margin on {symbol}"
            )
        if not allow_existing_exposure and current_margin.get("marginMode") != "isolated":
            await self._call(lambda: self._client.set_margin_mode("isolated", symbol))
        if not allow_existing_exposure:
            await self._call(lambda: self._client.set_leverage(leverage, symbol))

        configured_margin = await self._call(lambda: self._client.fetch_margin_mode(symbol))
        raw_leverage = (configured_margin.get("info") or {}).get("leverage")
        if configured_margin.get("marginMode") != "isolated":
            raise ExchangeRejected(f"Binance did not confirm isolated margin for {symbol}")
        if raw_leverage is None or int(raw_leverage) != leverage:
            raise ExchangeRejected(f"Binance did not confirm requested {leverage}x leverage")

    def stop_order_type(self, request: StopOrderRequest) -> str:
        if request.product is TradingProduct.LINEAR_PERPETUAL:
            return "market"  # CCXT translates stopPrice into Binance STOP_MARKET/algo order.
        return super().stop_order_type(request)

    def lookup_params(self, client_order_id: str) -> dict[str, Any]:
        if client_order_id.endswith("-sl"):
            # CCXT selects the current USD-M algo-order endpoints with trigger=True.
            return {"clientAlgoId": client_order_id, "trigger": True}
        return super().lookup_params(client_order_id)

    async def fetch_open_orders(self, symbol: str) -> list[VenueOrder]:
        standard = await super().fetch_open_orders(symbol)
        conditional = await self._call(
            lambda: self._client.fetch_open_orders(symbol, None, None, {"trigger": True})
        )
        # Conditional (algo) orders are raw CCXT dicts: normalize them like the standard ones, or
        # callers that read ``order.client_order_id`` fail as soon as a native stop is open.
        return [*standard, *(parse_order(raw, symbol, trades=[]) for raw in conditional)]

    async def fetch_all_open_orders(self) -> list[VenueOrder]:
        """Read every standard and conditional USD-M order for account-wide reconciliation."""
        self._require_authentication()
        standard_raw = await self._call(lambda: self._client.fetch_open_orders(None))
        conditional_raw = await self._call(
            lambda: self._client.fetch_open_orders(None, None, None, {"trigger": True})
        )
        orders: list[VenueOrder] = []
        for raw in [*standard_raw, *conditional_raw]:
            symbol = str(raw.get("symbol") or "")
            if not symbol:
                raise ExchangeError("Binance USD-M returned an open order without a symbol")
            orders.append(parse_order(raw, symbol, trades=[]))
        return orders

    def stop_order_params(self, request: StopOrderRequest) -> dict[str, Any]:
        if request.product is not TradingProduct.LINEAR_PERPETUAL:
            return super().stop_order_params(request)
        if not request.reduce_only or request.position_side is None:
            raise ExchangeRejected("Binance USD-M protective stops must reduce a position")
        # CCXT uses this flag to route conditional USD-M orders through Binance's
        # current Algo Order API (POST /fapi/v1/algoOrder). Without it, a
        # stopPrice is translated to the retired conditional-order endpoint.
        return {
            "reduceOnly": True,
            "workingType": "MARK_PRICE",
            "isAlgoOrder": True,
        }

    def market_order_params(self, request: MarketOrderRequest) -> dict[str, Any]:
        return {"reduceOnly": True} if request.reduce_only else {}


def _optional_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ExchangeError("Binance USD-M returned a malformed numeric position field") from None
    if not parsed.is_finite():
        raise ExchangeError("Binance USD-M returned a non-finite position field")
    return parsed


def _positive_decimal(value: Any) -> Decimal | None:
    parsed = _optional_decimal(value)
    return parsed if parsed is not None and parsed > 0 else None


def _optional_integer(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ExchangeError("Binance USD-M returned a malformed leverage field") from None
