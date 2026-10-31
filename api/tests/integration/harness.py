"""Shared integration harness: real API + PostgreSQL, simulated time and exchange."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

import httpx
from sqlalchemy import text

from container import Container, JobRunner
from factories import MARKET
from modules.market_data.domain.models import Candle, MarketInfo, Timeframe
from simulated_exchange import SimulatedExchange

START = datetime(2024, 1, 1, tzinfo=UTC)
SYMBOL = "TST/USDT"
# Hourly closes by hour offset from START. With an EMA 2/3 bot: flat 100, a cross up at hour 23
# (BUY), then 120/130, and a cross down at hour 26 (SELL).
PATH = {23: 110, 24: 120, 25: 130, 26: 100, 27: 80, 28: 60}


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self.current = now

    def now(self) -> datetime:
        return self.current

    def advance(self, **kwargs: float) -> None:
        self.current += timedelta(**kwargs)


class PathSource:
    """Deterministic market: the close of the candle opening at START + h hours is path[h]."""

    def __init__(self, clock: FakeClock, path: dict[int, int] | None = None) -> None:
        self.clock = clock
        self.path = path or PATH

    def price(self, hour: int) -> Decimal:
        if hour in self.path:
            return Decimal(self.path[hour])
        return Decimal(self.path[max(self.path)] if hour > max(self.path) else 100)

    async def fetch_candles(
        self, symbol: str, timeframe: Timeframe, since: datetime, limit: int
    ) -> list[Candle]:
        out: list[Candle] = []
        t = since
        while len(out) < limit and t <= self.clock.now():  # includes the in-progress candle
            close = self.price(int((t - START).total_seconds() // 3600))
            out.append(Candle(symbol, timeframe, t, close, close, close, close, Decimal(1)))
            t += timeframe.delta
        return out

    async def fetch_market_info(self, symbol: str) -> MarketInfo:
        return MARKET


class BrokenSource(PathSource):
    async def fetch_candles(self, *args: Any, **kwargs: Any) -> list[Candle]:
        raise ConnectionError("exchange unreachable")


RunnerFactory = Callable[..., JobRunner]


@dataclass
class Env:
    http: httpx.AsyncClient
    clock: FakeClock
    make_runner: RunnerFactory
    containers: list[Container] = field(default_factory=list)

    async def create_bot(self, **overrides: Any) -> str:
        body = {
            "name": f"itest-{uuid4().hex[:8]}",
            "strategy_type": "ema_crossover",
            "strategy_params": {"fast_period": 2, "slow_period": 3},
            "symbol": SYMBOL,
            "timeframe": "1h",
            "initial_capital": "1000",
            "risk": {"max_daily_loss_pct": None},
            **overrides,
        }
        resp = await self.http.post("/api/v1/bots", json=body)
        assert resp.status_code == 201, resp.text
        return str(resp.json()["id"])

    async def command(self, bot_id: str, name: str) -> httpx.Response:
        return await self.http.post(f"/api/v1/bots/{bot_id}/{name}")

    async def bot(self, bot_id: str) -> dict[str, Any]:
        return dict((await self.http.get(f"/api/v1/bots/{bot_id}")).json())

    async def orders(self, bot_id: str) -> list[dict[str, Any]]:
        resp = await self.http.get(f"/api/v1/bots/{bot_id}/orders")
        return list(reversed(resp.json()))  # oldest first

    async def signals(self, bot_id: str) -> list[dict[str, Any]]:
        return list(reversed((await self.http.get(f"/api/v1/bots/{bot_id}/signals")).json()))

    async def audit_types(self, bot_id: str) -> set[str]:
        resp = await self.http.get("/api/v1/audit-events", params={"bot_id": bot_id})
        return {e["event_type"] for e in resp.json()}

    async def run_until(self, runner: JobRunner, hours_after_start: int) -> None:
        """Advance the clock hour by hour (5s after each close) running the worker each step."""
        target = START + timedelta(hours=hours_after_start, seconds=5)
        while self.clock.now() < target:
            self.clock.advance(hours=1)
            await runner.run_once()


async def cleanup(container: Container) -> None:
    async with container.engine.begin() as conn:
        bots = "(SELECT id FROM bots WHERE name LIKE 'itest-%')"
        statements = [
            "DELETE FROM order_fills WHERE order_id IN "
            f"(SELECT id FROM orders WHERE bot_id IN {bots})",
            f"DELETE FROM orders WHERE bot_id IN {bots}",
            f"DELETE FROM trading_signals WHERE bot_id IN {bots}",
            f"DELETE FROM portfolio_snapshots WHERE bot_id IN {bots}",
            f"DELETE FROM bot_portfolios WHERE bot_id IN {bots}",
            f"DELETE FROM trading_sessions WHERE bot_id IN {bots}",
            f"DELETE FROM audit_events WHERE bot_id IN {bots}",
            "DELETE FROM bots WHERE name LIKE 'itest-%'",
            "DELETE FROM reconciliation_runs WHERE connection_id IN "
            "(SELECT id FROM exchange_connections WHERE label LIKE 'itest-%')",
            "DELETE FROM exchange_connections WHERE label LIKE 'itest-%'",
            "DELETE FROM system_flags WHERE key IN ('kill_switch', 'worker_heartbeat')",
        ]
        for statement in statements:
            await conn.execute(text(statement))


API_TOKEN = "itest-token"
API_KEY = "itest-api-key-ABCD1234"
API_SECRET = "itest-api-secret-WXYZ9876"


@dataclass
class TestnetEnv(Env):
    """Env plus a simulated exchange account, an authenticated API and a vault."""

    __test__ = False  # not a pytest test class

    sim: SimulatedExchange | None = None
    anonymous: httpx.AsyncClient | None = None  # same API, no token
    api_container: Container | None = None

    async def create_connection(self, label: str | None = None) -> str:
        body = {
            "exchange": "binance",
            "environment": "testnet",
            "label": label or f"itest-{uuid4().hex[:6]}",
            "api_key": API_KEY,
            "api_secret": API_SECRET,
        }
        resp = await self.http.post("/api/v1/exchange-connections", json=body)
        assert resp.status_code == 201, resp.text
        return str(resp.json()["id"])

    async def create_testnet_bot(self, connection_id: str, **overrides: Any) -> str:
        return await self.create_bot(mode="testnet", connection_id=connection_id, **overrides)

    async def portfolio(self, bot_id: str) -> dict[str, Any]:
        return dict((await self.http.get(f"/api/v1/bots/{bot_id}/portfolio")).json())

    async def reconciliations(self, connection_id: str) -> list[tuple[str, dict[str, Any]]]:
        assert self.api_container is not None
        async with self.api_container.engine.connect() as conn:
            rows = await conn.execute(
                text(
                    "SELECT status, details FROM reconciliation_runs "
                    "WHERE connection_id = :c ORDER BY started_at, id"
                ),
                {"c": connection_id},
            )
            return [(r[0], r[1]) for r in rows]
