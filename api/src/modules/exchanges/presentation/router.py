from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Request, status
from pydantic import BaseModel, Field, SecretStr

from container import Container
from modules.exchanges.domain.connections import (
    ConnectionStatus,
    Credentials,
    Environment,
    ExchangeConnection,
)

router = APIRouter(prefix="/exchange-connections", tags=["exchange-connections"])


class ConnectionCreate(BaseModel):
    exchange: str = "binance"
    environment: Literal["testnet"] = "testnet"  # live connections are not available yet
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
    )


def _container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


@router.post("", response_model=ConnectionOut, status_code=status.HTTP_201_CREATED)
async def create_connection(body: ConnectionCreate, request: Request) -> ConnectionOut:
    """Register exchange credentials (testnet only). They are stored encrypted, only the
    worker can decrypt them, and they are never returned. Requires `API_TOKEN` to be set."""
    connection = await _container(request).connections.create(
        body.exchange,
        Environment(body.environment),
        body.label,
        Credentials(body.api_key.get_secret_value(), body.api_secret.get_secret_value()),
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
