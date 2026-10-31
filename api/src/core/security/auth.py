"""Bearer-token authentication for the HTTP API.

Single-user deployments need one shared secret, not an identity provider. The token comes from
``API_TOKEN``; it may be omitted only with ``APP_ENV=local`` (developer machine). Endpoints that
accept secrets (exchange credentials) additionally refuse to work while no token is configured.
"""

import secrets

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.config import AppEnv, Settings
from core.errors import LostCryptoError

_bearer = HTTPBearer(auto_error=False)


class InsecureConfiguration(LostCryptoError):
    """The deployment would expose the API without authentication."""


def assert_secure_configuration(settings: Settings) -> None:
    if settings.app_env is not AppEnv.LOCAL and settings.api_token is None:
        raise InsecureConfiguration(f"API_TOKEN is required when APP_ENV={settings.app_env.value}")


def _settings(request: Request) -> Settings:
    settings: Settings = request.app.state.container.settings
    return settings


async def require_api_token(request: Request) -> None:
    """Dependency for every business endpoint (health checks stay open)."""
    settings = _settings(request)
    if settings.api_token is None:
        return  # only reachable with APP_ENV=local (validated at startup)
    credentials: HTTPAuthorizationCredentials | None = await _bearer(request)
    expected = settings.api_token.get_secret_value()
    if credentials is None or not secrets.compare_digest(credentials.credentials, expected):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "missing or invalid API token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_auth_configured(request: Request) -> None:
    """Endpoints that accept secrets are unavailable while the API is unauthenticated."""
    if _settings(request).api_token is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "this endpoint accepts secrets: configure API_TOKEN before using it",
        )
