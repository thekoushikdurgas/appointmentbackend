"""Base service class with common patterns for all services.

This module provides a BaseService class that encapsulates common patterns
used across all services, including:
- Common error handling
- Replica detection
- Cache management helpers

Services should inherit from BaseService to reduce code duplication and
ensure consistent patterns across the codebase.
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.utils.cache_service import (
    invalidate_on_create,
    invalidate_on_delete,
    invalidate_on_update,
)
from app.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


class BaseService:
    """Base service class with common utility methods.
    
    All services should inherit from this class to get common functionality:
    - Common error handling helpers
    - Replica detection
    - Cache invalidation helpers
    
    Example:
        class ContactsService(BaseService):
            def __init__(self):
                super().__init__()
    """

    def __init__(self):
        """
        Initialize the service.
        """
        pass

    def _is_using_replica(self) -> bool:
        """
        Determine if the current database connection is using a replica.
        
        Checks configuration flags and database URL to detect replica usage.
        This is useful for logging and monitoring purposes.
        
        Returns:
            True if using replica, False otherwise
        """
        # Check explicit USE_REPLICA flag
        if settings.USE_REPLICA:
            return True
        
        # Check if DATABASE_REPLICA_URL is configured
        if settings.DATABASE_REPLICA_URL:
            return True
        
        # Check if DATABASE_URL contains replica indicators
        if settings.DATABASE_URL:
            url_lower = settings.DATABASE_URL.lower()
            replica_indicators = ["replica", "readonly", "read-only", "read_replica"]
            if any(indicator in url_lower for indicator in replica_indicators):
                return True
        
        return False

    def _raise_not_found(self, entity_name: str, identifier: str) -> None:
        """
        Raise a 404 HTTPException for entity not found.
        
        Args:
            entity_name: Name of the entity (e.g., "Contact", "Company")
            identifier: Entity identifier (UUID or ID)
        
        Raises:
            HTTPException: 404 Not Found
        """
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{entity_name} not found: {identifier}",
        )

    def _raise_bad_request(self, detail: str) -> None:
        """
        Raise a 400 HTTPException for bad request.
        
        Args:
            detail: Error detail message
        
        Raises:
            HTTPException: 400 Bad Request
        """
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )

    async def _invalidate_list_cache(self, prefix: str) -> None:
        """
        Invalidate list cache for a given prefix.
        
        Convenience method that uses the cache service helper.
        
        Args:
            prefix: Cache prefix (e.g., "contacts", "companies")
        """
        await invalidate_on_update(prefix)

    async def _invalidate_on_create(self, prefix: str) -> None:
        """
        Invalidate cache after a create operation.
        
        Args:
            prefix: Cache prefix (e.g., "contacts", "companies")
        """
        await invalidate_on_create(prefix)

    async def _invalidate_on_update(self, prefix: str) -> None:
        """
        Invalidate cache after an update operation.
        
        Args:
            prefix: Cache prefix (e.g., "contacts", "companies")
        """
        await invalidate_on_update(prefix)

    async def _invalidate_on_delete(self, prefix: str) -> None:
        """
        Invalidate cache after a delete operation.
        
        Args:
            prefix: Cache prefix (e.g., "contacts", "companies")
        """
        await invalidate_on_delete(prefix)

