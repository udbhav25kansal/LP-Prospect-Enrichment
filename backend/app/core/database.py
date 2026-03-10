from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import get_settings

settings = get_settings()

# SQLite needs special handling
connect_args = {}
if "sqlite" in settings.database_url:
    connect_args = {"check_same_thread": False}

engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args=connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_tables():
    """Create all tables (for SQLite dev mode)."""
    from app.models.base import Base
    from app.models import (
        PipelineRun, Organization, Contact,
        EnrichmentResult, Score, ValidationFlag, APICostLog,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
