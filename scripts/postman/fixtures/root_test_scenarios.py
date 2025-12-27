"""Comprehensive test scenarios for Root API endpoints.

This module defines all test scenarios for the Root API,
covering API metadata and health check endpoints.
"""

from typing import Dict, List, Any


class RootTestScenarios:
    """Comprehensive test scenarios for Root API endpoints."""
    
    @staticmethod
    def get_metadata_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for API metadata endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "metadata",
                "name": "get_api_metadata",
                "description": "Get API metadata (name, version, docs)",
                "method": "GET",
                "endpoint": "/api/v1/",
                "query_params": {},
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["name", "version", "docs"],
                    "name_is_string": True,
                    "version_is_string": True,
                    "docs_is_string": True
                }
            },
            {
                "category": "metadata",
                "name": "get_api_metadata_without_auth",
                "description": "Get API metadata without authentication (public endpoint)",
                "method": "GET",
                "endpoint": "/api/v1/",
                "query_params": {},
                "headers": {},  # No Authorization header
                "expected_status": [200],  # Should work without auth
                "validate_response": {
                    "has_fields": ["name", "version", "docs"]
                }
            },
            {
                "category": "metadata",
                "name": "get_api_metadata_response_structure",
                "description": "Verify API metadata response structure",
                "method": "GET",
                "endpoint": "/api/v1/",
                "query_params": {},
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["name", "version", "docs"],
                    "name_is_string": True,
                    "version_is_string": True,
                    "docs_is_string": True,
                    "name_not_empty": True,
                    "version_not_empty": True
                }
            },
        ]
    
    @staticmethod
    def get_health_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for API health endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "health",
                "name": "get_api_health",
                "description": "Get API health status",
                "method": "GET",
                "endpoint": "/api/v1/health/",
                "query_params": {},
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["status", "environment"],
                    "status_is_string": True,
                    "environment_is_string": True
                }
            },
            {
                "category": "health",
                "name": "get_api_health_without_auth",
                "description": "Get API health without authentication (public endpoint)",
                "method": "GET",
                "endpoint": "/api/v1/health/",
                "query_params": {},
                "headers": {},  # No Authorization header
                "expected_status": [200],  # Should work without auth
                "validate_response": {
                    "has_fields": ["status", "environment"]
                }
            },
            {
                "category": "health",
                "name": "get_api_health_response_structure",
                "description": "Verify API health response structure",
                "method": "GET",
                "endpoint": "/api/v1/health/",
                "query_params": {},
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["status", "environment"],
                    "status_is_string": True,
                    "environment_is_string": True,
                    "status_not_empty": True,
                    "environment_not_empty": True
                }
            },
            {
                "category": "health",
                "name": "get_api_health_status_value",
                "description": "Verify health status is 'healthy'",
                "method": "GET",
                "endpoint": "/api/v1/health/",
                "query_params": {},
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["status", "environment"],
                    "status": "healthy"  # Expected status value
                }
            },
        ]
    
    @staticmethod
    def get_all_scenarios() -> Dict[str, List[Dict[str, Any]]]:
        """Get all test scenarios organized by category.
        
        Returns:
            Dictionary mapping category names to lists of scenarios
        """
        return {
            "metadata": RootTestScenarios.get_metadata_scenarios(),
            "health": RootTestScenarios.get_health_scenarios(),
        }


This module defines all test scenarios for the Root API,
covering API metadata and health check endpoints.
"""

from typing import Dict, List, Any


class RootTestScenarios:
    """Comprehensive test scenarios for Root API endpoints."""
    
    @staticmethod
    def get_metadata_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for API metadata endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "metadata",
                "name": "get_api_metadata",
                "description": "Get API metadata (name, version, docs)",
                "method": "GET",
                "endpoint": "/api/v1/",
                "query_params": {},
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["name", "version", "docs"],
                    "name_is_string": True,
                    "version_is_string": True,
                    "docs_is_string": True
                }
            },
            {
                "category": "metadata",
                "name": "get_api_metadata_without_auth",
                "description": "Get API metadata without authentication (public endpoint)",
                "method": "GET",
                "endpoint": "/api/v1/",
                "query_params": {},
                "headers": {},  # No Authorization header
                "expected_status": [200],  # Should work without auth
                "validate_response": {
                    "has_fields": ["name", "version", "docs"]
                }
            },
            {
                "category": "metadata",
                "name": "get_api_metadata_response_structure",
                "description": "Verify API metadata response structure",
                "method": "GET",
                "endpoint": "/api/v1/",
                "query_params": {},
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["name", "version", "docs"],
                    "name_is_string": True,
                    "version_is_string": True,
                    "docs_is_string": True,
                    "name_not_empty": True,
                    "version_not_empty": True
                }
            },
        ]
    
    @staticmethod
    def get_health_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for API health endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "health",
                "name": "get_api_health",
                "description": "Get API health status",
                "method": "GET",
                "endpoint": "/api/v1/health/",
                "query_params": {},
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["status", "environment"],
                    "status_is_string": True,
                    "environment_is_string": True
                }
            },
            {
                "category": "health",
                "name": "get_api_health_without_auth",
                "description": "Get API health without authentication (public endpoint)",
                "method": "GET",
                "endpoint": "/api/v1/health/",
                "query_params": {},
                "headers": {},  # No Authorization header
                "expected_status": [200],  # Should work without auth
                "validate_response": {
                    "has_fields": ["status", "environment"]
                }
            },
            {
                "category": "health",
                "name": "get_api_health_response_structure",
                "description": "Verify API health response structure",
                "method": "GET",
                "endpoint": "/api/v1/health/",
                "query_params": {},
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["status", "environment"],
                    "status_is_string": True,
                    "environment_is_string": True,
                    "status_not_empty": True,
                    "environment_not_empty": True
                }
            },
            {
                "category": "health",
                "name": "get_api_health_status_value",
                "description": "Verify health status is 'healthy'",
                "method": "GET",
                "endpoint": "/api/v1/health/",
                "query_params": {},
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["status", "environment"],
                    "status": "healthy"  # Expected status value
                }
            },
        ]
    
    @staticmethod
    def get_all_scenarios() -> Dict[str, List[Dict[str, Any]]]:
        """Get all test scenarios organized by category.
        
        Returns:
            Dictionary mapping category names to lists of scenarios
        """
        return {
            "metadata": RootTestScenarios.get_metadata_scenarios(),
            "health": RootTestScenarios.get_health_scenarios(),
        }


This module defines all test scenarios for the Root API,
covering API metadata and health check endpoints.
"""

from typing import Dict, List, Any


class RootTestScenarios:
    """Comprehensive test scenarios for Root API endpoints."""
    
    @staticmethod
    def get_metadata_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for API metadata endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "metadata",
                "name": "get_api_metadata",
                "description": "Get API metadata (name, version, docs)",
                "method": "GET",
                "endpoint": "/api/v1/",
                "query_params": {},
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["name", "version", "docs"],
                    "name_is_string": True,
                    "version_is_string": True,
                    "docs_is_string": True
                }
            },
            {
                "category": "metadata",
                "name": "get_api_metadata_without_auth",
                "description": "Get API metadata without authentication (public endpoint)",
                "method": "GET",
                "endpoint": "/api/v1/",
                "query_params": {},
                "headers": {},  # No Authorization header
                "expected_status": [200],  # Should work without auth
                "validate_response": {
                    "has_fields": ["name", "version", "docs"]
                }
            },
            {
                "category": "metadata",
                "name": "get_api_metadata_response_structure",
                "description": "Verify API metadata response structure",
                "method": "GET",
                "endpoint": "/api/v1/",
                "query_params": {},
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["name", "version", "docs"],
                    "name_is_string": True,
                    "version_is_string": True,
                    "docs_is_string": True,
                    "name_not_empty": True,
                    "version_not_empty": True
                }
            },
        ]
    
    @staticmethod
    def get_health_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for API health endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "health",
                "name": "get_api_health",
                "description": "Get API health status",
                "method": "GET",
                "endpoint": "/api/v1/health/",
                "query_params": {},
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["status", "environment"],
                    "status_is_string": True,
                    "environment_is_string": True
                }
            },
            {
                "category": "health",
                "name": "get_api_health_without_auth",
                "description": "Get API health without authentication (public endpoint)",
                "method": "GET",
                "endpoint": "/api/v1/health/",
                "query_params": {},
                "headers": {},  # No Authorization header
                "expected_status": [200],  # Should work without auth
                "validate_response": {
                    "has_fields": ["status", "environment"]
                }
            },
            {
                "category": "health",
                "name": "get_api_health_response_structure",
                "description": "Verify API health response structure",
                "method": "GET",
                "endpoint": "/api/v1/health/",
                "query_params": {},
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["status", "environment"],
                    "status_is_string": True,
                    "environment_is_string": True,
                    "status_not_empty": True,
                    "environment_not_empty": True
                }
            },
            {
                "category": "health",
                "name": "get_api_health_status_value",
                "description": "Verify health status is 'healthy'",
                "method": "GET",
                "endpoint": "/api/v1/health/",
                "query_params": {},
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["status", "environment"],
                    "status": "healthy"  # Expected status value
                }
            },
        ]
    
    @staticmethod
    def get_all_scenarios() -> Dict[str, List[Dict[str, Any]]]:
        """Get all test scenarios organized by category.
        
        Returns:
            Dictionary mapping category names to lists of scenarios
        """
        return {
            "metadata": RootTestScenarios.get_metadata_scenarios(),
            "health": RootTestScenarios.get_health_scenarios(),
        }


This module defines all test scenarios for the Root API,
covering API metadata and health check endpoints.
"""

from typing import Dict, List, Any


class RootTestScenarios:
    """Comprehensive test scenarios for Root API endpoints."""
    
    @staticmethod
    def get_metadata_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for API metadata endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "metadata",
                "name": "get_api_metadata",
                "description": "Get API metadata (name, version, docs)",
                "method": "GET",
                "endpoint": "/api/v1/",
                "query_params": {},
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["name", "version", "docs"],
                    "name_is_string": True,
                    "version_is_string": True,
                    "docs_is_string": True
                }
            },
            {
                "category": "metadata",
                "name": "get_api_metadata_without_auth",
                "description": "Get API metadata without authentication (public endpoint)",
                "method": "GET",
                "endpoint": "/api/v1/",
                "query_params": {},
                "headers": {},  # No Authorization header
                "expected_status": [200],  # Should work without auth
                "validate_response": {
                    "has_fields": ["name", "version", "docs"]
                }
            },
            {
                "category": "metadata",
                "name": "get_api_metadata_response_structure",
                "description": "Verify API metadata response structure",
                "method": "GET",
                "endpoint": "/api/v1/",
                "query_params": {},
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["name", "version", "docs"],
                    "name_is_string": True,
                    "version_is_string": True,
                    "docs_is_string": True,
                    "name_not_empty": True,
                    "version_not_empty": True
                }
            },
        ]
    
    @staticmethod
    def get_health_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for API health endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "health",
                "name": "get_api_health",
                "description": "Get API health status",
                "method": "GET",
                "endpoint": "/api/v1/health/",
                "query_params": {},
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["status", "environment"],
                    "status_is_string": True,
                    "environment_is_string": True
                }
            },
            {
                "category": "health",
                "name": "get_api_health_without_auth",
                "description": "Get API health without authentication (public endpoint)",
                "method": "GET",
                "endpoint": "/api/v1/health/",
                "query_params": {},
                "headers": {},  # No Authorization header
                "expected_status": [200],  # Should work without auth
                "validate_response": {
                    "has_fields": ["status", "environment"]
                }
            },
            {
                "category": "health",
                "name": "get_api_health_response_structure",
                "description": "Verify API health response structure",
                "method": "GET",
                "endpoint": "/api/v1/health/",
                "query_params": {},
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["status", "environment"],
                    "status_is_string": True,
                    "environment_is_string": True,
                    "status_not_empty": True,
                    "environment_not_empty": True
                }
            },
            {
                "category": "health",
                "name": "get_api_health_status_value",
                "description": "Verify health status is 'healthy'",
                "method": "GET",
                "endpoint": "/api/v1/health/",
                "query_params": {},
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["status", "environment"],
                    "status": "healthy"  # Expected status value
                }
            },
        ]
    
    @staticmethod
    def get_all_scenarios() -> Dict[str, List[Dict[str, Any]]]:
        """Get all test scenarios organized by category.
        
        Returns:
            Dictionary mapping category names to lists of scenarios
        """
        return {
            "metadata": RootTestScenarios.get_metadata_scenarios(),
            "health": RootTestScenarios.get_health_scenarios(),
        }

