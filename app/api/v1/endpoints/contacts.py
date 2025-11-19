"""Contacts API endpoints providing list and attribute lookups."""

from __future__ import annotations

import json
import time
from typing import Any, Callable, Iterable, List, Optional, Union

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_current_user
from app.core.config import get_settings
from app.core.logging import get_logger, log_function_call
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import CountResponse, CursorPage, UuidListResponse
from app.schemas.contacts import ContactCreate, ContactDetail, ContactListItem, ContactSimpleItem
from app.schemas.filters import AttributeListParams, ContactFilterParams
from app.services.contacts_service import ContactsService
from app.utils.cursor import decode_offset_cursor


settings = get_settings()
router = APIRouter(prefix="/contacts", tags=["Contacts"])
service = ContactsService()
logger = get_logger(__name__)


async def require_contacts_write_key(
    contacts_write_key: Optional[str] = Header(None, alias="X-Contacts-Write-Key"),
) -> None:
    """Ensure write requests include the configured authorization key."""
    configured_key = (settings.CONTACTS_WRITE_KEY or "").strip()
    if not configured_key:
        logger.warning("Contacts write key is not configured; denying write access.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if contacts_write_key != configured_key:
        logger.info("Contacts write key mismatch; denying request.")
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


async def resolve_attribute_params(request: Request) -> AttributeListParams:
    """Parse attribute list query parameters without triggering raw bool coercion errors."""
    try:
        return AttributeListParams.model_validate(dict(request.query_params))
    except ValidationError as exc:
        first_error = exc.errors()[0] if exc.errors() else {}
        message = first_error.get("msg", "Invalid query parameters")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc


async def resolve_industry_attribute_params(request: Request) -> AttributeListParams:
    """Parse attribute list query parameters for industry endpoint with distinct=True always enforced."""
    query_params = dict(request.query_params)
    # Always set distinct=True - remove it from query params so users can't override
    query_params.pop("distinct", None)
    query_params["distinct"] = "true"
    try:
        params = AttributeListParams.model_validate(query_params)
        # Force distinct to True regardless of user input
        params.distinct = True
        return params
    except ValidationError as exc:
        first_error = exc.errors()[0] if exc.errors() else {}
        message = first_error.get("msg", "Invalid query parameters")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc


async def resolve_keywords_attribute_params(request: Request) -> AttributeListParams:
    """Parse attribute list query parameters for keywords endpoint with distinct=True always enforced."""
    query_params = dict(request.query_params)
    # Always set distinct=True - remove it from query params so users can't override
    query_params.pop("distinct", None)
    query_params["distinct"] = "true"
    try:
        params = AttributeListParams.model_validate(query_params)
        # Force distinct to True regardless of user input
        params.distinct = True
        return params
    except ValidationError as exc:
        first_error = exc.errors()[0] if exc.errors() else {}
        message = first_error.get("msg", "Invalid query parameters")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc


@log_function_call(logger=logger, log_arguments=True, log_result=True)
def _resolve_pagination(
    filters: ContactFilterParams,
    limit: Optional[int],
) -> Optional[int]:
    """Choose the most appropriate page size within configured bounds."""
    # If explicit limit is provided, use it (no cap when explicitly requested)
    if limit is not None:
        logger.debug(
            "Resolved pagination: explicit limit=%d (no cap applied)",
            limit,
        )
        return limit
    
    # If page_size is specified in filters, use it (with cap if MAX_PAGE_SIZE is set)
    if filters.page_size is not None:
        if settings.MAX_PAGE_SIZE is not None:
            resolved = min(filters.page_size, settings.MAX_PAGE_SIZE)
            logger.debug(
                "Resolved pagination: page_size=%d capped to %d",
                filters.page_size,
                resolved,
            )
            return resolved
        logger.debug(
            "Resolved pagination: page_size=%d (no cap)",
            filters.page_size,
        )
        return filters.page_size
    
    # Default: unlimited (None)
    logger.debug(
        "Resolved pagination: default=unlimited (None)",
    )
    return None


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
            logger.warning("Invalid cursor token supplied: token=%s error=%s", cursor_token, exc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid cursor value",
            ) from exc
        use_cursor = True
    elif offset == 0 and filters.page is not None and page_limit is not None:
        # Only use filters.page if no explicit offset was provided (offset defaults to 0)
        resolved_offset = (filters.page - 1) * page_limit

    active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
    logger.info(
        "Listing contacts: limit=%s offset=%d use_cursor=%s filters=%s",
        page_limit,
        resolved_offset,
        use_cursor,
        active_filter_keys,
    )

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
    
    logger.info(
        "Listed contacts: returned=%d has_next=%s has_previous=%s duration=%.3fs",
        len(page.results),
        bool(page.next),
        bool(page.previous),
        request_duration,
    )
    return page


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
    logger.info("Counting contacts with filters=%s", active_filter_keys)
    count = await service.count_contacts(session, filters)
    logger.info("Counted contacts: filters=%s total=%d", active_filter_keys, count.count)
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
    logger.info("Getting contact UUIDs with filters=%s limit=%s", active_filter_keys, limit)
    uuids = await service.get_uuids_by_filters(session, filters, limit)
    logger.info("Retrieved contact UUIDs: filters=%s count=%d", active_filter_keys, len(uuids))
    return UuidListResponse(count=len(uuids), uuids=uuids)


@router.post("/", response_model=ContactDetail, status_code=status.HTTP_201_CREATED)
async def create_contact(
    payload: ContactCreate,
    current_user: User = Depends(get_current_admin),
    _: None = Depends(require_contacts_write_key),
    session: AsyncSession = Depends(get_db),
) -> ContactDetail:
    """Create a new contact with optional fields."""
    logger.info("Creating contact via API")
    contact = await service.create_contact(session, payload)
    logger.info("Created contact via API: uuid=%s", contact.uuid)
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
        logger.debug(
            "Forcing distinct parameters for array attribute: attribute=%s limit=%d offset=%d",
            attribute_label,
            params.limit,
            params.offset,
        )

    if params.limit is not None and params.limit <= 0:
        logger.warning(
            "Attribute list rejected due to non-positive limit: attribute=%s limit=%d",
            attribute_label,
            params.limit,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="limit must be a positive integer",
        )
    if params.limit is None:
        logger.warning(
            "Unlimited attribute query requested - this may return a large dataset. attribute=%s",
            attribute_label,
        )
    if params.offset is not None and params.offset < 0:
        logger.warning(
            "Attribute list rejected due to negative offset: attribute=%s offset=%d",
            attribute_label,
            params.offset,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="offset must be zero or greater",
        )

    logger.info(
        "Listing contact attribute values: attribute=%s distinct=%s limit=%d offset=%d",
        attribute_label,
        effective_params.distinct,
        effective_params.limit,
        effective_params.offset,
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
        logger.debug(
            "Deduplicated attribute values: attribute=%s before=%d after=%d",
            attribute_label,
            len(values),
            len(unique_values),
        )
        return unique_values
    logger.info("Listed contact attribute values: attribute=%s count=%d", attribute_label, len(values))
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
    logger.info(
        "Listing titles: distinct=%s limit=%d offset=%d ordering=%s search=%s",
        params.distinct,
        params.limit or 0,
        params.offset,
        params.ordering,
        bool(params.search),
    )
    request_url = str(request.url)
    result = await service.list_titles_paginated(
        session,
        filters,
        params,
        request_url,
        lambda Contact, Company, ContactMetadata, CompanyMetadata: Contact.title,
    )
    logger.info(
        "Listed titles: count=%d next=%s previous=%s",
        len(result.results),
        bool(result.next),
        bool(result.previous),
    )
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
    logger.info(
        "Listing company names (simple): distinct=%s limit=%d offset=%d ordering=%s search=%s",
        params.distinct,
        params.limit or 0,
        params.offset,
        params.ordering,
        bool(params.search),
    )
    request_url = str(request.url)
    result = await service.list_company_names_simple(session, params, request_url)
    logger.info(
        "Listed company names (simple): count=%d next=%s previous=%s",
        len(result.results),
        bool(result.next),
        bool(result.previous),
    )
    return result


def _normalize_company_list(company_value: Optional[list[str]]) -> Optional[list[str]]:
    """
    Normalize company list query parameter by splitting comma-separated values.
    
    FastAPI parses comma-separated query parameters like `?company=Acme,Corp` as
    a single string in a list: `["Acme,Corp"]`. This function splits such values
    and handles both formats:
    - Comma-separated: `?company=Acme,Corp` -> `["Acme", "Corp"]`
    - Multiple params: `?company=Acme&company=Corp` -> `["Acme", "Corp"]`
    - Mixed: `?company=Acme,Corp&company=Tech` -> `["Acme", "Corp", "Tech"]`
    
    Args:
        company_value: Optional list of strings from FastAPI Query parameter
        
    Returns:
        Normalized list with comma-separated values split, or None if input is None/empty
    """
    if not company_value:
        return None
    
    # Split each string by comma and flatten into a single list
    normalized = []
    for item in company_value:
        if item:
            # Split by comma and add each part
            parts = item.split(",")
            for part in parts:
                # Trim whitespace and add if not empty
                trimmed = part.strip()
                if trimmed:
                    normalized.append(trimmed)
    
    return normalized if normalized else None


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
    normalized_companies = _normalize_company_list(company)
    
    logger.info(
        "Listing industries (simple): distinct=%s limit=%d offset=%d ordering=%s search=%s company=%s separated=true",
        params.distinct,
        params.limit or 0,
        params.offset,
        params.ordering,
        bool(params.search),
        len(normalized_companies) if normalized_companies else 0,
    )
    request_url = str(request.url)
    # Always use separated=True and distinct=True for optimal performance
    result = await service.list_industries_simple(session, params, normalized_companies, separated=True, request_url=request_url)
    logger.info(
        "Listed industries (simple): count=%d next=%s previous=%s",
        len(result.results),
        bool(result.next),
        bool(result.previous),
    )
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
    normalized_companies = _normalize_company_list(company)
    
    logger.info(
        "Listing keywords (simple): distinct=%s limit=%d offset=%d ordering=%s search=%s company=%s separated=true",
        params.distinct,
        params.limit or 0,
        params.offset,
        params.ordering,
        bool(params.search),
        len(normalized_companies) if normalized_companies else 0,
    )
    request_url = str(request.url)
    # Always use separated=True and distinct=True for optimal performance
    result = await service.list_keywords_simple(session, params, normalized_companies, request_url)
    logger.info(
        "Listed keywords (simple): count=%d next=%s previous=%s",
        len(result.results),
        bool(result.next),
        bool(result.previous),
    )
    return result


@router.get("/technologies/", response_model=List[str])
async def list_technologies(
    filters: ContactFilterParams = Depends(resolve_contact_filters),
    params: AttributeListParams = Depends(resolve_attribute_params),
    separated: bool = Query(False),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[str]:
    """Return technology values for associated companies."""
    column_factory = (
        (
            lambda Contact, Company, ContactMetadata, CompanyMetadata: Company.technologies
        )
        if separated
        else (
            lambda Contact, Company, ContactMetadata, CompanyMetadata: func.array_to_string(
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
        logger.debug("Separated technology values count=%d", len(deduped))
        return deduped
    filtered = [value for value in values if value]
    logger.debug("Collapsed technology values count=%d", len(filtered))
    return filtered


@router.get("/company_address/", response_model=List[str])
async def list_company_addresses(
    filters: ContactFilterParams = Depends(resolve_contact_filters),
    params: AttributeListParams = Depends(resolve_attribute_params),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[str]:
    """Return company address text sourced from the text search column."""
    return await _attribute_endpoint(
        session,
        filters,
        params,
        lambda Contact, Company, ContactMetadata, CompanyMetadata: Company.text_search,
        "company_address",
    )


@router.get("/contact_address/", response_model=List[str])
async def list_contact_addresses(
    filters: ContactFilterParams = Depends(resolve_contact_filters),
    params: AttributeListParams = Depends(resolve_attribute_params),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[str]:
    """Return contact address text sourced from the text search column."""
    return await _attribute_endpoint(
        session,
        filters,
        params,
        lambda Contact, Company, ContactMetadata, CompanyMetadata: Contact.text_search,
        "contact_address",
    )


@router.get("/city/", response_model=List[str])
async def list_contact_cities(
    filters: ContactFilterParams = Depends(resolve_contact_filters),
    params: AttributeListParams = Depends(resolve_attribute_params),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[str]:
    """Return distinct contact city values."""
    return await _attribute_endpoint(
        session,
        filters,
        params,
        lambda Contact, Company, ContactMetadata, CompanyMetadata: ContactMetadata.city,
        "city",
    )


@router.get("/state/", response_model=List[str])
async def list_contact_states(
    filters: ContactFilterParams = Depends(resolve_contact_filters),
    params: AttributeListParams = Depends(resolve_attribute_params),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[str]:
    """Return distinct contact state values."""
    return await _attribute_endpoint(
        session,
        filters,
        params,
        lambda Contact, Company, ContactMetadata, CompanyMetadata: ContactMetadata.state,
        "state",
    )


@router.get("/country/", response_model=List[str])
async def list_contact_countries(
    filters: ContactFilterParams = Depends(resolve_contact_filters),
    params: AttributeListParams = Depends(resolve_attribute_params),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[str]:
    """Return distinct contact country values."""
    return await _attribute_endpoint(
        session,
        filters,
        params,
        lambda Contact, Company, ContactMetadata, CompanyMetadata: ContactMetadata.country,
        "country",
    )


@router.get("/company_city/", response_model=List[str])
async def list_company_cities(
    filters: ContactFilterParams = Depends(resolve_contact_filters),
    params: AttributeListParams = Depends(resolve_attribute_params),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[str]:
    """Return distinct company city values."""
    return await _attribute_endpoint(
        session,
        filters,
        params,
        lambda Contact, Company, ContactMetadata, CompanyMetadata: CompanyMetadata.city,
        "company_city",
    )


@router.get("/company_state/", response_model=List[str])
async def list_company_states(
    filters: ContactFilterParams = Depends(resolve_contact_filters),
    params: AttributeListParams = Depends(resolve_attribute_params),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[str]:
    """Return distinct company state values."""
    return await _attribute_endpoint(
        session,
        filters,
        params,
        lambda Contact, Company, ContactMetadata, CompanyMetadata: CompanyMetadata.state,
        "company_state",
    )


@router.get("/company_country/", response_model=List[str])
async def list_company_countries(
    filters: ContactFilterParams = Depends(resolve_contact_filters),
    params: AttributeListParams = Depends(resolve_attribute_params),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[str]:
    """Return distinct company country values."""
    return await _attribute_endpoint(
        session,
        filters,
        params,
        lambda Contact, Company, ContactMetadata, CompanyMetadata: CompanyMetadata.country,
        "company_country",
    )


@router.get("/{contact_uuid}/", response_model=ContactDetail)
async def retrieve_contact(
    contact_uuid: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContactDetail:
    """Retrieve a single contact by UUID."""
    logger.info("Retrieving contact detail: contact_uuid=%s", contact_uuid)
    contact = await service.get_contact(session, contact_uuid)
    logger.info("Retrieved contact detail: contact_uuid=%s", contact_uuid)
    return contact

