"""Contacts API endpoints providing list and attribute lookups."""

from __future__ import annotations

from typing import Callable, List, Optional

from fastapi import APIRouter, Depends, Query, Request, status
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
    filters: ContactFilterParams = Depends(),
    limit: Optional[int] = Query(None, ge=1),
    offset: Optional[int] = Query(0, ge=0),
    cursor: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db),
) -> CursorPage[ContactListItem]:
    """Return a paginated list of contacts."""
    page_limit = _resolve_pagination(filters, limit)
    use_cursor = False
    resolved_offset = offset or 0
    cursor_token = cursor or filters.cursor
    if cursor_token:
        resolved_offset = decode_offset_cursor(cursor_token)
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


@router.get("/count/", response_model=CountResponse)
async def count_contacts(
    filters: ContactFilterParams = Depends(),
    session: AsyncSession = Depends(get_db),
) -> CountResponse:
    """Return the total number of contacts that match the provided filters."""
    active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
    logger.info("Counting contacts with filters=%s", active_filter_keys)
    count = await service.count_contacts(session, filters)
    logger.info("Counted contacts: filters=%s total=%d", active_filter_keys, count.count)
    return count


@router.get("/{contact_id}", response_model=ContactDetail)
async def retrieve_contact(
    contact_id: int,
    session: AsyncSession = Depends(get_db),
) -> ContactDetail:
    """Retrieve a single contact by primary key."""
    logger.info("Retrieving contact detail: contact_id=%d", contact_id)
    contact = await service.get_contact(session, contact_id)
    logger.info("Retrieved contact detail: contact_id=%d", contact_id)
    return contact


@router.post("/", response_model=ContactDetail, status_code=status.HTTP_201_CREATED)
async def create_contact(
    payload: ContactCreate,
    session: AsyncSession = Depends(get_db),
) -> ContactDetail:
    """Create a new contact with optional fields."""
    logger.info("Creating contact: email=%s uuid=%s", payload.email, payload.uuid)
    contact = await service.create_contact(session, payload)
    logger.info("Created contact: id=%s email=%s", contact.id, contact.email)
    return contact


async def _attribute_endpoint(
    session: AsyncSession,
    filters: ContactFilterParams,
    params: AttributeListParams,
    column_factory: Callable,
    attribute_label: str,
) -> List[str]:
    """Shared handler for list-of-values endpoints."""
    logger.info(
        "Listing contact attribute values: attribute=%s distinct=%s limit=%d offset=%d",
        attribute_label,
        params.distinct,
        params.limit,
        params.offset,
    )
    values = await service.list_attribute_values(session, filters, params, column_factory=column_factory)
    if params.distinct:
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
    filters: ContactFilterParams = Depends(),
    params: AttributeListParams = Depends(),
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
    filters: ContactFilterParams = Depends(),
    params: AttributeListParams = Depends(),
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
    filters: ContactFilterParams = Depends(),
    params: AttributeListParams = Depends(),
    session: AsyncSession = Depends(get_db),
) -> List[str]:
    """Return industry values sourced from related companies."""
    return await _attribute_endpoint(
        session,
        filters,
        params,
        lambda Contact, Company, ContactMetadata, CompanyMetadata: func.unnest(Company.industries),
        "industry",
    )


@router.get("/keywords/", response_model=List[str])
async def list_keywords(
    filters: ContactFilterParams = Depends(),
    params: AttributeListParams = Depends(),
    separated: bool = Query(False),
    session: AsyncSession = Depends(get_db),
) -> List[str]:
    """Return keyword values for companies, optionally split into unique tokens."""
    column_factory = (
        (lambda Contact, Company, ContactMetadata, CompanyMetadata: func.unnest(Company.keywords))
        if separated
        else (
            lambda Contact, Company, ContactMetadata, CompanyMetadata: func.array_to_string(
                Company.keywords, ","
            )
        )
    )
    values = await _attribute_endpoint(session, filters, params, column_factory, "keywords")
    if separated:
        deduped = sorted({value.strip() for value in values if value})
        logger.debug("Separated keyword values count=%d", len(deduped))
        return deduped
    filtered = [value for value in values if value]
    logger.debug("Collapsed keyword values count=%d", len(filtered))
    return filtered


@router.get("/technologies/", response_model=List[str])
async def list_technologies(
    filters: ContactFilterParams = Depends(),
    params: AttributeListParams = Depends(),
    separated: bool = Query(True),
    session: AsyncSession = Depends(get_db),
) -> List[str]:
    """Return technology values for associated companies."""
    column_factory = (
        (lambda Contact, Company, ContactMetadata, CompanyMetadata: func.unnest(Company.technologies))
        if separated
        else (
            lambda Contact, Company, ContactMetadata, CompanyMetadata: func.array_to_string(
                Company.technologies, ","
            )
        )
    )
    values = await _attribute_endpoint(session, filters, params, column_factory, "technologies")
    if separated:
        deduped = sorted({value.strip() for value in values if value})
        logger.debug("Separated technology values count=%d", len(deduped))
        return deduped
    filtered = [value for value in values if value]
    logger.debug("Collapsed technology values count=%d", len(filtered))
    return filtered


@router.get("/city/", response_model=List[str])
async def list_person_cities(
    filters: ContactFilterParams = Depends(),
    params: AttributeListParams = Depends(),
    session: AsyncSession = Depends(get_db),
) -> List[str]:
    """Return city names for individual contacts."""
    return await _attribute_endpoint(
        session,
        filters,
        params,
        lambda Contact, Company, ContactMetadata, CompanyMetadata: ContactMetadata.city,
        "person_city",
    )


@router.get("/state/", response_model=List[str])
async def list_person_states(
    filters: ContactFilterParams = Depends(),
    params: AttributeListParams = Depends(),
    session: AsyncSession = Depends(get_db),
) -> List[str]:
    """Return state values for individual contacts."""
    return await _attribute_endpoint(
        session,
        filters,
        params,
        lambda Contact, Company, ContactMetadata, CompanyMetadata: ContactMetadata.state,
        "person_state",
    )


@router.get("/country/", response_model=List[str])
async def list_person_countries(
    filters: ContactFilterParams = Depends(),
    params: AttributeListParams = Depends(),
    session: AsyncSession = Depends(get_db),
) -> List[str]:
    """Return country values for individual contacts."""
    return await _attribute_endpoint(
        session,
        filters,
        params,
        lambda Contact, Company, ContactMetadata, CompanyMetadata: ContactMetadata.country,
        "person_country",
    )


@router.get("/company_address/", response_model=List[str])
async def list_company_addresses(
    filters: ContactFilterParams = Depends(),
    params: AttributeListParams = Depends(),
    session: AsyncSession = Depends(get_db),
) -> List[str]:
    """Return mailing addresses for related companies."""
    return await _attribute_endpoint(
        session,
        filters,
        params,
        lambda Contact, Company, ContactMetadata, CompanyMetadata: Company.address,
        "company_address",
    )


@router.get("/company_city/", response_model=List[str])
async def list_company_cities(
    filters: ContactFilterParams = Depends(),
    params: AttributeListParams = Depends(),
    session: AsyncSession = Depends(get_db),
) -> List[str]:
    """Return company city values sourced from metadata."""
    return await _attribute_endpoint(
        session,
        filters,
        params,
        lambda Contact, Company, ContactMetadata, CompanyMetadata: CompanyMetadata.city,
        "company_city",
    )


@router.get("/company_state/", response_model=List[str])
async def list_company_states(
    filters: ContactFilterParams = Depends(),
    params: AttributeListParams = Depends(),
    session: AsyncSession = Depends(get_db),
) -> List[str]:
    """Return company state values sourced from metadata."""
    return await _attribute_endpoint(
        session,
        filters,
        params,
        lambda Contact, Company, ContactMetadata, CompanyMetadata: CompanyMetadata.state,
        "company_state",
    )


@router.get("/company_country/", response_model=List[str])
async def list_company_countries(
    filters: ContactFilterParams = Depends(),
    params: AttributeListParams = Depends(),
    session: AsyncSession = Depends(get_db),
) -> List[str]:
    """Return company country values sourced from metadata."""
    return await _attribute_endpoint(
        session,
        filters,
        params,
        lambda Contact, Company, ContactMetadata, CompanyMetadata: CompanyMetadata.country,
        "company_country",
    )

