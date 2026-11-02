"""Binance USDⓈ-M perpetual integration, isolated from the Binance Spot adapter."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from modules.exchanges.application.ports import MarketOrderRequest, StopOrderRequest, VenueOrder
from modules.exchanges.domain.connections import ApiPermissions
from modules.exchanges.domain.models import (
    ExchangeCapabilities,
    ExchangeProfile,
    FeeSchedule,
    MarginMode,
    OrderType,
    TradingProduct,
)
from modules.exchanges.errors import ExchangeRejected
from modules.exchanges.infrastructure.ccxt_exchange import CcxtExchange
from modules.market_data.domain.models import Candle, FundingRate, MarketInfo, MarkPrice, Timeframe

BINANCE_USDM_ID = "binance-usdm"
MAX_LEVERAGE = 10

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

    async def fetch_mark_price(self, symbol: str) -> MarkPrice:
        raw = await self._call(lambda: self._client.fetch_mark_price(symbol))
        return MarkPrice(
            symbol=symbol,
            price=Decimal(str(raw["mark"])),
            timestamp=datetime.fromtimestamp(int(raw["timestamp"]) / 1000, UTC),
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
            )
            for row in rows
            if row.get("fundingRate") is not None and row.get("timestamp") is not None
        ]

    async def fetch_api_permissions(self) -> ApiPermissions:
        self._require_authentication()
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
        permissions = await self.fetch_api_permissions()
        if not permissions.can_read or not permissions.can_trade_derivatives:
            raise ExchangeRejected("API key must have read and Binance Futures trading access")
        position_mode = await self._call(self._client.fetch_position_mode)
        if position_mode.get("hedged"):
            raise ExchangeRejected("Binance USD-M account must use one-way position mode")
        positions = await self._call(lambda: self._client.fetch_positions([symbol]))
        if any(Decimal(str(position.get("contracts") or 0)) != 0 for position in positions):
            raise ExchangeRejected(
                f"close the existing {symbol} futures position before starting this bot"
            )
        orders = await self.fetch_open_orders(symbol)
        if orders:
            raise ExchangeRejected(f"cancel existing {symbol} futures orders before starting")

        current_margin = await self._call(lambda: self._client.fetch_margin_mode(symbol))
        if current_margin.get("marginMode") != "isolated":
            await self._call(lambda: self._client.set_margin_mode("isolated", symbol))
        await self._call(lambda: self._client.set_leverage(leverage, symbol))

        configured_margin = await self._call(lambda: self._client.fetch_margin_mode(symbol))
        raw_leverage = (configured_margin.get("info") or {}).get("leverage")
        if configured_margin.get("marginMode") != "isolated":
            raise ExchangeRejected(f"Binance did not confirm isolated margin for {symbol}")
        if raw_leverage is None or int(raw_leverage) != leverage:
            raise ExchangeRejected(f"Binance did not confirm requested {leverage}x leverage")

        tiers = await self._call(lambda: self._client.fetch_leverage_tiers([symbol]))
        symbol_tiers = tiers.get(symbol, [])
        if not symbol_tiers or max(int(tier["maxLeverage"]) for tier in symbol_tiers) < leverage:
            raise ExchangeRejected(
                f"Binance leverage tiers do not support {leverage}x for {symbol}"
            )

    def stop_order_type(self, request: StopOrderRequest) -> str:
        if request.product is TradingProduct.LINEAR_PERPETUAL:
            return "market"  # CCXT translates stopPrice into Binance STOP_MARKET/algo order.
        return super().stop_order_type(request)

    def lookup_params(self, client_order_id: str) -> dict[str, Any]:
        if client_order_id.endswith("-sl"):
            # CCXT selects Binance's conditional algo-order endpoint from these fields.
            return {"clientAlgoId": client_order_id, "triggerPrice": "1"}
        return super().lookup_params(client_order_id)

    async def fetch_open_orders(self, symbol: str) -> list[VenueOrder]:
        standard = await super().fetch_open_orders(symbol)
        conditional = await self._call(
            lambda: self._client.fetch_open_orders(symbol, None, None, {"triggerPrice": "1"})
        )
        return [*standard, *conditional]

    def stop_order_params(self, request: StopOrderRequest) -> dict[str, Any]:
        if request.product is not TradingProduct.LINEAR_PERPETUAL:
            return super().stop_order_params(request)
        if not request.reduce_only or request.position_side is None:
            raise ExchangeRejected("Binance USD-M protective stops must reduce a position")
        return {"reduceOnly": True, "workingType": "MARK_PRICE"}

    def market_order_params(self, request: MarketOrderRequest) -> dict[str, Any]:
        return {"reduceOnly": True} if request.reduce_only else {}
