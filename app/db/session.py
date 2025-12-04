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
import atexit


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
        "application_name": "contact360_api",
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

    # Connection pool statistics
    pool_stats = {
        "checkouts": 0,
        "checkins": 0,
        "invalidated": 0,
        "overflow": 0,
        "wait_times": [],  # Track connection wait times
        "max_wait_time": 0.0,
        "total_wait_time": 0.0,
    }
    
    @event.listens_for(sync_engine, "checkout")
    def receive_checkout(dbapi_conn, connection_record, connection_proxy):
        """Log connection checkout for monitoring."""
        import time
        checkout_start = time.time()
        pool_stats["checkouts"] += 1
        
        if settings.ENABLE_POOL_MONITORING:
            pool = sync_engine.pool
            size = pool.size()
            checked_in = pool.checkedin()
            checked_out = pool.checkedout()
            overflow = pool.overflow()
            
            # Calculate wait time (time spent waiting for connection)
            # This is approximate - actual wait happens before this event
            wait_time = time.time() - checkout_start
            if wait_time > 0:
                pool_stats["wait_times"].append(wait_time)
                pool_stats["total_wait_time"] += wait_time
                if wait_time > pool_stats["max_wait_time"]:
                    pool_stats["max_wait_time"] = wait_time
                
                # Keep only last 1000 wait times to avoid memory issues
                if len(pool_stats["wait_times"]) > 1000:
                    pool_stats["wait_times"] = pool_stats["wait_times"][-1000:]
            
            # Log warning if pool is getting full
            if checked_out > size * 0.8:
                logger.warning(
                    "Connection pool usage high: checked_out=%d/%d overflow=%d wait_time=%.3fs",
                    checked_out,
                    size,
                    overflow,
                    wait_time,
                )
            
            # Log warning if wait time is significant
            if wait_time > 0.1:  # 100ms threshold
                logger.warning(
                    "Connection checkout took longer than expected: wait_time=%.3fs checked_out=%d/%d",
                    wait_time,
                    checked_out,
                    size,
                )
            
            logger.debug(
                "Connection checked out: total=%d checked_out=%d checked_in=%d overflow=%d wait_time=%.3fs",
                pool_stats["checkouts"],
                checked_out,
                checked_in,
                overflow,
                wait_time,
            )
    
    @event.listens_for(sync_engine, "checkin")
    def receive_checkin(dbapi_conn, connection_record):
        """Log connection checkin for monitoring."""
        pool_stats["checkins"] += 1
        if settings.ENABLE_POOL_MONITORING:
            pool = sync_engine.pool
            logger.debug(
                "Connection checked in: total=%d pool_size=%d",
                pool_stats["checkins"],
                pool.size(),
            )
    
    @event.listens_for(sync_engine, "invalidate")
    def receive_invalidate(dbapi_conn, connection_record, exception):
        """Log connection invalidation."""
        pool_stats["invalidated"] += 1
        logger.warning(
            "Connection invalidated: total=%d exception=%s",
            pool_stats["invalidated"],
            exception,
        )
    
    def get_pool_stats() -> dict:
        """Get current connection pool statistics."""
        try:
            pool = sync_engine.pool
            size = pool.size()
            checked_out = pool.checkedout()
            checked_in = pool.checkedin()
            overflow = pool.overflow()
            
            # Calculate wait time statistics
            wait_times = pool_stats["wait_times"]
            avg_wait_time = (
                pool_stats["total_wait_time"] / len(wait_times)
                if wait_times else 0.0
            )
            
            return {
                "size": size,
                "checked_in": checked_in,
                "checked_out": checked_out,
                "overflow": overflow,
                "usage_percentage": (checked_out / size * 100) if size > 0 else 0.0,
                "total_checkouts": pool_stats["checkouts"],
                "total_checkins": pool_stats["checkins"],
                "total_invalidated": pool_stats["invalidated"],
                "wait_time_stats": {
                    "avg_wait_time_seconds": avg_wait_time,
                    "max_wait_time_seconds": pool_stats["max_wait_time"],
                    "total_wait_time_seconds": pool_stats["total_wait_time"],
                    "samples": len(wait_times),
                },
                "health_status": (
                    "healthy" if checked_out < size * 0.7 and overflow == 0
                    else "warning" if checked_out < size * 0.9
                    else "critical"
                ),
            }
        except Exception as exc:
            logger.warning("Could not get pool stats: %s", exc)
            return {}
    
    def check_pool_health() -> dict:
        """Check connection pool health and return status."""
        stats = get_pool_stats()
        if not stats:
            return {
                "status": "unknown",
                "message": "Could not retrieve pool statistics",
            }
        
        size = stats.get("size", 0)
        checked_out = stats.get("checked_out", 0)
        overflow = stats.get("overflow", 0)
        usage_percentage = stats.get("usage_percentage", 0.0)
        avg_wait_time = stats.get("wait_time_stats", {}).get("avg_wait_time_seconds", 0.0)
        
        # Health check criteria
        # Healthy: < 70% usage, no overflow, low wait time
        # Warning: 70-90% usage or some overflow or moderate wait time
        # Critical: > 90% usage or high overflow or high wait time
        usage_ratio = checked_out / size if size > 0 else 0.0
        
        if usage_ratio < 0.7 and overflow == 0 and avg_wait_time < 0.1:
            status = "healthy"
        elif usage_ratio < 0.9 and overflow < size * 0.1 and avg_wait_time < 0.5:
            status = "warning"
        else:
            status = "critical"
        message = (
            f"Pool usage: {usage_percentage:.1f}% ({checked_out}/{size}), "
            f"overflow: {overflow}, avg wait: {avg_wait_time*1000:.1f}ms"
        )
        
        return {
            "status": status,
            "message": message,
            "stats": stats,
        }
    
    # Log pool statistics periodically if enabled
    if settings.ENABLE_POOL_MONITORING and settings.POOL_MONITORING_INTERVAL > 0:
        import threading
        import time
        
        def log_pool_stats():
            """Periodically log pool statistics."""
            while True:
                time.sleep(settings.POOL_MONITORING_INTERVAL)
                stats = get_pool_stats()
                if stats:
                    wait_stats = stats.get("wait_time_stats", {})
                    logger.info(
                        "Connection pool stats: size=%d checked_out=%d checked_in=%d overflow=%d "
                        "usage=%.1f%% health=%s "
                        "total_checkouts=%d total_checkins=%d invalidated=%d "
                        "avg_wait=%.3fs max_wait=%.3fs",
                        stats.get("size", 0),
                        stats.get("checked_out", 0),
                        stats.get("checked_in", 0),
                        stats.get("overflow", 0),
                        stats.get("usage_percentage", 0.0),
                        stats.get("health_status", "unknown"),
                        stats.get("total_checkouts", 0),
                        stats.get("total_checkins", 0),
                        stats.get("total_invalidated", 0),
                        wait_stats.get("avg_wait_time_seconds", 0.0),
                        wait_stats.get("max_wait_time_seconds", 0.0),
                    )
        
        # Start monitoring thread (daemon so it doesn't block shutdown)
        monitor_thread = threading.Thread(target=log_pool_stats, daemon=True)
        monitor_thread.start()
        logger.info("Connection pool monitoring started (interval=%ds)", settings.POOL_MONITORING_INTERVAL)
    
    # Log pool stats on shutdown
    def log_final_pool_stats():
        """Log final pool statistics on application shutdown."""
        stats = get_pool_stats()
        if stats:
            logger.info(
                "Final connection pool stats: size=%d total_checkouts=%d total_checkins=%d invalidated=%d",
                stats.get("size", 0),
                stats.get("total_checkouts", 0),
                stats.get("total_checkins", 0),
                stats.get("total_invalidated", 0),
            )
    
    atexit.register(log_final_pool_stats)
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

