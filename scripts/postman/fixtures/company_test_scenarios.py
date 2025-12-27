"""Comprehensive test scenarios for Company API endpoints.

This module defines all test scenarios for the Company API,
covering VQL queries, filters, company details, and company contacts.
"""

from typing import Dict, List, Any


class CompanyTestScenarios:
    """Comprehensive test scenarios for Company API endpoints."""
    
    @staticmethod
    def get_query_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for companies query endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "query",
                "name": "query_companies_simple",
                "description": "Query companies with simple filter",
                "method": "POST",
                "endpoint": "/api/v3/companies/query",
                "body": {
                    "filters": {
                        "and": [
                            {
                                "field": "name",
                                "operator": "contains",
                                "value": "Acme"
                            }
                        ]
                    },
                    "limit": 25,
                    "offset": 0
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["results", "meta"]
                }
            },
            {
                "category": "query",
                "name": "query_companies_with_select_columns",
                "description": "Query companies with field selection",
                "method": "POST",
                "endpoint": "/api/v3/companies/query",
                "body": {
                    "filters": {
                        "and": [
                            {
                                "field": "name",
                                "operator": "contains",
                                "value": "Tech"
                            }
                        ]
                    },
                    "select_columns": ["uuid", "name", "employees_count"],
                    "limit": 25
                },
                "expected_status": [200]
            },
            {
                "category": "query",
                "name": "query_companies_with_sorting",
                "description": "Query companies with sorting",
                "method": "POST",
                "endpoint": "/api/v3/companies/query",
                "body": {
                    "filters": {
                        "and": [
                            {
                                "field": "name",
                                "operator": "exists",
                                "value": True
                            }
                        ]
                    },
                    "sort_by": "created_at",
                    "sort_direction": "desc",
                    "limit": 25
                },
                "expected_status": [200]
            },
            {
                "category": "query",
                "name": "query_companies_empty_filters",
                "description": "Query all companies (empty filters)",
                "method": "POST",
                "endpoint": "/api/v3/companies/query",
                "body": {
                    "limit": 25,
                    "offset": 0
                },
                "expected_status": [200]
            },
            {
                "category": "query_errors",
                "name": "query_companies_invalid_vql",
                "description": "Query companies with invalid VQL (missing field)",
                "method": "POST",
                "endpoint": "/api/v3/companies/query",
                "body": {
                    "filters": {
                        "and": [
                            {
                                "operator": "contains",
                                "value": "Acme"
                            }
                        ]
                    }
                },
                "expected_status": [400],
                "validate_response": {
                    "has_field": "detail"
                }
            },
            {
                "category": "query_errors",
                "name": "query_companies_unauthorized",
                "description": "Query companies without authentication (should fail)",
                "method": "POST",
                "endpoint": "/api/v3/companies/query",
                "body": {
                    "limit": 25
                },
                "requires_auth": False,
                "expected_status": [401]
            }
        ]
    
    @staticmethod
    def get_count_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for companies count endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "count",
                "name": "count_companies_with_filters",
                "description": "Count companies with filters",
                "method": "POST",
                "endpoint": "/api/v3/companies/count",
                "body": {
                    "filters": {
                        "and": [
                            {
                                "field": "employees_count",
                                "operator": "gte",
                                "value": 100
                            }
                        ]
                    }
                },
                "expected_status": [200],
                "validate_response": {
                    "has_field": "count"
                }
            },
            {
                "category": "count",
                "name": "count_companies_empty_filters",
                "description": "Count all companies (empty filters)",
                "method": "POST",
                "endpoint": "/api/v3/companies/count",
                "body": {},
                "expected_status": [200]
            },
            {
                "category": "count_errors",
                "name": "count_companies_unauthorized",
                "description": "Count companies without authentication (should fail)",
                "method": "POST",
                "endpoint": "/api/v3/companies/count",
                "body": {},
                "requires_auth": False,
                "expected_status": [401]
            }
        ]
    
    @staticmethod
    def get_filters_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for companies filters endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "filters",
                "name": "get_company_filters",
                "description": "Get available company filters",
                "method": "GET",
                "endpoint": "/api/v3/companies/filters",
                "expected_status": [200],
                "validate_response": {
                    "has_field": "data",
                    "data_is_list": True
                }
            },
            {
                "category": "filters_errors",
                "name": "get_company_filters_unauthorized",
                "description": "Get company filters without authentication (should fail)",
                "method": "GET",
                "endpoint": "/api/v3/companies/filters",
                "requires_auth": False,
                "expected_status": [401]
            }
        ]
    
    @staticmethod
    def get_filter_data_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for companies filter data endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "filter_data",
                "name": "get_company_filter_data_industries",
                "description": "Get company filter data for industries",
                "method": "POST",
                "endpoint": "/api/v3/companies/filters/data",
                "body": {
                    "service": "company",
                    "filter_key": "industries",
                    "page": 1,
                    "limit": 25
                },
                "expected_status": [200],
                "validate_response": {
                    "has_field": "data"
                }
            },
            {
                "category": "filter_data",
                "name": "get_company_filter_data_with_search",
                "description": "Get company filter data with search text",
                "method": "POST",
                "endpoint": "/api/v3/companies/filters/data",
                "body": {
                    "service": "company",
                    "filter_key": "industries",
                    "search_text": "Soft",
                    "page": 1,
                    "limit": 25
                },
                "expected_status": [200]
            },
            {
                "category": "filter_data_errors",
                "name": "get_company_filter_data_invalid_service",
                "description": "Get company filter data with invalid service (should fail)",
                "method": "POST",
                "endpoint": "/api/v3/companies/filters/data",
                "body": {
                    "service": "invalid-service",
                    "filter_key": "industries"
                },
                "expected_status": [400]
            },
            {
                "category": "filter_data_errors",
                "name": "get_company_filter_data_missing_filter_key",
                "description": "Get company filter data with missing filter_key (should fail)",
                "method": "POST",
                "endpoint": "/api/v3/companies/filters/data",
                "body": {
                    "service": "company"
                },
                "expected_status": [422]
            },
            {
                "category": "filter_data_errors",
                "name": "get_company_filter_data_unauthorized",
                "description": "Get company filter data without authentication (should fail)",
                "method": "POST",
                "endpoint": "/api/v3/companies/filters/data",
                "body": {
                    "service": "company",
                    "filter_key": "industries"
                },
                "requires_auth": False,
                "expected_status": [401]
            }
        ]
    
    @staticmethod
    def get_company_detail_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for company detail endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "detail",
                "name": "get_company_by_uuid",
                "description": "Get company details by UUID",
                "method": "GET",
                "endpoint": "/api/v3/companies/{company_uuid}/",
                "path_params": {
                    "company_uuid": "test-uuid"
                },
                "expected_status": [200, 404],  # 404 if company doesn't exist
                "validate_response": {
                    "has_field": "uuid"
                }
            },
            {
                "category": "detail_errors",
                "name": "get_company_invalid_uuid",
                "description": "Get company with invalid UUID (should return 404)",
                "method": "GET",
                "endpoint": "/api/v3/companies/{company_uuid}/",
                "path_params": {
                    "company_uuid": "00000000-0000-0000-0000-000000000000"
                },
                "expected_status": [404]
            },
            {
                "category": "detail_errors",
                "name": "get_company_unauthorized",
                "description": "Get company without authentication (should fail)",
                "method": "GET",
                "endpoint": "/api/v3/companies/{company_uuid}/",
                "path_params": {
                    "company_uuid": "test-uuid"
                },
                "requires_auth": False,
                "expected_status": [401]
            }
        ]
    
    @staticmethod
    def get_company_contacts_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for company contacts endpoints.
        
        Returns:
            List of test scenario dictionaries
        """
        scenarios = []
        
        # List company contacts
        scenarios.extend([
            {
                "category": "company_contacts",
                "name": "list_company_contacts",
                "description": "List contacts for a company",
                "method": "GET",
                "endpoint": "/api/v3/companies/company/{company_uuid}/contacts/",
                "path_params": {
                    "company_uuid": "test-uuid"
                },
                "query_params": {
                    "limit": 25,
                    "offset": 0
                },
                "expected_status": [200, 404],  # 404 if company doesn't exist
                "validate_response": {
                    "has_fields": ["results", "meta"]
                }
            },
            {
                "category": "company_contacts",
                "name": "list_company_contacts_with_filters",
                "description": "List company contacts with filters",
                "method": "GET",
                "endpoint": "/api/v3/companies/company/{company_uuid}/contacts/",
                "path_params": {
                    "company_uuid": "test-uuid"
                },
                "query_params": {
                    "first_name": "John",
                    "title": "engineer",
                    "limit": 25
                },
                "expected_status": [200, 404]
            },
            {
                "category": "company_contacts",
                "name": "count_company_contacts",
                "description": "Count contacts for a company",
                "method": "GET",
                "endpoint": "/api/v3/companies/company/{company_uuid}/contacts/count/",
                "path_params": {
                    "company_uuid": "test-uuid"
                },
                "expected_status": [200, 404],
                "validate_response": {
                    "has_field": "count"
                }
            },
            {
                "category": "company_contacts",
                "name": "get_company_contact_filters",
                "description": "Get filters for company contacts",
                "method": "GET",
                "endpoint": "/api/v3/companies/company/{company_uuid}/contacts/filters",
                "path_params": {
                    "company_uuid": "test-uuid"
                },
                "expected_status": [200, 404],
                "validate_response": {
                    "has_field": "data"
                }
            },
            {
                "category": "company_contacts",
                "name": "get_company_contact_filter_data",
                "description": "Get filter data for company contacts",
                "method": "POST",
                "endpoint": "/api/v3/companies/company/{company_uuid}/contacts/filters/data",
                "path_params": {
                    "company_uuid": "test-uuid"
                },
                "body": {
                    "service": "contact",
                    "filter_key": "departments",
                    "page": 1,
                    "limit": 25
                },
                "expected_status": [200, 404]
            },
            {
                "category": "company_contacts_errors",
                "name": "list_company_contacts_unauthorized",
                "description": "List company contacts without authentication (should fail)",
                "method": "GET",
                "endpoint": "/api/v3/companies/company/{company_uuid}/contacts/",
                "path_params": {
                    "company_uuid": "test-uuid"
                },
                "requires_auth": False,
                "expected_status": [401]
            }
        ])
        
        return scenarios
    
    @staticmethod
    def get_all_scenarios() -> List[Dict[str, Any]]:
        """Get all test scenarios for Company API.
        
        Returns:
            List of all test scenario dictionaries
        """
        scenarios = []
        scenarios.extend(CompanyTestScenarios.get_query_scenarios())
        scenarios.extend(CompanyTestScenarios.get_count_scenarios())
        scenarios.extend(CompanyTestScenarios.get_filters_scenarios())
        scenarios.extend(CompanyTestScenarios.get_filter_data_scenarios())
        scenarios.extend(CompanyTestScenarios.get_company_detail_scenarios())
        scenarios.extend(CompanyTestScenarios.get_company_contacts_scenarios())
        return scenarios

