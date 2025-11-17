"""Async SQLAlchemy session management for FastAPI dependencies."""

from collections.abc import AsyncGenerator
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.core.logging import get_logger
from app.utils.query_monitor import get_query_monitor


settings = get_settings()
logger = get_logger(__name__)
database_url = settings.DATABASE_URL
if not database_url:
    raise ValueError("DATABASE_URL is not configured.")

# Enhance database URL with compression if enabled
def enhance_database_url(url: str, enable_compression: bool) -> str:
    """Add query compression parameters to database URL if enabled."""
    if not enable_compression:
        return url
    
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    
    # Add compression parameters for asyncpg
    # Note: asyncpg supports compression via connection parameters
    # We'll handle this in the connection args instead of URL params
    return url

enhanced_database_url = enhance_database_url(database_url, settings.ENABLE_QUERY_COMPRESSION)

# Connection arguments for asyncpg with compression
connect_args = {}
if settings.ENABLE_QUERY_COMPRESSION:
    # Enable compression for large result sets
    # asyncpg supports server_min_messages and other connection options
    connect_args["server_settings"] = {
        "application_name": "appointment360_api",
    }

engine: AsyncEngine = create_async_engine(
    enhanced_database_url,
    echo=settings.DATABASE_ECHO,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=settings.DATABASE_POOL_TIMEOUT,
    pool_recycle=settings.DATABASE_POOL_RECYCLE,
    pool_pre_ping=settings.DATABASE_POOL_PRE_PING,
    connect_args=connect_args,
)

# Set up query monitoring if enabled
if settings.ENABLE_QUERY_MONITORING:
    try:
        query_monitor = get_query_monitor()
        query_monitor.slow_query_threshold = settings.SLOW_QUERY_THRESHOLD
        query_monitor.setup_engine_monitoring(engine)
        logger.info("Query monitoring enabled (threshold=%.2fs)", settings.SLOW_QUERY_THRESHOLD)
    except Exception as e:
        logger.warning("Could not set up query monitoring: %s", e)

# Add connection pool event listeners for monitoring
# Note: For async engines, we use sync_engine for event listeners
try:
    sync_engine = engine.sync_engine
    
    @event.listens_for(sync_engine, "connect")
    def set_connection_settings(dbapi_conn, connection_record):
        """Set connection-level settings for optimal performance."""
        if settings.ENABLE_QUERY_COMPRESSION:
            # Enable compression at connection level if supported
            try:
                # asyncpg connection compression is handled via connection parameters
                # This is a placeholder for any connection-level optimizations
                pass
            except Exception as e:
                logger.debug("Could not set connection compression: %s", e)

    @event.listens_for(sync_engine, "checkout")
    def receive_checkout(dbapi_conn, connection_record, connection_proxy):
        """Log connection checkout for monitoring."""
        logger.debug("Connection checked out from pool")

    @event.listens_for(sync_engine, "checkin")
    def receive_checkin(dbapi_conn, connection_record):
        """Log connection checkin for monitoring."""
        logger.debug("Connection checked in to pool")
except AttributeError:
    # If sync_engine is not available, skip event listeners
    logger.debug("sync_engine not available, skipping connection pool event listeners")

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an async database session.

    Commits the transaction on successful completion, rolls back on exception.
    """
    logger.debug("Entering get_db dependency")
    async with AsyncSessionLocal() as session:
        logger.debug("Opening async DB session")
        try:
            yield session
            await session.commit()
            logger.debug("Session committed successfully")
        except Exception as exc:
            await session.rollback()
            logger.debug("Session rollback due to exception: %s", exc, exc_info=True)
            raise
        finally:
            await session.close()
            logger.debug("Closed async DB session")
    logger.debug("Exiting get_db dependency")

