import json
import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from datetime import datetime, timedelta
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
    ApiPermissions,
    ConnectionStatus,
    Credentials,
    Environment,
    ExchangeConnection,
    permission_problem,
)
from modules.exchanges.errors import AuthenticationFailed, ExchangeError

logger = logging.getLogger(__name__)

RECHECK_EVERY = timedelta(days=1)


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
    async def list_pending(self) -> list[ExchangeConnection]: ...
    async def list_active_live(self) -> list[ExchangeConnection]: ...
    async def record_check(
        self,
        connection_id: UUID,
        *,
        checked_at: datetime,
        permissions: ApiPermissions | None,
        reason: str | None,
        warning: str | None,
    ) -> None:
        """Store the last permission check (and the warning, None to clear it)."""
        ...

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
        live_allowed: bool = False,
    ) -> None:
        self._stores = stores
        self._live_allowed = live_allowed
        self._vault = vault
        self._exchanges = exchanges
        self._clock = clock
        self._next_recheck: datetime | None = None
        self._ids = ids

    async def create(
        self,
        exchange: str,
        environment: Environment,
        label: str,
        credentials: Credentials,
        confirm_real_money: bool = False,
    ) -> ExchangeConnection:
        if self._vault is None:
            raise VaultNotConfigured("CREDENTIAL_MASTER_KEYS is not set")
        profile = self._exchanges.profile(exchange)
        if environment is Environment.LIVE:
            if not self._live_allowed:
                raise InvalidConnection("live connections can only be created with APP_ENV=prod")
            if not confirm_real_money:
                raise InvalidConnection(
                    "live connections use REAL MONEY: send confirm_real_money=true to proceed"
                )
        elif environment is Environment.DEMO and not profile.capabilities.has_demo:
            raise InvalidConnection(f"{exchange} has no Demo Mode API")
        elif environment is Environment.TESTNET and not profile.capabilities.has_testnet:
            raise InvalidConnection(f"{exchange} has no testnet")
        if len(credentials.api_key) < 8 or len(credentials.api_secret) < 8:
            raise InvalidConnection("api_key and api_secret look too short to be real")

        connection = ExchangeConnection(
            id=self._ids.new_id(),
            exchange=exchange,
            environment=environment,
            label=label,
            api_key_hint=credentials.api_key[-4:],
            # Live keys are unusable until the worker has checked what they are allowed to do.
            status=ConnectionStatus.PENDING
            if environment is Environment.LIVE
            else ConnectionStatus.ACTIVE,
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
        clock: Clock,
    ) -> None:
        self._stores = stores
        self._vault = vault
        self._exchanges = exchanges
        self._clock = clock
        self._next_recheck: datetime | None = None

    def _now(self) -> datetime:
        return self._clock.now()

    async def exchange_for(self, connection_id: UUID, *, allow_pending: bool = False) -> Exchange:
        if self._vault is None:
            raise VaultNotConfigured("CREDENTIAL_MASTER_KEYS is not set")
        async with self._stores() as store:
            connection = await store.connections.get(connection_id)
            sealed = await store.connections.get_sealed(connection_id)
        if connection is None or sealed is None:
            raise ConnectionNotFound(str(connection_id))
        allowed = {ConnectionStatus.ACTIVE} | (
            {ConnectionStatus.PENDING} if allow_pending else set()
        )
        if connection.status not in allowed:
            raise InvalidConnection(f"connection {connection.label!r} is {connection.status.value}")
        raw = json.loads(self._vault.open(sealed))
        return self._exchanges.authenticated(
            connection.exchange,
            connection_id,
            Credentials(raw["api_key"], raw["api_secret"]),
            connection.environment,
        )

    async def environment_for(self, connection_id: UUID) -> Environment:
        async with self._stores() as store:
            connection = await store.connections.get(connection_id)
        if connection is None:
            raise ConnectionNotFound(str(connection_id))
        return connection.environment

    async def verify_pending(self, require_ip_restriction: bool) -> int:
        """Check what each pending (live) key may do; activate the acceptable, reject the rest.

        A key that can withdraw or transfer funds is refused outright. Transient errors leave
        the connection pending to be retried on the next pass."""
        async with self._stores() as store:
            pending = await store.connections.list_pending()
        done = 0
        for connection in pending:
            permissions: ApiPermissions | None = None
            try:
                exchange = await self.exchange_for(connection.id, allow_pending=True)
                permissions = await exchange.fetch_api_permissions()
                problem = permission_problem(permissions, require_ip_restriction)
            except AuthenticationFailed as exc:
                problem = f"the exchange rejected the credentials: {exc}"
            except ExchangeError:
                continue  # cannot tell right now: stay pending, try again
            status = ConnectionStatus.INVALID if problem else ConnectionStatus.ACTIVE
            async with self._stores() as store:
                await store.connections.set_status(
                    connection.id, status, None if problem else self._now()
                )
                await store.connections.record_check(
                    connection.id,
                    checked_at=self._now(),
                    permissions=permissions,
                    reason=problem,
                    warning=None,
                )
                await store.audit.add(
                    AuditEvent(
                        "connection.invalid" if problem else "connection.verified",
                        "connection",
                        str(connection.id),
                        actor="worker",
                        payload={"reason": problem} if problem else {},
                    )
                )
                await store.commit()
            done += 1
        return done

    async def recheck_due(self, require_ip_restriction: bool) -> int:
        """Once a day, check active live keys again (book 1 ch. 4, O1)."""
        now = self._now()
        if self._next_recheck is not None and now < self._next_recheck:
            return 0
        self._next_recheck = now + RECHECK_EVERY
        async with self._stores() as store:
            active = await store.connections.list_active_live()
        checked = 0
        for connection in active:
            try:
                await self.recheck(connection.id, require_ip_restriction)
                checked += 1
            except ExchangeError:
                logger.warning("permission recheck of %s failed; next pass", connection.id)
        return checked

    async def recheck(
        self, connection_id: UUID, require_ip_restriction: bool
    ) -> ExchangeConnection:
        """Check an ACTIVE key's permissions now.

        A key that became unacceptable is not invalidated (that would also block the exits of a
        bot holding a position): it gets ``permission_warning``, which stops new entries.
        Transient exchange errors propagate and change nothing.
        """
        async with self._stores() as store:
            connection = await store.connections.get(connection_id)
        if connection is None:
            raise ConnectionNotFound(str(connection_id))
        if connection.status is not ConnectionStatus.ACTIVE:
            raise InvalidConnection(f"connection {connection.label!r} is {connection.status.value}")
        exchange = await self.exchange_for(connection_id)
        try:
            permissions = await exchange.fetch_api_permissions()
            problem = permission_problem(
                permissions,
                require_ip_restriction and connection.environment is Environment.LIVE,
            )
        except AuthenticationFailed as exc:
            permissions, problem = None, f"the exchange rejected the credentials: {exc}"
        now = self._now()
        async with self._stores() as store:
            await store.connections.record_check(
                connection_id,
                checked_at=now,
                permissions=permissions,
                reason=problem,
                warning=problem,
            )
            if problem != connection.permission_warning:
                await store.audit.add(
                    AuditEvent(
                        "connection.permissions_changed"
                        if problem
                        else "connection.permissions_ok",
                        "connection",
                        str(connection_id),
                        actor="worker",
                        payload={"reason": problem} if problem else {},
                    )
                )
            await store.commit()
            updated = await store.connections.get(connection_id)
        if updated is None:
            raise ConnectionNotFound(str(connection_id))
        return updated

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
