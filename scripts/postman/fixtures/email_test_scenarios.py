"""Comprehensive test scenarios for Email API endpoints.

This module defines all test scenarios for the Email API,
covering email finder, export, and verification operations.
"""

from typing import Dict, List, Any


class EmailTestScenarios:
    """Comprehensive test scenarios for Email API endpoints."""
    
    @staticmethod
    def get_finder_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for email finder endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "finder",
                "name": "find_emails_by_name_and_domain",
                "description": "Find emails by first name, last name, and domain",
                "method": "GET",
                "endpoint": "/api/v3/email/finder/",
                "query_params": {
                    "first_name": "John",
                    "last_name": "Doe",
                    "domain": "example.com"
                },
                "expected_status": [200, 404],  # 404 if no contacts found
                "validate_response": {
                    "has_fields": ["emails", "total"],
                    "emails_is_list": True
                }
            },
            {
                "category": "finder",
                "name": "find_emails_with_website_url",
                "description": "Find emails using website URL instead of domain",
                "method": "GET",
                "endpoint": "/api/v3/email/finder/",
                "query_params": {
                    "first_name": "Jane",
                    "last_name": "Smith",
                    "website": "https://www.example.com"
                },
                "expected_status": [200, 404],
                "validate_response": {
                    "has_fields": ["emails", "total"]
                }
            },
            {
                "category": "finder",
                "name": "find_emails_partial_name_match",
                "description": "Find emails with partial name matching (case-insensitive)",
                "method": "GET",
                "endpoint": "/api/v3/email/finder/",
                "query_params": {
                    "first_name": "john",
                    "last_name": "doe",
                    "domain": "example.com"
                },
                "expected_status": [200, 404],
                "validate_response": {
                    "has_fields": ["emails", "total"]
                }
            },
            {
                "category": "finder",
                "name": "find_emails_no_results",
                "description": "Find emails when no contacts match (should return 404)",
                "method": "GET",
                "endpoint": "/api/v3/email/finder/",
                "query_params": {
                    "first_name": "Nonexistent",
                    "last_name": "Person",
                    "domain": "example.com"
                },
                "expected_status": [404],
                "validate_response": {
                    "has_field": "detail"
                }
            },
            {
                "category": "finder",
                "name": "find_emails_unauthorized",
                "description": "Find emails without authentication (should fail)",
                "method": "GET",
                "endpoint": "/api/v3/email/finder/",
                "query_params": {
                    "first_name": "John",
                    "last_name": "Doe",
                    "domain": "example.com"
                },
                "requires_auth": False,
                "expected_status": [401],
                "validate_response": {
                    "has_field": "detail"
                }
            }
        ]
    
    @staticmethod
    def get_finder_error_scenarios() -> List[Dict[str, Any]]:
        """Get error test scenarios for email finder endpoint.
        
        Returns:
            List of error test scenario dictionaries
        """
        return [
            {
                "category": "finder_errors",
                "name": "missing_first_name",
                "description": "Email finder without first_name parameter",
                "method": "GET",
                "endpoint": "/api/v3/email/finder/",
                "query_params": {
                    "last_name": "Doe",
                    "domain": "example.com"
                },
                "expected_status": [400],
                "validate_response": {
                    "has_field": "detail"
                }
            },
            {
                "category": "finder_errors",
                "name": "missing_last_name",
                "description": "Email finder without last_name parameter",
                "method": "GET",
                "endpoint": "/api/v3/email/finder/",
                "query_params": {
                    "first_name": "John",
                    "domain": "example.com"
                },
                "expected_status": [400],
                "validate_response": {
                    "has_field": "detail"
                }
            },
            {
                "category": "finder_errors",
                "name": "missing_domain",
                "description": "Email finder without domain or website parameter",
                "method": "GET",
                "endpoint": "/api/v3/email/finder/",
                "query_params": {
                    "first_name": "John",
                    "last_name": "Doe"
                },
                "expected_status": [400],
                "validate_response": {
                    "has_field": "detail"
                }
            },
            {
                "category": "finder_errors",
                "name": "invalid_domain_format",
                "description": "Email finder with invalid domain format",
                "method": "GET",
                "endpoint": "/api/v3/email/finder/",
                "query_params": {
                    "first_name": "John",
                    "last_name": "Doe",
                    "domain": "invalid-domain-format"
                },
                "expected_status": [400],
                "validate_response": {
                    "has_field": "detail"
                }
            }
        ]
    
    @staticmethod
    def get_export_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for email export endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "export",
                "name": "export_emails_minimal",
                "description": "Export emails with minimal contact data",
                "method": "POST",
                "endpoint": "/api/v3/email/export",
                "body": {
                    "contacts": [
                        {
                            "first_name": "John",
                            "last_name": "Doe",
                            "domain": "example.com"
                        }
                    ]
                },
                "expected_status": [201],
                "validate_response": {
                    "has_fields": ["export_id", "download_url", "expires_at", "contact_count", "status"]
                }
            },
            {
                "category": "export",
                "name": "export_emails_with_existing_email",
                "description": "Export emails with existing email addresses to verify",
                "method": "POST",
                "endpoint": "/api/v3/email/export",
                "body": {
                    "contacts": [
                        {
                            "first_name": "John",
                            "last_name": "Doe",
                            "domain": "example.com",
                            "email": "john.doe@example.com"
                        }
                    ]
                },
                "expected_status": [201],
                "validate_response": {
                    "has_fields": ["export_id", "status"]
                }
            },
            {
                "category": "export",
                "name": "export_emails_multiple_contacts",
                "description": "Export emails for multiple contacts",
                "method": "POST",
                "endpoint": "/api/v3/email/export",
                "body": {
                    "contacts": [
                        {
                            "first_name": "John",
                            "last_name": "Doe",
                            "domain": "example.com"
                        },
                        {
                            "first_name": "Jane",
                            "last_name": "Smith",
                            "website": "https://www.example.com"
                        }
                    ]
                },
                "expected_status": [201],
                "validate_response": {
                    "has_fields": ["export_id", "contact_count"]
                }
            },
            {
                "category": "export",
                "name": "export_emails_with_mapping",
                "description": "Export emails with CSV column mapping",
                "method": "POST",
                "endpoint": "/api/v3/email/export",
                "body": {
                    "contacts": [
                        {
                            "first_name": "John",
                            "last_name": "Doe",
                            "domain": "example.com"
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
                "expected_status": [201],
                "validate_response": {
                    "has_fields": ["export_id"]
                }
            }
        ]
    
    @staticmethod
    def get_export_error_scenarios() -> List[Dict[str, Any]]:
        """Get error test scenarios for email export endpoint.
        
        Returns:
            List of error test scenario dictionaries
        """
        return [
            {
                "category": "export_errors",
                "name": "empty_contacts",
                "description": "Export emails with empty contacts list",
                "method": "POST",
                "endpoint": "/api/v3/email/export",
                "body": {
                    "contacts": []
                },
                "expected_status": [400, 422],
                "validate_response": {
                    "has_field": "detail"
                }
            },
            {
                "category": "export_errors",
                "name": "missing_first_name",
                "description": "Export emails with missing first_name",
                "method": "POST",
                "endpoint": "/api/v3/email/export",
                "body": {
                    "contacts": [
                        {
                            "last_name": "Doe",
                            "domain": "example.com"
                        }
                    ]
                },
                "expected_status": [400, 422],
                "validate_response": {
                    "has_field": "detail"
                }
            },
            {
                "category": "export_errors",
                "name": "missing_domain",
                "description": "Export emails with missing domain/website",
                "method": "POST",
                "endpoint": "/api/v3/email/export",
                "body": {
                    "contacts": [
                        {
                            "first_name": "John",
                            "last_name": "Doe"
                        }
                    ]
                },
                "expected_status": [400, 422],
                "validate_response": {
                    "has_field": "detail"
                }
            }
        ]
    
    @staticmethod
    def get_single_email_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for single email endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "single",
                "name": "get_single_email",
                "description": "Get single email address for a contact",
                "method": "POST",
                "endpoint": "/api/v3/email/single/",
                "body": {
                    "first_name": "John",
                    "last_name": "Doe",
                    "domain": "example.com",
                    "provider": "truelist"
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["email", "source"]
                }
            },
            {
                "category": "single",
                "name": "get_single_email_with_website",
                "description": "Get single email using website URL",
                "method": "POST",
                "endpoint": "/api/v3/email/single/",
                "body": {
                    "first_name": "Jane",
                    "last_name": "Smith",
                    "website": "https://www.example.com",
                    "provider": "truelist"
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["email", "source"]
                }
            },
            {
                "category": "single",
                "name": "get_single_email_not_found",
                "description": "Get single email when no email found (returns null)",
                "method": "POST",
                "endpoint": "/api/v3/email/single/",
                "body": {
                    "first_name": "Nonexistent",
                    "last_name": "Person",
                    "domain": "example.com",
                    "provider": "truelist"
                },
                "expected_status": [200],
                "validate_response": {
                    "email_is_null": True
                }
            }
        ]
    
    @staticmethod
    def get_single_email_error_scenarios() -> List[Dict[str, Any]]:
        """Get error test scenarios for single email endpoint.
        
        Returns:
            List of error test scenario dictionaries
        """
        return [
            {
                "category": "single_errors",
                "name": "missing_first_name",
                "description": "Single email without first_name",
                "method": "POST",
                "endpoint": "/api/v3/email/single/",
                "body": {
                    "last_name": "Doe",
                    "domain": "example.com",
                    "provider": "truelist"
                },
                "expected_status": [400, 422],
                "validate_response": {
                    "has_field": "detail"
                }
            },
            {
                "category": "single_errors",
                "name": "missing_domain",
                "description": "Single email without domain or website",
                "method": "POST",
                "endpoint": "/api/v3/email/single/",
                "body": {
                    "first_name": "John",
                    "last_name": "Doe",
                    "provider": "truelist"
                },
                "expected_status": [400, 422],
                "validate_response": {
                    "has_field": "detail"
                }
            }
        ]
    
    @staticmethod
    def get_bulk_verifier_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for bulk email verifier endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "bulk_verifier",
                "name": "verify_multiple_emails",
                "description": "Verify multiple email addresses",
                "method": "POST",
                "endpoint": "/api/v3/email/bulk/verifier/",
                "body": {
                    "provider": "truelist",
                    "emails": [
                        "john.doe@example.com",
                        "jane.smith@example.com",
                        "test@example.com"
                    ]
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["results", "total", "valid_count", "invalid_count", "catchall_count", "unknown_count"]
                }
            },
            {
                "category": "bulk_verifier",
                "name": "verify_emails_with_csv_context",
                "description": "Verify emails with CSV context for file generation",
                "method": "POST",
                "endpoint": "/api/v3/email/bulk/verifier/",
                "body": {
                    "provider": "truelist",
                    "emails": [
                        "john.doe@example.com",
                        "jane.smith@example.com"
                    ],
                    "raw_headers": ["first_name", "last_name", "email"],
                    "rows": [
                        {"first_name": "John", "last_name": "Doe", "email": "john.doe@example.com"},
                        {"first_name": "Jane", "last_name": "Smith", "email": "jane.smith@example.com"}
                    ],
                    "email_column": "email"
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["results", "download_url", "export_id", "expires_at"]
                }
            }
        ]
    
    @staticmethod
    def get_bulk_verifier_error_scenarios() -> List[Dict[str, Any]]:
        """Get error test scenarios for bulk email verifier endpoint.
        
        Returns:
            List of error test scenario dictionaries
        """
        return [
            {
                "category": "bulk_verifier_errors",
                "name": "empty_emails",
                "description": "Bulk verifier with empty emails list",
                "method": "POST",
                "endpoint": "/api/v3/email/bulk/verifier/",
                "body": {
                    "provider": "truelist",
                    "emails": []
                },
                "expected_status": [400, 422],
                "validate_response": {
                    "has_field": "detail"
                }
            },
            {
                "category": "bulk_verifier_errors",
                "name": "invalid_email_format",
                "description": "Bulk verifier with invalid email format",
                "method": "POST",
                "endpoint": "/api/v3/email/bulk/verifier/",
                "body": {
                    "provider": "truelist",
                    "emails": ["invalid-email-format"]
                },
                "expected_status": [400, 422],
                "validate_response": {
                    "has_field": "detail"
                }
            },
            {
                "category": "bulk_verifier_errors",
                "name": "exceeds_email_limit",
                "description": "Bulk verifier with more than 10000 emails",
                "method": "POST",
                "endpoint": "/api/v3/email/bulk/verifier/",
                "body": {
                    "provider": "truelist",
                    "emails": [f"test{i}@example.com" for i in range(10001)]
                },
                "expected_status": [400, 422],
                "validate_response": {
                    "has_field": "detail"
                }
            }
        ]
    
    @staticmethod
    def get_single_verifier_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for single email verifier endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "single_verifier",
                "name": "verify_single_email",
                "description": "Verify a single email address",
                "method": "POST",
                "endpoint": "/api/v3/email/single/verifier/",
                "body": {
                    "email": "john.doe@example.com",
                    "provider": "truelist"
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["result"],
                    "result_has_fields": ["email", "status"]
                }
            },
            {
                "category": "single_verifier",
                "name": "verify_single_email_truelist",
                "description": "Verify a single email using Truelist provider",
                "method": "POST",
                "endpoint": "/api/v3/email/single/verifier/",
                "body": {
                    "email": "jane.smith@example.com",
                    "provider": "truelist"
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["result"]
                }
            }
        ]
    
    @staticmethod
    def get_single_verifier_error_scenarios() -> List[Dict[str, Any]]:
        """Get error test scenarios for single email verifier endpoint.
        
        Returns:
            List of error test scenario dictionaries
        """
        return [
            {
                "category": "single_verifier_errors",
                "name": "invalid_email_format",
                "description": "Single verifier with invalid email format",
                "method": "POST",
                "endpoint": "/api/v3/email/single/verifier/",
                "body": {
                    "email": "invalid-email-format",
                    "provider": "truelist"
                },
                "expected_status": [400, 422],
                "validate_response": {
                    "has_field": "detail"
                }
            },
            {
                "category": "single_verifier_errors",
                "name": "missing_email",
                "description": "Single verifier without email field",
                "method": "POST",
                "endpoint": "/api/v3/email/single/verifier/",
                "body": {
                    "provider": "truelist"
                },
                "expected_status": [400, 422],
                "validate_response": {
                    "has_field": "detail"
                }
            }
        ]
    
    @staticmethod
    def get_verifier_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for email verifier endpoint (synchronous).
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "verifier",
                "name": "verify_emails_synchronously",
                "description": "Verify emails synchronously by generating and checking combinations",
                "method": "POST",
                "endpoint": "/api/v3/email/verifier/",
                "body": {
                    "first_name": "John",
                    "last_name": "Doe",
                    "domain": "example.com",
                    "provider": "truelist",
                    "email_count": 1000,
                    "max_retries": 10
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["valid_emails", "total_valid", "generated_emails", "total_generated", "total_batches_processed"]
                }
            },
            {
                "category": "verifier",
                "name": "verify_emails_custom_params",
                "description": "Verify emails with custom email_count and max_retries",
                "method": "POST",
                "endpoint": "/api/v3/email/verifier/",
                "body": {
                    "first_name": "Jane",
                    "last_name": "Smith",
                    "domain": "example.com",
                    "provider": "truelist",
                    "email_count": 500,
                    "max_retries": 5
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["valid_emails", "total_valid"]
                }
            }
        ]
    
    @staticmethod
    def get_verifier_error_scenarios() -> List[Dict[str, Any]]:
        """Get error test scenarios for email verifier endpoint.
        
        Returns:
            List of error test scenario dictionaries
        """
        return [
            {
                "category": "verifier_errors",
                "name": "missing_first_name",
                "description": "Email verifier without first_name",
                "method": "POST",
                "endpoint": "/api/v3/email/verifier/",
                "body": {
                    "last_name": "Doe",
                    "domain": "example.com",
                    "provider": "truelist"
                },
                "expected_status": [400, 422],
                "validate_response": {
                    "has_field": "detail"
                }
            },
            {
                "category": "verifier_errors",
                "name": "missing_domain",
                "description": "Email verifier without domain or website",
                "method": "POST",
                "endpoint": "/api/v3/email/verifier/",
                "body": {
                    "first_name": "John",
                    "last_name": "Doe",
                    "provider": "truelist"
                },
                "expected_status": [400, 422],
                "validate_response": {
                    "has_field": "detail"
                }
            },
            {
                "category": "verifier_errors",
                "name": "invalid_email_count",
                "description": "Email verifier with email_count < 1",
                "method": "POST",
                "endpoint": "/api/v3/email/verifier/",
                "body": {
                    "first_name": "John",
                    "last_name": "Doe",
                    "domain": "example.com",
                    "provider": "truelist",
                    "email_count": 0
                },
                "expected_status": [400, 422],
                "validate_response": {
                    "has_field": "detail"
                }
            },
            {
                "category": "verifier_errors",
                "name": "invalid_max_retries",
                "description": "Email verifier with max_retries < 1",
                "method": "POST",
                "endpoint": "/api/v3/email/verifier/",
                "body": {
                    "first_name": "John",
                    "last_name": "Doe",
                    "domain": "example.com",
                    "provider": "truelist",
                    "max_retries": 0
                },
                "expected_status": [400, 422],
                "validate_response": {
                    "has_field": "detail"
                }
            }
        ]
    
    @staticmethod
    def get_verifier_single_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for email verifier single endpoint (find first valid).
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "verifier_single",
                "name": "find_first_valid_email",
                "description": "Find first valid email by generating and verifying combinations",
                "method": "POST",
                "endpoint": "/api/v3/email/verifier/single/",
                "body": {
                    "first_name": "John",
                    "last_name": "Doe",
                    "domain": "example.com",
                    "provider": "truelist",
                    "email_count": 1000,
                    "max_retries": 10
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["valid_email", "status"]
                }
            },
            {
                "category": "verifier_single",
                "name": "find_first_valid_email_not_found",
                "description": "Find first valid email when none found (returns null)",
                "method": "POST",
                "endpoint": "/api/v3/email/verifier/single/",
                "body": {
                    "first_name": "Nonexistent",
                    "last_name": "Person",
                    "domain": "example.com",
                    "provider": "truelist",
                    "email_count": 100,
                    "max_retries": 1
                },
                "expected_status": [200],
                "validate_response": {
                    "valid_email_is_null": True
                }
            }
        ]
    
    @staticmethod
    def get_verifier_single_error_scenarios() -> List[Dict[str, Any]]:
        """Get error test scenarios for email verifier single endpoint.
        
        Returns:
            List of error test scenario dictionaries
        """
        return [
            {
                "category": "verifier_single_errors",
                "name": "missing_first_name",
                "description": "Email verifier single without first_name",
                "method": "POST",
                "endpoint": "/api/v3/email/verifier/single/",
                "body": {
                    "last_name": "Doe",
                    "domain": "example.com",
                    "provider": "truelist"
                },
                "expected_status": [400, 422],
                "validate_response": {
                    "has_field": "detail"
                }
            },
            {
                "category": "verifier_single_errors",
                "name": "missing_domain",
                "description": "Email verifier single without domain or website",
                "method": "POST",
                "endpoint": "/api/v3/email/verifier/single/",
                "body": {
                    "first_name": "John",
                    "last_name": "Doe",
                    "provider": "truelist"
                },
                "expected_status": [400, 422],
                "validate_response": {
                    "has_field": "detail"
                }
            },
            {
                "category": "verifier_single_errors",
                "name": "invalid_email_count",
                "description": "Email verifier single with email_count < 1",
                "method": "POST",
                "endpoint": "/api/v3/email/verifier/single/",
                "body": {
                    "first_name": "John",
                    "last_name": "Doe",
                    "domain": "example.com",
                    "provider": "truelist",
                    "email_count": 0
                },
                "expected_status": [400, 422],
                "validate_response": {
                    "has_field": "detail"
                }
            }
        ]
    
    @staticmethod
    def get_bulk_download_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for bulk download endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "bulk_download",
                "name": "download_valid_emails",
                "description": "Download valid emails CSV file",
                "method": "GET",
                "endpoint": "/api/v3/email/bulk/download/valid/test-slug-123/",
                "query_params": {
                    "provider": "truelist"
                },
                "expected_status": [200, 404],  # 404 if file not found
                "validate_response": {
                    "content_type": "text/csv"
                }
            },
            {
                "category": "bulk_download",
                "name": "download_invalid_emails",
                "description": "Download invalid emails CSV file",
                "method": "GET",
                "endpoint": "/api/v3/email/bulk/download/invalid/test-slug-123/",
                "query_params": {
                    "provider": "truelist"
                },
                "expected_status": [200, 404],
                "validate_response": {
                    "content_type": "text/csv"
                }
            },
            {
                "category": "bulk_download",
                "name": "download_catchall_emails",
                "description": "Download catchall emails CSV file",
                "method": "GET",
                "endpoint": "/api/v3/email/bulk/download/c-all/test-slug-123/",
                "query_params": {
                    "provider": "truelist"
                },
                "expected_status": [200, 404],
                "validate_response": {
                    "content_type": "text/csv"
                }
            },
            {
                "category": "bulk_download",
                "name": "download_unknown_emails",
                "description": "Download unknown emails CSV file",
                "method": "GET",
                "endpoint": "/api/v3/email/bulk/download/unknown/test-slug-123/",
                "query_params": {
                    "provider": "truelist"
                },
                "expected_status": [200, 404],
                "validate_response": {
                    "content_type": "text/csv"
                }
            },
            {
                "category": "bulk_download",
                "name": "download_truelist",
                "description": "Download CSV from Truelist provider",
                "method": "GET",
                "endpoint": "/api/v3/email/bulk/download/valid/batch-id-123/",
                "query_params": {
                    "provider": "truelist"
                },
                "expected_status": [200, 404],
                "validate_response": {
                    "content_type": "text/csv"
                }
            }
        ]
    
    @staticmethod
    def get_bulk_download_error_scenarios() -> List[Dict[str, Any]]:
        """Get error test scenarios for bulk download endpoint.
        
        Returns:
            List of error test scenario dictionaries
        """
        return [
            {
                "category": "bulk_download_errors",
                "name": "invalid_file_type",
                "description": "Bulk download with invalid file_type",
                "method": "GET",
                "endpoint": "/api/v3/email/bulk/download/invalid-type/test-slug-123/",
                "query_params": {
                    "provider": "truelist"
                },
                "expected_status": [400],
                "validate_response": {
                    "has_field": "detail"
                }
            },
            {
                "category": "bulk_download_errors",
                "name": "unsupported_provider",
                "description": "Bulk download with unsupported provider",
                "method": "GET",
                "endpoint": "/api/v3/email/bulk/download/valid/test-slug-123/",
                "query_params": {
                    "provider": "unsupported-provider"
                },
                "expected_status": [400, 500],
                "validate_response": {
                    "has_field": "detail"
                }
            },
            {
                "category": "bulk_download_errors",
                "name": "missing_provider",
                "description": "Bulk download without provider parameter",
                "method": "GET",
                "endpoint": "/api/v3/email/bulk/download/valid/test-slug-123/",
                "query_params": {},
                "expected_status": [400],
                "validate_response": {
                    "has_field": "detail"
                }
            }
        ]
    
    @staticmethod
    def get_all_scenarios() -> List[Dict[str, Any]]:
        """Get all test scenarios for Email API endpoints.
        
        Returns:
            List of all test scenario dictionaries
        """
        scenarios = []
        scenarios.extend(EmailTestScenarios.get_finder_scenarios())
        scenarios.extend(EmailTestScenarios.get_finder_error_scenarios())
        scenarios.extend(EmailTestScenarios.get_export_scenarios())
        scenarios.extend(EmailTestScenarios.get_export_error_scenarios())
        scenarios.extend(EmailTestScenarios.get_single_email_scenarios())
        scenarios.extend(EmailTestScenarios.get_single_email_error_scenarios())
        scenarios.extend(EmailTestScenarios.get_bulk_verifier_scenarios())
        scenarios.extend(EmailTestScenarios.get_bulk_verifier_error_scenarios())
        scenarios.extend(EmailTestScenarios.get_single_verifier_scenarios())
        scenarios.extend(EmailTestScenarios.get_single_verifier_error_scenarios())
        scenarios.extend(EmailTestScenarios.get_verifier_scenarios())
        scenarios.extend(EmailTestScenarios.get_verifier_error_scenarios())
        scenarios.extend(EmailTestScenarios.get_verifier_single_scenarios())
        scenarios.extend(EmailTestScenarios.get_verifier_single_error_scenarios())
        scenarios.extend(EmailTestScenarios.get_bulk_download_scenarios())
        scenarios.extend(EmailTestScenarios.get_bulk_download_error_scenarios())
        return scenarios

