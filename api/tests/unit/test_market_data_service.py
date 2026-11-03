from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

from sqlalchemy.dialects import postgresql

from modules.exchanges.domain.models import TradingProduct
from modules.market_data.application.service import MarketDataService
from modules.market_data.domain.models import Candle, FundingRate, Timeframe
from modules.market_data.infrastructure.orm import CandleRow, PerpetualMarkCandleRow
from modules.market_data.infrastructure.repository import (
    SqlAlchemyCandleRepository,
    SqlAlchemyPerpetualDataRepository,
)


async def test_perpetual_import_includes_funding_at_the_requested_end_boundary() -> None:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    end = start + timedelta(hours=1)
    symbol = "BTC/USDT:USDT"
    mark = Candle(
        symbol=symbol,
        timeframe=Timeframe.H1,
        open_time=start,
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100"),
        volume=Decimal("1"),
    )
    settlement = FundingRate(
        symbol=symbol,
        rate=Decimal("0.001"),
        funding_time=end,
        mark_price=Decimal("100"),
    )

    class Source:
        async def fetch_mark_candles(
            self, _symbol: str, _timeframe: Timeframe, since: datetime, _limit: int
        ) -> list[Candle]:
            return [mark] if since <= start else []

        async def fetch_funding_rates(
            self, _symbol: str, since: datetime, _limit: int
        ) -> list[FundingRate]:
            return [settlement] if since <= end else []

    class Registry:
        def require(self, _exchange: str, _timeframe: Timeframe) -> Any:
            return SimpleNamespace(
                capabilities=SimpleNamespace(products={TradingProduct.LINEAR_PERPETUAL})
            )

        def exchange(self, _exchange: str) -> Source:
            return Source()

    imported_marks: list[Candle] = []
    imported_funding: list[FundingRate] = []

    class PerpetualData:
        async def upsert_mark_candles(self, _exchange: str, candles: list[Candle]) -> int:
            imported_marks.extend(candles)
            return len(candles)

        async def upsert_funding_rates(self, _exchange: str, rates: list[FundingRate]) -> int:
            imported_funding.extend(rates)
            return len(rates)

    store = SimpleNamespace(perpetual_data=PerpetualData(), commit=_commit)

    @asynccontextmanager
    async def stores() -> Any:
        yield store

    service = MarketDataService(stores, Registry(), None, None)  # type: ignore[arg-type]

    result = await service.import_perpetual_auxiliary(
        "binance-usdm", symbol, Timeframe.H1, start, end
    )

    assert result == (1, 1)
    assert imported_marks == [mark]
    assert imported_funding == [settlement]


async def _commit() -> None:
    return None


async def test_funding_repository_uses_an_inclusive_upper_time_bound() -> None:
    class Session:
        statement: Any = None

        async def execute(self, statement: Any) -> Any:
            self.statement = statement
            return SimpleNamespace(scalars=lambda: [])

    session = Session()
    repository = SqlAlchemyPerpetualDataRepository(session)  # type: ignore[arg-type]
    start = datetime(2025, 1, 1, tzinfo=UTC)
    end = start + timedelta(hours=1)

    await repository.get_funding_rates("binance-usdm", "BTC/USDT:USDT", start, end)

    sql = str(session.statement.compile(dialect=postgresql.dialect()))
    assert "perpetual_funding_rates.funding_time <=" in sql


async def test_spot_and_usdm_candles_have_separate_persistence_identities() -> None:
    # Both series represent BTC quoted in USDT, but come from different markets and must not
    # overwrite each other if a caller ever requests the same display symbol for both products.
    assert set(CandleRow.__table__.primary_key.columns.keys()) == {
        "exchange",
        "symbol",
        "timeframe",
        "open_time",
    }
    assert set(PerpetualMarkCandleRow.__table__.primary_key.columns.keys()) == {
        "exchange",
        "symbol",
        "timeframe",
        "open_time",
    }

    class Session:
        def __init__(self) -> None:
            self.statements: list[Any] = []

        async def execute(self, statement: Any) -> Any:
            self.statements.append(statement)
            return SimpleNamespace(scalars=lambda: [])

    session = Session()
    candles = SqlAlchemyCandleRepository(session)  # type: ignore[arg-type]
    start = datetime(2025, 1, 1, tzinfo=UTC)
    end = start + timedelta(hours=1)
    await candles.get_range("binance", "BTC/USDT", Timeframe.H1, start, end)
    await candles.get_range("binance-usdm", "BTC/USDT:USDT", Timeframe.H1, start, end)

    compiled = [statement.compile(dialect=postgresql.dialect()) for statement in session.statements]
    exchanges = [value for query in compiled for value in query.params.values()]
    assert "binance" in exchanges
    assert "binance-usdm" in exchanges
