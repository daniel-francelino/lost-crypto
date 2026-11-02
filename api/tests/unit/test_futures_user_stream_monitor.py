import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest

from modules.trading.application.futures_user_stream import FuturesUserStreamMonitor


class _Exchange:
    capabilities = SimpleNamespace(exchange_id="binance-usdm")

    def __init__(self) -> None:
        self.calls = 0
        self.reconnected = asyncio.Event()

    async def stream_user_events(self):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("simulated socket gap")
        self.reconnected.set()
        await asyncio.Event().wait()
        if False:
            yield {}


class _Resolver:
    def __init__(self, exchange: _Exchange) -> None:
        self.exchange = exchange

    async def exchange_for(self, connection_id):
        return self.exchange


class _Reconciler:
    def __init__(self) -> None:
        self.reconciliations = 0

    async def resolve_pending(self, connection_id) -> None:
        return None

    async def reconcile_connection(self, connection_id) -> None:
        self.reconciliations += 1
        if self.reconciliations == 2:
            raise RuntimeError("simulated REST outage")


@pytest.mark.asyncio
async def test_stream_reconnect_waits_for_pause_and_successful_rest_reconciliation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_wait(_seconds: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", no_wait)
    exchange = _Exchange()
    reconciler = _Reconciler()
    pauses: list[tuple[str, str]] = []
    monitor = FuturesUserStreamMonitor(
        stores=None,  # type: ignore[arg-type]
        resolver=_Resolver(exchange),  # type: ignore[arg-type]
        reconciler=reconciler,  # type: ignore[arg-type]
        clock=None,  # type: ignore[arg-type]
    )

    async def record_pause(connection_id, event_type: str, reason: str) -> None:
        pauses.append((event_type, reason))

    monkeypatch.setattr(monitor, "_pause_connection", record_pause)
    task = asyncio.create_task(monitor._run_connection(uuid4()))
    try:
        await asyncio.wait_for(exchange.reconnected.wait(), timeout=1)
        assert exchange.calls == 2
        # Initial snapshot, successful post-gap recovery snapshot, and pre-reconnect snapshot.
        assert reconciler.reconciliations == 4
        assert len(pauses) == 2
        assert all(event == "risk.futures_user_stream_disconnected" for event, _ in pauses)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
