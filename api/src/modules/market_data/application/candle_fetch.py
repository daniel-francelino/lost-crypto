"""Fetch a stretch of candles that may be longer than one exchange page."""

from datetime import datetime

from modules.market_data.application.ports import MarketDataSource
from modules.market_data.domain.models import Candle, Timeframe

PAGE_SIZE = 1000
MAX_PAGES = 8


async def fetch_candles_since(
    source: MarketDataSource,
    symbol: str,
    timeframe: Timeframe,
    since: datetime,
    until: datetime,
) -> list[Candle]:
    """Candles opening at or after ``since``, page after page until ``until`` is reached.

    A short page means the exchange has nothing more; a page that does not move the cursor
    forward stops the loop, so a misbehaving source can never spin forever."""
    candles: list[Candle] = []
    cursor = since
    for _ in range(MAX_PAGES):
        page = await source.fetch_candles(symbol, timeframe, cursor, PAGE_SIZE)
        candles.extend(page)
        if len(page) < PAGE_SIZE:
            break
        following = max(c.open_time for c in page) + timeframe.delta
        if following <= cursor or following >= until:
            break
        cursor = following
    return candles
