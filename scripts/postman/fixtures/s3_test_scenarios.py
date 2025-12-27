"""Comprehensive test scenarios for S3 File Operations API endpoints.

This module defines all test scenarios for the S3 File Operations API,
covering list files, download files, and paginated data retrieval.
"""

from typing import Dict, List, Any


class S3TestScenarios:
    """Comprehensive test scenarios for S3 File Operations API endpoints."""
    
    @staticmethod
    def get_list_files_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for list CSV files endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "list_files",
                "name": "list_all_files",
                "description": "List all CSV files in S3 bucket without prefix filter",
                "method": "GET",
                "endpoint": "/api/v3/s3/files",
                "query_params": {},
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["files", "total"],
                    "files_is_list": True,
                    "total_is_int": True
                }
            },
            {
                "category": "list_files",
                "name": "list_files_with_prefix",
                "description": "List CSV files filtered by prefix (e.g., 'data/')",
                "method": "GET",
                "endpoint": "/api/v3/s3/files",
                "query_params": {
                    "prefix": "data/"
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["files", "total"],
                    "files_is_list": True,
                    "total_is_int": True
                }
            },
            {
                "category": "list_files",
                "name": "list_files_with_nested_prefix",
                "description": "List CSV files with nested prefix (e.g., 'data/2024/')",
                "method": "GET",
                "endpoint": "/api/v3/s3/files",
                "query_params": {
                    "prefix": "data/2024/"
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["files", "total"],
                    "files_is_list": True,
                    "total_is_int": True
                }
            },
            {
                "category": "list_files",
                "name": "list_files_empty_prefix",
                "description": "List files with empty prefix (should return all files)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files",
                "query_params": {
                    "prefix": ""
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["files", "total"],
                    "files_is_list": True,
                    "total_is_int": True
                }
            },
            {
                "category": "list_files",
                "name": "list_files_unauthorized",
                "description": "List files without authentication (should fail)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files",
                "query_params": {},
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
        ]
    
    @staticmethod
    def get_file_download_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for file download endpoint (download mode).
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "get_file",
                "name": "download_full_file",
                "description": "Download full CSV file (no pagination parameters)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {},  # No limit/offset = download mode
                "expected_status": [200, 404],  # 404 if file doesn't exist
                "validate_response": {
                    "content_type": "text/csv"
                }
            },
            {
                "category": "get_file",
                "name": "download_file_with_path",
                "description": "Download CSV file with nested path",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "exports/data/contacts_2024.csv"
                },
                "query_params": {},
                "expected_status": [200, 404],
                "validate_response": {
                    "content_type": "text/csv"
                }
            },
            {
                "category": "get_file",
                "name": "download_file_not_found",
                "description": "Attempt to download non-existent file (should fail)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "nonexistent/file.csv"
                },
                "query_params": {},
                "expected_status": [404],
            },
            {
                "category": "get_file",
                "name": "download_file_unauthorized",
                "description": "Download file without authentication (should fail)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {},
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
        ]
    
    @staticmethod
    def get_file_pagination_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for file pagination endpoint (pagination mode).
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "get_file_pagination",
                "name": "get_paginated_data_first_page",
                "description": "Get first page of CSV data (limit=50, offset=0)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 50,
                    "offset": 0
                },
                "expected_status": [200, 404],
                "validate_response": {
                    "has_fields": ["file_key", "rows", "limit", "offset"],
                    "rows_is_list": True,
                    "limit": 50,
                    "offset": 0
                }
            },
            {
                "category": "get_file_pagination",
                "name": "get_paginated_data_second_page",
                "description": "Get second page of CSV data (limit=50, offset=50)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 50,
                    "offset": 50
                },
                "expected_status": [200, 404],
                "validate_response": {
                    "has_fields": ["file_key", "rows", "limit", "offset"],
                    "rows_is_list": True,
                    "limit": 50,
                    "offset": 50
                }
            },
            {
                "category": "get_file_pagination",
                "name": "get_paginated_data_max_limit",
                "description": "Get paginated data with maximum limit (limit=1000)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 1000,
                    "offset": 0
                },
                "expected_status": [200, 404],
                "validate_response": {
                    "has_fields": ["file_key", "rows", "limit", "offset"],
                    "rows_is_list": True,
                    "limit": 1000,
                    "offset": 0
                }
            },
            {
                "category": "get_file_pagination",
                "name": "get_paginated_data_small_limit",
                "description": "Get paginated data with small limit (limit=10)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 10,
                    "offset": 0
                },
                "expected_status": [200, 404],
                "validate_response": {
                    "has_fields": ["file_key", "rows", "limit", "offset"],
                    "rows_is_list": True,
                    "limit": 10,
                    "offset": 0
                }
            },
            {
                "category": "get_file_pagination",
                "name": "get_paginated_data_large_offset",
                "description": "Get paginated data with large offset",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 50,
                    "offset": 1000
                },
                "expected_status": [200, 404],
                "validate_response": {
                    "has_fields": ["file_key", "rows", "limit", "offset"],
                    "rows_is_list": True,
                    "limit": 50,
                    "offset": 1000
                }
            },
            {
                "category": "get_file_pagination",
                "name": "get_paginated_data_limit_only",
                "description": "Get paginated data with limit only (offset defaults to 0)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 50
                    # offset not provided, should default to 0
                },
                "expected_status": [200, 404],
                "validate_response": {
                    "has_fields": ["file_key", "rows", "limit", "offset"],
                    "rows_is_list": True,
                    "limit": 50,
                    "offset": 0
                }
            },
            {
                "category": "get_file_pagination",
                "name": "get_paginated_data_not_found",
                "description": "Get paginated data from non-existent file (should fail)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "nonexistent/file.csv"
                },
                "query_params": {
                    "limit": 50,
                    "offset": 0
                },
                "expected_status": [404],
            },
            {
                "category": "get_file_pagination",
                "name": "get_paginated_data_unauthorized",
                "description": "Get paginated data without authentication (should fail)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 50,
                    "offset": 0
                },
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
        ]
    
    @staticmethod
    def get_file_error_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for file endpoint error cases.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "get_file_errors",
                "name": "invalid_limit_too_large",
                "description": "Get file with limit > 1000 (should fail validation)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 2000,
                    "offset": 0
                },
                "expected_status": [422],
            },
            {
                "category": "get_file_errors",
                "name": "invalid_limit_zero",
                "description": "Get file with limit = 0 (should fail validation)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 0,
                    "offset": 0
                },
                "expected_status": [422],
            },
            {
                "category": "get_file_errors",
                "name": "invalid_offset_negative",
                "description": "Get file with negative offset (should fail validation)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 50,
                    "offset": -10
                },
                "expected_status": [422],
            },
            {
                "category": "get_file_errors",
                "name": "invalid_offset_without_limit",
                "description": "Get file with offset but no limit (may default to download mode or fail)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "offset": 10
                    # limit not provided
                },
                "expected_status": [200, 422],  # May default to download mode or fail validation
            },
        ]
    
    @staticmethod
    def get_all_scenarios() -> Dict[str, List[Dict[str, Any]]]:
        """Get all test scenarios organized by category.
        
        Returns:
            Dictionary mapping category names to lists of scenarios
        """
        return {
            "list_files": S3TestScenarios.get_list_files_scenarios(),
            "get_file": S3TestScenarios.get_file_download_scenarios(),
            "get_file_pagination": S3TestScenarios.get_file_pagination_scenarios(),
            "get_file_errors": S3TestScenarios.get_file_error_scenarios(),
        }

This module defines all test scenarios for the S3 File Operations API,
covering list files, download files, and paginated data retrieval.
"""

from typing import Dict, List, Any


class S3TestScenarios:
    """Comprehensive test scenarios for S3 File Operations API endpoints."""
    
    @staticmethod
    def get_list_files_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for list CSV files endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "list_files",
                "name": "list_all_files",
                "description": "List all CSV files in S3 bucket without prefix filter",
                "method": "GET",
                "endpoint": "/api/v3/s3/files",
                "query_params": {},
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["files", "total"],
                    "files_is_list": True,
                    "total_is_int": True
                }
            },
            {
                "category": "list_files",
                "name": "list_files_with_prefix",
                "description": "List CSV files filtered by prefix (e.g., 'data/')",
                "method": "GET",
                "endpoint": "/api/v3/s3/files",
                "query_params": {
                    "prefix": "data/"
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["files", "total"],
                    "files_is_list": True,
                    "total_is_int": True
                }
            },
            {
                "category": "list_files",
                "name": "list_files_with_nested_prefix",
                "description": "List CSV files with nested prefix (e.g., 'data/2024/')",
                "method": "GET",
                "endpoint": "/api/v3/s3/files",
                "query_params": {
                    "prefix": "data/2024/"
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["files", "total"],
                    "files_is_list": True,
                    "total_is_int": True
                }
            },
            {
                "category": "list_files",
                "name": "list_files_empty_prefix",
                "description": "List files with empty prefix (should return all files)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files",
                "query_params": {
                    "prefix": ""
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["files", "total"],
                    "files_is_list": True,
                    "total_is_int": True
                }
            },
            {
                "category": "list_files",
                "name": "list_files_unauthorized",
                "description": "List files without authentication (should fail)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files",
                "query_params": {},
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
        ]
    
    @staticmethod
    def get_file_download_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for file download endpoint (download mode).
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "get_file",
                "name": "download_full_file",
                "description": "Download full CSV file (no pagination parameters)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {},  # No limit/offset = download mode
                "expected_status": [200, 404],  # 404 if file doesn't exist
                "validate_response": {
                    "content_type": "text/csv"
                }
            },
            {
                "category": "get_file",
                "name": "download_file_with_path",
                "description": "Download CSV file with nested path",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "exports/data/contacts_2024.csv"
                },
                "query_params": {},
                "expected_status": [200, 404],
                "validate_response": {
                    "content_type": "text/csv"
                }
            },
            {
                "category": "get_file",
                "name": "download_file_not_found",
                "description": "Attempt to download non-existent file (should fail)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "nonexistent/file.csv"
                },
                "query_params": {},
                "expected_status": [404],
            },
            {
                "category": "get_file",
                "name": "download_file_unauthorized",
                "description": "Download file without authentication (should fail)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {},
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
        ]
    
    @staticmethod
    def get_file_pagination_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for file pagination endpoint (pagination mode).
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "get_file_pagination",
                "name": "get_paginated_data_first_page",
                "description": "Get first page of CSV data (limit=50, offset=0)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 50,
                    "offset": 0
                },
                "expected_status": [200, 404],
                "validate_response": {
                    "has_fields": ["file_key", "rows", "limit", "offset"],
                    "rows_is_list": True,
                    "limit": 50,
                    "offset": 0
                }
            },
            {
                "category": "get_file_pagination",
                "name": "get_paginated_data_second_page",
                "description": "Get second page of CSV data (limit=50, offset=50)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 50,
                    "offset": 50
                },
                "expected_status": [200, 404],
                "validate_response": {
                    "has_fields": ["file_key", "rows", "limit", "offset"],
                    "rows_is_list": True,
                    "limit": 50,
                    "offset": 50
                }
            },
            {
                "category": "get_file_pagination",
                "name": "get_paginated_data_max_limit",
                "description": "Get paginated data with maximum limit (limit=1000)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 1000,
                    "offset": 0
                },
                "expected_status": [200, 404],
                "validate_response": {
                    "has_fields": ["file_key", "rows", "limit", "offset"],
                    "rows_is_list": True,
                    "limit": 1000,
                    "offset": 0
                }
            },
            {
                "category": "get_file_pagination",
                "name": "get_paginated_data_small_limit",
                "description": "Get paginated data with small limit (limit=10)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 10,
                    "offset": 0
                },
                "expected_status": [200, 404],
                "validate_response": {
                    "has_fields": ["file_key", "rows", "limit", "offset"],
                    "rows_is_list": True,
                    "limit": 10,
                    "offset": 0
                }
            },
            {
                "category": "get_file_pagination",
                "name": "get_paginated_data_large_offset",
                "description": "Get paginated data with large offset",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 50,
                    "offset": 1000
                },
                "expected_status": [200, 404],
                "validate_response": {
                    "has_fields": ["file_key", "rows", "limit", "offset"],
                    "rows_is_list": True,
                    "limit": 50,
                    "offset": 1000
                }
            },
            {
                "category": "get_file_pagination",
                "name": "get_paginated_data_limit_only",
                "description": "Get paginated data with limit only (offset defaults to 0)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 50
                    # offset not provided, should default to 0
                },
                "expected_status": [200, 404],
                "validate_response": {
                    "has_fields": ["file_key", "rows", "limit", "offset"],
                    "rows_is_list": True,
                    "limit": 50,
                    "offset": 0
                }
            },
            {
                "category": "get_file_pagination",
                "name": "get_paginated_data_not_found",
                "description": "Get paginated data from non-existent file (should fail)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "nonexistent/file.csv"
                },
                "query_params": {
                    "limit": 50,
                    "offset": 0
                },
                "expected_status": [404],
            },
            {
                "category": "get_file_pagination",
                "name": "get_paginated_data_unauthorized",
                "description": "Get paginated data without authentication (should fail)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 50,
                    "offset": 0
                },
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
        ]
    
    @staticmethod
    def get_file_error_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for file endpoint error cases.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "get_file_errors",
                "name": "invalid_limit_too_large",
                "description": "Get file with limit > 1000 (should fail validation)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 2000,
                    "offset": 0
                },
                "expected_status": [422],
            },
            {
                "category": "get_file_errors",
                "name": "invalid_limit_zero",
                "description": "Get file with limit = 0 (should fail validation)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 0,
                    "offset": 0
                },
                "expected_status": [422],
            },
            {
                "category": "get_file_errors",
                "name": "invalid_offset_negative",
                "description": "Get file with negative offset (should fail validation)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 50,
                    "offset": -10
                },
                "expected_status": [422],
            },
            {
                "category": "get_file_errors",
                "name": "invalid_offset_without_limit",
                "description": "Get file with offset but no limit (may default to download mode or fail)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "offset": 10
                    # limit not provided
                },
                "expected_status": [200, 422],  # May default to download mode or fail validation
            },
        ]
    
    @staticmethod
    def get_all_scenarios() -> Dict[str, List[Dict[str, Any]]]:
        """Get all test scenarios organized by category.
        
        Returns:
            Dictionary mapping category names to lists of scenarios
        """
        return {
            "list_files": S3TestScenarios.get_list_files_scenarios(),
            "get_file": S3TestScenarios.get_file_download_scenarios(),
            "get_file_pagination": S3TestScenarios.get_file_pagination_scenarios(),
            "get_file_errors": S3TestScenarios.get_file_error_scenarios(),
        }

This module defines all test scenarios for the S3 File Operations API,
covering list files, download files, and paginated data retrieval.
"""

from typing import Dict, List, Any


class S3TestScenarios:
    """Comprehensive test scenarios for S3 File Operations API endpoints."""
    
    @staticmethod
    def get_list_files_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for list CSV files endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "list_files",
                "name": "list_all_files",
                "description": "List all CSV files in S3 bucket without prefix filter",
                "method": "GET",
                "endpoint": "/api/v3/s3/files",
                "query_params": {},
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["files", "total"],
                    "files_is_list": True,
                    "total_is_int": True
                }
            },
            {
                "category": "list_files",
                "name": "list_files_with_prefix",
                "description": "List CSV files filtered by prefix (e.g., 'data/')",
                "method": "GET",
                "endpoint": "/api/v3/s3/files",
                "query_params": {
                    "prefix": "data/"
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["files", "total"],
                    "files_is_list": True,
                    "total_is_int": True
                }
            },
            {
                "category": "list_files",
                "name": "list_files_with_nested_prefix",
                "description": "List CSV files with nested prefix (e.g., 'data/2024/')",
                "method": "GET",
                "endpoint": "/api/v3/s3/files",
                "query_params": {
                    "prefix": "data/2024/"
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["files", "total"],
                    "files_is_list": True,
                    "total_is_int": True
                }
            },
            {
                "category": "list_files",
                "name": "list_files_empty_prefix",
                "description": "List files with empty prefix (should return all files)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files",
                "query_params": {
                    "prefix": ""
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["files", "total"],
                    "files_is_list": True,
                    "total_is_int": True
                }
            },
            {
                "category": "list_files",
                "name": "list_files_unauthorized",
                "description": "List files without authentication (should fail)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files",
                "query_params": {},
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
        ]
    
    @staticmethod
    def get_file_download_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for file download endpoint (download mode).
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "get_file",
                "name": "download_full_file",
                "description": "Download full CSV file (no pagination parameters)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {},  # No limit/offset = download mode
                "expected_status": [200, 404],  # 404 if file doesn't exist
                "validate_response": {
                    "content_type": "text/csv"
                }
            },
            {
                "category": "get_file",
                "name": "download_file_with_path",
                "description": "Download CSV file with nested path",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "exports/data/contacts_2024.csv"
                },
                "query_params": {},
                "expected_status": [200, 404],
                "validate_response": {
                    "content_type": "text/csv"
                }
            },
            {
                "category": "get_file",
                "name": "download_file_not_found",
                "description": "Attempt to download non-existent file (should fail)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "nonexistent/file.csv"
                },
                "query_params": {},
                "expected_status": [404],
            },
            {
                "category": "get_file",
                "name": "download_file_unauthorized",
                "description": "Download file without authentication (should fail)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {},
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
        ]
    
    @staticmethod
    def get_file_pagination_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for file pagination endpoint (pagination mode).
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "get_file_pagination",
                "name": "get_paginated_data_first_page",
                "description": "Get first page of CSV data (limit=50, offset=0)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 50,
                    "offset": 0
                },
                "expected_status": [200, 404],
                "validate_response": {
                    "has_fields": ["file_key", "rows", "limit", "offset"],
                    "rows_is_list": True,
                    "limit": 50,
                    "offset": 0
                }
            },
            {
                "category": "get_file_pagination",
                "name": "get_paginated_data_second_page",
                "description": "Get second page of CSV data (limit=50, offset=50)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 50,
                    "offset": 50
                },
                "expected_status": [200, 404],
                "validate_response": {
                    "has_fields": ["file_key", "rows", "limit", "offset"],
                    "rows_is_list": True,
                    "limit": 50,
                    "offset": 50
                }
            },
            {
                "category": "get_file_pagination",
                "name": "get_paginated_data_max_limit",
                "description": "Get paginated data with maximum limit (limit=1000)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 1000,
                    "offset": 0
                },
                "expected_status": [200, 404],
                "validate_response": {
                    "has_fields": ["file_key", "rows", "limit", "offset"],
                    "rows_is_list": True,
                    "limit": 1000,
                    "offset": 0
                }
            },
            {
                "category": "get_file_pagination",
                "name": "get_paginated_data_small_limit",
                "description": "Get paginated data with small limit (limit=10)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 10,
                    "offset": 0
                },
                "expected_status": [200, 404],
                "validate_response": {
                    "has_fields": ["file_key", "rows", "limit", "offset"],
                    "rows_is_list": True,
                    "limit": 10,
                    "offset": 0
                }
            },
            {
                "category": "get_file_pagination",
                "name": "get_paginated_data_large_offset",
                "description": "Get paginated data with large offset",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 50,
                    "offset": 1000
                },
                "expected_status": [200, 404],
                "validate_response": {
                    "has_fields": ["file_key", "rows", "limit", "offset"],
                    "rows_is_list": True,
                    "limit": 50,
                    "offset": 1000
                }
            },
            {
                "category": "get_file_pagination",
                "name": "get_paginated_data_limit_only",
                "description": "Get paginated data with limit only (offset defaults to 0)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 50
                    # offset not provided, should default to 0
                },
                "expected_status": [200, 404],
                "validate_response": {
                    "has_fields": ["file_key", "rows", "limit", "offset"],
                    "rows_is_list": True,
                    "limit": 50,
                    "offset": 0
                }
            },
            {
                "category": "get_file_pagination",
                "name": "get_paginated_data_not_found",
                "description": "Get paginated data from non-existent file (should fail)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "nonexistent/file.csv"
                },
                "query_params": {
                    "limit": 50,
                    "offset": 0
                },
                "expected_status": [404],
            },
            {
                "category": "get_file_pagination",
                "name": "get_paginated_data_unauthorized",
                "description": "Get paginated data without authentication (should fail)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 50,
                    "offset": 0
                },
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
        ]
    
    @staticmethod
    def get_file_error_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for file endpoint error cases.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "get_file_errors",
                "name": "invalid_limit_too_large",
                "description": "Get file with limit > 1000 (should fail validation)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 2000,
                    "offset": 0
                },
                "expected_status": [422],
            },
            {
                "category": "get_file_errors",
                "name": "invalid_limit_zero",
                "description": "Get file with limit = 0 (should fail validation)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 0,
                    "offset": 0
                },
                "expected_status": [422],
            },
            {
                "category": "get_file_errors",
                "name": "invalid_offset_negative",
                "description": "Get file with negative offset (should fail validation)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 50,
                    "offset": -10
                },
                "expected_status": [422],
            },
            {
                "category": "get_file_errors",
                "name": "invalid_offset_without_limit",
                "description": "Get file with offset but no limit (may default to download mode or fail)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "offset": 10
                    # limit not provided
                },
                "expected_status": [200, 422],  # May default to download mode or fail validation
            },
        ]
    
    @staticmethod
    def get_all_scenarios() -> Dict[str, List[Dict[str, Any]]]:
        """Get all test scenarios organized by category.
        
        Returns:
            Dictionary mapping category names to lists of scenarios
        """
        return {
            "list_files": S3TestScenarios.get_list_files_scenarios(),
            "get_file": S3TestScenarios.get_file_download_scenarios(),
            "get_file_pagination": S3TestScenarios.get_file_pagination_scenarios(),
            "get_file_errors": S3TestScenarios.get_file_error_scenarios(),
        }

This module defines all test scenarios for the S3 File Operations API,
covering list files, download files, and paginated data retrieval.
"""

from typing import Dict, List, Any


class S3TestScenarios:
    """Comprehensive test scenarios for S3 File Operations API endpoints."""
    
    @staticmethod
    def get_list_files_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for list CSV files endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "list_files",
                "name": "list_all_files",
                "description": "List all CSV files in S3 bucket without prefix filter",
                "method": "GET",
                "endpoint": "/api/v3/s3/files",
                "query_params": {},
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["files", "total"],
                    "files_is_list": True,
                    "total_is_int": True
                }
            },
            {
                "category": "list_files",
                "name": "list_files_with_prefix",
                "description": "List CSV files filtered by prefix (e.g., 'data/')",
                "method": "GET",
                "endpoint": "/api/v3/s3/files",
                "query_params": {
                    "prefix": "data/"
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["files", "total"],
                    "files_is_list": True,
                    "total_is_int": True
                }
            },
            {
                "category": "list_files",
                "name": "list_files_with_nested_prefix",
                "description": "List CSV files with nested prefix (e.g., 'data/2024/')",
                "method": "GET",
                "endpoint": "/api/v3/s3/files",
                "query_params": {
                    "prefix": "data/2024/"
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["files", "total"],
                    "files_is_list": True,
                    "total_is_int": True
                }
            },
            {
                "category": "list_files",
                "name": "list_files_empty_prefix",
                "description": "List files with empty prefix (should return all files)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files",
                "query_params": {
                    "prefix": ""
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["files", "total"],
                    "files_is_list": True,
                    "total_is_int": True
                }
            },
            {
                "category": "list_files",
                "name": "list_files_unauthorized",
                "description": "List files without authentication (should fail)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files",
                "query_params": {},
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
        ]
    
    @staticmethod
    def get_file_download_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for file download endpoint (download mode).
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "get_file",
                "name": "download_full_file",
                "description": "Download full CSV file (no pagination parameters)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {},  # No limit/offset = download mode
                "expected_status": [200, 404],  # 404 if file doesn't exist
                "validate_response": {
                    "content_type": "text/csv"
                }
            },
            {
                "category": "get_file",
                "name": "download_file_with_path",
                "description": "Download CSV file with nested path",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "exports/data/contacts_2024.csv"
                },
                "query_params": {},
                "expected_status": [200, 404],
                "validate_response": {
                    "content_type": "text/csv"
                }
            },
            {
                "category": "get_file",
                "name": "download_file_not_found",
                "description": "Attempt to download non-existent file (should fail)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "nonexistent/file.csv"
                },
                "query_params": {},
                "expected_status": [404],
            },
            {
                "category": "get_file",
                "name": "download_file_unauthorized",
                "description": "Download file without authentication (should fail)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {},
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
        ]
    
    @staticmethod
    def get_file_pagination_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for file pagination endpoint (pagination mode).
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "get_file_pagination",
                "name": "get_paginated_data_first_page",
                "description": "Get first page of CSV data (limit=50, offset=0)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 50,
                    "offset": 0
                },
                "expected_status": [200, 404],
                "validate_response": {
                    "has_fields": ["file_key", "rows", "limit", "offset"],
                    "rows_is_list": True,
                    "limit": 50,
                    "offset": 0
                }
            },
            {
                "category": "get_file_pagination",
                "name": "get_paginated_data_second_page",
                "description": "Get second page of CSV data (limit=50, offset=50)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 50,
                    "offset": 50
                },
                "expected_status": [200, 404],
                "validate_response": {
                    "has_fields": ["file_key", "rows", "limit", "offset"],
                    "rows_is_list": True,
                    "limit": 50,
                    "offset": 50
                }
            },
            {
                "category": "get_file_pagination",
                "name": "get_paginated_data_max_limit",
                "description": "Get paginated data with maximum limit (limit=1000)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 1000,
                    "offset": 0
                },
                "expected_status": [200, 404],
                "validate_response": {
                    "has_fields": ["file_key", "rows", "limit", "offset"],
                    "rows_is_list": True,
                    "limit": 1000,
                    "offset": 0
                }
            },
            {
                "category": "get_file_pagination",
                "name": "get_paginated_data_small_limit",
                "description": "Get paginated data with small limit (limit=10)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 10,
                    "offset": 0
                },
                "expected_status": [200, 404],
                "validate_response": {
                    "has_fields": ["file_key", "rows", "limit", "offset"],
                    "rows_is_list": True,
                    "limit": 10,
                    "offset": 0
                }
            },
            {
                "category": "get_file_pagination",
                "name": "get_paginated_data_large_offset",
                "description": "Get paginated data with large offset",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 50,
                    "offset": 1000
                },
                "expected_status": [200, 404],
                "validate_response": {
                    "has_fields": ["file_key", "rows", "limit", "offset"],
                    "rows_is_list": True,
                    "limit": 50,
                    "offset": 1000
                }
            },
            {
                "category": "get_file_pagination",
                "name": "get_paginated_data_limit_only",
                "description": "Get paginated data with limit only (offset defaults to 0)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 50
                    # offset not provided, should default to 0
                },
                "expected_status": [200, 404],
                "validate_response": {
                    "has_fields": ["file_key", "rows", "limit", "offset"],
                    "rows_is_list": True,
                    "limit": 50,
                    "offset": 0
                }
            },
            {
                "category": "get_file_pagination",
                "name": "get_paginated_data_not_found",
                "description": "Get paginated data from non-existent file (should fail)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "nonexistent/file.csv"
                },
                "query_params": {
                    "limit": 50,
                    "offset": 0
                },
                "expected_status": [404],
            },
            {
                "category": "get_file_pagination",
                "name": "get_paginated_data_unauthorized",
                "description": "Get paginated data without authentication (should fail)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 50,
                    "offset": 0
                },
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
        ]
    
    @staticmethod
    def get_file_error_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for file endpoint error cases.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "get_file_errors",
                "name": "invalid_limit_too_large",
                "description": "Get file with limit > 1000 (should fail validation)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 2000,
                    "offset": 0
                },
                "expected_status": [422],
            },
            {
                "category": "get_file_errors",
                "name": "invalid_limit_zero",
                "description": "Get file with limit = 0 (should fail validation)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 0,
                    "offset": 0
                },
                "expected_status": [422],
            },
            {
                "category": "get_file_errors",
                "name": "invalid_offset_negative",
                "description": "Get file with negative offset (should fail validation)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "limit": 50,
                    "offset": -10
                },
                "expected_status": [422],
            },
            {
                "category": "get_file_errors",
                "name": "invalid_offset_without_limit",
                "description": "Get file with offset but no limit (may default to download mode or fail)",
                "method": "GET",
                "endpoint": "/api/v3/s3/files/{file_id}",
                "path_params": {
                    "file_id": "data/contacts_2024.csv"
                },
                "query_params": {
                    "offset": 10
                    # limit not provided
                },
                "expected_status": [200, 422],  # May default to download mode or fail validation
            },
        ]
    
    @staticmethod
    def get_all_scenarios() -> Dict[str, List[Dict[str, Any]]]:
        """Get all test scenarios organized by category.
        
        Returns:
            Dictionary mapping category names to lists of scenarios
        """
        return {
            "list_files": S3TestScenarios.get_list_files_scenarios(),
            "get_file": S3TestScenarios.get_file_download_scenarios(),
            "get_file_pagination": S3TestScenarios.get_file_pagination_scenarios(),
            "get_file_errors": S3TestScenarios.get_file_error_scenarios(),
        }
