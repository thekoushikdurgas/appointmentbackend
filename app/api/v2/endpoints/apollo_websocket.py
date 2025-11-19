"""WebSocket endpoints for Apollo.io URL analysis and contact operations."""

import json
from typing import Optional, Union

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_websocket
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.schemas.apollo import (
    ApolloContactsSearchResponse,
    ApolloUrlAnalysisRequest,
    ApolloUrlAnalysisResponse,
    ApolloWebSocketRequest,
    ApolloWebSocketResponse,
    MappingSummary,
    ParameterCategory,
    ParameterDetail,
    UnmappedCategory,
    UnmappedParameter,
)
from app.schemas.common import CountResponse, UuidListResponse
from app.schemas.contacts import ContactListItem, ContactSimpleItem
from app.schemas.filters import ContactFilterParams
from app.services.apollo_analysis_service import ApolloAnalysisService
from app.services.contacts_service import ContactsService
from app.utils.cursor import decode_offset_cursor
from app.utils.industry_mapping import get_industry_names_from_ids

router = APIRouter(prefix="/apollo", tags=["Apollo WebSocket"])
logger = get_logger(__name__)
settings = get_settings()
service = ApolloAnalysisService()
contacts_service = ContactsService()


class ApolloWebSocketManager:
    """Manages WebSocket connections for Apollo endpoints."""

    def __init__(self):
        """Initialize the connection manager."""
        self.active_connections: dict[str, WebSocket] = {}  # user_id -> websocket

    async def connect(self, websocket: WebSocket, user: User) -> None:
        """
        Accept and store a new WebSocket connection.
        
        Args:
            websocket: WebSocket connection object
            user: Authenticated user
        """
        await websocket.accept()
        self.active_connections[str(user.id)] = websocket
        logger.info("WebSocket connected: user_id=%s total_connections=%d", user.id, len(self.active_connections))

    def disconnect(self, user_id: str) -> None:
        """
        Remove a disconnected WebSocket connection.
        
        Args:
            user_id: User ID whose connection to remove
        """
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info("WebSocket disconnected: user_id=%s total_connections=%d", user_id, len(self.active_connections))

    async def send_message(self, websocket: WebSocket, message: dict) -> None:
        """
        Send a JSON message to the WebSocket connection.
        
        Args:
            websocket: WebSocket connection object
            message: Message dictionary to send
        """
        try:
            await websocket.send_json(message)
        except Exception as exc:
            logger.error("Error sending WebSocket message: %s", exc)
            raise


# Global connection manager instance
connection_manager = ApolloWebSocketManager()


def _convert_industry_tagids_to_names(param_name: str, tag_ids: list[str]) -> list[str]:
    """
    Convert industry Tag IDs to industry names for display in API responses.
    
    Args:
        param_name: The parameter name (e.g., 'organizationIndustryTagIds[]')
        tag_ids: List of Tag IDs or other values
        
    Returns:
        List of industry names if param is industry-related, otherwise original values
    """
    if param_name in ("organizationIndustryTagIds[]", "organizationNotIndustryTagIds[]"):
        industry_names = get_industry_names_from_ids(tag_ids)
        if industry_names:
            logger.debug(
                "Converted %d Tag IDs to industry names for display: %s → %s",
                len(tag_ids),
                tag_ids[:3],
                industry_names[:3],
            )
            return industry_names
        else:
            logger.warning(
                "Failed to convert Tag IDs to industry names for %s: %s",
                param_name,
                tag_ids[:5],
            )
    return tag_ids


def _normalize_list_query_param(param_value: Optional[list[str]]) -> Optional[list[str]]:
    """
    Normalize a list query parameter by splitting comma-separated values.
    
    Args:
        param_value: Optional list of strings from query parameter
        
    Returns:
        Normalized list with comma-separated values split, or None if input is None/empty
    """
    if not param_value:
        return None
    
    normalized = []
    for item in param_value:
        if item:
            parts = item.split(",")
            for part in parts:
                trimmed = part.strip()
                if trimmed:
                    normalized.append(trimmed)
    
    return normalized if normalized else None


def _resolve_pagination(filters: ContactFilterParams, limit: Optional[int]) -> Optional[int]:
    """Choose the most appropriate page size within configured bounds."""
    if limit is not None:
        logger.debug("Resolved pagination: explicit limit=%d (no cap applied)", limit)
        return limit
    
    if filters.page_size is not None:
        if settings.MAX_PAGE_SIZE is not None:
            resolved = min(filters.page_size, settings.MAX_PAGE_SIZE)
            logger.debug("Resolved pagination: page_size=%d capped to %d", filters.page_size, resolved)
            return resolved
        logger.debug("Resolved pagination: page_size=%d (no cap)", filters.page_size)
        return filters.page_size
    
    logger.debug("Resolved pagination: default=unlimited (None)")
    return None


async def _send_error_response(
    websocket: WebSocket,
    request_id: str,
    action: str,
    error_message: str,
    error_code: Optional[str] = None,
) -> None:
    """
    Send an error response via WebSocket.
    
    Args:
        websocket: WebSocket connection
        request_id: Request ID from client
        action: Action that failed
        error_message: Error message
        error_code: Optional error code
    """
    response = ApolloWebSocketResponse(
        request_id=request_id,
        action=action,
        status="error",
        data=None,
        error={"message": error_message, "code": error_code},
    )
    # Use mode='json' to serialize datetime objects to ISO format strings
    await connection_manager.send_message(websocket, response.model_dump(mode='json'))


async def _send_success_response(
    websocket: WebSocket,
    request_id: str,
    action: str,
    data: dict,
) -> None:
    """
    Send a success response via WebSocket.
    
    Args:
        websocket: WebSocket connection
        request_id: Request ID from client
        action: Action that succeeded
        data: Response data
    """
    response = ApolloWebSocketResponse(
        request_id=request_id,
        action=action,
        status="success",
        data=data,
        error=None,
    )
    # Use mode='json' to serialize datetime objects to ISO format strings
    await connection_manager.send_message(websocket, response.model_dump(mode='json'))


async def _parse_websocket_message(websocket: WebSocket, text: str) -> Optional[ApolloWebSocketRequest]:
    """
    Parse and validate a WebSocket message.
    
    Args:
        websocket: WebSocket connection
        text: Raw message text
        
    Returns:
        Parsed request object or None if invalid
    """
    try:
        data = json.loads(text)
        request = ApolloWebSocketRequest.model_validate(data)
        return request
    except json.JSONDecodeError as exc:
        logger.warning("Invalid JSON in WebSocket message: %s", exc)
        await _send_error_response(
            websocket,
            "unknown",
            "unknown",
            "Invalid JSON format",
            "invalid_json",
        )
        return None
    except ValidationError as exc:
        logger.warning("Invalid WebSocket request format: %s", exc)
        await _send_error_response(
            websocket,
            data.get("request_id", "unknown") if isinstance(data, dict) else "unknown",
            data.get("action", "unknown") if isinstance(data, dict) else "unknown",
            f"Invalid request format: {exc.errors()[0].get('msg', 'Validation error')}",
            "validation_error",
        )
        return None


async def _handle_analyze_action(websocket: WebSocket, request: ApolloWebSocketRequest) -> None:
    """Handle the analyze action."""
    if "url" not in request.data:
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            "Missing required field: url",
            "missing_field",
        )
        return
    
    try:
        # Analyze the URL
        result = await service.analyze_url(request.data["url"])
        
        # Convert Tag IDs to industry names
        converted_categories = []
        converted_raw_parameters = {}
        
        for category in result.categories:
            converted_params = []
            for param in category.parameters:
                converted_values = _convert_industry_tagids_to_names(param.name, param.values)
                converted_params.append(
                    ParameterDetail(
                        name=param.name,
                        values=converted_values,
                        description=param.description,
                        category=param.category,
                    )
                )
            converted_categories.append(
                ParameterCategory(
                    name=category.name,
                    parameters=converted_params,
                    total_parameters=category.total_parameters,
                )
            )
        
        for param_name, param_values in result.raw_parameters.items():
            converted_raw_parameters[param_name] = _convert_industry_tagids_to_names(
                param_name, param_values
            )
        
        # Build response data
        # Use mode='json' to serialize datetime objects to ISO format strings
        response_data = {
            "url": result.url,
            "url_structure": result.url_structure.model_dump(mode='json'),
            "categories": [cat.model_dump(mode='json') for cat in converted_categories],
            "statistics": result.statistics.model_dump(mode='json'),
            "raw_parameters": converted_raw_parameters,
        }
        
        await _send_success_response(websocket, request.request_id, request.action, response_data)
        
    except Exception as exc:
        logger.exception("Error analyzing Apollo URL via WebSocket: %s", exc)
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            f"An error occurred while analyzing the URL: {str(exc)}",
            "analysis_error",
        )


async def _handle_search_contacts_action(websocket: WebSocket, request: ApolloWebSocketRequest) -> None:
    """Handle the search_contacts action."""
    if "url" not in request.data:
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            "Missing required field: url",
            "missing_field",
        )
        return
    
    try:
        async with AsyncSessionLocal() as session:
            # Step 1: Analyze the Apollo URL
            analysis = await service.analyze_url(request.data["url"])
            
            # Step 2: Map Apollo parameters to contact filter parameters
            filter_dict, unmapped_dict = service.map_to_contact_filters(
                analysis.raw_parameters, include_unmapped=True
            )
            
            # Step 2.5: Apply additional filters from request data
            if "include_company_name" in request.data:
                filter_dict["include_company_name"] = request.data["include_company_name"]
            if "exclude_company_name" in request.data:
                filter_dict["exclude_company_name"] = request.data["exclude_company_name"]
            if "include_domain_list" in request.data:
                normalized = _normalize_list_query_param(request.data["include_domain_list"])
                if normalized is not None:
                    filter_dict["include_domain_list"] = normalized
            if "exclude_domain_list" in request.data:
                normalized = _normalize_list_query_param(request.data["exclude_domain_list"])
                if normalized is not None:
                    filter_dict["exclude_domain_list"] = normalized
            
            # Step 3: Validate and construct ContactFilterParams
            try:
                filters = ContactFilterParams.model_validate(filter_dict)
            except ValidationError as exc:
                await _send_error_response(
                    websocket,
                    request.request_id,
                    request.action,
                    f"Invalid filter parameters: {exc.errors()[0].get('msg', 'Validation error')}",
                    "validation_error",
                )
                return
            
            # Step 4: Determine pagination settings
            limit = request.data.get("limit")
            page_limit = _resolve_pagination(filters, limit)
            
            offset = request.data.get("offset", 0)
            cursor = request.data.get("cursor")
            view = request.data.get("view")
            
            use_cursor = False
            resolved_offset = offset
            cursor_token = cursor or filters.cursor
            
            if cursor_token:
                try:
                    resolved_offset = decode_offset_cursor(cursor_token)
                except ValueError as exc:
                    await _send_error_response(
                        websocket,
                        request.request_id,
                        request.action,
                        f"Invalid cursor token: {str(exc)}",
                        "invalid_cursor",
                    )
                    return
                use_cursor = True
            elif offset == 0 and filters.page is not None and page_limit is not None:
                resolved_offset = (filters.page - 1) * page_limit
            
            # Step 5: Query contacts
            if (view or "").strip().lower() == "simple":
                page = await contacts_service.list_contacts_simple(
                    session,
                    filters,
                    limit=page_limit,
                    offset=resolved_offset,
                    request_url="",
                    use_cursor=use_cursor,
                )
            else:
                page = await contacts_service.list_contacts(
                    session,
                    filters,
                    limit=page_limit,
                    offset=resolved_offset,
                    request_url="",
                    use_cursor=use_cursor,
                )
            
            # Step 6: Build unmapped categories structure
            unmapped_categories = []
            category_unmapped_map = {}
            
            for param_name, (param_values, reason) in unmapped_dict.items():
                param_category = "Other"
                for category in analysis.categories:
                    for param in category.parameters:
                        if param.name == param_name:
                            param_category = category.name
                            break
                
                if param_category not in category_unmapped_map:
                    category_unmapped_map[param_category] = []
                
                converted_values = _convert_industry_tagids_to_names(param_name, param_values)
                
                category_unmapped_map[param_category].append(
                    UnmappedParameter(
                        name=param_name,
                        values=converted_values,
                        category=param_category,
                        reason=reason,
                    )
                )
            
            for category_name, params in category_unmapped_map.items():
                unmapped_categories.append(
                    UnmappedCategory(
                        name=category_name,
                        parameters=params,
                        total_parameters=len(params),
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
                unmapped_parameter_names=unmapped_param_names,
            )
            
            # Step 8: Build response data
            # Use mode='json' to serialize datetime objects to ISO format strings
            response_data = {
                "next": page.next,
                "previous": page.previous,
                "results": [item.model_dump(mode='json') for item in page.results],
                "apollo_url": request.data["url"],
                "mapping_summary": mapping_summary.model_dump(mode='json'),
                "unmapped_categories": [cat.model_dump(mode='json') for cat in unmapped_categories],
            }
            
            await _send_success_response(websocket, request.request_id, request.action, response_data)
    
    except Exception as exc:
        logger.exception("Error searching contacts via WebSocket: %s", exc)
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            f"An error occurred while searching contacts: {str(exc)}",
            "search_error",
        )


async def _handle_count_contacts_action(websocket: WebSocket, request: ApolloWebSocketRequest) -> None:
    """Handle the count_contacts action."""
    if "url" not in request.data:
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            "Missing required field: url",
            "missing_field",
        )
        return
    
    try:
        async with AsyncSessionLocal() as session:
            # Step 1: Analyze the Apollo URL
            analysis = await service.analyze_url(request.data["url"])
            
            # Step 2: Map Apollo parameters to contact filter parameters
            filter_dict, unmapped_dict = service.map_to_contact_filters(
                analysis.raw_parameters, include_unmapped=True
            )
            
            # Step 2.5: Apply additional filters from request data
            if "include_company_name" in request.data:
                filter_dict["include_company_name"] = request.data["include_company_name"]
            if "exclude_company_name" in request.data:
                filter_dict["exclude_company_name"] = request.data["exclude_company_name"]
            if "include_domain_list" in request.data:
                normalized = _normalize_list_query_param(request.data["include_domain_list"])
                if normalized is not None:
                    filter_dict["include_domain_list"] = normalized
            if "exclude_domain_list" in request.data:
                normalized = _normalize_list_query_param(request.data["exclude_domain_list"])
                if normalized is not None:
                    filter_dict["exclude_domain_list"] = normalized
            
            # Step 3: Validate and construct ContactFilterParams
            try:
                filters = ContactFilterParams.model_validate(filter_dict)
            except ValidationError as exc:
                await _send_error_response(
                    websocket,
                    request.request_id,
                    request.action,
                    f"Invalid filter parameters: {exc.errors()[0].get('msg', 'Validation error')}",
                    "validation_error",
                )
                return
            
            # Step 4: Count contacts
            count = await contacts_service.count_contacts(session, filters)
            
            # Build response data
            response_data = {"count": count}
            
            await _send_success_response(websocket, request.request_id, request.action, response_data)
    
    except Exception as exc:
        logger.exception("Error counting contacts via WebSocket: %s", exc)
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            f"An error occurred while counting contacts: {str(exc)}",
            "count_error",
        )


async def _handle_get_uuids_action(websocket: WebSocket, request: ApolloWebSocketRequest) -> None:
    """Handle the get_uuids action."""
    if "url" not in request.data:
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            "Missing required field: url",
            "missing_field",
        )
        return
    
    try:
        async with AsyncSessionLocal() as session:
            # Step 1: Analyze the Apollo URL
            analysis = await service.analyze_url(request.data["url"])
            
            # Step 2: Map Apollo parameters to contact filter parameters
            filter_dict, unmapped_dict = service.map_to_contact_filters(
                analysis.raw_parameters, include_unmapped=True
            )
            
            # Step 2.5: Apply additional filters from request data
            if "include_company_name" in request.data:
                filter_dict["include_company_name"] = request.data["include_company_name"]
            if "exclude_company_name" in request.data:
                filter_dict["exclude_company_name"] = request.data["exclude_company_name"]
            if "include_domain_list" in request.data:
                normalized = _normalize_list_query_param(request.data["include_domain_list"])
                if normalized is not None:
                    filter_dict["include_domain_list"] = normalized
            if "exclude_domain_list" in request.data:
                normalized = _normalize_list_query_param(request.data["exclude_domain_list"])
                if normalized is not None:
                    filter_dict["exclude_domain_list"] = normalized
            
            # Step 3: Validate and construct ContactFilterParams
            try:
                filters = ContactFilterParams.model_validate(filter_dict)
            except ValidationError as exc:
                await _send_error_response(
                    websocket,
                    request.request_id,
                    request.action,
                    f"Invalid filter parameters: {exc.errors()[0].get('msg', 'Validation error')}",
                    "validation_error",
                )
                return
            
            # Step 4: Get contact UUIDs
            limit = request.data.get("limit")
            uuids = await contacts_service.get_uuids_by_filters(session, filters, limit)
            
            # Build response data
            response_data = {"count": len(uuids), "uuids": uuids}
            
            await _send_success_response(websocket, request.request_id, request.action, response_data)
    
    except Exception as exc:
        logger.exception("Error getting contact UUIDs via WebSocket: %s", exc)
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            f"An error occurred while getting contact UUIDs: {str(exc)}",
            "uuids_error",
        )


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):
    """
    Unified WebSocket endpoint for all Apollo operations.
    
    This endpoint accepts messages with different actions:
    - "analyze": Analyze Apollo.io URLs
    - "search_contacts": Search contacts using Apollo URL parameters
    - "count_contacts": Count contacts matching Apollo URL parameters
    - "get_uuids": Get contact UUIDs matching Apollo URL parameters
    
    All actions are handled over a single persistent WebSocket connection.
    """
    user = None
    try:
        # Authenticate user
        user = await get_current_user_websocket(websocket, token)
        await connection_manager.connect(websocket, user)
        
        while True:
            # Receive message
            text = await websocket.receive_text()
            request = await _parse_websocket_message(websocket, text)
            
            if not request:
                continue
            
            # Route to appropriate handler based on action
            if request.action == "analyze":
                await _handle_analyze_action(websocket, request)
            elif request.action == "search_contacts":
                await _handle_search_contacts_action(websocket, request)
            elif request.action == "count_contacts":
                await _handle_count_contacts_action(websocket, request)
            elif request.action == "get_uuids":
                await _handle_get_uuids_action(websocket, request)
            else:
                await _send_error_response(
                    websocket,
                    request.request_id,
                    request.action,
                    f"Unknown action: {request.action}. Supported actions: analyze, search_contacts, count_contacts, get_uuids",
                    "unknown_action",
                )
    
    except WebSocketDisconnect:
        if user:
            connection_manager.disconnect(str(user.id))
            logger.info("WebSocket disconnected: user_id=%s", user.id)
    except Exception as exc:
        logger.exception("WebSocket error in unified endpoint: %s", exc)
        if user:
            connection_manager.disconnect(str(user.id))


@router.websocket("/analyze")
async def websocket_analyze_apollo_url(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):
    """
    WebSocket endpoint for analyzing Apollo.io URLs.
    
    Accepts JSON messages with action="analyze" and returns structured parameter breakdown.
    """
    try:
        # Authenticate user
        user = await get_current_user_websocket(websocket, token)
        await connection_manager.connect(websocket, user)
        
        while True:
            # Receive message
            text = await websocket.receive_text()
            request = await _parse_websocket_message(websocket, text)
            
            if not request:
                continue
            
            if request.action != "analyze":
                await _send_error_response(
                    websocket,
                    request.request_id,
                    request.action,
                    f"Invalid action for this endpoint. Expected 'analyze', got '{request.action}'",
                    "invalid_action",
                )
                continue
            
            # Validate request data
            if "url" not in request.data:
                await _send_error_response(
                    websocket,
                    request.request_id,
                    request.action,
                    "Missing required field: url",
                    "missing_field",
                )
                continue
            
            try:
                # Analyze the URL
                result = await service.analyze_url(request.data["url"])
                
                # Convert Tag IDs to industry names
                converted_categories = []
                converted_raw_parameters = {}
                
                for category in result.categories:
                    converted_params = []
                    for param in category.parameters:
                        converted_values = _convert_industry_tagids_to_names(param.name, param.values)
                        converted_params.append(
                            ParameterDetail(
                                name=param.name,
                                values=converted_values,
                                description=param.description,
                                category=param.category,
                            )
                        )
                    converted_categories.append(
                        ParameterCategory(
                            name=category.name,
                            parameters=converted_params,
                            total_parameters=category.total_parameters,
                        )
                    )
                
                for param_name, param_values in result.raw_parameters.items():
                    converted_raw_parameters[param_name] = _convert_industry_tagids_to_names(
                        param_name, param_values
                    )
                
                # Build response data
                response_data = {
                    "url": result.url,
                    # Use mode='json' to serialize datetime objects to ISO format strings
                    "url_structure": result.url_structure.model_dump(mode='json'),
                    "categories": [cat.model_dump(mode='json') for cat in converted_categories],
                    "statistics": result.statistics.model_dump(mode='json'),
                    "raw_parameters": converted_raw_parameters,
                }
                
                await _send_success_response(websocket, request.request_id, request.action, response_data)
                
            except Exception as exc:
                logger.exception("Error analyzing Apollo URL via WebSocket: %s", exc)
                await _send_error_response(
                    websocket,
                    request.request_id,
                    request.action,
                    f"An error occurred while analyzing the URL: {str(exc)}",
                    "analysis_error",
                )
    
    except WebSocketDisconnect:
        connection_manager.disconnect(str(user.id))
        logger.info("WebSocket disconnected: user_id=%s", user.id)
    except Exception as exc:
        logger.exception("WebSocket error in analyze endpoint: %s", exc)
        if "user" in locals():
            connection_manager.disconnect(str(user.id))


@router.websocket("/contacts")
async def websocket_search_contacts_from_apollo_url(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):
    """
    WebSocket endpoint for searching contacts using Apollo.io URL parameters.
    
    Accepts JSON messages with action="search_contacts" and returns matching contacts.
    """
    try:
        # Authenticate user
        user = await get_current_user_websocket(websocket, token)
        await connection_manager.connect(websocket, user)
        
        while True:
            # Receive message
            text = await websocket.receive_text()
            request = await _parse_websocket_message(websocket, text)
            
            if not request:
                continue
            
            if request.action != "search_contacts":
                await _send_error_response(
                    websocket,
                    request.request_id,
                    request.action,
                    f"Invalid action for this endpoint. Expected 'search_contacts', got '{request.action}'",
                    "invalid_action",
                )
                continue
            
            # Validate request data
            if "url" not in request.data:
                await _send_error_response(
                    websocket,
                    request.request_id,
                    request.action,
                    "Missing required field: url",
                    "missing_field",
                )
                continue
            
            try:
                async with AsyncSessionLocal() as session:
                    # Step 1: Analyze the Apollo URL
                    analysis = await service.analyze_url(request.data["url"])
                    
                    # Step 2: Map Apollo parameters to contact filter parameters
                    filter_dict, unmapped_dict = service.map_to_contact_filters(
                        analysis.raw_parameters, include_unmapped=True
                    )
                    
                    # Step 2.5: Apply additional filters from request data
                    if "include_company_name" in request.data:
                        filter_dict["include_company_name"] = request.data["include_company_name"]
                    if "exclude_company_name" in request.data:
                        filter_dict["exclude_company_name"] = request.data["exclude_company_name"]
                    if "include_domain_list" in request.data:
                        normalized = _normalize_list_query_param(request.data["include_domain_list"])
                        if normalized is not None:
                            filter_dict["include_domain_list"] = normalized
                    if "exclude_domain_list" in request.data:
                        normalized = _normalize_list_query_param(request.data["exclude_domain_list"])
                        if normalized is not None:
                            filter_dict["exclude_domain_list"] = normalized
                    
                    # Step 3: Validate and construct ContactFilterParams
                    try:
                        filters = ContactFilterParams.model_validate(filter_dict)
                    except ValidationError as exc:
                        await _send_error_response(
                            websocket,
                            request.request_id,
                            request.action,
                            f"Invalid filter parameters: {exc.errors()[0].get('msg', 'Validation error')}",
                            "validation_error",
                        )
                        continue
                    
                    # Step 4: Determine pagination settings
                    limit = request.data.get("limit")
                    page_limit = _resolve_pagination(filters, limit)
                    
                    offset = request.data.get("offset", 0)
                    cursor = request.data.get("cursor")
                    view = request.data.get("view")
                    
                    use_cursor = False
                    resolved_offset = offset
                    cursor_token = cursor or filters.cursor
                    
                    if cursor_token:
                        try:
                            resolved_offset = decode_offset_cursor(cursor_token)
                        except ValueError as exc:
                            await _send_error_response(
                                websocket,
                                request.request_id,
                                request.action,
                                f"Invalid cursor token: {str(exc)}",
                                "invalid_cursor",
                            )
                            continue
                        use_cursor = True
                    elif offset == 0 and filters.page is not None and page_limit is not None:
                        resolved_offset = (filters.page - 1) * page_limit
                    
                    # Step 5: Query contacts
                    if (view or "").strip().lower() == "simple":
                        page = await contacts_service.list_contacts_simple(
                            session,
                            filters,
                            limit=page_limit,
                            offset=resolved_offset,
                            request_url="",  # Not needed for WebSocket
                            use_cursor=use_cursor,
                        )
                    else:
                        page = await contacts_service.list_contacts(
                            session,
                            filters,
                            limit=page_limit,
                            offset=resolved_offset,
                            request_url="",  # Not needed for WebSocket
                            use_cursor=use_cursor,
                        )
                    
                    # Step 6: Build unmapped categories structure
                    unmapped_categories = []
                    category_unmapped_map = {}
                    
                    for param_name, (param_values, reason) in unmapped_dict.items():
                        param_category = "Other"
                        for category in analysis.categories:
                            for param in category.parameters:
                                if param.name == param_name:
                                    param_category = category.name
                                    break
                        
                        if param_category not in category_unmapped_map:
                            category_unmapped_map[param_category] = []
                        
                        converted_values = _convert_industry_tagids_to_names(param_name, param_values)
                        
                        category_unmapped_map[param_category].append(
                            UnmappedParameter(
                                name=param_name,
                                values=converted_values,
                                category=param_category,
                                reason=reason,
                            )
                        )
                    
                    for category_name, params in category_unmapped_map.items():
                        unmapped_categories.append(
                            UnmappedCategory(
                                name=category_name,
                                parameters=params,
                                total_parameters=len(params),
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
                        unmapped_parameter_names=unmapped_param_names,
                    )
                    
                    # Step 8: Build response data
                    response_data = {
                        "next": page.next,
                        "previous": page.previous,
                        # Use mode='json' to serialize datetime objects to ISO format strings
                        "results": [item.model_dump(mode='json') for item in page.results],
                        "apollo_url": request.data["url"],
                        "mapping_summary": mapping_summary.model_dump(mode='json'),
                        "unmapped_categories": [cat.model_dump(mode='json') for cat in unmapped_categories],
                    }
                    
                    await _send_success_response(websocket, request.request_id, request.action, response_data)
            
            except Exception as exc:
                logger.exception("Error searching contacts via WebSocket: %s", exc)
                await _send_error_response(
                    websocket,
                    request.request_id,
                    request.action,
                    f"An error occurred while searching contacts: {str(exc)}",
                    "search_error",
                )
    
    except WebSocketDisconnect:
        connection_manager.disconnect(str(user.id))
        logger.info("WebSocket disconnected: user_id=%s", user.id)
    except Exception as exc:
        logger.exception("WebSocket error in contacts endpoint: %s", exc)
        if "user" in locals():
            connection_manager.disconnect(str(user.id))


@router.websocket("/contacts/count")
async def websocket_count_contacts_from_apollo_url(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):
    """
    WebSocket endpoint for counting contacts matching Apollo.io URL parameters.
    
    Accepts JSON messages with action="count_contacts" and returns total count.
    """
    try:
        # Authenticate user
        user = await get_current_user_websocket(websocket, token)
        await connection_manager.connect(websocket, user)
        
        while True:
            # Receive message
            text = await websocket.receive_text()
            request = await _parse_websocket_message(websocket, text)
            
            if not request:
                continue
            
            if request.action != "count_contacts":
                await _send_error_response(
                    websocket,
                    request.request_id,
                    request.action,
                    f"Invalid action for this endpoint. Expected 'count_contacts', got '{request.action}'",
                    "invalid_action",
                )
                continue
            
            # Validate request data
            if "url" not in request.data:
                await _send_error_response(
                    websocket,
                    request.request_id,
                    request.action,
                    "Missing required field: url",
                    "missing_field",
                )
                continue
            
            try:
                async with AsyncSessionLocal() as session:
                    # Step 1: Analyze the Apollo URL
                    analysis = await service.analyze_url(request.data["url"])
                    
                    # Step 2: Map Apollo parameters to contact filter parameters
                    filter_dict, unmapped_dict = service.map_to_contact_filters(
                        analysis.raw_parameters, include_unmapped=True
                    )
                    
                    # Step 2.5: Apply additional filters from request data
                    if "include_company_name" in request.data:
                        filter_dict["include_company_name"] = request.data["include_company_name"]
                    if "exclude_company_name" in request.data:
                        filter_dict["exclude_company_name"] = request.data["exclude_company_name"]
                    if "include_domain_list" in request.data:
                        normalized = _normalize_list_query_param(request.data["include_domain_list"])
                        if normalized is not None:
                            filter_dict["include_domain_list"] = normalized
                    if "exclude_domain_list" in request.data:
                        normalized = _normalize_list_query_param(request.data["exclude_domain_list"])
                        if normalized is not None:
                            filter_dict["exclude_domain_list"] = normalized
                    
                    # Step 3: Validate and construct ContactFilterParams
                    try:
                        filters = ContactFilterParams.model_validate(filter_dict)
                    except ValidationError as exc:
                        await _send_error_response(
                            websocket,
                            request.request_id,
                            request.action,
                            f"Invalid filter parameters: {exc.errors()[0].get('msg', 'Validation error')}",
                            "validation_error",
                        )
                        continue
                    
                    # Step 4: Count contacts
                    count_response = await contacts_service.count_contacts(session, filters)
                    
                    # Build response data
                    response_data = {"count": count_response.count}
                    
                    await _send_success_response(websocket, request.request_id, request.action, response_data)
            
            except Exception as exc:
                logger.exception("Error counting contacts via WebSocket: %s", exc)
                await _send_error_response(
                    websocket,
                    request.request_id,
                    request.action,
                    f"An error occurred while counting contacts: {str(exc)}",
                    "count_error",
                )
    
    except WebSocketDisconnect:
        connection_manager.disconnect(str(user.id))
        logger.info("WebSocket disconnected: user_id=%s", user.id)
    except Exception as exc:
        logger.exception("WebSocket error in count endpoint: %s", exc)
        if "user" in locals():
            connection_manager.disconnect(str(user.id))


@router.websocket("/contacts/count/uuids")
async def websocket_get_contact_uuids_from_apollo_url(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):
    """
    WebSocket endpoint for getting contact UUIDs matching Apollo.io URL parameters.
    
    Accepts JSON messages with action="get_uuids" and returns list of UUIDs.
    """
    try:
        # Authenticate user
        user = await get_current_user_websocket(websocket, token)
        await connection_manager.connect(websocket, user)
        
        while True:
            # Receive message
            text = await websocket.receive_text()
            request = await _parse_websocket_message(websocket, text)
            
            if not request:
                continue
            
            if request.action != "get_uuids":
                await _send_error_response(
                    websocket,
                    request.request_id,
                    request.action,
                    f"Invalid action for this endpoint. Expected 'get_uuids', got '{request.action}'",
                    "invalid_action",
                )
                continue
            
            # Validate request data
            if "url" not in request.data:
                await _send_error_response(
                    websocket,
                    request.request_id,
                    request.action,
                    "Missing required field: url",
                    "missing_field",
                )
                continue
            
            try:
                async with AsyncSessionLocal() as session:
                    # Step 1: Analyze the Apollo URL
                    analysis = await service.analyze_url(request.data["url"])
                    
                    # Step 2: Map Apollo parameters to contact filter parameters
                    filter_dict, unmapped_dict = service.map_to_contact_filters(
                        analysis.raw_parameters, include_unmapped=True
                    )
                    
                    # Step 2.5: Apply additional filters from request data
                    if "include_company_name" in request.data:
                        filter_dict["include_company_name"] = request.data["include_company_name"]
                    if "exclude_company_name" in request.data:
                        filter_dict["exclude_company_name"] = request.data["exclude_company_name"]
                    if "include_domain_list" in request.data:
                        normalized = _normalize_list_query_param(request.data["include_domain_list"])
                        if normalized is not None:
                            filter_dict["include_domain_list"] = normalized
                    if "exclude_domain_list" in request.data:
                        normalized = _normalize_list_query_param(request.data["exclude_domain_list"])
                        if normalized is not None:
                            filter_dict["exclude_domain_list"] = normalized
                    
                    # Step 3: Validate and construct ContactFilterParams
                    try:
                        filters = ContactFilterParams.model_validate(filter_dict)
                    except ValidationError as exc:
                        await _send_error_response(
                            websocket,
                            request.request_id,
                            request.action,
                            f"Invalid filter parameters: {exc.errors()[0].get('msg', 'Validation error')}",
                            "validation_error",
                        )
                        continue
                    
                    # Step 4: Get contact UUIDs
                    limit = request.data.get("limit")
                    uuids = await contacts_service.get_uuids_by_filters(session, filters, limit)
                    
                    # Build response data
                    response_data = {"count": len(uuids), "uuids": uuids}
                    
                    await _send_success_response(websocket, request.request_id, request.action, response_data)
            
            except Exception as exc:
                logger.exception("Error getting contact UUIDs via WebSocket: %s", exc)
                await _send_error_response(
                    websocket,
                    request.request_id,
                    request.action,
                    f"An error occurred while getting contact UUIDs: {str(exc)}",
                    "uuids_error",
                )
    
    except WebSocketDisconnect:
        connection_manager.disconnect(str(user.id))
        logger.info("WebSocket disconnected: user_id=%s", user.id)
    except Exception as exc:
        logger.exception("WebSocket error in UUIDs endpoint: %s", exc)
        if "user" in locals():
            connection_manager.disconnect(str(user.id))

