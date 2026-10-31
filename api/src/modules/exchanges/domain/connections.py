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
    INVALID = "invalid"  # rejected by the exchange, or its permissions are unacceptable
    PENDING = "pending"  # live keys wait for the worker to verify their permissions


@dataclass(frozen=True, slots=True)
class ApiPermissions:
    """What an exchange API key is allowed to do (as reported by the exchange)."""

    can_read: bool
    can_trade: bool
    can_withdraw: bool
    can_transfer: bool  # internal / universal transfers: also a way to move funds out
    ip_restricted: bool


def permission_problem(permissions: ApiPermissions, require_ip_restriction: bool) -> str | None:
    """Why live keys are unacceptable for a trading bot, or None. A bot needs to trade and read,
    nothing else: a key that can move funds out is a loaded gun if it ever leaks."""
    if not permissions.can_trade:
        return "the API key cannot trade (enable Spot trading on it)"
    if permissions.can_withdraw:
        return "the API key can WITHDRAW funds: create a new trade-only key without withdrawals"
    if permissions.can_transfer:
        return "the API key can transfer funds: disable internal/universal transfers"
    if require_ip_restriction and not permissions.ip_restricted:
        return "the API key is not restricted to trusted IPs: whitelist your server's IP"
    return None


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
