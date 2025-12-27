"""Service for transforming VQL responses to backend schema formats."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from app.schemas.common import CursorPage
from app.schemas.companies import CompanyListItem
from app.schemas.contacts import ContactListItem, ContactLocation, ContactSimpleItem
from app.schemas.filters import CompanyFilterParams, ContactFilterParams
from app.utils.cursor import encode_offset_cursor
from app.utils.logger import get_logger, log_error
from app.utils.pagination import build_pagination_link

logger = get_logger(__name__)


class VQLTransformer:
    """Transforms VQL API responses to backend schema formats."""

    def transform_contact_response(
        self, vql_response: Dict[str, Any]
    ) -> List[ContactListItem]:
        """
        Transform VQL contact response to ContactListItem list.

        Args:
            vql_response: VQL API response dictionary

        Returns:
            List of ContactListItem objects
        """
        start_time = time.time()
        contacts = []
        data = vql_response.get("data", [])
        total_items = len(data)
        failed_count = 0

        for item in data:
            try:
                contact = self._transform_contact_item(item)
                contacts.append(contact)
            except Exception as exc:
                failed_count += 1
                log_error(
                    "Failed to transform contact item",
                    exc,
                    "app.services.vql_transformer",
                    context={"item_uuid": item.get("uuid"), "total_items": total_items}
                )
                continue

        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            "Contact response transformation completed",
            extra={
                "context": {
                    "operation": "transform_contact_response",
                    "total_items": total_items,
                    "successful": len(contacts),
                    "failed": failed_count,
                },
                "performance": {"duration_ms": duration_ms}
            }
        )

        return contacts

    def transform_contact_simple_response(
        self, vql_response: Dict[str, Any]
    ) -> List[ContactSimpleItem]:
        """
        Transform VQL contact response to ContactSimpleItem list.

        Args:
            vql_response: VQL API response dictionary

        Returns:
            List of ContactSimpleItem objects
        """
        start_time = time.time()
        contacts = []
        data = vql_response.get("data", [])
        total_items = len(data)
        failed_count = 0

        for item in data:
            try:
                contact = self._transform_contact_simple_item(item)
                contacts.append(contact)
            except Exception as exc:
                failed_count += 1
                log_error(
                    "Failed to transform contact simple item",
                    exc,
                    "app.services.vql_transformer",
                    context={"item_uuid": item.get("uuid"), "total_items": total_items}
                )
                continue

        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            "Contact simple response transformation completed",
            extra={
                "context": {
                    "operation": "transform_contact_simple_response",
                    "total_items": total_items,
                    "successful": len(contacts),
                    "failed": failed_count,
                },
                "performance": {"duration_ms": duration_ms}
            }
        )

        return contacts

    def _transform_contact_item(self, item: Dict[str, Any]) -> ContactListItem:
        """Transform a single contact item from VQL response."""
        # Map VQL response fields to ContactListItem
        # Note: ContactListItem has flattened structure with company fields
        contact_data: Dict[str, Any] = {
            "uuid": item.get("uuid"),
            "first_name": item.get("first_name"),
            "last_name": item.get("last_name"),
            "email": item.get("email"),
            "title": item.get("title"),
            "departments": ", ".join(item.get("departments", [])) if item.get("departments") else None,
            "mobile_phone": item.get("mobile_phone"),
            "email_status": item.get("email_status"),
            "seniority": item.get("seniority"),
            "city": item.get("city"),
            "state": item.get("state"),
            "country": item.get("country"),
            "person_linkedin_url": item.get("linkedin_url"),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
        }

        # Handle company object if present (flatten company fields)
        company = item.get("company")
        if company:
            contact_data["company"] = company.get("name")
            contact_data["company_name_for_emails"] = company.get("company_name_for_emails")
            contact_data["employees"] = company.get("employees_count")
            contact_data["annual_revenue"] = company.get("annual_revenue")
            contact_data["total_funding"] = company.get("total_funding")
            contact_data["industry"] = company.get("industries", [None])[0] if company.get("industries") else None
            contact_data["company_city"] = company.get("city")
            contact_data["company_state"] = company.get("state")
            contact_data["company_country"] = company.get("country")
            contact_data["company_address"] = company.get("address")
            contact_data["company_linkedin_url"] = company.get("linkedin_url")
            contact_data["company_phone"] = company.get("phone_number")
            contact_data["technologies"] = ", ".join(company.get("technologies", [])) if company.get("technologies") else None
            contact_data["latest_funding"] = company.get("latest_funding")
            contact_data["latest_funding_amount"] = company.get("latest_funding_amount")
            contact_data["last_raised_at"] = company.get("last_raised_at")

        # Handle metadata fields if present
        if item.get("work_direct_phone"):
            contact_data["work_direct_phone"] = item.get("work_direct_phone")
        if item.get("home_phone"):
            contact_data["home_phone"] = item.get("home_phone")
        if item.get("other_phone"):
            contact_data["other_phone"] = item.get("other_phone")
        if item.get("facebook_url"):
            contact_data["facebook_url"] = item.get("facebook_url")
        if item.get("twitter_url"):
            contact_data["twitter_url"] = item.get("twitter_url")
        if item.get("website"):
            contact_data["website"] = item.get("website")
        if item.get("stage"):
            contact_data["stage"] = item.get("stage")

        return ContactListItem(**contact_data)

    def _transform_contact_simple_item(self, item: Dict[str, Any]) -> ContactSimpleItem:
        """Transform a single contact item to ContactSimpleItem."""
        
        company = item.get("company", {})
        location = None
        if item.get("city") or item.get("state") or item.get("country"):
            location = ContactLocation(
                city=item.get("city"),
                state=item.get("state"),
                country=item.get("country"),
            )
        
        return ContactSimpleItem(
            uuid=item.get("uuid"),
            first_name=item.get("first_name"),
            last_name=item.get("last_name"),
            title=item.get("title"),
            location=location,
            company_name=company.get("name") if company else None,
            person_linkedin_url=item.get("linkedin_url"),
            company_domain=company.get("normalized_domain") if company else None,
        )

    def build_cursor_page(
        self,
        vql_response: Dict[str, Any],
        original_filters: ContactFilterParams,
        request_url: str,
        use_cursor: bool = False,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> CursorPage[ContactListItem]:
        """
        Build CursorPage from VQL response.

        Args:
            vql_response: VQL API response
            original_filters: Original filter parameters
            request_url: Request URL for pagination links
            use_cursor: Whether to use cursor-based pagination
            limit: Page limit
            offset: Current offset

        Returns:
            CursorPage with contacts and pagination metadata
        """
        data = self.transform_contact_response(vql_response)
        success = vql_response.get("success", True)

        # Build pagination metadata
        # VQL uses page-based pagination, but we need to convert to cursor-based
        # for consistency with existing API
        next_link = None
        previous_link = None

        if use_cursor:
            # Calculate next/previous cursors
            if len(data) == (limit or 25):
                # There might be more results
                next_offset = offset + len(data)
                next_cursor = encode_offset_cursor(next_offset)
                next_link = build_pagination_link(request_url, cursor=next_cursor)

            if offset > 0:
                prev_offset = max(0, offset - (limit or 25))
                prev_cursor = encode_offset_cursor(prev_offset)
                previous_link = build_pagination_link(request_url, cursor=prev_cursor)
        else:
            # Page-based pagination
            current_page = original_filters.page or 1
            if len(data) == (limit or 25):
                # There might be more results
                next_page = current_page + 1
                next_link = build_pagination_link(request_url, page=next_page)

            if current_page > 1:
                prev_page = current_page - 1
                previous_link = build_pagination_link(request_url, page=prev_page)

        return CursorPage(
            data=data,
            success=success,
            next=next_link,
            previous=previous_link,
        )

    def build_cursor_page_simple(
        self,
        vql_response: Dict[str, Any],
        original_filters: ContactFilterParams,
        request_url: str,
        use_cursor: bool = False,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> CursorPage[ContactSimpleItem]:
        """
        Build CursorPage with ContactSimpleItem from VQL response.

        Args:
            vql_response: VQL API response
            original_filters: Original filter parameters
            request_url: Request URL for pagination links
            use_cursor: Whether to use cursor-based pagination
            limit: Page limit
            offset: Current offset

        Returns:
            CursorPage with simple contacts and pagination metadata
        """
        data = self.transform_contact_simple_response(vql_response)
        success = vql_response.get("success", True)

        # Build pagination metadata (same as build_cursor_page)
        next_link = None
        previous_link = None

        if use_cursor:
            if len(data) == (limit or 25):
                next_offset = offset + len(data)
                next_cursor = encode_offset_cursor(next_offset)
                next_link = build_pagination_link(request_url, cursor=next_cursor)

            if offset > 0:
                prev_offset = max(0, offset - (limit or 25))
                prev_cursor = encode_offset_cursor(prev_offset)
                previous_link = build_pagination_link(request_url, cursor=prev_cursor)
        else:
            current_page = original_filters.page or 1
            if len(data) == (limit or 25):
                next_page = current_page + 1
                next_link = build_pagination_link(request_url, page=next_page)

            if current_page > 1:
                prev_page = current_page - 1
                previous_link = build_pagination_link(request_url, page=prev_page)

        return CursorPage(
            data=data,
            success=success,
            next=next_link,
            previous=previous_link,
        )

    def transform_company_response(
        self, vql_response: Dict[str, Any]
    ) -> List[CompanyListItem]:
        """
        Transform VQL company response to CompanyListItem list.

        Args:
            vql_response: VQL API response dictionary

        Returns:
            List of CompanyListItem objects
        """
        start_time = time.time()
        companies = []
        data = vql_response.get("data", [])
        total_items = len(data)
        failed_count = 0

        for item in data:
            try:
                company_data = self._transform_company_item(item)
                company = CompanyListItem(**company_data)
                companies.append(company)
            except Exception as exc:
                failed_count += 1
                log_error(
                    "Failed to transform company item",
                    exc,
                    "app.services.vql_transformer",
                    context={"item_uuid": item.get("uuid"), "total_items": total_items}
                )
                continue

        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            "Company response transformation completed",
            extra={
                "context": {
                    "operation": "transform_company_response",
                    "total_items": total_items,
                    "successful": len(companies),
                    "failed": failed_count,
                },
                "performance": {"duration_ms": duration_ms}
            }
        )

        return companies

    def build_company_cursor_page(
        self,
        vql_response: Dict[str, Any],
        original_filters: CompanyFilterParams,
        request_url: str,
        use_cursor: bool = False,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> CursorPage[CompanyListItem]:
        """
        Build CursorPage from VQL company response.

        Args:
            vql_response: VQL API response
            original_filters: Original filter parameters
            request_url: Request URL for pagination links
            use_cursor: Whether to use cursor-based pagination
            limit: Page limit
            offset: Current offset

        Returns:
            CursorPage with companies and pagination metadata
        """
        data = self.transform_company_response(vql_response)
        success = vql_response.get("success", True)

        # Build pagination metadata
        next_link = None
        previous_link = None

        if use_cursor:
            if len(data) == (limit or 25):
                next_offset = offset + len(data)
                next_cursor = encode_offset_cursor(next_offset)
                next_link = build_pagination_link(request_url, cursor=next_cursor)

            if offset > 0:
                prev_offset = max(0, offset - (limit or 25))
                prev_cursor = encode_offset_cursor(prev_offset)
                previous_link = build_pagination_link(request_url, cursor=prev_cursor)
        else:
            current_page = original_filters.page or 1
            if len(data) == (limit or 25):
                next_page = current_page + 1
                next_link = build_pagination_link(request_url, page=next_page)

            if current_page > 1:
                prev_page = current_page - 1
                previous_link = build_pagination_link(request_url, page=prev_page)

        return CursorPage(
            data=data,
            success=success,
            next=next_link,
            previous=previous_link,
        )

    def _transform_company_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a single company item from VQL response."""
        # Handle industries - take first one for industry field
        industries = item.get("industries", [])
        industry = industries[0] if industries else None
        
        return {
            "uuid": item.get("uuid"),
            "name": item.get("name"),
            "employees_count": item.get("employees_count"),
            "annual_revenue": item.get("annual_revenue"),
            "total_funding": item.get("total_funding"),
            "industry": industry,
            "city": item.get("city"),
            "state": item.get("state"),
            "country": item.get("country"),
            "website": item.get("website"),
            "linkedin_url": item.get("linkedin_url"),
            "phone_number": item.get("phone_number"),  # From metadata if available
            "technologies": item.get("technologies"),
            "keywords": item.get("keywords"),
        }

