from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field, SecretStr

from container import Container
from modules.exchanges.domain.connections import (
    ConnectionStatus,
    Credentials,
    Environment,
    ExchangeConnection,
)
from modules.exchanges.errors import ExchangeError

router = APIRouter(prefix="/exchange-connections", tags=["exchange-connections"])


class PermissionsOut(BaseModel):
    can_read: bool
    can_trade: bool
    can_withdraw: bool
    can_transfer: bool
    ip_restricted: bool


class ConnectionCreate(BaseModel):
    exchange: str = "binance"
    environment: Literal["demo", "testnet", "live"] = "demo"
    confirm_real_money: bool = Field(
        default=False,
        description="Required for environment=live: these keys can spend REAL money",
    )
    label: str = Field(min_length=1, max_length=60)
    # SecretStr: never echoed back, never printed by repr/logging of the model.
    api_key: SecretStr
    api_secret: SecretStr


class ConnectionOut(BaseModel):
    """What the API ever returns about a connection: no secret, only a hint of the key."""

    id: UUID
    exchange: str
    environment: Environment
    label: str
    api_key_hint: str
    status: ConnectionStatus
    created_at: datetime
    verified_at: datetime | None
    permissions: PermissionsOut | None = Field(
        default=None, description="What the key could do at the last check."
    )
    status_reason: str | None = Field(
        default=None, description="Why the last check refused the key (null when accepted)."
    )
    last_checked_at: datetime | None = None
    permission_warning: str | None = Field(
        default=None,
        description="An ACTIVE key that later became unacceptable: new entries are refused, "
        "exits continue, until the key is fixed and checked again.",
    )


def _out(c: ExchangeConnection) -> ConnectionOut:
    return ConnectionOut(
        id=c.id,
        exchange=c.exchange,
        environment=c.environment,
        label=c.label,
        api_key_hint=f"...{c.api_key_hint}",
        status=c.status,
        created_at=c.created_at,
        verified_at=c.verified_at,
        permissions=None
        if c.permissions is None
        else PermissionsOut(
            can_read=c.permissions.can_read,
            can_trade=c.permissions.can_trade,
            can_withdraw=c.permissions.can_withdraw,
            can_transfer=c.permissions.can_transfer,
            ip_restricted=c.permissions.ip_restricted,
        ),
        status_reason=c.status_reason,
        last_checked_at=c.last_checked_at,
        permission_warning=c.permission_warning,
    )


def _container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


@router.post("", response_model=ConnectionOut, status_code=status.HTTP_201_CREATED)
async def create_connection(body: ConnectionCreate, request: Request) -> ConnectionOut:
    """Register exchange credentials. They are stored encrypted, only the worker can decrypt
    them, and they are never returned. **Live** keys start `pending`: the worker checks what
    they may do and refuses any key that can withdraw or transfer funds."""
    connection = await _container(request).connections.create(
        body.exchange,
        Environment(body.environment),
        body.label,
        Credentials(body.api_key.get_secret_value(), body.api_secret.get_secret_value()),
        confirm_real_money=body.confirm_real_money,
    )
    return _out(connection)


@router.get("", response_model=list[ConnectionOut])
async def list_connections(request: Request) -> list[ConnectionOut]:
    return [_out(c) for c in await _container(request).connections.list_connections()]


@router.get("/{connection_id}", response_model=ConnectionOut)
async def get_connection(connection_id: UUID, request: Request) -> ConnectionOut:
    return _out(await _container(request).connections.get(connection_id))


@router.post("/{connection_id}/disable", response_model=ConnectionOut)
async def disable_connection(connection_id: UUID, request: Request) -> ConnectionOut:
    """Stop using these credentials. Bots bound to a disabled connection cannot start."""
    return _out(await _container(request).connections.disable(connection_id))


@router.post("/{connection_id}/recheck", response_model=ConnectionOut)
async def recheck_connection(connection_id: UUID, request: Request) -> ConnectionOut:
    """Ask the exchange now what this ACTIVE key may do (the worker also does it daily).

    A key that turned unacceptable keeps working for exits but gets ``permission_warning``,
    which blocks new entries until it is fixed and checked again.
    """
    container = _container(request)
    try:
        connection = await container.resolver.recheck(
            connection_id, container.settings.live_require_ip_restriction
        )
    except ExchangeError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, f"the exchange did not answer: {exc}"
        ) from exc
    return _out(connection)
