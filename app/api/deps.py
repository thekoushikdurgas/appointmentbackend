"""Shared dependencies for API endpoints."""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import decode_token
from app.db.session import get_db
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
        logger.warning("Authentication failed: no token provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Decode token
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        logger.warning("Authentication failed: invalid token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Given token not valid for any token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        logger.warning("Authentication failed: missing user ID in token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Given token not valid for any token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    user_repo = UserRepository()
    user = await user_repo.get_by_uuid(session, user_id)
    if not user:
        logger.warning("Authentication failed: user not found: %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Given token not valid for any token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.debug("User authenticated: id=%s email=%s", user.id, user.email)
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Ensure the current user is active.
    
    Raises HTTPException if user is inactive.
    """
    if not current_user.is_active:
        logger.warning("Access denied: user is inactive: %s", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"non_field_errors": ["User account is disabled"]}
        )
    
    return current_user


async def get_current_admin(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> User:
    """
    Ensure the current user is an admin.
    
    Checks the user's profile role. If profile doesn't exist, defaults to "Member".
    Raises HTTPException (403 Forbidden) if user is not an admin.
    """
    profile_repo = UserProfileRepository()
    profile = await profile_repo.get_by_user_id(session, current_user.id)
    
    # Default role is "Member" if profile doesn't exist
    user_role = profile.role if profile and profile.role else "Member"
    
    if user_role != "Admin":
        logger.warning("Access denied: user is not admin: user_id=%s role=%s", current_user.id, user_role)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action. Admin role required."
        )
    
    logger.debug("Admin access granted: user_id=%s email=%s", current_user.id, current_user.email)
    return current_user

