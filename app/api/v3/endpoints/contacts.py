"""Contacts API endpoints providing list and attribute lookups."""

from __future__ import annotations

import json
import time
from typing import Any, Callable, Iterable, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    resolve_pagination_params,
)
from app.clients.connectra_client import ConnectraClient
from app.core.config import get_settings
from app.core.vql.parser import VQLParser
from app.db.session import get_db
from app.models.contacts import Contact
from app.models.user import User
from app.schemas.common import CountResponse, CursorPage, LinkedInSearchRequest, LinkedInSearchResponse
from app.schemas.contacts import ContactDetail, ContactListItem, ContactSimpleItem
from app.schemas.filters import AttributeListParams, ContactFilterParams, FilterDataRequest
from app.schemas.vql import VQLFilterDataResponse, VQLFilterDefinition, VQLFiltersResponse, VQLQuery
from app.services.contacts_service import ContactsService
from app.utils.cursor import decode_offset_cursor
from app.utils.normalization import normalize_list_param
from app.utils.pagination_cache import build_list_meta, build_pagination_links
from app.utils.logger import get_logger
from app.utils.streaming_queries import stream_query_results

logger = get_logger(__name__)
settings = get_settings()
router = APIRouter(prefix="/contacts", tags=["Contacts"])
service = ContactsService()


# VQL-based endpoints
@router.post("/query", response_model=CursorPage[ContactListItem])
async def query_contacts(
    vql_query: VQLQuery,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CursorPage[ContactListItem]:
    """
    Query contacts using VQL (Vivek Query Language).
    
    This endpoint replaces the old GET /contacts/ endpoint with a more flexible
    filter-based query system supporting complex conditions, field selection, and
    related entity population.
    """
    # Query contacts using VQL
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
async def count_contacts_vql(
    vql_query: VQLQuery,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CountResponse:
    """
    Count contacts matching VQL query.
    
    This endpoint replaces the old GET /contacts/count/ endpoint.
    """
    return await service.count_with_vql(session, vql_query)


@router.get("/filters", response_model=VQLFiltersResponse)
async def get_contact_filters(
    current_user: User = Depends(get_current_user),
) -> VQLFiltersResponse:
    """
    Get available filters for contacts.
    
    Returns:
        List of filter definitions with metadata about each filterable field
    """
    async with ConnectraClient() as client:
        filters = await client.get_filters("contact")
    
    # Convert dicts to VQLFilterDefinition objects
    filter_definitions = [VQLFilterDefinition(**filter_dict) for filter_dict in filters]
    return VQLFiltersResponse(data=filter_definitions)


@router.post("/filters/data", response_model=VQLFilterDataResponse)
async def get_contact_filter_data(
    request: FilterDataRequest,
    current_user: User = Depends(get_current_user),
) -> VQLFilterDataResponse:
    """
    Get filter data values for a specific contact filter.
    
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


# Old endpoints removed - use VQL endpoints instead


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


# Old count endpoints removed - use VQL endpoints instead


# All attribute listing endpoints removed - use VQL query endpoint with field selection instead


@router.post("/linkedin/search", response_model=LinkedInSearchResponse)
async def search_contacts_by_linkedin_urls(
    request: LinkedInSearchRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LinkedInSearchResponse:
    """
    Search contacts by LinkedIn URLs.
    
    Searches for contacts whose linkedin_url matches any of the provided LinkedIn URLs.
    Uses VQL query with 'in' operator to match multiple URLs efficiently.
    
    Args:
        request: LinkedIn search request with list of URLs and optional return format
        
    Returns:
        LinkedInSearchResponse with list of contact UUIDs and count
    """
    from app.core.vql.structures import VQLCondition, VQLFilter, VQLOperator, VQLQuery
    
    # Build VQL query to search contacts by linkedin_url
    # Use 'in' operator to match any of the provided URLs
    condition = VQLCondition(
        field="linkedin_url",
        operator=VQLOperator.IN,
        value=request.urls
    )
    
    vql_query = VQLQuery(
        filters=VQLFilter(and_=[condition]),
        select_columns=["uuid"],  # Only need UUIDs for this search
        limit=1000,  # Set high limit to get all matching contacts
        offset=0
    )
    
    # Query contacts using VQL
    results = await service.query_with_vql(session, vql_query)
    
    # Extract UUIDs from results
    contact_ids = [contact.uuid for contact in results]
    
    return LinkedInSearchResponse(
        contact_ids=contact_ids,
        count=len(contact_ids)
    )


@router.get("/{contact_uuid}/", response_model=ContactDetail)
async def retrieve_contact(
    contact_uuid: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContactDetail:
    """Retrieve a single contact by UUID."""
    contact = await service.get_contact(session, contact_uuid)
    return contact

