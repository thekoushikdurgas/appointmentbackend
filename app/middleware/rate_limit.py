"""Rate limiting middleware for AI endpoints."""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Request, status

from app.api.deps import get_current_user
from app.core.ai_config import get_ai_settings
from app.models.user import User
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Sliding window rate limiter for API endpoints."""

    def __init__(
        self,
        requests: int = 20,
        window: int = 60,
    ):
        """
        Initialize rate limiter.
        
        Args:
            requests: Maximum requests allowed per window
            window: Time window in seconds
        """
        self.requests = requests
        self.window = window
        self.clients: dict[str, list[datetime]] = defaultdict(list)
        self._lock = None  # Could use asyncio.Lock for thread safety if needed

    async def check_rate_limit(self, client_id: str) -> None:
        """
        Check if client has exceeded rate limit.
        
        Args:
            client_id: Unique identifier for the client (user ID or IP)
            
        Raises:
            HTTPException: If rate limit is exceeded
        """
        now = datetime.now()
        
        # Clean old requests outside the window
        cutoff_time = now - timedelta(seconds=self.window)
        self.clients[client_id] = [
            req_time
            for req_time in self.clients[client_id]
            if req_time > cutoff_time
        ]
        
        # Check if limit exceeded
        if len(self.clients[client_id]) >= self.requests:
            logger.warning(
                "Rate limit exceeded",
                extra={
                    "context": {
                        "client_id": client_id,
                        "request_count": len(self.clients[client_id]),
                        "limit": self.requests,
                        "window_seconds": self.window,
                    }
                }
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {self.requests} requests per {self.window} seconds.",
                headers={
                    "X-RateLimit-Limit": str(self.requests),
                    "X-RateLimit-Window": str(self.window),
                    "Retry-After": str(self.window),
                },
            )
        
        # Add current request
        self.clients[client_id].append(now)


# Global rate limiter instance
_ai_rate_limiter: Optional[RateLimiter] = None


def get_ai_rate_limiter() -> RateLimiter:
    """Get or create the global AI rate limiter instance."""
    global _ai_rate_limiter
    if _ai_rate_limiter is None:
        ai_settings = get_ai_settings()
        _ai_rate_limiter = RateLimiter(
            requests=ai_settings.AI_RATE_LIMIT_REQUESTS,
            window=ai_settings.AI_RATE_LIMIT_WINDOW,
        )
    return _ai_rate_limiter


async def rate_limit_dependency(
    request: Request,
    rate_limiter: RateLimiter = Depends(get_ai_rate_limiter),
) -> None:
    """
    Dependency for rate limiting AI endpoints.
    
    Uses IP address for rate limiting. For user-based rate limiting,
    use rate_limit_by_user dependency instead.
    """
    client_id = request.client.host if request.client else "unknown"
    await rate_limiter.check_rate_limit(client_id)


async def rate_limit_by_user(
    request: Request,
    current_user: User = Depends(get_current_user),
    rate_limiter: RateLimiter = Depends(get_ai_rate_limiter),
) -> None:
    """
    Dependency for rate limiting AI endpoints by user ID.
    
    This should be used after get_current_user dependency.
    Uses user UUID for rate limiting, falls back to IP if user not available.
    """
    # Try to get user ID from current_user (injected by FastAPI)
    client_id = None
    if current_user and hasattr(current_user, "uuid"):
        client_id = current_user.uuid
    
    # Fall back to IP address if no user ID
    if not client_id:
        client_id = request.client.host if request.client else "unknown"
    
    await rate_limiter.check_rate_limit(client_id)

