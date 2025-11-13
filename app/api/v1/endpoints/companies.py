"""Companies API endpoints providing CRUD operations and attribute lookups."""

from __future__ import annotations

import json
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
from app.schemas.common import CountResponse, CursorPage
from app.schemas.companies import CompanyCreate, CompanyDetail, CompanyListItem, CompanyUpdate
from app.schemas.contacts import ContactListItem
from app.schemas.filters import AttributeListParams, CompanyFilterParams
from app.services.companies_service import CompaniesService
from app.utils.cursor import decode_offset_cursor


settings = get_settings()
router = APIRouter(prefix="/companies", tags=["Companies"])
service = CompaniesService()
logger = get_logger(__name__)


async def require_companies_write_key(
    companies_write_key: Optional[str] = Header(None, alias="X-Companies-Write-Key"),
) -> None:
    """Ensure write requests include the configured authorization key."""
    configured_key = (settings.COMPANIES_WRITE_KEY or "").strip()
    if not configured_key:
        logger.warning("Companies write key is not configured; denying write access.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if companies_write_key != configured_key:
        logger.info("Companies write key mismatch; denying request.")
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


@log_function_call(logger=logger, log_arguments=True, log_result=True)
def _resolve_pagination(
    filters: CompanyFilterParams,
    limit: Optional[int],
) -> int:
    """Choose the most appropriate page size within configured bounds."""
    page_size = filters.page_size if filters.page_size is not None else limit or settings.DEFAULT_PAGE_SIZE
    resolved = min(page_size, settings.MAX_PAGE_SIZE)
    logger.debug(
        "Resolved pagination: requested=%s limit_param=%s effective=%d max_allowed=%d",
        filters.page_size,
        limit,
        resolved,
        settings.MAX_PAGE_SIZE,
    )
    return resolved


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
            logger.warning("Invalid cursor token supplied: token=%s error=%s", cursor_token, exc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid cursor value",
            ) from exc
        use_cursor = True
    elif filters.page is not None:
        resolved_offset = (filters.page - 1) * page_limit

    active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
    logger.info(
        "Listing companies: limit=%d offset=%d use_cursor=%s filters=%s",
        page_limit,
        resolved_offset,
        use_cursor,
        active_filter_keys,
    )

    page = await service.list_companies(
        session,
        filters,
        limit=page_limit,
        offset=resolved_offset,
        request_url=str(request.url),
        use_cursor=use_cursor,
    )

    logger.info(
        "Listed companies: returned=%d has_next=%s has_previous=%s",
        len(page.results),
        bool(page.next),
        bool(page.previous),
    )
    return page


@router.get("/count/", response_model=CountResponse)
async def count_companies(
    filters: CompanyFilterParams = Depends(resolve_company_filters),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CountResponse:
    """Return the total number of companies that match the provided filters."""
    active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
    logger.info("Counting companies with filters=%s", active_filter_keys)
    count = await service.count_companies(session, filters)
    logger.info("Counted companies: filters=%s total=%d", active_filter_keys, count.count)
    return count


@router.post("/", response_model=CompanyDetail, status_code=status.HTTP_201_CREATED)
async def create_company(
    payload: CompanyCreate,
    current_user: User = Depends(get_current_admin),
    _: None = Depends(require_companies_write_key),
    session: AsyncSession = Depends(get_db),
) -> CompanyDetail:
    """Create a new company with optional fields."""
    logger.info("Creating company via API")
    company = await service.create_company(session, payload)
    logger.info("Created company via API: company_id=%d", company.id)
    return company


@router.put("/{company_id:int}/", response_model=CompanyDetail)
async def update_company(
    company_id: int,
    payload: CompanyUpdate,
    current_user: User = Depends(get_current_admin),
    _: None = Depends(require_companies_write_key),
    session: AsyncSession = Depends(get_db),
) -> CompanyDetail:
    """Update an existing company."""
    logger.info("Updating company via API: company_id=%d", company_id)
    company = await service.update_company(session, company_id, payload)
    logger.info("Updated company via API: company_id=%d", company_id)
    return company


@router.delete(
    "/{company_id:int}/",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_company(
    company_id: int,
    current_user: User = Depends(get_current_admin),
    _: None = Depends(require_companies_write_key),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Delete a company."""
    logger.info("Deleting company via API: company_id=%d", company_id)
    await service.delete_company(session, company_id)
    logger.info("Deleted company via API: company_id=%d", company_id)


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
        "Listing company attribute values: attribute=%s distinct=%s limit=%d offset=%d",
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
    logger.info("Listed company attribute values: attribute=%s count=%d", attribute_label, len(values))
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
        logger.debug("Separated industry values count=%d", len(deduped))
        return deduped
    filtered = [value for value in values if value]
    logger.debug("Collapsed industry values count=%d", len(filtered))
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
        logger.debug("Separated keyword values count=%d", len(deduped))
        return deduped
    filtered = [value for value in values if value]
    logger.debug("Collapsed keyword values count=%d", len(filtered))
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
        logger.debug("Separated technology values count=%d", len(deduped))
        return deduped
    filtered = [value for value in values if value]
    logger.debug("Collapsed technology values count=%d", len(filtered))
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


@router.get("/{company_id:int}/", response_model=CompanyDetail)
async def retrieve_company_with_trailing_slash(
    company_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyDetail:
    """Retrieve a single company by primary key."""
    logger.info("Retrieving company detail: company_id=%d", company_id)
    company = await service.get_company(session, company_id)
    logger.info("Retrieved company detail: company_id=%d", company_id)
    return company


@router.get("/{company_id:int}", include_in_schema=False)
async def retrieve_company_without_trailing_slash(
    company_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyDetail:
    """Retrieve a single company by primary key."""
    logger.info("Retrieving company detail: company_id=%d", company_id)
    company = await service.get_company(session, company_id)
    logger.info("Retrieved company detail: company_id=%d", company_id)
    return company


# ============================================================================
# Company Contacts Endpoints
# ============================================================================

async def resolve_company_contact_filters(request: Request) -> "CompanyContactFilterParams":
    """Build company contact filter parameters from query string."""
    from app.schemas.filters import CompanyContactFilterParams
    
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
    from app.schemas.filters import CompanyContactFilterParams
    from app.services.contacts_service import ContactsService
    from app.utils.cursor import decode_offset_cursor
    
    page_limit = min(
        filters.page_size if filters.page_size is not None else limit or settings.DEFAULT_PAGE_SIZE,
        settings.MAX_PAGE_SIZE,
    )
    
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
    elif filters.page is not None:
        resolved_offset = (filters.page - 1) * page_limit
    
    active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
    logger.info(
        "Listing contacts for company %s: limit=%d offset=%d use_cursor=%s filters=%s",
        company_uuid,
        page_limit,
        resolved_offset,
        use_cursor,
        active_filter_keys,
    )
    
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
    
    logger.info(
        "Listed %d contacts for company %s",
        len(page.results),
        company_uuid,
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
    from app.schemas.filters import CompanyContactFilterParams
    from app.services.contacts_service import ContactsService
    
    active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
    logger.info(
        "Counting contacts for company %s with filters=%s",
        company_uuid,
        active_filter_keys,
    )
    
    contacts_service = ContactsService()
    count = await contacts_service.count_contacts_by_company(
        session,
        company_uuid,
        filters,
    )
    
    logger.info(
        "Counted %d contacts for company %s",
        count.count,
        company_uuid,
    )
    return count


async def _company_contact_attribute_endpoint(
    company_uuid: str,
    session: AsyncSession,
    filters: "CompanyContactFilterParams",
    params: AttributeListParams,
    attribute: str,
) -> List[str]:
    """Helper for company contact attribute endpoints."""
    from app.schemas.filters import CompanyContactFilterParams
    from app.services.contacts_service import ContactsService
    
    logger.info(
        "Listing attribute %s for company %s contacts with filters=%s params=%s",
        attribute,
        company_uuid,
        sorted(filters.model_dump(exclude_none=True).keys()),
        params.model_dump(exclude_none=True),
    )
    
    contacts_service = ContactsService()
    values = await contacts_service.list_attribute_values_by_company(
        session,
        company_uuid,
        attribute,
        filters,
        params,
    )
    
    logger.info(
        "Listed %d distinct %s values for company %s contacts",
        len(values),
        attribute,
        company_uuid,
    )
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

