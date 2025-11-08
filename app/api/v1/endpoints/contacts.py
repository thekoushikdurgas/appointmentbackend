from __future__ import annotations

from typing import Callable, List, Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.common import CountResponse, CursorPage
from app.schemas.contacts import ContactDetail, ContactListItem
from app.schemas.filters import AttributeListParams, ContactFilterParams
from app.services.contacts_service import ContactsService
from app.utils.cursor import decode_offset_cursor


settings = get_settings()
router = APIRouter(prefix="/contacts", tags=["Contacts"])
service = ContactsService()


def _resolve_pagination(
    filters: ContactFilterParams,
    limit: Optional[int],
) -> int:
    page_size = filters.page_size if filters.page_size is not None else limit or settings.DEFAULT_PAGE_SIZE
    return min(page_size, settings.MAX_PAGE_SIZE)


@router.get("/", response_model=CursorPage[ContactListItem])
async def list_contacts(
    request: Request,
    filters: ContactFilterParams = Depends(),
    limit: Optional[int] = Query(None, ge=1),
    offset: Optional[int] = Query(0, ge=0),
    cursor: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db),
) -> CursorPage[ContactListItem]:
    page_limit = _resolve_pagination(filters, limit)
    use_cursor = False
    resolved_offset = offset or 0
    cursor_token = cursor or filters.cursor
    if cursor_token:
        resolved_offset = decode_offset_cursor(cursor_token)
        use_cursor = True

    page = await service.list_contacts(
        session,
        filters,
        limit=page_limit,
        offset=resolved_offset,
        request_url=str(request.url),
        use_cursor=use_cursor,
    )
    return page


@router.get("/count/", response_model=CountResponse)
async def count_contacts(
    filters: ContactFilterParams = Depends(),
    session: AsyncSession = Depends(get_db),
) -> CountResponse:
    return await service.count_contacts(session, filters)


@router.get("/{contact_id}", response_model=ContactDetail)
async def retrieve_contact(
    contact_id: int,
    session: AsyncSession = Depends(get_db),
) -> ContactDetail:
    return await service.get_contact(session, contact_id)


async def _attribute_endpoint(
    session: AsyncSession,
    filters: ContactFilterParams,
    params: AttributeListParams,
    column_factory: Callable,
) -> List[str]:
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
        return unique_values
    return values


@router.get("/title/", response_model=List[str])
async def list_titles(
    filters: ContactFilterParams = Depends(),
    params: AttributeListParams = Depends(),
    session: AsyncSession = Depends(get_db),
) -> List[str]:
    return await _attribute_endpoint(
        session,
        filters,
        params,
        lambda Contact, Company, ContactMetadata, CompanyMetadata: Contact.title,
    )


@router.get("/company/", response_model=List[str])
async def list_companies(
    filters: ContactFilterParams = Depends(),
    params: AttributeListParams = Depends(),
    session: AsyncSession = Depends(get_db),
) -> List[str]:
    return await _attribute_endpoint(
        session,
        filters,
        params,
        lambda Contact, Company, ContactMetadata, CompanyMetadata: Company.name,
    )


@router.get("/industry/", response_model=List[str])
async def list_industries(
    filters: ContactFilterParams = Depends(),
    params: AttributeListParams = Depends(),
    session: AsyncSession = Depends(get_db),
) -> List[str]:
    return await _attribute_endpoint(
        session,
        filters,
        params,
        lambda Contact, Company, ContactMetadata, CompanyMetadata: func.unnest(Company.industries),
    )


@router.get("/keywords/", response_model=List[str])
async def list_keywords(
    filters: ContactFilterParams = Depends(),
    params: AttributeListParams = Depends(),
    separated: bool = Query(False),
    session: AsyncSession = Depends(get_db),
) -> List[str]:
    column_factory = (
        (lambda Contact, Company, ContactMetadata, CompanyMetadata: func.unnest(Company.keywords))
        if separated
        else (
            lambda Contact, Company, ContactMetadata, CompanyMetadata: func.array_to_string(
                Company.keywords, ","
            )
        )
    )
    values = await _attribute_endpoint(session, filters, params, column_factory)
    if separated:
        return sorted({value.strip() for value in values if value})
    return [value for value in values if value]


@router.get("/technologies/", response_model=List[str])
async def list_technologies(
    filters: ContactFilterParams = Depends(),
    params: AttributeListParams = Depends(),
    separated: bool = Query(True),
    session: AsyncSession = Depends(get_db),
) -> List[str]:
    column_factory = (
        (lambda Contact, Company, ContactMetadata, CompanyMetadata: func.unnest(Company.technologies))
        if separated
        else (
            lambda Contact, Company, ContactMetadata, CompanyMetadata: func.array_to_string(
                Company.technologies, ","
            )
        )
    )
    values = await _attribute_endpoint(session, filters, params, column_factory)
    if separated:
        return sorted({value.strip() for value in values if value})
    return [value for value in values if value]


@router.get("/city/", response_model=List[str])
async def list_person_cities(
    filters: ContactFilterParams = Depends(),
    params: AttributeListParams = Depends(),
    session: AsyncSession = Depends(get_db),
) -> List[str]:
    return await _attribute_endpoint(
        session,
        filters,
        params,
        lambda Contact, Company, ContactMetadata, CompanyMetadata: ContactMetadata.city,
    )


@router.get("/state/", response_model=List[str])
async def list_person_states(
    filters: ContactFilterParams = Depends(),
    params: AttributeListParams = Depends(),
    session: AsyncSession = Depends(get_db),
) -> List[str]:
    return await _attribute_endpoint(
        session,
        filters,
        params,
        lambda Contact, Company, ContactMetadata, CompanyMetadata: ContactMetadata.state,
    )


@router.get("/country/", response_model=List[str])
async def list_person_countries(
    filters: ContactFilterParams = Depends(),
    params: AttributeListParams = Depends(),
    session: AsyncSession = Depends(get_db),
) -> List[str]:
    return await _attribute_endpoint(
        session,
        filters,
        params,
        lambda Contact, Company, ContactMetadata, CompanyMetadata: ContactMetadata.country,
    )


@router.get("/company_address/", response_model=List[str])
async def list_company_addresses(
    filters: ContactFilterParams = Depends(),
    params: AttributeListParams = Depends(),
    session: AsyncSession = Depends(get_db),
) -> List[str]:
    return await _attribute_endpoint(
        session,
        filters,
        params,
        lambda Contact, Company, ContactMetadata, CompanyMetadata: Company.address,
    )


@router.get("/company_city/", response_model=List[str])
async def list_company_cities(
    filters: ContactFilterParams = Depends(),
    params: AttributeListParams = Depends(),
    session: AsyncSession = Depends(get_db),
) -> List[str]:
    return await _attribute_endpoint(
        session,
        filters,
        params,
        lambda Contact, Company, ContactMetadata, CompanyMetadata: CompanyMetadata.city,
    )


@router.get("/company_state/", response_model=List[str])
async def list_company_states(
    filters: ContactFilterParams = Depends(),
    params: AttributeListParams = Depends(),
    session: AsyncSession = Depends(get_db),
) -> List[str]:
    return await _attribute_endpoint(
        session,
        filters,
        params,
        lambda Contact, Company, ContactMetadata, CompanyMetadata: CompanyMetadata.state,
    )


@router.get("/company_country/", response_model=List[str])
async def list_company_countries(
    filters: ContactFilterParams = Depends(),
    params: AttributeListParams = Depends(),
    session: AsyncSession = Depends(get_db),
) -> List[str]:
    return await _attribute_endpoint(
        session,
        filters,
        params,
        lambda Contact, Company, ContactMetadata, CompanyMetadata: CompanyMetadata.country,
    )

