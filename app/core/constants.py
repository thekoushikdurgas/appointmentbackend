"""Application-wide constants for roles and user management."""

from app.utils.logger import get_logger

logger = get_logger(__name__)

# User Roles
SUPER_ADMIN = "SuperAdmin"
ADMIN = "Admin"
FREE_USER = "FreeUser"
PRO_USER = "ProUser"

# Default role for new users
DEFAULT_ROLE = FREE_USER

# Initial credits for free users
INITIAL_FREE_CREDITS = 50

# All valid roles
VALID_ROLES = [SUPER_ADMIN, ADMIN, FREE_USER, PRO_USER]

# Roles with unlimited credits (no deduction)
UNLIMITED_CREDITS_ROLES = [SUPER_ADMIN, ADMIN]

