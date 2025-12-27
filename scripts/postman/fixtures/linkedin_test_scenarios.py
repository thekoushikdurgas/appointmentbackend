"""Comprehensive test scenarios for LinkedIn API endpoints.

This module defines all test scenarios for the LinkedIn API,
covering LinkedIn URL search operations.
"""

from typing import Dict, List, Any


class LinkedInTestScenarios:
    """Comprehensive test scenarios for LinkedIn API endpoints."""
    
    @staticmethod
    def get_search_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for LinkedIn search endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "search",
                "name": "search_person_url",
                "description": "Search for contacts by LinkedIn person URL",
                "method": "POST",
                "endpoint": "/api/v3/linkedin/",
                "body": {
                    "url": "https://www.linkedin.com/in/john-doe"
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["contacts", "companies", "total_contacts", "total_companies"],
                    "contacts_is_list": True,
                    "companies_is_list": True
                }
            },
            {
                "category": "search",
                "name": "search_company_url",
                "description": "Search for companies by LinkedIn company URL",
                "method": "POST",
                "endpoint": "/api/v3/linkedin/",
                "body": {
                    "url": "https://www.linkedin.com/company/tech-corp"
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["contacts", "companies", "total_contacts", "total_companies"]
                }
            },
            {
                "category": "search",
                "name": "search_partial_url",
                "description": "Search with partial LinkedIn URL (case-insensitive partial matching)",
                "method": "POST",
                "endpoint": "/api/v3/linkedin/",
                "body": {
                    "url": "linkedin.com/in/john"
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["contacts", "companies", "total_contacts", "total_companies"]
                }
            },
            {
                "category": "search",
                "name": "search_no_results",
                "description": "Search with URL that has no matches (should return empty arrays)",
                "method": "POST",
                "endpoint": "/api/v3/linkedin/",
                "body": {
                    "url": "https://www.linkedin.com/in/nonexistent-person-12345"
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["contacts", "companies", "total_contacts", "total_companies"],
                    "total_contacts": 0,
                    "total_companies": 0
                }
            },
            {
                "category": "search",
                "name": "search_unauthorized",
                "description": "Search without authentication (should fail)",
                "method": "POST",
                "endpoint": "/api/v3/linkedin/",
                "body": {
                    "url": "https://www.linkedin.com/in/john-doe"
                },
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
        ]
    
    @staticmethod
    def get_search_error_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for LinkedIn search error cases.
        
        Returns:
            List of error test scenario dictionaries
        """
        return [
            {
                "category": "search_errors",
                "name": "missing_required_url",
                "description": "Search without required url field (should fail)",
                "method": "POST",
                "endpoint": "/api/v3/linkedin/",
                "body": {},
                "expected_status": [400, 422],
            },
            {
                "category": "search_errors",
                "name": "empty_url",
                "description": "Search with empty URL string (should fail)",
                "method": "POST",
                "endpoint": "/api/v3/linkedin/",
                "body": {
                    "url": ""
                },
                "expected_status": [400],
            },
            {
                "category": "search_errors",
                "name": "invalid_url_format",
                "description": "Search with invalid URL format (may return empty results or error)",
                "method": "POST",
                "endpoint": "/api/v3/linkedin/",
                "body": {
                    "url": "not-a-linkedin-url"
                },
                "expected_status": [200, 400],  # May return empty results or error
            },
            {
                "category": "search_errors",
                "name": "invalid_url_type",
                "description": "Search with non-string URL (should fail)",
                "method": "POST",
                "endpoint": "/api/v3/linkedin/",
                "body": {
                    "url": 12345
                },
                "expected_status": [400, 422],
            },
            {
                "category": "search_errors",
                "name": "missing_url_key",
                "description": "Search with body missing url key (should fail)",
                "method": "POST",
                "endpoint": "/api/v3/linkedin/",
                "body": {
                    "other_field": "value"
                },
                "expected_status": [400, 422],
            },
        ]
    
    @staticmethod
    def get_all_scenarios() -> Dict[str, List[Dict[str, Any]]]:
        """Get all test scenarios organized by category.
        
        Returns:
            Dictionary mapping category names to lists of scenarios
        """
        return {
            "search": LinkedInTestScenarios.get_search_scenarios(),
            "search_errors": LinkedInTestScenarios.get_search_error_scenarios(),
        }
