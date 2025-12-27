"""Access control utilities for role-based content filtering."""

from typing import List, Optional

from app.core.constants import ADMIN, FREE_USER, PRO_USER, SUPER_ADMIN
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Role hierarchy: lower index = lower privilege
ROLE_HIERARCHY = {
    "Public": 0,
    FREE_USER: 1,
    PRO_USER: 2,
    ADMIN: 3,
    SUPER_ADMIN: 4,
}

# Role names for consistency
PUBLIC_ROLE = "Public"


def get_role_level(role: Optional[str]) -> int:
    """
    Get the hierarchy level of a role.
    
    Args:
        role: User role string or None for public users
        
    Returns:
        Integer level (0 = Public, 1 = FreeUser, etc.)
    """
    if role is None:
        return ROLE_HIERARCHY[PUBLIC_ROLE]
    return ROLE_HIERARCHY.get(role, ROLE_HIERARCHY[PUBLIC_ROLE])


def has_role_access(user_role: Optional[str], allowed_roles: List[str]) -> bool:
    """
    Check if a user role has access based on allowed roles list.
    
    Rules:
    - Empty allowed_roles list means accessible to all (including public)
    - If user_role is None (public), only accessible if "Public" in allowed_roles or list is empty
    - Admin and SuperAdmin always have access (they see everything)
    - Otherwise, check if user_role is in allowed_roles
    
    Args:
        user_role: User's role (None for public users)
        allowed_roles: List of roles that can access the content
        
    Returns:
        True if user has access, False otherwise
    """
    # Empty list means accessible to all
    if not allowed_roles:
        return True
    
    # Admin and SuperAdmin always have access
    if user_role in [ADMIN, SUPER_ADMIN]:
        return True
    
    # Public users (None) - check if Public is explicitly allowed or list is empty
    if user_role is None:
        return PUBLIC_ROLE in allowed_roles or not allowed_roles
    
    # Check if user's role is in allowed roles
    return user_role in allowed_roles


def get_effective_role(user_role: Optional[str]) -> str:
    """
    Get the effective role string for a user.
    
    Args:
        user_role: User's role (None for public users)
        
    Returns:
        Role string (or "Public" if None)
    """
    return user_role if user_role is not None else PUBLIC_ROLE


def get_default_access_control() -> dict:
    """
    Get default access control metadata.
    
    Default behavior: paid-only (ProUser, Admin, SuperAdmin)
    
    Returns:
        Dictionary with default access control settings
    """
    return {
        "allowed_roles": [PRO_USER, ADMIN, SUPER_ADMIN],
        "restriction_type": "full",
        "upgrade_message": "Upgrade to Pro to unlock this feature",
        "required_role": PRO_USER,
    }


def is_role_higher_or_equal(role1: Optional[str], role2: str) -> bool:
    """
    Check if role1 is higher or equal to role2 in hierarchy.
    
    Args:
        role1: First role (None = Public)
        role2: Second role
        
    Returns:
        True if role1 >= role2 in hierarchy
    """
    level1 = get_role_level(role1)
    level2 = get_role_level(role2)
    return level1 >= level2

