import json
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from datetime import datetime
from typing import Protocol
from uuid import UUID

from core.clock import Clock
from core.errors import ConflictError, DomainError, NotFoundError
from core.ids import IdGenerator
from core.security.vault import CredentialVault, VaultNotConfigured
from modules.audit.models import AuditEvent, AuditRepository
from modules.exchanges.application.exchange import Exchange
from modules.exchanges.application.registry import ExchangeRegistry
from modules.exchanges.domain.connections import (
    ConnectionStatus,
    Credentials,
    Environment,
    ExchangeConnection,
)


class ConnectionNotFound(NotFoundError):
    pass


class ConnectionLabelTaken(ConflictError):
    pass


class InvalidConnection(DomainError):
    pass


class ConnectionRepository(Protocol):
    async def add(self, connection: ExchangeConnection, sealed: bytes, key_id: str) -> bool:
        """Persist; False when (exchange, environment, label) already exists."""
        ...

    async def get(self, connection_id: UUID) -> ExchangeConnection | None: ...
    async def get_sealed(self, connection_id: UUID) -> bytes | None: ...
    async def list_connections(self) -> list[ExchangeConnection]: ...
    async def set_status(
        self, connection_id: UUID, status: ConnectionStatus, verified_at: datetime | None
    ) -> None: ...


class ConnectionStore(Protocol):
    @property
    def connections(self) -> ConnectionRepository: ...
    @property
    def audit(self) -> AuditRepository: ...

    async def commit(self) -> None: ...


ConnectionStoreFactory = Callable[[], AbstractAsyncContextManager[ConnectionStore]]


class ConnectionService:
    """API side: register and manage connections. Accepts secrets, stores them encrypted, and
    never returns or logs them."""

    def __init__(
        self,
        stores: ConnectionStoreFactory,
        vault: CredentialVault | None,
        exchanges: ExchangeRegistry,
        clock: Clock,
        ids: IdGenerator,
    ) -> None:
        self._stores = stores
        self._vault = vault
        self._exchanges = exchanges
        self._clock = clock
        self._ids = ids

    async def create(
        self,
        exchange: str,
        environment: Environment,
        label: str,
        credentials: Credentials,
    ) -> ExchangeConnection:
        if self._vault is None:
            raise VaultNotConfigured("CREDENTIAL_MASTER_KEYS is not set")
        profile = self._exchanges.profile(exchange)
        if environment is Environment.LIVE:
            raise InvalidConnection("live connections are not available yet (testnet only)")
        if not profile.capabilities.has_testnet:
            raise InvalidConnection(f"{exchange} has no testnet")
        if len(credentials.api_key) < 8 or len(credentials.api_secret) < 8:
            raise InvalidConnection("api_key and api_secret look too short to be real")

        connection = ExchangeConnection(
            id=self._ids.new_id(),
            exchange=exchange,
            environment=environment,
            label=label,
            api_key_hint=credentials.api_key[-4:],
            status=ConnectionStatus.ACTIVE,
            created_at=self._clock.now(),
        )
        sealed = self._vault.seal(
            json.dumps({"api_key": credentials.api_key, "api_secret": credentials.api_secret})
        )
        async with self._stores() as store:
            if not await store.connections.add(connection, sealed, self._vault.key_id):
                raise ConnectionLabelTaken(
                    f"a {exchange} {environment.value} connection named {label!r} already exists"
                )
            await store.audit.add(
                AuditEvent(
                    "connection.created",
                    "connection",
                    str(connection.id),
                    actor="api",
                    payload={
                        "exchange": exchange,
                        "environment": environment.value,
                        "label": label,
                        "api_key_hint": connection.api_key_hint,
                    },
                )
            )
            await store.commit()
        return connection

    async def get(self, connection_id: UUID) -> ExchangeConnection:
        async with self._stores() as store:
            connection = await store.connections.get(connection_id)
        if connection is None:
            raise ConnectionNotFound(str(connection_id))
        return connection

    async def list_connections(self) -> list[ExchangeConnection]:
        async with self._stores() as store:
            return await store.connections.list_connections()

    async def disable(self, connection_id: UUID) -> ExchangeConnection:
        connection = await self.get(connection_id)
        async with self._stores() as store:
            await store.connections.set_status(
                connection_id, ConnectionStatus.DISABLED, connection.verified_at
            )
            await store.audit.add(
                AuditEvent("connection.disabled", "connection", str(connection_id), actor="api")
            )
            await store.commit()
        connection.status = ConnectionStatus.DISABLED
        return connection


class ConnectionResolver:
    """Worker side: turns a connection into an authenticated exchange integration. This is the
    only place that opens stored credentials."""

    def __init__(
        self,
        stores: ConnectionStoreFactory,
        vault: CredentialVault | None,
        exchanges: ExchangeRegistry,
    ) -> None:
        self._stores = stores
        self._vault = vault
        self._exchanges = exchanges

    async def exchange_for(self, connection_id: UUID) -> Exchange:
        if self._vault is None:
            raise VaultNotConfigured("CREDENTIAL_MASTER_KEYS is not set")
        async with self._stores() as store:
            connection = await store.connections.get(connection_id)
            sealed = await store.connections.get_sealed(connection_id)
        if connection is None or sealed is None:
            raise ConnectionNotFound(str(connection_id))
        if connection.status is not ConnectionStatus.ACTIVE:
            raise InvalidConnection(f"connection {connection.label!r} is {connection.status.value}")
        raw = json.loads(self._vault.open(sealed))
        return self._exchanges.authenticated(
            connection.exchange,
            connection_id,
            Credentials(raw["api_key"], raw["api_secret"]),
            connection.environment,
        )

    async def mark_invalid(self, connection_id: UUID, reason: str) -> None:
        async with self._stores() as store:
            await store.connections.set_status(connection_id, ConnectionStatus.INVALID, None)
            await store.audit.add(
                AuditEvent(
                    "connection.invalid",
                    "connection",
                    str(connection_id),
                    actor="worker",
                    payload={"reason": reason},
                )
            )
            await store.commit()
