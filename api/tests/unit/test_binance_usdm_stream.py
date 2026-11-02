import asyncio
import json
from types import SimpleNamespace
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest

from modules.exchanges.domain.connections import Credentials
from modules.exchanges.errors import ExchangeError, ExchangeRejected
from modules.exchanges.infrastructure import binance_usdm
from modules.exchanges.infrastructure.binance_usdm import BinanceUsdmExchange


class _WebSocket:
    def __init__(self, events: list[dict[str, Any]]) -> None:
        self._events = iter(events)

    async def __aenter__(self) -> "_WebSocket":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def receive(self) -> SimpleNamespace:
        try:
            event = next(self._events)
        except StopIteration:
            return SimpleNamespace(type=SimpleNamespace(name="CLOSED"), data="")
        return SimpleNamespace(type=SimpleNamespace(name="TEXT"), data=json.dumps(event))


class _Session:
    closed = False

    def __init__(self, events: list[dict[str, Any]]) -> None:
        self.websocket = _WebSocket(events)
        self.url: str | None = None
        self.options: dict[str, Any] = {}

    def ws_connect(self, url: str, **options: Any) -> _WebSocket:
        self.url = url
        self.options = options
        return self.websocket


class _Client:
    def __init__(self, events: list[dict[str, Any]]) -> None:
        self.session = _Session(events)
        self.last_response_headers: dict[str, str] = {}
        self.started = 0
        self.kept_alive = 0
        self.closed = 0
        self.keepalive_event = asyncio.Event()

    async def fetch_time(self) -> int:
        return 1

    async def fapiPrivatePostListenKey(self) -> dict[str, str]:
        self.started += 1
        return {"listenKey": "test-listen-key"}

    async def fapiPrivatePutListenKey(self, params: dict[str, str]) -> dict[str, str]:
        assert params == {"listenKey": "test-listen-key"}
        self.kept_alive += 1
        self.keepalive_event.set()
        return {"listenKey": "test-listen-key"}

    async def fapiPrivateDeleteListenKey(self, params: dict[str, str]) -> dict[str, object]:
        assert params == {"listenKey": "test-listen-key"}
        self.closed += 1
        return {}


def _exchange(events: list[dict[str, Any]]) -> tuple[BinanceUsdmExchange, _Client]:
    client = _Client(events)
    exchange = BinanceUsdmExchange(
        client,
        credentials=Credentials("demo-api-key", "demo-api-secret"),
        demo=True,
    )
    return exchange, client


async def test_user_stream_uses_demo_private_route_and_yields_wrapped_events() -> None:
    exchange, client = _exchange(
        [{"subscriptionId": "sub-1", "event": {"e": "ACCOUNT_UPDATE", "E": 123}}]
    )
    # End the stream with the documented expiry event so the adapter returns for recovery.
    client.session.websocket._events = iter(
        [
            {"subscriptionId": "sub-1", "event": {"e": "ACCOUNT_UPDATE", "E": 123}},
            {"e": "listenKeyExpired", "E": 124},
        ]
    )

    events = [event async for event in exchange.stream_user_events()]

    assert events == [{"e": "ACCOUNT_UPDATE", "E": 123}, {"e": "listenKeyExpired", "E": 124}]
    assert client.started == 1
    assert client.closed == 1
    parsed = urlparse(client.session.url or "")
    assert parsed.netloc == "demo-fstream.binance.com"
    assert parsed.path == "/private/ws"
    assert parse_qs(parsed.query)["listenKey"] == ["test-listen-key"]
    assert "ALGO_UPDATE" in parse_qs(parsed.query)["events"][0]
    assert client.session.options == {"heartbeat": 30}


async def test_user_stream_disconnect_raises_so_worker_can_reconcile_and_reconnect() -> None:
    exchange, client = _exchange([])

    with pytest.raises(ExchangeError, match="disconnected"):
        _ = [event async for event in exchange.stream_user_events()]
    assert client.closed == 1


async def test_user_stream_renews_key_while_events_are_continuously_arriving(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exchange, client = _exchange([])
    monkeypatch.setattr(binance_usdm, "USER_STREAM_KEEPALIVE_SECONDS", 0.001)

    class ActiveWebSocket(_WebSocket):
        def __init__(self) -> None:
            super().__init__([])
            self.sent_event = False

        async def receive(self) -> SimpleNamespace:
            if not self.sent_event:
                await client.keepalive_event.wait()
                self.sent_event = True
                return SimpleNamespace(
                    type=SimpleNamespace(name="TEXT"),
                    data=json.dumps({"e": "ACCOUNT_UPDATE", "E": 123}),
                )
            return SimpleNamespace(
                type=SimpleNamespace(name="TEXT"),
                data=json.dumps({"e": "listenKeyExpired", "E": 124}),
            )

    client.session.websocket = ActiveWebSocket()
    events = [event async for event in exchange.stream_user_events()]

    assert events == [
        {"e": "ACCOUNT_UPDATE", "E": 123},
        {"e": "listenKeyExpired", "E": 124},
    ]
    assert client.kept_alive == 1
    assert client.closed == 1


async def test_user_stream_refuses_non_demo_credentials() -> None:
    client = _Client([])
    exchange = BinanceUsdmExchange(client, credentials=Credentials("api-key-1234", "secret-5678"))

    with pytest.raises(ExchangeRejected, match="only for Binance Demo"):
        _ = [event async for event in exchange.stream_user_events()]
