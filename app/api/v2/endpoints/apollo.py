"""Apollo.io URL Analysis API endpoints."""

from typing import Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.logging import get_logger, log_function_call
from app.db.session import get_db
from app.models.user import User
from app.schemas.apollo import (
    ApolloContactsSearchResponse,
    ApolloUrlAnalysisRequest,
    ApolloUrlAnalysisResponse,
    MappingSummary,
    UnmappedCategory,
    UnmappedParameter,
)
from app.schemas.common import CursorPage
from app.schemas.contacts import ContactListItem, ContactSimpleItem
from app.schemas.filters import ContactFilterParams
from app.services.apollo_analysis_service import ApolloAnalysisService
from app.services.contacts_service import ContactsService

router = APIRouter(prefix="/apollo", tags=["Apollo"])
logger = get_logger(__name__)
settings = get_settings()
service = ApolloAnalysisService()
contacts_service = ContactsService()


@router.post("/analyze", response_model=ApolloUrlAnalysisResponse)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
async def analyze_apollo_url(
    request_data: ApolloUrlAnalysisRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ApolloUrlAnalysisResponse:
    """
    Analyze an Apollo.io URL and return structured parameter breakdown.

    This endpoint parses Apollo.io search URLs (typically from the People Search page)
    and extracts all query parameters, categorizing them into logical groups such as:
    - Pagination (page numbers)
    - Sorting (sort field and direction)
    - Person Filters (titles, locations, seniorities, departments)
    - Organization Filters (employee ranges, locations, industries, revenue)
    - Email Filters (verification status, catch-all exclusion)
    - Keyword Filters (organization keywords, search fields)
    - And more...

    The analysis includes:
    - URL structure breakdown (base URL, hash path, query string)
    - Categorized parameters with descriptions
    - Parameter values (URL-decoded)
    - Statistics about the search criteria

    Args:
        request_data: Request containing the Apollo.io URL to analyze
        current_user: Authenticated user (from dependency)
        session: Database session (from dependency)

    Returns:
        ApolloUrlAnalysisResponse with complete URL analysis

    Raises:
        HTTPException: If URL is invalid, not from Apollo.io, or analysis fails
    """
    logger.info(
        "Apollo URL analysis request: user_id=%s url_length=%d",
        current_user.id,
        len(request_data.url),
    )

    try:
        result = service.analyze_url(request_data.url)
        logger.info(
            "Apollo URL analyzed successfully: user_id=%s total_params=%d categories=%d",
            current_user.id,
            result.statistics.total_parameters,
            result.statistics.categories_used,
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Apollo URL analysis failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while analyzing the URL",
        ) from exc


@router.post("/contacts", response_model=ApolloContactsSearchResponse[Union[ContactListItem, ContactSimpleItem]])
@log_function_call(logger=logger, log_arguments=True, log_result=True)
async def search_contacts_from_apollo_url(
    request_data: ApolloUrlAnalysisRequest,
    request: Request,
    limit: Optional[int] = Query(None, ge=1),
    offset: Optional[int] = Query(0, ge=0),
    cursor: Optional[str] = Query(None),
    view: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ApolloContactsSearchResponse[Union[ContactListItem, ContactSimpleItem]]:
    """
    Search contacts using Apollo.io URL parameters.

    This endpoint converts an Apollo.io People Search URL into contact filter
    parameters and returns matching contacts from the database. It provides a
    seamless way to replicate Apollo.io searches in your own contact database.

    **Parameter Mappings:**
    - `page` → `page`
    - `sortByField` + `sortAscending` → `ordering` (with `-` prefix for descending)
    - `personTitles[]` → `title` (comma-separated for OR logic)
    - `personNotTitles[]` → `exclude_titles`
    - `personSeniorities[]` → `seniority` (comma-separated)
    - `personDepartmentOrSubdepartments[]` → `department` (comma-separated)
    - `personLocations[]` → `contact_location` (comma-separated)
    - `personNotLocations[]` → `exclude_contact_locations`
    - `organizationNumEmployeesRanges[]` → `employees_min`, `employees_max`
    - `organizationLocations[]` → `company_location` (comma-separated)
    - `organizationNotLocations[]` → `exclude_company_locations`
    - `revenueRange[min/max]` → `annual_revenue_min`, `annual_revenue_max`
    - `contactEmailStatusV2[]` → `email_status` (comma-separated)
    - `qOrganizationKeywordTags[]` → `keywords` (comma-separated)
    - `qNotOrganizationKeywordTags[]` → `exclude_keywords`
    - `qKeywords` → `search`

    **Skipped Parameters:**
    - ID-based filters (industry tags, technology UIDs) - no mapping available
    - Apollo-specific features (search lists, personas, intent, lookalike)
    - Unmapped filters (job postings, trading status, market segments)

    Args:
        request_data: Request containing the Apollo.io URL to convert
        request: FastAPI request object for URL construction
        limit: Maximum number of results per page
        offset: Starting offset for results
        cursor: Opaque cursor token for pagination
        view: When "simple", returns ContactSimpleItem, otherwise ContactListItem
        current_user: Authenticated user (from dependency)
        session: Database session (from dependency)

    Returns:
        CursorPage containing ContactListItem or ContactSimpleItem results

    Raises:
        HTTPException: If URL is invalid, not from Apollo.io, or query fails
    """
    logger.info(
        "Apollo contacts search request: user_id=%s url_length=%d",
        current_user.id,
        len(request_data.url),
    )

    try:
        # Step 1: Analyze the Apollo URL to extract parameters
        analysis = service.analyze_url(request_data.url)
        logger.info(
            "Apollo URL analyzed: total_params=%d categories=%d",
            analysis.statistics.total_parameters,
            analysis.statistics.categories_used,
        )

        # Step 2: Map Apollo parameters to contact filter parameters (with unmapped tracking)
        filter_dict, unmapped_dict = service.map_to_contact_filters(analysis.raw_parameters, include_unmapped=True)
        logger.debug("Mapped filter dictionary: %s", filter_dict)
        logger.debug("Unmapped parameters: %d", len(unmapped_dict))

        # Step 3: Validate and construct ContactFilterParams
        try:
            filters = ContactFilterParams.model_validate(filter_dict)
        except ValidationError as exc:
            logger.warning("Invalid contact filter parameters: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid filter parameters: {exc.errors()[0].get('msg', 'Validation error')}",
            ) from exc

        # Step 4: Determine pagination settings
        page_size = filters.page_size if filters.page_size is not None else limit or settings.DEFAULT_PAGE_SIZE
        page_limit = min(page_size, settings.MAX_PAGE_SIZE)

        use_cursor = False
        resolved_offset = offset or 0
        cursor_token = cursor or filters.cursor
        
        if cursor_token:
            try:
                from app.utils.cursor import decode_offset_cursor
                resolved_offset = decode_offset_cursor(cursor_token)
            except ValueError as exc:
                logger.warning("Invalid cursor token: token=%s error=%s", cursor_token, exc)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid cursor value",
                ) from exc
            use_cursor = True
        elif filters.page is not None:
            resolved_offset = (filters.page - 1) * page_limit

        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
        logger.info(
            "Searching contacts with Apollo filters: limit=%d offset=%d use_cursor=%s filters=%s",
            page_limit,
            resolved_offset,
            use_cursor,
            active_filter_keys,
        )

        # Step 5: Query contacts based on view parameter
        if (view or "").strip().lower() == "simple":
            page = await contacts_service.list_contacts_simple(
                session,
                filters,
                limit=page_limit,
                offset=resolved_offset,
                request_url=str(request.url),
                use_cursor=use_cursor,
            )
        else:
            page = await contacts_service.list_contacts(
                session,
                filters,
                limit=page_limit,
                offset=resolved_offset,
                request_url=str(request.url),
                use_cursor=use_cursor,
            )

        logger.info(
            "Apollo contacts search completed: user_id=%s returned=%d has_next=%s",
            current_user.id,
            len(page.results),
            bool(page.next),
        )

        # Step 6: Build unmapped categories structure from analysis
        unmapped_categories = []
        category_unmapped_map = {}  # Map category name to list of unmapped parameters
        
        # Group unmapped parameters by category
        for param_name, (param_values, reason) in unmapped_dict.items():
            # Find the category for this parameter from the analysis
            param_category = "Other"
            for category in analysis.categories:
                for param in category.parameters:
                    if param.name == param_name:
                        param_category = category.name
                        break
            
            if param_category not in category_unmapped_map:
                category_unmapped_map[param_category] = []
            
            category_unmapped_map[param_category].append(
                UnmappedParameter(
                    name=param_name,
                    values=param_values,
                    category=param_category,
                    reason=reason
                )
            )
        
        # Build UnmappedCategory objects
        for category_name, params in category_unmapped_map.items():
            unmapped_categories.append(
                UnmappedCategory(
                    name=category_name,
                    parameters=params,
                    total_parameters=len(params)
                )
            )
        
        # Step 7: Build mapping summary
        mapped_param_names = sorted(
            [p for p in analysis.raw_parameters.keys() if p not in unmapped_dict]
        )
        unmapped_param_names = sorted(unmapped_dict.keys())
        
        mapping_summary = MappingSummary(
            total_apollo_parameters=len(analysis.raw_parameters),
            mapped_parameters=len(mapped_param_names),
            unmapped_parameters=len(unmapped_param_names),
            mapped_parameter_names=mapped_param_names,
            unmapped_parameter_names=unmapped_param_names
        )
        
        # Step 8: Build final response with mapping metadata
        response = ApolloContactsSearchResponse[Union[ContactListItem, ContactSimpleItem]](
            count=page.count,
            next=page.next,
            previous=page.previous,
            results=page.results,
            apollo_url=request_data.url,
            mapping_summary=mapping_summary,
            unmapped_categories=unmapped_categories
        )
        
        logger.info(
            "Apollo contacts response built: mapped=%d unmapped=%d unmapped_categories=%d",
            mapping_summary.mapped_parameters,
            mapping_summary.unmapped_parameters,
            len(unmapped_categories),
        )

        return response

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Apollo contacts search failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while searching contacts",
        ) from exc

