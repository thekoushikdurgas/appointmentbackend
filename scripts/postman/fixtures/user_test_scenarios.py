"""Comprehensive test scenarios for user API endpoints."""

from typing import Dict, Any, List, Optional
import uuid


class UserTestScenarios:
    """Comprehensive test scenarios for user API endpoints."""
    
    @staticmethod
    def get_registration_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for user registration endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        unique_id = uuid.uuid4().hex[:8]
        
        return [
            {
                "name": "valid_registration_with_geolocation",
                "description": "Valid registration with all fields including geolocation",
                "body": {
                    "name": f"Test User {unique_id}",
                    "email": f"test_{unique_id}@example.com",
                    "password": "testpass123",
                    "geolocation": {
                        "ip": "192.168.1.100",
                        "continent": "North America",
                        "continent_code": "NA",
                        "country": "United States",
                        "country_code": "US",
                        "region": "CA",
                        "region_name": "California",
                        "city": "San Francisco",
                        "district": "",
                        "zip": "94102",
                        "lat": 37.7749,
                        "lon": -122.4194,
                        "timezone": "America/Los_Angeles",
                        "offset": -28800,
                        "currency": "USD",
                        "isp": "Test ISP",
                        "org": "Test Org",
                        "asname": "",
                        "reverse": "",
                        "device": "Mozilla/5.0 (Test Browser)",
                        "proxy": False,
                        "hosting": False
                    }
                },
                "expected_status": [201]
            },
            {
                "name": "valid_registration_without_geolocation",
                "description": "Valid registration without geolocation (optional field)",
                "body": {
                    "name": f"Test User {uuid.uuid4().hex[:8]}",
                    "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
                    "password": "testpass123"
                },
                "expected_status": [201]
            },
            {
                "name": "registration_existing_email",
                "description": "Registration with existing email (should fail)",
                "body": {
                    "name": "Test User",
                    "email": "existing@example.com",  # Assuming this exists
                    "password": "testpass123"
                },
                "expected_status": [400]
            },
            {
                "name": "registration_short_password",
                "description": "Registration with password too short (< 8 characters)",
                "body": {
                    "name": "Test User",
                    "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
                    "password": "short"
                },
                "expected_status": [400, 422]  # FastAPI returns 422 for validation errors
            },
            {
                "name": "registration_long_password",
                "description": "Registration with password too long (> 72 characters)",
                "body": {
                    "name": "Test User",
                    "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
                    "password": "a" * 73
                },
                "expected_status": [400, 422]  # FastAPI returns 422 for validation errors
            },
            {
                "name": "registration_invalid_email",
                "description": "Registration with invalid email format",
                "body": {
                    "name": "Test User",
                    "email": "not-an-email",
                    "password": "testpass123"
                },
                "expected_status": [422]
            },
            {
                "name": "registration_missing_fields",
                "description": "Registration with missing required fields",
                "body": {
                    "email": f"test_{uuid.uuid4().hex[:8]}@example.com"
                    # Missing name and password
                },
                "expected_status": [422]
            }
        ]
    
    @staticmethod
    def get_login_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for user login endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "name": "valid_login",
                "description": "Valid login with correct credentials",
                "body": {
                    "email": "test@example.com",
                    "password": "testpass123",
                    "geolocation": {
                        "ip": "192.168.1.100",
                        "continent": "North America",
                        "country": "United States",
                        "city": "San Francisco"
                    }
                },
                "expected_status": [200]
            },
            {
                "name": "login_invalid_credentials",
                "description": "Login with invalid credentials",
                "body": {
                    "email": "test@example.com",
                    "password": "wrongpassword"
                },
                "expected_status": [400]
            },
            {
                "name": "login_disabled_account",
                "description": "Login with disabled account (should fail)",
                "body": {
                    "email": "disabled@example.com",
                    "password": "testpass123"
                },
                "expected_status": [400]
            },
            {
                "name": "login_missing_fields",
                "description": "Login with missing required fields",
                "body": {
                    "email": "test@example.com"
                    # Missing password
                },
                "expected_status": [422]
            }
        ]
    
    @staticmethod
    def get_token_management_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for token management endpoints.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "name": "logout_with_refresh_token",
                "description": "Logout with refresh token",
                "body": {
                    "refresh_token": "{{refresh_token}}"
                },
                "expected_status": [200]
            },
            {
                "name": "logout_without_refresh_token",
                "description": "Logout without refresh token (still succeeds)",
                "body": {},
                "expected_status": [200]
            },
            {
                "name": "refresh_valid_token",
                "description": "Refresh with valid refresh token",
                "body": {
                    "refresh_token": "{{refresh_token}}"
                },
                "expected_status": [200]
            },
            {
                "name": "refresh_invalid_token",
                "description": "Refresh with invalid token",
                "body": {
                    "refresh_token": "invalid_token_12345"
                },
                "expected_status": [400]
            },
            {
                "name": "refresh_blacklisted_token",
                "description": "Refresh with blacklisted token (after logout)",
                "body": {
                    "refresh_token": "{{blacklisted_refresh_token}}"
                },
                "expected_status": [400]
            }
        ]
    
    @staticmethod
    def get_profile_management_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for profile management endpoints.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "name": "get_profile",
                "description": "Get current user profile",
                "method": "GET",
                "expected_status": [200]
            },
            {
                "name": "update_partial_profile",
                "description": "Update profile with partial fields",
                "method": "PUT",
                "body": {
                    "name": "Updated Name",
                    "job_title": "Senior Engineer"
                },
                "expected_status": [200]
            },
            {
                "name": "update_full_profile",
                "description": "Update profile with all fields",
                "method": "PUT",
                "body": {
                    "name": "Updated Full Name",
                    "job_title": "Senior Software Engineer",
                    "bio": "Updated bio with more details",
                    "timezone": "America/New_York",
                    "avatar_url": "https://picsum.photos/seed/123/40/40",
                    "notifications": {
                        "weeklyReports": False,
                        "newLeadAlerts": True
                    }
                },
                "expected_status": [200]
            },
            {
                "name": "update_profile_invalid_data",
                "description": "Update profile with invalid data (name too long)",
                "method": "PUT",
                "body": {
                    "name": "a" * 256  # Exceeds 255 char limit
                },
                "expected_status": [400, 422]  # FastAPI returns 422 for validation errors
            },
            {
                "name": "upload_valid_avatar",
                "description": "Upload valid avatar image",
                "method": "POST",
                "endpoint": "/api/v1/users/profile/avatar/",
                "is_file_upload": True,
                "expected_status": [200]
            },
            {
                "name": "upload_oversized_avatar",
                "description": "Upload avatar file > 5MB (should fail)",
                "method": "POST",
                "endpoint": "/api/v1/users/profile/avatar/",
                "is_file_upload": True,
                "file_size": 6 * 1024 * 1024,  # 6MB
                "expected_status": [400]
            },
            {
                "name": "upload_invalid_file_type",
                "description": "Upload invalid file type (not an image)",
                "method": "POST",
                "endpoint": "/api/v1/users/profile/avatar/",
                "is_file_upload": True,
                "file_type": "text/plain",
                "expected_status": [400]
            }
        ]
    
    @staticmethod
    def get_role_management_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for role management endpoints.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "name": "self_promote_to_admin",
                "description": "Self-promote current user to admin",
                "method": "POST",
                "endpoint": "/api/v1/users/promote-to-admin/",
                "body": {},
                "expected_status": [200]
            },
            {
                "name": "super_admin_promote_user",
                "description": "Super admin promote user to super admin",
                "method": "POST",
                "endpoint": "/api/v1/users/promote-to-super-admin/",
                "query_params": {
                    "user_id": "{{user_id}}"
                },
                "expected_status": [200]
            },
            {
                "name": "non_super_admin_promote",
                "description": "Non-super admin try to promote (should fail with 403)",
                "method": "POST",
                "endpoint": "/api/v1/users/promote-to-super-admin/",
                "query_params": {
                    "user_id": "{{user_id}}"
                },
                "expected_status": [403],
                "requires_super_admin": False  # Test with regular user
            },
            {
                "name": "promote_disabled_user",
                "description": "Promote disabled user (should fail)",
                "method": "POST",
                "endpoint": "/api/v1/users/promote-to-super-admin/",
                "query_params": {
                    "user_id": "{{disabled_user_id}}"
                },
                "expected_status": [400]
            }
        ]
    
    @staticmethod
    def get_super_admin_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for super admin endpoints.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "name": "list_all_users_paginated",
                "description": "List all users with pagination",
                "method": "GET",
                "endpoint": "/api/v1/users/",
                "query_params": {
                    "limit": 100,
                    "offset": 0
                },
                "expected_status": [200],
                "requires_super_admin": True
            },
            {
                "name": "update_user_role",
                "description": "Update user role to ProUser",
                "method": "PUT",
                "endpoint": "/api/v1/users/{user_id}/role/",
                "body": {
                    "role": "ProUser"
                },
                "expected_status": [200],
                "requires_super_admin": True
            },
            {
                "name": "update_user_credits",
                "description": "Update user credits",
                "method": "PUT",
                "endpoint": "/api/v1/users/{user_id}/credits/",
                "body": {
                    "credits": 1000
                },
                "expected_status": [200],
                "requires_super_admin": True
            },
            {
                "name": "delete_user",
                "description": "Delete user account",
                "method": "DELETE",
                "endpoint": "/api/v1/users/{user_id}/",
                "expected_status": [204],
                "requires_super_admin": True
            },
            {
                "name": "delete_own_account",
                "description": "Try to delete own account (should fail)",
                "method": "DELETE",
                "endpoint": "/api/v1/users/{current_user_id}/",
                "expected_status": [400],
                "requires_super_admin": True
            },
            {
                "name": "non_super_admin_access",
                "description": "Non-super admin try to access super admin endpoint (should fail with 403)",
                "method": "GET",
                "endpoint": "/api/v1/users/",
                "expected_status": [403],
                "requires_super_admin": False  # Test with regular user
            },
            {
                "name": "get_user_statistics",
                "description": "Get user statistics",
                "method": "GET",
                "endpoint": "/api/v1/users/stats/",
                "expected_status": [200],
                "requires_super_admin": True
            },
            {
                "name": "get_user_history_with_filters",
                "description": "Get user history with filters",
                "method": "GET",
                "endpoint": "/api/v1/users/history/",
                "query_params": {
                    "user_id": "{{user_id}}",
                    "event_type": "registration",
                    "limit": 100,
                    "offset": 0
                },
                "expected_status": [200],
                "requires_super_admin": True
            }
        ]
    
    @staticmethod
    def get_all_scenarios() -> Dict[str, List[Dict[str, Any]]]:
        """Get all test scenarios organized by category.
        
        Returns:
            Dictionary mapping category to list of scenarios
        """
        return {
            "registration": UserTestScenarios.get_registration_scenarios(),
            "login": UserTestScenarios.get_login_scenarios(),
            "token_management": UserTestScenarios.get_token_management_scenarios(),
            "profile_management": UserTestScenarios.get_profile_management_scenarios(),
            "role_management": UserTestScenarios.get_role_management_scenarios(),
            "super_admin": UserTestScenarios.get_super_admin_scenarios()
        }

