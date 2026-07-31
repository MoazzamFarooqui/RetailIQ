"""Async SQLAlchemy engine and session factory — supports MySQL + SQLite dev."""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings


def _create_engine():
    """Create an async engine, handling SQLite vs MySQL differences."""
    url = settings.DATABASE_URL

    if url.startswith("sqlite"):
        # SQLite doesn't support pool_size/max_overflow — use default
        return create_async_engine(url, echo=settings.DATABASE_ECHO)
    else:
        return create_async_engine(
            url,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            echo=settings.DATABASE_ECHO,
            pool_pre_ping=True,
        )


engine = _create_engine()

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency that yields an async DB session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create all tables (for development) and seed default admin user."""
    async with engine.begin() as conn:
        from app.models.user import User  # noqa
        from app.models.dataset import Dataset  # noqa
        from app.models.forecast import Forecast, ForecastHeader  # noqa
        from app.models.inventory import InventoryRecommendation  # noqa
        from app.models.model_history import ModelHistory  # noqa
        from app.models.insight import BusinessInsight  # noqa
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        from sqlalchemy import select
        from app.models.user import User, UserRole
        from app.core.security import hash_password
        result = await session.execute(select(User).where(User.username == "admin"))
        if not result.scalar_one_or_none():
            admin = User(
                email="admin@retailiq.com",
                username="admin",
                hashed_password=hash_password("admin123"),
                role=UserRole.ADMIN,
            )
            session.add(admin)
            await session.commit()


async def close_db():
    """Dispose of the engine connection pool."""
    await engine.dispose()
