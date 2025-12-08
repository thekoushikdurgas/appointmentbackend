"""Companies API endpoints providing CRUD operations and attribute lookups."""

from __future__ import annotations

import json
from typing import Any, Callable, Iterable, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    check_can_modify_resources,
    get_current_free_or_pro_user,
    get_current_user,
    resolve_pagination_params,
)
from app.core.config import get_settings
from app.db.session import get_db
from app.models.companies import Company
from app.models.user import User
from app.schemas.common import CountResponse, CursorPage, UuidListResponse
from app.schemas.companies import CompanyCreate, CompanyDetail, CompanyListItem, CompanyUpdate
from app.schemas.contacts import ContactListItem
from app.schemas.filters import AttributeListParams, CompanyContactFilterParams, CompanyFilterParams
from app.services.companies_service import CompaniesService
from app.services.contacts_service import ContactsService
from app.utils.cursor import decode_offset_cursor
from app.utils.streaming_queries import stream_query_results


settings = get_settings()
router = APIRouter(prefix="/companies", tags=["Companies"])
service = CompaniesService()


async def require_companies_write_key(
    companies_write_key: Optional[str] = Header(None, alias="X-Companies-Write-Key"),
) -> None:
    """Ensure write requests include the configured authorization key."""
    configured_key = (settings.COMPANIES_WRITE_KEY or "").strip()
    if not configured_key:
        # Companies write key is not configured; denying write access
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if companies_write_key != configured_key:
        # Companies write key mismatch; denying request
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


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


@router.get("/", response_model=CursorPage[CompanyListItem])
async def list_companies(
    request: Request,
    filters: CompanyFilterParams = Depends(resolve_company_filters),
    limit: Optional[int] = Query(None, ge=1),
    offset: Optional[int] = Query(0, ge=0),
    cursor: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CursorPage[CompanyListItem]:
    """Return a paginated list of companies."""
    raw_path = request.scope.get("raw_path")
    if isinstance(raw_path, (bytes, bytearray)):
        raw_path_text = raw_path.decode("latin-1", errors="ignore")
    else:
        raw_path_text = str(raw_path) if raw_path is not None else request.url.path
    if "/companies//" in raw_path_text:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    page_limit = _resolve_pagination(filters, limit)
    use_cursor = False
    resolved_offset = offset or 0
    cursor_token = cursor or filters.cursor
    if cursor_token:
        try:
            resolved_offset = decode_offset_cursor(cursor_token)
        except ValueError as exc:
            # Warning condition: Invalid cursor token supplied with token and error details
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid cursor value",
            ) from exc
        use_cursor = True
    elif offset == 0 and filters.page is not None and page_limit is not None:
        # Only use filters.page if no explicit offset was provided (offset defaults to 0)
        resolved_offset = (filters.page - 1) * page_limit

    active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())

    page = await service.list_companies(
        session,
        filters,
        limit=page_limit,
        offset=resolved_offset,
        request_url=str(request.url),
        use_cursor=use_cursor,
    )

    return page


@router.get("/stream/")
async def stream_companies(
    request: Request,
    filters: CompanyFilterParams = Depends(resolve_company_filters),
    format: str = Query("jsonl", regex="^(jsonl|csv)$"),
    max_results: Optional[int] = Query(None, ge=1, description="Maximum results to stream"),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """
    Stream companies as JSONL or CSV for large datasets.
    
    This endpoint is optimized for large result sets and streams data in chunks
    without loading everything into memory. Use this for exports or bulk operations.
    
    Formats:
    - jsonl: Newline-delimited JSON (one JSON object per line)
    - csv: Comma-separated values with header row
    
    Example:
        GET /api/v1/companies/stream/?format=jsonl&name=example
    """
    if not settings.ENABLE_STREAMING_QUERIES:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Streaming queries are disabled",
        )
    
    # Apply max_results limit from settings if not specified
    if max_results is None and settings.MAX_STREAMING_RESULTS:
        max_results = settings.MAX_STREAMING_RESULTS
    
    # Build query - simplified for streaming
    query = select(Company)
    
    # Apply basic filters
    if filters.name:
        query = query.where(Company.name.ilike(f"%{filters.name}%"))
    if filters.address:
        query = query.where(Company.address.ilike(f"%{filters.address}%"))
    
    async def generate_jsonl():
        """Generate JSONL stream using optimized serialization."""
        from pydantic import TypeAdapter
        
        count = 0
        # Use TypeAdapter for efficient JSON serialization
        adapter = TypeAdapter(dict)
        
        async for batch in stream_query_results(
            session,
            query,
            batch_size=settings.STREAMING_BATCH_SIZE,
            max_results=max_results,
        ):
            for company in batch:
                company_dict = {
                    "uuid": company.uuid,
                    "name": company.name,
                    "address": company.address,
                    "employees_count": company.employees_count,
                    "annual_revenue": company.annual_revenue,
                    "total_funding": company.total_funding,
                }
                # Use TypeAdapter for faster serialization
                json_line = adapter.dump_json(company_dict).decode("utf-8") + "\n"
                yield json_line
                count += 1
                if max_results and count >= max_results:
                    break
    
    async def generate_csv():
        """Generate CSV stream."""
        import csv
        from io import StringIO
        
        # Write header
        header = ["uuid", "name", "address", "employees_count", "annual_revenue", "total_funding"]
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(header)
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
        
        count = 0
        async for batch in stream_query_results(
            session,
            query,
            batch_size=settings.STREAMING_BATCH_SIZE,
            max_results=max_results,
        ):
            for company in batch:
                writer.writerow([
                    company.uuid,
                    company.name or "",
                    company.address or "",
                    company.employees_count or "",
                    company.annual_revenue or "",
                    company.total_funding or "",
                ])
                yield buffer.getvalue()
                buffer.seek(0)
                buffer.truncate(0)
                count += 1
                if max_results and count >= max_results:
                    break
    
    if format == "jsonl":
        return StreamingResponse(
            generate_jsonl(),
            media_type="application/x-ndjson",
            headers={
                "Content-Disposition": "attachment; filename=companies.jsonl",
            },
        )
    else:  # csv
        return StreamingResponse(
            generate_csv(),
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=companies.csv",
            },
        )


@router.get("/count/", response_model=CountResponse)
async def count_companies(
    filters: CompanyFilterParams = Depends(resolve_company_filters),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CountResponse:
    """Return the total number of companies that match the provided filters."""
    active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
    # Counting companies with filters
    count = await service.count_companies(session, filters)
    # Counted companies with filters and total count
    return count


@router.get("/count/uuids/", response_model=UuidListResponse)
async def get_company_uuids(
    filters: CompanyFilterParams = Depends(resolve_company_filters),
    offset: int = Query(0, ge=0, description="Number of UUIDs to skip before returning results"),
    limit: Optional[int] = Query(None, ge=1, description="Limit the number of UUIDs returned. If not provided, returns all matching UUIDs."),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UuidListResponse:
    """Return company UUIDs that match the provided filters."""
    active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
    # Getting company UUIDs with filters, offset, and limit
    uuids = await service.get_uuids_by_filters(session, filters, limit, offset)
    # Retrieved company UUIDs with filters and count
    return UuidListResponse(count=len(uuids), uuids=uuids)


@router.post("/", response_model=CompanyDetail, status_code=status.HTTP_201_CREATED)
async def create_company(
    payload: CompanyCreate,
    current_user: User = Depends(get_current_free_or_pro_user),  # Free and Pro users can create
    _: None = Depends(require_companies_write_key),
    session: AsyncSession = Depends(get_db),
) -> CompanyDetail:
    """Create a new company with optional fields.
    
    Free users and Pro users can create companies.
    """
    # Creating company via API with user ID
    company = await service.create_company(session, payload)
    # Created company via API with UUID
    return company


@router.put("/{company_uuid}/", response_model=CompanyDetail)
async def update_company(
    company_uuid: str,
    payload: CompanyUpdate,
    current_user: User = Depends(check_can_modify_resources),  # Only Pro users and above can update
    _: None = Depends(require_companies_write_key),
    session: AsyncSession = Depends(get_db),
) -> CompanyDetail:
    """Update an existing company.
    
    Only Pro users, Admin, and Super Admin can update companies.
    Free users can only create and read.
    """
    # Updating company via API with company UUID and user ID
    company = await service.update_company(session, company_uuid, payload)
    # Updated company via API with company UUID
    return company


@router.delete(
    "/{company_uuid}/",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_company(
    company_uuid: str,
    current_user: User = Depends(check_can_modify_resources),  # Only Pro users and above can delete
    _: None = Depends(require_companies_write_key),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Delete a company.
    
    Only Pro users, Admin, and Super Admin can delete companies.
    Free users can only create and read.
    """
    # Deleting company via API with company UUID and user ID
    await service.delete_company(session, company_uuid)
    # Deleted company via API with company UUID


async def _attribute_endpoint(
    session: AsyncSession,
    filters: CompanyFilterParams,
    params: AttributeListParams,
    column_factory: Callable,
    attribute_label: str,
    *,
    array_mode: bool = False,
) -> List[str]:
    """Shared handler for list-of-values endpoints."""
    effective_params = params
    forced_distinct = False
    if array_mode and not params.distinct:
        forced_distinct = True
        effective_params = params.model_copy(update={"distinct": True})
        # Forcing distinct parameters for array attribute

    if params.limit is not None and params.limit <= 0:
        # Warning condition: Attribute list rejected due to non-positive limit with attribute label and limit
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="limit must be a positive integer",
        )
    if params.offset is not None and params.offset < 0:
        # Warning condition: Attribute list rejected due to negative offset with attribute label and offset
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="offset must be zero or greater",
        )

    # Listing company attribute values with attribute label, distinct flag, limit, and offset
    values = await service.list_attribute_values(
        session,
        filters,
        effective_params,
        column_factory=column_factory,
        array_mode=array_mode,
    )
    distinct_requested = effective_params.distinct or forced_distinct
    if distinct_requested:
        # Repository already applies distinct; guard to ensure uniqueness after post-processing.
        seen = set()
        unique_values = []
        for value in values:
            if value is None:
                continue
            normalized = value.lower() if isinstance(value, str) else str(value)
            if normalized not in seen:
                seen.add(normalized)
                unique_values.append(value)
        # Deduplicated attribute values with attribute label, before count, and after count
        return unique_values
    # Listed company attribute values with attribute label and count
    return values


@router.get("/name/", response_model=List[str])
async def list_company_names(
    filters: CompanyFilterParams = Depends(resolve_company_filters),
    params: AttributeListParams = Depends(resolve_attribute_params),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[str]:
    """Return company names filtered by the supplied parameters."""
    return await _attribute_endpoint(
        session,
        filters,
        params,
        lambda Company, CompanyMetadata: Company.name,
        "name",
    )


@router.get("/industry/", response_model=List[str])
async def list_industries(
    filters: CompanyFilterParams = Depends(resolve_company_filters),
    params: AttributeListParams = Depends(resolve_attribute_params),
    separated: bool = Query(False),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[str]:
    """Return industry values sourced from companies."""
    column_factory = (
        (
            lambda Company, CompanyMetadata: Company.industries
        )
        if separated
        else (
            lambda Company, CompanyMetadata: func.array_to_string(
                Company.industries, ","
            )
        )
    )
    values = await _attribute_endpoint(
        session,
        filters,
        params,
        column_factory,
        "industry",
        array_mode=separated,
    )
    if separated:
        deduped = _normalize_array_values(values)
        if params.limit:
            deduped = deduped[: params.limit]
        # Separated industry values count
        return deduped
    filtered = [value for value in values if value]
    # Collapsed industry values count
    return filtered


@router.get("/keywords/", response_model=List[str])
async def list_keywords(
    filters: CompanyFilterParams = Depends(resolve_company_filters),
    params: AttributeListParams = Depends(resolve_attribute_params),
    separated: bool = Query(False),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[str]:
    """Return keyword values for companies, optionally split into unique tokens."""
    column_factory = (
        (
            lambda Company, CompanyMetadata: Company.keywords
        )
        if separated
        else (
            lambda Company, CompanyMetadata: func.array_to_string(
                Company.keywords, ","
            )
        )
    )
    values = await _attribute_endpoint(
        session,
        filters,
        params,
        column_factory,
        "keywords",
        array_mode=separated,
    )
    if separated:
        deduped = _normalize_array_values(values)
        if params.limit:
            deduped = deduped[: params.limit]
        # Separated keyword values count
        return deduped
    filtered = [value for value in values if value]
    # Collapsed keyword values count
    return filtered


@router.get("/technologies/", response_model=List[str])
async def list_technologies(
    filters: CompanyFilterParams = Depends(resolve_company_filters),
    params: AttributeListParams = Depends(resolve_attribute_params),
    separated: bool = Query(False),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[str]:
    """Return technology values for companies."""
    column_factory = (
        (
            lambda Company, CompanyMetadata: Company.technologies
        )
        if separated
        else (
            lambda Company, CompanyMetadata: func.array_to_string(
                Company.technologies, ","
            )
        )
    )
    values = await _attribute_endpoint(
        session,
        filters,
        params,
        column_factory,
        "technologies",
        array_mode=separated,
    )
    if separated:
        deduped = _normalize_array_values(values)
        if params.limit:
            deduped = deduped[: params.limit]
        # Separated technology values count
        return deduped
    filtered = [value for value in values if value]
    # Collapsed technology values count
    return filtered


@router.get("/address/", response_model=List[str])
async def list_company_addresses(
    filters: CompanyFilterParams = Depends(resolve_company_filters),
    params: AttributeListParams = Depends(resolve_attribute_params),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[str]:
    """Return company address text sourced from the text search column."""
    return await _attribute_endpoint(
        session,
        filters,
        params,
        lambda Company, CompanyMetadata: Company.text_search,
        "address",
    )


@router.get("/city/", response_model=List[str])
async def list_company_cities(
    filters: CompanyFilterParams = Depends(resolve_company_filters),
    params: AttributeListParams = Depends(resolve_attribute_params),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[str]:
    """Return distinct company city values."""
    return await _attribute_endpoint(
        session,
        filters,
        params,
        lambda Company, CompanyMetadata: CompanyMetadata.city,
        "city",
    )


@router.get("/state/", response_model=List[str])
async def list_company_states(
    filters: CompanyFilterParams = Depends(resolve_company_filters),
    params: AttributeListParams = Depends(resolve_attribute_params),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[str]:
    """Return distinct company state values."""
    return await _attribute_endpoint(
        session,
        filters,
        params,
        lambda Company, CompanyMetadata: CompanyMetadata.state,
        "state",
    )


@router.get("/country/", response_model=List[str])
async def list_company_countries(
    filters: CompanyFilterParams = Depends(resolve_company_filters),
    params: AttributeListParams = Depends(resolve_attribute_params),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[str]:
    """Return distinct company country values."""
    return await _attribute_endpoint(
        session,
        filters,
        params,
        lambda Company, CompanyMetadata: CompanyMetadata.country,
        "country",
    )


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


@router.get("/company/{company_uuid}/contacts/count/uuids/", response_model=UuidListResponse)
async def get_company_contact_uuids(
    company_uuid: str,
    filters: "CompanyContactFilterParams" = Depends(resolve_company_contact_filters),
    offset: int = Query(0, ge=0, description="Number of UUIDs to skip before returning results"),
    limit: Optional[int] = Query(None, ge=1, description="Limit the number of UUIDs returned. If not provided, returns all matching UUIDs."),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UuidListResponse:
    """Return contact UUIDs for a specific company that match the provided filters."""
    active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
    # Getting contact UUIDs for company with company UUID, filters, offset, and limit
    
    contacts_service = ContactsService()
    uuids = await contacts_service.get_uuids_by_company(
        session,
        company_uuid,
        filters,
        limit,
        offset,
    )
    
    # Retrieved number of contact UUIDs for company with company UUID
    return UuidListResponse(count=len(uuids), uuids=uuids)


async def _company_contact_attribute_endpoint(
    company_uuid: str,
    session: AsyncSession,
    filters: "CompanyContactFilterParams",
    params: AttributeListParams,
    attribute: str,
) -> List[str]:
    """Helper for company contact attribute endpoints."""
    # Listing attribute for company contacts with attribute, company UUID, filters, and params
    
    contacts_service = ContactsService()
    values = await contacts_service.list_attribute_values_by_company(
        session,
        company_uuid,
        attribute,
        filters,
        params,
    )
    
    # Listed number of distinct attribute values for company contacts with attribute and company UUID
    return values


@router.get("/company/{company_uuid}/contacts/first_name/", response_model=List[str])
async def list_company_contact_first_names(
    company_uuid: str,
    filters: "CompanyContactFilterParams" = Depends(resolve_company_contact_filters),
    params: AttributeListParams = Depends(resolve_attribute_params),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[str]:
    """Return distinct first name values for contacts in a specific company."""
    return await _company_contact_attribute_endpoint(
        company_uuid,
        session,
        filters,
        params,
        "first_name",
    )


@router.get("/company/{company_uuid}/contacts/last_name/", response_model=List[str])
async def list_company_contact_last_names(
    company_uuid: str,
    filters: "CompanyContactFilterParams" = Depends(resolve_company_contact_filters),
    params: AttributeListParams = Depends(resolve_attribute_params),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[str]:
    """Return distinct last name values for contacts in a specific company."""
    return await _company_contact_attribute_endpoint(
        company_uuid,
        session,
        filters,
        params,
        "last_name",
    )


@router.get("/company/{company_uuid}/contacts/title/", response_model=List[str])
async def list_company_contact_titles(
    company_uuid: str,
    filters: "CompanyContactFilterParams" = Depends(resolve_company_contact_filters),
    params: AttributeListParams = Depends(resolve_attribute_params),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[str]:
    """Return distinct title values for contacts in a specific company."""
    return await _company_contact_attribute_endpoint(
        company_uuid,
        session,
        filters,
        params,
        "title",
    )


@router.get("/company/{company_uuid}/contacts/seniority/", response_model=List[str])
async def list_company_contact_seniorities(
    company_uuid: str,
    filters: "CompanyContactFilterParams" = Depends(resolve_company_contact_filters),
    params: AttributeListParams = Depends(resolve_attribute_params),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[str]:
    """Return distinct seniority values for contacts in a specific company."""
    return await _company_contact_attribute_endpoint(
        company_uuid,
        session,
        filters,
        params,
        "seniority",
    )


@router.get("/company/{company_uuid}/contacts/department/", response_model=List[str])
async def list_company_contact_departments(
    company_uuid: str,
    filters: "CompanyContactFilterParams" = Depends(resolve_company_contact_filters),
    params: AttributeListParams = Depends(resolve_attribute_params),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[str]:
    """Return distinct department values for contacts in a specific company."""
    return await _company_contact_attribute_endpoint(
        company_uuid,
        session,
        filters,
        params,
        "department",
    )


@router.get("/company/{company_uuid}/contacts/email_status/", response_model=List[str])
async def list_company_contact_email_statuses(
    company_uuid: str,
    filters: "CompanyContactFilterParams" = Depends(resolve_company_contact_filters),
    params: AttributeListParams = Depends(resolve_attribute_params),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[str]:
    """Return distinct email status values for contacts in a specific company."""
    return await _company_contact_attribute_endpoint(
        company_uuid,
        session,
        filters,
        params,
        "email_status",
    )

