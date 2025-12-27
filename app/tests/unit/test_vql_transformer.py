"""Unit tests for VQL transformer service."""

import pytest

from app.schemas.filters import ContactFilterParams
from app.services.vql_transformer import VQLTransformer


class TestVQLTransformer:
    """Test cases for VQLTransformer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.transformer = VQLTransformer()

    def test_transform_contact_response(self):
        """Test transforming VQL contact response."""
        vql_response = {
            "data": [
                {
                    "id": 1,
                    "uuid": "test-uuid-1",
                    "first_name": "John",
                    "last_name": "Doe",
                    "email": "john@example.com",
                    "title": "Engineer",
                    "departments": ["Engineering"],
                    "email_status": "verified",
                    "seniority": "Senior",
                }
            ],
            "success": True,
        }
        
        contacts = self.transformer.transform_contact_response(vql_response)
        
        assert len(contacts) == 1
        assert contacts[0].uuid == "test-uuid-1"
        assert contacts[0].first_name == "John"

    def test_transform_contact_simple_response(self):
        """Test transforming VQL contact simple response."""
        vql_response = {
            "data": [
                {
                    "uuid": "test-uuid-1",
                    "first_name": "John",
                    "last_name": "Doe",
                    "title": "Engineer",
                    "city": "San Francisco",
                    "state": "CA",
                    "country": "USA",
                }
            ],
            "success": True,
        }
        
        contacts = self.transformer.transform_contact_simple_response(vql_response)
        
        assert len(contacts) == 1
        assert contacts[0].uuid == "test-uuid-1"
        assert contacts[0].first_name == "John"

    def test_build_cursor_page(self):
        """Test building cursor page from VQL response."""
        vql_response = {
            "data": [
                {
                    "uuid": "test-uuid-1",
                    "first_name": "John",
                    "last_name": "Doe",
                }
            ],
            "success": True,
        }
        
        filters = ContactFilterParams()
        page = self.transformer.build_cursor_page(
            vql_response, filters, "http://test.com", use_cursor=False, limit=25, offset=0
        )
        
        assert page.success is True
        assert len(page.data) == 1

