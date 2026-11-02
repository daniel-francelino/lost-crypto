from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from modules.market_data.domain.models import Candle, FundingRate, MarkPrice, Timeframe


class PerpetualMarketDataSource(Protocol):
    """Supplemental data required for linear perpetual accounting and backtests."""

    async def fetch_mark_price(self, symbol: str) -> MarkPrice: ...

    async def fetch_mark_candles(
        self, symbol: str, timeframe: Timeframe, since: datetime, limit: int
    ) -> list[Candle]: ...

    async def fetch_funding_rates(
        self, symbol: str, since: datetime, limit: int
    ) -> list[FundingRate]: ...


class PerpetualDataRepository(Protocol):
    async def upsert_mark_candles(self, exchange: str, candles: Sequence[Candle]) -> int: ...

    async def get_mark_candles(
        self, exchange: str, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[Candle]: ...

    async def upsert_funding_rates(self, exchange: str, rates: Sequence[FundingRate]) -> int: ...

    async def get_funding_rates(
        self, exchange: str, symbol: str, start: datetime, end: datetime
    ) -> list[FundingRate]: ...
