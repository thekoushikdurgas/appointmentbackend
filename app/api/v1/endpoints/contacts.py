"""Contacts API endpoints providing list and attribute lookups."""

from __future__ import annotations

import json
from typing import Any, Callable, Iterable, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger, log_function_call
from app.db.session import get_db
from app.schemas.common import CountResponse, CursorPage
from app.schemas.contacts import ContactCreate, ContactDetail, ContactListItem
from app.schemas.filters import AttributeListParams, ContactFilterParams
from app.services.contacts_service import ContactsService
from app.utils.cursor import decode_offset_cursor


settings = get_settings()
router = APIRouter(prefix="/contacts", tags=["Contacts"])
service = ContactsService()
logger = get_logger(__name__)


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


@log_function_call(logger=logger, log_arguments=True, log_result=True)
def _resolve_pagination(
    filters: ContactFilterParams,
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


@router.get("/", response_model=CursorPage[ContactListItem])
async def list_contacts(
    request: Request,
    filters: ContactFilterParams = Depends(resolve_contact_filters),
    limit: Optional[int] = Query(None, ge=1),
    offset: Optional[int] = Query(0, ge=0),
    cursor: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db),
) -> CursorPage[ContactListItem]:
    """Return a paginated list of contacts."""
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

    active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
    logger.info(
        "Listing contacts: limit=%d offset=%d use_cursor=%s filters=%s",
        page_limit,
        resolved_offset,
        use_cursor,
        active_filter_keys,
    )

    page = await service.list_contacts(
        session,
        filters,
        limit=page_limit,
        offset=resolved_offset,
        request_url=str(request.url),
        use_cursor=use_cursor,
    )

    logger.info(
        "Listed contacts: returned=%d has_next=%s has_previous=%s",
        len(page.results),
        bool(page.next),
        bool(page.previous),
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
) -> CountResponse:
    """Return the total number of contacts that match the provided filters."""
    active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
    logger.info("Counting contacts with filters=%s", active_filter_keys)
    count = await service.count_contacts(session, filters)
    logger.info("Counted contacts: filters=%s total=%d", active_filter_keys, count.count)
    return count


@router.post("/", response_model=ContactDetail, status_code=status.HTTP_201_CREATED)
async def create_contact(
    payload: ContactCreate,
    session: AsyncSession = Depends(get_db),
) -> ContactDetail:
    """Create a new contact with optional fields."""
    logger.info("Creating contact via API")
    contact = await service.create_contact(session, payload)
    logger.info("Created contact via API: contact_id=%d", contact.id)
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


@router.get("/title/", response_model=List[str])
async def list_titles(
    filters: ContactFilterParams = Depends(resolve_contact_filters),
    params: AttributeListParams = Depends(resolve_attribute_params),
    session: AsyncSession = Depends(get_db),
) -> List[str]:
    """Return contact titles filtered by the supplied parameters."""
    return await _attribute_endpoint(
        session,
        filters,
        params,
        lambda Contact, Company, ContactMetadata, CompanyMetadata: Contact.title,
        "title",
    )


@router.get("/company/", response_model=List[str])
async def list_companies(
    filters: ContactFilterParams = Depends(resolve_contact_filters),
    params: AttributeListParams = Depends(resolve_attribute_params),
    session: AsyncSession = Depends(get_db),
) -> List[str]:
    """Return company names for contacts matching the filters."""
    return await _attribute_endpoint(
        session,
        filters,
        params,
        lambda Contact, Company, ContactMetadata, CompanyMetadata: Company.name,
        "company",
    )


@router.get("/industry/", response_model=List[str])
async def list_industries(
    filters: ContactFilterParams = Depends(resolve_contact_filters),
    params: AttributeListParams = Depends(resolve_attribute_params),
    separated: bool = Query(False),
    session: AsyncSession = Depends(get_db),
) -> List[str]:
    """Return industry values sourced from related companies."""
    column_factory = (
        (
            lambda Contact, Company, ContactMetadata, CompanyMetadata: Company.industries
        )
        if separated
        else (
            lambda Contact, Company, ContactMetadata, CompanyMetadata: func.array_to_string(
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
    filters: ContactFilterParams = Depends(resolve_contact_filters),
    params: AttributeListParams = Depends(resolve_attribute_params),
    separated: bool = Query(False),
    session: AsyncSession = Depends(get_db),
) -> List[str]:
    """Return keyword values for companies, optionally split into unique tokens."""
    column_factory = (
        (
            lambda Contact, Company, ContactMetadata, CompanyMetadata: Company.keywords
        )
        if separated
        else (
            lambda Contact, Company, ContactMetadata, CompanyMetadata: func.array_to_string(
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
    filters: ContactFilterParams = Depends(resolve_contact_filters),
    params: AttributeListParams = Depends(resolve_attribute_params),
    separated: bool = Query(False),
    session: AsyncSession = Depends(get_db),
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
) -> List[str]:
    """Return distinct company country values."""
    return await _attribute_endpoint(
        session,
        filters,
        params,
        lambda Contact, Company, ContactMetadata, CompanyMetadata: CompanyMetadata.country,
        "company_country",
    )


@router.get("/{contact_id:int}/", response_model=ContactDetail)
async def retrieve_contact_with_trailing_slash(
    contact_id: int,
    session: AsyncSession = Depends(get_db),
) -> ContactDetail:
    """Retrieve a single contact by primary key."""
    logger.info("Retrieving contact detail: contact_id=%d", contact_id)
    contact = await service.get_contact(session, contact_id)
    logger.info("Retrieved contact detail: contact_id=%d", contact_id)
    return contact


@router.get("/{contact_id:int}", include_in_schema=False)
async def retrieve_contact_without_trailing_slash(
    contact_id: int,
    session: AsyncSession = Depends(get_db),
) -> ContactDetail:
    """Retrieve a single contact by primary key."""
    return await retrieve_contact_with_trailing_slash(contact_id, session)

