"""Comprehensive test scenarios for Activities API endpoints.

This module defines all test scenarios for the Activities API,
covering activity history and statistics operations.
"""

from typing import Dict, List, Any


class ActivitiesTestScenarios:
    """Comprehensive test scenarios for Activities API endpoints."""
    
    @staticmethod
    def get_list_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for list activities endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "list",
                "name": "list_all_activities",
                "description": "List all activities with default pagination",
                "method": "GET",
                "endpoint": "/api/v3/activities/",
                "query_params": {},
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["items", "total", "limit", "offset"],
                    "items_is_list": True
                }
            },
            {
                "category": "list",
                "name": "list_activities_with_pagination",
                "description": "List activities with custom pagination",
                "method": "GET",
                "endpoint": "/api/v3/activities/",
                "query_params": {
                    "limit": 50,
                    "offset": 0
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["items", "total", "limit", "offset"]
                }
            },
            {
                "category": "list",
                "name": "list_activities_filter_by_service_type_linkedin",
                "description": "List activities filtered by LinkedIn service type",
                "method": "GET",
                "endpoint": "/api/v3/activities/",
                "query_params": {
                    "service_type": "linkedin"
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["items", "total"]
                }
            },
            {
                "category": "list",
                "name": "list_activities_filter_by_service_type_email",
                "description": "List activities filtered by email service type",
                "method": "GET",
                "endpoint": "/api/v3/activities/",
                "query_params": {
                    "service_type": "email"
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["items", "total"]
                }
            },
            {
                "category": "list",
                "name": "list_activities_filter_by_action_type_search",
                "description": "List activities filtered by search action type",
                "method": "GET",
                "endpoint": "/api/v3/activities/",
                "query_params": {
                    "action_type": "search"
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["items", "total"]
                }
            },
            {
                "category": "list",
                "name": "list_activities_filter_by_action_type_export",
                "description": "List activities filtered by export action type",
                "method": "GET",
                "endpoint": "/api/v3/activities/",
                "query_params": {
                    "action_type": "export"
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["items", "total"]
                }
            },
            {
                "category": "list",
                "name": "list_activities_filter_by_status_success",
                "description": "List activities filtered by success status",
                "method": "GET",
                "endpoint": "/api/v3/activities/",
                "query_params": {
                    "status": "success"
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["items", "total"]
                }
            },
            {
                "category": "list",
                "name": "list_activities_filter_by_status_failed",
                "description": "List activities filtered by failed status",
                "method": "GET",
                "endpoint": "/api/v3/activities/",
                "query_params": {
                    "status": "failed"
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["items", "total"]
                }
            },
            {
                "category": "list",
                "name": "list_activities_filter_by_date_range",
                "description": "List activities filtered by date range",
                "method": "GET",
                "endpoint": "/api/v3/activities/",
                "query_params": {
                    "start_date": "2024-01-01T00:00:00Z",
                    "end_date": "2024-12-31T23:59:59Z"
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["items", "total"]
                }
            },
            {
                "category": "list",
                "name": "list_activities_combined_filters",
                "description": "List activities with multiple filters combined",
                "method": "GET",
                "endpoint": "/api/v3/activities/",
                "query_params": {
                    "service_type": "linkedin",
                    "action_type": "search",
                    "status": "success",
                    "start_date": "2024-01-01T00:00:00Z",
                    "limit": 50
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["items", "total"]
                }
            },
            {
                "category": "list_errors",
                "name": "list_activities_invalid_service_type",
                "description": "List activities with invalid service_type (should fail)",
                "method": "GET",
                "endpoint": "/api/v3/activities/",
                "query_params": {
                    "service_type": "invalid_service"
                },
                "expected_status": [400],
                "validate_response": {
                    "has_field": "detail"
                }
            },
            {
                "category": "list_errors",
                "name": "list_activities_invalid_action_type",
                "description": "List activities with invalid action_type (should fail)",
                "method": "GET",
                "endpoint": "/api/v3/activities/",
                "query_params": {
                    "action_type": "invalid_action"
                },
                "expected_status": [400],
                "validate_response": {
                    "has_field": "detail"
                }
            },
            {
                "category": "list_errors",
                "name": "list_activities_invalid_status",
                "description": "List activities with invalid status (should fail)",
                "method": "GET",
                "endpoint": "/api/v3/activities/",
                "query_params": {
                    "status": "invalid_status"
                },
                "expected_status": [400],
                "validate_response": {
                    "has_field": "detail"
                }
            },
            {
                "category": "list_errors",
                "name": "list_activities_invalid_limit_too_low",
                "description": "List activities with limit < 1 (should fail)",
                "method": "GET",
                "endpoint": "/api/v3/activities/",
                "query_params": {
                    "limit": 0
                },
                "expected_status": [422],
                "validate_response": {
                    "has_field": "detail"
                }
            },
            {
                "category": "list_errors",
                "name": "list_activities_invalid_limit_too_high",
                "description": "List activities with limit > 1000 (should fail)",
                "method": "GET",
                "endpoint": "/api/v3/activities/",
                "query_params": {
                    "limit": 1001
                },
                "expected_status": [422],
                "validate_response": {
                    "has_field": "detail"
                }
            },
            {
                "category": "list_errors",
                "name": "list_activities_invalid_offset",
                "description": "List activities with offset < 0 (should fail)",
                "method": "GET",
                "endpoint": "/api/v3/activities/",
                "query_params": {
                    "offset": -1
                },
                "expected_status": [422],
                "validate_response": {
                    "has_field": "detail"
                }
            },
            {
                "category": "list_errors",
                "name": "list_activities_unauthorized",
                "description": "List activities without authentication (should fail)",
                "method": "GET",
                "endpoint": "/api/v3/activities/",
                "query_params": {},
                "requires_auth": False,
                "expected_status": [401],
                "validate_response": {
                    "has_field": "detail"
                }
            }
        ]
    
    @staticmethod
    def get_stats_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for activity statistics endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "stats",
                "name": "get_activity_stats_all",
                "description": "Get activity statistics for all activities",
                "method": "GET",
                "endpoint": "/api/v3/activities/stats/",
                "query_params": {},
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["total_activities", "by_service_type", "by_action_type", "by_status", "recent_activities"]
                }
            },
            {
                "category": "stats",
                "name": "get_activity_stats_with_date_range",
                "description": "Get activity statistics filtered by date range",
                "method": "GET",
                "endpoint": "/api/v3/activities/stats/",
                "query_params": {
                    "start_date": "2024-01-01T00:00:00Z",
                    "end_date": "2024-12-31T23:59:59Z"
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["total_activities", "by_service_type", "by_action_type", "by_status", "recent_activities"]
                }
            },
            {
                "category": "stats_errors",
                "name": "get_activity_stats_unauthorized",
                "description": "Get activity statistics without authentication (should fail)",
                "method": "GET",
                "endpoint": "/api/v3/activities/stats/",
                "query_params": {},
                "requires_auth": False,
                "expected_status": [401],
                "validate_response": {
                    "has_field": "detail"
                }
            }
        ]
    
    @staticmethod
    def get_all_scenarios() -> List[Dict[str, Any]]:
        """Get all test scenarios for Activities API.
        
        Returns:
            List of all test scenario dictionaries
        """
        scenarios = []
        scenarios.extend(ActivitiesTestScenarios.get_list_scenarios())
        scenarios.extend(ActivitiesTestScenarios.get_stats_scenarios())
        return scenarios

