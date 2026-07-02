import asyncio

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from alphaedge.config import settings


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
def require_migrated_db():
    async def check() -> None:
        engine = create_async_engine(settings.database_url)
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1 FROM instruments LIMIT 1"))
        finally:
            await engine.dispose()

    try:
        asyncio.run(check())
    except Exception:
        pytest.skip("Database unavailable or migrations not applied")
