from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request, status
from pydantic import BaseModel, Field

from container import Container
from modules.market_data.domain.trend import Trend, TrendFrame
from modules.trends.application.service import AvailablePage, AvailableSort, SymbolTrends
from modules.trends.domain.models import TrendRecord, WatchedSymbol

router = APIRouter(prefix="/trends", tags=["trends"])


class SymbolCreate(BaseModel):
    exchange: str = "binance-usdm"
    symbol: str = Field(
        min_length=3,
        max_length=30,
        description="BTCUSDT or BTC/USDT:USDT; the exchange must list it",
    )


class SymbolOut(BaseModel):
    id: UUID
    exchange: str
    symbol: str
    active: bool
    created_at: datetime


class AvailableSymbolOut(BaseModel):
    symbol: str
    base: str
    quote_volume: Decimal | None = Field(description="Traded volume of the last 24 h, in USDT")
    registry_id: UUID | None = Field(description="Set when the pair is in the registry")
    active: bool = Field(description="In the registry and switched on")


class AvailablePageOut(BaseModel):
    items: list[AvailableSymbolOut]
    total: int = Field(description="Pairs matching the search, over all pages")


class ReadingOut(BaseModel):
    frame: TrendFrame
    bar_open_time: datetime = Field(description="Start of the bar (UTC); it closed one bar later")
    trend: Trend
    previous_trend: Trend | None
    confirmed: bool = Field(description="A directional trend that passes all four checks")
    checks: dict[str, bool | None] = Field(
        description="distance / slope / adx / structure; null = not enough data yet"
    )
    close: Decimal | None
    ema_fast: Decimal | None
    ema_slow: Decimal | None
    ema_distance_pct: Decimal | None
    slow_slope_pct: Decimal | None
    adx: Decimal | None
    atr: Decimal | None
    structure: Trend | None
    computed_at: datetime


class SymbolTrendsOut(BaseModel):
    symbol: SymbolOut
    readings: list[ReadingOut]


def _symbol(s: WatchedSymbol) -> SymbolOut:
    return SymbolOut(
        id=s.id, exchange=s.exchange, symbol=s.symbol, active=s.active, created_at=s.created_at
    )


def _reading(r: TrendRecord) -> ReadingOut:
    return ReadingOut(
        frame=r.frame,
        bar_open_time=r.bar_open_time,
        trend=r.trend,
        previous_trend=r.previous_trend,
        confirmed=r.confirmed,
        checks=r.checks,
        close=r.close,
        ema_fast=r.ema_fast,
        ema_slow=r.ema_slow,
        ema_distance_pct=r.ema_distance_pct,
        slow_slope_pct=r.slow_slope_pct,
        adx=r.adx,
        atr=r.atr,
        structure=r.structure,
        computed_at=r.computed_at,
    )


def _out(item: SymbolTrends) -> SymbolTrendsOut:
    return SymbolTrendsOut(
        symbol=_symbol(item.symbol), readings=[_reading(r) for r in item.readings]
    )


def _container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


@router.get("/symbols", response_model=list[SymbolOut])
async def list_symbols(request: Request) -> list[SymbolOut]:
    """The symbol registry: the pairs the trend detector follows."""
    return [_symbol(s) for s in await _container(request).trends.list_symbols()]


@router.post("/symbols", response_model=SymbolOut, status_code=status.HTTP_201_CREATED)
async def add_symbol(body: SymbolCreate, request: Request) -> SymbolOut:
    """Follow a pair. Its history is fetched by the worker at the next pass."""
    return _symbol(await _container(request).trends.add_symbol(body.exchange, body.symbol))


@router.post("/symbols/{symbol_id}/deactivate", response_model=SymbolOut)
async def deactivate_symbol(symbol_id: UUID, request: Request) -> SymbolOut:
    """Stop following a pair (its stored readings are kept)."""
    return _symbol(await _container(request).trends.set_active(symbol_id, False))


@router.post("/symbols/{symbol_id}/activate", response_model=SymbolOut)
async def activate_symbol(symbol_id: UUID, request: Request) -> SymbolOut:
    return _symbol(await _container(request).trends.set_active(symbol_id, True))


@router.get("/available", response_model=AvailablePageOut)
async def available_symbols(
    request: Request,
    exchange: str = "binance-usdm",
    q: Annotated[str, Query(max_length=20)] = "",
    sort: AvailableSort = AvailableSort.VOLUME,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AvailablePageOut:
    """The USDT pairs of the exchange to pick from, most traded first (or by name), paged."""
    page: AvailablePage = await _container(request).trends.available(
        exchange, q, sort, limit, offset
    )
    return AvailablePageOut(
        items=[
            AvailableSymbolOut(
                symbol=i.symbol,
                base=i.base,
                quote_volume=i.quote_volume,
                registry_id=i.registry_id,
                active=i.active,
            )
            for i in page.items
        ],
        total=page.total,
    )


@router.get("", response_model=list[SymbolTrendsOut])
async def latest_trends(
    request: Request, exchange: str | None = None, symbol: str | None = None
) -> list[SymbolTrendsOut]:
    """The newest reading of every timeframe (1w, 1d, 4h, 1h) of each followed pair."""
    items = await _container(request).trends.latest(exchange, symbol)
    return [_out(i) for i in items]


@router.get("/history", response_model=list[ReadingOut])
async def trend_history(
    request: Request,
    exchange: str,
    symbol: str,
    frame: TrendFrame,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    before: datetime | None = None,
) -> list[ReadingOut]:
    """Readings of one timeframe, newest first (page backwards with ``before``)."""
    rows = await _container(request).trends.history(exchange, symbol, frame, limit, before)
    return [_reading(r) for r in rows]
