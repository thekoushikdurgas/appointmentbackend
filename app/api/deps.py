"""Shared dependencies for API endpoints."""

import asyncio
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.constants import ADMIN, FREE_USER, PRO_USER, SUPER_ADMIN, UNLIMITED_CREDITS_ROLES
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User
from app.repositories.user import UserProfileRepository, UserRepository
from app.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)

# Simple in-memory cache for user authentication (TTL-based)
# Cache key: user_uuid, Value: User object, TTL: 5 minutes (300 seconds)
try:
    from cachetools import TTLCache
    _user_cache: Optional[TTLCache] = TTLCache(maxsize=10000, ttl=600)  # Increased: 10k users for 10 minutes
    CACHE_AVAILABLE = True
except ImportError:
    _user_cache = None
    CACHE_AVAILABLE = False

# Request-scoped cache to prevent multiple DB queries within the same request
# This is a simple dict that gets cleared periodically
_request_cache: dict[str, User] = {}
_request_cache_max_size = 100  # Prevent memory leaks

# OAuth2 scheme for Bearer token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V2_PREFIX}/auth/login",
    auto_error=False
)


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Get the current authenticated user from Bearer token (optional).
    
    Returns None if no token is provided (for public access).
    Raises HTTPException if token is invalid.
    """
    if not token:
        return None
    
    # Decode token
    try:
        payload = decode_token(token)
    except Exception:
        # Invalid token - return None for public access
        return None
    
    if not payload or payload.get("type") != "access":
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    # Get user from database
    user_repo = UserRepository()
    try:
        user = await asyncio.wait_for(
            user_repo.get_by_uuid(session, user_id),
            timeout=5.0
        )
        return user
    except (asyncio.TimeoutError, Exception):
        return None


def get_user_role(user: Optional[User], session: AsyncSession) -> Optional[str]:
    """
    Get user's role from their profile.
    
    Args:
        user: User object or None
        session: Database session
        
    Returns:
        Role string or None for public users
    """
    if not user:
        return None
    
    profile_repo = UserProfileRepository()
    
    # This is a sync function but we need async - we'll handle this differently
    # For now, return None and handle in the endpoint
    return None


async def get_user_role_async(user: Optional[User], session: AsyncSession) -> Optional[str]:
    """
    Get user's role from their profile (async version).
    
    Args:
        user: User object or None
        session: Database session
        
    Returns:
        Role string or None for public users
    """
    if not user:
        return None
    
    profile_repo = UserProfileRepository()
    profile = await profile_repo.get_by_user_id(session, user.uuid)
    
    if profile and hasattr(profile, 'role') and profile.role:
        return profile.role
    
    return FREE_USER


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:
    """
    Get the current authenticated user from Bearer token.
    
    Raises HTTPException if token is invalid or user not found.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Decode token
    try:
        payload = decode_token(token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Given token not valid for any token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Given token not valid for any token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database (with multi-tier caching optimization)
    user = None
    
    # TIER 1: Check request-scoped cache (fastest - prevents duplicate queries in same request)
    global _request_cache
    user_in_request_cache = user_id in _request_cache
    if user_in_request_cache:
        user = _request_cache.get(user_id)
    
    # TIER 2: Check TTL cache if request cache missed
    if not user and CACHE_AVAILABLE and _user_cache is not None:
        user = _user_cache.get(user_id)
        if user:
            # Store in request cache for this request
            _request_cache[user_id] = user
    
    # TIER 3: Query database if both caches missed (slowest)
    if not user:
        # OPTIMIZATION: Add query timeout and execution hints
        user_repo = UserRepository()
        try:
            # Set a timeout for the query to prevent hanging (5 seconds max)
            user = await asyncio.wait_for(
                user_repo.get_by_uuid(session, user_id),
                timeout=5.0
            )
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database query timeout - service temporarily unavailable",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Cache the user in BOTH caches if found
        if user:
            # Store in request cache
            _request_cache[user_id] = user
            # Prevent request cache from growing too large (memory leak protection)
            if len(_request_cache) > _request_cache_max_size:
                # Remove oldest entries (simple FIFO eviction)
                keys_to_remove = list(_request_cache.keys())[:-_request_cache_max_size]
                for key in keys_to_remove:
                    _request_cache.pop(key, None)
            
            # Store in TTL cache
            if CACHE_AVAILABLE and _user_cache is not None:
                _user_cache[user_id] = user
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Given token not valid for any token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Ensure the current user is active.
    
    Raises HTTPException if user is inactive.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"non_field_errors": ["User account is disabled"]}
        )
    
    return current_user


def get_user_role(profile: Optional[object]) -> str:
    """
    Helper function to get user role from profile.
    
    Returns the role from profile, or FREE_USER as default.
    """
    if profile and hasattr(profile, 'role') and profile.role:
        return profile.role
    return FREE_USER


def is_unlimited_credits_role(role: str) -> bool:
    """
    Check if a user role has unlimited credits (no deduction).
    
    Args:
        role: User role string
        
    Returns:
        True if role has unlimited credits (SuperAdmin/Admin), False otherwise
    """
    return role in UNLIMITED_CREDITS_ROLES


async def get_current_admin(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> User:
    """
    Ensure the current user is an admin or super admin.
    
    Checks the user's profile role. If profile doesn't exist, defaults to FREE_USER.
    Raises HTTPException (403 Forbidden) if user is not an admin or super admin.
    """
    profile_repo = UserProfileRepository()
    profile = await profile_repo.get_by_user_id(session, current_user.uuid)
    
    user_role = get_user_role(profile)
    
    if user_role not in [ADMIN, SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action. Admin role required."
        )
    
    return current_user


async def get_current_super_admin(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> User:
    """
    Ensure the current user is a super admin.
    
    Checks the user's profile role. If profile doesn't exist, defaults to FREE_USER.
    Raises HTTPException (403 Forbidden) if user is not a super admin.
    """
    profile_repo = UserProfileRepository()
    profile = await profile_repo.get_by_user_id(session, current_user.uuid)
    
    user_role = get_user_role(profile)
    
    if user_role != SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action. Super Admin role required."
        )
    
    return current_user


async def get_current_admin_or_super_admin(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> User:
    """
    Ensure the current user is an admin or super admin.
    
    This is an alias for get_current_admin for clarity.
    """
    return await get_current_admin(current_user, session)


async def get_current_pro_user(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> User:
    """
    Ensure the current user is a pro user.
    
    Checks the user's profile role. If profile doesn't exist, defaults to FREE_USER.
    Raises HTTPException (403 Forbidden) if user is not a pro user.
    """
    profile_repo = UserProfileRepository()
    profile = await profile_repo.get_by_user_id(session, current_user.uuid)
    
    user_role = get_user_role(profile)
    
    if user_role != PRO_USER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action. Pro User role required."
        )
    
    return current_user


async def get_current_free_or_pro_user(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> User:
    """
    Ensure the current user is a free user or pro user.
    
    Checks the user's profile role. If profile doesn't exist, defaults to FREE_USER.
    Raises HTTPException (403 Forbidden) if user is not a free or pro user.
    """
    profile_repo = UserProfileRepository()
    profile = await profile_repo.get_by_user_id(session, current_user.uuid)
    
    user_role = get_user_role(profile)
    
    if user_role not in [FREE_USER, PRO_USER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action. Free or Pro User role required."
        )
    
    return current_user


async def check_can_modify_resources(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> User:
    """
    Check if user can modify (update/delete) resources.
    
    Free users can only create and read, not update or delete.
    Pro users, Admin, and Super Admin can do full CRUD.
    """
    profile_repo = UserProfileRepository()
    profile = await profile_repo.get_by_user_id(session, current_user.uuid)
    
    user_role = get_user_role(profile)
    
    if user_role == FREE_USER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Free users can only create and read resources. Upgrade to Pro for full access."
        )
    
    return current_user


def resolve_pagination_params(
    filters: object,  # Any filter params with page_size attribute
    limit: Optional[int],
    cap_explicit_limit: bool = False,
) -> Optional[int]:
    """
    Choose the most appropriate page size within configured bounds.
    
    This is a shared function for resolving pagination parameters across all endpoints.
    It handles the common pattern of checking explicit limit first, then page_size in filters,
    with optional capping based on MAX_PAGE_SIZE.
    
    Args:
        filters: Filter params object with optional page_size attribute
        limit: Explicit limit from query parameter
        cap_explicit_limit: If True, cap explicit limit at MAX_PAGE_SIZE (default: False)
        
    Returns:
        Resolved limit value (None = unlimited)
        
    Example:
        # For contacts endpoint (caps explicit limit)
        resolved = resolve_pagination_params(filters, limit, cap_explicit_limit=True)
        
        # For companies endpoints (no cap on explicit limit)
        resolved = resolve_pagination_params(filters, limit, cap_explicit_limit=False)
    """
    # If explicit limit is provided
    if limit is not None:
        if cap_explicit_limit and settings.MAX_PAGE_SIZE is not None:
            resolved = min(limit, settings.MAX_PAGE_SIZE)
            return resolved
        return limit
    
    # If page_size is specified in filters, use it (with cap if MAX_PAGE_SIZE is set)
    if hasattr(filters, "page_size") and filters.page_size is not None:
        if settings.MAX_PAGE_SIZE is not None:
            resolved = min(filters.page_size, settings.MAX_PAGE_SIZE)
            return resolved
        return filters.page_size
    
    # Default: unlimited (None)
    return None

