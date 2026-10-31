from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from modules.auth.domain import RefreshToken, Role, User
from modules.auth.orm import RefreshTokenRow, UserRow


def _to_user(row: UserRow) -> User:
    return User(
        id=row.id,
        username=row.username,
        role=Role(row.role),
        password_hash=row.password_hash,
        is_active=row.is_active,
        created_at=row.created_at,
        password_changed_at=row.password_changed_at,
        failed_logins=row.failed_logins,
        locked_until=row.locked_until,
        last_login_at=row.last_login_at,
    )


def _to_token(row: RefreshTokenRow) -> RefreshToken:
    return RefreshToken(
        id=row.id,
        user_id=row.user_id,
        family_id=row.family_id,
        token_hash=row.token_hash,
        expires_at=row.expires_at,
        created_at=row.created_at,
        user_agent=row.user_agent,
        revoked_at=row.revoked_at,
        replaced_by=row.replaced_by,
    )


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> bool:
        self._session.add(
            UserRow(
                id=user.id,
                username=user.username,
                role=user.role.value,
                password_hash=user.password_hash,
                is_active=user.is_active,
                created_at=user.created_at,
                password_changed_at=user.password_changed_at,
            )
        )
        try:
            await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            return False
        return True

    async def get(self, user_id: UUID) -> User | None:
        row = await self._session.get(UserRow, user_id)
        return _to_user(row) if row else None

    async def get_by_username(self, username: str) -> User | None:
        result = await self._session.execute(select(UserRow).where(UserRow.username == username))
        row = result.scalar_one_or_none()
        return _to_user(row) if row else None

    async def list_users(self) -> list[User]:
        result = await self._session.execute(select(UserRow).order_by(UserRow.created_at))
        return [_to_user(r) for r in result.scalars()]

    async def set_login_state(
        self,
        user_id: UUID,
        failed_logins: int,
        locked_until: datetime | None,
        last_login_at: datetime | None,
    ) -> None:
        await self._session.execute(
            update(UserRow)
            .where(UserRow.id == user_id)
            .values(
                failed_logins=failed_logins, locked_until=locked_until, last_login_at=last_login_at
            )
        )

    async def set_password(self, user_id: UUID, password_hash: str, changed_at: datetime) -> None:
        await self._session.execute(
            update(UserRow)
            .where(UserRow.id == user_id)
            .values(password_hash=password_hash, password_changed_at=changed_at)
        )

    async def set_active(self, user_id: UUID, active: bool) -> None:
        await self._session.execute(
            update(UserRow).where(UserRow.id == user_id).values(is_active=active)
        )


class SqlAlchemyRefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, token: RefreshToken) -> None:
        self._session.add(
            RefreshTokenRow(
                id=token.id,
                user_id=token.user_id,
                family_id=token.family_id,
                token_hash=token.token_hash,
                expires_at=token.expires_at,
                created_at=token.created_at,
                user_agent=token.user_agent,
            )
        )
        await self._session.flush()

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self._session.execute(
            select(RefreshTokenRow).where(RefreshTokenRow.token_hash == token_hash)
        )
        row = result.scalar_one_or_none()
        return _to_token(row) if row else None

    async def revoke(self, token_id: UUID, at: datetime, replaced_by: UUID | None) -> None:
        await self._session.execute(
            update(RefreshTokenRow)
            .where(RefreshTokenRow.id == token_id, RefreshTokenRow.revoked_at.is_(None))
            .values(revoked_at=at, replaced_by=replaced_by)
        )

    async def revoke_family(self, family_id: UUID, at: datetime) -> None:
        await self._session.execute(
            update(RefreshTokenRow)
            .where(RefreshTokenRow.family_id == family_id, RefreshTokenRow.revoked_at.is_(None))
            .values(revoked_at=at)
        )

    async def revoke_all_for_user(self, user_id: UUID, at: datetime) -> None:
        await self._session.execute(
            update(RefreshTokenRow)
            .where(RefreshTokenRow.user_id == user_id, RefreshTokenRow.revoked_at.is_(None))
            .values(revoked_at=at)
        )
