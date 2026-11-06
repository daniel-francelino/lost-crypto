"""Trend detector against real PostgreSQL: registry API, worker pass, stored readings."""

import math
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from harness import START, Env, PathSource
from sqlalchemy import text

from modules.market_data.domain.models import Candle, Timeframe

pytestmark = pytest.mark.integration

SYMBOL = "TRD/USDT"
BASE = "/api/v1/trends"


class ClimbingSource(PathSource):
    """Every timeframe: a steady climb with slow waves (a trend with pullbacks)."""

    @staticmethod
    def _price(moment: datetime) -> Decimal:
        hours = (moment - START).total_seconds() / 3600 + 24 * 400
        return Decimal(f"{100 + 0.05 * hours + 30 * math.sin(2 * math.pi * hours / 288):.4f}")

    async def fetch_candles(
        self, symbol: str, timeframe: Timeframe, since: datetime, limit: int
    ) -> list[Candle]:
        out: list[Candle] = []
        t = since
        while len(out) < limit and t <= self.clock.now():
            opened, closed = self._price(t), self._price(t + timeframe.delta)
            high, low = max(opened, closed) + Decimal("0.5"), min(opened, closed) - Decimal("0.5")
            out.append(Candle(symbol, timeframe, t, opened, high, low, closed, Decimal(1)))
            t += timeframe.delta
        return out


async def _forget(env: Env) -> None:
    async with env.containers[0].engine.begin() as conn:
        for table in ("trend_readings", "trend_states", "trend_symbols", "candles"):
            await conn.execute(text(f"DELETE FROM {table} WHERE symbol = :s"), {"s": SYMBOL})


async def test_a_registered_symbol_is_followed_hour_after_hour(env: Env) -> None:
    runner = env.make_runner(ClimbingSource)
    try:
        # The API container talks to the real exchange to validate a pair, so the test registers
        # it through the worker's service (simulated exchange); the API reads and switches it.
        symbol_id = str((await env.containers[0].trends.add_symbol("binance", SYMBOL)).id)

        await runner.run_once()  # backfills history and classifies the four timeframes

        latest = (await env.http.get(BASE, params={"symbol": SYMBOL})).json()
        (item,) = latest
        readings = {r["frame"]: r for r in item["readings"]}
        assert set(readings) == {"1h", "4h", "1d", "1w"}
        assert readings["1d"]["trend"] == "bullish"
        assert set(readings["1d"]["checks"]) == {"distance", "slope", "adx", "structure"}
        assert Decimal(readings["1d"]["ema_fast"]) > Decimal(readings["1d"]["ema_slow"])

        hourly = (
            await env.http.get(
                f"{BASE}/history",
                params={"exchange": "binance", "symbol": SYMBOL, "frame": "1h", "limit": 3},
            )
        ).json()
        assert [h["bar_open_time"] for h in hourly] == sorted(
            (h["bar_open_time"] for h in hourly), reverse=True
        )
        newest = datetime.fromisoformat(hourly[0]["bar_open_time"])

        env.clock.advance(hours=1)
        await runner.run_once()  # a new hourly bar closed: exactly one new 1h reading
        again = (
            await env.http.get(
                f"{BASE}/history",
                params={"exchange": "binance", "symbol": SYMBOL, "frame": "1h", "limit": 1},
            )
        ).json()
        assert datetime.fromisoformat(again[0]["bar_open_time"]) == newest + timedelta(hours=1)

        # nothing closed: a pass does not write anything
        async with env.containers[0].engine.connect() as conn:
            before = (
                await conn.execute(
                    text("SELECT count(*) FROM trend_readings WHERE symbol=:s"), {"s": SYMBOL}
                )
            ).scalar_one()
        env.clock.advance(minutes=10)
        await runner.run_once()
        async with env.containers[0].engine.connect() as conn:
            after = (
                await conn.execute(
                    text("SELECT count(*) FROM trend_readings WHERE symbol=:s"), {"s": SYMBOL}
                )
            ).scalar_one()
        assert after == before

        off = await env.http.post(f"{BASE}/symbols/{symbol_id}/deactivate")
        assert off.status_code == 200 and off.json()["active"] is False
        assert (await env.http.get(BASE)).json() == []  # only active symbols by default
        assert (await env.http.post(f"{BASE}/symbols/{symbol_id}/activate")).json()[
            "active"
        ] is True
    finally:
        await _forget(env)
