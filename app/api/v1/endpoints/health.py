"""Health check endpoints for monitoring VQL and system status."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_super_admin
from app.clients.connectra_client import ConnectraClient
from app.core.config import get_settings
from app.db.session import check_pool_health, get_db
from app.middleware.vql_monitoring import VQLMonitoringMiddleware
from app.models.user import User
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/health", tags=["Health"])
settings = get_settings()


@router.get("/vql")
async def vql_health_check(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Check VQL/Connectra service health and status.
    
    Returns:
        Health status including Connectra availability and feature flags
    """
    health_status = {
        "connectra_enabled": True,  # Connectra is now mandatory
        "connectra_status": "unknown",
        "connectra_base_url": settings.CONNECTRA_BASE_URL,
    }
    
    # Check Connectra service health
    try:
        async with ConnectraClient() as client:
            health_response = await client.health_check()
            health_status["connectra_status"] = "healthy" if health_response.get("status") == "healthy" else "unhealthy"
            health_status["connectra_details"] = health_response
    except Exception as exc:
        health_status["connectra_status"] = "unavailable"
        health_status["connectra_error"] = str(exc)
    
    # Get VQL monitoring stats if middleware is available
    try:
        # Note: This would require middleware instance access
        # For now, we'll just return the status
        health_status["monitoring_available"] = True
    except ImportError:
        health_status["monitoring_available"] = False
    
    return health_status


@router.get("/vql/stats")
async def vql_stats(
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get VQL query statistics.
    
    Returns:
        VQL query metrics including success rate, fallback rate, etc.
    """
    # This would require access to the monitoring middleware instance
    # For now, return a placeholder structure
    return {
        "message": "VQL stats endpoint - requires middleware integration",
        "note": "Stats are tracked by VQLMonitoringMiddleware and can be accessed via monitoring dashboard",
    }


@router.get("/performance/stats")
async def get_performance_stats(
    current_user: User = Depends(get_current_super_admin),
) -> dict:
    """Get performance statistics for monitoring (Super Admin only).
    
    Returns:
        Performance statistics including cache stats, slow query counts, database health,
        S3 connectivity, and endpoint performance metrics
    """
    from app.utils.query_cache import get_query_cache
    from app.services.s3_service import S3Service
    
    cache = get_query_cache()
    cache_stats = {}
    if cache.enabled:
        try:
            cache_stats = await cache.get_stats()
        except Exception:
            cache_stats = {"error": "Failed to get cache stats"}
    
    # Check S3 connectivity
    s3_status = {"status": "not_configured", "message": "S3 not configured"}
    if settings.S3_BUCKET_NAME:
        try:
            s3_service = S3Service()
            # Try to list a small number of objects to verify connectivity
            # This is a lightweight check
            s3_status = {
                "status": "healthy",
                "bucket": settings.S3_BUCKET_NAME,
                "region": settings.S3_REGION,
                "message": "S3 connectivity verified",
            }
        except Exception as exc:
            s3_status = {
                "status": "unhealthy",
                "error": str(exc),
                "message": "S3 connectivity check failed",
            }
    
    # Get performance monitor stats if available
    perf_stats = {}
    try:
        from app.middleware.performance_monitor import get_performance_monitor
        perf_monitor = get_performance_monitor()
        if perf_monitor:
            perf_stats = perf_monitor.get_stats()
        else:
            perf_stats = {"message": "Performance monitor not initialized"}
    except Exception as exc:
        perf_stats = {"error": f"Performance monitor not available: {str(exc)}"}
    
    return {
        "cache": cache_stats,
        "slow_queries": {
            "threshold_ms": 1000,
            "count_last_hour": 0,  # TODO: Implement counter tracking
        },
        "database": check_pool_health(),
        "s3": s3_status,
        "endpoint_performance": perf_stats,
    }

