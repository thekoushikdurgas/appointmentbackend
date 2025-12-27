"""Service for filtering page content based on user roles (marketing and dashboard pages)."""

from typing import Any, Dict, List, Optional

from app.utils.access_control import (
    ADMIN,
    PUBLIC_ROLE,
    SUPER_ADMIN,
    get_default_access_control,
    has_role_access,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AccessControlService:
    """Service for applying access control to page content (marketing and dashboard pages)."""
    
    def filter_page_by_role(
        self,
        page_data: Dict[str, Any],
        user_role: Optional[str]
    ) -> Dict[str, Any]:
        """
        Filter page content based on user role.
        
        Works for both marketing pages and dashboard pages.
        
        Args:
            page_data: Full page data from MongoDB
            user_role: User's role (None for public users)
            
        Returns:
            Filtered page data with access control metadata
        """
        # Admin and SuperAdmin see everything - no filtering
        if user_role in [ADMIN, SUPER_ADMIN]:
            return page_data
        
        # Create a copy to avoid modifying original
        filtered_page = page_data.copy()
        
        # Filter sections
        if "sections" in filtered_page and isinstance(filtered_page["sections"], dict):
            filtered_page["sections"] = self._filter_sections(
                filtered_page["sections"],
                user_role
            )
        
        return filtered_page
    
    def _filter_sections(
        self,
        sections: Dict[str, Any],
        user_role: Optional[str]
    ) -> Dict[str, Any]:
        """Filter sections based on access control."""
        filtered_sections = {}
        
        for section_key, section_data in sections.items():
            if not isinstance(section_data, dict):
                # Non-dict section data - include as-is
                filtered_sections[section_key] = section_data
                continue
            
            # Get access control for this section
            access_control = section_data.get("access_control")
            
            # If no access control, use default (paid-only)
            if not access_control:
                access_control = get_default_access_control()
                section_data = section_data.copy()
                section_data["access_control"] = access_control
            
            # Check if user has access
            allowed_roles = access_control.get("allowed_roles", [])
            has_access = has_role_access(user_role, allowed_roles)
            
            if has_access:
                # User has access - include full content
                filtered_section = section_data.copy()
                filtered_section["is_locked"] = False
                filtered_section["access_metadata"] = {
                    "has_access": True,
                    "user_role": user_role or PUBLIC_ROLE,
                }
                
                # Filter nested components if they exist
                if "components" in filtered_section and isinstance(filtered_section["components"], list):
                    filtered_section["components"] = self._filter_components(
                        filtered_section["components"],
                        user_role
                    )
                
                filtered_sections[section_key] = filtered_section
            else:
                # User doesn't have access - apply restriction
                restriction_type = access_control.get("restriction_type", "full")
                
                if restriction_type == "hidden":
                    # Don't include this section at all
                    continue
                
                # Create locked section metadata
                locked_section = {
                    "is_locked": True,
                    "restriction_type": restriction_type,
                    "upgrade_message": access_control.get(
                        "upgrade_message",
                        "Upgrade to unlock this feature"
                    ),
                    "required_role": access_control.get("required_role"),
                    "redirect_path": access_control.get("redirect_path"),
                    "redirect_message": access_control.get("redirect_message"),
                    "access_metadata": {
                        "has_access": False,
                        "user_role": user_role or PUBLIC_ROLE,
                    },
                }
                
                # Include partial content if restriction_type is "partial"
                if restriction_type == "partial":
                    # Include title and description but not full content
                    if "title" in section_data:
                        locked_section["title"] = section_data["title"]
                    if "description" in section_data:
                        locked_section["description"] = section_data.get("description", "")
                    # Don't include full content
                elif restriction_type == "full":
                    # Only include metadata, no content
                    if "title" in section_data:
                        locked_section["title"] = section_data["title"]
                
                filtered_sections[section_key] = locked_section
        
        return filtered_sections
    
    def _filter_components(
        self,
        components: List[Dict[str, Any]],
        user_role: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Filter components within a section based on access control."""
        filtered_components = []
        
        for component in components:
            if not isinstance(component, dict):
                filtered_components.append(component)
                continue
            
            # Get access control for this component
            access_control = component.get("access_control")
            
            # If no access control, use default (paid-only)
            if not access_control:
                access_control = get_default_access_control()
                component = component.copy()
                component["access_control"] = access_control
            
            # Check if user has access
            allowed_roles = access_control.get("allowed_roles", [])
            has_access = has_role_access(user_role, allowed_roles)
            
            if has_access:
                # User has access - include full component
                filtered_component = component.copy()
                filtered_component["is_locked"] = False
                filtered_components.append(filtered_component)
            else:
                # User doesn't have access - apply restriction
                restriction_type = access_control.get("restriction_type", "full")
                
                if restriction_type == "hidden":
                    # Don't include this component
                    continue
                
                # Create locked component metadata
                locked_component = {
                    "is_locked": True,
                    "restriction_type": restriction_type,
                    "upgrade_message": access_control.get(
                        "upgrade_message",
                        "Upgrade to unlock this feature"
                    ),
                    "required_role": access_control.get("required_role"),
                    "redirect_path": access_control.get("redirect_path"),
                    "redirect_message": access_control.get("redirect_message"),
                }
                
                # Include partial content if restriction_type is "partial"
                if restriction_type == "partial":
                    if "title" in component:
                        locked_component["title"] = component["title"]
                    if "description" in component:
                        locked_component["description"] = component.get("description", "")
                
                filtered_components.append(locked_component)
        
        return filtered_components
    
    def check_component_access(
        self,
        access_control: Optional[Dict[str, Any]],
        user_role: Optional[str]
    ) -> bool:
        """
        Check if a user has access to a component based on access control.
        
        Args:
            access_control: Access control metadata
            user_role: User's role (None for public users)
            
        Returns:
            True if user has access, False otherwise
        """
        if not access_control:
            # No access control - use default (paid-only)
            default_ac = get_default_access_control()
            allowed_roles = default_ac.get("allowed_roles", [])
        else:
            allowed_roles = access_control.get("allowed_roles", [])
        
        return has_role_access(user_role, allowed_roles)

