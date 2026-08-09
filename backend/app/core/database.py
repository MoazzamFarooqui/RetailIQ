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
        from app.models import (  # noqa: F401  — imports register all models
            User, Organization, OrganizationMember, Invitation, Dataset,
            Product, Store, Sale, Forecast, ForecastHeader,
            InventoryRecommendation, ModelHistory, BusinessInsight,
        )
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        from sqlalchemy import select
        from app.models import User, UserRole, Organization, OrgStatus, OrganizationMember, OrganizationRole
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
            # Seed a default organization and make admin its owner, so the
            # v3 UI has an org to work with on first boot.
            org = Organization(
                name="RetailIQ Demo Org",
                slug="retailiq-demo",
                owner_id=admin.id,
                status=OrgStatus.ACTIVE,
            )
            session.add(org)
            await session.flush()
            session.add(OrganizationMember(
                organization_id=org.id,
                user_id=admin.id,
                role=OrganizationRole.OWNER,
            ))
            admin.organization_id = org.id
            await session.commit()


async def close_db():
    """Dispose of the engine connection pool."""
    await engine.dispose()

