"""Unit tests for VQL converter service."""

import pytest

from app.schemas.filters import CompanyFilterParams, ContactFilterParams
from app.services.vql_converter import VQLConverter


class TestVQLConverter:
    """Test cases for VQLConverter."""

    def setup_method(self):
        """Set up test fixtures."""
        self.converter = VQLConverter()

    def test_convert_contact_filters_simple(self):
        """Test converting simple contact filters to VQL."""
        filters = ContactFilterParams(
            first_name="John",
            seniority="Senior",
        )
        
        vql_query = self.converter.convert_contact_filters_to_vql(filters)
        
        assert vql_query is not None
        assert vql_query.where is not None
        assert vql_query.page == 1
        assert vql_query.limit == 25

    def test_convert_contact_filters_with_range(self):
        """Test converting contact filters with range queries."""
        filters = ContactFilterParams(
            employees_min=100,
            employees_max=1000,
        )
        
        vql_query = self.converter.convert_contact_filters_to_vql(filters)
        
        assert vql_query.where is not None
        assert vql_query.where.range_query is not None
        assert "company_employees_count" in vql_query.where.range_query.must

    def test_convert_company_filters_simple(self):
        """Test converting simple company filters to VQL."""
        filters = CompanyFilterParams(
            name="Software",
            industries=["Technology"],
        )
        
        vql_query = self.converter.convert_company_filters_to_vql(filters)
        
        assert vql_query is not None
        assert vql_query.where is not None

    def test_build_order_by(self):
        """Test building order_by from ordering string."""
        ordering = "created_at:desc,email:asc"
        order_by_list = self.converter._build_order_by(ordering)
        
        assert len(order_by_list) == 2
        assert order_by_list[0].order_by == "created_at"
        assert order_by_list[0].order_direction == "desc"
        assert order_by_list[1].order_by == "email"
        assert order_by_list[1].order_direction == "asc"

    def test_convert_with_exclude_filters(self):
        """Test converting filters with exclude conditions."""
        filters = ContactFilterParams(
            first_name="John",
            exclude_titles=["Intern"],
            exclude_seniorities=["Junior"],
        )
        
        vql_query = self.converter.convert_contact_filters_to_vql(filters)
        
        assert vql_query.where is not None
        if vql_query.where.text_matches:
            assert len(vql_query.where.text_matches.get("must_not", [])) > 0
        if vql_query.where.keyword_match:
            assert "seniority" in vql_query.where.keyword_match.must_not

