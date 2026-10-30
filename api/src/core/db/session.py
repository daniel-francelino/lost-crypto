from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine as _create_async_engine


def create_engine(database_url: str) -> AsyncEngine:
    return _create_async_engine(database_url, pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


def make_store_factory[T](
    session_factory: async_sessionmaker[AsyncSession],
    build: Callable[[AsyncSession], T],
) -> Callable[[], AbstractAsyncContextManager[T]]:
    """One transaction scope per ``async with``: the store commits explicitly, and the
    session is closed (rolling back anything uncommitted) on exit."""

    @asynccontextmanager
    async def scope() -> AsyncIterator[T]:
        async with session_factory() as session:
            yield build(session)

    return scope
