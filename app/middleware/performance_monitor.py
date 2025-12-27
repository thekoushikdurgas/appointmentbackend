"""Performance monitoring middleware for tracking endpoint metrics."""

import time
from collections import defaultdict, deque
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)

# Global instance for health check access
_performance_monitor_instance = None


def get_performance_monitor():
    """Get the global performance monitor instance."""
    return _performance_monitor_instance


def set_performance_monitor(instance):
    """Set the global performance monitor instance."""
    global _performance_monitor_instance
    _performance_monitor_instance = instance


class PerformanceMonitorMiddleware(BaseHTTPMiddleware):
    """
    Middleware that tracks endpoint performance metrics (P50, P95, P99).
    
    Maintains rolling window of response times per endpoint and logs
    aggregated statistics periodically.
    """
    
    def __init__(self, app, window_size: int = 1000, log_interval: int = 100):
        """
        Initialize performance monitor.
        
        Args:
            app: FastAPI application
            window_size: Number of requests to keep in rolling window per endpoint
            log_interval: Log aggregated stats every N requests
        """
        super().__init__(app)
        self.window_size = window_size
        self.log_interval = log_interval
        self.request_count = 0
        
        # Store response times per endpoint: {endpoint: deque([durations...])}
        self.response_times: dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        
        # Store error counts per endpoint: {endpoint: count}
        self.error_counts: dict[str, int] = defaultdict(int)
        
        # Register global instance for health check access
        set_performance_monitor(self)
    
    def _calculate_percentiles(self, durations: deque) -> dict[str, float]:
        """Calculate P50, P95, P99 percentiles from durations."""
        if not durations:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0}
        
        sorted_durations = sorted(durations)
        n = len(sorted_durations)
        
        p50_idx = int(n * 0.50)
        p95_idx = int(n * 0.95)
        p99_idx = int(n * 0.99)
        
        return {
            "p50": sorted_durations[p50_idx] if p50_idx < n else sorted_durations[-1],
            "p95": sorted_durations[p95_idx] if p95_idx < n else sorted_durations[-1],
            "p99": sorted_durations[p99_idx] if p99_idx < n else sorted_durations[-1],
        }
    
    def _get_endpoint_key(self, method: str, path: str) -> str:
        """Generate endpoint key from method and path."""
        # Normalize path (remove trailing slashes, query params)
        normalized_path = path.rstrip("/")
        return f"{method} {normalized_path}"
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Track request performance and log aggregated metrics."""
        start_time = time.perf_counter()
        method = request.method
        path = request.url.path
        
        # Skip metrics for health checks and static files
        if path in ["/health", "/health/", "/health/db", "/favicon.ico"]:
            return await call_next(request)
        
        endpoint_key = self._get_endpoint_key(method, path)
        
        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            # Track response time
            self.response_times[endpoint_key].append(duration_ms)
            
            # Track errors (4xx and 5xx)
            if response.status_code >= 400:
                self.error_counts[endpoint_key] += 1
            
            # Log aggregated stats periodically
            self.request_count += 1
            if self.request_count % self.log_interval == 0:
                self._log_aggregated_stats()
            
            return response
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.response_times[endpoint_key].append(duration_ms)
            self.error_counts[endpoint_key] += 1
            raise
    
    def _log_aggregated_stats(self):
        """Log aggregated performance statistics for all endpoints."""
        stats = []
        for endpoint_key, durations in self.response_times.items():
            if not durations:
                continue
            
            percentiles = self._calculate_percentiles(durations)
            error_count = self.error_counts.get(endpoint_key, 0)
            total_requests = len(durations)
            error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0
            
            stats.append({
                "endpoint": endpoint_key,
                "request_count": total_requests,
                "p50_ms": round(percentiles["p50"], 2),
                "p95_ms": round(percentiles["p95"], 2),
                "p99_ms": round(percentiles["p99"], 2),
                "error_count": error_count,
                "error_rate_percent": round(error_rate, 2),
            })
        
        if stats:
            # Sort by P95 response time (descending) to show slowest endpoints first
            stats.sort(key=lambda x: x["p95_ms"], reverse=True)
            
            logger.debug(
                "Performance metrics summary",
                extra={
                    "context": {
                        "total_endpoints": len(stats),
                        "total_requests": self.request_count,
                    },
                    "performance": {
                        "endpoints": stats[:20],  # Top 20 slowest endpoints
                    }
                }
            )
    
    def get_stats(self) -> dict:
        """Get current performance statistics (for health checks)."""
        stats = {}
        for endpoint_key, durations in self.response_times.items():
            if not durations:
                continue
            
            percentiles = self._calculate_percentiles(durations)
            error_count = self.error_counts.get(endpoint_key, 0)
            total_requests = len(durations)
            
            stats[endpoint_key] = {
                "request_count": total_requests,
                "p50_ms": round(percentiles["p50"], 2),
                "p95_ms": round(percentiles["p95"], 2),
                "p99_ms": round(percentiles["p99"], 2),
                "error_count": error_count,
                "error_rate_percent": round((error_count / total_requests * 100) if total_requests > 0 else 0, 2),
            }
        
        return stats

