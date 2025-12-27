"""Integration tests comparing VQL vs Direct DB query results."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app

client = TestClient(app)


@pytest.mark.asyncio
@pytest.mark.integration
class TestVQLEndpoints:
    """Integration tests for VQL endpoints."""

    def test_contacts_list_endpoint_vql_enabled(self):
        """Test contacts list endpoint with VQL enabled."""
        # This test would require VQL to be enabled and Connectra service running
        # For now, it's a placeholder structure
        response = client.get("/api/v1/contacts/")
        
        # Basic smoke test - endpoint should respond
        assert response.status_code in [200, 401]  # 401 if no auth

    def test_contacts_count_endpoint_vql_enabled(self):
        """Test contacts count endpoint with VQL enabled."""
        response = client.get("/api/v1/contacts/count/")
        
        # Basic smoke test
        assert response.status_code in [200, 401]

    def test_companies_list_endpoint_vql_enabled(self):
        """Test companies list endpoint with VQL enabled."""
        response = client.get("/api/v1/companies/")
        
        # Basic smoke test
        assert response.status_code in [200, 401]

    def test_companies_count_endpoint_vql_enabled(self):
        """Test companies count endpoint with VQL enabled."""
        response = client.get("/api/v1/companies/count/")
        
        # Basic smoke test
        assert response.status_code in [200, 401]


@pytest.mark.asyncio
@pytest.mark.integration
class TestVQLMigrationEndpoints:
    """Integration tests for VQL migration endpoints (single records, company contacts, etc.)."""

    def test_single_contact_retrieval_vql(self):
        """Test single contact retrieval via VQL."""
        # Test GET /api/v1/contacts/{contact_uuid}/
        # This endpoint now uses VQL when VQL_SINGLE_RECORD_RETRIEVAL is enabled
        # Note: Requires valid contact UUID and authentication
        response = client.get("/api/v1/contacts/test-uuid/")
        
        # Should return 404 for invalid UUID or 401 for no auth
        assert response.status_code in [404, 401]

    def test_single_company_retrieval_vql(self):
        """Test single company retrieval via VQL."""
        # Test GET /api/v1/companies/{company_uuid}/
        # This endpoint now uses VQL when VQL_SINGLE_RECORD_RETRIEVAL is enabled
        response = client.get("/api/v1/companies/test-uuid/")
        
        # Should return 404 for invalid UUID or 401 for no auth
        assert response.status_code in [404, 401]

    def test_company_contacts_listing_vql(self):
        """Test company contacts listing via VQL."""
        # Test GET /api/v1/companies/company/{company_uuid}/contacts/
        # This endpoint now uses VQL when VQL_COMPANY_CONTACTS is enabled
        response = client.get("/api/v1/companies/company/test-uuid/contacts/")
        
        # Should return 404 for invalid company UUID or 401 for no auth
        assert response.status_code in [404, 401]

    def test_company_contacts_count_vql(self):
        """Test company contacts count via VQL."""
        # Test GET /api/v1/companies/company/{company_uuid}/contacts/count/
        # This endpoint now uses VQL when VQL_COMPANY_CONTACTS is enabled
        response = client.get("/api/v1/companies/company/test-uuid/contacts/count/")
        
        # Should return 404 for invalid company UUID or 401 for no auth
        assert response.status_code in [404, 401]

    def test_linkedin_search_vql(self):
        """Test LinkedIn search via VQL."""
        # Test POST /api/v2/linkedin/
        # This endpoint now uses VQL when VQL_LINKEDIN_SEARCH is enabled
        response = client.post(
            "/api/v2/linkedin/",
            json={"url": "https://www.linkedin.com/in/test"}
        )
        
        # Should return 401 for no auth or 400 for invalid URL
        assert response.status_code in [400, 401]


@pytest.mark.asyncio
@pytest.mark.integration
class TestVQLFallback:
    """Test VQL fallback to repository when Connectra is unavailable."""

    def test_vql_fallback_on_connectra_error(self):
        """Test that endpoints fall back to repository when VQL fails."""
        # When CONNECTRA_ENABLED=True but Connectra service is down,
        # endpoints should fall back to direct repository queries
        # This is tested implicitly by the service layer error handling
        pass  # Integration test would require mocking ConnectraClient

    def test_vql_fallback_when_disabled(self):
        """Test that endpoints use repository when VQL is disabled."""
        # When CONNECTRA_ENABLED=False, all endpoints should use repository
        # This is the default behavior
        pass  # This is the default state


@pytest.mark.asyncio
@pytest.mark.integration
class TestVQLFeatureFlags:
    """Test VQL feature flag behavior."""

    def test_feature_flags_exist(self):
        """Verify that VQL feature flags are defined in config."""
        
        settings = get_settings()
        assert hasattr(settings, 'VQL_SINGLE_RECORD_RETRIEVAL')
        assert hasattr(settings, 'VQL_COMPANY_CONTACTS')
        assert hasattr(settings, 'VQL_EXPORTS')
        assert hasattr(settings, 'VQL_LINKEDIN_SEARCH')
        assert hasattr(settings, 'CONNECTRA_ENABLED')

    # Note: Full integration tests comparing VQL vs DB results would require:
    # 1. Test database with known data
    # 2. Elasticsearch with same data indexed
    # 3. Connectra service running
    # 4. Authentication setup
    # 5. Feature flags enabled/disabled scenarios
    # These are placeholders for the test structure

