"""Base service class with common patterns for all services.

This module provides a BaseService class that encapsulates common patterns
used across all services, including:
- Logger initialization
- Repository dependency injection
- Common error handling
- Replica detection
- Cache management helpers

Services should inherit from BaseService to reduce code duplication and
ensure consistent patterns across the codebase.
"""

from __future__ import annotations

from typing import Generic, Optional, TypeVar

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.utils.cache_service import (
    invalidate_on_create,
    invalidate_on_delete,
    invalidate_on_update,
)

settings = get_settings()

# Type variable for repository type
RepositoryType = TypeVar("RepositoryType")


class BaseService(Generic[RepositoryType]):
    """Base service class with common initialization and utility methods.
    
    All services should inherit from this class to get common functionality:
    - Automatic logger initialization
    - Repository dependency injection pattern
    - Common error handling helpers
    - Replica detection
    - Cache invalidation helpers
    
    Example:
        class ContactsService(BaseService[ContactRepository]):
            def __init__(self, repository: Optional[ContactRepository] = None):
                super().__init__(repository or ContactRepository())
    """

    def __init__(self, repository: RepositoryType):
        """
        Initialize the service with a repository dependency.
        
        Args:
            repository: Repository instance for data access
        """
        self.logger = get_logger(self.__class__.__module__)
        self.repository = repository
        self.logger.debug(
            "Initialized %s with repository=%s",
            self.__class__.__name__,
            repository.__class__.__name__,
        )

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
        await invalidate_on_update(prefix, self.logger)

    async def _invalidate_on_create(self, prefix: str) -> None:
        """
        Invalidate cache after a create operation.
        
        Args:
            prefix: Cache prefix (e.g., "contacts", "companies")
        """
        await invalidate_on_create(prefix, self.logger)

    async def _invalidate_on_update(self, prefix: str) -> None:
        """
        Invalidate cache after an update operation.
        
        Args:
            prefix: Cache prefix (e.g., "contacts", "companies")
        """
        await invalidate_on_update(prefix, self.logger)

    async def _invalidate_on_delete(self, prefix: str) -> None:
        """
        Invalidate cache after a delete operation.
        
        Args:
            prefix: Cache prefix (e.g., "contacts", "companies")
        """
        await invalidate_on_delete(prefix, self.logger)

