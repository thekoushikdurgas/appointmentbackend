"""Contacts API endpoints providing list and attribute lookups."""

from __future__ import annotations

import json
import time
from typing import Any, Callable, Iterable, List, Optional, Union

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    check_can_modify_resources,
    get_current_free_or_pro_user,
    get_current_user,
    resolve_pagination_params,
)
from app.core.config import get_settings
from app.db.session import get_db
from app.models.contacts import Contact
from app.models.user import User
from app.repositories.contacts import ContactRepository
from app.schemas.common import CountResponse, CursorPage, UuidListResponse
from app.schemas.contacts import ContactCreate, ContactDetail, ContactListItem, ContactSimpleItem
from app.schemas.filters import AttributeListParams, ContactFilterParams
from app.services.contacts_service import ContactsService
from app.utils.cursor import decode_offset_cursor
from app.utils.normalization import normalize_list_param
from app.utils.streaming_queries import stream_query_results


settings = get_settings()
router = APIRouter(prefix="/contacts", tags=["Contacts"])
service = ContactsService()


async def require_contacts_write_key(
    contacts_write_key: Optional[str] = Header(None, alias="X-Contacts-Write-Key"),
) -> None:
    """Ensure write requests include the configured authorization key."""
    configured_key = (settings.CONTACTS_WRITE_KEY or "").strip()
    if not configured_key:
        # Contacts write key not configured - denying write access
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if contacts_write_key != configured_key:
        # Contacts write key mismatch - denying request
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


async def resolve_contact_filters(request: Request) -> ContactFilterParams:
    """Build contact filter parameters from query string, preserving multi-value inputs."""
    query_params = request.query_params
    data = dict(query_params)
    multi_value_keys = (
        "exclude_company_ids",
        "exclude_titles",
        "exclude_company_locations",
        "exclude_contact_locations",
        "exclude_seniorities",
        "exclude_departments",
        "exclude_technologies",
        "exclude_keywords",
        "exclude_industries",
    )
    for key in multi_value_keys:
        values = query_params.getlist(key)
        if values:
            data[key] = values
    try:
        return ContactFilterParams.model_validate(data)
    except ValidationError as exc:
        first_error = exc.errors()[0] if exc.errors() else {}
        message = first_error.get("msg", "Invalid query parameters")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc


async def resolve_attribute_params(
    request: Request, force_distinct: bool = False
) -> AttributeListParams:
    """
    Parse attribute list query parameters without triggering raw bool coercion errors.
    
    Args:
        request: FastAPI request object
        force_distinct: If True, always set distinct=True regardless of user input
        
    Returns:
        AttributeListParams instance
    """
    query_params = dict(request.query_params)
    
    # If force_distinct is True, override the distinct parameter
    if force_distinct:
        query_params.pop("distinct", None)
        query_params["distinct"] = "true"
    
    try:
        params = AttributeListParams.model_validate(query_params)
        # Force distinct to True if requested, regardless of user input
        if force_distinct:
            params.distinct = True
        return params
    except ValidationError as exc:
        first_error = exc.errors()[0] if exc.errors() else {}
        message = first_error.get("msg", "Invalid query parameters")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc


# Convenience functions for endpoints that require distinct=True
async def resolve_industry_attribute_params(request: Request) -> AttributeListParams:
    """Parse attribute list query parameters for industry endpoint with distinct=True always enforced."""
    return await resolve_attribute_params(request, force_distinct=True)


async def resolve_keywords_attribute_params(request: Request) -> AttributeListParams:
    """Parse attribute list query parameters for keywords endpoint with distinct=True always enforced."""
    return await resolve_attribute_params(request, force_distinct=True)


async def resolve_technologies_attribute_params(request: Request) -> AttributeListParams:
    """Parse attribute list query parameters for technologies endpoint with distinct=True always enforced."""
    return await resolve_attribute_params(request, force_distinct=True)


def _resolve_pagination(
    filters: ContactFilterParams,
    limit: Optional[int],
) -> Optional[int]:
    """Choose the most appropriate page size within configured bounds."""
    return resolve_pagination_params(filters, limit, cap_explicit_limit=True)


@router.get("/", response_model=CursorPage[Union[ContactListItem, ContactSimpleItem]])
async def list_contacts(
    request: Request,
    filters: ContactFilterParams = Depends(resolve_contact_filters),
    limit: Optional[int] = Query(None, ge=1),
    offset: Optional[int] = Query(0, ge=0),
    cursor: Optional[str] = Query(None),
    view: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ) -> CursorPage[Union[ContactListItem, ContactSimpleItem]]:
    """Return a paginated list of contacts."""
    # Record request start time for performance monitoring
    request_start_time = time.time()
    
    raw_path = request.scope.get("raw_path")
    if isinstance(raw_path, (bytes, bytearray)):
        raw_path_text = raw_path.decode("latin-1", errors="ignore")
    else:
        raw_path_text = str(raw_path) if raw_path is not None else request.url.path
    if "/contacts//" in raw_path_text:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    page_limit = _resolve_pagination(filters, limit)
    use_cursor = False
    resolved_offset = offset or 0
    cursor_token = cursor or filters.cursor
    if cursor_token:
        try:
            resolved_offset = decode_offset_cursor(cursor_token)
        except ValueError as exc:
            # Invalid cursor token - raising error
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid cursor value",
            ) from exc
        use_cursor = True
    elif offset == 0 and filters.page is not None and page_limit is not None:
        # Only use filters.page if no explicit offset was provided (offset defaults to 0)
        resolved_offset = (filters.page - 1) * page_limit

    active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())

    if (view or "").strip().lower() == "simple":
        page = await service.list_contacts_simple(
            session,
            filters,
            limit=page_limit,
            offset=resolved_offset,
            request_url=str(request.url),
            use_cursor=use_cursor,
        )
    else:
        page = await service.list_contacts(
            session,
            filters,
            limit=page_limit,
            offset=resolved_offset,
            request_url=str(request.url),
            use_cursor=use_cursor,
        )

    # Calculate total request duration for performance monitoring
    request_end_time = time.time()
    request_duration = request_end_time - request_start_time
    
    return page


@router.get("/stream/")
async def stream_contacts(
    request: Request,
    filters: ContactFilterParams = Depends(resolve_contact_filters),
    format: str = Query("jsonl", regex="^(jsonl|csv)$"),
    max_results: Optional[int] = Query(None, ge=1, description="Maximum results to stream"),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """
    Stream contacts as JSONL or CSV for large datasets.
    
    This endpoint is optimized for large result sets and streams data in chunks
    without loading everything into memory. Use this for exports or bulk operations.
    
    Formats:
    - jsonl: Newline-delimited JSON (one JSON object per line)
    - csv: Comma-separated values with header row
    
    Example:
        GET /api/v1/contacts/stream/?format=jsonl&email=example.com
    """
    if not settings.ENABLE_STREAMING_QUERIES:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Streaming queries are disabled",
        )
    
    # Apply max_results limit from settings if not specified
    if max_results is None and settings.MAX_STREAMING_RESULTS:
        max_results = settings.MAX_STREAMING_RESULTS
    
    # Build query using repository - use a simplified approach for streaming
    # For full filtering, we'd need to replicate the repository's query building logic
    # For now, use a basic query with common filters
    contact_repo = ContactRepository()
    
    # Start with base query
    query = select(Contact)
    
    # Apply basic filters that don't require complex joins
    if filters.email:
        query = query.where(Contact.email.ilike(f"%{filters.email}%"))
    if filters.first_name:
        query = query.where(Contact.first_name.ilike(f"%{filters.first_name}%"))
    if filters.last_name:
        query = query.where(Contact.last_name.ilike(f"%{filters.last_name}%"))
    if filters.title:
        query = query.where(Contact.title.ilike(f"%{filters.title}%"))
    
    # Note: For full filter support, we'd need to use the repository's full query building
    # This is a simplified version for streaming large datasets
    
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
            for contact in batch:
                # Convert contact to dict (simplified for streaming)
                contact_dict = {
                    "uuid": contact.uuid,
                    "first_name": contact.first_name,
                    "last_name": contact.last_name,
                    "email": contact.email,
                    "title": contact.title,
                    "mobile_phone": contact.mobile_phone,
                    "company_id": contact.company_id,
                }
                # Use TypeAdapter for faster serialization
                json_line = adapter.dump_json(contact_dict).decode("utf-8") + "\n"
                yield json_line
                count += 1
                if max_results and count >= max_results:
                    break
    
    async def generate_csv():
        """Generate CSV stream."""
        import csv
        from io import StringIO
        
        # Write header
        header = ["uuid", "first_name", "last_name", "email", "title", "mobile_phone", "company_id"]
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
            for contact in batch:
                writer.writerow([
                    contact.uuid,
                    contact.first_name or "",
                    contact.last_name or "",
                    contact.email or "",
                    contact.title or "",
                    contact.mobile_phone or "",
                    contact.company_id or "",
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
                "Content-Disposition": "attachment; filename=contacts.jsonl",
            },
        )
    else:  # csv
        return StreamingResponse(
            generate_csv(),
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=contacts.csv",
            },
        )


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

        # JSON encoded arrays (SQLite fallback or upstream serialization)
        if stripped.startswith("[") and stripped.endswith("]"):
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item or "").strip()]
            except json.JSONDecodeError:
                pass

        # PostgreSQL array string representation {"a","b"}
        if stripped.startswith("{") and stripped.endswith("}"):
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


def _has_alphanumeric(value: Any) -> bool:
    """Return True when the value contains at least one alphanumeric character."""
    if value is None:
        return False
    text = str(value).strip()
    if not text:
        return False
    return any(char.isalnum() for char in text)


@router.get("/count/", response_model=CountResponse)
async def count_contacts(
    filters: ContactFilterParams = Depends(resolve_contact_filters),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CountResponse:
    """Return the total number of contacts that match the provided filters."""
    active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
    count = await service.count_contacts(session, filters)
    return count


@router.get("/count/uuids/", response_model=UuidListResponse)
async def get_contact_uuids(
    filters: ContactFilterParams = Depends(resolve_contact_filters),
    limit: Optional[int] = Query(None, ge=1, description="Limit the number of UUIDs returned. If not provided, returns all matching UUIDs."),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UuidListResponse:
    """Return contact UUIDs that match the provided filters."""
    active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
    uuids = await service.get_uuids_by_filters(session, filters, limit)
    return UuidListResponse(count=len(uuids), uuids=uuids)


@router.post("/", response_model=ContactDetail, status_code=status.HTTP_201_CREATED)
async def create_contact(
    payload: ContactCreate,
    current_user: User = Depends(get_current_free_or_pro_user),  # Free and Pro users can create
    _: None = Depends(require_contacts_write_key),
    session: AsyncSession = Depends(get_db),
) -> ContactDetail:
    """Create a new contact with optional fields.
    
    Free users and Pro users can create contacts.
    """
    contact = await service.create_contact(session, payload)
    return contact


async def _attribute_endpoint(
    session: AsyncSession,
    filters: ContactFilterParams,
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
        # Forcing distinct for array attributes

    if params.limit is not None and params.limit <= 0:
        # Invalid limit - rejecting request
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="limit must be a positive integer",
        )
    if params.offset is not None and params.offset < 0:
        # Invalid offset - rejecting request
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="offset must be zero or greater",
        )

    values = await service.list_attribute_values(
        session,
        filters,
        effective_params,
        column_factory=column_factory,
        array_mode=array_mode,
    )
    if attribute_label == "title":
        values = [value for value in values if _has_alphanumeric(value)]
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
        # Deduplicated attribute values
        return unique_values
    return values


@router.get("/title/", response_model=CursorPage[str])
async def list_titles(
    request: Request,
    filters: ContactFilterParams = Depends(resolve_contact_filters),
    params: AttributeListParams = Depends(resolve_attribute_params),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CursorPage[str]:
    """Return contact titles filtered by the supplied parameters.
    
    Response includes next and previous pagination URLs.
    """
    request_url = str(request.url)
    result = await service.list_titles_paginated(
        session,
        filters,
        params,
        request_url,
        lambda Contact, Company, ContactMetadata, CompanyMetadata: Contact.title,
    )
    return result


@router.get("/seniority/", response_model=CursorPage[str])
async def list_seniority(
    request: Request,
    filters: ContactFilterParams = Depends(resolve_contact_filters),
    params: AttributeListParams = Depends(resolve_attribute_params),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CursorPage[str]:
    """Return contact seniority values filtered by the supplied parameters.
    
    Filters out placeholder value "_" (default value in database).
    Response includes next and previous pagination URLs.
    """
    request_url = str(request.url)
    result = await service.list_titles_paginated(
        session,
        filters,
        params,
        request_url,
        lambda Contact, Company, ContactMetadata, CompanyMetadata: Contact.seniority,
    )
    return result


@router.get("/department/", response_model=CursorPage[str])
async def list_departments(
    request: Request,
    filters: ContactFilterParams = Depends(resolve_contact_filters),
    params: AttributeListParams = Depends(resolve_attribute_params),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CursorPage[str]:
    """Return department values from Contact.departments array field.
    
    This endpoint queries Contact.departments and supports all contact filters.
    Always uses: separated=true, distinct=true (hardcoded for optimal performance)
    
    Equivalent to: SELECT DISTINCT unnest(departments) FROM contacts WHERE departments IS NOT NULL
    
    Response includes next and previous pagination URLs.
    """
    request_url = str(request.url)
    # Always use separated=True and distinct=True for optimal performance
    result = await service.list_departments_simple(session, filters, params, separated=True, request_url=request_url)
    return result


@router.get("/company/", response_model=CursorPage[str])
async def list_companies(
    request: Request,
    params: AttributeListParams = Depends(resolve_attribute_params),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CursorPage[str]:
    """Return company names directly from Company table.
    
    This endpoint queries ONLY the Company table and ignores all contact filters.
    Only uses: distinct, limit, offset, ordering, search parameters.
    
    Equivalent to: SELECT DISTINCT name FROM companies WHERE name IS NOT NULL
    
    Response includes next and previous pagination URLs.
    """
    request_url = str(request.url)
    result = await service.list_company_names_simple(session, params, request_url)
    return result


@router.get("/company/domain/", response_model=CursorPage[str])
async def list_company_domains(
    request: Request,
    params: AttributeListParams = Depends(resolve_attribute_params),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CursorPage[str]:
    """Return company domains extracted from CompanyMetadata.website.
    
    This endpoint queries ONLY the CompanyMetadata table and ignores all contact filters.
    Only uses: distinct, limit, offset, ordering, search parameters.
    
    Extracts domain from website URLs:
    - Removes protocol (http://, https://)
    - Removes www. prefix
    - Removes port numbers
    - Converts to lowercase
    
    Equivalent to: SELECT DISTINCT extract_domain(website) FROM companies_metadata WHERE website IS NOT NULL
    
    Response includes next and previous pagination URLs.
    """
    request_url = str(request.url)
    result = await service.list_company_domains_simple(session, params, request_url)
    return result


@router.get("/industry/", response_model=CursorPage[str])
async def list_industries(
    request: Request,
    params: AttributeListParams = Depends(resolve_industry_attribute_params),
    company: Optional[list[str]] = Query(None, description="Filter by exact company name(s). Supports multiple values: ?company=Acme&company=Corp or ?company=Acme,Corp"),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CursorPage[str]:
    """Return industry values directly from Company table.
    
    This endpoint queries ONLY the Company table and ignores all contact filters.
    Only uses: limit, offset, ordering, search, company parameters.
    
    Always uses: separated=true, distinct=true (hardcoded for optimal performance)
    
    Equivalent to: SELECT DISTINCT unnest(industries) FROM companies WHERE industries IS NOT NULL
    
    Response includes next and previous pagination URLs.
    
    Company parameter supports multiple values:
    - Multiple query params: ?company=Acme&company=Corp
    - Comma-separated: ?company=Acme,Corp
    - Mixed: ?company=Acme,Corp&company=Tech
    """
    # Normalize company list to handle comma-separated values
    normalized_companies = normalize_list_param(company)
    
    request_url = str(request.url)
    # Always use separated=True and distinct=True for optimal performance
    result = await service.list_industries_simple(session, params, normalized_companies, separated=True, request_url=request_url)
    return result


@router.get("/keywords/", response_model=CursorPage[str])
async def list_keywords(
    request: Request,
    params: AttributeListParams = Depends(resolve_keywords_attribute_params),
    company: Optional[list[str]] = Query(None, description="Filter by exact company name(s). Supports multiple values: ?company=Acme&company=Corp or ?company=Acme,Corp"),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CursorPage[str]:
    """Return keyword values directly from Company table.
    
    This endpoint queries ONLY the Company table and ignores all contact filters.
    Only uses: limit, offset, ordering, search, company parameters.
    
    Always uses: separated=true, distinct=true (hardcoded for optimal performance)
    
    Equivalent to: SELECT DISTINCT unnest(keywords) FROM companies WHERE keywords IS NOT NULL
    
    Response includes next and previous pagination URLs.
    
    Company parameter supports multiple values:
    - Multiple query params: ?company=Acme&company=Corp
    - Comma-separated: ?company=Acme,Corp
    - Mixed: ?company=Acme,Corp&company=Tech
    """
    # Normalize company list to handle comma-separated values
    normalized_companies = normalize_list_param(company)
    
    request_url = str(request.url)
    # Always use separated=True and distinct=True for optimal performance
    result = await service.list_keywords_simple(session, params, normalized_companies, request_url)
    return result


@router.get("/technologies/", response_model=CursorPage[str])
async def list_technologies(
    request: Request,
    params: AttributeListParams = Depends(resolve_technologies_attribute_params),
    company: Optional[list[str]] = Query(None, description="Filter by exact company name(s). Supports multiple values: ?company=Acme&company=Corp or ?company=Acme,Corp"),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CursorPage[str]:
    """Return technology values directly from Company table.
    
    This endpoint queries ONLY the Company table and ignores all contact filters.
    Only uses: limit, offset, ordering, search, company parameters.
    
    Always uses: separated=true, distinct=true (hardcoded for optimal performance)
    
    Equivalent to: SELECT DISTINCT unnest(technologies) FROM companies WHERE technologies IS NOT NULL
    
    Response includes next and previous pagination URLs.
    
    Company parameter supports multiple values:
    - Multiple query params: ?company=Acme&company=Corp
    - Comma-separated: ?company=Acme,Corp
    - Mixed: ?company=Acme,Corp&company=Tech
    """
    # Normalize company list to handle comma-separated values
    normalized_companies = normalize_list_param(company)
    
    request_url = str(request.url)
    # Always use separated=True and distinct=True for optimal performance
    result = await service.list_technologies_simple(session, params, normalized_companies, request_url)
    return result


@router.get("/company_address/", response_model=CursorPage[str])
async def list_company_addresses(
    request: Request,
    filters: ContactFilterParams = Depends(resolve_contact_filters),
    params: AttributeListParams = Depends(resolve_attribute_params),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CursorPage[str]:
    """Return company address text sourced from the text search column.
    
    Response includes next and previous pagination URLs.
    """
    import time
    start_time = time.time()
    
    request_url = str(request.url)
    active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
    
    try:
        service_start_time = time.time()
        result = await service.list_company_addresses_paginated(
            session,
            filters,
            params,
            request_url,
        )
        service_time = time.time() - service_start_time
        
        return result
        
    except Exception as e:
        # Error in list_company_addresses endpoint
        total_time = time.time() - start_time
        raise


@router.get("/contact_address/", response_model=CursorPage[str])
async def list_contact_addresses(
    request: Request,
    filters: ContactFilterParams = Depends(resolve_contact_filters),
    params: AttributeListParams = Depends(resolve_attribute_params),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CursorPage[str]:
    """Return contact address text sourced from the text search column.
    
    Response includes next and previous pagination URLs.
    """
    request_url = str(request.url)
    active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
    
    result = await service.list_contact_addresses_paginated(
        session,
        filters,
        params,
        request_url,
    )
    
    return result


@router.get("/{contact_uuid}/", response_model=ContactDetail)
async def retrieve_contact(
    contact_uuid: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContactDetail:
    """Retrieve a single contact by UUID."""
    contact = await service.get_contact(session, contact_uuid)
    return contact

