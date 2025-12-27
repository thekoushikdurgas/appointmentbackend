"""Service layer orchestrating company repository operations and transformations."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Callable, Iterable, List, Optional
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.connectra_client import ConnectraClient
from app.core.config import get_settings
from app.core.vql.structures import VQLCondition, VQLFilter, VQLOperator, VQLQuery
from app.schemas.common import CountResponse, CursorPage
from app.schemas.companies import (
    CompanyCreate,
    CompanyDetail,
    CompanyListItem,
    CompanyMetadataOut,
    CompanyUpdate,
)
from app.schemas.filters import AttributeListParams, CompanyFilterParams
from app.services.base import BaseService
from app.services.vql_converter import VQLConverter
from app.services.vql_transformer import VQLTransformer
from app.utils.batch_lookup import batch_fetch_company_metadata_by_uuids
from app.utils.normalization import (
    normalize_sequence,
    normalize_text,
)
from app.utils.pagination_cache import (
    build_list_meta,
    build_pagination_links,
    cache_list_result,
    get_cached_list_result,
)

if TYPE_CHECKING:
    pass  # VQLQuery is now imported at top level

logger = logging.getLogger(__name__)
settings = get_settings()


class CompaniesService(BaseService):
    """Business logic for retrieving and shaping company data."""

    def __init__(self) -> None:
        """Initialize the service."""
        super().__init__()

    async def create_company(
        self,
        session: AsyncSession,
        payload: CompanyCreate,
    ) -> CompanyDetail:
        """Create a new company via Connectra API and return the hydrated detail schema."""
        data = payload.model_dump()
        normalized_uuid = normalize_text(data.get("uuid"), allow_placeholder=False)
        data["uuid"] = normalized_uuid or uuid4().hex

        for field in (
            "name",
            "address",
            "text_search",
        ):
            data[field] = normalize_text(data.get(field))

        for field in ("employees_count", "annual_revenue", "total_funding"):
            if data.get(field) is not None and data[field] < 0:
                data[field] = None

        industries = normalize_sequence(data.get("industries"))
        data["industries"] = industries or None

        keywords = normalize_sequence(data.get("keywords"))
        data["keywords"] = keywords or None

        technologies = normalize_sequence(data.get("technologies"))
        data["technologies"] = technologies or None

        # Create company via Connectra API
        async with ConnectraClient() as client:
            result = await client.create_company(data)
        
        # Invalidate companies list cache on creation
        await self._invalidate_on_create("companies")
        
        # Fetch the created company detail
        company_uuid = result.get("data", {}).get("uuid") if "data" in result else result.get("uuid")
        if not company_uuid:
            raise ValueError("Company creation did not return a valid UUID")
        
        detail = await self.get_company_by_uuid(session, company_uuid)
        return detail

    async def update_company(
        self,
        session: AsyncSession,
        company_uuid: str,
        payload: CompanyUpdate,
    ) -> CompanyDetail:
        """Update an existing company via Connectra API and return the hydrated detail schema."""
        data = payload.model_dump(exclude_unset=True)
        
        for field in ("name", "address", "text_search"):
            if field in data:
                data[field] = normalize_text(data.get(field))

        for field in ("employees_count", "annual_revenue", "total_funding"):
            if field in data and data[field] is not None and data[field] < 0:
                data[field] = None

        if "industries" in data:
            industries = normalize_sequence(data.get("industries"))
            data["industries"] = industries or None

        if "keywords" in data:
            keywords = normalize_sequence(data.get("keywords"))
            data["keywords"] = keywords or None

        if "technologies" in data:
            technologies = normalize_sequence(data.get("technologies"))
            data["technologies"] = technologies or None

        # Update company via Connectra API
        async with ConnectraClient() as client:
            result = await client.update_company(company_uuid, data)
        
        if not result or not result.get("success", True):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        
        # Invalidate companies list cache on update
        await self._invalidate_on_update("companies")
        
        detail = await self.get_company_by_uuid(session, company_uuid)
        return detail

    async def delete_company(
        self,
        session: AsyncSession,
        company_uuid: str,
    ) -> None:
        """Delete a company via Connectra API."""
        async with ConnectraClient() as client:
            await client.delete_company(company_uuid)
        
        # Invalidate companies list cache on deletion
        await self._invalidate_on_delete("companies")

    async def list_companies(
        self,
        session: AsyncSession,
        filters: CompanyFilterParams,
        *,
        limit: Optional[int],
        offset: int,
        request_url: str,
        use_cursor: bool = False,
    ) -> CursorPage[CompanyListItem]:
        """List companies using Connectra and build pagination metadata."""

        # Check cache if enabled and query is cacheable
        cached_result = await get_cached_list_result(
            "companies", filters, limit, offset, use_cursor
        )
        if cached_result:
            return CursorPage(**cached_result)
        
        try:
            # Convert filters to VQL query
            converter = VQLConverter()
            vql_query = converter.convert_company_filters_to_vql(
                filters,
                limit=limit,
                offset=offset
            )
            
            # Query Connectra
            async with ConnectraClient() as client:
                response = await client.search_companies(vql_query)
                transformer = VQLTransformer()
                results = transformer.transform_company_response(response)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except Exception as exc:
            logger.error(f"Connectra query failed: {exc}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Company service temporarily unavailable"
            ) from exc

        # Build pagination links
        next_link, previous_link = build_pagination_links(
            request_url, limit, offset, len(results), use_cursor
        )
        
        # Build meta information
        meta = build_list_meta(filters, use_cursor, len(results), limit, False)  # No replica with Connectra
        
        page = CursorPage(next=next_link, previous=previous_link, results=results, meta=meta)
        
        # Cache result if enabled and query is cacheable
        await cache_list_result("companies", page, filters, limit, offset, use_cursor)
        
        return page

    async def count_companies(
        self,
        session: AsyncSession,
        filters: CompanyFilterParams,
    ) -> CountResponse:
        """Count companies that match the provided filters using Connectra."""

        try:
            # Convert filters to VQL query
            converter = VQLConverter()
            vql_query = converter.convert_company_filters_to_vql(filters)
            
            # Query Connectra
            async with ConnectraClient() as client:
                total = await client.count_companies(vql_query)
                return CountResponse(count=total)
        except Exception as exc:
            logger.error(f"Connectra count failed: {exc}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Company service temporarily unavailable"
            ) from exc

    async def get_uuids_by_filters(
        self,
        session: AsyncSession,
        filters: CompanyFilterParams,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[str]:
        """Return company UUIDs that match the supplied filters using Connectra."""

        try:
            # Convert filters to VQL query
            converter = VQLConverter()
            vql_query = converter.convert_company_filters_to_vql(filters, limit=limit, offset=offset)
            
            # Query Connectra
            async with ConnectraClient() as client:
                response = await client.search_companies(vql_query)
                data = response.get("data", [])
                return [item.get("uuid") for item in data if item.get("uuid")]
        except Exception as exc:
            logger.error(f"Connectra UUID query failed: {exc}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Company service temporarily unavailable"
            ) from exc

    async def get_company(
        self,
        session: AsyncSession,
        company_uuid: str,
    ) -> CompanyDetail:
        """Fetch a single company with related data using Connectra."""
        # Delegate to get_company_by_uuid which uses Connectra
        return await self.get_company_by_uuid(session, company_uuid)

    async def get_company_by_uuid(
        self,
        session: AsyncSession,
        company_uuid: str,
    ) -> CompanyDetail:
        """Fetch a single company by UUID with related data using Connectra."""

        try:
            async with ConnectraClient() as client:
                # Use VQL query to get company
                condition = VQLCondition(
                    field="uuid",
                    operator=VQLOperator.EQ,
                    value=company_uuid
                )
                filter_obj = VQLFilter(and_=[condition])
                vql_query = VQLQuery(
                    filters=filter_obj,
                    limit=1,
                    offset=0
                )
                
                response = await client.search_companies(vql_query)
                data = response.get("data", [])
                if data:
                    transformer = VQLTransformer()
                    companies = transformer.transform_company_response({"data": data})
                    if companies:
                        company_item = companies[0]
                        # Convert CompanyListItem to CompanyDetail
                        detail = CompanyDetail(
                            **company_item.model_dump(),
                            created_at=None,  # Will be in response if available
                            updated_at=None,  # Will be in response if available
                        )
                        return detail
        except Exception as exc:
            logger.error(f"Connectra query failed for company {company_uuid}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Company service temporarily unavailable"
            ) from exc

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    async def list_attribute_values(
        self,
        session: AsyncSession,
        filters: CompanyFilterParams,
        params: AttributeListParams,
        column_factory: Callable[[Company, CompanyMetadata], Iterable],
        *,
        array_mode: bool = False,
    ) -> List[str]:
        """Return a list of attribute values for companies."""
        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
        try:
            values = await self.repository.list_attribute_values(
                session,
                filters,
                params,
                array_mode=array_mode,
                column_factory=column_factory,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return values

    def _hydrate_company(
        self,
        company: Company,
        company_meta: Optional[CompanyMetadata],
    ) -> CompanyListItem:
        """Construct a company list item schema from ORM entities."""
        industries = normalize_sequence(company.industries)
        keywords = normalize_sequence(company.keywords)
        technologies = normalize_sequence(company.technologies)

        industry = ", ".join(industries) if industries else None

        item = CompanyListItem(
            uuid=company.uuid,
            name=normalize_text(company.name),
            employees_count=company.employees_count,
            annual_revenue=company.annual_revenue,
            total_funding=company.total_funding,
            industry=industry,
            city=normalize_text(company_meta.city if company_meta else None),
            state=normalize_text(company_meta.state if company_meta else None),
            country=normalize_text(company_meta.country if company_meta else None),
            website=normalize_text(company_meta.website if company_meta else None),
            linkedin_url=normalize_text(company_meta.linkedin_url if company_meta else None),
            phone_number=normalize_text(company_meta.phone_number if company_meta else None),
            technologies=technologies or None,
            keywords=keywords or None,
            metadata=self._company_metadata(company_meta),
        )
        return item

    def _company_metadata(
        self,
        company_meta: Optional[CompanyMetadata],
    ):
        """Convert company metadata ORM instance into a response schema."""
        if not company_meta:
            return None
        metadata = CompanyMetadataOut(
            uuid=company_meta.uuid,
            linkedin_url=normalize_text(company_meta.linkedin_url),
            facebook_url=normalize_text(company_meta.facebook_url),
            twitter_url=normalize_text(company_meta.twitter_url),
            website=normalize_text(company_meta.website),
            company_name_for_emails=normalize_text(company_meta.company_name_for_emails),
            phone_number=normalize_text(company_meta.phone_number),
            latest_funding=normalize_text(company_meta.latest_funding),
            latest_funding_amount=company_meta.latest_funding_amount,
            last_raised_at=normalize_text(company_meta.last_raised_at),
            city=normalize_text(company_meta.city),
            state=normalize_text(company_meta.state),
            country=normalize_text(company_meta.country),
        )
        return metadata

    # VQL Query Methods
    async def query_with_vql(
        self,
        session: AsyncSession,
        vql_query: "VQLQuery",
    ) -> List[CompanyListItem]:
        """
        Query companies using VQL via Connectra and return hydrated CompanyListItem objects.

        Args:
            session: Database session (kept for compatibility, not used)
            vql_query: VQL query object

        Returns:
            List of CompanyListItem objects
        """

        try:
            async with ConnectraClient() as client:
                response = await client.search_companies(vql_query)
                transformer = VQLTransformer()
                results = transformer.transform_company_response(response)
                return results
        except Exception as exc:
            logger.error(f"Connectra query failed: {exc}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Company service temporarily unavailable"
            ) from exc

    async def count_with_vql(
        self,
        session: AsyncSession,
        vql_query: "VQLQuery",
    ) -> CountResponse:
        """
        Count companies matching VQL query via Connectra.

        Args:
            session: Database session (kept for compatibility, not used)
            vql_query: VQL query object

        Returns:
            CountResponse with count
        """

        try:
            async with ConnectraClient() as client:
                count = await client.count_companies(vql_query)
                return CountResponse(count=count)
        except Exception as exc:
            logger.error(f"Connectra count failed: {exc}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Company service temporarily unavailable"
            ) from exc


