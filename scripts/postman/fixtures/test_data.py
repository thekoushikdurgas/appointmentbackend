"""Test data fixtures for API testing."""

import json
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List
import requests
from ..tests.config import TestConfig
from ..tests.auth import AuthHandler


class TestDataFixtures:
    """Manage test data lifecycle for API testing."""
    
    def __init__(self, config: TestConfig, auth_handler: AuthHandler):
        """Initialize test data fixtures.
        
        Args:
            config: Test configuration
            auth_handler: Authentication handler
        """
        self.config = config
        self.auth_handler = auth_handler
        self.base_url = config.base_url
        self.fixtures_file = config.output_dir / "test_fixtures.json"
        self._fixtures: Dict[str, Any] = {}
        self._load_fixtures()
    
    def _load_fixtures(self):
        """Load existing fixtures from file."""
        if self.fixtures_file.exists():
            try:
                with open(self.fixtures_file, 'r') as f:
                    self._fixtures = json.load(f)
            except Exception as e:
                print(f"Warning: Could not load fixtures: {e}")
                self._fixtures = {}
        else:
            self._fixtures = {
                "chat_ids": [],
                "company_uuids": [],
                "contact_uuids": [],
                "export_ids": [],
                "page_ids": [],
            }
    
    def _save_fixtures(self):
        """Save fixtures to file."""
        try:
            with open(self.fixtures_file, 'w') as f:
                json.dump(self._fixtures, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save fixtures: {e}")
    
    def create_test_chat(self) -> Optional[str]:
        """Create a test AI chat and return chat_id.
        
        Returns:
            Chat ID string or None if creation failed
        """
        try:
            # Normalize base_url (remove trailing slash)
            base_url = self.base_url.rstrip('/')
            url = f"{base_url}/api/v2/ai-chats/"
            headers = self.auth_handler.get_auth_headers("v2", "POST", "/api/v2/ai-chats/")
            
            # Create chat with minimal data
            payload = {
                "title": f"Test Chat {uuid.uuid4().hex[:8]}",
            }
            
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.config.timeout
            )
            
            if response.status_code == 201:
                data = response.json()
                chat_id = data.get("chat_id") or data.get("uuid") or data.get("id")
                if chat_id:
                    if "chat_ids" not in self._fixtures:
                        self._fixtures["chat_ids"] = []
                    self._fixtures["chat_ids"].append(chat_id)
                    self._save_fixtures()
                    return str(chat_id)
            
            return None
        except Exception as e:
            print(f"Failed to create test chat: {e}")
            return None
    
    def get_test_chat_id(self) -> Optional[str]:
        """Get an existing test chat ID or create a new one.
        
        Returns:
            Chat ID string or None
        """
        # Try to get existing chat ID
        if self._fixtures.get("chat_ids"):
            return self._fixtures["chat_ids"][0]
        
        # Create new chat
        return self.create_test_chat()
    
    def create_test_company(self) -> Optional[str]:
        """Create test company via Connectra and return UUID.
        
        Note: This requires Connectra API access. For now, returns a placeholder.
        
        Returns:
            Company UUID string or None
        """
        # TODO: Implement actual company creation via Connectra API
        # For now, return None and tests will use placeholder UUIDs
        return None
    
    def get_test_company_uuid(self) -> Optional[str]:
        """Get an existing test company UUID or create a new one.
        
        Returns:
            Company UUID string or None
        """
        # Try to get existing UUID
        if self._fixtures.get("company_uuids"):
            return self._fixtures["company_uuids"][0]
        
        # Try to create new company
        uuid_str = self.create_test_company()
        if uuid_str:
            return uuid_str
        
        # Return a placeholder UUID format (tests will handle 404 appropriately)
        return None
    
    def create_test_contact(self) -> Optional[str]:
        """Create test contact via Connectra and return UUID.
        
        Note: This requires Connectra API access. For now, returns a placeholder.
        
        Returns:
            Contact UUID string or None
        """
        # TODO: Implement actual contact creation via Connectra API
        # For now, return None and tests will use placeholder UUIDs
        return None
    
    def get_test_contact_uuid(self) -> Optional[str]:
        """Get an existing test contact UUID or create a new one.
        
        Returns:
            Contact UUID string or None
        """
        # Try to get existing UUID
        if self._fixtures.get("contact_uuids"):
            return self._fixtures["contact_uuids"][0]
        
        # Try to create new contact
        uuid_str = self.create_test_contact()
        if uuid_str:
            return uuid_str
        
        # Return a placeholder UUID format (tests will handle 404 appropriately)
        return None
    
    def get_test_export_id(self) -> Optional[str]:
        """Get a test export ID.
        
        Returns:
            Export ID string or None
        """
        # Try to get existing export ID
        if self._fixtures.get("export_ids"):
            return self._fixtures["export_ids"][0]
        
        # For now, return None (tests will handle 404 appropriately)
        return None
    
    def get_test_page_id(self) -> Optional[str]:
        """Get a test page ID for dashboard/marketing pages.
        
        Returns:
            Page ID string or None
        """
        # Try to get existing page ID
        if self._fixtures.get("page_ids"):
            return self._fixtures["page_ids"][0]
        
        # For now, return None (tests will handle 404 appropriately)
        return None
    
    def get_test_user_id(self) -> Optional[str]:
        """Get a test user ID (UUID) for super admin operations.
        
        Returns:
            User UUID string or None
        """
        # Try to get existing user ID
        if self._fixtures.get("user_ids"):
            return self._fixtures["user_ids"][0]
        
        # Return None (tests will handle 404 appropriately)
        return None
    
    def create_test_user_registration_data(self, with_geolocation: bool = True) -> Dict[str, Any]:
        """Generate test user registration data.
        
        Args:
            with_geolocation: Whether to include geolocation data
            
        Returns:
            Dictionary with registration data
        """
        unique_id = uuid.uuid4().hex[:8]
        data = {
            "name": f"Test User {unique_id}",
            "email": f"testuser_{unique_id}@example.com",
            "password": "testpass123",  # 12 chars, within 8-72 limit
        }
        
        if with_geolocation:
            data["geolocation"] = {
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
        
        return data
    
    def create_test_user_login_data(self, email: Optional[str] = None, with_geolocation: bool = True) -> Dict[str, Any]:
        """Generate test user login data.
        
        Args:
            email: User email (default: test email)
            with_geolocation: Whether to include geolocation data
            
        Returns:
            Dictionary with login data
        """
        data = {
            "email": email or "test@example.com",
            "password": "testpass123",
        }
        
        if with_geolocation:
            data["geolocation"] = {
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
        
        return data
    
    def create_test_profile_update_data(self, partial: bool = False) -> Dict[str, Any]:
        """Generate test profile update data.
        
        Args:
            partial: If True, only include some fields (partial update)
            
        Returns:
            Dictionary with profile update data
        """
        if partial:
            return {
                "name": "Updated Name",
                "job_title": "Senior Engineer"
            }
        
        return {
            "name": "Updated Full Name",
            "job_title": "Senior Software Engineer",
            "bio": "Updated bio with more details about the user",
            "timezone": "America/New_York",
            "avatar_url": "https://picsum.photos/seed/123/40/40",
            "notifications": {
                "weeklyReports": False,
                "newLeadAlerts": True
            },
            "role": "ProUser"  # Note: This may be restricted in actual API
        }
    
    def create_test_role_update_data(self, role: str = "ProUser") -> Dict[str, Any]:
        """Generate test role update data.
        
        Args:
            role: Role to set (SuperAdmin, Admin, FreeUser, ProUser)
            
        Returns:
            Dictionary with role update data
        """
        return {
            "role": role
        }
    
    def create_test_credits_update_data(self, credits: int = 1000) -> Dict[str, Any]:
        """Generate test credits update data.
        
        Args:
            credits: Credit amount (must be >= 0)
            
        Returns:
            Dictionary with credits update data
        """
        return {
            "credits": max(0, credits)  # Ensure non-negative
        }
    
    def create_test_avatar_file_data(self) -> Dict[str, Any]:
        """Generate test avatar file upload data.
        
        Returns:
            Dictionary with file upload info (for multipart/form-data)
        """
        # This is a placeholder - actual file upload would need a real file
        return {
            "field_name": "avatar",
            "file_name": "test_avatar.jpg",
            "file_type": "image/jpeg",
            "file_size": 50000,  # 50KB, under 5MB limit
            "note": "Actual file upload requires binary file data"
        }
    
    def create_invalid_password_data(self, length: int = 7) -> str:
        """Generate invalid password (too short).
        
        Args:
            length: Password length (default: 7, below minimum of 8)
            
        Returns:
            Password string
        """
        return "a" * length
    
    def create_long_password_data(self, length: int = 73) -> str:
        """Generate password that's too long (>72 chars).
        
        Args:
            length: Password length (default: 73, above maximum of 72)
            
        Returns:
            Password string
        """
        return "a" * length
    
    def create_invalid_email_data(self) -> str:
        """Generate invalid email format.
        
        Returns:
            Invalid email string
        """
        return "not-an-email"
    
    def create_test_user_history_query_params(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Generate query parameters for user history endpoint.
        
        Args:
            user_id: User ID (UUID format, optional)
            event_type: Event type filter (registration, login, optional)
            limit: Maximum records to return
            offset: Number of records to skip
            
        Returns:
            Dictionary with query parameters
        """
        params = {
            "limit": limit,
            "offset": offset
        }
        
        if user_id:
            params["user_id"] = user_id
        
        if event_type:
            params["event_type"] = event_type
        
        return params
    
    def create_test_user_list_query_params(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """Generate query parameters for user list endpoint.
        
        Args:
            limit: Maximum users to return
            offset: Number of users to skip
            
        Returns:
            Dictionary with query parameters
        """
        return {
            "limit": limit,
            "offset": offset
        }
    
    def create_test_sales_navigator_list_query_params(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """Generate query parameters for sales navigator list endpoint.
        
        Args:
            limit: Maximum records to return
            offset: Number of records to skip
            
        Returns:
            Dictionary with query parameters
        """
        return {
            "limit": limit,
            "offset": offset
        }
    
    def create_test_track_usage_data(self, feature: str = "EMAIL_FINDER", amount: int = 1) -> Dict[str, Any]:
        """Generate test track usage data.
        
        Args:
            feature: Feature name (default: EMAIL_FINDER)
            amount: Amount to increment (default: 1, min: 1)
            
        Returns:
            Dictionary with track usage data
        """
        return {
            "feature": feature,
            "amount": max(1, amount)  # Ensure at least 1
        }
    
    def create_test_reset_usage_data(self, feature: str = "EMAIL_FINDER") -> Dict[str, Any]:
        """Generate test reset usage data.
        
        Args:
            feature: Feature name to reset (default: EMAIL_FINDER)
            
        Returns:
            Dictionary with reset usage data
        """
        return {
            "feature": feature
        }
    
    def get_valid_feature_names(self) -> List[str]:
        """Get list of valid feature names.
        
        Returns:
            List of valid feature name strings
        """
        return [
            "AI_CHAT",
            "BULK_EXPORT",
            "API_KEYS",
            "TEAM_MANAGEMENT",
            "EMAIL_FINDER",
            "VERIFIER",
            "LINKEDIN",
            "DATA_SEARCH",
            "ADVANCED_FILTERS",
            "AI_SUMMARIES",
            "SAVE_SEARCHES",
            "BULK_VERIFICATION"
        ]
    
    def create_invalid_feature_name(self) -> str:
        """Generate invalid feature name for testing.
        
        Returns:
            Invalid feature name string
        """
        return "INVALID_FEATURE"
    
    def create_invalid_amount_data(self, amount: int = 0) -> int:
        """Generate invalid amount (<= 0) for testing.
        
        Args:
            amount: Amount value (default: 0, invalid)
            
        Returns:
            Invalid amount value
        """
        return amount
    
    def create_test_sales_navigator_scrape_data(self, save: bool = False) -> Dict[str, Any]:
        """Generate test Sales Navigator scrape data.
        
        Args:
            save: Whether to save profiles to database (default: False)
            
        Returns:
            Dictionary with scrape request data
        """
        # Create minimal valid HTML that looks like Sales Navigator structure
        # This is a simplified version - real HTML would be much larger
        sample_html = """<html><head><title>Sales Navigator</title></head><body>
            <div class="search-results">
                <div class="profile-card">
                    <div class="profile-name">John Doe</div>
                    <div class="profile-title">Software Engineer</div>
                    <div class="profile-company">Tech Corp</div>
                </div>
            </div>
        </body></html>"""
        
        return {
            "html": sample_html,
            "save": save
        }
    
    def create_test_sales_navigator_scrape_data_with_save(self) -> Dict[str, Any]:
        """Generate test Sales Navigator scrape data with save=true.
        
        Returns:
            Dictionary with scrape request data (save=true)
        """
        return self.create_test_sales_navigator_scrape_data(save=True)
    
    def create_empty_html_data(self) -> Dict[str, Any]:
        """Generate scrape data with empty HTML (should fail).
        
        Returns:
            Dictionary with empty HTML
        """
        return {
            "html": "",
            "save": False
        }
    
    def create_whitespace_only_html_data(self) -> Dict[str, Any]:
        """Generate scrape data with whitespace-only HTML (should fail).
        
        Returns:
            Dictionary with whitespace-only HTML
        """
        return {
            "html": "   \n\t  ",
            "save": False
        }
    
    def create_invalid_html_data(self) -> Dict[str, Any]:
        """Generate scrape data with invalid HTML structure.
        
        Returns:
            Dictionary with invalid HTML
        """
        return {
            "html": "This is not valid HTML content",
            "save": False
        }
    
    def create_test_s3_list_query_params(self, prefix: Optional[str] = None) -> Dict[str, Any]:
        """Generate query parameters for S3 file list endpoint.
        
        Args:
            prefix: Optional prefix to filter files by path
            
        Returns:
            Dictionary with query parameters
        """
        params = {}
        if prefix:
            params["prefix"] = prefix
        return params
    
    def create_test_s3_file_download_params(self) -> Dict[str, Any]:
        """Generate query parameters for S3 file download (no pagination).
        
        Returns:
            Empty dictionary (no query params for download mode)
        """
        return {}
    
    def create_test_s3_file_pagination_params(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """Generate query parameters for S3 file pagination mode.
        
        Args:
            limit: Maximum number of rows to return (min: 1, max: 1000)
            offset: Number of rows to skip (min: 0)
            
        Returns:
            Dictionary with pagination query parameters
        """
        return {
            "limit": max(1, min(1000, limit)),  # Ensure within valid range
            "offset": max(0, offset)  # Ensure non-negative
        }
    
    def create_test_s3_file_id(self) -> str:
        """Generate test S3 file ID (object key).
        
        Returns:
            S3 object key string (e.g., "data/contacts_2024.csv")
        """
        return "data/contacts_2024.csv"
    
    def create_invalid_s3_file_id(self) -> str:
        """Generate invalid S3 file ID for testing 404 errors.
        
        Returns:
            Invalid file ID string
        """
        return "nonexistent/file.csv"
    
    def create_invalid_pagination_params(self) -> Dict[str, Any]:
        """Generate invalid pagination parameters for testing validation errors.
        
        Returns:
            Dictionary with invalid pagination params
        """
        return {
            "limit": 2000,  # Exceeds max of 1000
            "offset": -10  # Negative offset
        }
    
    def create_test_root_metadata_query_params(self) -> Dict[str, Any]:
        """Generate query parameters for root metadata endpoint.
        
        Returns:
            Empty dictionary (RootFilterParams are typically unused)
        """
        return {}
    
    def create_test_root_health_query_params(self) -> Dict[str, Any]:
        """Generate query parameters for root health endpoint.
        
        Returns:
            Empty dictionary (RootFilterParams are typically unused)
        """
        return {}
    
    def create_test_marketing_page_id(self) -> str:
        """Generate test marketing page ID.
        
        Returns:
            Page ID string (e.g., "example-page")
        """
        return "example-page"
    
    def create_test_marketing_page_create_data(self) -> Dict[str, Any]:
        """Generate test data for creating a marketing page.
        
        Returns:
            Dictionary with marketing page creation data
        """
        return {
            "page_id": "test-page",
            "metadata": {
                "title": "Test Page",
                "description": "Test page description",
                "keywords": ["test", "page"],
                "status": "draft",
                "version": 1
            },
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
        }
    
    def create_test_marketing_page_update_data(self) -> Dict[str, Any]:
        """Generate test data for updating a marketing page (partial update).
        
        Returns:
            Dictionary with marketing page update data
        """
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
    
    def create_test_marketing_list_query_params(self, include_drafts: bool = False, include_deleted: bool = False) -> Dict[str, Any]:
        """Generate query parameters for marketing page list endpoint.
        
        Args:
            include_drafts: Include draft pages (admin endpoint only)
            include_deleted: Include deleted pages (admin endpoint only)
            
        Returns:
            Dictionary with query parameters
        """
        params = {}
        if include_drafts:
            params["include_drafts"] = True
        if include_deleted:
            params["include_deleted"] = True
        return params
    
    def create_test_marketing_delete_query_params(self, hard_delete: bool = False) -> Dict[str, Any]:
        """Generate query parameters for marketing page delete endpoint.
        
        Args:
            hard_delete: Permanently delete instead of soft delete
            
        Returns:
            Dictionary with query parameters
        """
        params = {}
        if hard_delete:
            params["hard_delete"] = True
        return params
    
    def create_invalid_marketing_page_id(self) -> str:
        """Generate invalid marketing page ID for testing 404 errors.
        
        Returns:
            Invalid page ID string
        """
        return "non-existent-page"
    
    def create_test_marketing_page_create_minimal_data(self) -> Dict[str, Any]:
        """Generate minimal test data for creating a marketing page (only required fields).
        
        Returns:
            Dictionary with minimal marketing page creation data
        """
        return {
            "page_id": "minimal-page",
            "hero": {
                "title": "Minimal Hero Title",
                "description": "Minimal hero description"
            }
        }
    
    def create_test_marketing_page_create_invalid_data(self) -> Dict[str, Any]:
        """Generate invalid test data for creating a marketing page (missing required fields).
        
        Returns:
            Dictionary with invalid marketing page creation data
        """
        return {
            "page_id": "invalid-page"
            # Missing required 'hero' field
        }
    
    def create_test_linkedin_search_data(self, url: str = "https://www.linkedin.com/in/john-doe") -> Dict[str, Any]:
        """Generate test data for LinkedIn URL search.
        
        Args:
            url: LinkedIn URL to search for (person or company)
            
        Returns:
            Dictionary with LinkedIn search request data
        """
        return {
            "url": url
        }
    
    def create_test_linkedin_person_url(self) -> str:
        """Generate test LinkedIn person URL.
        
        Returns:
            LinkedIn person URL string
        """
        return "https://www.linkedin.com/in/john-doe"
    
    def create_test_linkedin_company_url(self) -> str:
        """Generate test LinkedIn company URL.
        
        Returns:
            LinkedIn company URL string
        """
        return "https://www.linkedin.com/company/tech-corp"
    
    def create_invalid_linkedin_url_empty(self) -> Dict[str, Any]:
        """Generate invalid LinkedIn search data with empty URL.
        
        Returns:
            Dictionary with empty URL (should fail validation)
        """
        return {
            "url": ""
        }
    
    def create_invalid_linkedin_url_missing(self) -> Dict[str, Any]:
        """Generate invalid LinkedIn search data with missing URL field.
        
        Returns:
            Dictionary without URL field (should fail validation)
        """
        return {}
    
    def create_invalid_linkedin_url_non_linkedin(self) -> Dict[str, Any]:
        """Generate invalid LinkedIn search data with non-LinkedIn URL.
        
        Returns:
            Dictionary with non-LinkedIn URL
        """
        return {
            "url": "https://www.example.com/profile"
        }
    
    def create_test_linkedin_search_data(self, url: Optional[str] = None) -> Dict[str, Any]:
        """Generate test data for LinkedIn search endpoint.
        
        Args:
            url: LinkedIn URL to search for (person or company)
            
        Returns:
            Dictionary with LinkedIn search request data
        """
        if url is None:
            url = "https://www.linkedin.com/in/john-doe"
        return {
            "url": url
        }
    
    def create_test_linkedin_person_url(self) -> str:
        """Generate test LinkedIn person URL.
        
        Returns:
            LinkedIn person URL string
        """
        return "https://www.linkedin.com/in/john-doe"
    
    def create_test_linkedin_company_url(self) -> str:
        """Generate test LinkedIn company URL.
        
        Returns:
            LinkedIn company URL string
        """
        return "https://www.linkedin.com/company/tech-corp"
    
    def create_test_linkedin_partial_url(self) -> str:
        """Generate test LinkedIn partial URL (for partial matching test).
        
        Returns:
            LinkedIn partial URL string
        """
        return "linkedin.com/in/john"  # Partial URL without https://
    
    def create_invalid_linkedin_url_data(self) -> Dict[str, Any]:
        """Generate invalid LinkedIn URL data for error testing.
        
        Returns:
            Dictionary with invalid LinkedIn URL (empty string)
        """
        return {
            "url": ""  # Empty URL should fail
        }
    
    def create_test_linkedin_url_missing_field(self) -> Dict[str, Any]:
        """Generate test data with missing URL field.
        
        Returns:
            Empty dictionary (missing required 'url' field)
        """
        return {}  # Missing required 'url' field
    
    # ==================== Email API Test Data ====================
    
    def create_test_email_finder_query_params(self, first_name: Optional[str] = None, last_name: Optional[str] = None, domain: Optional[str] = None, website: Optional[str] = None) -> Dict[str, Any]:
        """Generate query parameters for email finder endpoint.
        
        Args:
            first_name: Contact first name (default: "John")
            last_name: Contact last name (default: "Doe")
            domain: Company domain (default: "example.com")
            website: Company website URL (alternative to domain)
            
        Returns:
            Dictionary with query parameters
        """
        params = {}
        if first_name:
            params["first_name"] = first_name
        else:
            params["first_name"] = "John"
        if last_name:
            params["last_name"] = last_name
        else:
            params["last_name"] = "Doe"
        if domain:
            params["domain"] = domain
        elif website:
            params["website"] = website
        else:
            params["domain"] = "example.com"
        return params
    
    def create_test_email_finder_missing_first_name(self) -> Dict[str, Any]:
        """Generate query params missing first_name for error testing."""
        return {
            "last_name": "Doe",
            "domain": "example.com"
        }
    
    def create_test_email_finder_missing_last_name(self) -> Dict[str, Any]:
        """Generate query params missing last_name for error testing."""
        return {
            "first_name": "John",
            "domain": "example.com"
        }
    
    def create_test_email_finder_missing_domain(self) -> Dict[str, Any]:
        """Generate query params missing domain/website for error testing."""
        return {
            "first_name": "John",
            "last_name": "Doe"
        }
    
    def create_test_email_finder_invalid_domain(self) -> Dict[str, Any]:
        """Generate query params with invalid domain for error testing."""
        return {
            "first_name": "John",
            "last_name": "Doe",
            "domain": "invalid-domain-format"
        }
    
    def create_test_email_export_data(self, contacts_count: int = 2) -> Dict[str, Any]:
        """Generate test data for email export endpoint.
        
        Args:
            contacts_count: Number of contacts to include (default: 2)
            
        Returns:
            Dictionary with email export request data
        """
        contacts = []
        for i in range(contacts_count):
            contacts.append({
                "first_name": f"John{i}",
                "last_name": f"Doe{i}",
                "domain": "example.com",
                "email": f"john{i}.doe{i}@example.com"
            })
        return {
            "contacts": contacts,
            "mapping": {
                "first_name": "first_name",
                "last_name": "last_name",
                "domain": "domain",
                "website": None,
                "email": "email"
            }
        }
    
    def create_test_email_export_minimal_data(self) -> Dict[str, Any]:
        """Generate minimal test data for email export endpoint."""
        return {
            "contacts": [
                {
                    "first_name": "John",
                    "last_name": "Doe",
                    "domain": "example.com"
                }
            ]
        }
    
    def create_test_email_export_invalid_data(self) -> Dict[str, Any]:
        """Generate invalid email export data (missing first_name)."""
        return {
            "contacts": [
                {
                    "last_name": "Doe",
                    "domain": "example.com"
                }
            ]
        }
    
    def create_test_email_export_empty_contacts(self) -> Dict[str, Any]:
        """Generate email export data with empty contacts list."""
        return {
            "contacts": []
        }
    
    def create_test_email_single_data(self, first_name: Optional[str] = None, last_name: Optional[str] = None, domain: Optional[str] = None, website: Optional[str] = None, provider: str = "truelist") -> Dict[str, Any]:
        """Generate test data for single email endpoint.
        
        Args:
            first_name: Contact first name (default: "John")
            last_name: Contact last name (default: "Doe")
            domain: Company domain (default: "example.com")
            website: Company website URL (alternative to domain)
            provider: Email verification provider (default: "truelist")
            
        Returns:
            Dictionary with single email request data
        """
        data = {
            "provider": provider
        }
        if first_name:
            data["first_name"] = first_name
        else:
            data["first_name"] = "John"
        if last_name:
            data["last_name"] = last_name
        else:
            data["last_name"] = "Doe"
        if domain:
            data["domain"] = domain
        elif website:
            data["website"] = website
        else:
            data["domain"] = "example.com"
        return data
    
    def create_test_email_single_missing_first_name(self) -> Dict[str, Any]:
        """Generate single email data missing first_name."""
        return {
            "last_name": "Doe",
            "domain": "example.com",
            "provider": "truelist"
        }
    
    def create_test_email_single_missing_domain(self) -> Dict[str, Any]:
        """Generate single email data missing domain/website."""
        return {
            "first_name": "John",
            "last_name": "Doe",
            "provider": "truelist"
        }
    
    def create_test_bulk_verifier_data(self, emails: Optional[List[str]] = None, provider: str = "truelist") -> Dict[str, Any]:
        """Generate test data for bulk email verifier endpoint.
        
        Args:
            emails: List of email addresses (default: 3 test emails)
            provider: Email verification provider (default: "truelist")
            
        Returns:
            Dictionary with bulk verifier request data
        """
        if emails is None:
            emails = [
                "john.doe@example.com",
                "jane.smith@example.com",
                "test@example.com"
            ]
        return {
            "provider": provider,
            "emails": emails
        }
    
    def create_test_bulk_verifier_empty_emails(self) -> Dict[str, Any]:
        """Generate bulk verifier data with empty emails list."""
        return {
            "provider": "truelist",
            "emails": []
        }
    
    def create_test_bulk_verifier_invalid_email(self) -> Dict[str, Any]:
        """Generate bulk verifier data with invalid email format."""
        return {
            "provider": "truelist",
            "emails": ["invalid-email-format"]
        }
    
    def create_test_bulk_verifier_exceeds_limit(self) -> Dict[str, Any]:
        """Generate bulk verifier data exceeding 10000 email limit."""
        emails = [f"test{i}@example.com" for i in range(10001)]
        return {
            "provider": "truelist",
            "emails": emails
        }
    
    def create_test_single_verifier_data(self, email: Optional[str] = None, provider: str = "truelist") -> Dict[str, Any]:
        """Generate test data for single email verifier endpoint.
        
        Args:
            email: Email address to verify (default: "john.doe@example.com")
            provider: Email verification provider (default: "truelist")
            
        Returns:
            Dictionary with single verifier request data
        """
        if email is None:
            email = "john.doe@example.com"
        return {
            "email": email,
            "provider": provider
        }
    
    def create_test_single_verifier_invalid_email(self) -> Dict[str, Any]:
        """Generate single verifier data with invalid email format."""
        return {
            "email": "invalid-email-format",
            "provider": "truelist"
        }
    
    def create_test_single_verifier_missing_email(self) -> Dict[str, Any]:
        """Generate single verifier data missing email field."""
        return {
            "provider": "truelist"
        }
    
    def create_test_email_verifier_data(self, first_name: Optional[str] = None, last_name: Optional[str] = None, domain: Optional[str] = None, website: Optional[str] = None, provider: str = "truelist", email_count: Optional[int] = None, max_retries: Optional[int] = None) -> Dict[str, Any]:
        """Generate test data for email verifier endpoint (synchronous).
        
        Args:
            first_name: Contact first name (default: "John")
            last_name: Contact last name (default: "Doe")
            domain: Company domain (default: "example.com")
            website: Company website URL (alternative to domain)
            provider: Email verification provider (default: "truelist")
            email_count: Number of emails to generate per batch (default: 1000)
            max_retries: Maximum number of batches (default: 10)
            
        Returns:
            Dictionary with email verifier request data
        """
        data = {
            "provider": provider
        }
        if first_name:
            data["first_name"] = first_name
        else:
            data["first_name"] = "John"
        if last_name:
            data["last_name"] = last_name
        else:
            data["last_name"] = "Doe"
        if domain:
            data["domain"] = domain
        elif website:
            data["website"] = website
        else:
            data["domain"] = "example.com"
        if email_count is not None:
            data["email_count"] = email_count
        if max_retries is not None:
            data["max_retries"] = max_retries
        return data
    
    def create_test_email_verifier_invalid_email_count(self) -> Dict[str, Any]:
        """Generate email verifier data with invalid email_count (< 1)."""
        return {
            "first_name": "John",
            "last_name": "Doe",
            "domain": "example.com",
            "provider": "truelist",
            "email_count": 0
        }
    
    def create_test_email_verifier_invalid_max_retries(self) -> Dict[str, Any]:
        """Generate email verifier data with invalid max_retries (< 1)."""
        return {
            "first_name": "John",
            "last_name": "Doe",
            "domain": "example.com",
            "provider": "truelist",
            "max_retries": 0
        }
    
    def create_test_email_verifier_single_data(self, first_name: Optional[str] = None, last_name: Optional[str] = None, domain: Optional[str] = None, website: Optional[str] = None, provider: str = "truelist", email_count: Optional[int] = None, max_retries: Optional[int] = None) -> Dict[str, Any]:
        """Generate test data for email verifier single endpoint (find first valid).
        
        Args:
            first_name: Contact first name (default: "John")
            last_name: Contact last name (default: "Doe")
            domain: Company domain (default: "example.com")
            website: Company website URL (alternative to domain)
            provider: Email verification provider (default: "truelist")
            email_count: Number of emails to generate per batch (default: 1000)
            max_retries: Maximum number of batches (default: 10)
            
        Returns:
            Dictionary with email verifier single request data
        """
        return self.create_test_email_verifier_data(
            first_name=first_name,
            last_name=last_name,
            domain=domain,
            website=website,
            provider=provider,
            email_count=email_count,
            max_retries=max_retries
        )
    
    def create_test_email_bulk_download_params(self, file_type: str = "valid", slug: str = "test-slug-123", provider: str = "truelist") -> Dict[str, Any]:
        """Generate query parameters for bulk download endpoint.
        
        Args:
            file_type: File type (valid, invalid, c-all, unknown)
            slug: Slug identifier for the list
            provider: Email verification provider
            
        Returns:
            Dictionary with query parameters
        """
        return {
            "provider": provider
        }
    
    def create_test_email_bulk_download_path_params(self, file_type: str = "valid", slug: str = "test-slug-123") -> Dict[str, str]:
        """Generate path parameters for bulk download endpoint.
        
        Args:
            file_type: File type (valid, invalid, c-all, unknown)
            slug: Slug identifier for the list
            
        Returns:
            Dictionary with path parameters
        """
        return {
            "file_type": file_type,
            "slug": slug
        }
    
    def create_test_email_bulk_download_invalid_file_type(self) -> Dict[str, str]:
        """Generate path params with invalid file_type."""
        return {
            "file_type": "invalid-type",
            "slug": "test-slug-123"
        }
    
    # ==================== Dashboard Pages API Test Data ====================
    
    def create_test_dashboard_page_id(self) -> str:
        """Generate a test dashboard page ID.
        
        Returns:
            Dashboard page ID string
        """
        return "test-dashboard-page"
    
    def create_test_dashboard_page_get_path_params(self, page_id: Optional[str] = None) -> Dict[str, str]:
        """Generate path parameters for dashboard page get endpoint.
        
        Args:
            page_id: Page ID (default: "finder")
            
        Returns:
            Dictionary with path parameters
        """
        if page_id is None:
            page_id = "finder"
        return {
            "page_id": page_id
        }
    
    def create_test_dashboard_page_create_data(self, page_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate test data for dashboard page creation.
        
        Args:
            page_id: Page ID (default: generated unique ID)
            
        Returns:
            Dictionary with dashboard page creation request data
        """
        if page_id is None:
            page_id = f"test-page-{uuid.uuid4().hex[:8]}"
        return {
            "page_id": page_id,
            "metadata": {
                "title": "Test Dashboard Page",
                "description": "Test dashboard page description",
                "route": f"/{page_id}"
            },
            "access_control": {
                "allowed_roles": ["FreeUser", "ProUser", "Admin", "SuperAdmin"],
                "restriction_type": "none"
            },
            "sections": {}
        }
    
    def create_test_dashboard_page_create_minimal_data(self, page_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate minimal test data for dashboard page creation (only required fields).
        
        Args:
            page_id: Page ID (default: generated unique ID)
            
        Returns:
            Dictionary with minimal dashboard page creation request data
        """
        if page_id is None:
            page_id = f"test-page-{uuid.uuid4().hex[:8]}"
        return {
            "page_id": page_id
        }
    
    def create_test_dashboard_page_update_data(self) -> Dict[str, Any]:
        """Generate test data for dashboard page update (partial update).
        
        Returns:
            Dictionary with dashboard page update request data
        """
        return {
            "metadata": {
                "title": "Updated Dashboard Page Title"
            },
            "access_control": {
                "allowed_roles": ["ProUser", "Admin", "SuperAdmin"]
            },
            "sections": {
                "new_section": {
                    "content": "New section content"
                }
            }
        }
    
    def create_test_dashboard_page_update_partial_data(self) -> Dict[str, Any]:
        """Generate partial test data for dashboard page update (only metadata).
        
        Returns:
            Dictionary with partial dashboard page update request data
        """
        return {
            "metadata": {
                "title": "Updated Title Only"
            }
        }
    
    def create_test_dashboard_page_create_invalid_data(self) -> Dict[str, Any]:
        """Generate invalid dashboard page creation data (missing page_id).
        
        Returns:
            Dictionary with invalid dashboard page creation data
        """
        return {
            "metadata": {
                "title": "Test Page",
                "description": "Test description",
                "route": "/test"
            }
            # Missing required page_id field
        }
    
    def create_invalid_dashboard_page_id(self) -> str:
        """Generate an invalid dashboard page ID for error testing.
        
        Returns:
            Invalid page ID string
        """
        return "non-existent-dashboard-page-12345"
    
    # ==================== Contacts API Test Data ====================
    
    def create_test_contact_uuid(self) -> str:
        """Generate a test contact UUID.
        
        Returns:
            Contact UUID string
        """
        return str(uuid.uuid4())
    
    def create_test_contacts_query_vql_data(self) -> Dict[str, Any]:
        """Generate test data for contacts query endpoint (simple VQL query).
        
        Returns:
            Dictionary with VQL query request data
        """
        return {
            "filters": {
                "and": [
                    {
                        "field": "first_name",
                        "operator": "contains",
                        "value": "John"
                    }
                ]
            },
            "limit": 25,
            "offset": 0
        }
    
    def create_test_contacts_query_with_select_columns(self) -> Dict[str, Any]:
        """Generate test data for contacts query with field selection.
        
        Returns:
            Dictionary with VQL query request data including select_columns
        """
        return {
            "filters": {
                "and": [
                    {
                        "field": "first_name",
                        "operator": "contains",
                        "value": "John"
                    }
                ]
            },
            "select_columns": ["uuid", "first_name", "last_name", "email", "title"],
            "limit": 25,
            "offset": 0
        }
    
    def create_test_contacts_query_with_company_populate(self) -> Dict[str, Any]:
        """Generate test data for contacts query with company population.
        
        Returns:
            Dictionary with VQL query request data including company_config
        """
        return {
            "filters": {
                "and": [
                    {
                        "field": "email_status",
                        "operator": "eq",
                        "value": "valid"
                    }
                ]
            },
            "company_config": {
                "populate": True,
                "select_columns": ["name", "employees_count"]
            },
            "limit": 25,
            "offset": 0
        }
    
    def create_test_contacts_query_with_sorting(self) -> Dict[str, Any]:
        """Generate test data for contacts query with sorting.
        
        Returns:
            Dictionary with VQL query request data including sorting
        """
        return {
            "filters": {
                "and": [
                    {
                        "field": "first_name",
                        "operator": "exists",
                        "value": True
                    }
                ]
            },
            "sort_by": "created_at",
            "sort_direction": "desc",
            "limit": 25,
            "offset": 0
        }
    
    def create_test_contacts_query_complex_filters(self) -> Dict[str, Any]:
        """Generate test data for contacts query with complex AND/OR filters.
        
        Returns:
            Dictionary with complex VQL query request data
        """
        return {
            "filters": {
                "and": [
                    {
                        "field": "email_status",
                        "operator": "eq",
                        "value": "valid"
                    },
                    {
                        "or": [
                            {
                                "field": "title",
                                "operator": "contains",
                                "value": "CEO"
                            },
                            {
                                "field": "title",
                                "operator": "contains",
                                "value": "CTO"
                            }
                        ]
                    }
                ]
            },
            "limit": 25,
            "offset": 0
        }
    
    def create_test_contacts_query_empty_filters(self) -> Dict[str, Any]:
        """Generate test data for contacts query with empty filters (returns all).
        
        Returns:
            Dictionary with empty VQL query request data
        """
        return {
            "limit": 25,
            "offset": 0
        }
    
    def create_test_contacts_query_invalid_vql(self) -> Dict[str, Any]:
        """Generate invalid VQL query data (missing field in filter).
        
        Returns:
            Dictionary with invalid VQL query request data
        """
        return {
            "filters": {
                "and": [
                    {
                        "operator": "contains",
                        "value": "John"
                        # Missing required "field"
                    }
                ]
            }
        }
    
    def create_test_contacts_count_vql_data(self) -> Dict[str, Any]:
        """Generate test data for contacts count endpoint.
        
        Returns:
            Dictionary with VQL count request data
        """
        return {
            "filters": {
                "and": [
                    {
                        "field": "email_status",
                        "operator": "eq",
                        "value": "valid"
                    }
                ]
            }
        }
    
    def create_test_contacts_count_empty_filters(self) -> Dict[str, Any]:
        """Generate test data for contacts count with empty filters (count all).
        
        Returns:
            Dictionary with empty count request data
        """
        return {}
    
    def create_test_contacts_filter_data_request(self, filter_key: str = "departments", service: str = "contact", search_text: Optional[str] = None) -> Dict[str, Any]:
        """Generate test data for contacts filter data endpoint.
        
        Args:
            filter_key: Filter key (default: "departments")
            service: Service name (default: "contact")
            search_text: Optional search text (default: None)
            
        Returns:
            Dictionary with filter data request data
        """
        data = {
            "service": service,
            "filter_key": filter_key,
            "page": 1,
            "limit": 25
        }
        if search_text:
            data["search_text"] = search_text
        return data
    
    def create_test_contacts_filter_data_invalid_service(self) -> Dict[str, Any]:
        """Generate invalid filter data request (invalid service).
        
        Returns:
            Dictionary with invalid service value
        """
        return {
            "service": "invalid-service",
            "filter_key": "departments"
        }
    
    def create_test_contacts_filter_data_missing_filter_key(self) -> Dict[str, Any]:
        """Generate invalid filter data request (missing filter_key).
        
        Returns:
            Dictionary without required filter_key field
        """
        return {
            "service": "contact"
            # Missing required "filter_key"
        }
    
    def create_test_contact_get_path_params(self, contact_uuid: Optional[str] = None) -> Dict[str, str]:
        """Generate path parameters for contact get endpoint.
        
        Args:
            contact_uuid: Contact UUID (default: generated UUID)
            
        Returns:
            Dictionary with path parameters
        """
        if contact_uuid is None:
            contact_uuid = str(uuid.uuid4())
        return {
            "contact_uuid": contact_uuid
        }
    
    def create_invalid_contact_uuid(self) -> str:
        """Generate an invalid contact UUID for error testing.
        
        Returns:
            Invalid contact UUID string
        """
        return "00000000-0000-0000-0000-000000000000"
    
    # ==================== Company API Test Data ====================
    
    def create_test_company_uuid(self) -> str:
        """Generate a test company UUID.
        
        Returns:
            Company UUID string
        """
        return str(uuid.uuid4())
    
    def create_test_companies_query_vql_data(self) -> Dict[str, Any]:
        """Generate test data for companies query endpoint (simple VQL query).
        
        Returns:
            Dictionary with VQL query request data
        """
        return {
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
        }
    
    def create_test_companies_query_with_select_columns(self) -> Dict[str, Any]:
        """Generate test data for companies query with field selection.
        
        Returns:
            Dictionary with VQL query request data including select_columns
        """
        return {
            "filters": {
                "and": [
                    {
                        "field": "name",
                        "operator": "contains",
                        "value": "Tech"
                    }
                ]
            },
            "select_columns": ["uuid", "name", "employees_count", "annual_revenue"],
            "limit": 25,
            "offset": 0
        }
    
    def create_test_companies_query_with_contact_populate(self) -> Dict[str, Any]:
        """Generate test data for companies query with contact population.
        
        Returns:
            Dictionary with VQL query request data including contact_config
        """
        return {
            "filters": {
                "and": [
                    {
                        "field": "employees_count",
                        "operator": "gte",
                        "value": 100
                    }
                ]
            },
            "contact_config": {
                "populate": True,
                "select_columns": ["first_name", "last_name", "email"]
            },
            "limit": 25,
            "offset": 0
        }
    
    def create_test_companies_query_with_sorting(self) -> Dict[str, Any]:
        """Generate test data for companies query with sorting.
        
        Returns:
            Dictionary with VQL query request data including sorting
        """
        return {
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
            "limit": 25,
            "offset": 0
        }
    
    def create_test_companies_query_complex_filters(self) -> Dict[str, Any]:
        """Generate test data for companies query with complex AND/OR filters.
        
        Returns:
            Dictionary with complex VQL query request data
        """
        return {
            "filters": {
                "and": [
                    {
                        "field": "employees_count",
                        "operator": "gte",
                        "value": 100
                    },
                    {
                        "or": [
                            {
                                "field": "name",
                                "operator": "contains",
                                "value": "Tech"
                            },
                            {
                                "field": "name",
                                "operator": "contains",
                                "value": "Software"
                            }
                        ]
                    }
                ]
            },
            "limit": 25,
            "offset": 0
        }
    
    def create_test_companies_query_numeric_filters(self) -> Dict[str, Any]:
        """Generate test data for companies query with numeric comparison filters.
        
        Returns:
            Dictionary with numeric VQL query request data
        """
        return {
            "filters": {
                "and": [
                    {
                        "field": "employees_count",
                        "operator": "gte",
                        "value": 100
                    },
                    {
                        "field": "annual_revenue",
                        "operator": "gt",
                        "value": 1000000
                    }
                ]
            },
            "limit": 25,
            "offset": 0
        }
    
    def create_test_companies_query_empty_filters(self) -> Dict[str, Any]:
        """Generate test data for companies query with empty filters (returns all).
        
        Returns:
            Dictionary with empty VQL query request data
        """
        return {
            "limit": 25,
            "offset": 0
        }
    
    def create_test_companies_query_invalid_vql(self) -> Dict[str, Any]:
        """Generate invalid VQL query data (missing field in filter).
        
        Returns:
            Dictionary with invalid VQL query request data
        """
        return {
            "filters": {
                "and": [
                    {
                        "operator": "contains",
                        "value": "Acme"
                        # Missing required "field"
                    }
                ]
            }
        }
    
    def create_test_companies_count_vql_data(self) -> Dict[str, Any]:
        """Generate test data for companies count endpoint.
        
        Returns:
            Dictionary with VQL count request data
        """
        return {
            "filters": {
                "and": [
                    {
                        "field": "employees_count",
                        "operator": "gte",
                        "value": 100
                    }
                ]
            }
        }
    
    def create_test_companies_count_empty_filters(self) -> Dict[str, Any]:
        """Generate test data for companies count with empty filters (count all).
        
        Returns:
            Dictionary with empty count request data
        """
        return {}
    
    def create_test_companies_filter_data_request(self, filter_key: str = "industries", service: str = "company", search_text: Optional[str] = None) -> Dict[str, Any]:
        """Generate test data for companies filter data endpoint.
        
        Args:
            filter_key: Filter key (default: "industries")
            service: Service name (default: "company")
            search_text: Optional search text (default: None)
            
        Returns:
            Dictionary with filter data request data
        """
        data = {
            "service": service,
            "filter_key": filter_key,
            "page": 1,
            "limit": 25
        }
        if search_text:
            data["search_text"] = search_text
        return data
    
    def create_test_companies_filter_data_invalid_service(self) -> Dict[str, Any]:
        """Generate invalid filter data request (invalid service).
        
        Returns:
            Dictionary with invalid service value
        """
        return {
            "service": "invalid-service",
            "filter_key": "industries"
        }
    
    def create_test_companies_filter_data_missing_filter_key(self) -> Dict[str, Any]:
        """Generate invalid filter data request (missing filter_key).
        
        Returns:
            Dictionary without required filter_key field
        """
        return {
            "service": "company"
            # Missing required "filter_key"
        }
    
    def create_test_company_get_path_params(self, company_uuid: Optional[str] = None) -> Dict[str, str]:
        """Generate path parameters for company get endpoint.
        
        Args:
            company_uuid: Company UUID (default: generated UUID)
            
        Returns:
            Dictionary with path parameters
        """
        if company_uuid is None:
            company_uuid = str(uuid.uuid4())
        return {
            "company_uuid": company_uuid
        }
    
    def create_invalid_company_uuid(self) -> str:
        """Generate an invalid company UUID for error testing.
        
        Returns:
            Invalid company UUID string
        """
        return "00000000-0000-0000-0000-000000000000"
    
    def create_test_company_contacts_list_query_params(self, company_uuid: Optional[str] = None, limit: int = 25, offset: int = 0) -> Dict[str, Any]:
        """Generate query parameters for company contacts list endpoint.
        
        Args:
            company_uuid: Company UUID (for path param, not query param)
            limit: Limit for pagination (default: 25)
            offset: Offset for pagination (default: 0)
            
        Returns:
            Dictionary with query parameters
        """
        params = {
            "limit": limit,
            "offset": offset
        }
        return params
    
    def create_test_company_contacts_list_with_filters(self, first_name: Optional[str] = None, title: Optional[str] = None, seniority: Optional[str] = None) -> Dict[str, Any]:
        """Generate query parameters for company contacts list with filters.
        
        Args:
            first_name: Filter by first name (optional)
            title: Filter by title (optional)
            seniority: Filter by seniority (optional)
            
        Returns:
            Dictionary with query parameters including filters
        """
        params = {
            "limit": 25,
            "offset": 0
        }
        if first_name:
            params["first_name"] = first_name
        if title:
            params["title"] = title
        if seniority:
            params["seniority"] = seniority
        return params
    
    def create_test_company_contacts_list_path_params(self, company_uuid: Optional[str] = None) -> Dict[str, str]:
        """Generate path parameters for company contacts list endpoint.
        
        Args:
            company_uuid: Company UUID (default: generated UUID)
            
        Returns:
            Dictionary with path parameters
        """
        if company_uuid is None:
            company_uuid = str(uuid.uuid4())
        return {
            "company_uuid": company_uuid
        }
    
    def create_test_company_contacts_count_query_params(self) -> Dict[str, Any]:
        """Generate query parameters for company contacts count endpoint.
        
        Returns:
            Dictionary with query parameters (can include filters)
        """
        return {}
    
    def create_test_company_contacts_filters_path_params(self, company_uuid: Optional[str] = None) -> Dict[str, str]:
        """Generate path parameters for company contacts filters endpoint.
        
        Args:
            company_uuid: Company UUID (default: generated UUID)
            
        Returns:
            Dictionary with path parameters
        """
        if company_uuid is None:
            company_uuid = str(uuid.uuid4())
        return {
            "company_uuid": company_uuid
        }
    
    def create_test_company_contacts_filter_data_request(self, company_uuid: Optional[str] = None, filter_key: str = "departments", service: str = "contact", search_text: Optional[str] = None) -> Dict[str, Any]:
        """Generate test data for company contacts filter data endpoint.
        
        Args:
            company_uuid: Company UUID (for path param, not body)
            filter_key: Filter key (default: "departments")
            service: Service name (default: "contact")
            search_text: Optional search text (default: None)
            
        Returns:
            Dictionary with filter data request data
        """
        data = {
            "service": service,
            "filter_key": filter_key,
            "page": 1,
            "limit": 25
        }
        if search_text:
            data["search_text"] = search_text
        return data
    
    def create_test_company_contacts_filter_data_path_params(self, company_uuid: Optional[str] = None) -> Dict[str, str]:
        """Generate path parameters for company contacts filter data endpoint.
        
        Args:
            company_uuid: Company UUID (default: generated UUID)
            
        Returns:
            Dictionary with path parameters
        """
        if company_uuid is None:
            company_uuid = str(uuid.uuid4())
        return {
            "company_uuid": company_uuid
        }
    
    # ==================== Billing API Test Data ====================
    
    def create_test_billing_info_request(self) -> Dict[str, Any]:
        """Generate test data for billing info endpoint.
        
        Returns:
            Empty dictionary (no request body needed)
        """
        return {}
    
    def create_test_billing_subscribe_request(self, tier: str = "5k", period: str = "monthly") -> Dict[str, Any]:
        """Generate test data for subscribe endpoint.
        
        Args:
            tier: Subscription tier (default: "5k")
            period: Billing period (default: "monthly")
            
        Returns:
            Dictionary with subscribe request data
        """
        return {
            "tier": tier,
            "period": period
        }
    
    def create_test_billing_subscribe_invalid_tier(self) -> Dict[str, Any]:
        """Generate invalid subscribe request (invalid tier).
        
        Returns:
            Dictionary with invalid tier value
        """
        return {
            "tier": "invalid_tier",
            "period": "monthly"
        }
    
    def create_test_billing_subscribe_invalid_period(self) -> Dict[str, Any]:
        """Generate invalid subscribe request (invalid period).
        
        Returns:
            Dictionary with invalid period value
        """
        return {
            "tier": "5k",
            "period": "invalid_period"
        }
    
    def create_test_billing_subscribe_missing_tier(self) -> Dict[str, Any]:
        """Generate invalid subscribe request (missing tier).
        
        Returns:
            Dictionary without required tier field
        """
        return {
            "period": "monthly"
            # Missing required "tier"
        }
    
    def create_test_billing_subscribe_missing_period(self) -> Dict[str, Any]:
        """Generate invalid subscribe request (missing period).
        
        Returns:
            Dictionary without required period field
        """
        return {
            "tier": "5k"
            # Missing required "period"
        }
    
    def create_test_billing_addon_purchase_request(self, package_id: str = "small") -> Dict[str, Any]:
        """Generate test data for addon purchase endpoint.
        
        Args:
            package_id: Package ID (default: "small")
            
        Returns:
            Dictionary with addon purchase request data
        """
        return {
            "package_id": package_id
        }
    
    def create_test_billing_addon_purchase_invalid_package(self) -> Dict[str, Any]:
        """Generate invalid addon purchase request (invalid package_id).
        
        Returns:
            Dictionary with invalid package_id value
        """
        return {
            "package_id": "invalid_package"
        }
    
    def create_test_billing_addon_purchase_missing_package_id(self) -> Dict[str, Any]:
        """Generate invalid addon purchase request (missing package_id).
        
        Returns:
            Dictionary without required package_id field
        """
        return {}
    
    def create_test_billing_cancel_request(self) -> Dict[str, Any]:
        """Generate test data for cancel subscription endpoint.
        
        Returns:
            Empty dictionary (no request body needed)
        """
        return {}
    
    def create_test_billing_invoices_query_params(self, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """Generate query parameters for invoices endpoint.
        
        Args:
            limit: Limit for pagination (default: 10)
            offset: Offset for pagination (default: 0)
            
        Returns:
            Dictionary with query parameters
        """
        return {
            "limit": limit,
            "offset": offset
        }
    
    def create_test_billing_invoices_invalid_limit(self) -> Dict[str, Any]:
        """Generate invalid invoices query params (invalid limit).
        
        Returns:
            Dictionary with invalid limit value
        """
        return {
            "limit": 0,  # Invalid: must be >= 1
            "offset": 0
        }
    
    def create_test_billing_invoices_invalid_offset(self) -> Dict[str, Any]:
        """Generate invalid invoices query params (invalid offset).
        
        Returns:
            Dictionary with invalid offset value
        """
        return {
            "limit": 10,
            "offset": -1  # Invalid: must be >= 0
        }
    
    # Admin endpoints test data
    def create_test_billing_admin_plans_query_params(self, include_inactive: bool = False) -> Dict[str, Any]:
        """Generate query parameters for admin plans list endpoint.
        
        Args:
            include_inactive: Whether to include inactive plans (default: False)
            
        Returns:
            Dictionary with query parameters
        """
        return {
            "include_inactive": include_inactive
        }
    
    def create_test_billing_admin_plan_create_request(self, tier: str = "test-tier", name: str = "Test Plan", category: str = "STARTER") -> Dict[str, Any]:
        """Generate test data for admin plan create endpoint.
        
        Args:
            tier: Plan tier (default: "test-tier")
            name: Plan name (default: "Test Plan")
            category: Plan category (default: "STARTER")
            
        Returns:
            Dictionary with plan create request data
        """
        return {
            "tier": tier,
            "name": name,
            "category": category,
            "periods": [
                {
                    "period": "monthly",
                    "credits": 5000,
                    "rate_per_credit": 0.002,
                    "price": 10.0
                }
            ]
        }
    
    def create_test_billing_admin_plan_create_missing_tier(self) -> Dict[str, Any]:
        """Generate invalid admin plan create request (missing tier).
        
        Returns:
            Dictionary without required tier field
        """
        return {
            "name": "Test Plan",
            "category": "STARTER",
            "periods": []
            # Missing required "tier"
        }
    
    def create_test_billing_admin_plan_update_request(self, name: Optional[str] = None, category: Optional[str] = None) -> Dict[str, Any]:
        """Generate test data for admin plan update endpoint.
        
        Args:
            name: Optional plan name
            category: Optional plan category
            
        Returns:
            Dictionary with plan update request data
        """
        data = {}
        if name:
            data["name"] = name
        if category:
            data["category"] = category
        return data
    
    def create_test_billing_admin_plan_tier_path_param(self, tier: str = "5k") -> Dict[str, str]:
        """Generate path parameters for admin plan endpoints with tier.
        
        Args:
            tier: Plan tier (default: "5k")
            
        Returns:
            Dictionary with path parameters
        """
        return {
            "tier": tier
        }
    
    def create_test_billing_admin_plan_period_create_request(self, period: str = "monthly", credits: int = 5000, rate_per_credit: float = 0.002, price: float = 10.0) -> Dict[str, Any]:
        """Generate test data for admin plan period create endpoint.
        
        Args:
            period: Billing period (default: "monthly")
            credits: Credits (default: 5000)
            rate_per_credit: Rate per credit (default: 0.002)
            price: Price (default: 10.0)
            
        Returns:
            Dictionary with plan period create request data
        """
        return {
            "period": period,
            "credits": credits,
            "rate_per_credit": rate_per_credit,
            "price": price,
            "savings_amount": None,
            "savings_percentage": None
        }
    
    def create_test_billing_admin_plan_period_create_with_savings(self) -> Dict[str, Any]:
        """Generate test data for admin plan period create with savings.
        
        Returns:
            Dictionary with plan period create request data including savings
        """
        return {
            "period": "quarterly",
            "credits": 15000,
            "rate_per_credit": 0.0018,
            "price": 27.0,
            "savings_amount": 3.0,
            "savings_percentage": 10
        }
    
    def create_test_billing_admin_plan_period_create_invalid_credits(self) -> Dict[str, Any]:
        """Generate invalid admin plan period create request (invalid credits).
        
        Returns:
            Dictionary with invalid credits value
        """
        return {
            "period": "monthly",
            "credits": 0,  # Invalid: must be >= 1
            "rate_per_credit": 0.002,
            "price": 10.0
        }
    
    def create_test_billing_admin_plan_period_path_params(self, tier: str = "5k", period: str = "monthly") -> Dict[str, str]:
        """Generate path parameters for admin plan period endpoints.
        
        Args:
            tier: Plan tier (default: "5k")
            period: Billing period (default: "monthly")
            
        Returns:
            Dictionary with path parameters
        """
        return {
            "tier": tier,
            "period": period
        }
    
    def create_test_billing_admin_addons_query_params(self, include_inactive: bool = False) -> Dict[str, Any]:
        """Generate query parameters for admin addons list endpoint.
        
        Args:
            include_inactive: Whether to include inactive packages (default: False)
            
        Returns:
            Dictionary with query parameters
        """
        return {
            "include_inactive": include_inactive
        }
    
    def create_test_billing_admin_addon_create_request(self, package_id: str = "test-package", name: str = "Test Package", credits: int = 5000, rate_per_credit: float = 0.002, price: float = 10.0) -> Dict[str, Any]:
        """Generate test data for admin addon create endpoint.
        
        Args:
            package_id: Package ID (default: "test-package")
            name: Package name (default: "Test Package")
            credits: Credits (default: 5000)
            rate_per_credit: Rate per credit (default: 0.002)
            price: Price (default: 10.0)
            
        Returns:
            Dictionary with addon create request data
        """
        return {
            "id": package_id,
            "name": name,
            "credits": credits,
            "rate_per_credit": rate_per_credit,
            "price": price,
            "is_active": True
        }
    
    def create_test_billing_admin_addon_create_missing_id(self) -> Dict[str, Any]:
        """Generate invalid admin addon create request (missing id).
        
        Returns:
            Dictionary without required id field
        """
        return {
            "name": "Test Package",
            "credits": 5000,
            "rate_per_credit": 0.002,
            "price": 10.0
            # Missing required "id"
        }
    
    def create_test_billing_admin_addon_create_invalid_credits(self) -> Dict[str, Any]:
        """Generate invalid admin addon create request (invalid credits).
        
        Returns:
            Dictionary with invalid credits value
        """
        return {
            "id": "test-package",
            "name": "Test Package",
            "credits": 0,  # Invalid: must be >= 1
            "rate_per_credit": 0.002,
            "price": 10.0
        }
    
    def create_test_billing_admin_addon_update_request(self, name: Optional[str] = None, credits: Optional[int] = None, price: Optional[float] = None) -> Dict[str, Any]:
        """Generate test data for admin addon update endpoint.
        
        Args:
            name: Optional package name
            credits: Optional credits
            price: Optional price
            
        Returns:
            Dictionary with addon update request data
        """
        data = {}
        if name:
            data["name"] = name
        if credits:
            data["credits"] = credits
        if price:
            data["price"] = price
        return data
    
    def create_test_billing_admin_addon_package_id_path_param(self, package_id: str = "small") -> Dict[str, str]:
        """Generate path parameters for admin addon endpoints with package_id.
        
        Args:
            package_id: Package ID (default: "small")
            
        Returns:
            Dictionary with path parameters
        """
        return {
            "package_id": package_id
        }
    
    # ==================== Activities API Test Data ====================
    
    def create_test_activities_list_query_params(self, service_type: Optional[str] = None, action_type: Optional[str] = None, status: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """Generate query parameters for activities list endpoint.
        
        Args:
            service_type: Filter by service type (default: None)
            action_type: Filter by action type (default: None)
            status: Filter by status (default: None)
            start_date: Filter by start date ISO format (default: None)
            end_date: Filter by end date ISO format (default: None)
            limit: Limit for pagination (default: 100)
            offset: Offset for pagination (default: 0)
            
        Returns:
            Dictionary with query parameters
        """
        params = {
            "limit": limit,
            "offset": offset
        }
        if service_type:
            params["service_type"] = service_type
        if action_type:
            params["action_type"] = action_type
        if status:
            params["status"] = status
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return params
    
    def create_test_activities_list_all_filters(self) -> Dict[str, Any]:
        """Generate query parameters for activities list with all filters.
        
        Returns:
            Dictionary with all filter query parameters
        """
        return {
            "service_type": "linkedin",
            "action_type": "search",
            "status": "success",
            "start_date": "2024-01-01T00:00:00Z",
            "end_date": "2024-12-31T23:59:59Z",
            "limit": 50,
            "offset": 0
        }
    
    def create_test_activities_list_service_type_linkedin(self) -> Dict[str, Any]:
        """Generate query parameters for activities list filtered by LinkedIn service type.
        
        Returns:
            Dictionary with service_type filter for linkedin
        """
        return {
            "service_type": "linkedin",
            "limit": 100,
            "offset": 0
        }
    
    def create_test_activities_list_service_type_email(self) -> Dict[str, Any]:
        """Generate query parameters for activities list filtered by email service type.
        
        Returns:
            Dictionary with service_type filter for email
        """
        return {
            "service_type": "email",
            "limit": 100,
            "offset": 0
        }
    
    def create_test_activities_list_action_type_search(self) -> Dict[str, Any]:
        """Generate query parameters for activities list filtered by search action type.
        
        Returns:
            Dictionary with action_type filter for search
        """
        return {
            "action_type": "search",
            "limit": 100,
            "offset": 0
        }
    
    def create_test_activities_list_action_type_export(self) -> Dict[str, Any]:
        """Generate query parameters for activities list filtered by export action type.
        
        Returns:
            Dictionary with action_type filter for export
        """
        return {
            "action_type": "export",
            "limit": 100,
            "offset": 0
        }
    
    def create_test_activities_list_status_success(self) -> Dict[str, Any]:
        """Generate query parameters for activities list filtered by success status.
        
        Returns:
            Dictionary with status filter for success
        """
        return {
            "status": "success",
            "limit": 100,
            "offset": 0
        }
    
    def create_test_activities_list_status_failed(self) -> Dict[str, Any]:
        """Generate query parameters for activities list filtered by failed status.
        
        Returns:
            Dictionary with status filter for failed
        """
        return {
            "status": "failed",
            "limit": 100,
            "offset": 0
        }
    
    def create_test_activities_list_date_range(self) -> Dict[str, Any]:
        """Generate query parameters for activities list with date range filter.
        
        Returns:
            Dictionary with date range query parameters
        """
        return {
            "start_date": "2024-01-01T00:00:00Z",
            "end_date": "2024-12-31T23:59:59Z",
            "limit": 100,
            "offset": 0
        }
    
    def create_test_activities_list_pagination(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """Generate query parameters for activities list with pagination.
        
        Args:
            limit: Limit for pagination (default: 50)
            offset: Offset for pagination (default: 0)
            
        Returns:
            Dictionary with pagination query parameters
        """
        return {
            "limit": limit,
            "offset": offset
        }
    
    def create_test_activities_list_invalid_service_type(self) -> Dict[str, Any]:
        """Generate invalid query parameters (invalid service_type).
        
        Returns:
            Dictionary with invalid service_type value
        """
        return {
            "service_type": "invalid_service",
            "limit": 100,
            "offset": 0
        }
    
    def create_test_activities_list_invalid_action_type(self) -> Dict[str, Any]:
        """Generate invalid query parameters (invalid action_type).
        
        Returns:
            Dictionary with invalid action_type value
        """
        return {
            "action_type": "invalid_action",
            "limit": 100,
            "offset": 0
        }
    
    def create_test_activities_list_invalid_status(self) -> Dict[str, Any]:
        """Generate invalid query parameters (invalid status).
        
        Returns:
            Dictionary with invalid status value
        """
        return {
            "status": "invalid_status",
            "limit": 100,
            "offset": 0
        }
    
    def create_test_activities_list_invalid_limit(self) -> Dict[str, Any]:
        """Generate invalid query parameters (invalid limit).
        
        Returns:
            Dictionary with invalid limit value
        """
        return {
            "limit": 0,  # Invalid: must be >= 1
            "offset": 0
        }
    
    def create_test_activities_list_limit_exceeds_max(self) -> Dict[str, Any]:
        """Generate invalid query parameters (limit exceeds max).
        
        Returns:
            Dictionary with limit exceeding maximum (1000)
        """
        return {
            "limit": 1001,  # Invalid: must be <= 1000
            "offset": 0
        }
    
    def create_test_activities_list_invalid_offset(self) -> Dict[str, Any]:
        """Generate invalid query parameters (invalid offset).
        
        Returns:
            Dictionary with invalid offset value
        """
        return {
            "limit": 100,
            "offset": -1  # Invalid: must be >= 0
        }
    
    def create_test_activities_list_invalid_date_format(self) -> Dict[str, Any]:
        """Generate invalid query parameters (invalid date format).
        
        Returns:
            Dictionary with invalid date format
        """
        return {
            "start_date": "2024-01-01",  # Invalid: should be ISO 8601 with time
            "end_date": "2024-12-31",
            "limit": 100,
            "offset": 0
        }
    
    def create_test_activities_stats_query_params(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """Generate query parameters for activities stats endpoint.
        
        Args:
            start_date: Filter by start date ISO format (default: None)
            end_date: Filter by end date ISO format (default: None)
            
        Returns:
            Dictionary with query parameters
        """
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return params
    
    def create_test_activities_stats_date_range(self) -> Dict[str, Any]:
        """Generate query parameters for activities stats with date range.
        
        Returns:
            Dictionary with date range query parameters
        """
        return {
            "start_date": "2024-01-01T00:00:00Z",
            "end_date": "2024-12-31T23:59:59Z"
        }
    
    def create_test_activities_stats_no_params(self) -> Dict[str, Any]:
        """Generate empty query parameters for activities stats (all activities).
        
        Returns:
            Empty dictionary
        """
        return {}
    
    def create_test_activities_stats_invalid_date_format(self) -> Dict[str, Any]:
        """Generate invalid query parameters (invalid date format).
        
        Returns:
            Dictionary with invalid date format
        """
        return {
            "start_date": "2024-01-01",  # Invalid: should be ISO 8601 with time
            "end_date": "2024-12-31"
        }
    
    def cleanup_test_data(self):
        """Clean up all test data."""
        # TODO: Implement cleanup logic
        # For now, just clear the fixtures file
        self._fixtures = {
            "chat_ids": [],
            "company_uuids": [],
            "contact_uuids": [],
            "export_ids": [],
            "page_ids": [],
            "user_ids": [],
        }
        if self.fixtures_file.exists():
            self.fixtures_file.unlink()

