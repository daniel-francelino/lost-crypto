from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from modules.market_data.domain.trend import Trend, TrendFrame, TrendReading, TrendSettings


@dataclass(frozen=True, slots=True)
class WatchedSymbol:
    """A pair whose trend the detector keeps up to date (the "symbol registry")."""

    id: UUID
    exchange: str
    symbol: str
    active: bool
    created_at: datetime


@dataclass(frozen=True, slots=True)
class TrendRecord:
    """What the detector concluded at the close of one bar of one timeframe."""

    exchange: str
    symbol: str
    frame: TrendFrame
    bar_open_time: datetime  # the bar this reading belongs to (UTC); its close is open + frame
    trend: Trend
    previous_trend: Trend | None
    close: Decimal | None
    ema_fast: Decimal | None
    ema_slow: Decimal | None
    ema_distance_pct: Decimal | None
    slow_slope_pct: Decimal | None
    adx: Decimal | None
    atr: Decimal | None
    structure: Trend | None
    checks: dict[str, bool | None]
    confirmed: bool
    computed_at: datetime


@dataclass(frozen=True, slots=True)
class FrameProgress:
    """Where the detector stopped for one (symbol, timeframe): the last bar it processed and the
    indicator state to resume from, so a bar is never processed twice and the EMAs stay
    continuous. ``settings_key`` changes when the EMA lengths do, which restarts the frame."""

    frame: TrendFrame
    last_bar_open_time: datetime
    settings_key: str
    state: dict[str, Any]


def settings_key(settings: TrendSettings) -> str:
    return (
        f"{settings.fast}/{settings.slow}/{settings.min_distance_pct}/{settings.adx_min}/"
        f"{settings.adx_period}/{settings.slope_bars}/{settings.swing_window}"
    )


def record_from_reading(
    exchange: str, symbol: str, reading: TrendReading, computed_at: datetime
) -> TrendRecord | None:
    """The record of a reading, or None while the frame is still warming up."""
    if reading.trend is None or reading.bar_open_time is None:
        return None
    return TrendRecord(
        exchange,
        symbol,
        reading.frame,
        reading.bar_open_time,
        reading.trend,
        reading.previous_trend,
        reading.close,
        reading.ema_fast,
        reading.ema_slow,
        reading.ema_distance_pct,
        reading.slow_slope_pct,
        reading.adx,
        reading.atr,
        reading.structure,
        dict(reading.checks),
        reading.confirmed,
        computed_at,
    )


def normalize_symbol(exchange: str, symbol: str) -> str:
    """``BTCUSDT`` / ``btc/usdt`` -> the exchange's unified symbol (``BTC/USDT:USDT`` on a
    USD-M perpetual exchange, ``BTC/USDT`` on spot). Already unified symbols pass unchanged."""
    text = symbol.strip().upper()
    if "/" in text:
        return text
    if text.endswith("USDT") and len(text) > 4:
        base = text[:-4]
        return f"{base}/USDT:USDT" if "usdm" in exchange else f"{base}/USDT"
    return text
