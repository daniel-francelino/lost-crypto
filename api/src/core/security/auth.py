"""Who is calling, and may they do this?

Two kinds of caller are accepted on a ``Authorization: Bearer <token>`` header:

* **Users** (the frontend): a short-lived JWT access token obtained from ``POST /auth/login``,
  renewed through a rotating refresh-token cookie. Roles: ``admin`` (everything) and ``viewer``
  (read-only).
* **A service token** (``API_TOKEN``): a static secret for scripts, curl and monitors. It acts as
  admin.

Authentication is optional only on a developer machine (``APP_ENV=local`` with neither ``API_TOKEN``
nor ``JWT_SECRET`` set); anywhere else the app refuses to start without one of them. Endpoints that
accept secrets additionally refuse to work while authentication is off.
"""

import secrets
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.config import AppEnv, Settings
from core.errors import DomainError, LostCryptoError

ADMIN = "admin"
VIEWER = "viewer"
WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

_bearer = HTTPBearer(auto_error=False)


class InsecureConfiguration(LostCryptoError):
    """The deployment would expose the API without authentication."""


@dataclass(frozen=True, slots=True)
class Principal:
    subject: str  # user id, or "service" / "local"
    username: str
    role: str
    kind: str  # user | service | anonymous (local development only)


def assert_secure_configuration(settings: Settings) -> None:
    if settings.app_env is not AppEnv.LOCAL and not settings.auth_enabled:
        raise InsecureConfiguration(
            f"set JWT_SECRET (users) and/or API_TOKEN (service) when "
            f"APP_ENV={settings.app_env.value}"
        )


def _unauthorized(detail: str = "missing or invalid credentials") -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": "Bearer"}
    )


async def require_auth(request: Request) -> Principal:
    """Authenticate the caller (any role). Stores the principal on ``request.state``."""
    container: Any = request.app.state.container
    settings: Settings = container.settings
    if not settings.auth_enabled:
        principal = Principal("local", "local", ADMIN, "anonymous")
    else:
        credentials: HTTPAuthorizationCredentials | None = await _bearer(request)
        if credentials is None:
            raise _unauthorized()
        token = credentials.credentials
        if settings.api_token is not None and secrets.compare_digest(
            token, settings.api_token.get_secret_value()
        ):
            principal = Principal("service", "service", ADMIN, "service")
        elif settings.jwt_secret is not None:
            try:
                claims = container.auth.authenticate(token)
            except DomainError:  # InvalidCredentials
                raise _unauthorized("invalid or expired token") from None
            principal = Principal(str(claims.user_id), claims.username, claims.role, "user")
        else:
            raise _unauthorized()
    request.state.principal = principal
    return principal


async def require_access(
    request: Request, principal: Principal = Depends(require_auth)
) -> Principal:
    """Reading needs any signed-in role; anything that changes state needs ``admin``."""
    if request.method in WRITE_METHODS and principal.role != ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "this action requires the admin role")
    return principal


async def require_admin(principal: Principal = Depends(require_auth)) -> Principal:
    if principal.role != ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "this action requires the admin role")
    return principal


async def require_auth_configured(request: Request) -> None:
    """Endpoints that accept secrets are unavailable while the API is unauthenticated."""
    settings: Settings = request.app.state.container.settings
    if not settings.auth_enabled:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "this endpoint accepts secrets: configure JWT_SECRET or API_TOKEN first",
        )
