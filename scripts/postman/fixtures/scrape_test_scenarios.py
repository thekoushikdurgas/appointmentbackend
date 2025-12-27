"""Comprehensive test scenarios for Sales Navigator scraping API endpoints."""

from typing import Dict, Any, List


class ScrapeTestScenarios:
    """Comprehensive test scenarios for Sales Navigator scraping API endpoints."""
    
    @staticmethod
    def get_sample_html() -> str:
        """Get sample Sales Navigator HTML for testing.
        
        Returns:
            Sample HTML string
        """
        return """<html><head><title>Sales Navigator</title></head><body>
            <div class="search-results">
                <div class="profile-card">
                    <div class="profile-name">John Doe</div>
                    <div class="profile-title">Software Engineer</div>
                    <div class="profile-company">Tech Corp</div>
                    <div class="profile-location">San Francisco, CA</div>
                    <div class="connection-degree">3rd</div>
                </div>
                <div class="profile-card">
                    <div class="profile-name">Jane Smith</div>
                    <div class="profile-title">Product Manager</div>
                    <div class="profile-company">Startup Inc</div>
                    <div class="profile-location">New York, NY</div>
                    <div class="connection-degree">2nd</div>
                </div>
            </div>
        </body></html>"""
    
    @staticmethod
    def get_scrape_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for scrape endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "name": "scrape_basic",
                "description": "Basic scrape without saving to database",
                "method": "POST",
                "endpoint": "/api/v3/sales-navigator/scrape",
                "body": {
                    "html": ScrapeTestScenarios.get_sample_html(),
                    "save": False
                },
                "expected_status": [200]
            },
            {
                "name": "scrape_with_save",
                "description": "Scrape with save=true (persists profiles to database)",
                "method": "POST",
                "endpoint": "/api/v3/sales-navigator/scrape",
                "body": {
                    "html": ScrapeTestScenarios.get_sample_html(),
                    "save": True
                },
                "expected_status": [200]
            },
            {
                "name": "scrape_without_save_field",
                "description": "Scrape without save field (defaults to false)",
                "method": "POST",
                "endpoint": "/api/v3/sales-navigator/scrape",
                "body": {
                    "html": ScrapeTestScenarios.get_sample_html()
                },
                "expected_status": [200]
            },
            {
                "name": "scrape_empty_html",
                "description": "Scrape with empty HTML (should fail)",
                "method": "POST",
                "endpoint": "/api/v3/sales-navigator/scrape",
                "body": {
                    "html": "",
                    "save": False
                },
                "expected_status": [422, 400]
            },
            {
                "name": "scrape_whitespace_only_html",
                "description": "Scrape with whitespace-only HTML (should fail)",
                "method": "POST",
                "endpoint": "/api/v3/sales-navigator/scrape",
                "body": {
                    "html": "   \n\t  ",
                    "save": False
                },
                "expected_status": [422, 400]
            },
            {
                "name": "scrape_missing_html",
                "description": "Scrape with missing HTML field (should fail)",
                "method": "POST",
                "endpoint": "/api/v3/sales-navigator/scrape",
                "body": {
                    "save": False
                },
                "expected_status": [422]
            },
            {
                "name": "scrape_invalid_html_type",
                "description": "Scrape with invalid HTML type (not string, should fail)",
                "method": "POST",
                "endpoint": "/api/v3/sales-navigator/scrape",
                "body": {
                    "html": 12345,
                    "save": False
                },
                "expected_status": [422]
            },
            {
                "name": "scrape_invalid_html_structure",
                "description": "Scrape with invalid HTML structure (not Sales Navigator HTML)",
                "method": "POST",
                "endpoint": "/api/v3/sales-navigator/scrape",
                "body": {
                    "html": "This is not valid HTML content",
                    "save": False
                },
                "expected_status": [200, 400, 500]  # May succeed but return empty profiles or fail
            },
            {
                "name": "scrape_large_html",
                "description": "Scrape with large HTML content (multiple profiles)",
                "method": "POST",
                "endpoint": "/api/v3/sales-navigator/scrape",
                "body": {
                    "html": ScrapeTestScenarios.get_sample_html() * 10,  # Simulate larger HTML
                    "save": False
                },
                "expected_status": [200]
            }
        ]
    
    @staticmethod
    def get_list_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for list scraping records endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "name": "list_scraping_records",
                "description": "List user scraping records with default pagination",
                "method": "GET",
                "endpoint": "/api/v1/users/sales-navigator/list",
                "query_params": {},
                "expected_status": [200]
            },
            {
                "name": "list_scraping_records_with_limit",
                "description": "List user scraping records with custom limit",
                "method": "GET",
                "endpoint": "/api/v1/users/sales-navigator/list",
                "query_params": {
                    "limit": 50
                },
                "expected_status": [200]
            },
            {
                "name": "list_scraping_records_with_pagination",
                "description": "List user scraping records with pagination",
                "method": "GET",
                "endpoint": "/api/v1/users/sales-navigator/list",
                "query_params": {
                    "limit": 25,
                    "offset": 0
                },
                "expected_status": [200]
            },
            {
                "name": "list_scraping_records_second_page",
                "description": "List user scraping records (second page)",
                "method": "GET",
                "endpoint": "/api/v1/users/sales-navigator/list",
                "query_params": {
                    "limit": 25,
                    "offset": 25
                },
                "expected_status": [200]
            }
        ]
    
    @staticmethod
    def get_all_scenarios() -> Dict[str, List[Dict[str, Any]]]:
        """Get all test scenarios organized by category.
        
        Returns:
            Dictionary mapping category to list of scenarios
        """
        return {
            "scrape": ScrapeTestScenarios.get_scrape_scenarios(),
            "list_records": ScrapeTestScenarios.get_list_scenarios()
        }


from typing import Dict, Any, List


class ScrapeTestScenarios:
    """Comprehensive test scenarios for Sales Navigator scraping API endpoints."""
    
    @staticmethod
    def get_sample_html() -> str:
        """Get sample Sales Navigator HTML for testing.
        
        Returns:
            Sample HTML string
        """
        return """<html><head><title>Sales Navigator</title></head><body>
            <div class="search-results">
                <div class="profile-card">
                    <div class="profile-name">John Doe</div>
                    <div class="profile-title">Software Engineer</div>
                    <div class="profile-company">Tech Corp</div>
                    <div class="profile-location">San Francisco, CA</div>
                    <div class="connection-degree">3rd</div>
                </div>
                <div class="profile-card">
                    <div class="profile-name">Jane Smith</div>
                    <div class="profile-title">Product Manager</div>
                    <div class="profile-company">Startup Inc</div>
                    <div class="profile-location">New York, NY</div>
                    <div class="connection-degree">2nd</div>
                </div>
            </div>
        </body></html>"""
    
    @staticmethod
    def get_scrape_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for scrape endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "name": "scrape_basic",
                "description": "Basic scrape without saving to database",
                "method": "POST",
                "endpoint": "/api/v3/sales-navigator/scrape",
                "body": {
                    "html": ScrapeTestScenarios.get_sample_html(),
                    "save": False
                },
                "expected_status": [200]
            },
            {
                "name": "scrape_with_save",
                "description": "Scrape with save=true (persists profiles to database)",
                "method": "POST",
                "endpoint": "/api/v3/sales-navigator/scrape",
                "body": {
                    "html": ScrapeTestScenarios.get_sample_html(),
                    "save": True
                },
                "expected_status": [200]
            },
            {
                "name": "scrape_without_save_field",
                "description": "Scrape without save field (defaults to false)",
                "method": "POST",
                "endpoint": "/api/v3/sales-navigator/scrape",
                "body": {
                    "html": ScrapeTestScenarios.get_sample_html()
                },
                "expected_status": [200]
            },
            {
                "name": "scrape_empty_html",
                "description": "Scrape with empty HTML (should fail)",
                "method": "POST",
                "endpoint": "/api/v3/sales-navigator/scrape",
                "body": {
                    "html": "",
                    "save": False
                },
                "expected_status": [422, 400]
            },
            {
                "name": "scrape_whitespace_only_html",
                "description": "Scrape with whitespace-only HTML (should fail)",
                "method": "POST",
                "endpoint": "/api/v3/sales-navigator/scrape",
                "body": {
                    "html": "   \n\t  ",
                    "save": False
                },
                "expected_status": [422, 400]
            },
            {
                "name": "scrape_missing_html",
                "description": "Scrape with missing HTML field (should fail)",
                "method": "POST",
                "endpoint": "/api/v3/sales-navigator/scrape",
                "body": {
                    "save": False
                },
                "expected_status": [422]
            },
            {
                "name": "scrape_invalid_html_type",
                "description": "Scrape with invalid HTML type (not string, should fail)",
                "method": "POST",
                "endpoint": "/api/v3/sales-navigator/scrape",
                "body": {
                    "html": 12345,
                    "save": False
                },
                "expected_status": [422]
            },
            {
                "name": "scrape_invalid_html_structure",
                "description": "Scrape with invalid HTML structure (not Sales Navigator HTML)",
                "method": "POST",
                "endpoint": "/api/v3/sales-navigator/scrape",
                "body": {
                    "html": "This is not valid HTML content",
                    "save": False
                },
                "expected_status": [200, 400, 500]  # May succeed but return empty profiles or fail
            },
            {
                "name": "scrape_large_html",
                "description": "Scrape with large HTML content (multiple profiles)",
                "method": "POST",
                "endpoint": "/api/v3/sales-navigator/scrape",
                "body": {
                    "html": ScrapeTestScenarios.get_sample_html() * 10,  # Simulate larger HTML
                    "save": False
                },
                "expected_status": [200]
            }
        ]
    
    @staticmethod
    def get_list_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for list scraping records endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "name": "list_scraping_records",
                "description": "List user scraping records with default pagination",
                "method": "GET",
                "endpoint": "/api/v1/users/sales-navigator/list",
                "query_params": {},
                "expected_status": [200]
            },
            {
                "name": "list_scraping_records_with_limit",
                "description": "List user scraping records with custom limit",
                "method": "GET",
                "endpoint": "/api/v1/users/sales-navigator/list",
                "query_params": {
                    "limit": 50
                },
                "expected_status": [200]
            },
            {
                "name": "list_scraping_records_with_pagination",
                "description": "List user scraping records with pagination",
                "method": "GET",
                "endpoint": "/api/v1/users/sales-navigator/list",
                "query_params": {
                    "limit": 25,
                    "offset": 0
                },
                "expected_status": [200]
            },
            {
                "name": "list_scraping_records_second_page",
                "description": "List user scraping records (second page)",
                "method": "GET",
                "endpoint": "/api/v1/users/sales-navigator/list",
                "query_params": {
                    "limit": 25,
                    "offset": 25
                },
                "expected_status": [200]
            }
        ]
    
    @staticmethod
    def get_all_scenarios() -> Dict[str, List[Dict[str, Any]]]:
        """Get all test scenarios organized by category.
        
        Returns:
            Dictionary mapping category to list of scenarios
        """
        return {
            "scrape": ScrapeTestScenarios.get_scrape_scenarios(),
            "list_records": ScrapeTestScenarios.get_list_scenarios()
        }


from typing import Dict, Any, List


class ScrapeTestScenarios:
    """Comprehensive test scenarios for Sales Navigator scraping API endpoints."""
    
    @staticmethod
    def get_sample_html() -> str:
        """Get sample Sales Navigator HTML for testing.
        
        Returns:
            Sample HTML string
        """
        return """<html><head><title>Sales Navigator</title></head><body>
            <div class="search-results">
                <div class="profile-card">
                    <div class="profile-name">John Doe</div>
                    <div class="profile-title">Software Engineer</div>
                    <div class="profile-company">Tech Corp</div>
                    <div class="profile-location">San Francisco, CA</div>
                    <div class="connection-degree">3rd</div>
                </div>
                <div class="profile-card">
                    <div class="profile-name">Jane Smith</div>
                    <div class="profile-title">Product Manager</div>
                    <div class="profile-company">Startup Inc</div>
                    <div class="profile-location">New York, NY</div>
                    <div class="connection-degree">2nd</div>
                </div>
            </div>
        </body></html>"""
    
    @staticmethod
    def get_scrape_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for scrape endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "name": "scrape_basic",
                "description": "Basic scrape without saving to database",
                "method": "POST",
                "endpoint": "/api/v3/sales-navigator/scrape",
                "body": {
                    "html": ScrapeTestScenarios.get_sample_html(),
                    "save": False
                },
                "expected_status": [200]
            },
            {
                "name": "scrape_with_save",
                "description": "Scrape with save=true (persists profiles to database)",
                "method": "POST",
                "endpoint": "/api/v3/sales-navigator/scrape",
                "body": {
                    "html": ScrapeTestScenarios.get_sample_html(),
                    "save": True
                },
                "expected_status": [200]
            },
            {
                "name": "scrape_without_save_field",
                "description": "Scrape without save field (defaults to false)",
                "method": "POST",
                "endpoint": "/api/v3/sales-navigator/scrape",
                "body": {
                    "html": ScrapeTestScenarios.get_sample_html()
                },
                "expected_status": [200]
            },
            {
                "name": "scrape_empty_html",
                "description": "Scrape with empty HTML (should fail)",
                "method": "POST",
                "endpoint": "/api/v3/sales-navigator/scrape",
                "body": {
                    "html": "",
                    "save": False
                },
                "expected_status": [422, 400]
            },
            {
                "name": "scrape_whitespace_only_html",
                "description": "Scrape with whitespace-only HTML (should fail)",
                "method": "POST",
                "endpoint": "/api/v3/sales-navigator/scrape",
                "body": {
                    "html": "   \n\t  ",
                    "save": False
                },
                "expected_status": [422, 400]
            },
            {
                "name": "scrape_missing_html",
                "description": "Scrape with missing HTML field (should fail)",
                "method": "POST",
                "endpoint": "/api/v3/sales-navigator/scrape",
                "body": {
                    "save": False
                },
                "expected_status": [422]
            },
            {
                "name": "scrape_invalid_html_type",
                "description": "Scrape with invalid HTML type (not string, should fail)",
                "method": "POST",
                "endpoint": "/api/v3/sales-navigator/scrape",
                "body": {
                    "html": 12345,
                    "save": False
                },
                "expected_status": [422]
            },
            {
                "name": "scrape_invalid_html_structure",
                "description": "Scrape with invalid HTML structure (not Sales Navigator HTML)",
                "method": "POST",
                "endpoint": "/api/v3/sales-navigator/scrape",
                "body": {
                    "html": "This is not valid HTML content",
                    "save": False
                },
                "expected_status": [200, 400, 500]  # May succeed but return empty profiles or fail
            },
            {
                "name": "scrape_large_html",
                "description": "Scrape with large HTML content (multiple profiles)",
                "method": "POST",
                "endpoint": "/api/v3/sales-navigator/scrape",
                "body": {
                    "html": ScrapeTestScenarios.get_sample_html() * 10,  # Simulate larger HTML
                    "save": False
                },
                "expected_status": [200]
            }
        ]
    
    @staticmethod
    def get_list_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for list scraping records endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "name": "list_scraping_records",
                "description": "List user scraping records with default pagination",
                "method": "GET",
                "endpoint": "/api/v1/users/sales-navigator/list",
                "query_params": {},
                "expected_status": [200]
            },
            {
                "name": "list_scraping_records_with_limit",
                "description": "List user scraping records with custom limit",
                "method": "GET",
                "endpoint": "/api/v1/users/sales-navigator/list",
                "query_params": {
                    "limit": 50
                },
                "expected_status": [200]
            },
            {
                "name": "list_scraping_records_with_pagination",
                "description": "List user scraping records with pagination",
                "method": "GET",
                "endpoint": "/api/v1/users/sales-navigator/list",
                "query_params": {
                    "limit": 25,
                    "offset": 0
                },
                "expected_status": [200]
            },
            {
                "name": "list_scraping_records_second_page",
                "description": "List user scraping records (second page)",
                "method": "GET",
                "endpoint": "/api/v1/users/sales-navigator/list",
                "query_params": {
                    "limit": 25,
                    "offset": 25
                },
                "expected_status": [200]
            }
        ]
    
    @staticmethod
    def get_all_scenarios() -> Dict[str, List[Dict[str, Any]]]:
        """Get all test scenarios organized by category.
        
        Returns:
            Dictionary mapping category to list of scenarios
        """
        return {
            "scrape": ScrapeTestScenarios.get_scrape_scenarios(),
            "list_records": ScrapeTestScenarios.get_list_scenarios()
        }


from typing import Dict, Any, List


class ScrapeTestScenarios:
    """Comprehensive test scenarios for Sales Navigator scraping API endpoints."""
    
    @staticmethod
    def get_sample_html() -> str:
        """Get sample Sales Navigator HTML for testing.
        
        Returns:
            Sample HTML string
        """
        return """<html><head><title>Sales Navigator</title></head><body>
            <div class="search-results">
                <div class="profile-card">
                    <div class="profile-name">John Doe</div>
                    <div class="profile-title">Software Engineer</div>
                    <div class="profile-company">Tech Corp</div>
                    <div class="profile-location">San Francisco, CA</div>
                    <div class="connection-degree">3rd</div>
                </div>
                <div class="profile-card">
                    <div class="profile-name">Jane Smith</div>
                    <div class="profile-title">Product Manager</div>
                    <div class="profile-company">Startup Inc</div>
                    <div class="profile-location">New York, NY</div>
                    <div class="connection-degree">2nd</div>
                </div>
            </div>
        </body></html>"""
    
    @staticmethod
    def get_scrape_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for scrape endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "name": "scrape_basic",
                "description": "Basic scrape without saving to database",
                "method": "POST",
                "endpoint": "/api/v3/sales-navigator/scrape",
                "body": {
                    "html": ScrapeTestScenarios.get_sample_html(),
                    "save": False
                },
                "expected_status": [200]
            },
            {
                "name": "scrape_with_save",
                "description": "Scrape with save=true (persists profiles to database)",
                "method": "POST",
                "endpoint": "/api/v3/sales-navigator/scrape",
                "body": {
                    "html": ScrapeTestScenarios.get_sample_html(),
                    "save": True
                },
                "expected_status": [200]
            },
            {
                "name": "scrape_without_save_field",
                "description": "Scrape without save field (defaults to false)",
                "method": "POST",
                "endpoint": "/api/v3/sales-navigator/scrape",
                "body": {
                    "html": ScrapeTestScenarios.get_sample_html()
                },
                "expected_status": [200]
            },
            {
                "name": "scrape_empty_html",
                "description": "Scrape with empty HTML (should fail)",
                "method": "POST",
                "endpoint": "/api/v3/sales-navigator/scrape",
                "body": {
                    "html": "",
                    "save": False
                },
                "expected_status": [422, 400]
            },
            {
                "name": "scrape_whitespace_only_html",
                "description": "Scrape with whitespace-only HTML (should fail)",
                "method": "POST",
                "endpoint": "/api/v3/sales-navigator/scrape",
                "body": {
                    "html": "   \n\t  ",
                    "save": False
                },
                "expected_status": [422, 400]
            },
            {
                "name": "scrape_missing_html",
                "description": "Scrape with missing HTML field (should fail)",
                "method": "POST",
                "endpoint": "/api/v3/sales-navigator/scrape",
                "body": {
                    "save": False
                },
                "expected_status": [422]
            },
            {
                "name": "scrape_invalid_html_type",
                "description": "Scrape with invalid HTML type (not string, should fail)",
                "method": "POST",
                "endpoint": "/api/v3/sales-navigator/scrape",
                "body": {
                    "html": 12345,
                    "save": False
                },
                "expected_status": [422]
            },
            {
                "name": "scrape_invalid_html_structure",
                "description": "Scrape with invalid HTML structure (not Sales Navigator HTML)",
                "method": "POST",
                "endpoint": "/api/v3/sales-navigator/scrape",
                "body": {
                    "html": "This is not valid HTML content",
                    "save": False
                },
                "expected_status": [200, 400, 500]  # May succeed but return empty profiles or fail
            },
            {
                "name": "scrape_large_html",
                "description": "Scrape with large HTML content (multiple profiles)",
                "method": "POST",
                "endpoint": "/api/v3/sales-navigator/scrape",
                "body": {
                    "html": ScrapeTestScenarios.get_sample_html() * 10,  # Simulate larger HTML
                    "save": False
                },
                "expected_status": [200]
            }
        ]
    
    @staticmethod
    def get_list_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for list scraping records endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "name": "list_scraping_records",
                "description": "List user scraping records with default pagination",
                "method": "GET",
                "endpoint": "/api/v1/users/sales-navigator/list",
                "query_params": {},
                "expected_status": [200]
            },
            {
                "name": "list_scraping_records_with_limit",
                "description": "List user scraping records with custom limit",
                "method": "GET",
                "endpoint": "/api/v1/users/sales-navigator/list",
                "query_params": {
                    "limit": 50
                },
                "expected_status": [200]
            },
            {
                "name": "list_scraping_records_with_pagination",
                "description": "List user scraping records with pagination",
                "method": "GET",
                "endpoint": "/api/v1/users/sales-navigator/list",
                "query_params": {
                    "limit": 25,
                    "offset": 0
                },
                "expected_status": [200]
            },
            {
                "name": "list_scraping_records_second_page",
                "description": "List user scraping records (second page)",
                "method": "GET",
                "endpoint": "/api/v1/users/sales-navigator/list",
                "query_params": {
                    "limit": 25,
                    "offset": 25
                },
                "expected_status": [200]
            }
        ]
    
    @staticmethod
    def get_all_scenarios() -> Dict[str, List[Dict[str, Any]]]:
        """Get all test scenarios organized by category.
        
        Returns:
            Dictionary mapping category to list of scenarios
        """
        return {
            "scrape": ScrapeTestScenarios.get_scrape_scenarios(),
            "list_records": ScrapeTestScenarios.get_list_scenarios()
        }

