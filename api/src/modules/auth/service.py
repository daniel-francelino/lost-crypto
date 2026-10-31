"""Login, rotating sessions, password changes and user administration.

Sessions are a short-lived JWT access token (stateless, minutes) plus an opaque refresh token
kept only as a hash in the database. Each refresh *rotates* the token; replaying a token that was
already rotated means it leaked, so the whole login (token family) is revoked.
"""

import asyncio
import hashlib
import re
import secrets
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from core.clock import Clock
from core.errors import LostCryptoError
from core.ids import IdGenerator
from core.security.passwords import PasswordService, WeakPassword, validate_password
from core.security.tokens import AccessClaims, InvalidToken, TokenCodec
from modules.audit.models import AuditEvent
from modules.auth.domain import (
    InvalidCredentials,
    RefreshToken,
    Role,
    User,
    UsernameTaken,
    UserNotFound,
)
from modules.auth.ports import AuthStore

AuthStoreFactory = Callable[[], AbstractAsyncContextManager[AuthStore]]

_USERNAME = re.compile(r"^[a-z0-9][a-z0-9._-]{2,39}$")


class AuthNotConfigured(LostCryptoError):
    """JWT_SECRET is not set: login is unavailable."""


@dataclass(frozen=True, slots=True)
class AuthConfig:
    refresh_ttl: timedelta
    max_failed_logins: int
    lockout: timedelta
    reuse_grace: timedelta


@dataclass(frozen=True, slots=True)
class IssuedSession:
    access_token: str
    expires_in: int  # seconds
    refresh_token: str  # raw; handed to the client once, never stored
    refresh_expires_at: datetime
    user: User


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class AuthService:
    def __init__(
        self,
        stores: AuthStoreFactory,
        passwords: PasswordService,
        codec: TokenCodec | None,
        clock: Clock,
        ids: IdGenerator,
        config: AuthConfig,
    ) -> None:
        self._stores = stores
        self._passwords = passwords
        self._codec = codec
        self._clock = clock
        self._ids = ids
        self._config = config

    # --- sessions ----------------------------------------------------------------------------

    async def login(self, username: str, password: str, user_agent: str | None) -> IssuedSession:
        codec = self._require_codec()
        now = self._clock.now()
        name = username.strip().lower()
        async with self._stores() as store:
            user = await store.users.get_by_username(name)
            usable = user is not None and user.is_active
            locked = user is not None and user.locked_until is not None and user.locked_until > now
            if user is None or not usable or locked:
                await asyncio.to_thread(self._passwords.verify_dummy, password)  # same timing
                await self._audit(store, "auth.login_failed", name, user, locked=locked)
                await store.commit()
                raise InvalidCredentials("invalid credentials or account temporarily locked")

            ok = await asyncio.to_thread(self._passwords.verify, user.password_hash, password)
            if not ok:
                failures = user.failed_logins + 1
                lock = failures >= self._config.max_failed_logins
                await store.users.set_login_state(
                    user.id,
                    0 if lock else failures,
                    now + self._config.lockout if lock else None,
                    user.last_login_at,
                )
                await self._audit(store, "auth.login_failed", name, user, locked=lock)
                await store.commit()
                raise InvalidCredentials("invalid credentials or account temporarily locked")

            await store.users.set_login_state(user.id, 0, None, now)
            if self._passwords.needs_rehash(user.password_hash):
                new_hash = await asyncio.to_thread(self._passwords.hash, password)
                await store.users.set_password(user.id, new_hash, user.password_changed_at)
            session = await self._issue(
                store, codec, user, family_id=self._ids.new_id(), user_agent=user_agent, now=now
            )
            await self._audit(store, "auth.login", name, user)
            await store.commit()
        return session

    async def refresh(self, raw_token: str, user_agent: str | None) -> IssuedSession:
        codec = self._require_codec()
        now = self._clock.now()
        async with self._stores() as store:
            token = await store.refresh_tokens.get_by_hash(_hash(raw_token))
            if token is None:
                raise InvalidCredentials("invalid session")
            if token.revoked_at is not None:
                if (
                    token.replaced_by is not None
                    and now - token.revoked_at <= self._config.reuse_grace
                ):
                    raise InvalidCredentials("invalid session")  # a double click, not an attack
                await store.refresh_tokens.revoke_family(token.family_id, now)
                await self._audit(
                    store, "auth.refresh_reuse_detected", "", None, user_id=token.user_id
                )
                await store.commit()
                raise InvalidCredentials("invalid session")
            user = await store.users.get(token.user_id)
            if token.expires_at <= now or user is None or not user.is_active:
                await store.refresh_tokens.revoke_family(token.family_id, now)
                await store.commit()
                raise InvalidCredentials("invalid session")

            session = await self._issue(
                store, codec, user, token.family_id, user_agent, now, replaces=token
            )
            await store.commit()
        return session

    async def logout(self, raw_token: str | None) -> None:
        """End the login this refresh token belongs to. Idempotent and silent on bad tokens."""
        if not raw_token:
            return
        now = self._clock.now()
        async with self._stores() as store:
            token = await store.refresh_tokens.get_by_hash(_hash(raw_token))
            if token is not None:
                await store.refresh_tokens.revoke_family(token.family_id, now)
                await self._audit(store, "auth.logout", "", None, user_id=token.user_id)
                await store.commit()

    def authenticate(self, access_token: str) -> AccessClaims:
        """Validate an access token (no database access: it is stateless)."""
        try:
            return self._require_codec().decode(access_token, self._clock.now())
        except InvalidToken as exc:
            raise InvalidCredentials("invalid or expired token") from exc

    # --- users -------------------------------------------------------------------------------

    async def create_user(
        self, username: str, password: str, role: Role, actor: str = "cli"
    ) -> User:
        name = username.strip().lower()
        if not _USERNAME.match(name):
            raise WeakPassword(
                "username must be 3-40 chars: lowercase letters, digits, '.', '_' or '-'"
            )
        validate_password(password, name)
        password_hash = await asyncio.to_thread(self._passwords.hash, password)
        now = self._clock.now()
        user = User(self._ids.new_id(), name, role, password_hash, True, now, now)
        async with self._stores() as store:
            if not await store.users.add(user):
                raise UsernameTaken(f"username {name!r} is taken")
            await store.audit.add(
                AuditEvent(
                    "user.created",
                    "user",
                    str(user.id),
                    actor=actor,
                    payload={"username": name, "role": role.value},
                )
            )
            await store.commit()
        return user

    async def get_user(self, user_id: UUID) -> User:
        async with self._stores() as store:
            user = await store.users.get(user_id)
        if user is None:
            raise UserNotFound(str(user_id))
        return user

    async def list_users(self) -> list[User]:
        async with self._stores() as store:
            return await store.users.list_users()

    async def set_active(self, user_id: UUID, active: bool, actor: str) -> User:
        user = await self.get_user(user_id)
        now = self._clock.now()
        async with self._stores() as store:
            await store.users.set_active(user_id, active)
            if not active:
                await store.refresh_tokens.revoke_all_for_user(user_id, now)
            await store.audit.add(
                AuditEvent(
                    "user.enabled" if active else "user.disabled", "user", str(user_id), actor=actor
                )
            )
            await store.commit()
        user.is_active = active
        return user

    async def change_password(self, user_id: UUID, current: str, new: str) -> None:
        user = await self.get_user(user_id)
        if not await asyncio.to_thread(self._passwords.verify, user.password_hash, current):
            raise InvalidCredentials("current password is wrong")
        validate_password(new, user.username)
        new_hash = await asyncio.to_thread(self._passwords.hash, new)
        now = self._clock.now()
        async with self._stores() as store:
            await store.users.set_password(user_id, new_hash, now)
            await store.refresh_tokens.revoke_all_for_user(user_id, now)  # log out everywhere
            await store.audit.add(
                AuditEvent("auth.password_changed", "user", str(user_id), actor=user.username)
            )
            await store.commit()

    # --- internals ---------------------------------------------------------------------------

    def _require_codec(self) -> TokenCodec:
        if self._codec is None:
            raise AuthNotConfigured("JWT_SECRET is not set: login is unavailable")
        return self._codec

    async def _issue(
        self,
        store: AuthStore,
        codec: TokenCodec,
        user: User,
        family_id: UUID,
        user_agent: str | None,
        now: datetime,
        replaces: RefreshToken | None = None,
    ) -> IssuedSession:
        raw = secrets.token_urlsafe(48)
        expires_at = now + self._config.refresh_ttl
        record = RefreshToken(
            self._ids.new_id(),
            user.id,
            family_id,
            _hash(raw),
            expires_at,
            now,
            (user_agent or "")[:200] or None,
        )
        await store.refresh_tokens.add(record)
        if replaces is not None:
            await store.refresh_tokens.revoke(replaces.id, now, replaced_by=record.id)
        return IssuedSession(
            codec.issue(user.id, user.username, user.role.value, now),
            codec.lifetime_seconds,
            raw,
            expires_at,
            user,
        )

    @staticmethod
    async def _audit(
        store: AuthStore,
        event_type: str,
        username: str,
        user: User | None,
        *,
        locked: bool = False,
        user_id: UUID | None = None,
    ) -> None:
        subject = user.id if user is not None else user_id
        await store.audit.add(
            AuditEvent(
                event_type,
                "user",
                str(subject) if subject else username or "unknown",
                actor="auth",
                payload={"username": username, "locked": locked} if username else {},
            )
        )
