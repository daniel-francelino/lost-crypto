"""Short-lived JWT access tokens (HS256).

Only *access* tokens are JWTs; they are stateless and expire in minutes. Session continuity comes
from opaque, rotating refresh tokens stored (hashed) in the database, which can be revoked.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt

from core.errors import LostCryptoError

ISSUER = "lost-crypto"
MIN_SECRET_LENGTH = 32


class InvalidToken(LostCryptoError):
    """Missing, malformed, expired, tampered or wrong-kind token."""


@dataclass(frozen=True, slots=True)
class AccessClaims:
    user_id: UUID
    username: str
    role: str
    expires_at: datetime


class TokenCodec:
    def __init__(self, secret: str, lifetime: timedelta) -> None:
        if len(secret) < MIN_SECRET_LENGTH:
            raise ValueError(f"JWT_SECRET must have at least {MIN_SECRET_LENGTH} characters")
        self._secret = secret
        self._lifetime = lifetime

    @property
    def lifetime_seconds(self) -> int:
        return int(self._lifetime.total_seconds())

    def issue(self, user_id: UUID, username: str, role: str, now: datetime) -> str:
        return jwt.encode(
            {
                "iss": ISSUER,
                "sub": str(user_id),
                "usr": username,
                "role": role,
                "typ": "access",
                "jti": uuid4().hex,
                "iat": int(now.timestamp()),
                "exp": int((now + self._lifetime).timestamp()),
            },
            self._secret,
            algorithm="HS256",
        )

    def decode(self, token: str, now: datetime | None = None) -> AccessClaims:
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=["HS256"],  # never trust the token's own "alg"
                issuer=ISSUER,
                # Expiry is checked below against the injected clock, not PyJWT's wall clock.
                options={"require": ["exp", "iat", "sub", "iss"], "verify_exp": False},
            )
            if payload.get("typ") != "access":
                raise InvalidToken("not an access token")
            expires_at = datetime.fromtimestamp(payload["exp"], UTC)
            if expires_at + timedelta(seconds=5) < (now or datetime.now(UTC)):  # 5 s of skew
                raise InvalidToken("token expired")
            return AccessClaims(UUID(payload["sub"]), payload["usr"], payload["role"], expires_at)
        except (jwt.PyJWTError, KeyError, ValueError) as exc:
            raise InvalidToken(str(exc)) from exc
