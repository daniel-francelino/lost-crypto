import pytest
from sqlalchemy import text

from lost_crypto.core.config import get_settings
from lost_crypto.core.db import SqlAlchemyUnitOfWork, create_engine, create_session_factory

pytestmark = pytest.mark.integration


async def test_unit_of_work_executes_query_against_postgres() -> None:
    engine = create_engine(get_settings().database_url)
    try:
        uow = SqlAlchemyUnitOfWork(create_session_factory(engine))
        async with uow:
            result = await uow.session.execute(text("SELECT 1"))
            assert result.scalar_one() == 1
    finally:
        await engine.dispose()
