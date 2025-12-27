"""Test case generator for API endpoints."""

import sys
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
import json

# Add backend to path for imports
# Script is at: backend/scripts/postman/tests/test_generator.py
# Need to add workspace root so we can import from backend.app
# Path(__file__).parent.parent.parent = backend
# Path(__file__).parent.parent.parent.parent = workspace root
workspace_root = Path(__file__).parent.parent.parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

# Import from generate_collection.py
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from generate_collection import (
        extract_filter_params_from_model,
        get_filter_class_for_endpoint,
        extract_schema_fields,
        get_request_body,
        FILTERS_AVAILABLE,
        SCHEMAS_AVAILABLE,
    )
except ImportError:
    # Fallback if imports fail
    FILTERS_AVAILABLE = False
    SCHEMAS_AVAILABLE = False
    extract_filter_params_from_model = None
    get_filter_class_for_endpoint = None
    extract_schema_fields = None
    get_request_body = None


class TestCaseGenerator:
    """Generates test cases for API endpoints."""
    
    def __init__(self, test_mode: str = "hybrid"):
        """Initialize test case generator.
        
        Args:
            test_mode: Test mode (smoke/comprehensive/hybrid)
        """
        self.test_mode = test_mode
    
    def generate_test_cases(self, endpoint: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate test cases for an endpoint.
        
        Args:
            endpoint: Endpoint dictionary from CSV with keys:
                - method: HTTP method
                - endpoint: Endpoint path
                - api_version: API version
                - category: Category name
                - description: Endpoint description
        
        Returns:
            List of test case dictionaries
        """
        method = endpoint.get("method", "GET")
        endpoint_path = endpoint.get("endpoint", "")
        api_version = endpoint.get("api_version", "v1")
        
        # Skip WebSocket endpoints
        if method == "WEBSOCKET":
            return []
        
        test_cases = []
        
        # Determine test strategy based on method and mode
        if method == "GET":
            if self.test_mode in ["smoke", "hybrid"]:
                test_cases.extend(self._generate_get_smoke_tests(endpoint))
            elif self.test_mode == "comprehensive":
                test_cases.extend(self._generate_get_comprehensive_tests(endpoint))
        elif method in ["POST", "PUT", "PATCH"]:
            if self.test_mode in ["comprehensive", "hybrid"]:
                test_cases.extend(self._generate_post_comprehensive_tests(endpoint))
            elif self.test_mode == "smoke":
                test_cases.extend(self._generate_post_smoke_tests(endpoint))
        
        return test_cases
    
    def _generate_get_smoke_tests(self, endpoint: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate smoke tests for GET endpoints.
        
        Args:
            endpoint: Endpoint dictionary
        
        Returns:
            List of test case dictionaries
        """
        test_cases = []
        endpoint_path = endpoint.get("endpoint", "")
        method = endpoint.get("method", "GET")
        
        # Check for endpoints with required query parameters
        required_params = self._get_required_query_params(endpoint_path)
        
        # Basic test with minimal parameters
        test_case = {
            "name": "basic_request",
            "description": "Basic GET request with default parameters",
            "method": method,
            "endpoint": endpoint_path,
            "query_params": required_params.copy() if required_params else {},
            "expected_status": [200, 201, 204, 404],  # 404 is acceptable for missing resources
        }
        
        # Add common query parameters if available
        if FILTERS_AVAILABLE and extract_filter_params_from_model and get_filter_class_for_endpoint:
            filter_class = get_filter_class_for_endpoint(endpoint_path, method)
            if filter_class:
                filter_params = extract_filter_params_from_model(filter_class)
                # Add a few common parameters
                for param in filter_params[:5]:  # Limit to first 5 params
                    if param["key"] in ["limit", "offset", "page", "page_size"]:
                        test_case["query_params"][param["key"]] = param.get("value", "")
        
        # Note: VQL endpoints and deprecated endpoints removed
        # No endpoint-specific parameters needed for remaining GET endpoints
        
        test_cases.append(test_case)
        return test_cases
    
    def _get_required_query_params(self, endpoint_path: str) -> Dict[str, Any]:
        """Get required query parameters for an endpoint.
        
        Args:
            endpoint_path: Endpoint path
        
        Returns:
            Dictionary of required query parameters
        """
        # Define required query parameters for specific endpoints
        required_params_map = {
            "/api/v3/email/finder/": {
                "first_name": "John",  # Required: Contact first name
                "last_name": "Doe",  # Required: Contact last name
                "domain": "example.com"  # Either domain or website is required
            },
            "/api/v3/email/bulk/download/{file_type}/{slug}/": {
                "provider": "truelist"  # Must be 'truelist' or 'truelioo'
            },
            "/api/v3/exports/{export_id}/download": {
                "token": "test_download_token"  # Required token for download
            },
            # User endpoints with optional query parameters
            "/api/v1/users/": {
                "limit": 100,
                "offset": 0
            },
            "/api/v1/users/history/": {
                "limit": 100,
                "offset": 0
                # user_id and event_type are optional
            },
            "/api/v1/users/sales-navigator/list": {
                "limit": 100,
                "offset": 0
            },
            "/api/v1/users/promote-to-super-admin/": {
                "user_id": "{{user_id}}"  # Required query parameter
            },
            # S3 endpoints with query parameters
            "/api/v3/s3/files": {
                # prefix is optional, no default needed
            },
            "/api/v3/s3/files/{file_id}": {
                # limit and offset are optional for pagination mode
                # If not provided, returns full file download
            },
            # Marketing endpoints with query parameters
            "/api/v4/marketing/": {
                # include_drafts is ignored (always false for public endpoint)
            },
            "/api/v4/admin/marketing/": {
                "include_drafts": True,
                "include_deleted": False
            },
            "/api/v4/admin/marketing/{page_id}": {
                # hard_delete is optional for DELETE method
            },
            # Email endpoints with query parameters
            "/api/v3/email/finder/": {
                "first_name": "John",
                "last_name": "Doe",
                "domain": "example.com"
            },
        }
        
        # Check for exact match first
        if endpoint_path in required_params_map:
            return required_params_map[endpoint_path].copy()
        
        # Check for pattern matches (with placeholders)
        for pattern, params in required_params_map.items():
            # Simple pattern matching - check if endpoint contains key parts
            pattern_parts = pattern.split("/")
            endpoint_parts = endpoint_path.split("/")
            
            # Match if structure is similar (same number of parts, matching non-placeholder parts)
            if len(pattern_parts) == len(endpoint_parts):
                matches = True
                for p, e in zip(pattern_parts, endpoint_parts):
                    if p.startswith("{") and p.endswith("}"):
                        continue  # Skip placeholder parts
                    if p != e:
                        matches = False
                        break
                if matches:
                    return params.copy()
        
        return {}
    
    def _generate_get_comprehensive_tests(self, endpoint: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate comprehensive tests for GET endpoints.
        
        Args:
            endpoint: Endpoint dictionary
        
        Returns:
            List of test case dictionaries
        """
        # Start with smoke tests
        test_cases = self._generate_get_smoke_tests(endpoint)
        endpoint_path = endpoint.get("endpoint", "")
        method = endpoint.get("method", "GET")
        
        # Root-specific comprehensive tests
        if endpoint_path == "/api/v1/":
            # Test root metadata endpoint
            test_cases.append({
                "name": "get_api_metadata",
                "description": "Get API metadata (name, version, docs)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {},
                "expected_status": [200],
            })
        
        elif endpoint_path == "/api/v1/health/":
            # Test root health endpoint
            test_cases.append({
                "name": "get_api_health",
                "description": "Get API health status",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {},
                "expected_status": [200],
            })
        
        # Marketing-specific comprehensive tests
        elif endpoint_path == "/api/v4/marketing/":
            # Test public list endpoint
            test_cases.append({
                "name": "list_published_pages",
                "description": "List published marketing pages (public endpoint)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {},
                "expected_status": [200],
            })
        
        elif endpoint_path == "/api/v4/admin/marketing/":
            # Test admin list with drafts
            test_cases.append({
                "name": "list_all_pages_with_drafts",
                "description": "List all marketing pages including drafts (admin)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "include_drafts": True,
                    "include_deleted": False
                },
                "expected_status": [200, 401, 403],  # 401/403 if not admin
            })
            
            # Test admin list with deleted
            test_cases.append({
                "name": "list_all_pages_with_deleted",
                "description": "List all marketing pages including deleted (admin)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "include_drafts": True,
                    "include_deleted": True
                },
                "expected_status": [200, 401, 403],  # 401/403 if not admin
            })
        
        # S3-specific comprehensive tests
        elif endpoint_path == "/api/v3/s3/files":
            # Test with prefix filter
            test_cases.append({
                "name": "list_with_prefix",
                "description": "List S3 files with prefix filter",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "prefix": "data/"
                },
                "expected_status": [200],
            })
        
        elif "/s3/files/{file_id}" in endpoint_path or (endpoint_path.startswith("/api/v3/s3/files/") and endpoint_path != "/api/v3/s3/files"):
            # Test pagination mode
            test_cases.append({
                "name": "pagination_mode",
                "description": "Get S3 file in pagination mode (with limit and offset)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 50,
                    "offset": 0
                },
                "expected_status": [200, 404],  # 404 if file doesn't exist
            })
            
            # Test download mode (no query params)
            test_cases.append({
                "name": "download_mode",
                "description": "Get S3 file in download mode (no pagination params)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {},
                "expected_status": [200, 404],  # 404 if file doesn't exist
            })
        
        # Add tests with various filter combinations
        elif FILTERS_AVAILABLE and extract_filter_params_from_model and get_filter_class_for_endpoint:
            filter_class = get_filter_class_for_endpoint(endpoint_path, method)
            if filter_class:
                filter_params = extract_filter_params_from_model(filter_class)
                
                # Test with all filter parameters enabled
                # Get required params first
                required_params = self._get_required_query_params(endpoint_path)
                comprehensive_test = {
                    "name": "comprehensive_filters",
                    "description": "GET request with all filter parameters",
                    "method": method,
                    "endpoint": endpoint_path,
                    "query_params": required_params.copy() if required_params else {},
                    "expected_status": [200, 201, 204, 404],
                }
                
                for param in filter_params:
                    if param.get("value"):
                        comprehensive_test["query_params"][param["key"]] = param["value"]
                
                test_cases.append(comprehensive_test)
        
        return test_cases
    
    def _generate_post_smoke_tests(self, endpoint: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate smoke tests for POST/PUT/PATCH endpoints.
        
        Args:
            endpoint: Endpoint dictionary
        
        Returns:
            List of test case dictionaries
        """
        test_cases = []
        endpoint_path = endpoint.get("endpoint", "")
        method = endpoint.get("method", "POST")
        description = endpoint.get("description", "")
        
        # Generate valid request body
        body = self._generate_valid_body(endpoint_path, method, description)
        
        # Special handling for refresh token endpoint - token might be invalid/expired
        # Accept 400 as valid response when token is invalid (correct behavior)
        expected_status = [200, 201, 202, 204]
        if endpoint_path == "/api/v1/auth/refresh/":
            expected_status = [200, 201, 202, 204, 400]  # Accept 400 if token is invalid/expired
        
        test_case = {
            "name": "valid_request",
            "description": f"Valid {method} request",
            "method": method,
            "endpoint": endpoint_path,
            "body": body,
            "expected_status": expected_status,
        }
        
        test_cases.append(test_case)
        return test_cases
    
    def _generate_post_comprehensive_tests(self, endpoint: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate comprehensive tests for POST/PUT/PATCH endpoints.
        
        Args:
            endpoint: Endpoint dictionary
        
        Returns:
            List of test case dictionaries
        """
        test_cases = []
        endpoint_path = endpoint.get("endpoint", "")
        method = endpoint.get("method", "POST")
        description = endpoint.get("description", "")
        
        # Check if this is a VQL endpoint
        is_vql_endpoint = ('/query' in endpoint_path or '/count' in endpoint_path) and ('/contacts/' in endpoint_path or '/companies/' in endpoint_path)
        
        if is_vql_endpoint:
            # Generate VQL-specific test cases
            test_cases.extend(self._generate_vql_tests(endpoint))
        else:
            # Standard POST endpoint tests
            # 1. Valid request test
            valid_body = self._generate_valid_body(endpoint_path, method, description)
            if valid_body:
                # Special handling for refresh token endpoint - token might be invalid/expired
                # Accept 400 as valid response when token is invalid (correct behavior)
                expected_status = [200, 201, 202, 204]
                if endpoint_path == "/api/v1/auth/refresh/":
                    expected_status = [200, 201, 202, 204, 400]  # Accept 400 if token is invalid/expired
                
                test_cases.append({
                    "name": "valid_request",
                    "description": f"Valid {method} request with all required fields",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": valid_body,
                    "expected_status": expected_status,
                })
            
            # 2. Missing required fields tests
            if SCHEMAS_AVAILABLE and extract_schema_fields and valid_body:
                schema_fields = self._get_schema_fields(endpoint_path, method, description)
                if schema_fields:
                    # Test missing each field one at a time
                    for field_name in schema_fields.keys():
                        test_body = valid_body.copy() if valid_body else {}
                        test_body.pop(field_name, None)
                        
                        test_cases.append({
                            "name": f"missing_{field_name}",
                            "description": f"{method} request missing required field: {field_name}",
                            "method": method,
                            "endpoint": endpoint_path,
                            "body": test_body,
                            "expected_status": [422, 400],  # Expect validation error
                        })
            
            # 3. User-specific error test cases
            if endpoint_path.startswith("/api/v1/auth/") or endpoint_path.startswith("/api/v1/users/"):
                test_cases.extend(self._generate_user_endpoint_error_tests(endpoint_path, method, valid_body))
            
            # 4. Usage-specific error test cases
            if endpoint_path.startswith("/api/v1/usage/") or endpoint_path.startswith("/api/v2/usage/"):
                test_cases.extend(self._generate_usage_endpoint_error_tests(endpoint_path, method, valid_body))
            
            # 5. Scrape-specific error test cases
            if endpoint_path.startswith("/api/v3/sales-navigator/"):
                test_cases.extend(self._generate_scrape_endpoint_error_tests(endpoint_path, method, valid_body))
            
            # 6. S3-specific error test cases
            if endpoint_path.startswith("/api/v3/s3/files"):
                test_cases.extend(self._generate_s3_endpoint_error_tests(endpoint_path, method))
            
            # 7. Root-specific error test cases (minimal - only 500 errors expected)
            if endpoint_path in ["/api/v1/", "/api/v1/health/"]:
                test_cases.extend(self._generate_root_endpoint_error_tests(endpoint_path, method))
            
            # 8. Marketing-specific error test cases
            if "/marketing" in endpoint_path:
                test_cases.extend(self._generate_marketing_endpoint_error_tests(endpoint_path, method, valid_body))
            
            # 9. LinkedIn-specific error test cases
            if endpoint_path == "/api/v3/linkedin/":
                test_cases.extend(self._generate_linkedin_endpoint_error_tests(endpoint_path, method, valid_body))
            
            # 10. Email-specific error test cases
            if "/email" in endpoint_path:
                test_cases.extend(self._generate_email_endpoint_error_tests(endpoint_path, method, valid_body))
            
            # 10. Health-specific error test cases (minimal - only 401, 500 errors expected)
            if endpoint_path in ["/api/v1/health/vql", "/api/v1/health/vql/stats"]:
                test_cases.extend(self._generate_health_endpoint_error_tests(endpoint_path, method))
            
            # 11. Invalid data type tests
            if valid_body:
                for field_name, field_value in valid_body.items():
                    # Skip nested objects and None values
                    if isinstance(field_value, (dict, list)) or field_value is None:
                        continue
                    
                    if isinstance(field_value, str):
                        # Test with integer instead of string
                        invalid_body = valid_body.copy()
                        invalid_body[field_name] = 12345
                        test_cases.append({
                            "name": f"invalid_type_{field_name}",
                            "description": f"{method} request with invalid type for {field_name}",
                            "method": method,
                            "endpoint": endpoint_path,
                            "body": invalid_body,
                            "expected_status": [422, 400],
                        })
                    elif isinstance(field_value, int):
                        # Test with string instead of integer
                        invalid_body = valid_body.copy()
                        invalid_body[field_name] = "invalid_number"
                        test_cases.append({
                            "name": f"invalid_type_{field_name}",
                            "description": f"{method} request with invalid type for {field_name}",
                            "method": method,
                            "endpoint": endpoint_path,
                            "body": invalid_body,
                            "expected_status": [422, 400],
                        })
            
            # 11. Empty body test
            # Some endpoints allow empty body (e.g., POST /api/v2/ai-chats/ returns 201)
            # Some endpoints return 404 for invalid IDs before validating body
            # Adjust expected status based on endpoint behavior
            expected_status_for_empty = self._get_expected_status_for_empty_body(endpoint_path, method)
            test_cases.append({
                "name": "empty_body",
                "description": f"{method} request with empty body",
                "method": method,
                "endpoint": endpoint_path,
                "body": {},
                "expected_status": expected_status_for_empty,
            })
        
        return test_cases
    
    def _generate_vql_tests(self, endpoint: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate VQL-specific test cases.
        
        Args:
            endpoint: Endpoint dictionary
        
        Returns:
            List of test case dictionaries
        """
        test_cases = []
        endpoint_path = endpoint.get("endpoint", "")
        method = endpoint.get("method", "POST")
        is_company = "/companies/" in endpoint_path
        
        # 1. Simple VQL filter test
        simple_filter = {
            "filters": {
                "and": [
                    {
                        "field": "name" if is_company else "first_name",
                        "operator": "eq",
                        "value": "Example" if is_company else "John"
                    }
                ]
            },
            "limit": 10,
            "offset": 0
        }
        test_cases.append({
            "name": "simple_vql_filter",
            "description": "VQL query with simple filter",
            "method": method,
            "endpoint": endpoint_path,
            "body": simple_filter,
            "expected_status": [200, 201],
        })
        
        # 2. Nested AND/OR filters test
        nested_filter = {
            "filters": {
                "and": [
                    {
                        "field": "name" if is_company else "first_name",
                        "operator": "eq",
                        "value": "Example" if is_company else "John"
                    },
                    {
                        "or": [
                            {
                                "field": "employees_count" if is_company else "title",
                                "operator": "gt" if is_company else "contains",
                                "value": 100 if is_company else "Engineer"
                            }
                        ]
                    }
                ]
            },
            "limit": 10,
            "offset": 0
        }
        test_cases.append({
            "name": "nested_vql_filters",
            "description": "VQL query with nested AND/OR filters",
            "method": method,
            "endpoint": endpoint_path,
            "body": nested_filter,
            "expected_status": [200, 201],
        })
        
        # 3. With select_columns test
        select_columns_body = {
            "filters": {
                "and": [
                    {
                        "field": "name" if is_company else "first_name",
                        "operator": "eq",
                        "value": "Example" if is_company else "John"
                    }
                ]
            },
            "select_columns": ["uuid", "name"] if is_company else ["uuid", "first_name", "last_name"],
            "limit": 10,
            "offset": 0
        }
        test_cases.append({
            "name": "vql_with_select_columns",
            "description": "VQL query with select_columns",
            "method": method,
            "endpoint": endpoint_path,
            "body": select_columns_body,
            "expected_status": [200, 201],
        })
        
        # 4. With populate config (for contacts only)
        if not is_company:
            populate_body = {
                "filters": {
                    "and": [
                        {
                            "field": "first_name",
                            "operator": "eq",
                            "value": "John"
                        }
                    ]
                },
                "company_config": {
                    "populate": True,
                    "select_columns": ["uuid", "name"]
                },
                "limit": 10,
                "offset": 0
            }
            test_cases.append({
                "name": "vql_with_populate_config",
                "description": "VQL query with company_config populate",
                "method": method,
                "endpoint": endpoint_path,
                "body": populate_body,
                "expected_status": [200, 201],
            })
        
        # 5. With sorting test
        sort_body = {
            "filters": {
                "and": [
                    {
                        "field": "name" if is_company else "first_name",
                        "operator": "exists",
                        "value": True
                    }
                ]
            },
            "sort_by": "name" if is_company else "first_name",
            "sort_direction": "asc",
            "limit": 10,
            "offset": 0
        }
        test_cases.append({
            "name": "vql_with_sorting",
            "description": "VQL query with sorting",
            "method": method,
            "endpoint": endpoint_path,
            "body": sort_body,
            "expected_status": [200, 201],
        })
        
        # 6. Empty filters test (should still work)
        empty_filters_body = {
            "limit": 10,
            "offset": 0
        }
        test_cases.append({
            "name": "vql_empty_filters",
            "description": "VQL query with empty filters (returns all)",
            "method": method,
            "endpoint": endpoint_path,
            "body": empty_filters_body,
            "expected_status": [200, 201],
        })
        
        return test_cases
    
    def _generate_valid_body(self, endpoint_path: str, method: str, description: str) -> Optional[Dict[str, Any]]:
        """Generate a valid request body for an endpoint.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            description: Endpoint description
        
        Returns:
            Request body dictionary or None
        """
        # Try to use schema-based generation
        if SCHEMAS_AVAILABLE and extract_schema_fields:
            schema_fields = self._get_schema_fields(endpoint_path, method, description)
            if schema_fields:
                return schema_fields
        
        # VQL endpoints - generate VQL query structure
        if ('/query' in endpoint_path or '/count' in endpoint_path) and ('/contacts/' in endpoint_path or '/companies/' in endpoint_path):
            is_company = "/companies/" in endpoint_path
            return {
                "filters": {
                    "and": [
                        {
                            "field": "name" if is_company else "first_name",
                            "operator": "eq",
                            "value": "Example" if is_company else "John"
                        }
                    ]
                },
                "select_columns": ["uuid", "name"] if is_company else ["uuid", "first_name", "last_name"],
                "limit": 10,
                "offset": 0,
                "sort_by": "name" if is_company else "first_name",
                "sort_direction": "asc"
            }
        
        # Fallback to hardcoded templates
        body_templates = {
            # Authentication endpoints
            "/api/v1/auth/register": {
                "name": "Test User",
                "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
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
            "/api/v1/auth/register/": {
                "name": "Test User",
                "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
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
            "/api/v1/auth/login/": {
                "email": "test@example.com",
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
            "/api/v1/auth/logout/": {
                "refresh_token": "{{refresh_token}}"
            },
            "/api/v1/auth/refresh/": {
                "refresh_token": "{{refresh_token}}"
            },
            # Profile endpoints
            "/api/v1/users/profile/": {
                "name": "Updated Test User",
                "job_title": "Senior Software Engineer",
                "bio": "Updated bio with more details",
                "timezone": "America/New_York",
                "avatar_url": "https://picsum.photos/seed/123/40/40",
                "notifications": {
                    "weeklyReports": False,
                    "newLeadAlerts": True
                }
            },
            # Super admin endpoints
            "/api/v1/users/{user_id}/role/": {
                "role": "ProUser"
            },
            "/api/v1/users/{user_id}/credits/": {
                "credits": 1000
            },
            # Usage endpoints
            "/api/v1/usage/track/": {
                "feature": "EMAIL_FINDER",
                "amount": 1
            },
            "/api/v2/usage/reset": {
                "feature": "EMAIL_FINDER"
            },
            # Sales Navigator scrape endpoint
            "/api/v3/sales-navigator/scrape": {
                "html": "<html><head><title>Sales Navigator</title></head><body><div class=\"search-results\"><div class=\"profile-card\"><div class=\"profile-name\">John Doe</div><div class=\"profile-title\">Software Engineer</div><div class=\"profile-company\">Tech Corp</div></div></div></body></html>",
                "save": False
            },
            # Email endpoints
            "/api/v3/email/export": {
                "contacts": [
                    {
                        "first_name": "John",
                        "last_name": "Doe",
                        "domain": "example.com",
                        "email": "john.doe@example.com"
                    }
                ],
                "mapping": {
                    "first_name": "first_name",
                    "last_name": "last_name",
                    "domain": "domain",
                    "website": None,
                    "email": "email"
                }
            },
            "/api/v3/email/single/": {
                "first_name": "John",
                "last_name": "Doe",
                "domain": "example.com",
                "provider": "truelist"
            },
            "/api/v3/email/bulk/verifier/": {
                "provider": "truelist",
                "emails": [
                    "john.doe@example.com",
                    "jane.smith@example.com"
                ]
            },
            "/api/v3/email/single/verifier/": {
                "email": "john.doe@example.com",
                "provider": "truelist"
            },
            "/api/v3/email/verifier/": {
                "first_name": "John",
                "last_name": "Doe",
                "domain": "example.com",
                "provider": "truelist",
                "email_count": 1000,
                "max_retries": 10
            },
            "/api/v3/email/verifier/single/": {
                "first_name": "John",
                "last_name": "Doe",
                "domain": "example.com",
                "provider": "truelist",
                "email_count": 1000,
                "max_retries": 10
            },
            # Marketing endpoints
            "/api/v4/admin/marketing/": {
                "page_id": f"test-page-{uuid.uuid4().hex[:8]}",
                "hero": {
                    "title": "Test Hero Title",
                    "subtitle": "Test Hero Subtitle",
                    "description": "Test hero description",
                    "features": ["Feature 1", "Feature 2"],
                    "cta_text": "Get Started",
                    "cta_href": "/signup"
                },
                "sections": {},
                "hero_stats": None,
                "hero_table": None
            },
        }
        
        # Check for exact match
        if endpoint_path in body_templates:
            return body_templates[endpoint_path].copy()
        
        # Check for pattern matches
        for pattern, body in body_templates.items():
            if endpoint_path.startswith(pattern):
                return body.copy()
        
        # Marketing update endpoint (PUT) - partial update
        if endpoint_path.startswith("/api/v4/admin/marketing/") and method == "PUT":
            return {
                "metadata": {
                    "title": "Updated Title"
                },
                "hero": {
                    "subtitle": "Updated Subtitle"
                },
                "sections": {
                    "new_section": {
                        "content": "New section content"
                    }
                }
            }
        
        # Special handling for LinkedIn endpoints
        if endpoint_path == "/api/v2/linkedin/":
            if "Search" in description or "search" in description.lower():
                return {"url": "https://www.linkedin.com/in/johndoe/"}
            elif "Create or update" in description or "upsert" in description.lower():
                return {
                    "url": "https://www.linkedin.com/in/johndoe/",
                    "contact_data": None,
                    "company_data": None
                }
        
        # Default empty body
        return {}
    
    def _get_schema_fields(self, endpoint_path: str, method: str, description: str) -> Optional[Dict[str, Any]]:
        """Get schema fields for an endpoint.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            description: Endpoint description
        
        Returns:
            Schema fields dictionary or None
        """
        if not SCHEMAS_AVAILABLE or not extract_schema_fields:
            return None
        
        # Import request schemas
        try:
            from app.schemas.user import (
                UserRegister, UserLogin, RefreshTokenRequest, LogoutRequest,
                ProfileUpdate, UpdateUserRoleRequest, UpdateUserCreditsRequest
            )
            from app.schemas.usage import TrackUsageRequest
            from app.schemas.sales_navigator import SalesNavigatorScrapeRequest
            from app.schemas.linkedin import LinkedInSearchRequest, LinkedInUpsertRequest
            from app.schemas.email import (
                EmailExportRequest, SingleEmailRequest, BulkEmailVerifierRequest,
                SingleEmailVerifierRequest, EmailVerifierRequest
            )
            
            # Try to import VQLQuery for VQL endpoints
            try:
                from app.core.vql.structures import VQLQuery
                VQL_AVAILABLE = True
            except ImportError:
                VQL_AVAILABLE = False
            
            # VQL endpoints use VQLQuery schema
            if ('/query' in endpoint_path or '/count' in endpoint_path) and ('/contacts/' in endpoint_path or '/companies/' in endpoint_path):
                if VQL_AVAILABLE:
                    return extract_schema_fields(VQLQuery)
                # Fallback to basic structure if VQLQuery not available
                return {
                    "filters": {},
                    "select_columns": [],
                    "limit": 10,
                    "offset": 0
                }
            
            schema_map = {
                "/api/v1/auth/register": UserRegister,
                "/api/v1/auth/register/": UserRegister,
                "/api/v1/auth/login/": UserLogin,
                "/api/v1/auth/refresh/": RefreshTokenRequest,
                "/api/v1/auth/logout/": LogoutRequest,
                "/api/v1/users/profile/": ProfileUpdate,
                "/api/v1/users/{user_id}/role/": UpdateUserRoleRequest,
                "/api/v1/users/{user_id}/credits/": UpdateUserCreditsRequest,
                "/api/v1/usage/track/": TrackUsageRequest,
                "/api/v3/sales-navigator/scrape": SalesNavigatorScrapeRequest,
                "/api/v3/email/export": EmailExportRequest,
                "/api/v3/email/single/": SingleEmailRequest,
                "/api/v3/email/bulk/verifier/": BulkEmailVerifierRequest,
                "/api/v3/email/single/verifier/": SingleEmailVerifierRequest,
                "/api/v3/email/verifier/": EmailVerifierRequest,
                "/api/v3/email/verifier/single/": EmailVerifierRequest,
            }
            
            # Check exact match
            if endpoint_path in schema_map:
                return extract_schema_fields(schema_map[endpoint_path])
            
            # Special handling for LinkedIn
            if endpoint_path == "/api/v3/linkedin/":
                if "Search" in description or "search" in description.lower():
                    return extract_schema_fields(LinkedInSearchRequest)
                elif "Create or update" in description or "upsert" in description.lower():
                    return extract_schema_fields(LinkedInUpsertRequest)
            
        except ImportError:
            pass
        
        return None
    
    def _get_expected_status_for_empty_body(self, endpoint_path: str, method: str) -> List[int]:
        """Get expected status codes for empty body requests based on endpoint behavior.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
        
        Returns:
            List of expected status codes
        """
        # Endpoints that allow empty body and return success
        allows_empty_body = {
            "POST /api/v2/ai-chats/": [201],  # Creates chat with empty body
            "POST /api/v1/auth/logout/": [200],  # Logout accepts empty body and returns 200
            "PUT /api/v1/users/profile/": [200],  # Profile update accepts empty body (all fields optional, partial update)
        }
        
        # Endpoints that return 404 for invalid IDs (before body validation)
        returns_404_for_invalid_id = {
            "PUT /api/v2/ai-chats/{chat_id}/": [404],  # Resource not found takes precedence
            "PUT /api/v4/admin/dashboard-pages/{page_id}": [404],  # Page not found
            "PUT /api/v4/admin/marketing/{page_id}": [404],  # Page not found
            "POST /api/v4/admin/marketing/{page_id}/publish": [404],  # Page not found
        }
        
        # Check exact match
        key = f"{method} {endpoint_path}"
        if key in allows_empty_body:
            return allows_empty_body[key]
        if key in returns_404_for_invalid_id:
            return returns_404_for_invalid_id[key]
        
        # Check pattern matches for endpoints with placeholders
        for pattern, statuses in returns_404_for_invalid_id.items():
            pattern_method, pattern_path = pattern.split(" ", 1)
            if method == pattern_method:
                # Check if endpoint structure matches (same number of parts)
                pattern_parts = pattern_path.split("/")
                endpoint_parts = endpoint_path.split("/")
                if len(pattern_parts) == len(endpoint_parts):
                    # Check if non-placeholder parts match
                    matches = True
                    for p, e in zip(pattern_parts, endpoint_parts):
                        if p.startswith("{") and p.endswith("}"):
                            continue  # Skip placeholder parts
                        if p != e:
                            matches = False
                            break
                    if matches:
                        return statuses
        
        # Default: expect validation error
        return [422, 400]
    
    def _generate_user_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate user-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body (if available)
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Registration endpoint error tests
        if endpoint_path in ["/api/v1/auth/register", "/api/v1/auth/register/"]:
            if valid_body:
                # Short password (< 8 chars)
                short_password_body = valid_body.copy()
                short_password_body["password"] = "short"
                test_cases.append({
                    "name": "short_password",
                    "description": "Registration with password too short (< 8 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": short_password_body,
                    "expected_status": [400],
                })
                
                # Long password (> 72 chars)
                long_password_body = valid_body.copy()
                long_password_body["password"] = "a" * 73
                test_cases.append({
                    "name": "long_password",
                    "description": "Registration with password too long (> 72 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": long_password_body,
                    "expected_status": [400],
                })
                
                # Invalid email format
                invalid_email_body = valid_body.copy()
                invalid_email_body["email"] = "not-an-email"
                test_cases.append({
                    "name": "invalid_email",
                    "description": "Registration with invalid email format",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_email_body,
                    "expected_status": [422],
                })
        
        # Login endpoint error tests
        if endpoint_path == "/api/v1/auth/login/":
            if valid_body:
                # Invalid credentials
                invalid_creds_body = valid_body.copy()
                invalid_creds_body["password"] = "wrongpassword"
                test_cases.append({
                    "name": "invalid_credentials",
                    "description": "Login with invalid credentials",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_creds_body,
                    "expected_status": [400],
                })
        
        # Profile update endpoint error tests
        if endpoint_path == "/api/v1/users/profile/":
            if valid_body:
                # Name too long (> 255 chars)
                long_name_body = valid_body.copy()
                long_name_body["name"] = "a" * 256
                test_cases.append({
                    "name": "long_name",
                    "description": "Profile update with name too long (> 255 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": long_name_body,
                    "expected_status": [400, 422],  # FastAPI returns 422 for validation errors
                })
                
                # Timezone too long (> 100 chars)
                long_timezone_body = valid_body.copy()
                long_timezone_body["timezone"] = "a" * 101
                test_cases.append({
                    "name": "long_timezone",
                    "description": "Profile update with timezone too long (> 100 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": long_timezone_body,
                    "expected_status": [400, 422],  # FastAPI returns 422 for validation errors
                })
        
        # Role update endpoint error tests
        if "/users/{user_id}/role/" in endpoint_path:
            if valid_body:
                # Invalid role
                invalid_role_body = valid_body.copy()
                invalid_role_body["role"] = "InvalidRole"
                test_cases.append({
                    "name": "invalid_role",
                    "description": "Role update with invalid role value",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_role_body,
                    "expected_status": [400],
                })
        
        # Credits update endpoint error tests
        if "/users/{user_id}/credits/" in endpoint_path:
            if valid_body:
                # Negative credits
                negative_credits_body = valid_body.copy()
                negative_credits_body["credits"] = -1
                test_cases.append({
                    "name": "negative_credits",
                    "description": "Credits update with negative value",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": negative_credits_body,
                    "expected_status": [422, 400],
                })
        
        return test_cases
    
    def _generate_s3_endpoint_error_tests(
        self, endpoint_path: str, method: str
    ) -> List[Dict[str, Any]]:
        """Generate S3-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # S3 file get endpoint error tests (with file_id path parameter)
        if "/s3/files/{file_id}" in endpoint_path or "/s3/files/" in endpoint_path and "{file_id}" in endpoint_path:
            # Invalid pagination parameters
            # Limit too large (> 1000)
            test_cases.append({
                "name": "invalid_limit_too_large",
                "description": "Get S3 file with limit > 1000 (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 2000,
                    "offset": 0
                },
                "expected_status": [422],
            })
            
            # Negative offset
            test_cases.append({
                "name": "invalid_offset_negative",
                "description": "Get S3 file with negative offset (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 50,
                    "offset": -10
                },
                "expected_status": [422],
            })
            
            # Limit = 0 (below minimum)
            test_cases.append({
                "name": "invalid_limit_zero",
                "description": "Get S3 file with limit = 0 (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 0,
                    "offset": 0
                },
                "expected_status": [422],
            })
            
            # Limit without offset (should still work, offset defaults to 0)
            test_cases.append({
                "name": "limit_without_offset",
                "description": "Get S3 file with limit but no offset (offset defaults to 0)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 50
                },
                "expected_status": [200],
            })
            
            # Offset without limit (should fail - limit is required for pagination)
            test_cases.append({
                "name": "offset_without_limit",
                "description": "Get S3 file with offset but no limit (should fail or default to download mode)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "offset": 10
                },
                "expected_status": [200, 422],  # May default to download mode or fail validation
            })
        
        return test_cases
    
    def _generate_root_endpoint_error_tests(
        self, endpoint_path: str, method: str
    ) -> List[Dict[str, Any]]:
        """Generate Root-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Root endpoints are designed to be highly available and should rarely return errors
        # The only documented error is 500 Internal Server Error (server configuration issue)
        # Since these are public endpoints, we don't test authentication errors
        
        # Note: Root endpoints don't have request bodies or complex query parameters
        # Error scenarios are limited to server errors (500)
        # These are typically not testable in normal test runs, but we document them
        
        return test_cases
    
    def _generate_marketing_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate Marketing-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body for reference
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Marketing create endpoint error tests
        if endpoint_path == "/api/v4/admin/marketing/" and method == "POST":
            # Missing required hero field
            test_cases.append({
                "name": "missing_required_hero",
                "description": "Create marketing page without required hero field (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "page_id": "test-page"
                    # Missing hero
                },
                "expected_status": [400, 422],
            })
            
            # Missing required page_id
            test_cases.append({
                "name": "missing_required_page_id",
                "description": "Create marketing page without required page_id (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "hero": {
                        "title": "Test Title",
                        "description": "Test description"
                    }
                    # Missing page_id
                },
                "expected_status": [400, 422],
            })
            
            # Invalid metadata status
            if valid_body:
                invalid_status_body = valid_body.copy()
                invalid_status_body["metadata"] = {
                    "title": "Test Title",
                    "description": "Test description",
                    "status": "invalid_status"  # Invalid status
                }
                test_cases.append({
                    "name": "invalid_metadata_status",
                    "description": "Create marketing page with invalid status (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_status_body,
                    "expected_status": [400, 422],
                })
        
        # Marketing update endpoint error tests
        if endpoint_path.startswith("/api/v4/admin/marketing/") and "{page_id}" in endpoint_path and method == "PUT":
            # Empty body (partial update allows empty, but we test it)
            test_cases.append({
                "name": "empty_update_body",
                "description": "Update marketing page with empty body (partial update - should work)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {},
                "expected_status": [200, 400],  # May work or fail depending on implementation
            })
        
        return test_cases
    
    def _generate_linkedin_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate LinkedIn-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body for reference
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # LinkedIn search endpoint error tests
        if endpoint_path == "/api/v3/linkedin/" and method == "POST":
            # Missing required url field
            test_cases.append({
                "name": "missing_required_url",
                "description": "LinkedIn search without required url field (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {},
                "expected_status": [400, 422],
            })
            
            # Empty URL string
            test_cases.append({
                "name": "empty_url",
                "description": "LinkedIn search with empty URL (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "url": ""
                },
                "expected_status": [400],
            })
            
            # Invalid URL format
            test_cases.append({
                "name": "invalid_url_format",
                "description": "LinkedIn search with invalid URL format (may fail or return empty results)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "url": "not-a-linkedin-url"
                },
                "expected_status": [200, 400],  # May return empty results or error
            })
            
            # Wrong data type for URL
            test_cases.append({
                "name": "invalid_url_type",
                "description": "LinkedIn search with non-string URL (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "url": 12345
                },
                "expected_status": [400, 422],
            })
        
        return test_cases
    
    def _generate_email_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate email-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body for reference
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Email finder endpoint (GET with query params - handled separately, not here)
        # This method only handles POST endpoints with request bodies
        
        # Email export endpoint error tests
        if endpoint_path == "/api/v3/email/export" and method == "POST":
            if valid_body:
                # Missing required contacts field
                test_cases.append({
                    "name": "missing_required_contacts",
                    "description": "Email export without required contacts field (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": {},
                    "expected_status": [400, 422],
                })
                
                # Empty contacts array
                empty_contacts_body = valid_body.copy()
                empty_contacts_body["contacts"] = []
                test_cases.append({
                    "name": "empty_contacts_array",
                    "description": "Email export with empty contacts array (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_contacts_body,
                    "expected_status": [400, 422],
                })
                
                # Invalid contacts structure (not an array)
                invalid_contacts_body = valid_body.copy()
                invalid_contacts_body["contacts"] = "not-an-array"
                test_cases.append({
                    "name": "invalid_contacts_type",
                    "description": "Email export with invalid contacts type (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_contacts_body,
                    "expected_status": [400, 422],
                })
        
        # Single email endpoint error tests
        if endpoint_path == "/api/v3/email/single/" and method == "POST":
            if valid_body:
                # Missing required first_name
                missing_first_name_body = valid_body.copy()
                missing_first_name_body.pop("first_name", None)
                test_cases.append({
                    "name": "missing_first_name",
                    "description": "Single email without first_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_first_name_body,
                    "expected_status": [400, 422],
                })
                
                # Missing required last_name
                missing_last_name_body = valid_body.copy()
                missing_last_name_body.pop("last_name", None)
                test_cases.append({
                    "name": "missing_last_name",
                    "description": "Single email without last_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_last_name_body,
                    "expected_status": [400, 422],
                })
                
                # Missing required domain
                missing_domain_body = valid_body.copy()
                missing_domain_body.pop("domain", None)
                test_cases.append({
                    "name": "missing_domain",
                    "description": "Single email without domain (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_domain_body,
                    "expected_status": [400, 422],
                })
                
                # Empty first_name
                empty_first_name_body = valid_body.copy()
                empty_first_name_body["first_name"] = ""
                test_cases.append({
                    "name": "empty_first_name",
                    "description": "Single email with empty first_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_first_name_body,
                    "expected_status": [400],
                })
                
                # Empty last_name
                empty_last_name_body = valid_body.copy()
                empty_last_name_body["last_name"] = ""
                test_cases.append({
                    "name": "empty_last_name",
                    "description": "Single email with empty last_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_last_name_body,
                    "expected_status": [400],
                })
                
                # Empty domain
                empty_domain_body = valid_body.copy()
                empty_domain_body["domain"] = ""
                test_cases.append({
                    "name": "empty_domain",
                    "description": "Single email with empty domain (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_domain_body,
                    "expected_status": [400],
                })
        
        # Bulk verifier endpoint error tests
        if endpoint_path == "/api/v3/email/bulk/verifier/" and method == "POST":
            if valid_body:
                # Missing required provider
                missing_provider_body = valid_body.copy()
                missing_provider_body.pop("provider", None)
                test_cases.append({
                    "name": "missing_provider",
                    "description": "Bulk verifier without provider (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_provider_body,
                    "expected_status": [400, 422],
                })
                
                # Missing required emails
                missing_emails_body = valid_body.copy()
                missing_emails_body.pop("emails", None)
                test_cases.append({
                    "name": "missing_emails",
                    "description": "Bulk verifier without emails array (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_emails_body,
                    "expected_status": [400, 422],
                })
                
                # Empty emails array
                empty_emails_body = valid_body.copy()
                empty_emails_body["emails"] = []
                test_cases.append({
                    "name": "empty_emails_array",
                    "description": "Bulk verifier with empty emails array (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_emails_body,
                    "expected_status": [400, 422],
                })
                
                # Invalid provider value
                invalid_provider_body = valid_body.copy()
                invalid_provider_body["provider"] = "invalid_provider"
                test_cases.append({
                    "name": "invalid_provider",
                    "description": "Bulk verifier with invalid provider (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_provider_body,
                    "expected_status": [400, 422],
                })
        
        # Single verifier endpoint error tests
        if endpoint_path == "/api/v3/email/single/verifier/" and method == "POST":
            if valid_body:
                # Missing required email
                missing_email_body = valid_body.copy()
                missing_email_body.pop("email", None)
                test_cases.append({
                    "name": "missing_email",
                    "description": "Single verifier without email (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_email_body,
                    "expected_status": [400, 422],
                })
                
                # Missing required provider
                missing_provider_body = valid_body.copy()
                missing_provider_body.pop("provider", None)
                test_cases.append({
                    "name": "missing_provider",
                    "description": "Single verifier without provider (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_provider_body,
                    "expected_status": [400, 422],
                })
                
                # Empty email
                empty_email_body = valid_body.copy()
                empty_email_body["email"] = ""
                test_cases.append({
                    "name": "empty_email",
                    "description": "Single verifier with empty email (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_email_body,
                    "expected_status": [400],
                })
                
                # Invalid email format
                invalid_email_body = valid_body.copy()
                invalid_email_body["email"] = "not-an-email"
                test_cases.append({
                    "name": "invalid_email_format",
                    "description": "Single verifier with invalid email format (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_email_body,
                    "expected_status": [400, 422],
                })
                
                # Invalid provider value
                invalid_provider_body = valid_body.copy()
                invalid_provider_body["provider"] = "invalid_provider"
                test_cases.append({
                    "name": "invalid_provider",
                    "description": "Single verifier with invalid provider (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_provider_body,
                    "expected_status": [400, 422],
                })
        
        # Verifier endpoint error tests
        if endpoint_path == "/api/v3/email/verifier/" and method == "POST":
            if valid_body:
                # Missing required fields
                test_cases.append({
                    "name": "missing_required_fields",
                    "description": "Verifier without required fields (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": {},
                    "expected_status": [400, 422],
                })
                
                # Missing first_name
                missing_first_name_body = valid_body.copy()
                missing_first_name_body.pop("first_name", None)
                test_cases.append({
                    "name": "missing_first_name",
                    "description": "Verifier without first_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_first_name_body,
                    "expected_status": [400, 422],
                })
                
                # Missing last_name
                missing_last_name_body = valid_body.copy()
                missing_last_name_body.pop("last_name", None)
                test_cases.append({
                    "name": "missing_last_name",
                    "description": "Verifier without last_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_last_name_body,
                    "expected_status": [400, 422],
                })
                
                # Missing domain
                missing_domain_body = valid_body.copy()
                missing_domain_body.pop("domain", None)
                test_cases.append({
                    "name": "missing_domain",
                    "description": "Verifier without domain (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_domain_body,
                    "expected_status": [400, 422],
                })
                
                # Invalid email_count (negative or zero)
                if "email_count" in valid_body:
                    invalid_email_count_body = valid_body.copy()
                    invalid_email_count_body["email_count"] = -1
                    test_cases.append({
                        "name": "invalid_email_count_negative",
                        "description": "Verifier with negative email_count (should fail)",
                        "method": method,
                        "endpoint": endpoint_path,
                        "body": invalid_email_count_body,
                        "expected_status": [400, 422],
                    })
                    
                    invalid_email_count_zero_body = valid_body.copy()
                    invalid_email_count_zero_body["email_count"] = 0
                    test_cases.append({
                        "name": "invalid_email_count_zero",
                        "description": "Verifier with email_count = 0 (should fail)",
                        "method": method,
                        "endpoint": endpoint_path,
                        "body": invalid_email_count_zero_body,
                        "expected_status": [400, 422],
                    })
        
        # Verifier single endpoint error tests
        if endpoint_path == "/api/v3/email/verifier/single/" and method == "POST":
            if valid_body:
                # Missing required fields
                test_cases.append({
                    "name": "missing_required_fields",
                    "description": "Verifier single without required fields (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": {},
                    "expected_status": [400, 422],
                })
                
                # Missing first_name
                missing_first_name_body = valid_body.copy()
                missing_first_name_body.pop("first_name", None)
                test_cases.append({
                    "name": "missing_first_name",
                    "description": "Verifier single without first_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_first_name_body,
                    "expected_status": [400, 422],
                })
                
                # Missing last_name
                missing_last_name_body = valid_body.copy()
                missing_last_name_body.pop("last_name", None)
                test_cases.append({
                    "name": "missing_last_name",
                    "description": "Verifier single without last_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_last_name_body,
                    "expected_status": [400, 422],
                })
                
                # Missing domain
                missing_domain_body = valid_body.copy()
                missing_domain_body.pop("domain", None)
                test_cases.append({
                    "name": "missing_domain",
                    "description": "Verifier single without domain (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_domain_body,
                    "expected_status": [400, 422],
                })
        
        return test_cases

    def _generate_email_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate email-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body for reference
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Email finder endpoint (GET with query params - handled separately, not here)
        # This method only handles POST endpoints with request bodies
        
        # Email export endpoint error tests
        if endpoint_path == "/api/v3/email/export" and method == "POST":
            if valid_body:
                # Missing required contacts field
                test_cases.append({
                    "name": "missing_required_contacts",
                    "description": "Email export without required contacts field (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": {},
                    "expected_status": [400, 422],
                })
                
                # Empty contacts array
                empty_contacts_body = valid_body.copy()
                empty_contacts_body["contacts"] = []
                test_cases.append({
                    "name": "empty_contacts_array",
                    "description": "Email export with empty contacts array (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_contacts_body,
                    "expected_status": [400, 422],
                })
                
                # Invalid contacts structure (not an array)
                invalid_contacts_body = valid_body.copy()
                invalid_contacts_body["contacts"] = "not-an-array"
                test_cases.append({
                    "name": "invalid_contacts_type",
                    "description": "Email export with invalid contacts type (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_contacts_body,
                    "expected_status": [400, 422],
                })
        
        # Single email endpoint error tests
        if endpoint_path == "/api/v3/email/single/" and method == "POST":
            if valid_body:
                # Missing required first_name
                missing_first_name_body = valid_body.copy()
                missing_first_name_body.pop("first_name", None)
                test_cases.append({
                    "name": "missing_first_name",
                    "description": "Single email without first_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_first_name_body,
                    "expected_status": [400, 422],
                })
                
                # Missing required last_name
                missing_last_name_body = valid_body.copy()
                missing_last_name_body.pop("last_name", None)
                test_cases.append({
                    "name": "missing_last_name",
                    "description": "Single email without last_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_last_name_body,
                    "expected_status": [400, 422],
                })
                
                # Missing required domain
                missing_domain_body = valid_body.copy()
                missing_domain_body.pop("domain", None)
                test_cases.append({
                    "name": "missing_domain",
                    "description": "Single email without domain (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_domain_body,
                    "expected_status": [400, 422],
                })
                
                # Empty first_name
                empty_first_name_body = valid_body.copy()
                empty_first_name_body["first_name"] = ""
                test_cases.append({
                    "name": "empty_first_name",
                    "description": "Single email with empty first_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_first_name_body,
                    "expected_status": [400],
                })
                
                # Empty last_name
                empty_last_name_body = valid_body.copy()
                empty_last_name_body["last_name"] = ""
                test_cases.append({
                    "name": "empty_last_name",
                    "description": "Single email with empty last_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_last_name_body,
                    "expected_status": [400],
                })
                
                # Empty domain
                empty_domain_body = valid_body.copy()
                empty_domain_body["domain"] = ""
                test_cases.append({
                    "name": "empty_domain",
                    "description": "Single email with empty domain (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_domain_body,
                    "expected_status": [400],
                })
        
        # Bulk verifier endpoint error tests
        if endpoint_path == "/api/v3/email/bulk/verifier/" and method == "POST":
            if valid_body:
                # Missing required provider
                missing_provider_body = valid_body.copy()
                missing_provider_body.pop("provider", None)
                test_cases.append({
                    "name": "missing_provider",
                    "description": "Bulk verifier without provider (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_provider_body,
                    "expected_status": [400, 422],
                })
                
                # Missing required emails
                missing_emails_body = valid_body.copy()
                missing_emails_body.pop("emails", None)
                test_cases.append({
                    "name": "missing_emails",
                    "description": "Bulk verifier without emails array (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_emails_body,
                    "expected_status": [400, 422],
                })
                
                # Empty emails array
                empty_emails_body = valid_body.copy()
                empty_emails_body["emails"] = []
                test_cases.append({
                    "name": "empty_emails_array",
                    "description": "Bulk verifier with empty emails array (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_emails_body,
                    "expected_status": [400, 422],
                })
                
                # Invalid provider value
                invalid_provider_body = valid_body.copy()
                invalid_provider_body["provider"] = "invalid_provider"
                test_cases.append({
                    "name": "invalid_provider",
                    "description": "Bulk verifier with invalid provider (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_provider_body,
                    "expected_status": [400, 422],
                })
        
        # Single verifier endpoint error tests
        if endpoint_path == "/api/v3/email/single/verifier/" and method == "POST":
            if valid_body:
                # Missing required email
                missing_email_body = valid_body.copy()
                missing_email_body.pop("email", None)
                test_cases.append({
                    "name": "missing_email",
                    "description": "Single verifier without email (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_email_body,
                    "expected_status": [400, 422],
                })
                
                # Missing required provider
                missing_provider_body = valid_body.copy()
                missing_provider_body.pop("provider", None)
                test_cases.append({
                    "name": "missing_provider",
                    "description": "Single verifier without provider (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_provider_body,
                    "expected_status": [400, 422],
                })
                
                # Empty email
                empty_email_body = valid_body.copy()
                empty_email_body["email"] = ""
                test_cases.append({
                    "name": "empty_email",
                    "description": "Single verifier with empty email (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_email_body,
                    "expected_status": [400],
                })
                
                # Invalid email format
                invalid_email_body = valid_body.copy()
                invalid_email_body["email"] = "not-an-email"
                test_cases.append({
                    "name": "invalid_email_format",
                    "description": "Single verifier with invalid email format (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_email_body,
                    "expected_status": [400, 422],
                })
                
                # Invalid provider value
                invalid_provider_body = valid_body.copy()
                invalid_provider_body["provider"] = "invalid_provider"
                test_cases.append({
                    "name": "invalid_provider",
                    "description": "Single verifier with invalid provider (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_provider_body,
                    "expected_status": [400, 422],
                })
        
        # Verifier endpoint error tests
        if endpoint_path == "/api/v3/email/verifier/" and method == "POST":
            if valid_body:
                # Missing required fields
                test_cases.append({
                    "name": "missing_required_fields",
                    "description": "Verifier without required fields (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": {},
                    "expected_status": [400, 422],
                })
                
                # Missing first_name
                missing_first_name_body = valid_body.copy()
                missing_first_name_body.pop("first_name", None)
                test_cases.append({
                    "name": "missing_first_name",
                    "description": "Verifier without first_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_first_name_body,
                    "expected_status": [400, 422],
                })
                
                # Missing last_name
                missing_last_name_body = valid_body.copy()
                missing_last_name_body.pop("last_name", None)
                test_cases.append({
                    "name": "missing_last_name",
                    "description": "Verifier without last_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_last_name_body,
                    "expected_status": [400, 422],
                })
                
                # Missing domain
                missing_domain_body = valid_body.copy()
                missing_domain_body.pop("domain", None)
                test_cases.append({
                    "name": "missing_domain",
                    "description": "Verifier without domain (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_domain_body,
                    "expected_status": [400, 422],
                })
                
                # Invalid email_count (negative or zero)
                if "email_count" in valid_body:
                    invalid_email_count_body = valid_body.copy()
                    invalid_email_count_body["email_count"] = -1
                    test_cases.append({
                        "name": "invalid_email_count_negative",
                        "description": "Verifier with negative email_count (should fail)",
                        "method": method,
                        "endpoint": endpoint_path,
                        "body": invalid_email_count_body,
                        "expected_status": [400, 422],
                    })
                    
                    invalid_email_count_zero_body = valid_body.copy()
                    invalid_email_count_zero_body["email_count"] = 0
                    test_cases.append({
                        "name": "invalid_email_count_zero",
                        "description": "Verifier with email_count = 0 (should fail)",
                        "method": method,
                        "endpoint": endpoint_path,
                        "body": invalid_email_count_zero_body,
                        "expected_status": [400, 422],
                    })
        
        # Verifier single endpoint error tests
        if endpoint_path == "/api/v3/email/verifier/single/" and method == "POST":
            if valid_body:
                # Missing required fields
                test_cases.append({
                    "name": "missing_required_fields",
                    "description": "Verifier single without required fields (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": {},
                    "expected_status": [400, 422],
                })
                
                # Missing first_name
                missing_first_name_body = valid_body.copy()
                missing_first_name_body.pop("first_name", None)
                test_cases.append({
                    "name": "missing_first_name",
                    "description": "Verifier single without first_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_first_name_body,
                    "expected_status": [400, 422],
                })
                
                # Missing last_name
                missing_last_name_body = valid_body.copy()
                missing_last_name_body.pop("last_name", None)
                test_cases.append({
                    "name": "missing_last_name",
                    "description": "Verifier single without last_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_last_name_body,
                    "expected_status": [400, 422],
                })
                
                # Missing domain
                missing_domain_body = valid_body.copy()
                missing_domain_body.pop("domain", None)
                test_cases.append({
                    "name": "missing_domain",
                    "description": "Verifier single without domain (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_domain_body,
                    "expected_status": [400, 422],
                })
        
        return test_cases

    def _generate_email_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate email-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body for reference
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Email finder endpoint (GET with query params - handled separately, not here)
        # This method only handles POST endpoints with request bodies
        
        # Email export endpoint error tests
        if endpoint_path == "/api/v3/email/export" and method == "POST":
            if valid_body:
                # Missing required contacts field
                test_cases.append({
                    "name": "missing_required_contacts",
                    "description": "Email export without required contacts field (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": {},
                    "expected_status": [400, 422],
                })
                
                # Empty contacts array
                empty_contacts_body = valid_body.copy()
                empty_contacts_body["contacts"] = []
                test_cases.append({
                    "name": "empty_contacts_array",
                    "description": "Email export with empty contacts array (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_contacts_body,
                    "expected_status": [400, 422],
                })
                
                # Invalid contacts structure (not an array)
                invalid_contacts_body = valid_body.copy()
                invalid_contacts_body["contacts"] = "not-an-array"
                test_cases.append({
                    "name": "invalid_contacts_type",
                    "description": "Email export with invalid contacts type (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_contacts_body,
                    "expected_status": [400, 422],
                })
        
        # Single email endpoint error tests
        if endpoint_path == "/api/v3/email/single/" and method == "POST":
            if valid_body:
                # Missing required first_name
                missing_first_name_body = valid_body.copy()
                missing_first_name_body.pop("first_name", None)
                test_cases.append({
                    "name": "missing_first_name",
                    "description": "Single email without first_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_first_name_body,
                    "expected_status": [400, 422],
                })
                
                # Missing required last_name
                missing_last_name_body = valid_body.copy()
                missing_last_name_body.pop("last_name", None)
                test_cases.append({
                    "name": "missing_last_name",
                    "description": "Single email without last_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_last_name_body,
                    "expected_status": [400, 422],
                })
                
                # Missing required domain
                missing_domain_body = valid_body.copy()
                missing_domain_body.pop("domain", None)
                test_cases.append({
                    "name": "missing_domain",
                    "description": "Single email without domain (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_domain_body,
                    "expected_status": [400, 422],
                })
                
                # Empty first_name
                empty_first_name_body = valid_body.copy()
                empty_first_name_body["first_name"] = ""
                test_cases.append({
                    "name": "empty_first_name",
                    "description": "Single email with empty first_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_first_name_body,
                    "expected_status": [400],
                })
                
                # Empty last_name
                empty_last_name_body = valid_body.copy()
                empty_last_name_body["last_name"] = ""
                test_cases.append({
                    "name": "empty_last_name",
                    "description": "Single email with empty last_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_last_name_body,
                    "expected_status": [400],
                })
                
                # Empty domain
                empty_domain_body = valid_body.copy()
                empty_domain_body["domain"] = ""
                test_cases.append({
                    "name": "empty_domain",
                    "description": "Single email with empty domain (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_domain_body,
                    "expected_status": [400],
                })
        
        # Bulk verifier endpoint error tests
        if endpoint_path == "/api/v3/email/bulk/verifier/" and method == "POST":
            if valid_body:
                # Missing required provider
                missing_provider_body = valid_body.copy()
                missing_provider_body.pop("provider", None)
                test_cases.append({
                    "name": "missing_provider",
                    "description": "Bulk verifier without provider (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_provider_body,
                    "expected_status": [400, 422],
                })
                
                # Missing required emails
                missing_emails_body = valid_body.copy()
                missing_emails_body.pop("emails", None)
                test_cases.append({
                    "name": "missing_emails",
                    "description": "Bulk verifier without emails array (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_emails_body,
                    "expected_status": [400, 422],
                })
                
                # Empty emails array
                empty_emails_body = valid_body.copy()
                empty_emails_body["emails"] = []
                test_cases.append({
                    "name": "empty_emails_array",
                    "description": "Bulk verifier with empty emails array (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_emails_body,
                    "expected_status": [400, 422],
                })
                
                # Invalid provider value
                invalid_provider_body = valid_body.copy()
                invalid_provider_body["provider"] = "invalid_provider"
                test_cases.append({
                    "name": "invalid_provider",
                    "description": "Bulk verifier with invalid provider (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_provider_body,
                    "expected_status": [400, 422],
                })
        
        # Single verifier endpoint error tests
        if endpoint_path == "/api/v3/email/single/verifier/" and method == "POST":
            if valid_body:
                # Missing required email
                missing_email_body = valid_body.copy()
                missing_email_body.pop("email", None)
                test_cases.append({
                    "name": "missing_email",
                    "description": "Single verifier without email (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_email_body,
                    "expected_status": [400, 422],
                })
                
                # Missing required provider
                missing_provider_body = valid_body.copy()
                missing_provider_body.pop("provider", None)
                test_cases.append({
                    "name": "missing_provider",
                    "description": "Single verifier without provider (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_provider_body,
                    "expected_status": [400, 422],
                })
                
                # Empty email
                empty_email_body = valid_body.copy()
                empty_email_body["email"] = ""
                test_cases.append({
                    "name": "empty_email",
                    "description": "Single verifier with empty email (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_email_body,
                    "expected_status": [400],
                })
                
                # Invalid email format
                invalid_email_body = valid_body.copy()
                invalid_email_body["email"] = "not-an-email"
                test_cases.append({
                    "name": "invalid_email_format",
                    "description": "Single verifier with invalid email format (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_email_body,
                    "expected_status": [400, 422],
                })
                
                # Invalid provider value
                invalid_provider_body = valid_body.copy()
                invalid_provider_body["provider"] = "invalid_provider"
                test_cases.append({
                    "name": "invalid_provider",
                    "description": "Single verifier with invalid provider (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_provider_body,
                    "expected_status": [400, 422],
                })
        
        # Verifier endpoint error tests
        if endpoint_path == "/api/v3/email/verifier/" and method == "POST":
            if valid_body:
                # Missing required fields
                test_cases.append({
                    "name": "missing_required_fields",
                    "description": "Verifier without required fields (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": {},
                    "expected_status": [400, 422],
                })
                
                # Missing first_name
                missing_first_name_body = valid_body.copy()
                missing_first_name_body.pop("first_name", None)
                test_cases.append({
                    "name": "missing_first_name",
                    "description": "Verifier without first_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_first_name_body,
                    "expected_status": [400, 422],
                })
                
                # Missing last_name
                missing_last_name_body = valid_body.copy()
                missing_last_name_body.pop("last_name", None)
                test_cases.append({
                    "name": "missing_last_name",
                    "description": "Verifier without last_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_last_name_body,
                    "expected_status": [400, 422],
                })
                
                # Missing domain
                missing_domain_body = valid_body.copy()
                missing_domain_body.pop("domain", None)
                test_cases.append({
                    "name": "missing_domain",
                    "description": "Verifier without domain (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_domain_body,
                    "expected_status": [400, 422],
                })
                
                # Invalid email_count (negative or zero)
                if "email_count" in valid_body:
                    invalid_email_count_body = valid_body.copy()
                    invalid_email_count_body["email_count"] = -1
                    test_cases.append({
                        "name": "invalid_email_count_negative",
                        "description": "Verifier with negative email_count (should fail)",
                        "method": method,
                        "endpoint": endpoint_path,
                        "body": invalid_email_count_body,
                        "expected_status": [400, 422],
                    })
                    
                    invalid_email_count_zero_body = valid_body.copy()
                    invalid_email_count_zero_body["email_count"] = 0
                    test_cases.append({
                        "name": "invalid_email_count_zero",
                        "description": "Verifier with email_count = 0 (should fail)",
                        "method": method,
                        "endpoint": endpoint_path,
                        "body": invalid_email_count_zero_body,
                        "expected_status": [400, 422],
                    })
        
        # Verifier single endpoint error tests
        if endpoint_path == "/api/v3/email/verifier/single/" and method == "POST":
            if valid_body:
                # Missing required fields
                test_cases.append({
                    "name": "missing_required_fields",
                    "description": "Verifier single without required fields (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": {},
                    "expected_status": [400, 422],
                })
                
                # Missing first_name
                missing_first_name_body = valid_body.copy()
                missing_first_name_body.pop("first_name", None)
                test_cases.append({
                    "name": "missing_first_name",
                    "description": "Verifier single without first_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_first_name_body,
                    "expected_status": [400, 422],
                })
                
                # Missing last_name
                missing_last_name_body = valid_body.copy()
                missing_last_name_body.pop("last_name", None)
                test_cases.append({
                    "name": "missing_last_name",
                    "description": "Verifier single without last_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_last_name_body,
                    "expected_status": [400, 422],
                })
                
                # Missing domain
                missing_domain_body = valid_body.copy()
                missing_domain_body.pop("domain", None)
                test_cases.append({
                    "name": "missing_domain",
                    "description": "Verifier single without domain (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_domain_body,
                    "expected_status": [400, 422],
                })
        
        return test_cases

    def _generate_usage_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate usage-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body (if available)
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Track usage endpoint error tests
        if endpoint_path == "/api/v1/usage/track/":
            if valid_body:
                # Invalid feature name
                invalid_feature_body = valid_body.copy()
                invalid_feature_body["feature"] = "INVALID_FEATURE"
                test_cases.append({
                    "name": "invalid_feature",
                    "description": "Track usage with invalid feature name",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_feature_body,
                    "expected_status": [400],
                })
                
                # Invalid amount (0 or negative)
                invalid_amount_body = valid_body.copy()
                invalid_amount_body["amount"] = 0
                test_cases.append({
                    "name": "invalid_amount_zero",
                    "description": "Track usage with amount = 0 (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_amount_body,
                    "expected_status": [422],
                })
                
                invalid_amount_body_negative = valid_body.copy()
                invalid_amount_body_negative["amount"] = -1
                test_cases.append({
                    "name": "invalid_amount_negative",
                    "description": "Track usage with negative amount (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_amount_body_negative,
                    "expected_status": [422],
                })
        
        # Reset usage endpoint error tests
        if endpoint_path == "/api/v2/usage/reset":
            if valid_body:
                # Invalid feature name
                invalid_feature_body = valid_body.copy()
                invalid_feature_body["feature"] = "INVALID_FEATURE"
                test_cases.append({
                    "name": "invalid_feature",
                    "description": "Reset usage with invalid feature name",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_feature_body,
                    "expected_status": [400],
                })
        
        return test_cases
    
    def _generate_scrape_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate scrape-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body (if available)
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Sales Navigator scrape endpoint error tests
        if endpoint_path == "/api/v3/sales-navigator/scrape":
            if valid_body:
                # Empty HTML
                empty_html_body = valid_body.copy()
                empty_html_body["html"] = ""
                test_cases.append({
                    "name": "empty_html",
                    "description": "Scrape with empty HTML (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_html_body,
                    "expected_status": [422, 400],
                })
                
                # Whitespace-only HTML
                whitespace_html_body = valid_body.copy()
                whitespace_html_body["html"] = "   \n\t  "
                test_cases.append({
                    "name": "whitespace_only_html",
                    "description": "Scrape with whitespace-only HTML (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": whitespace_html_body,
                    "expected_status": [422, 400],
                })
                
                # Missing HTML field
                missing_html_body = {"save": False}
                test_cases.append({
                    "name": "missing_html_field",
                    "description": "Scrape with missing HTML field (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_html_body,
                    "expected_status": [422],
                })
                
                # Invalid HTML type (not string)
                invalid_type_body = valid_body.copy()
                invalid_type_body["html"] = 12345
                test_cases.append({
                    "name": "invalid_html_type",
                    "description": "Scrape with invalid HTML type (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_type_body,
                    "expected_status": [422],
                })
        
        return test_cases


    def _get_expected_status_for_empty_body(self, endpoint_path: str, method: str) -> List[int]:
        """Get expected status codes for empty body requests based on endpoint behavior.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
        
        Returns:
            List of expected status codes
        """
        # Endpoints that allow empty body and return success
        allows_empty_body = {
            "POST /api/v2/ai-chats/": [201],  # Creates chat with empty body
            "POST /api/v1/auth/logout/": [200],  # Logout accepts empty body and returns 200
            "PUT /api/v1/users/profile/": [200],  # Profile update accepts empty body (all fields optional, partial update)
        }
        
        # Endpoints that return 404 for invalid IDs (before body validation)
        returns_404_for_invalid_id = {
            "PUT /api/v2/ai-chats/{chat_id}/": [404],  # Resource not found takes precedence
            "PUT /api/v4/admin/dashboard-pages/{page_id}": [404],  # Page not found
            "PUT /api/v4/admin/marketing/{page_id}": [404],  # Page not found
            "POST /api/v4/admin/marketing/{page_id}/publish": [404],  # Page not found
        }
        
        # Check exact match
        key = f"{method} {endpoint_path}"
        if key in allows_empty_body:
            return allows_empty_body[key]
        if key in returns_404_for_invalid_id:
            return returns_404_for_invalid_id[key]
        
        # Check pattern matches for endpoints with placeholders
        for pattern, statuses in returns_404_for_invalid_id.items():
            pattern_method, pattern_path = pattern.split(" ", 1)
            if method == pattern_method:
                # Check if endpoint structure matches (same number of parts)
                pattern_parts = pattern_path.split("/")
                endpoint_parts = endpoint_path.split("/")
                if len(pattern_parts) == len(endpoint_parts):
                    # Check if non-placeholder parts match
                    matches = True
                    for p, e in zip(pattern_parts, endpoint_parts):
                        if p.startswith("{") and p.endswith("}"):
                            continue  # Skip placeholder parts
                        if p != e:
                            matches = False
                            break
                    if matches:
                        return statuses
        
        # Default: expect validation error
        return [422, 400]
    
    def _generate_user_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate user-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body (if available)
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Registration endpoint error tests
        if endpoint_path in ["/api/v1/auth/register", "/api/v1/auth/register/"]:
            if valid_body:
                # Short password (< 8 chars)
                short_password_body = valid_body.copy()
                short_password_body["password"] = "short"
                test_cases.append({
                    "name": "short_password",
                    "description": "Registration with password too short (< 8 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": short_password_body,
                    "expected_status": [400],
                })
                
                # Long password (> 72 chars)
                long_password_body = valid_body.copy()
                long_password_body["password"] = "a" * 73
                test_cases.append({
                    "name": "long_password",
                    "description": "Registration with password too long (> 72 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": long_password_body,
                    "expected_status": [400],
                })
                
                # Invalid email format
                invalid_email_body = valid_body.copy()
                invalid_email_body["email"] = "not-an-email"
                test_cases.append({
                    "name": "invalid_email",
                    "description": "Registration with invalid email format",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_email_body,
                    "expected_status": [422],
                })
        
        # Login endpoint error tests
        if endpoint_path == "/api/v1/auth/login/":
            if valid_body:
                # Invalid credentials
                invalid_creds_body = valid_body.copy()
                invalid_creds_body["password"] = "wrongpassword"
                test_cases.append({
                    "name": "invalid_credentials",
                    "description": "Login with invalid credentials",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_creds_body,
                    "expected_status": [400],
                })
        
        # Profile update endpoint error tests
        if endpoint_path == "/api/v1/users/profile/":
            if valid_body:
                # Name too long (> 255 chars)
                long_name_body = valid_body.copy()
                long_name_body["name"] = "a" * 256
                test_cases.append({
                    "name": "long_name",
                    "description": "Profile update with name too long (> 255 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": long_name_body,
                    "expected_status": [400, 422],  # FastAPI returns 422 for validation errors
                })
                
                # Timezone too long (> 100 chars)
                long_timezone_body = valid_body.copy()
                long_timezone_body["timezone"] = "a" * 101
                test_cases.append({
                    "name": "long_timezone",
                    "description": "Profile update with timezone too long (> 100 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": long_timezone_body,
                    "expected_status": [400, 422],  # FastAPI returns 422 for validation errors
                })
        
        # Role update endpoint error tests
        if "/users/{user_id}/role/" in endpoint_path:
            if valid_body:
                # Invalid role
                invalid_role_body = valid_body.copy()
                invalid_role_body["role"] = "InvalidRole"
                test_cases.append({
                    "name": "invalid_role",
                    "description": "Role update with invalid role value",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_role_body,
                    "expected_status": [400],
                })
        
        # Credits update endpoint error tests
        if "/users/{user_id}/credits/" in endpoint_path:
            if valid_body:
                # Negative credits
                negative_credits_body = valid_body.copy()
                negative_credits_body["credits"] = -1
                test_cases.append({
                    "name": "negative_credits",
                    "description": "Credits update with negative value",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": negative_credits_body,
                    "expected_status": [422, 400],
                })
        
        return test_cases
    
    def _generate_s3_endpoint_error_tests(
        self, endpoint_path: str, method: str
    ) -> List[Dict[str, Any]]:
        """Generate S3-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # S3 file get endpoint error tests (with file_id path parameter)
        if "/s3/files/{file_id}" in endpoint_path or "/s3/files/" in endpoint_path and "{file_id}" in endpoint_path:
            # Invalid pagination parameters
            # Limit too large (> 1000)
            test_cases.append({
                "name": "invalid_limit_too_large",
                "description": "Get S3 file with limit > 1000 (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 2000,
                    "offset": 0
                },
                "expected_status": [422],
            })
            
            # Negative offset
            test_cases.append({
                "name": "invalid_offset_negative",
                "description": "Get S3 file with negative offset (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 50,
                    "offset": -10
                },
                "expected_status": [422],
            })
            
            # Limit = 0 (below minimum)
            test_cases.append({
                "name": "invalid_limit_zero",
                "description": "Get S3 file with limit = 0 (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 0,
                    "offset": 0
                },
                "expected_status": [422],
            })
            
            # Limit without offset (should still work, offset defaults to 0)
            test_cases.append({
                "name": "limit_without_offset",
                "description": "Get S3 file with limit but no offset (offset defaults to 0)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 50
                },
                "expected_status": [200],
            })
            
            # Offset without limit (should fail - limit is required for pagination)
            test_cases.append({
                "name": "offset_without_limit",
                "description": "Get S3 file with offset but no limit (should fail or default to download mode)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "offset": 10
                },
                "expected_status": [200, 422],  # May default to download mode or fail validation
            })
        
        return test_cases
    
    def _generate_root_endpoint_error_tests(
        self, endpoint_path: str, method: str
    ) -> List[Dict[str, Any]]:
        """Generate Root-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Root endpoints are designed to be highly available and should rarely return errors
        # The only documented error is 500 Internal Server Error (server configuration issue)
        # Since these are public endpoints, we don't test authentication errors
        
        # Note: Root endpoints don't have request bodies or complex query parameters
        # Error scenarios are limited to server errors (500)
        # These are typically not testable in normal test runs, but we document them
        
        return test_cases
    
    def _generate_marketing_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate Marketing-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body for reference
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Marketing create endpoint error tests
        if endpoint_path == "/api/v4/admin/marketing/" and method == "POST":
            # Missing required hero field
            test_cases.append({
                "name": "missing_required_hero",
                "description": "Create marketing page without required hero field (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "page_id": "test-page"
                    # Missing hero
                },
                "expected_status": [400, 422],
            })
            
            # Missing required page_id
            test_cases.append({
                "name": "missing_required_page_id",
                "description": "Create marketing page without required page_id (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "hero": {
                        "title": "Test Title",
                        "description": "Test description"
                    }
                    # Missing page_id
                },
                "expected_status": [400, 422],
            })
            
            # Invalid metadata status
            if valid_body:
                invalid_status_body = valid_body.copy()
                invalid_status_body["metadata"] = {
                    "title": "Test Title",
                    "description": "Test description",
                    "status": "invalid_status"  # Invalid status
                }
                test_cases.append({
                    "name": "invalid_metadata_status",
                    "description": "Create marketing page with invalid status (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_status_body,
                    "expected_status": [400, 422],
                })
        
        # Marketing update endpoint error tests
        if endpoint_path.startswith("/api/v4/admin/marketing/") and "{page_id}" in endpoint_path and method == "PUT":
            # Empty body (partial update allows empty, but we test it)
            test_cases.append({
                "name": "empty_update_body",
                "description": "Update marketing page with empty body (partial update - should work)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {},
                "expected_status": [200, 400],  # May work or fail depending on implementation
            })
        
        return test_cases
    
    def _generate_linkedin_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate LinkedIn-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body for reference
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # LinkedIn search endpoint error tests
        if endpoint_path == "/api/v3/linkedin/" and method == "POST":
            # Missing required url field
            test_cases.append({
                "name": "missing_required_url",
                "description": "LinkedIn search without required url field (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {},
                "expected_status": [400, 422],
            })
            
            # Empty URL string
            test_cases.append({
                "name": "empty_url",
                "description": "LinkedIn search with empty URL (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "url": ""
                },
                "expected_status": [400],
            })
            
            # Invalid URL format
            test_cases.append({
                "name": "invalid_url_format",
                "description": "LinkedIn search with invalid URL format (may fail or return empty results)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "url": "not-a-linkedin-url"
                },
                "expected_status": [200, 400],  # May return empty results or error
            })
            
            # Wrong data type for URL
            test_cases.append({
                "name": "invalid_url_type",
                "description": "LinkedIn search with non-string URL (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "url": 12345
                },
                "expected_status": [400, 422],
            })
        
        return test_cases
    
    def _generate_usage_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate usage-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body (if available)
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Track usage endpoint error tests
        if endpoint_path == "/api/v1/usage/track/":
            if valid_body:
                # Invalid feature name
                invalid_feature_body = valid_body.copy()
                invalid_feature_body["feature"] = "INVALID_FEATURE"
                test_cases.append({
                    "name": "invalid_feature",
                    "description": "Track usage with invalid feature name",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_feature_body,
                    "expected_status": [400],
                })
                
                # Invalid amount (0 or negative)
                invalid_amount_body = valid_body.copy()
                invalid_amount_body["amount"] = 0
                test_cases.append({
                    "name": "invalid_amount_zero",
                    "description": "Track usage with amount = 0 (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_amount_body,
                    "expected_status": [422],
                })
                
                invalid_amount_body_negative = valid_body.copy()
                invalid_amount_body_negative["amount"] = -1
                test_cases.append({
                    "name": "invalid_amount_negative",
                    "description": "Track usage with negative amount (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_amount_body_negative,
                    "expected_status": [422],
                })
        
        # Reset usage endpoint error tests
        if endpoint_path == "/api/v2/usage/reset":
            if valid_body:
                # Invalid feature name
                invalid_feature_body = valid_body.copy()
                invalid_feature_body["feature"] = "INVALID_FEATURE"
                test_cases.append({
                    "name": "invalid_feature",
                    "description": "Reset usage with invalid feature name",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_feature_body,
                    "expected_status": [400],
                })
        
        return test_cases
    
    def _generate_scrape_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate scrape-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body (if available)
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Sales Navigator scrape endpoint error tests
        if endpoint_path == "/api/v3/sales-navigator/scrape":
            if valid_body:
                # Empty HTML
                empty_html_body = valid_body.copy()
                empty_html_body["html"] = ""
                test_cases.append({
                    "name": "empty_html",
                    "description": "Scrape with empty HTML (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_html_body,
                    "expected_status": [422, 400],
                })
                
                # Whitespace-only HTML
                whitespace_html_body = valid_body.copy()
                whitespace_html_body["html"] = "   \n\t  "
                test_cases.append({
                    "name": "whitespace_only_html",
                    "description": "Scrape with whitespace-only HTML (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": whitespace_html_body,
                    "expected_status": [422, 400],
                })
                
                # Missing HTML field
                missing_html_body = {"save": False}
                test_cases.append({
                    "name": "missing_html_field",
                    "description": "Scrape with missing HTML field (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_html_body,
                    "expected_status": [422],
                })
                
                # Invalid HTML type (not string)
                invalid_type_body = valid_body.copy()
                invalid_type_body["html"] = 12345
                test_cases.append({
                    "name": "invalid_html_type",
                    "description": "Scrape with invalid HTML type (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_type_body,
                    "expected_status": [422],
                })
        
        return test_cases


    def _get_expected_status_for_empty_body(self, endpoint_path: str, method: str) -> List[int]:
        """Get expected status codes for empty body requests based on endpoint behavior.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
        
        Returns:
            List of expected status codes
        """
        # Endpoints that allow empty body and return success
        allows_empty_body = {
            "POST /api/v2/ai-chats/": [201],  # Creates chat with empty body
            "POST /api/v1/auth/logout/": [200],  # Logout accepts empty body and returns 200
            "PUT /api/v1/users/profile/": [200],  # Profile update accepts empty body (all fields optional, partial update)
        }
        
        # Endpoints that return 404 for invalid IDs (before body validation)
        returns_404_for_invalid_id = {
            "PUT /api/v2/ai-chats/{chat_id}/": [404],  # Resource not found takes precedence
            "PUT /api/v4/admin/dashboard-pages/{page_id}": [404],  # Page not found
            "PUT /api/v4/admin/marketing/{page_id}": [404],  # Page not found
            "POST /api/v4/admin/marketing/{page_id}/publish": [404],  # Page not found
        }
        
        # Check exact match
        key = f"{method} {endpoint_path}"
        if key in allows_empty_body:
            return allows_empty_body[key]
        if key in returns_404_for_invalid_id:
            return returns_404_for_invalid_id[key]
        
        # Check pattern matches for endpoints with placeholders
        for pattern, statuses in returns_404_for_invalid_id.items():
            pattern_method, pattern_path = pattern.split(" ", 1)
            if method == pattern_method:
                # Check if endpoint structure matches (same number of parts)
                pattern_parts = pattern_path.split("/")
                endpoint_parts = endpoint_path.split("/")
                if len(pattern_parts) == len(endpoint_parts):
                    # Check if non-placeholder parts match
                    matches = True
                    for p, e in zip(pattern_parts, endpoint_parts):
                        if p.startswith("{") and p.endswith("}"):
                            continue  # Skip placeholder parts
                        if p != e:
                            matches = False
                            break
                    if matches:
                        return statuses
        
        # Default: expect validation error
        return [422, 400]
    
    def _generate_user_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate user-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body (if available)
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Registration endpoint error tests
        if endpoint_path in ["/api/v1/auth/register", "/api/v1/auth/register/"]:
            if valid_body:
                # Short password (< 8 chars)
                short_password_body = valid_body.copy()
                short_password_body["password"] = "short"
                test_cases.append({
                    "name": "short_password",
                    "description": "Registration with password too short (< 8 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": short_password_body,
                    "expected_status": [400],
                })
                
                # Long password (> 72 chars)
                long_password_body = valid_body.copy()
                long_password_body["password"] = "a" * 73
                test_cases.append({
                    "name": "long_password",
                    "description": "Registration with password too long (> 72 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": long_password_body,
                    "expected_status": [400],
                })
                
                # Invalid email format
                invalid_email_body = valid_body.copy()
                invalid_email_body["email"] = "not-an-email"
                test_cases.append({
                    "name": "invalid_email",
                    "description": "Registration with invalid email format",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_email_body,
                    "expected_status": [422],
                })
        
        # Login endpoint error tests
        if endpoint_path == "/api/v1/auth/login/":
            if valid_body:
                # Invalid credentials
                invalid_creds_body = valid_body.copy()
                invalid_creds_body["password"] = "wrongpassword"
                test_cases.append({
                    "name": "invalid_credentials",
                    "description": "Login with invalid credentials",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_creds_body,
                    "expected_status": [400],
                })
        
        # Profile update endpoint error tests
        if endpoint_path == "/api/v1/users/profile/":
            if valid_body:
                # Name too long (> 255 chars)
                long_name_body = valid_body.copy()
                long_name_body["name"] = "a" * 256
                test_cases.append({
                    "name": "long_name",
                    "description": "Profile update with name too long (> 255 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": long_name_body,
                    "expected_status": [400, 422],  # FastAPI returns 422 for validation errors
                })
                
                # Timezone too long (> 100 chars)
                long_timezone_body = valid_body.copy()
                long_timezone_body["timezone"] = "a" * 101
                test_cases.append({
                    "name": "long_timezone",
                    "description": "Profile update with timezone too long (> 100 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": long_timezone_body,
                    "expected_status": [400, 422],  # FastAPI returns 422 for validation errors
                })
        
        # Role update endpoint error tests
        if "/users/{user_id}/role/" in endpoint_path:
            if valid_body:
                # Invalid role
                invalid_role_body = valid_body.copy()
                invalid_role_body["role"] = "InvalidRole"
                test_cases.append({
                    "name": "invalid_role",
                    "description": "Role update with invalid role value",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_role_body,
                    "expected_status": [400],
                })
        
        # Credits update endpoint error tests
        if "/users/{user_id}/credits/" in endpoint_path:
            if valid_body:
                # Negative credits
                negative_credits_body = valid_body.copy()
                negative_credits_body["credits"] = -1
                test_cases.append({
                    "name": "negative_credits",
                    "description": "Credits update with negative value",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": negative_credits_body,
                    "expected_status": [422, 400],
                })
        
        return test_cases
    
    def _generate_s3_endpoint_error_tests(
        self, endpoint_path: str, method: str
    ) -> List[Dict[str, Any]]:
        """Generate S3-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # S3 file get endpoint error tests (with file_id path parameter)
        if "/s3/files/{file_id}" in endpoint_path or "/s3/files/" in endpoint_path and "{file_id}" in endpoint_path:
            # Invalid pagination parameters
            # Limit too large (> 1000)
            test_cases.append({
                "name": "invalid_limit_too_large",
                "description": "Get S3 file with limit > 1000 (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 2000,
                    "offset": 0
                },
                "expected_status": [422],
            })
            
            # Negative offset
            test_cases.append({
                "name": "invalid_offset_negative",
                "description": "Get S3 file with negative offset (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 50,
                    "offset": -10
                },
                "expected_status": [422],
            })
            
            # Limit = 0 (below minimum)
            test_cases.append({
                "name": "invalid_limit_zero",
                "description": "Get S3 file with limit = 0 (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 0,
                    "offset": 0
                },
                "expected_status": [422],
            })
            
            # Limit without offset (should still work, offset defaults to 0)
            test_cases.append({
                "name": "limit_without_offset",
                "description": "Get S3 file with limit but no offset (offset defaults to 0)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 50
                },
                "expected_status": [200],
            })
            
            # Offset without limit (should fail - limit is required for pagination)
            test_cases.append({
                "name": "offset_without_limit",
                "description": "Get S3 file with offset but no limit (should fail or default to download mode)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "offset": 10
                },
                "expected_status": [200, 422],  # May default to download mode or fail validation
            })
        
        return test_cases
    
    def _generate_root_endpoint_error_tests(
        self, endpoint_path: str, method: str
    ) -> List[Dict[str, Any]]:
        """Generate Root-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Root endpoints are designed to be highly available and should rarely return errors
        # The only documented error is 500 Internal Server Error (server configuration issue)
        # Since these are public endpoints, we don't test authentication errors
        
        # Note: Root endpoints don't have request bodies or complex query parameters
        # Error scenarios are limited to server errors (500)
        # These are typically not testable in normal test runs, but we document them
        
        return test_cases
    
    def _generate_marketing_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate Marketing-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body for reference
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Marketing create endpoint error tests
        if endpoint_path == "/api/v4/admin/marketing/" and method == "POST":
            # Missing required hero field
            test_cases.append({
                "name": "missing_required_hero",
                "description": "Create marketing page without required hero field (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "page_id": "test-page"
                    # Missing hero
                },
                "expected_status": [400, 422],
            })
            
            # Missing required page_id
            test_cases.append({
                "name": "missing_required_page_id",
                "description": "Create marketing page without required page_id (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "hero": {
                        "title": "Test Title",
                        "description": "Test description"
                    }
                    # Missing page_id
                },
                "expected_status": [400, 422],
            })
            
            # Invalid metadata status
            if valid_body:
                invalid_status_body = valid_body.copy()
                invalid_status_body["metadata"] = {
                    "title": "Test Title",
                    "description": "Test description",
                    "status": "invalid_status"  # Invalid status
                }
                test_cases.append({
                    "name": "invalid_metadata_status",
                    "description": "Create marketing page with invalid status (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_status_body,
                    "expected_status": [400, 422],
                })
        
        # Marketing update endpoint error tests
        if endpoint_path.startswith("/api/v4/admin/marketing/") and "{page_id}" in endpoint_path and method == "PUT":
            # Empty body (partial update allows empty, but we test it)
            test_cases.append({
                "name": "empty_update_body",
                "description": "Update marketing page with empty body (partial update - should work)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {},
                "expected_status": [200, 400],  # May work or fail depending on implementation
            })
        
        return test_cases
    
    def _generate_linkedin_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate LinkedIn-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body for reference
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # LinkedIn search endpoint error tests
        if endpoint_path == "/api/v3/linkedin/" and method == "POST":
            # Missing required url field
            test_cases.append({
                "name": "missing_required_url",
                "description": "LinkedIn search without required url field (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {},
                "expected_status": [400, 422],
            })
            
            # Empty URL string
            test_cases.append({
                "name": "empty_url",
                "description": "LinkedIn search with empty URL (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "url": ""
                },
                "expected_status": [400],
            })
            
            # Invalid URL format
            test_cases.append({
                "name": "invalid_url_format",
                "description": "LinkedIn search with invalid URL format (may fail or return empty results)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "url": "not-a-linkedin-url"
                },
                "expected_status": [200, 400],  # May return empty results or error
            })
            
            # Wrong data type for URL
            test_cases.append({
                "name": "invalid_url_type",
                "description": "LinkedIn search with non-string URL (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "url": 12345
                },
                "expected_status": [400, 422],
            })
        
        return test_cases
    
    def _generate_usage_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate usage-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body (if available)
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Track usage endpoint error tests
        if endpoint_path == "/api/v1/usage/track/":
            if valid_body:
                # Invalid feature name
                invalid_feature_body = valid_body.copy()
                invalid_feature_body["feature"] = "INVALID_FEATURE"
                test_cases.append({
                    "name": "invalid_feature",
                    "description": "Track usage with invalid feature name",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_feature_body,
                    "expected_status": [400],
                })
                
                # Invalid amount (0 or negative)
                invalid_amount_body = valid_body.copy()
                invalid_amount_body["amount"] = 0
                test_cases.append({
                    "name": "invalid_amount_zero",
                    "description": "Track usage with amount = 0 (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_amount_body,
                    "expected_status": [422],
                })
                
                invalid_amount_body_negative = valid_body.copy()
                invalid_amount_body_negative["amount"] = -1
                test_cases.append({
                    "name": "invalid_amount_negative",
                    "description": "Track usage with negative amount (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_amount_body_negative,
                    "expected_status": [422],
                })
        
        # Reset usage endpoint error tests
        if endpoint_path == "/api/v2/usage/reset":
            if valid_body:
                # Invalid feature name
                invalid_feature_body = valid_body.copy()
                invalid_feature_body["feature"] = "INVALID_FEATURE"
                test_cases.append({
                    "name": "invalid_feature",
                    "description": "Reset usage with invalid feature name",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_feature_body,
                    "expected_status": [400],
                })
        
        return test_cases
    
    def _generate_scrape_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate scrape-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body (if available)
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Sales Navigator scrape endpoint error tests
        if endpoint_path == "/api/v3/sales-navigator/scrape":
            if valid_body:
                # Empty HTML
                empty_html_body = valid_body.copy()
                empty_html_body["html"] = ""
                test_cases.append({
                    "name": "empty_html",
                    "description": "Scrape with empty HTML (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_html_body,
                    "expected_status": [422, 400],
                })
                
                # Whitespace-only HTML
                whitespace_html_body = valid_body.copy()
                whitespace_html_body["html"] = "   \n\t  "
                test_cases.append({
                    "name": "whitespace_only_html",
                    "description": "Scrape with whitespace-only HTML (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": whitespace_html_body,
                    "expected_status": [422, 400],
                })
                
                # Missing HTML field
                missing_html_body = {"save": False}
                test_cases.append({
                    "name": "missing_html_field",
                    "description": "Scrape with missing HTML field (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_html_body,
                    "expected_status": [422],
                })
                
                # Invalid HTML type (not string)
                invalid_type_body = valid_body.copy()
                invalid_type_body["html"] = 12345
                test_cases.append({
                    "name": "invalid_html_type",
                    "description": "Scrape with invalid HTML type (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_type_body,
                    "expected_status": [422],
                })
        
        return test_cases


    def _get_expected_status_for_empty_body(self, endpoint_path: str, method: str) -> List[int]:
        """Get expected status codes for empty body requests based on endpoint behavior.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
        
        Returns:
            List of expected status codes
        """
        # Endpoints that allow empty body and return success
        allows_empty_body = {
            "POST /api/v2/ai-chats/": [201],  # Creates chat with empty body
            "POST /api/v1/auth/logout/": [200],  # Logout accepts empty body and returns 200
            "PUT /api/v1/users/profile/": [200],  # Profile update accepts empty body (all fields optional, partial update)
        }
        
        # Endpoints that return 404 for invalid IDs (before body validation)
        returns_404_for_invalid_id = {
            "PUT /api/v2/ai-chats/{chat_id}/": [404],  # Resource not found takes precedence
            "PUT /api/v4/admin/dashboard-pages/{page_id}": [404],  # Page not found
            "PUT /api/v4/admin/marketing/{page_id}": [404],  # Page not found
            "POST /api/v4/admin/marketing/{page_id}/publish": [404],  # Page not found
        }
        
        # Check exact match
        key = f"{method} {endpoint_path}"
        if key in allows_empty_body:
            return allows_empty_body[key]
        if key in returns_404_for_invalid_id:
            return returns_404_for_invalid_id[key]
        
        # Check pattern matches for endpoints with placeholders
        for pattern, statuses in returns_404_for_invalid_id.items():
            pattern_method, pattern_path = pattern.split(" ", 1)
            if method == pattern_method:
                # Check if endpoint structure matches (same number of parts)
                pattern_parts = pattern_path.split("/")
                endpoint_parts = endpoint_path.split("/")
                if len(pattern_parts) == len(endpoint_parts):
                    # Check if non-placeholder parts match
                    matches = True
                    for p, e in zip(pattern_parts, endpoint_parts):
                        if p.startswith("{") and p.endswith("}"):
                            continue  # Skip placeholder parts
                        if p != e:
                            matches = False
                            break
                    if matches:
                        return statuses
        
        # Default: expect validation error
        return [422, 400]
    
    def _generate_user_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate user-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body (if available)
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Registration endpoint error tests
        if endpoint_path in ["/api/v1/auth/register", "/api/v1/auth/register/"]:
            if valid_body:
                # Short password (< 8 chars)
                short_password_body = valid_body.copy()
                short_password_body["password"] = "short"
                test_cases.append({
                    "name": "short_password",
                    "description": "Registration with password too short (< 8 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": short_password_body,
                    "expected_status": [400],
                })
                
                # Long password (> 72 chars)
                long_password_body = valid_body.copy()
                long_password_body["password"] = "a" * 73
                test_cases.append({
                    "name": "long_password",
                    "description": "Registration with password too long (> 72 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": long_password_body,
                    "expected_status": [400],
                })
                
                # Invalid email format
                invalid_email_body = valid_body.copy()
                invalid_email_body["email"] = "not-an-email"
                test_cases.append({
                    "name": "invalid_email",
                    "description": "Registration with invalid email format",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_email_body,
                    "expected_status": [422],
                })
        
        # Login endpoint error tests
        if endpoint_path == "/api/v1/auth/login/":
            if valid_body:
                # Invalid credentials
                invalid_creds_body = valid_body.copy()
                invalid_creds_body["password"] = "wrongpassword"
                test_cases.append({
                    "name": "invalid_credentials",
                    "description": "Login with invalid credentials",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_creds_body,
                    "expected_status": [400],
                })
        
        # Profile update endpoint error tests
        if endpoint_path == "/api/v1/users/profile/":
            if valid_body:
                # Name too long (> 255 chars)
                long_name_body = valid_body.copy()
                long_name_body["name"] = "a" * 256
                test_cases.append({
                    "name": "long_name",
                    "description": "Profile update with name too long (> 255 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": long_name_body,
                    "expected_status": [400, 422],  # FastAPI returns 422 for validation errors
                })
                
                # Timezone too long (> 100 chars)
                long_timezone_body = valid_body.copy()
                long_timezone_body["timezone"] = "a" * 101
                test_cases.append({
                    "name": "long_timezone",
                    "description": "Profile update with timezone too long (> 100 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": long_timezone_body,
                    "expected_status": [400, 422],  # FastAPI returns 422 for validation errors
                })
        
        # Role update endpoint error tests
        if "/users/{user_id}/role/" in endpoint_path:
            if valid_body:
                # Invalid role
                invalid_role_body = valid_body.copy()
                invalid_role_body["role"] = "InvalidRole"
                test_cases.append({
                    "name": "invalid_role",
                    "description": "Role update with invalid role value",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_role_body,
                    "expected_status": [400],
                })
        
        # Credits update endpoint error tests
        if "/users/{user_id}/credits/" in endpoint_path:
            if valid_body:
                # Negative credits
                negative_credits_body = valid_body.copy()
                negative_credits_body["credits"] = -1
                test_cases.append({
                    "name": "negative_credits",
                    "description": "Credits update with negative value",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": negative_credits_body,
                    "expected_status": [422, 400],
                })
        
        return test_cases
    
    def _generate_s3_endpoint_error_tests(
        self, endpoint_path: str, method: str
    ) -> List[Dict[str, Any]]:
        """Generate S3-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # S3 file get endpoint error tests (with file_id path parameter)
        if "/s3/files/{file_id}" in endpoint_path or "/s3/files/" in endpoint_path and "{file_id}" in endpoint_path:
            # Invalid pagination parameters
            # Limit too large (> 1000)
            test_cases.append({
                "name": "invalid_limit_too_large",
                "description": "Get S3 file with limit > 1000 (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 2000,
                    "offset": 0
                },
                "expected_status": [422],
            })
            
            # Negative offset
            test_cases.append({
                "name": "invalid_offset_negative",
                "description": "Get S3 file with negative offset (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 50,
                    "offset": -10
                },
                "expected_status": [422],
            })
            
            # Limit = 0 (below minimum)
            test_cases.append({
                "name": "invalid_limit_zero",
                "description": "Get S3 file with limit = 0 (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 0,
                    "offset": 0
                },
                "expected_status": [422],
            })
            
            # Limit without offset (should still work, offset defaults to 0)
            test_cases.append({
                "name": "limit_without_offset",
                "description": "Get S3 file with limit but no offset (offset defaults to 0)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 50
                },
                "expected_status": [200],
            })
            
            # Offset without limit (should fail - limit is required for pagination)
            test_cases.append({
                "name": "offset_without_limit",
                "description": "Get S3 file with offset but no limit (should fail or default to download mode)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "offset": 10
                },
                "expected_status": [200, 422],  # May default to download mode or fail validation
            })
        
        return test_cases
    
    def _generate_root_endpoint_error_tests(
        self, endpoint_path: str, method: str
    ) -> List[Dict[str, Any]]:
        """Generate Root-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Root endpoints are designed to be highly available and should rarely return errors
        # The only documented error is 500 Internal Server Error (server configuration issue)
        # Since these are public endpoints, we don't test authentication errors
        
        # Note: Root endpoints don't have request bodies or complex query parameters
        # Error scenarios are limited to server errors (500)
        # These are typically not testable in normal test runs, but we document them
        
        return test_cases
    
    def _generate_marketing_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate Marketing-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body for reference
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Marketing create endpoint error tests
        if endpoint_path == "/api/v4/admin/marketing/" and method == "POST":
            # Missing required hero field
            test_cases.append({
                "name": "missing_required_hero",
                "description": "Create marketing page without required hero field (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "page_id": "test-page"
                    # Missing hero
                },
                "expected_status": [400, 422],
            })
            
            # Missing required page_id
            test_cases.append({
                "name": "missing_required_page_id",
                "description": "Create marketing page without required page_id (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "hero": {
                        "title": "Test Title",
                        "description": "Test description"
                    }
                    # Missing page_id
                },
                "expected_status": [400, 422],
            })
            
            # Invalid metadata status
            if valid_body:
                invalid_status_body = valid_body.copy()
                invalid_status_body["metadata"] = {
                    "title": "Test Title",
                    "description": "Test description",
                    "status": "invalid_status"  # Invalid status
                }
                test_cases.append({
                    "name": "invalid_metadata_status",
                    "description": "Create marketing page with invalid status (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_status_body,
                    "expected_status": [400, 422],
                })
        
        # Marketing update endpoint error tests
        if endpoint_path.startswith("/api/v4/admin/marketing/") and "{page_id}" in endpoint_path and method == "PUT":
            # Empty body (partial update allows empty, but we test it)
            test_cases.append({
                "name": "empty_update_body",
                "description": "Update marketing page with empty body (partial update - should work)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {},
                "expected_status": [200, 400],  # May work or fail depending on implementation
            })
        
        return test_cases
    
    def _generate_linkedin_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate LinkedIn-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body for reference
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # LinkedIn search endpoint error tests
        if endpoint_path == "/api/v3/linkedin/" and method == "POST":
            # Missing required url field
            test_cases.append({
                "name": "missing_required_url",
                "description": "LinkedIn search without required url field (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {},
                "expected_status": [400, 422],
            })
            
            # Empty URL string
            test_cases.append({
                "name": "empty_url",
                "description": "LinkedIn search with empty URL (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "url": ""
                },
                "expected_status": [400],
            })
            
            # Invalid URL format
            test_cases.append({
                "name": "invalid_url_format",
                "description": "LinkedIn search with invalid URL format (may fail or return empty results)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "url": "not-a-linkedin-url"
                },
                "expected_status": [200, 400],  # May return empty results or error
            })
            
            # Wrong data type for URL
            test_cases.append({
                "name": "invalid_url_type",
                "description": "LinkedIn search with non-string URL (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "url": 12345
                },
                "expected_status": [400, 422],
            })
        
        return test_cases
    
    def _generate_usage_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate usage-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body (if available)
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Track usage endpoint error tests
        if endpoint_path == "/api/v1/usage/track/":
            if valid_body:
                # Invalid feature name
                invalid_feature_body = valid_body.copy()
                invalid_feature_body["feature"] = "INVALID_FEATURE"
                test_cases.append({
                    "name": "invalid_feature",
                    "description": "Track usage with invalid feature name",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_feature_body,
                    "expected_status": [400],
                })
                
                # Invalid amount (0 or negative)
                invalid_amount_body = valid_body.copy()
                invalid_amount_body["amount"] = 0
                test_cases.append({
                    "name": "invalid_amount_zero",
                    "description": "Track usage with amount = 0 (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_amount_body,
                    "expected_status": [422],
                })
                
                invalid_amount_body_negative = valid_body.copy()
                invalid_amount_body_negative["amount"] = -1
                test_cases.append({
                    "name": "invalid_amount_negative",
                    "description": "Track usage with negative amount (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_amount_body_negative,
                    "expected_status": [422],
                })
        
        # Reset usage endpoint error tests
        if endpoint_path == "/api/v2/usage/reset":
            if valid_body:
                # Invalid feature name
                invalid_feature_body = valid_body.copy()
                invalid_feature_body["feature"] = "INVALID_FEATURE"
                test_cases.append({
                    "name": "invalid_feature",
                    "description": "Reset usage with invalid feature name",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_feature_body,
                    "expected_status": [400],
                })
        
        return test_cases
    
    def _generate_scrape_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate scrape-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body (if available)
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Sales Navigator scrape endpoint error tests
        if endpoint_path == "/api/v3/sales-navigator/scrape":
            if valid_body:
                # Empty HTML
                empty_html_body = valid_body.copy()
                empty_html_body["html"] = ""
                test_cases.append({
                    "name": "empty_html",
                    "description": "Scrape with empty HTML (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_html_body,
                    "expected_status": [422, 400],
                })
                
                # Whitespace-only HTML
                whitespace_html_body = valid_body.copy()
                whitespace_html_body["html"] = "   \n\t  "
                test_cases.append({
                    "name": "whitespace_only_html",
                    "description": "Scrape with whitespace-only HTML (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": whitespace_html_body,
                    "expected_status": [422, 400],
                })
                
                # Missing HTML field
                missing_html_body = {"save": False}
                test_cases.append({
                    "name": "missing_html_field",
                    "description": "Scrape with missing HTML field (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_html_body,
                    "expected_status": [422],
                })
                
                # Invalid HTML type (not string)
                invalid_type_body = valid_body.copy()
                invalid_type_body["html"] = 12345
                test_cases.append({
                    "name": "invalid_html_type",
                    "description": "Scrape with invalid HTML type (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_type_body,
                    "expected_status": [422],
                })
        
        return test_cases
    
    def _get_expected_status_for_empty_body(self, endpoint_path: str, method: str) -> List[int]:
        """Get expected status codes for empty body requests based on endpoint behavior.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
        
        Returns:
            List of expected status codes
        """
        # Endpoints that allow empty body and return success
        allows_empty_body = {
            "POST /api/v2/ai-chats/": [201],  # Creates chat with empty body
            "POST /api/v1/auth/logout/": [200],  # Logout accepts empty body and returns 200
            "PUT /api/v1/users/profile/": [200],  # Profile update accepts empty body (all fields optional, partial update)
        }
        
        # Endpoints that return 404 for invalid IDs (before body validation)
        returns_404_for_invalid_id = {
            "PUT /api/v2/ai-chats/{chat_id}/": [404],  # Resource not found takes precedence
            "PUT /api/v4/admin/dashboard-pages/{page_id}": [404],  # Page not found
            "PUT /api/v4/admin/marketing/{page_id}": [404],  # Page not found
            "POST /api/v4/admin/marketing/{page_id}/publish": [404],  # Page not found
        }
        
        # Check exact match
        key = f"{method} {endpoint_path}"
        if key in allows_empty_body:
            return allows_empty_body[key]
        if key in returns_404_for_invalid_id:
            return returns_404_for_invalid_id[key]
        
        # Check pattern matches for endpoints with placeholders
        for pattern, statuses in returns_404_for_invalid_id.items():
            pattern_method, pattern_path = pattern.split(" ", 1)
            if method == pattern_method:
                # Check if endpoint structure matches (same number of parts)
                pattern_parts = pattern_path.split("/")
                endpoint_parts = endpoint_path.split("/")
                if len(pattern_parts) == len(endpoint_parts):
                    # Check if non-placeholder parts match
                    matches = True
                    for p, e in zip(pattern_parts, endpoint_parts):
                        if p.startswith("{") and p.endswith("}"):
                            continue  # Skip placeholder parts
                        if p != e:
                            matches = False
                            break
                    if matches:
                        return statuses
        
        # Default: expect validation error
        return [422, 400]
    
    def _generate_user_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate user-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body (if available)
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Registration endpoint error tests
        if endpoint_path in ["/api/v1/auth/register", "/api/v1/auth/register/"]:
            if valid_body:
                # Short password (< 8 chars)
                short_password_body = valid_body.copy()
                short_password_body["password"] = "short"
                test_cases.append({
                    "name": "short_password",
                    "description": "Registration with password too short (< 8 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": short_password_body,
                    "expected_status": [400],
                })
                
                # Long password (> 72 chars)
                long_password_body = valid_body.copy()
                long_password_body["password"] = "a" * 73
                test_cases.append({
                    "name": "long_password",
                    "description": "Registration with password too long (> 72 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": long_password_body,
                    "expected_status": [400],
                })
                
                # Invalid email format
                invalid_email_body = valid_body.copy()
                invalid_email_body["email"] = "not-an-email"
                test_cases.append({
                    "name": "invalid_email",
                    "description": "Registration with invalid email format",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_email_body,
                    "expected_status": [422],
                })
        
        # Login endpoint error tests
        if endpoint_path == "/api/v1/auth/login/":
            if valid_body:
                # Invalid credentials
                invalid_creds_body = valid_body.copy()
                invalid_creds_body["password"] = "wrongpassword"
                test_cases.append({
                    "name": "invalid_credentials",
                    "description": "Login with invalid credentials",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_creds_body,
                    "expected_status": [400],
                })
        
        # Profile update endpoint error tests
        if endpoint_path == "/api/v1/users/profile/":
            if valid_body:
                # Name too long (> 255 chars)
                long_name_body = valid_body.copy()
                long_name_body["name"] = "a" * 256
                test_cases.append({
                    "name": "long_name",
                    "description": "Profile update with name too long (> 255 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": long_name_body,
                    "expected_status": [400, 422],  # FastAPI returns 422 for validation errors
                })
                
                # Timezone too long (> 100 chars)
                long_timezone_body = valid_body.copy()
                long_timezone_body["timezone"] = "a" * 101
                test_cases.append({
                    "name": "long_timezone",
                    "description": "Profile update with timezone too long (> 100 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": long_timezone_body,
                    "expected_status": [400, 422],  # FastAPI returns 422 for validation errors
                })
        
        # Role update endpoint error tests
        if "/users/{user_id}/role/" in endpoint_path:
            if valid_body:
                # Invalid role
                invalid_role_body = valid_body.copy()
                invalid_role_body["role"] = "InvalidRole"
                test_cases.append({
                    "name": "invalid_role",
                    "description": "Role update with invalid role value",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_role_body,
                    "expected_status": [400],
                })
        
        # Credits update endpoint error tests
        if "/users/{user_id}/credits/" in endpoint_path:
            if valid_body:
                # Negative credits
                negative_credits_body = valid_body.copy()
                negative_credits_body["credits"] = -1
                test_cases.append({
                    "name": "negative_credits",
                    "description": "Credits update with negative value",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": negative_credits_body,
                    "expected_status": [422, 400],
                })
        
        return test_cases
    
    def _generate_s3_endpoint_error_tests(
        self, endpoint_path: str, method: str
    ) -> List[Dict[str, Any]]:
        """Generate S3-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # S3 file get endpoint error tests (with file_id path parameter)
        if "/s3/files/{file_id}" in endpoint_path or "/s3/files/" in endpoint_path and "{file_id}" in endpoint_path:
            # Invalid pagination parameters
            # Limit too large (> 1000)
            test_cases.append({
                "name": "invalid_limit_too_large",
                "description": "Get S3 file with limit > 1000 (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 2000,
                    "offset": 0
                },
                "expected_status": [422],
            })
            
            # Negative offset
            test_cases.append({
                "name": "invalid_offset_negative",
                "description": "Get S3 file with negative offset (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 50,
                    "offset": -10
                },
                "expected_status": [422],
            })
            
            # Limit = 0 (below minimum)
            test_cases.append({
                "name": "invalid_limit_zero",
                "description": "Get S3 file with limit = 0 (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 0,
                    "offset": 0
                },
                "expected_status": [422],
            })
            
            # Limit without offset (should still work, offset defaults to 0)
            test_cases.append({
                "name": "limit_without_offset",
                "description": "Get S3 file with limit but no offset (offset defaults to 0)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 50
                },
                "expected_status": [200],
            })
            
            # Offset without limit (should fail - limit is required for pagination)
            test_cases.append({
                "name": "offset_without_limit",
                "description": "Get S3 file with offset but no limit (should fail or default to download mode)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "offset": 10
                },
                "expected_status": [200, 422],  # May default to download mode or fail validation
            })
        
        return test_cases
    
    def _generate_root_endpoint_error_tests(
        self, endpoint_path: str, method: str
    ) -> List[Dict[str, Any]]:
        """Generate Root-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Root endpoints are designed to be highly available and should rarely return errors
        # The only documented error is 500 Internal Server Error (server configuration issue)
        # Since these are public endpoints, we don't test authentication errors
        
        # Note: Root endpoints don't have request bodies or complex query parameters
        # Error scenarios are limited to server errors (500)
        # These are typically not testable in normal test runs, but we document them
        
        return test_cases
    
    def _generate_marketing_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate Marketing-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body for reference
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Marketing create endpoint error tests
        if endpoint_path == "/api/v4/admin/marketing/" and method == "POST":
            # Missing required hero field
            test_cases.append({
                "name": "missing_required_hero",
                "description": "Create marketing page without required hero field (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "page_id": "test-page"
                    # Missing hero
                },
                "expected_status": [400, 422],
            })
            
            # Missing required page_id
            test_cases.append({
                "name": "missing_required_page_id",
                "description": "Create marketing page without required page_id (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "hero": {
                        "title": "Test Title",
                        "description": "Test description"
                    }
                    # Missing page_id
                },
                "expected_status": [400, 422],
            })
            
            # Invalid metadata status
            if valid_body:
                invalid_status_body = valid_body.copy()
                invalid_status_body["metadata"] = {
                    "title": "Test Title",
                    "description": "Test description",
                    "status": "invalid_status"  # Invalid status
                }
                test_cases.append({
                    "name": "invalid_metadata_status",
                    "description": "Create marketing page with invalid status (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_status_body,
                    "expected_status": [400, 422],
                })
        
        # Marketing update endpoint error tests
        if endpoint_path.startswith("/api/v4/admin/marketing/") and "{page_id}" in endpoint_path and method == "PUT":
            # Empty body (partial update allows empty, but we test it)
            test_cases.append({
                "name": "empty_update_body",
                "description": "Update marketing page with empty body (partial update - should work)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {},
                "expected_status": [200, 400],  # May work or fail depending on implementation
            })
        
        return test_cases
    
    def _generate_linkedin_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate LinkedIn-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body for reference
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # LinkedIn search endpoint error tests
        if endpoint_path == "/api/v3/linkedin/" and method == "POST":
            # Missing required url field
            test_cases.append({
                "name": "missing_required_url",
                "description": "LinkedIn search without required url field (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {},
                "expected_status": [400, 422],
            })
            
            # Empty URL string
            test_cases.append({
                "name": "empty_url",
                "description": "LinkedIn search with empty URL (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "url": ""
                },
                "expected_status": [400],
            })
            
            # Invalid URL format
            test_cases.append({
                "name": "invalid_url_format",
                "description": "LinkedIn search with invalid URL format (may fail or return empty results)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "url": "not-a-linkedin-url"
                },
                "expected_status": [200, 400],  # May return empty results or error
            })
            
            # Wrong data type for URL
            test_cases.append({
                "name": "invalid_url_type",
                "description": "LinkedIn search with non-string URL (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "url": 12345
                },
                "expected_status": [400, 422],
            })
        
        return test_cases
    
    def _generate_usage_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate usage-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body (if available)
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Track usage endpoint error tests
        if endpoint_path == "/api/v1/usage/track/":
            if valid_body:
                # Invalid feature name
                invalid_feature_body = valid_body.copy()
                invalid_feature_body["feature"] = "INVALID_FEATURE"
                test_cases.append({
                    "name": "invalid_feature",
                    "description": "Track usage with invalid feature name",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_feature_body,
                    "expected_status": [400],
                })
                
                # Invalid amount (0 or negative)
                invalid_amount_body = valid_body.copy()
                invalid_amount_body["amount"] = 0
                test_cases.append({
                    "name": "invalid_amount_zero",
                    "description": "Track usage with amount = 0 (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_amount_body,
                    "expected_status": [422],
                })
                
                invalid_amount_body_negative = valid_body.copy()
                invalid_amount_body_negative["amount"] = -1
                test_cases.append({
                    "name": "invalid_amount_negative",
                    "description": "Track usage with negative amount (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_amount_body_negative,
                    "expected_status": [422],
                })
        
        # Reset usage endpoint error tests
        if endpoint_path == "/api/v2/usage/reset":
            if valid_body:
                # Invalid feature name
                invalid_feature_body = valid_body.copy()
                invalid_feature_body["feature"] = "INVALID_FEATURE"
                test_cases.append({
                    "name": "invalid_feature",
                    "description": "Reset usage with invalid feature name",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_feature_body,
                    "expected_status": [400],
                })
        
        return test_cases
    
    def _generate_scrape_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate scrape-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body (if available)
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Sales Navigator scrape endpoint error tests
        if endpoint_path == "/api/v3/sales-navigator/scrape":
            if valid_body:
                # Empty HTML
                empty_html_body = valid_body.copy()
                empty_html_body["html"] = ""
                test_cases.append({
                    "name": "empty_html",
                    "description": "Scrape with empty HTML (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_html_body,
                    "expected_status": [422, 400],
                })
                
                # Whitespace-only HTML
                whitespace_html_body = valid_body.copy()
                whitespace_html_body["html"] = "   \n\t  "
                test_cases.append({
                    "name": "whitespace_only_html",
                    "description": "Scrape with whitespace-only HTML (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": whitespace_html_body,
                    "expected_status": [422, 400],
                })
                
                # Missing HTML field
                missing_html_body = {"save": False}
                test_cases.append({
                    "name": "missing_html_field",
                    "description": "Scrape with missing HTML field (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_html_body,
                    "expected_status": [422],
                })
                
                # Invalid HTML type (not string)
                invalid_type_body = valid_body.copy()
                invalid_type_body["html"] = 12345
                test_cases.append({
                    "name": "invalid_html_type",
                    "description": "Scrape with invalid HTML type (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_type_body,
                    "expected_status": [422],
                })
        
        return test_cases


    def _get_expected_status_for_empty_body(self, endpoint_path: str, method: str) -> List[int]:
        """Get expected status codes for empty body requests based on endpoint behavior.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
        
        Returns:
            List of expected status codes
        """
        # Endpoints that allow empty body and return success
        allows_empty_body = {
            "POST /api/v2/ai-chats/": [201],  # Creates chat with empty body
            "POST /api/v1/auth/logout/": [200],  # Logout accepts empty body and returns 200
            "PUT /api/v1/users/profile/": [200],  # Profile update accepts empty body (all fields optional, partial update)
        }
        
        # Endpoints that return 404 for invalid IDs (before body validation)
        returns_404_for_invalid_id = {
            "PUT /api/v2/ai-chats/{chat_id}/": [404],  # Resource not found takes precedence
            "PUT /api/v4/admin/dashboard-pages/{page_id}": [404],  # Page not found
            "PUT /api/v4/admin/marketing/{page_id}": [404],  # Page not found
            "POST /api/v4/admin/marketing/{page_id}/publish": [404],  # Page not found
        }
        
        # Check exact match
        key = f"{method} {endpoint_path}"
        if key in allows_empty_body:
            return allows_empty_body[key]
        if key in returns_404_for_invalid_id:
            return returns_404_for_invalid_id[key]
        
        # Check pattern matches for endpoints with placeholders
        for pattern, statuses in returns_404_for_invalid_id.items():
            pattern_method, pattern_path = pattern.split(" ", 1)
            if method == pattern_method:
                # Check if endpoint structure matches (same number of parts)
                pattern_parts = pattern_path.split("/")
                endpoint_parts = endpoint_path.split("/")
                if len(pattern_parts) == len(endpoint_parts):
                    # Check if non-placeholder parts match
                    matches = True
                    for p, e in zip(pattern_parts, endpoint_parts):
                        if p.startswith("{") and p.endswith("}"):
                            continue  # Skip placeholder parts
                        if p != e:
                            matches = False
                            break
                    if matches:
                        return statuses
        
        # Default: expect validation error
        return [422, 400]
    
    def _generate_user_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate user-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body (if available)
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Registration endpoint error tests
        if endpoint_path in ["/api/v1/auth/register", "/api/v1/auth/register/"]:
            if valid_body:
                # Short password (< 8 chars)
                short_password_body = valid_body.copy()
                short_password_body["password"] = "short"
                test_cases.append({
                    "name": "short_password",
                    "description": "Registration with password too short (< 8 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": short_password_body,
                    "expected_status": [400],
                })
                
                # Long password (> 72 chars)
                long_password_body = valid_body.copy()
                long_password_body["password"] = "a" * 73
                test_cases.append({
                    "name": "long_password",
                    "description": "Registration with password too long (> 72 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": long_password_body,
                    "expected_status": [400],
                })
                
                # Invalid email format
                invalid_email_body = valid_body.copy()
                invalid_email_body["email"] = "not-an-email"
                test_cases.append({
                    "name": "invalid_email",
                    "description": "Registration with invalid email format",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_email_body,
                    "expected_status": [422],
                })
        
        # Login endpoint error tests
        if endpoint_path == "/api/v1/auth/login/":
            if valid_body:
                # Invalid credentials
                invalid_creds_body = valid_body.copy()
                invalid_creds_body["password"] = "wrongpassword"
                test_cases.append({
                    "name": "invalid_credentials",
                    "description": "Login with invalid credentials",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_creds_body,
                    "expected_status": [400],
                })
        
        # Profile update endpoint error tests
        if endpoint_path == "/api/v1/users/profile/":
            if valid_body:
                # Name too long (> 255 chars)
                long_name_body = valid_body.copy()
                long_name_body["name"] = "a" * 256
                test_cases.append({
                    "name": "long_name",
                    "description": "Profile update with name too long (> 255 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": long_name_body,
                    "expected_status": [400, 422],  # FastAPI returns 422 for validation errors
                })
                
                # Timezone too long (> 100 chars)
                long_timezone_body = valid_body.copy()
                long_timezone_body["timezone"] = "a" * 101
                test_cases.append({
                    "name": "long_timezone",
                    "description": "Profile update with timezone too long (> 100 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": long_timezone_body,
                    "expected_status": [400, 422],  # FastAPI returns 422 for validation errors
                })
        
        # Role update endpoint error tests
        if "/users/{user_id}/role/" in endpoint_path:
            if valid_body:
                # Invalid role
                invalid_role_body = valid_body.copy()
                invalid_role_body["role"] = "InvalidRole"
                test_cases.append({
                    "name": "invalid_role",
                    "description": "Role update with invalid role value",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_role_body,
                    "expected_status": [400],
                })
        
        # Credits update endpoint error tests
        if "/users/{user_id}/credits/" in endpoint_path:
            if valid_body:
                # Negative credits
                negative_credits_body = valid_body.copy()
                negative_credits_body["credits"] = -1
                test_cases.append({
                    "name": "negative_credits",
                    "description": "Credits update with negative value",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": negative_credits_body,
                    "expected_status": [422, 400],
                })
        
        return test_cases
    
    def _generate_s3_endpoint_error_tests(
        self, endpoint_path: str, method: str
    ) -> List[Dict[str, Any]]:
        """Generate S3-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # S3 file get endpoint error tests (with file_id path parameter)
        if "/s3/files/{file_id}" in endpoint_path or "/s3/files/" in endpoint_path and "{file_id}" in endpoint_path:
            # Invalid pagination parameters
            # Limit too large (> 1000)
            test_cases.append({
                "name": "invalid_limit_too_large",
                "description": "Get S3 file with limit > 1000 (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 2000,
                    "offset": 0
                },
                "expected_status": [422],
            })
            
            # Negative offset
            test_cases.append({
                "name": "invalid_offset_negative",
                "description": "Get S3 file with negative offset (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 50,
                    "offset": -10
                },
                "expected_status": [422],
            })
            
            # Limit = 0 (below minimum)
            test_cases.append({
                "name": "invalid_limit_zero",
                "description": "Get S3 file with limit = 0 (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 0,
                    "offset": 0
                },
                "expected_status": [422],
            })
            
            # Limit without offset (should still work, offset defaults to 0)
            test_cases.append({
                "name": "limit_without_offset",
                "description": "Get S3 file with limit but no offset (offset defaults to 0)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 50
                },
                "expected_status": [200],
            })
            
            # Offset without limit (should fail - limit is required for pagination)
            test_cases.append({
                "name": "offset_without_limit",
                "description": "Get S3 file with offset but no limit (should fail or default to download mode)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "offset": 10
                },
                "expected_status": [200, 422],  # May default to download mode or fail validation
            })
        
        return test_cases
    
    def _generate_root_endpoint_error_tests(
        self, endpoint_path: str, method: str
    ) -> List[Dict[str, Any]]:
        """Generate Root-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Root endpoints are designed to be highly available and should rarely return errors
        # The only documented error is 500 Internal Server Error (server configuration issue)
        # Since these are public endpoints, we don't test authentication errors
        
        # Note: Root endpoints don't have request bodies or complex query parameters
        # Error scenarios are limited to server errors (500)
        # These are typically not testable in normal test runs, but we document them
        
        return test_cases
    
    def _generate_marketing_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate Marketing-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body for reference
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Marketing create endpoint error tests
        if endpoint_path == "/api/v4/admin/marketing/" and method == "POST":
            # Missing required hero field
            test_cases.append({
                "name": "missing_required_hero",
                "description": "Create marketing page without required hero field (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "page_id": "test-page"
                    # Missing hero
                },
                "expected_status": [400, 422],
            })
            
            # Missing required page_id
            test_cases.append({
                "name": "missing_required_page_id",
                "description": "Create marketing page without required page_id (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "hero": {
                        "title": "Test Title",
                        "description": "Test description"
                    }
                    # Missing page_id
                },
                "expected_status": [400, 422],
            })
            
            # Invalid metadata status
            if valid_body:
                invalid_status_body = valid_body.copy()
                invalid_status_body["metadata"] = {
                    "title": "Test Title",
                    "description": "Test description",
                    "status": "invalid_status"  # Invalid status
                }
                test_cases.append({
                    "name": "invalid_metadata_status",
                    "description": "Create marketing page with invalid status (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_status_body,
                    "expected_status": [400, 422],
                })
        
        # Marketing update endpoint error tests
        if endpoint_path.startswith("/api/v4/admin/marketing/") and "{page_id}" in endpoint_path and method == "PUT":
            # Empty body (partial update allows empty, but we test it)
            test_cases.append({
                "name": "empty_update_body",
                "description": "Update marketing page with empty body (partial update - should work)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {},
                "expected_status": [200, 400],  # May work or fail depending on implementation
            })
        
        return test_cases
    
    def _generate_linkedin_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate LinkedIn-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body for reference
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # LinkedIn search endpoint error tests
        if endpoint_path == "/api/v3/linkedin/" and method == "POST":
            # Missing required url field
            test_cases.append({
                "name": "missing_required_url",
                "description": "LinkedIn search without required url field (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {},
                "expected_status": [400, 422],
            })
            
            # Empty URL string
            test_cases.append({
                "name": "empty_url",
                "description": "LinkedIn search with empty URL (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "url": ""
                },
                "expected_status": [400],
            })
            
            # Invalid URL format
            test_cases.append({
                "name": "invalid_url_format",
                "description": "LinkedIn search with invalid URL format (may fail or return empty results)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "url": "not-a-linkedin-url"
                },
                "expected_status": [200, 400],  # May return empty results or error
            })
            
            # Wrong data type for URL
            test_cases.append({
                "name": "invalid_url_type",
                "description": "LinkedIn search with non-string URL (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "url": 12345
                },
                "expected_status": [400, 422],
            })
        
        return test_cases
    
    def _generate_usage_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate usage-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body (if available)
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Track usage endpoint error tests
        if endpoint_path == "/api/v1/usage/track/":
            if valid_body:
                # Invalid feature name
                invalid_feature_body = valid_body.copy()
                invalid_feature_body["feature"] = "INVALID_FEATURE"
                test_cases.append({
                    "name": "invalid_feature",
                    "description": "Track usage with invalid feature name",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_feature_body,
                    "expected_status": [400],
                })
                
                # Invalid amount (0 or negative)
                invalid_amount_body = valid_body.copy()
                invalid_amount_body["amount"] = 0
                test_cases.append({
                    "name": "invalid_amount_zero",
                    "description": "Track usage with amount = 0 (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_amount_body,
                    "expected_status": [422],
                })
                
                invalid_amount_body_negative = valid_body.copy()
                invalid_amount_body_negative["amount"] = -1
                test_cases.append({
                    "name": "invalid_amount_negative",
                    "description": "Track usage with negative amount (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_amount_body_negative,
                    "expected_status": [422],
                })
        
        # Reset usage endpoint error tests
        if endpoint_path == "/api/v2/usage/reset":
            if valid_body:
                # Invalid feature name
                invalid_feature_body = valid_body.copy()
                invalid_feature_body["feature"] = "INVALID_FEATURE"
                test_cases.append({
                    "name": "invalid_feature",
                    "description": "Reset usage with invalid feature name",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_feature_body,
                    "expected_status": [400],
                })
        
        return test_cases
    
    def _generate_scrape_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate scrape-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body (if available)
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Sales Navigator scrape endpoint error tests
        if endpoint_path == "/api/v3/sales-navigator/scrape":
            if valid_body:
                # Empty HTML
                empty_html_body = valid_body.copy()
                empty_html_body["html"] = ""
                test_cases.append({
                    "name": "empty_html",
                    "description": "Scrape with empty HTML (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_html_body,
                    "expected_status": [422, 400],
                })
                
                # Whitespace-only HTML
                whitespace_html_body = valid_body.copy()
                whitespace_html_body["html"] = "   \n\t  "
                test_cases.append({
                    "name": "whitespace_only_html",
                    "description": "Scrape with whitespace-only HTML (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": whitespace_html_body,
                    "expected_status": [422, 400],
                })
                
                # Missing HTML field
                missing_html_body = {"save": False}
                test_cases.append({
                    "name": "missing_html_field",
                    "description": "Scrape with missing HTML field (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_html_body,
                    "expected_status": [422],
                })
                
                # Invalid HTML type (not string)
                invalid_type_body = valid_body.copy()
                invalid_type_body["html"] = 12345
                test_cases.append({
                    "name": "invalid_html_type",
                    "description": "Scrape with invalid HTML type (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_type_body,
                    "expected_status": [422],
                })
        
        return test_cases


    def _get_expected_status_for_empty_body(self, endpoint_path: str, method: str) -> List[int]:
        """Get expected status codes for empty body requests based on endpoint behavior.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
        
        Returns:
            List of expected status codes
        """
        # Endpoints that allow empty body and return success
        allows_empty_body = {
            "POST /api/v2/ai-chats/": [201],  # Creates chat with empty body
            "POST /api/v1/auth/logout/": [200],  # Logout accepts empty body and returns 200
            "PUT /api/v1/users/profile/": [200],  # Profile update accepts empty body (all fields optional, partial update)
        }
        
        # Endpoints that return 404 for invalid IDs (before body validation)
        returns_404_for_invalid_id = {
            "PUT /api/v2/ai-chats/{chat_id}/": [404],  # Resource not found takes precedence
            "PUT /api/v4/admin/dashboard-pages/{page_id}": [404],  # Page not found
            "PUT /api/v4/admin/marketing/{page_id}": [404],  # Page not found
            "POST /api/v4/admin/marketing/{page_id}/publish": [404],  # Page not found
        }
        
        # Check exact match
        key = f"{method} {endpoint_path}"
        if key in allows_empty_body:
            return allows_empty_body[key]
        if key in returns_404_for_invalid_id:
            return returns_404_for_invalid_id[key]
        
        # Check pattern matches for endpoints with placeholders
        for pattern, statuses in returns_404_for_invalid_id.items():
            pattern_method, pattern_path = pattern.split(" ", 1)
            if method == pattern_method:
                # Check if endpoint structure matches (same number of parts)
                pattern_parts = pattern_path.split("/")
                endpoint_parts = endpoint_path.split("/")
                if len(pattern_parts) == len(endpoint_parts):
                    # Check if non-placeholder parts match
                    matches = True
                    for p, e in zip(pattern_parts, endpoint_parts):
                        if p.startswith("{") and p.endswith("}"):
                            continue  # Skip placeholder parts
                        if p != e:
                            matches = False
                            break
                    if matches:
                        return statuses
        
        # Default: expect validation error
        return [422, 400]
    
    def _generate_user_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate user-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body (if available)
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Registration endpoint error tests
        if endpoint_path in ["/api/v1/auth/register", "/api/v1/auth/register/"]:
            if valid_body:
                # Short password (< 8 chars)
                short_password_body = valid_body.copy()
                short_password_body["password"] = "short"
                test_cases.append({
                    "name": "short_password",
                    "description": "Registration with password too short (< 8 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": short_password_body,
                    "expected_status": [400],
                })
                
                # Long password (> 72 chars)
                long_password_body = valid_body.copy()
                long_password_body["password"] = "a" * 73
                test_cases.append({
                    "name": "long_password",
                    "description": "Registration with password too long (> 72 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": long_password_body,
                    "expected_status": [400],
                })
                
                # Invalid email format
                invalid_email_body = valid_body.copy()
                invalid_email_body["email"] = "not-an-email"
                test_cases.append({
                    "name": "invalid_email",
                    "description": "Registration with invalid email format",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_email_body,
                    "expected_status": [422],
                })
        
        # Login endpoint error tests
        if endpoint_path == "/api/v1/auth/login/":
            if valid_body:
                # Invalid credentials
                invalid_creds_body = valid_body.copy()
                invalid_creds_body["password"] = "wrongpassword"
                test_cases.append({
                    "name": "invalid_credentials",
                    "description": "Login with invalid credentials",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_creds_body,
                    "expected_status": [400],
                })
        
        # Profile update endpoint error tests
        if endpoint_path == "/api/v1/users/profile/":
            if valid_body:
                # Name too long (> 255 chars)
                long_name_body = valid_body.copy()
                long_name_body["name"] = "a" * 256
                test_cases.append({
                    "name": "long_name",
                    "description": "Profile update with name too long (> 255 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": long_name_body,
                    "expected_status": [400, 422],  # FastAPI returns 422 for validation errors
                })
                
                # Timezone too long (> 100 chars)
                long_timezone_body = valid_body.copy()
                long_timezone_body["timezone"] = "a" * 101
                test_cases.append({
                    "name": "long_timezone",
                    "description": "Profile update with timezone too long (> 100 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": long_timezone_body,
                    "expected_status": [400, 422],  # FastAPI returns 422 for validation errors
                })
        
        # Role update endpoint error tests
        if "/users/{user_id}/role/" in endpoint_path:
            if valid_body:
                # Invalid role
                invalid_role_body = valid_body.copy()
                invalid_role_body["role"] = "InvalidRole"
                test_cases.append({
                    "name": "invalid_role",
                    "description": "Role update with invalid role value",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_role_body,
                    "expected_status": [400],
                })
        
        # Credits update endpoint error tests
        if "/users/{user_id}/credits/" in endpoint_path:
            if valid_body:
                # Negative credits
                negative_credits_body = valid_body.copy()
                negative_credits_body["credits"] = -1
                test_cases.append({
                    "name": "negative_credits",
                    "description": "Credits update with negative value",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": negative_credits_body,
                    "expected_status": [422, 400],
                })
        
        return test_cases
    
    def _generate_s3_endpoint_error_tests(
        self, endpoint_path: str, method: str
    ) -> List[Dict[str, Any]]:
        """Generate S3-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # S3 file get endpoint error tests (with file_id path parameter)
        if "/s3/files/{file_id}" in endpoint_path or "/s3/files/" in endpoint_path and "{file_id}" in endpoint_path:
            # Invalid pagination parameters
            # Limit too large (> 1000)
            test_cases.append({
                "name": "invalid_limit_too_large",
                "description": "Get S3 file with limit > 1000 (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 2000,
                    "offset": 0
                },
                "expected_status": [422],
            })
            
            # Negative offset
            test_cases.append({
                "name": "invalid_offset_negative",
                "description": "Get S3 file with negative offset (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 50,
                    "offset": -10
                },
                "expected_status": [422],
            })
            
            # Limit = 0 (below minimum)
            test_cases.append({
                "name": "invalid_limit_zero",
                "description": "Get S3 file with limit = 0 (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 0,
                    "offset": 0
                },
                "expected_status": [422],
            })
            
            # Limit without offset (should still work, offset defaults to 0)
            test_cases.append({
                "name": "limit_without_offset",
                "description": "Get S3 file with limit but no offset (offset defaults to 0)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 50
                },
                "expected_status": [200],
            })
            
            # Offset without limit (should fail - limit is required for pagination)
            test_cases.append({
                "name": "offset_without_limit",
                "description": "Get S3 file with offset but no limit (should fail or default to download mode)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "offset": 10
                },
                "expected_status": [200, 422],  # May default to download mode or fail validation
            })
        
        return test_cases
    
    def _generate_root_endpoint_error_tests(
        self, endpoint_path: str, method: str
    ) -> List[Dict[str, Any]]:
        """Generate Root-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Root endpoints are designed to be highly available and should rarely return errors
        # The only documented error is 500 Internal Server Error (server configuration issue)
        # Since these are public endpoints, we don't test authentication errors
        
        # Note: Root endpoints don't have request bodies or complex query parameters
        # Error scenarios are limited to server errors (500)
        # These are typically not testable in normal test runs, but we document them
        
        return test_cases
    
    def _generate_marketing_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate Marketing-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body for reference
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Marketing create endpoint error tests
        if endpoint_path == "/api/v4/admin/marketing/" and method == "POST":
            # Missing required hero field
            test_cases.append({
                "name": "missing_required_hero",
                "description": "Create marketing page without required hero field (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "page_id": "test-page"
                    # Missing hero
                },
                "expected_status": [400, 422],
            })
            
            # Missing required page_id
            test_cases.append({
                "name": "missing_required_page_id",
                "description": "Create marketing page without required page_id (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "hero": {
                        "title": "Test Title",
                        "description": "Test description"
                    }
                    # Missing page_id
                },
                "expected_status": [400, 422],
            })
            
            # Invalid metadata status
            if valid_body:
                invalid_status_body = valid_body.copy()
                invalid_status_body["metadata"] = {
                    "title": "Test Title",
                    "description": "Test description",
                    "status": "invalid_status"  # Invalid status
                }
                test_cases.append({
                    "name": "invalid_metadata_status",
                    "description": "Create marketing page with invalid status (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_status_body,
                    "expected_status": [400, 422],
                })
        
        # Marketing update endpoint error tests
        if endpoint_path.startswith("/api/v4/admin/marketing/") and "{page_id}" in endpoint_path and method == "PUT":
            # Empty body (partial update allows empty, but we test it)
            test_cases.append({
                "name": "empty_update_body",
                "description": "Update marketing page with empty body (partial update - should work)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {},
                "expected_status": [200, 400],  # May work or fail depending on implementation
            })
        
        return test_cases
    
    def _generate_linkedin_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate LinkedIn-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body for reference
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # LinkedIn search endpoint error tests
        if endpoint_path == "/api/v3/linkedin/" and method == "POST":
            # Missing required url field
            test_cases.append({
                "name": "missing_required_url",
                "description": "LinkedIn search without required url field (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {},
                "expected_status": [400, 422],
            })
            
            # Empty URL string
            test_cases.append({
                "name": "empty_url",
                "description": "LinkedIn search with empty URL (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "url": ""
                },
                "expected_status": [400],
            })
            
            # Invalid URL format
            test_cases.append({
                "name": "invalid_url_format",
                "description": "LinkedIn search with invalid URL format (may fail or return empty results)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "url": "not-a-linkedin-url"
                },
                "expected_status": [200, 400],  # May return empty results or error
            })
            
            # Wrong data type for URL
            test_cases.append({
                "name": "invalid_url_type",
                "description": "LinkedIn search with non-string URL (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "url": 12345
                },
                "expected_status": [400, 422],
            })
        
        return test_cases
    
    def _generate_usage_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate usage-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body (if available)
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Track usage endpoint error tests
        if endpoint_path == "/api/v1/usage/track/":
            if valid_body:
                # Invalid feature name
                invalid_feature_body = valid_body.copy()
                invalid_feature_body["feature"] = "INVALID_FEATURE"
                test_cases.append({
                    "name": "invalid_feature",
                    "description": "Track usage with invalid feature name",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_feature_body,
                    "expected_status": [400],
                })
                
                # Invalid amount (0 or negative)
                invalid_amount_body = valid_body.copy()
                invalid_amount_body["amount"] = 0
                test_cases.append({
                    "name": "invalid_amount_zero",
                    "description": "Track usage with amount = 0 (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_amount_body,
                    "expected_status": [422],
                })
                
                invalid_amount_body_negative = valid_body.copy()
                invalid_amount_body_negative["amount"] = -1
                test_cases.append({
                    "name": "invalid_amount_negative",
                    "description": "Track usage with negative amount (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_amount_body_negative,
                    "expected_status": [422],
                })
        
        # Reset usage endpoint error tests
        if endpoint_path == "/api/v2/usage/reset":
            if valid_body:
                # Invalid feature name
                invalid_feature_body = valid_body.copy()
                invalid_feature_body["feature"] = "INVALID_FEATURE"
                test_cases.append({
                    "name": "invalid_feature",
                    "description": "Reset usage with invalid feature name",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_feature_body,
                    "expected_status": [400],
                })
        
        return test_cases
    
    def _generate_scrape_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate scrape-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body (if available)
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Sales Navigator scrape endpoint error tests
        if endpoint_path == "/api/v3/sales-navigator/scrape":
            if valid_body:
                # Empty HTML
                empty_html_body = valid_body.copy()
                empty_html_body["html"] = ""
                test_cases.append({
                    "name": "empty_html",
                    "description": "Scrape with empty HTML (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_html_body,
                    "expected_status": [422, 400],
                })
                
                # Whitespace-only HTML
                whitespace_html_body = valid_body.copy()
                whitespace_html_body["html"] = "   \n\t  "
                test_cases.append({
                    "name": "whitespace_only_html",
                    "description": "Scrape with whitespace-only HTML (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": whitespace_html_body,
                    "expected_status": [422, 400],
                })
                
                # Missing HTML field
                missing_html_body = {"save": False}
                test_cases.append({
                    "name": "missing_html_field",
                    "description": "Scrape with missing HTML field (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_html_body,
                    "expected_status": [422],
                })
                
                # Invalid HTML type (not string)
                invalid_type_body = valid_body.copy()
                invalid_type_body["html"] = 12345
                test_cases.append({
                    "name": "invalid_html_type",
                    "description": "Scrape with invalid HTML type (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_type_body,
                    "expected_status": [422],
                })
        
        return test_cases


    def _get_expected_status_for_empty_body(self, endpoint_path: str, method: str) -> List[int]:
        """Get expected status codes for empty body requests based on endpoint behavior.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
        
        Returns:
            List of expected status codes
        """
        # Endpoints that allow empty body and return success
        allows_empty_body = {
            "POST /api/v2/ai-chats/": [201],  # Creates chat with empty body
            "POST /api/v1/auth/logout/": [200],  # Logout accepts empty body and returns 200
            "PUT /api/v1/users/profile/": [200],  # Profile update accepts empty body (all fields optional, partial update)
        }
        
        # Endpoints that return 404 for invalid IDs (before body validation)
        returns_404_for_invalid_id = {
            "PUT /api/v2/ai-chats/{chat_id}/": [404],  # Resource not found takes precedence
            "PUT /api/v4/admin/dashboard-pages/{page_id}": [404],  # Page not found
            "PUT /api/v4/admin/marketing/{page_id}": [404],  # Page not found
            "POST /api/v4/admin/marketing/{page_id}/publish": [404],  # Page not found
        }
        
        # Check exact match
        key = f"{method} {endpoint_path}"
        if key in allows_empty_body:
            return allows_empty_body[key]
        if key in returns_404_for_invalid_id:
            return returns_404_for_invalid_id[key]
        
        # Check pattern matches for endpoints with placeholders
        for pattern, statuses in returns_404_for_invalid_id.items():
            pattern_method, pattern_path = pattern.split(" ", 1)
            if method == pattern_method:
                # Check if endpoint structure matches (same number of parts)
                pattern_parts = pattern_path.split("/")
                endpoint_parts = endpoint_path.split("/")
                if len(pattern_parts) == len(endpoint_parts):
                    # Check if non-placeholder parts match
                    matches = True
                    for p, e in zip(pattern_parts, endpoint_parts):
                        if p.startswith("{") and p.endswith("}"):
                            continue  # Skip placeholder parts
                        if p != e:
                            matches = False
                            break
                    if matches:
                        return statuses
        
        # Default: expect validation error
        return [422, 400]
    
    def _generate_user_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate user-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body (if available)
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Registration endpoint error tests
        if endpoint_path in ["/api/v1/auth/register", "/api/v1/auth/register/"]:
            if valid_body:
                # Short password (< 8 chars)
                short_password_body = valid_body.copy()
                short_password_body["password"] = "short"
                test_cases.append({
                    "name": "short_password",
                    "description": "Registration with password too short (< 8 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": short_password_body,
                    "expected_status": [400],
                })
                
                # Long password (> 72 chars)
                long_password_body = valid_body.copy()
                long_password_body["password"] = "a" * 73
                test_cases.append({
                    "name": "long_password",
                    "description": "Registration with password too long (> 72 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": long_password_body,
                    "expected_status": [400],
                })
                
                # Invalid email format
                invalid_email_body = valid_body.copy()
                invalid_email_body["email"] = "not-an-email"
                test_cases.append({
                    "name": "invalid_email",
                    "description": "Registration with invalid email format",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_email_body,
                    "expected_status": [422],
                })
        
        # Login endpoint error tests
        if endpoint_path == "/api/v1/auth/login/":
            if valid_body:
                # Invalid credentials
                invalid_creds_body = valid_body.copy()
                invalid_creds_body["password"] = "wrongpassword"
                test_cases.append({
                    "name": "invalid_credentials",
                    "description": "Login with invalid credentials",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_creds_body,
                    "expected_status": [400],
                })
        
        # Profile update endpoint error tests
        if endpoint_path == "/api/v1/users/profile/":
            if valid_body:
                # Name too long (> 255 chars)
                long_name_body = valid_body.copy()
                long_name_body["name"] = "a" * 256
                test_cases.append({
                    "name": "long_name",
                    "description": "Profile update with name too long (> 255 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": long_name_body,
                    "expected_status": [400, 422],  # FastAPI returns 422 for validation errors
                })
                
                # Timezone too long (> 100 chars)
                long_timezone_body = valid_body.copy()
                long_timezone_body["timezone"] = "a" * 101
                test_cases.append({
                    "name": "long_timezone",
                    "description": "Profile update with timezone too long (> 100 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": long_timezone_body,
                    "expected_status": [400, 422],  # FastAPI returns 422 for validation errors
                })
        
        # Role update endpoint error tests
        if "/users/{user_id}/role/" in endpoint_path:
            if valid_body:
                # Invalid role
                invalid_role_body = valid_body.copy()
                invalid_role_body["role"] = "InvalidRole"
                test_cases.append({
                    "name": "invalid_role",
                    "description": "Role update with invalid role value",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_role_body,
                    "expected_status": [400],
                })
        
        # Credits update endpoint error tests
        if "/users/{user_id}/credits/" in endpoint_path:
            if valid_body:
                # Negative credits
                negative_credits_body = valid_body.copy()
                negative_credits_body["credits"] = -1
                test_cases.append({
                    "name": "negative_credits",
                    "description": "Credits update with negative value",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": negative_credits_body,
                    "expected_status": [422, 400],
                })
        
        return test_cases
    
    def _generate_s3_endpoint_error_tests(
        self, endpoint_path: str, method: str
    ) -> List[Dict[str, Any]]:
        """Generate S3-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # S3 file get endpoint error tests (with file_id path parameter)
        if "/s3/files/{file_id}" in endpoint_path or "/s3/files/" in endpoint_path and "{file_id}" in endpoint_path:
            # Invalid pagination parameters
            # Limit too large (> 1000)
            test_cases.append({
                "name": "invalid_limit_too_large",
                "description": "Get S3 file with limit > 1000 (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 2000,
                    "offset": 0
                },
                "expected_status": [422],
            })
            
            # Negative offset
            test_cases.append({
                "name": "invalid_offset_negative",
                "description": "Get S3 file with negative offset (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 50,
                    "offset": -10
                },
                "expected_status": [422],
            })
            
            # Limit = 0 (below minimum)
            test_cases.append({
                "name": "invalid_limit_zero",
                "description": "Get S3 file with limit = 0 (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 0,
                    "offset": 0
                },
                "expected_status": [422],
            })
            
            # Limit without offset (should still work, offset defaults to 0)
            test_cases.append({
                "name": "limit_without_offset",
                "description": "Get S3 file with limit but no offset (offset defaults to 0)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 50
                },
                "expected_status": [200],
            })
            
            # Offset without limit (should fail - limit is required for pagination)
            test_cases.append({
                "name": "offset_without_limit",
                "description": "Get S3 file with offset but no limit (should fail or default to download mode)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "offset": 10
                },
                "expected_status": [200, 422],  # May default to download mode or fail validation
            })
        
        return test_cases
    
    def _generate_root_endpoint_error_tests(
        self, endpoint_path: str, method: str
    ) -> List[Dict[str, Any]]:
        """Generate Root-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Root endpoints are designed to be highly available and should rarely return errors
        # The only documented error is 500 Internal Server Error (server configuration issue)
        # Since these are public endpoints, we don't test authentication errors
        
        # Note: Root endpoints don't have request bodies or complex query parameters
        # Error scenarios are limited to server errors (500)
        # These are typically not testable in normal test runs, but we document them
        
        return test_cases
    
    def _generate_marketing_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate Marketing-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body for reference
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Marketing create endpoint error tests
        if endpoint_path == "/api/v4/admin/marketing/" and method == "POST":
            # Missing required hero field
            test_cases.append({
                "name": "missing_required_hero",
                "description": "Create marketing page without required hero field (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "page_id": "test-page"
                    # Missing hero
                },
                "expected_status": [400, 422],
            })
            
            # Missing required page_id
            test_cases.append({
                "name": "missing_required_page_id",
                "description": "Create marketing page without required page_id (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "hero": {
                        "title": "Test Title",
                        "description": "Test description"
                    }
                    # Missing page_id
                },
                "expected_status": [400, 422],
            })
            
            # Invalid metadata status
            if valid_body:
                invalid_status_body = valid_body.copy()
                invalid_status_body["metadata"] = {
                    "title": "Test Title",
                    "description": "Test description",
                    "status": "invalid_status"  # Invalid status
                }
                test_cases.append({
                    "name": "invalid_metadata_status",
                    "description": "Create marketing page with invalid status (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_status_body,
                    "expected_status": [400, 422],
                })
        
        # Marketing update endpoint error tests
        if endpoint_path.startswith("/api/v4/admin/marketing/") and "{page_id}" in endpoint_path and method == "PUT":
            # Empty body (partial update allows empty, but we test it)
            test_cases.append({
                "name": "empty_update_body",
                "description": "Update marketing page with empty body (partial update - should work)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {},
                "expected_status": [200, 400],  # May work or fail depending on implementation
            })
        
        return test_cases
    
    def _generate_linkedin_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate LinkedIn-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body for reference
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # LinkedIn search endpoint error tests
        if endpoint_path == "/api/v3/linkedin/" and method == "POST":
            # Missing required url field
            test_cases.append({
                "name": "missing_required_url",
                "description": "LinkedIn search without required url field (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {},
                "expected_status": [400, 422],
            })
            
            # Empty URL string
            test_cases.append({
                "name": "empty_url",
                "description": "LinkedIn search with empty URL (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "url": ""
                },
                "expected_status": [400],
            })
            
            # Invalid URL format
            test_cases.append({
                "name": "invalid_url_format",
                "description": "LinkedIn search with invalid URL format (may fail or return empty results)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "url": "not-a-linkedin-url"
                },
                "expected_status": [200, 400],  # May return empty results or error
            })
            
            # Wrong data type for URL
            test_cases.append({
                "name": "invalid_url_type",
                "description": "LinkedIn search with non-string URL (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "url": 12345
                },
                "expected_status": [400, 422],
            })
        
        return test_cases
    
    def _generate_usage_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate usage-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body (if available)
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Track usage endpoint error tests
        if endpoint_path == "/api/v1/usage/track/":
            if valid_body:
                # Invalid feature name
                invalid_feature_body = valid_body.copy()
                invalid_feature_body["feature"] = "INVALID_FEATURE"
                test_cases.append({
                    "name": "invalid_feature",
                    "description": "Track usage with invalid feature name",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_feature_body,
                    "expected_status": [400],
                })
                
                # Invalid amount (0 or negative)
                invalid_amount_body = valid_body.copy()
                invalid_amount_body["amount"] = 0
                test_cases.append({
                    "name": "invalid_amount_zero",
                    "description": "Track usage with amount = 0 (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_amount_body,
                    "expected_status": [422],
                })
                
                invalid_amount_body_negative = valid_body.copy()
                invalid_amount_body_negative["amount"] = -1
                test_cases.append({
                    "name": "invalid_amount_negative",
                    "description": "Track usage with negative amount (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_amount_body_negative,
                    "expected_status": [422],
                })
        
        # Reset usage endpoint error tests
        if endpoint_path == "/api/v2/usage/reset":
            if valid_body:
                # Invalid feature name
                invalid_feature_body = valid_body.copy()
                invalid_feature_body["feature"] = "INVALID_FEATURE"
                test_cases.append({
                    "name": "invalid_feature",
                    "description": "Reset usage with invalid feature name",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_feature_body,
                    "expected_status": [400],
                })
        
        return test_cases
    
    def _generate_scrape_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate scrape-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body (if available)
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Sales Navigator scrape endpoint error tests
        if endpoint_path == "/api/v3/sales-navigator/scrape":
            if valid_body:
                # Empty HTML
                empty_html_body = valid_body.copy()
                empty_html_body["html"] = ""
                test_cases.append({
                    "name": "empty_html",
                    "description": "Scrape with empty HTML (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_html_body,
                    "expected_status": [422, 400],
                })
                
                # Whitespace-only HTML
                whitespace_html_body = valid_body.copy()
                whitespace_html_body["html"] = "   \n\t  "
                test_cases.append({
                    "name": "whitespace_only_html",
                    "description": "Scrape with whitespace-only HTML (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": whitespace_html_body,
                    "expected_status": [422, 400],
                })
                
                # Missing HTML field
                missing_html_body = {"save": False}
                test_cases.append({
                    "name": "missing_html_field",
                    "description": "Scrape with missing HTML field (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_html_body,
                    "expected_status": [422],
                })
                
                # Invalid HTML type (not string)
                invalid_type_body = valid_body.copy()
                invalid_type_body["html"] = 12345
                test_cases.append({
                    "name": "invalid_html_type",
                    "description": "Scrape with invalid HTML type (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_type_body,
                    "expected_status": [422],
                })
        
        return test_cases


    def _get_expected_status_for_empty_body(self, endpoint_path: str, method: str) -> List[int]:
        """Get expected status codes for empty body requests based on endpoint behavior.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
        
        Returns:
            List of expected status codes
        """
        # Endpoints that allow empty body and return success
        allows_empty_body = {
            "POST /api/v2/ai-chats/": [201],  # Creates chat with empty body
            "POST /api/v1/auth/logout/": [200],  # Logout accepts empty body and returns 200
            "PUT /api/v1/users/profile/": [200],  # Profile update accepts empty body (all fields optional, partial update)
        }
        
        # Endpoints that return 404 for invalid IDs (before body validation)
        returns_404_for_invalid_id = {
            "PUT /api/v2/ai-chats/{chat_id}/": [404],  # Resource not found takes precedence
            "PUT /api/v4/admin/dashboard-pages/{page_id}": [404],  # Page not found
            "PUT /api/v4/admin/marketing/{page_id}": [404],  # Page not found
            "POST /api/v4/admin/marketing/{page_id}/publish": [404],  # Page not found
        }
        
        # Check exact match
        key = f"{method} {endpoint_path}"
        if key in allows_empty_body:
            return allows_empty_body[key]
        if key in returns_404_for_invalid_id:
            return returns_404_for_invalid_id[key]
        
        # Check pattern matches for endpoints with placeholders
        for pattern, statuses in returns_404_for_invalid_id.items():
            pattern_method, pattern_path = pattern.split(" ", 1)
            if method == pattern_method:
                # Check if endpoint structure matches (same number of parts)
                pattern_parts = pattern_path.split("/")
                endpoint_parts = endpoint_path.split("/")
                if len(pattern_parts) == len(endpoint_parts):
                    # Check if non-placeholder parts match
                    matches = True
                    for p, e in zip(pattern_parts, endpoint_parts):
                        if p.startswith("{") and p.endswith("}"):
                            continue  # Skip placeholder parts
                        if p != e:
                            matches = False
                            break
                    if matches:
                        return statuses
        
        # Default: expect validation error
        return [422, 400]
    
    def _generate_user_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate user-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body (if available)
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Registration endpoint error tests
        if endpoint_path in ["/api/v1/auth/register", "/api/v1/auth/register/"]:
            if valid_body:
                # Short password (< 8 chars)
                short_password_body = valid_body.copy()
                short_password_body["password"] = "short"
                test_cases.append({
                    "name": "short_password",
                    "description": "Registration with password too short (< 8 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": short_password_body,
                    "expected_status": [400],
                })
                
                # Long password (> 72 chars)
                long_password_body = valid_body.copy()
                long_password_body["password"] = "a" * 73
                test_cases.append({
                    "name": "long_password",
                    "description": "Registration with password too long (> 72 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": long_password_body,
                    "expected_status": [400],
                })
                
                # Invalid email format
                invalid_email_body = valid_body.copy()
                invalid_email_body["email"] = "not-an-email"
                test_cases.append({
                    "name": "invalid_email",
                    "description": "Registration with invalid email format",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_email_body,
                    "expected_status": [422],
                })
        
        # Login endpoint error tests
        if endpoint_path == "/api/v1/auth/login/":
            if valid_body:
                # Invalid credentials
                invalid_creds_body = valid_body.copy()
                invalid_creds_body["password"] = "wrongpassword"
                test_cases.append({
                    "name": "invalid_credentials",
                    "description": "Login with invalid credentials",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_creds_body,
                    "expected_status": [400],
                })
        
        # Profile update endpoint error tests
        if endpoint_path == "/api/v1/users/profile/":
            if valid_body:
                # Name too long (> 255 chars)
                long_name_body = valid_body.copy()
                long_name_body["name"] = "a" * 256
                test_cases.append({
                    "name": "long_name",
                    "description": "Profile update with name too long (> 255 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": long_name_body,
                    "expected_status": [400, 422],  # FastAPI returns 422 for validation errors
                })
                
                # Timezone too long (> 100 chars)
                long_timezone_body = valid_body.copy()
                long_timezone_body["timezone"] = "a" * 101
                test_cases.append({
                    "name": "long_timezone",
                    "description": "Profile update with timezone too long (> 100 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": long_timezone_body,
                    "expected_status": [400, 422],  # FastAPI returns 422 for validation errors
                })
        
        # Role update endpoint error tests
        if "/users/{user_id}/role/" in endpoint_path:
            if valid_body:
                # Invalid role
                invalid_role_body = valid_body.copy()
                invalid_role_body["role"] = "InvalidRole"
                test_cases.append({
                    "name": "invalid_role",
                    "description": "Role update with invalid role value",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_role_body,
                    "expected_status": [400],
                })
        
        # Credits update endpoint error tests
        if "/users/{user_id}/credits/" in endpoint_path:
            if valid_body:
                # Negative credits
                negative_credits_body = valid_body.copy()
                negative_credits_body["credits"] = -1
                test_cases.append({
                    "name": "negative_credits",
                    "description": "Credits update with negative value",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": negative_credits_body,
                    "expected_status": [422, 400],
                })
        
        return test_cases
    
    def _generate_s3_endpoint_error_tests(
        self, endpoint_path: str, method: str
    ) -> List[Dict[str, Any]]:
        """Generate S3-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # S3 file get endpoint error tests (with file_id path parameter)
        if "/s3/files/{file_id}" in endpoint_path or "/s3/files/" in endpoint_path and "{file_id}" in endpoint_path:
            # Invalid pagination parameters
            # Limit too large (> 1000)
            test_cases.append({
                "name": "invalid_limit_too_large",
                "description": "Get S3 file with limit > 1000 (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 2000,
                    "offset": 0
                },
                "expected_status": [422],
            })
            
            # Negative offset
            test_cases.append({
                "name": "invalid_offset_negative",
                "description": "Get S3 file with negative offset (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 50,
                    "offset": -10
                },
                "expected_status": [422],
            })
            
            # Limit = 0 (below minimum)
            test_cases.append({
                "name": "invalid_limit_zero",
                "description": "Get S3 file with limit = 0 (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 0,
                    "offset": 0
                },
                "expected_status": [422],
            })
            
            # Limit without offset (should still work, offset defaults to 0)
            test_cases.append({
                "name": "limit_without_offset",
                "description": "Get S3 file with limit but no offset (offset defaults to 0)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 50
                },
                "expected_status": [200],
            })
            
            # Offset without limit (should fail - limit is required for pagination)
            test_cases.append({
                "name": "offset_without_limit",
                "description": "Get S3 file with offset but no limit (should fail or default to download mode)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "offset": 10
                },
                "expected_status": [200, 422],  # May default to download mode or fail validation
            })
        
        return test_cases
    
    def _generate_root_endpoint_error_tests(
        self, endpoint_path: str, method: str
    ) -> List[Dict[str, Any]]:
        """Generate Root-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Root endpoints are designed to be highly available and should rarely return errors
        # The only documented error is 500 Internal Server Error (server configuration issue)
        # Since these are public endpoints, we don't test authentication errors
        
        # Note: Root endpoints don't have request bodies or complex query parameters
        # Error scenarios are limited to server errors (500)
        # These are typically not testable in normal test runs, but we document them
        
        return test_cases
    
    def _generate_marketing_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate Marketing-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body for reference
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Marketing create endpoint error tests
        if endpoint_path == "/api/v4/admin/marketing/" and method == "POST":
            # Missing required hero field
            test_cases.append({
                "name": "missing_required_hero",
                "description": "Create marketing page without required hero field (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "page_id": "test-page"
                    # Missing hero
                },
                "expected_status": [400, 422],
            })
            
            # Missing required page_id
            test_cases.append({
                "name": "missing_required_page_id",
                "description": "Create marketing page without required page_id (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "hero": {
                        "title": "Test Title",
                        "description": "Test description"
                    }
                    # Missing page_id
                },
                "expected_status": [400, 422],
            })
            
            # Invalid metadata status
            if valid_body:
                invalid_status_body = valid_body.copy()
                invalid_status_body["metadata"] = {
                    "title": "Test Title",
                    "description": "Test description",
                    "status": "invalid_status"  # Invalid status
                }
                test_cases.append({
                    "name": "invalid_metadata_status",
                    "description": "Create marketing page with invalid status (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_status_body,
                    "expected_status": [400, 422],
                })
        
        # Marketing update endpoint error tests
        if endpoint_path.startswith("/api/v4/admin/marketing/") and "{page_id}" in endpoint_path and method == "PUT":
            # Empty body (partial update allows empty, but we test it)
            test_cases.append({
                "name": "empty_update_body",
                "description": "Update marketing page with empty body (partial update - should work)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {},
                "expected_status": [200, 400],  # May work or fail depending on implementation
            })
        
        return test_cases
    
    def _generate_linkedin_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate LinkedIn-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body for reference
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # LinkedIn search endpoint error tests
        if endpoint_path == "/api/v3/linkedin/" and method == "POST":
            # Missing required url field
            test_cases.append({
                "name": "missing_required_url",
                "description": "LinkedIn search without required url field (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {},
                "expected_status": [400, 422],
            })
            
            # Empty URL string
            test_cases.append({
                "name": "empty_url",
                "description": "LinkedIn search with empty URL (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "url": ""
                },
                "expected_status": [400],
            })
            
            # Invalid URL format
            test_cases.append({
                "name": "invalid_url_format",
                "description": "LinkedIn search with invalid URL format (may fail or return empty results)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "url": "not-a-linkedin-url"
                },
                "expected_status": [200, 400],  # May return empty results or error
            })
            
            # Wrong data type for URL
            test_cases.append({
                "name": "invalid_url_type",
                "description": "LinkedIn search with non-string URL (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "url": 12345
                },
                "expected_status": [400, 422],
            })
        
        return test_cases
    
    def _generate_usage_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate usage-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body (if available)
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Track usage endpoint error tests
        if endpoint_path == "/api/v1/usage/track/":
            if valid_body:
                # Invalid feature name
                invalid_feature_body = valid_body.copy()
                invalid_feature_body["feature"] = "INVALID_FEATURE"
                test_cases.append({
                    "name": "invalid_feature",
                    "description": "Track usage with invalid feature name",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_feature_body,
                    "expected_status": [400],
                })
                
                # Invalid amount (0 or negative)
                invalid_amount_body = valid_body.copy()
                invalid_amount_body["amount"] = 0
                test_cases.append({
                    "name": "invalid_amount_zero",
                    "description": "Track usage with amount = 0 (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_amount_body,
                    "expected_status": [422],
                })
                
                invalid_amount_body_negative = valid_body.copy()
                invalid_amount_body_negative["amount"] = -1
                test_cases.append({
                    "name": "invalid_amount_negative",
                    "description": "Track usage with negative amount (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_amount_body_negative,
                    "expected_status": [422],
                })
        
        # Reset usage endpoint error tests
        if endpoint_path == "/api/v2/usage/reset":
            if valid_body:
                # Invalid feature name
                invalid_feature_body = valid_body.copy()
                invalid_feature_body["feature"] = "INVALID_FEATURE"
                test_cases.append({
                    "name": "invalid_feature",
                    "description": "Reset usage with invalid feature name",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_feature_body,
                    "expected_status": [400],
                })
        
        return test_cases
    
    def _generate_scrape_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate scrape-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body (if available)
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Sales Navigator scrape endpoint error tests
        if endpoint_path == "/api/v3/sales-navigator/scrape":
            if valid_body:
                # Empty HTML
                empty_html_body = valid_body.copy()
                empty_html_body["html"] = ""
                test_cases.append({
                    "name": "empty_html",
                    "description": "Scrape with empty HTML (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_html_body,
                    "expected_status": [422, 400],
                })
                
                # Whitespace-only HTML
                whitespace_html_body = valid_body.copy()
                whitespace_html_body["html"] = "   \n\t  "
                test_cases.append({
                    "name": "whitespace_only_html",
                    "description": "Scrape with whitespace-only HTML (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": whitespace_html_body,
                    "expected_status": [422, 400],
                })
                
                # Missing HTML field
                missing_html_body = {"save": False}
                test_cases.append({
                    "name": "missing_html_field",
                    "description": "Scrape with missing HTML field (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_html_body,
                    "expected_status": [422],
                })
                
                # Invalid HTML type (not string)
                invalid_type_body = valid_body.copy()
                invalid_type_body["html"] = 12345
                test_cases.append({
                    "name": "invalid_html_type",
                    "description": "Scrape with invalid HTML type (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_type_body,
                    "expected_status": [422],
                })
        
        return test_cases
    
    def _get_expected_status_for_empty_body(self, endpoint_path: str, method: str) -> List[int]:
        """Get expected status codes for empty body requests based on endpoint behavior.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
        
        Returns:
            List of expected status codes
        """
        # Endpoints that allow empty body and return success
        allows_empty_body = {
            "POST /api/v2/ai-chats/": [201],  # Creates chat with empty body
            "POST /api/v1/auth/logout/": [200],  # Logout accepts empty body and returns 200
            "PUT /api/v1/users/profile/": [200],  # Profile update accepts empty body (all fields optional, partial update)
        }
        
        # Endpoints that return 404 for invalid IDs (before body validation)
        returns_404_for_invalid_id = {
            "PUT /api/v2/ai-chats/{chat_id}/": [404],  # Resource not found takes precedence
            "PUT /api/v4/admin/dashboard-pages/{page_id}": [404],  # Page not found
            "PUT /api/v4/admin/marketing/{page_id}": [404],  # Page not found
            "POST /api/v4/admin/marketing/{page_id}/publish": [404],  # Page not found
        }
        
        # Check exact match
        key = f"{method} {endpoint_path}"
        if key in allows_empty_body:
            return allows_empty_body[key]
        if key in returns_404_for_invalid_id:
            return returns_404_for_invalid_id[key]
        
        # Check pattern matches for endpoints with placeholders
        for pattern, statuses in returns_404_for_invalid_id.items():
            pattern_method, pattern_path = pattern.split(" ", 1)
            if method == pattern_method:
                # Check if endpoint structure matches (same number of parts)
                pattern_parts = pattern_path.split("/")
                endpoint_parts = endpoint_path.split("/")
                if len(pattern_parts) == len(endpoint_parts):
                    # Check if non-placeholder parts match
                    matches = True
                    for p, e in zip(pattern_parts, endpoint_parts):
                        if p.startswith("{") and p.endswith("}"):
                            continue  # Skip placeholder parts
                        if p != e:
                            matches = False
                            break
                    if matches:
                        return statuses
        
        # Default: expect validation error
        return [422, 400]
    
    def _generate_user_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate user-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body (if available)
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Registration endpoint error tests
        if endpoint_path in ["/api/v1/auth/register", "/api/v1/auth/register/"]:
            if valid_body:
                # Short password (< 8 chars)
                short_password_body = valid_body.copy()
                short_password_body["password"] = "short"
                test_cases.append({
                    "name": "short_password",
                    "description": "Registration with password too short (< 8 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": short_password_body,
                    "expected_status": [400],
                })
                
                # Long password (> 72 chars)
                long_password_body = valid_body.copy()
                long_password_body["password"] = "a" * 73
                test_cases.append({
                    "name": "long_password",
                    "description": "Registration with password too long (> 72 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": long_password_body,
                    "expected_status": [400],
                })
                
                # Invalid email format
                invalid_email_body = valid_body.copy()
                invalid_email_body["email"] = "not-an-email"
                test_cases.append({
                    "name": "invalid_email",
                    "description": "Registration with invalid email format",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_email_body,
                    "expected_status": [422],
                })
        
        # Login endpoint error tests
        if endpoint_path == "/api/v1/auth/login/":
            if valid_body:
                # Invalid credentials
                invalid_creds_body = valid_body.copy()
                invalid_creds_body["password"] = "wrongpassword"
                test_cases.append({
                    "name": "invalid_credentials",
                    "description": "Login with invalid credentials",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_creds_body,
                    "expected_status": [400],
                })
        
        # Profile update endpoint error tests
        if endpoint_path == "/api/v1/users/profile/":
            if valid_body:
                # Name too long (> 255 chars)
                long_name_body = valid_body.copy()
                long_name_body["name"] = "a" * 256
                test_cases.append({
                    "name": "long_name",
                    "description": "Profile update with name too long (> 255 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": long_name_body,
                    "expected_status": [400, 422],  # FastAPI returns 422 for validation errors
                })
                
                # Timezone too long (> 100 chars)
                long_timezone_body = valid_body.copy()
                long_timezone_body["timezone"] = "a" * 101
                test_cases.append({
                    "name": "long_timezone",
                    "description": "Profile update with timezone too long (> 100 characters)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": long_timezone_body,
                    "expected_status": [400, 422],  # FastAPI returns 422 for validation errors
                })
        
        # Role update endpoint error tests
        if "/users/{user_id}/role/" in endpoint_path:
            if valid_body:
                # Invalid role
                invalid_role_body = valid_body.copy()
                invalid_role_body["role"] = "InvalidRole"
                test_cases.append({
                    "name": "invalid_role",
                    "description": "Role update with invalid role value",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_role_body,
                    "expected_status": [400],
                })
        
        # Credits update endpoint error tests
        if "/users/{user_id}/credits/" in endpoint_path:
            if valid_body:
                # Negative credits
                negative_credits_body = valid_body.copy()
                negative_credits_body["credits"] = -1
                test_cases.append({
                    "name": "negative_credits",
                    "description": "Credits update with negative value",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": negative_credits_body,
                    "expected_status": [422, 400],
                })
        
        return test_cases
    
    def _generate_s3_endpoint_error_tests(
        self, endpoint_path: str, method: str
    ) -> List[Dict[str, Any]]:
        """Generate S3-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # S3 file get endpoint error tests (with file_id path parameter)
        if "/s3/files/{file_id}" in endpoint_path or "/s3/files/" in endpoint_path and "{file_id}" in endpoint_path:
            # Invalid pagination parameters
            # Limit too large (> 1000)
            test_cases.append({
                "name": "invalid_limit_too_large",
                "description": "Get S3 file with limit > 1000 (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 2000,
                    "offset": 0
                },
                "expected_status": [422],
            })
            
            # Negative offset
            test_cases.append({
                "name": "invalid_offset_negative",
                "description": "Get S3 file with negative offset (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 50,
                    "offset": -10
                },
                "expected_status": [422],
            })
            
            # Limit = 0 (below minimum)
            test_cases.append({
                "name": "invalid_limit_zero",
                "description": "Get S3 file with limit = 0 (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 0,
                    "offset": 0
                },
                "expected_status": [422],
            })
            
            # Limit without offset (should still work, offset defaults to 0)
            test_cases.append({
                "name": "limit_without_offset",
                "description": "Get S3 file with limit but no offset (offset defaults to 0)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "limit": 50
                },
                "expected_status": [200],
            })
            
            # Offset without limit (should fail - limit is required for pagination)
            test_cases.append({
                "name": "offset_without_limit",
                "description": "Get S3 file with offset but no limit (should fail or default to download mode)",
                "method": method,
                "endpoint": endpoint_path,
                "query_params": {
                    "offset": 10
                },
                "expected_status": [200, 422],  # May default to download mode or fail validation
            })
        
        return test_cases
    
    def _generate_root_endpoint_error_tests(
        self, endpoint_path: str, method: str
    ) -> List[Dict[str, Any]]:
        """Generate Root-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Root endpoints are designed to be highly available and should rarely return errors
        # The only documented error is 500 Internal Server Error (server configuration issue)
        # Since these are public endpoints, we don't test authentication errors
        
        # Note: Root endpoints don't have request bodies or complex query parameters
        # Error scenarios are limited to server errors (500)
        # These are typically not testable in normal test runs, but we document them
        
        return test_cases
    
    def _generate_marketing_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate Marketing-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body for reference
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Marketing create endpoint error tests
        if endpoint_path == "/api/v4/admin/marketing/" and method == "POST":
            # Missing required hero field
            test_cases.append({
                "name": "missing_required_hero",
                "description": "Create marketing page without required hero field (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "page_id": "test-page"
                    # Missing hero
                },
                "expected_status": [400, 422],
            })
            
            # Missing required page_id
            test_cases.append({
                "name": "missing_required_page_id",
                "description": "Create marketing page without required page_id (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "hero": {
                        "title": "Test Title",
                        "description": "Test description"
                    }
                    # Missing page_id
                },
                "expected_status": [400, 422],
            })
            
            # Invalid metadata status
            if valid_body:
                invalid_status_body = valid_body.copy()
                invalid_status_body["metadata"] = {
                    "title": "Test Title",
                    "description": "Test description",
                    "status": "invalid_status"  # Invalid status
                }
                test_cases.append({
                    "name": "invalid_metadata_status",
                    "description": "Create marketing page with invalid status (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_status_body,
                    "expected_status": [400, 422],
                })
        
        # Marketing update endpoint error tests
        if endpoint_path.startswith("/api/v4/admin/marketing/") and "{page_id}" in endpoint_path and method == "PUT":
            # Empty body (partial update allows empty, but we test it)
            test_cases.append({
                "name": "empty_update_body",
                "description": "Update marketing page with empty body (partial update - should work)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {},
                "expected_status": [200, 400],  # May work or fail depending on implementation
            })
        
        return test_cases
    
    def _generate_linkedin_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate LinkedIn-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body for reference
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # LinkedIn search endpoint error tests
        if endpoint_path == "/api/v3/linkedin/" and method == "POST":
            # Missing required url field
            test_cases.append({
                "name": "missing_required_url",
                "description": "LinkedIn search without required url field (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {},
                "expected_status": [400, 422],
            })
            
            # Empty URL string
            test_cases.append({
                "name": "empty_url",
                "description": "LinkedIn search with empty URL (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "url": ""
                },
                "expected_status": [400],
            })
            
            # Invalid URL format
            test_cases.append({
                "name": "invalid_url_format",
                "description": "LinkedIn search with invalid URL format (may fail or return empty results)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "url": "not-a-linkedin-url"
                },
                "expected_status": [200, 400],  # May return empty results or error
            })
            
            # Wrong data type for URL
            test_cases.append({
                "name": "invalid_url_type",
                "description": "LinkedIn search with non-string URL (should fail)",
                "method": method,
                "endpoint": endpoint_path,
                "body": {
                    "url": 12345
                },
                "expected_status": [400, 422],
            })
        
        return test_cases
    
    def _generate_usage_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate usage-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body (if available)
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Track usage endpoint error tests
        if endpoint_path == "/api/v1/usage/track/":
            if valid_body:
                # Invalid feature name
                invalid_feature_body = valid_body.copy()
                invalid_feature_body["feature"] = "INVALID_FEATURE"
                test_cases.append({
                    "name": "invalid_feature",
                    "description": "Track usage with invalid feature name",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_feature_body,
                    "expected_status": [400],
                })
                
                # Invalid amount (0 or negative)
                invalid_amount_body = valid_body.copy()
                invalid_amount_body["amount"] = 0
                test_cases.append({
                    "name": "invalid_amount_zero",
                    "description": "Track usage with amount = 0 (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_amount_body,
                    "expected_status": [422],
                })
                
                invalid_amount_body_negative = valid_body.copy()
                invalid_amount_body_negative["amount"] = -1
                test_cases.append({
                    "name": "invalid_amount_negative",
                    "description": "Track usage with negative amount (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_amount_body_negative,
                    "expected_status": [422],
                })
        
        # Reset usage endpoint error tests
        if endpoint_path == "/api/v2/usage/reset":
            if valid_body:
                # Invalid feature name
                invalid_feature_body = valid_body.copy()
                invalid_feature_body["feature"] = "INVALID_FEATURE"
                test_cases.append({
                    "name": "invalid_feature",
                    "description": "Reset usage with invalid feature name",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_feature_body,
                    "expected_status": [400],
                })
        
        return test_cases
    
    def _generate_scrape_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate scrape-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body (if available)
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Sales Navigator scrape endpoint error tests
        if endpoint_path == "/api/v3/sales-navigator/scrape":
            if valid_body:
                # Empty HTML
                empty_html_body = valid_body.copy()
                empty_html_body["html"] = ""
                test_cases.append({
                    "name": "empty_html",
                    "description": "Scrape with empty HTML (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_html_body,
                    "expected_status": [422, 400],
                })
                
                # Whitespace-only HTML
                whitespace_html_body = valid_body.copy()
                whitespace_html_body["html"] = "   \n\t  "
                test_cases.append({
                    "name": "whitespace_only_html",
                    "description": "Scrape with whitespace-only HTML (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": whitespace_html_body,
                    "expected_status": [422, 400],
                })
                
                # Missing HTML field
                missing_html_body = {"save": False}
                test_cases.append({
                    "name": "missing_html_field",
                    "description": "Scrape with missing HTML field (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_html_body,
                    "expected_status": [422],
                })
                
                # Invalid HTML type (not string)
                invalid_type_body = valid_body.copy()
                invalid_type_body["html"] = 12345
                test_cases.append({
                    "name": "invalid_html_type",
                    "description": "Scrape with invalid HTML type (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_type_body,
                    "expected_status": [422],
                })
        
        return test_cases

    def _generate_email_endpoint_error_tests(
        self, endpoint_path: str, method: str, valid_body: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate email-specific error test cases.
        
        Args:
            endpoint_path: Endpoint path
            method: HTTP method
            valid_body: Valid request body for reference
            
        Returns:
            List of error test case dictionaries
        """
        test_cases = []
        
        # Email finder endpoint (GET with query params - handled separately, not here)
        # This method only handles POST endpoints with request bodies
        
        # Email export endpoint error tests
        if endpoint_path == "/api/v3/email/export" and method == "POST":
            if valid_body:
                # Missing required contacts field
                test_cases.append({
                    "name": "missing_required_contacts",
                    "description": "Email export without required contacts field (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": {},
                    "expected_status": [400, 422],
                })
                
                # Empty contacts array
                empty_contacts_body = valid_body.copy()
                empty_contacts_body["contacts"] = []
                test_cases.append({
                    "name": "empty_contacts_array",
                    "description": "Email export with empty contacts array (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_contacts_body,
                    "expected_status": [400, 422],
                })
                
                # Invalid contacts structure (not an array)
                invalid_contacts_body = valid_body.copy()
                invalid_contacts_body["contacts"] = "not-an-array"
                test_cases.append({
                    "name": "invalid_contacts_type",
                    "description": "Email export with invalid contacts type (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_contacts_body,
                    "expected_status": [400, 422],
                })
        
        # Single email endpoint error tests
        if endpoint_path == "/api/v3/email/single/" and method == "POST":
            if valid_body:
                # Missing required first_name
                missing_first_name_body = valid_body.copy()
                missing_first_name_body.pop("first_name", None)
                test_cases.append({
                    "name": "missing_first_name",
                    "description": "Single email without first_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_first_name_body,
                    "expected_status": [400, 422],
                })
                
                # Missing required last_name
                missing_last_name_body = valid_body.copy()
                missing_last_name_body.pop("last_name", None)
                test_cases.append({
                    "name": "missing_last_name",
                    "description": "Single email without last_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_last_name_body,
                    "expected_status": [400, 422],
                })
                
                # Missing required domain
                missing_domain_body = valid_body.copy()
                missing_domain_body.pop("domain", None)
                test_cases.append({
                    "name": "missing_domain",
                    "description": "Single email without domain (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_domain_body,
                    "expected_status": [400, 422],
                })
                
                # Empty first_name
                empty_first_name_body = valid_body.copy()
                empty_first_name_body["first_name"] = ""
                test_cases.append({
                    "name": "empty_first_name",
                    "description": "Single email with empty first_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_first_name_body,
                    "expected_status": [400],
                })
                
                # Empty last_name
                empty_last_name_body = valid_body.copy()
                empty_last_name_body["last_name"] = ""
                test_cases.append({
                    "name": "empty_last_name",
                    "description": "Single email with empty last_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_last_name_body,
                    "expected_status": [400],
                })
                
                # Empty domain
                empty_domain_body = valid_body.copy()
                empty_domain_body["domain"] = ""
                test_cases.append({
                    "name": "empty_domain",
                    "description": "Single email with empty domain (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_domain_body,
                    "expected_status": [400],
                })
        
        # Bulk verifier endpoint error tests
        if endpoint_path == "/api/v3/email/bulk/verifier/" and method == "POST":
            if valid_body:
                # Missing required provider
                missing_provider_body = valid_body.copy()
                missing_provider_body.pop("provider", None)
                test_cases.append({
                    "name": "missing_provider",
                    "description": "Bulk verifier without provider (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_provider_body,
                    "expected_status": [400, 422],
                })
                
                # Missing required emails
                missing_emails_body = valid_body.copy()
                missing_emails_body.pop("emails", None)
                test_cases.append({
                    "name": "missing_emails",
                    "description": "Bulk verifier without emails array (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_emails_body,
                    "expected_status": [400, 422],
                })
                
                # Empty emails array
                empty_emails_body = valid_body.copy()
                empty_emails_body["emails"] = []
                test_cases.append({
                    "name": "empty_emails_array",
                    "description": "Bulk verifier with empty emails array (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_emails_body,
                    "expected_status": [400, 422],
                })
                
                # Invalid provider value
                invalid_provider_body = valid_body.copy()
                invalid_provider_body["provider"] = "invalid_provider"
                test_cases.append({
                    "name": "invalid_provider",
                    "description": "Bulk verifier with invalid provider (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_provider_body,
                    "expected_status": [400, 422],
                })
        
        # Single verifier endpoint error tests
        if endpoint_path == "/api/v3/email/single/verifier/" and method == "POST":
            if valid_body:
                # Missing required email
                missing_email_body = valid_body.copy()
                missing_email_body.pop("email", None)
                test_cases.append({
                    "name": "missing_email",
                    "description": "Single verifier without email (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_email_body,
                    "expected_status": [400, 422],
                })
                
                # Missing required provider
                missing_provider_body = valid_body.copy()
                missing_provider_body.pop("provider", None)
                test_cases.append({
                    "name": "missing_provider",
                    "description": "Single verifier without provider (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_provider_body,
                    "expected_status": [400, 422],
                })
                
                # Empty email
                empty_email_body = valid_body.copy()
                empty_email_body["email"] = ""
                test_cases.append({
                    "name": "empty_email",
                    "description": "Single verifier with empty email (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": empty_email_body,
                    "expected_status": [400],
                })
                
                # Invalid email format
                invalid_email_body = valid_body.copy()
                invalid_email_body["email"] = "not-an-email"
                test_cases.append({
                    "name": "invalid_email_format",
                    "description": "Single verifier with invalid email format (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_email_body,
                    "expected_status": [400, 422],
                })
                
                # Invalid provider value
                invalid_provider_body = valid_body.copy()
                invalid_provider_body["provider"] = "invalid_provider"
                test_cases.append({
                    "name": "invalid_provider",
                    "description": "Single verifier with invalid provider (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": invalid_provider_body,
                    "expected_status": [400, 422],
                })
        
        # Verifier endpoint error tests
        if endpoint_path == "/api/v3/email/verifier/" and method == "POST":
            if valid_body:
                # Missing required fields
                test_cases.append({
                    "name": "missing_required_fields",
                    "description": "Verifier without required fields (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": {},
                    "expected_status": [400, 422],
                })
                
                # Missing first_name
                missing_first_name_body = valid_body.copy()
                missing_first_name_body.pop("first_name", None)
                test_cases.append({
                    "name": "missing_first_name",
                    "description": "Verifier without first_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_first_name_body,
                    "expected_status": [400, 422],
                })
                
                # Missing last_name
                missing_last_name_body = valid_body.copy()
                missing_last_name_body.pop("last_name", None)
                test_cases.append({
                    "name": "missing_last_name",
                    "description": "Verifier without last_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_last_name_body,
                    "expected_status": [400, 422],
                })
                
                # Missing domain
                missing_domain_body = valid_body.copy()
                missing_domain_body.pop("domain", None)
                test_cases.append({
                    "name": "missing_domain",
                    "description": "Verifier without domain (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_domain_body,
                    "expected_status": [400, 422],
                })
                
                # Invalid email_count (negative or zero)
                if "email_count" in valid_body:
                    invalid_email_count_body = valid_body.copy()
                    invalid_email_count_body["email_count"] = -1
                    test_cases.append({
                        "name": "invalid_email_count_negative",
                        "description": "Verifier with negative email_count (should fail)",
                        "method": method,
                        "endpoint": endpoint_path,
                        "body": invalid_email_count_body,
                        "expected_status": [400, 422],
                    })
                    
                    invalid_email_count_zero_body = valid_body.copy()
                    invalid_email_count_zero_body["email_count"] = 0
                    test_cases.append({
                        "name": "invalid_email_count_zero",
                        "description": "Verifier with email_count = 0 (should fail)",
                        "method": method,
                        "endpoint": endpoint_path,
                        "body": invalid_email_count_zero_body,
                        "expected_status": [400, 422],
                    })
        
        # Verifier single endpoint error tests
        if endpoint_path == "/api/v3/email/verifier/single/" and method == "POST":
            if valid_body:
                # Missing required fields
                test_cases.append({
                    "name": "missing_required_fields",
                    "description": "Verifier single without required fields (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": {},
                    "expected_status": [400, 422],
                })
                
                # Missing first_name
                missing_first_name_body = valid_body.copy()
                missing_first_name_body.pop("first_name", None)
                test_cases.append({
                    "name": "missing_first_name",
                    "description": "Verifier single without first_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_first_name_body,
                    "expected_status": [400, 422],
                })
                
                # Missing last_name
                missing_last_name_body = valid_body.copy()
                missing_last_name_body.pop("last_name", None)
                test_cases.append({
                    "name": "missing_last_name",
                    "description": "Verifier single without last_name (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_last_name_body,
                    "expected_status": [400, 422],
                })
                
                # Missing domain
                missing_domain_body = valid_body.copy()
                missing_domain_body.pop("domain", None)
                test_cases.append({
                    "name": "missing_domain",
                    "description": "Verifier single without domain (should fail)",
                    "method": method,
                    "endpoint": endpoint_path,
                    "body": missing_domain_body,
                    "expected_status": [400, 422],
                })
        
        return test_cases
