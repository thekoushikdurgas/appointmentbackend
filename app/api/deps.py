"""Shared dependencies for API endpoints."""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.constants import ADMIN, FREE_USER, PRO_USER, SUPER_ADMIN
from app.core.logging import get_logger
from app.core.security import decode_token
from app.db.session import AsyncSessionLocal, get_db
from app.models.user import User
from app.repositories.user import UserProfileRepository, UserRepository

settings = get_settings()
logger = get_logger(__name__)

# OAuth2 scheme for Bearer token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V2_PREFIX}/auth/login",
    auto_error=False
)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:
    """
    Get the current authenticated user from Bearer token.
    
    Raises HTTPException if token is invalid or user not found.
    """
    if not token:
        logger.debug("Authentication failed: no token provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Decode token
    try:
        payload = decode_token(token)
    except Exception as e:
        logger.debug("Authentication failed: token decode error: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    
    if not payload or payload.get("type") != "access":
        logger.debug("Authentication failed: invalid token type or payload")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Given token not valid for any token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        logger.debug("Authentication failed: missing user ID in token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Given token not valid for any token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    user_repo = UserRepository()
    user = await user_repo.get_by_uuid(session, user_id)
    if not user:
        logger.debug("Authentication failed: user not found: %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Given token not valid for any token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.debug("User authenticated: uuid=%s email=%s", user.uuid, user.email)
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Ensure the current user is active.
    
    Raises HTTPException if user is inactive.
    """
    if not current_user.is_active:
        logger.warning("Access denied: user is inactive: %s", current_user.uuid)
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
    from app.core.constants import UNLIMITED_CREDITS_ROLES
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
        logger.warning("Access denied: user is not admin: user_uuid=%s role=%s", current_user.uuid, user_role)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action. Admin role required."
        )
    
    logger.debug("Admin access granted: user_uuid=%s email=%s", current_user.uuid, current_user.email)
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
        logger.warning("Access denied: user is not super admin: user_uuid=%s role=%s", current_user.uuid, user_role)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action. Super Admin role required."
        )
    
    logger.debug("Super admin access granted: user_uuid=%s email=%s", current_user.uuid, current_user.email)
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
        logger.warning("Access denied: user is not pro user: user_uuid=%s role=%s", current_user.uuid, user_role)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action. Pro User role required."
        )
    
    logger.debug("Pro user access granted: user_uuid=%s email=%s", current_user.uuid, current_user.email)
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
        logger.warning("Access denied: user is not free or pro user: user_uuid=%s role=%s", current_user.uuid, user_role)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action. Free or Pro User role required."
        )
    
    logger.debug("Free or pro user access granted: user_uuid=%s email=%s", current_user.uuid, current_user.email)
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
        logger.warning("Access denied: free user cannot modify resources: user_uuid=%s", current_user.uuid)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Free users can only create and read resources. Upgrade to Pro for full access."
        )
    
    logger.debug("Modify access granted: user_uuid=%s role=%s", current_user.uuid, user_role)
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
        
        # For companies/apollo endpoints (no cap on explicit limit)
        resolved = resolve_pagination_params(filters, limit, cap_explicit_limit=False)
    """
    # If explicit limit is provided
    if limit is not None:
        if cap_explicit_limit and settings.MAX_PAGE_SIZE is not None:
            resolved = min(limit, settings.MAX_PAGE_SIZE)
            logger.debug(
                "Resolved pagination: explicit limit=%d capped to %d",
                limit,
                resolved,
            )
            return resolved
        logger.debug(
            "Resolved pagination: explicit limit=%d (no cap applied)",
            limit,
        )
        return limit
    
    # If page_size is specified in filters, use it (with cap if MAX_PAGE_SIZE is set)
    if hasattr(filters, "page_size") and filters.page_size is not None:
        if settings.MAX_PAGE_SIZE is not None:
            resolved = min(filters.page_size, settings.MAX_PAGE_SIZE)
            logger.debug(
                "Resolved pagination: page_size=%d capped to %d",
                filters.page_size,
                resolved,
            )
            return resolved
        logger.debug(
            "Resolved pagination: page_size=%d (no cap)",
            filters.page_size,
        )
        return filters.page_size
    
    # Default: unlimited (None)
    logger.debug(
        "Resolved pagination: default=unlimited (None)",
    )
    return None

