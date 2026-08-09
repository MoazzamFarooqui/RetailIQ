"""RetailIQ v3 test suite.

Tests run against a per-session SQLite file DB. All async fixtures and tests
share ONE session-scoped event loop so the module-level async engine (bound
at import time) is used from a single loop — avoiding cross-loop connection
errors with SQLite.
"""

import os

import pytest

# Force SQLite before importing the app
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_retailiq.db"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["SECRET_KEY"] = "test-secret-key-for-pytest"


@pytest.fixture(scope="session")
def event_loop():
    """Session-scoped event loop shared by all async tests and fixtures."""
    import asyncio

    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session():
    """Provide a fresh DB session with a clean schema per test."""
    from app.core.database import Base, engine, async_session_factory

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        yield session
        await session.close()
    await engine.dispose()

