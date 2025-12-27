"""Companies API endpoints providing CRUD operations and attribute lookups."""

from __future__ import annotations

import json
from typing import Any, Callable, Iterable, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    check_can_modify_resources,
    get_current_free_or_pro_user,
    get_current_user,
    resolve_pagination_params,
)
from app.clients.connectra_client import ConnectraClient, ConnectraClientError
from app.core.config import get_settings
from app.core.vql.parser import VQLParser
from app.core.vql.structures import VQLCondition, VQLFilter, VQLOperator
from app.db.session import get_db
from app.models.companies import Company
from app.models.user import User
from app.schemas.common import CountResponse, CursorPage
from app.schemas.companies import CompanyCreate, CompanyDetail, CompanyListItem, CompanyUpdate
from app.schemas.contacts import ContactListItem
from app.schemas.filters import (
    AttributeListParams,
    CompanyContactFilterParams,
    CompanyFilterParams,
    FilterDataRequest,
)
from app.schemas.vql import VQLFilterDataResponse, VQLFilterDefinition, VQLFiltersResponse, VQLQuery
from app.services.companies_service import CompaniesService
from app.services.contacts_service import ContactsService
from app.utils.cursor import decode_offset_cursor
from app.utils.pagination_cache import build_list_meta, build_pagination_links
from app.utils.logger import get_logger
from app.utils.streaming_queries import stream_query_results

logger = get_logger(__name__)
settings = get_settings()
router = APIRouter(prefix="/companies", tags=["Companies"])
service = CompaniesService()


# VQL-based endpoints
@router.post("/query", response_model=CursorPage[CompanyListItem])
async def query_companies(
    vql_query: VQLQuery,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CursorPage[CompanyListItem]:
    """
    Query companies using VQL (Vivek Query Language).
    
    This endpoint replaces the old GET /companies/ endpoint with a more flexible
    filter-based query system supporting complex conditions, field selection, and
    related entity population.
    """
    # Query companies using VQL
    results = await service.query_with_vql(session, vql_query)
    
    # Build pagination links
    request_url = str(request.url)
    limit = vql_query.limit
    offset = vql_query.offset
    
    next_link, previous_link = build_pagination_links(
        request_url, limit, offset, len(results), use_cursor=False
    )
    
    meta = build_list_meta(None, False, len(results), limit, False)
    
    return CursorPage(
        next=next_link,
        previous=previous_link,
        results=results,
        meta=meta,
    )


@router.post("/count", response_model=CountResponse)
async def count_companies_vql(
    vql_query: VQLQuery,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CountResponse:
    """
    Count companies matching VQL query.
    
    This endpoint replaces the old GET /companies/count/ endpoint.
    """
    return await service.count_with_vql(session, vql_query)


@router.get("/filters", response_model=VQLFiltersResponse)
async def get_company_filters(
    current_user: User = Depends(get_current_user),
) -> VQLFiltersResponse:
    """
    Get available filters for companies.
    
    Returns:
        List of filter definitions with metadata about each filterable field
    """
    async with ConnectraClient() as client:
        filters = await client.get_filters("company")
    
    # Convert dicts to VQLFilterDefinition objects
    filter_definitions = [VQLFilterDefinition(**filter_dict) for filter_dict in filters]
    return VQLFiltersResponse(data=filter_definitions)


@router.post("/filters/data", response_model=VQLFilterDataResponse)
async def get_company_filter_data(
    request: FilterDataRequest,
    current_user: User = Depends(get_current_user),
) -> VQLFilterDataResponse:
    """
    Get filter data values for a specific company filter.
    
    Args:
        request: Filter data request with service, filter_key, search_text, page, limit
        
    Returns:
        List of filter values matching the search criteria
    """
    # Validate service parameter
    if request.service not in ["contact", "company"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Service must be 'contact' or 'company'"
        )
    
    async with ConnectraClient() as client:
        data = await client.get_filter_data(
            service=request.service,
            filter_key=request.filter_key,
            search_text=request.search_text,
            page=request.page,
            limit=request.limit,
        )
    
    return VQLFilterDataResponse(data=data)


# Write key authentication removed - now using JWT authentication only
async def resolve_company_filters(request: Request) -> CompanyFilterParams:
    """Build company filter parameters from query string, preserving multi-value inputs."""
    query_params = request.query_params
    data = dict(query_params)
    multi_value_keys = (
        "exclude_industries",
        "exclude_keywords",
        "exclude_technologies",
        "exclude_locations",
    )
    for key in multi_value_keys:
        values = query_params.getlist(key)
        if values:
            data[key] = values
    try:
        return CompanyFilterParams.model_validate(data)
    except ValidationError as exc:
        first_error = exc.errors()[0] if exc.errors() else {}
        message = first_error.get("msg", "Invalid query parameters")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc


async def resolve_attribute_params(request: Request) -> AttributeListParams:
    """Parse attribute list query parameters without triggering raw bool coercion errors."""
    try:
        return AttributeListParams.model_validate(dict(request.query_params))
    except ValidationError as exc:
        first_error = exc.errors()[0] if exc.errors() else {}
        message = first_error.get("msg", "Invalid query parameters")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc


def _resolve_pagination(
    filters: CompanyFilterParams,
    limit: Optional[int],
) -> Optional[int]:
    """Choose the most appropriate page size within configured bounds."""
    return resolve_pagination_params(filters, limit, cap_explicit_limit=False)


def _parse_iterable_like(value: Any) -> Iterable[str]:
    """Best effort parsing for list-like attribute payloads."""
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item or "").strip()]

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []

        # Try parsing as JSON array first
        is_json_array = stripped.startswith("[") and stripped.endswith("]")
        is_postgres_array = stripped.startswith("{") and stripped.endswith("}")
        
        if is_json_array:
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item or "").strip()]
            except json.JSONDecodeError:
                pass

        # Try PostgreSQL array string representation {"a","b"}
        if is_postgres_array:
            transformed = "[" + stripped[1:-1] + "]"
            try:
                parsed = json.loads(transformed)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item or "").strip()]
            except json.JSONDecodeError:
                pass

        return [stripped]

    return [str(value).strip()]


def _normalize_array_values(values: Iterable[Any]) -> List[str]:
    """Flatten heterogeneous attribute values into a sorted, deduplicated list."""
    flattened: list[str] = []
    for entry in values:
        flattened.extend(_parse_iterable_like(entry))
    deduped: dict[str, str] = {}
    for token in flattened:
        if not token:
            continue
        key = token.lower()
        if key not in deduped:
            deduped[key] = token
    return sorted(deduped.values(), key=str.lower)





# All attribute listing endpoints removed - use VQL query endpoint with field selection instead


@router.get("/{company_uuid}/", response_model=CompanyDetail)
async def retrieve_company_by_uuid(
    company_uuid: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyDetail:
    """Retrieve a single company by UUID."""
    # Skip if this looks like it might be a company contacts route
    if company_uuid == "company":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    # Retrieving company detail with company UUID
    company = await service.get_company_by_uuid(session, company_uuid)
    # Retrieved company detail with company UUID
    return company


# ============================================================================
# Company Contacts Endpoints
# ============================================================================

def _resolve_company_contact_pagination(
    limit: Optional[int],
    offset: Optional[int],
    cursor: Optional[str],
    filters: "CompanyContactFilterParams",
) -> tuple[Optional[int], int, bool]:
    """Resolve pagination parameters for company contacts endpoint."""
    # Determine page limit
    if limit is not None:
        page_limit = limit
    elif filters.page_size is not None:
        page_limit = min(filters.page_size, settings.MAX_PAGE_SIZE) if settings.MAX_PAGE_SIZE else filters.page_size
    else:
        page_limit = None
    
    # Resolve offset and cursor
    use_cursor = False
    resolved_offset = offset or 0
    cursor_token = cursor or filters.cursor
    
    if cursor_token:
        try:
            resolved_offset = decode_offset_cursor(cursor_token)
            use_cursor = True
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid cursor value",
            ) from exc
    elif offset == 0 and filters.page is not None and page_limit is not None:
        # Only use filters.page if no explicit offset was provided
        resolved_offset = (filters.page - 1) * page_limit
    
    return page_limit, resolved_offset, use_cursor


async def resolve_company_contact_filters(request: Request) -> "CompanyContactFilterParams":
    """Build company contact filter parameters from query string."""
    query_params = request.query_params
    data = dict(query_params)
    multi_value_keys = (
        "exclude_titles",
        "exclude_contact_locations",
        "exclude_seniorities",
        "exclude_departments",
    )
    for key in multi_value_keys:
        values = query_params.getlist(key)
        if values:
            data[key] = values
    try:
        return CompanyContactFilterParams.model_validate(data)
    except ValidationError as exc:
        first_error = exc.errors()[0] if exc.errors() else {}
        message = first_error.get("msg", "Invalid query parameters")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc


@router.get("/company/{company_uuid}/contacts/", response_model=CursorPage[ContactListItem])
async def list_company_contacts(
    company_uuid: str,
    request: Request,
    filters: "CompanyContactFilterParams" = Depends(resolve_company_contact_filters),
    limit: Optional[int] = Query(None, ge=1),
    offset: Optional[int] = Query(0, ge=0),
    cursor: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CursorPage[ContactListItem]:
    """Return a paginated list of contacts for a specific company."""
    page_limit, resolved_offset, use_cursor = _resolve_company_contact_pagination(
        limit, offset, cursor, filters
    )
    
    active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
    
    contacts_service = ContactsService()
    page = await contacts_service.list_contacts_by_company(
        session,
        company_uuid,
        filters,
        limit=page_limit,
        offset=resolved_offset,
        request_url=str(request.url),
        use_cursor=use_cursor,
    )
    
    return page


@router.get("/company/{company_uuid}/contacts/count/", response_model=CountResponse)
async def count_company_contacts(
    company_uuid: str,
    filters: "CompanyContactFilterParams" = Depends(resolve_company_contact_filters),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CountResponse:
    """Return the total count of contacts for a specific company matching filters."""
    active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
    
    contacts_service = ContactsService()
    count = await contacts_service.count_contacts_by_company(
        session,
        company_uuid,
        filters,
    )
    
    return count


@router.get("/company/{company_uuid}/contacts/filters", response_model=VQLFiltersResponse)
async def get_company_contact_filters(
    company_uuid: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> VQLFiltersResponse:
    """
    Get available filters for contacts within a specific company.
    
    Args:
        company_uuid: Company UUID to scope filters to
        
    Returns:
        List of filter definitions with metadata about each filterable field
    """
    # Verify company exists
    async with ConnectraClient() as client:
        try:
            await client.get_company_by_uuid(company_uuid)
        except ConnectraClientError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )
        
        # Return same filters as contacts (they're the same entity type)
        filters = await client.get_filters("contact")
    
    # Convert dicts to VQLFilterDefinition objects
    filter_definitions = [VQLFilterDefinition(**filter_dict) for filter_dict in filters]
    return VQLFiltersResponse(data=filter_definitions)


@router.post("/company/{company_uuid}/contacts/filters/data", response_model=VQLFilterDataResponse)
async def get_company_contact_filter_data(
    company_uuid: str,
    request: FilterDataRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> VQLFilterDataResponse:
    """
    Get filter data values for contacts within a specific company.
    
    Args:
        company_uuid: Company UUID to scope filter data to
        request: Filter data request with service, filter_key, search_text, page, limit
        
    Returns:
        List of filter values matching the search criteria, scoped to contacts in this company
    """
    # Validate service parameter
    if request.service not in ["contact", "company"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Service must be 'contact' or 'company'"
        )
    
    async with ConnectraClient() as client:
        # Verify company exists
        try:
            await client.get_company_by_uuid(company_uuid)
        except ConnectraClientError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )
        
        # Build VQL query to get contacts filtered by company_id
        # Create filter with company_id condition
        company_filter = VQLFilter(
            and_=[
                VQLCondition(
                    field="company_id",
                    operator=VQLOperator.EQ,
                    value=company_uuid
                )
            ]
        )
        
        # Query contacts with company filter
        # Use a reasonable limit to get enough data for distinct values
        # Note: For large companies, we may need pagination
        vql_query = VQLQuery(
            filters=company_filter,
            limit=1000,  # Get enough contacts to extract distinct values
            offset=0
        )
        
        # Get contacts
        response = await client.search_contacts(vql_query)
        contacts = response.get("data", [])
        
        # Extract distinct values for the requested filter_key
        distinct_values = set()
        for contact in contacts:
            value = contact.get(request.filter_key)
            if value is not None:
                # Handle array fields (e.g., departments)
                if isinstance(value, list):
                    distinct_values.update(str(v) for v in value if v)
                else:
                    distinct_values.add(str(value))
        
        # Apply search_text filter if provided
        if request.search_text:
            search_lower = request.search_text.lower()
            distinct_values = {
                v for v in distinct_values
                if search_lower in v.lower()
            }
        
        # Sort and paginate
        sorted_values = sorted(distinct_values, key=str.lower)
        
        # Apply pagination
        start_idx = (request.page - 1) * request.limit
        end_idx = start_idx + request.limit
        paginated_values = sorted_values[start_idx:end_idx]
        
        return VQLFilterDataResponse(data=paginated_values)

