from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class Environment(StrEnum):
    TESTNET = "testnet"
    LIVE = "live"


class ConnectionStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    INVALID = "invalid"  # the exchange rejected the credentials


@dataclass(frozen=True, slots=True)
class Credentials:
    """API key pair. Never logged: ``repr``/``str`` mask the secret."""

    api_key: str
    api_secret: str

    def __repr__(self) -> str:
        return f"Credentials(api_key=...{self.api_key[-4:]}, api_secret=***)"

    __str__ = __repr__


@dataclass(slots=True)
class ExchangeConnection:
    """An account on an exchange environment. Holds no secret: the encrypted credentials live
    only in the repository and are opened by the worker when it needs them."""

    id: UUID
    exchange: str
    environment: Environment
    label: str
    api_key_hint: str  # last 4 characters of the key, to recognise it
    status: ConnectionStatus
    created_at: datetime
    verified_at: datetime | None = None
