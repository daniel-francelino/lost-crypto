from datetime import UTC, datetime
from uuid import uuid4

from modules.exchanges.application.connections import ConnectionResolver
from modules.exchanges.application.ports import Balance
from modules.exchanges.domain.connections import (
    ConnectionStatus,
    Environment,
    ExchangeConnection,
)

NOW = datetime(2026, 11, 3, tzinfo=UTC)


class _Clock:
    def now(self) -> datetime:
        return NOW


class _Connections:
    def __init__(self, connection: ExchangeConnection) -> None:
        self.connection = connection
        self.check: dict[str, object] | None = None

    async def get(self, connection_id):
        return self.connection if connection_id == self.connection.id else None

    async def record_check(self, connection_id, **kwargs) -> None:
        assert connection_id == self.connection.id
        self.check = kwargs
        self.connection.last_checked_at = kwargs["checked_at"]
        self.connection.permissions = kwargs["permissions"]
        self.connection.status_reason = kwargs["reason"]
        self.connection.permission_warning = kwargs["warning"]


class _Store:
    def __init__(self, connection: ExchangeConnection) -> None:
        self.connections = _Connections(connection)
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class _StoreContext:
    def __init__(self, store: _Store) -> None:
        self.store = store

    async def __aenter__(self) -> _Store:
        return self.store

    async def __aexit__(self, *args) -> None:
        return None


class _DemoExchange:
    def __init__(self) -> None:
        self.balance_reads = 0
        self.permission_reads = 0

    async def fetch_balances(self) -> dict[str, Balance]:
        self.balance_reads += 1
        return {"USDT": Balance("USDT", 100, 0)}

    async def fetch_api_permissions(self):
        self.permission_reads += 1
        raise AssertionError("Demo credentials must not call the live SAPI permissions endpoint")


class _Resolver(ConnectionResolver):
    def __init__(self, store: _Store, exchange: _DemoExchange) -> None:
        self._stores = lambda: _StoreContext(store)
        self._clock = _Clock()
        self.exchange = exchange

    async def exchange_for(self, connection_id, *, allow_pending: bool = False):
        assert connection_id is not None
        return self.exchange


async def test_recheck_demo_connection_uses_only_a_read_only_account_call() -> None:
    connection = ExchangeConnection(
        id=uuid4(),
        exchange="binance-usdm",
        environment=Environment.DEMO,
        label="USD-M Demo",
        api_key_hint="1234",
        status=ConnectionStatus.ACTIVE,
        created_at=NOW,
        verified_at=NOW,
    )
    store = _Store(connection)
    exchange = _DemoExchange()
    resolver = _Resolver(store, exchange)

    updated = await resolver.recheck(connection.id, require_ip_restriction=True)

    assert updated is connection
    assert exchange.balance_reads == 1
    assert exchange.permission_reads == 0
    assert connection.permissions is None
    assert connection.permission_warning is None
    assert connection.last_checked_at == NOW
    assert store.commits == 1
