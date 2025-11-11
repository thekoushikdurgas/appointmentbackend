"""Async SQLAlchemy session management for FastAPI dependencies."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.core.logging import get_logger


settings = get_settings()
logger = get_logger(__name__)
database_url = settings.DATABASE_URL
if not database_url:
    raise ValueError("DATABASE_URL is not configured.")

engine: AsyncEngine = create_async_engine(
    database_url,
    echo=settings.DATABASE_ECHO,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=settings.DATABASE_POOL_TIMEOUT,
    pool_recycle=settings.DATABASE_POOL_RECYCLE,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an async database session.

    Ensures the session is closed and the transaction is rolled back on exception.
    """
    logger.debug("Entering get_db dependency")
    async with AsyncSessionLocal() as session:
        logger.debug("Opening async DB session")
        try:
            yield session
        except Exception as exc:
            await session.rollback()
            logger.debug("Session rollback due to exception: %s", exc, exc_info=True)
            raise
        finally:
            await session.close()
            logger.debug("Closed async DB session")
    logger.debug("Exiting get_db dependency")

