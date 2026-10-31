from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from core.errors import ConflictError, DomainError, NotFoundError


class Role(StrEnum):
    ADMIN = "admin"  # everything, including trading controls and credentials
    VIEWER = "viewer"  # read-only: dashboards, orders, metrics


class InvalidCredentials(DomainError):
    """Wrong username/password, bad or expired session. One message for all of them."""


class AccountLocked(DomainError):
    """Too many failed logins; try again later."""


class UserNotFound(NotFoundError):
    pass


class UsernameTaken(ConflictError):
    pass


@dataclass(slots=True)
class User:
    id: UUID
    username: str
    role: Role
    password_hash: str
    is_active: bool
    created_at: datetime
    password_changed_at: datetime
    failed_logins: int = 0
    locked_until: datetime | None = None
    last_login_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class RefreshToken:
    """A server-side session. The raw token is only ever given to the client; we keep its hash."""

    id: UUID
    user_id: UUID
    family_id: UUID  # every rotation of one login shares a family
    token_hash: str
    expires_at: datetime
    created_at: datetime
    user_agent: str | None = None
    revoked_at: datetime | None = None
    replaced_by: UUID | None = None
