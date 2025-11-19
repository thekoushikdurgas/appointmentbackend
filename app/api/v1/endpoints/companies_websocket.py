"""WebSocket endpoints for company operations."""

import json
from typing import Any, Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_websocket
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.companies import Company, CompanyMetadata
from app.models.user import User
from app.repositories.user import UserProfileRepository
from app.schemas.companies import (
    CompanyCreate,
    CompanyDetail,
    CompanyListItem,
    CompanyUpdate,
    CompanyWebSocketRequest,
    CompanyWebSocketResponse,
)
from app.schemas.common import CountResponse, CursorPage, UuidListResponse
from app.schemas.filters import AttributeListParams, CompanyContactFilterParams, CompanyFilterParams
from app.services.companies_service import CompaniesService
from app.services.contacts_service import ContactsService
from app.utils.cursor import decode_offset_cursor

router = APIRouter(prefix="/companies", tags=["Companies WebSocket"])
logger = get_logger(__name__)
settings = get_settings()
companies_service = CompaniesService()
contacts_service = ContactsService()


class CompanyWebSocketManager:
    """Manages WebSocket connections for company endpoints."""

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
connection_manager = CompanyWebSocketManager()


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
    response = CompanyWebSocketResponse(
        request_id=request_id,
        action=action,
        status="error",
        data=None,
        error={"message": error_message, "code": error_code},
    )
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
    response = CompanyWebSocketResponse(
        request_id=request_id,
        action=action,
        status="success",
        data=data,
        error=None,
    )
    await connection_manager.send_message(websocket, response.model_dump(mode='json'))


async def _parse_websocket_message(websocket: WebSocket, text: str) -> Optional[CompanyWebSocketRequest]:
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
        request = CompanyWebSocketRequest.model_validate(data)
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


def _resolve_pagination(filters: CompanyFilterParams, limit: Optional[int]) -> Optional[int]:
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


def _parse_iterable_like(value: Any) -> list[str]:
    """Best effort parsing for list-like attribute payloads."""
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item or "").strip()]

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        # JSON encoded arrays
        if stripped.startswith("[") and stripped.endswith("]"):
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item or "").strip()]
            except json.JSONDecodeError:
                pass
        # PostgreSQL array string representation
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


def _normalize_array_values(values: list[Any]) -> list[str]:
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


async def _check_write_permission(websocket: WebSocket, request: CompanyWebSocketRequest, user: User) -> bool:
    """Check if user has permission to perform write operations."""
    try:
        # Check if user is admin
        async with AsyncSessionLocal() as session:
            profile_repo = UserProfileRepository()
            profile = await profile_repo.get_by_user_id(session, user.id)
            user_role = profile.role if profile and profile.role else "Member"
            
            if user_role != "Admin":
                await _send_error_response(
                    websocket,
                    request.request_id,
                    request.action,
                    "You do not have permission to perform this action. Admin role required.",
                    "forbidden",
                )
                return False
        
        # Check write key if provided in data
        write_key = request.data.get("write_key") or request.data.get("X-Companies-Write-Key")
        configured_key = (settings.COMPANIES_WRITE_KEY or "").strip()
        
        if not configured_key:
            await _send_error_response(
                websocket,
                request.request_id,
                request.action,
                "Companies write key is not configured",
                "forbidden",
            )
            return False
        
        if write_key != configured_key:
            await _send_error_response(
                websocket,
                request.request_id,
                request.action,
                "Forbidden",
                "forbidden",
            )
            return False
        
        return True
    except Exception as exc:
        logger.exception("Error checking write permission: %s", exc)
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            "You do not have permission to perform this action. Admin role required.",
            "forbidden",
        )
        return False


# ============================================================================
# Main Company Operation Handlers (7 actions)
# ============================================================================

async def _handle_list_companies(websocket: WebSocket, request: CompanyWebSocketRequest, user: User) -> None:
    """Handle list_companies action."""
    try:
        async with AsyncSessionLocal() as session:
            # Build filters from request data
            filter_data = request.data.copy()
            multi_value_keys = (
                "exclude_industries",
                "exclude_keywords",
                "exclude_technologies",
                "exclude_locations",
            )
            for key in multi_value_keys:
                if key in filter_data and isinstance(filter_data[key], str):
                    filter_data[key] = [v.strip() for v in filter_data[key].split(",") if v.strip()]
            
            filters = CompanyFilterParams.model_validate(filter_data)
            
            # Resolve pagination
            limit = request.data.get("limit")
            offset = request.data.get("offset", 0)
            cursor = request.data.get("cursor")
            page_limit = _resolve_pagination(filters, limit)
            
            use_cursor = False
            resolved_offset = offset
            if cursor:
                try:
                    resolved_offset = decode_offset_cursor(cursor)
                    use_cursor = True
                except ValueError as exc:
                    await _send_error_response(
                        websocket,
                        request.request_id,
                        request.action,
                        f"Invalid cursor value: {str(exc)}",
                        "invalid_cursor",
                    )
                    return
            elif offset == 0 and filters.page is not None and page_limit is not None:
                resolved_offset = (filters.page - 1) * page_limit
            
            # Build request URL for pagination links
            request_url = request.data.get("request_url", "http://localhost:8000/api/v1/companies/")
            
            page = await companies_service.list_companies(
                session,
                filters,
                limit=page_limit,
                offset=resolved_offset,
                request_url=request_url,
                use_cursor=use_cursor,
            )
            
            response_data = page.model_dump(mode='json')
            await _send_success_response(websocket, request.request_id, request.action, response_data)
    
    except ValidationError as exc:
        first_error = exc.errors()[0] if exc.errors() else {}
        message = first_error.get("msg", "Invalid query parameters")
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            message,
            "validation_error",
        )
    except Exception as exc:
        logger.exception("Error listing companies via WebSocket: %s", exc)
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            f"An error occurred while listing companies: {str(exc)}",
            "list_error",
        )


async def _handle_get_company(websocket: WebSocket, request: CompanyWebSocketRequest, user: User) -> None:
    """Handle get_company action."""
    if "company_uuid" not in request.data:
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            "Missing required field: company_uuid",
            "missing_field",
        )
        return
    
    try:
        async with AsyncSessionLocal() as session:
            company_uuid = request.data["company_uuid"]
            company = await companies_service.get_company_by_uuid(session, company_uuid)
            
            if not company:
                await _send_error_response(
                    websocket,
                    request.request_id,
                    request.action,
                    "Not found.",
                    "not_found",
                )
                return
            
            response_data = company.model_dump(mode='json')
            await _send_success_response(websocket, request.request_id, request.action, response_data)
    
    except Exception as exc:
        logger.exception("Error getting company via WebSocket: %s", exc)
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            f"An error occurred while getting company: {str(exc)}",
            "get_error",
        )


async def _handle_count_companies(websocket: WebSocket, request: CompanyWebSocketRequest, user: User) -> None:
    """Handle count_companies action."""
    try:
        async with AsyncSessionLocal() as session:
            # Build filters from request data
            filter_data = request.data.copy()
            multi_value_keys = (
                "exclude_industries",
                "exclude_keywords",
                "exclude_technologies",
                "exclude_locations",
            )
            for key in multi_value_keys:
                if key in filter_data and isinstance(filter_data[key], str):
                    filter_data[key] = [v.strip() for v in filter_data[key].split(",") if v.strip()]
            
            filters = CompanyFilterParams.model_validate(filter_data)
            count = await companies_service.count_companies(session, filters)
            
            response_data = count.model_dump(mode='json')
            await _send_success_response(websocket, request.request_id, request.action, response_data)
    
    except ValidationError as exc:
        first_error = exc.errors()[0] if exc.errors() else {}
        message = first_error.get("msg", "Invalid query parameters")
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            message,
            "validation_error",
        )
    except Exception as exc:
        logger.exception("Error counting companies via WebSocket: %s", exc)
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            f"An error occurred while counting companies: {str(exc)}",
            "count_error",
        )


async def _handle_get_company_uuids(websocket: WebSocket, request: CompanyWebSocketRequest, user: User) -> None:
    """Handle get_company_uuids action."""
    try:
        async with AsyncSessionLocal() as session:
            # Build filters from request data
            filter_data = request.data.copy()
            multi_value_keys = (
                "exclude_industries",
                "exclude_keywords",
                "exclude_technologies",
                "exclude_locations",
            )
            for key in multi_value_keys:
                if key in filter_data and isinstance(filter_data[key], str):
                    filter_data[key] = [v.strip() for v in filter_data[key].split(",") if v.strip()]
            
            filters = CompanyFilterParams.model_validate(filter_data)
            limit = request.data.get("limit")
            
            uuids = await companies_service.get_uuids_by_filters(session, filters, limit)
            
            response_data = UuidListResponse(count=len(uuids), uuids=uuids).model_dump(mode='json')
            await _send_success_response(websocket, request.request_id, request.action, response_data)
    
    except ValidationError as exc:
        first_error = exc.errors()[0] if exc.errors() else {}
        message = first_error.get("msg", "Invalid query parameters")
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            message,
            "validation_error",
        )
    except Exception as exc:
        logger.exception("Error getting company UUIDs via WebSocket: %s", exc)
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            f"An error occurred while getting company UUIDs: {str(exc)}",
            "uuids_error",
        )


async def _handle_create_company(websocket: WebSocket, request: CompanyWebSocketRequest, user: User) -> None:
    """Handle create_company action."""
    # Check write permission
    if not await _check_write_permission(websocket, request, user):
        return
    
    try:
        async with AsyncSessionLocal() as session:
            payload = CompanyCreate.model_validate(request.data)
            company = await companies_service.create_company(session, payload)
            await session.commit()
            
            response_data = company.model_dump(mode='json')
            await _send_success_response(websocket, request.request_id, request.action, response_data)
    
    except ValidationError as exc:
        first_error = exc.errors()[0] if exc.errors() else {}
        message = first_error.get("msg", "Invalid request data")
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            message,
            "validation_error",
        )
    except Exception as exc:
        logger.exception("Error creating company via WebSocket: %s", exc)
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            f"An error occurred while creating company: {str(exc)}",
            "create_error",
        )


async def _handle_update_company(websocket: WebSocket, request: CompanyWebSocketRequest, user: User) -> None:
    """Handle update_company action."""
    if "company_uuid" not in request.data:
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            "Missing required field: company_uuid",
            "missing_field",
        )
        return
    
    # Check write permission
    if not await _check_write_permission(websocket, request, user):
        return
    
    try:
        async with AsyncSessionLocal() as session:
            company_uuid = request.data["company_uuid"]
            payload = CompanyUpdate.model_validate(request.data)
            company = await companies_service.update_company(session, company_uuid, payload)
            await session.commit()
            
            if not company:
                await _send_error_response(
                    websocket,
                    request.request_id,
                    request.action,
                    "Not found.",
                    "not_found",
                )
                return
            
            response_data = company.model_dump(mode='json')
            await _send_success_response(websocket, request.request_id, request.action, response_data)
    
    except ValidationError as exc:
        first_error = exc.errors()[0] if exc.errors() else {}
        message = first_error.get("msg", "Invalid request data")
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            message,
            "validation_error",
        )
    except Exception as exc:
        logger.exception("Error updating company via WebSocket: %s", exc)
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            f"An error occurred while updating company: {str(exc)}",
            "update_error",
        )


async def _handle_delete_company(websocket: WebSocket, request: CompanyWebSocketRequest, user: User) -> None:
    """Handle delete_company action."""
    if "company_uuid" not in request.data:
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            "Missing required field: company_uuid",
            "missing_field",
        )
        return
    
    # Check write permission
    if not await _check_write_permission(websocket, request, user):
        return
    
    try:
        async with AsyncSessionLocal() as session:
            company_uuid = request.data["company_uuid"]
            await companies_service.delete_company(session, company_uuid)
            await session.commit()
            
            # Return empty response for delete (204 No Content equivalent)
            await _send_success_response(websocket, request.request_id, request.action, {})
    
    except Exception as exc:
        logger.exception("Error deleting company via WebSocket: %s", exc)
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            f"An error occurred while deleting company: {str(exc)}",
            "delete_error",
        )


# ============================================================================
# Company Attribute Lookup Handlers (8 actions)
# ============================================================================

async def _handle_list_company_names(websocket: WebSocket, request: CompanyWebSocketRequest, user: User) -> None:
    """Handle list_company_names action."""
    try:
        async with AsyncSessionLocal() as session:
            filter_data = request.data.copy()
            multi_value_keys = (
                "exclude_industries",
                "exclude_keywords",
                "exclude_technologies",
                "exclude_locations",
            )
            for key in multi_value_keys:
                if key in filter_data and isinstance(filter_data[key], str):
                    filter_data[key] = [v.strip() for v in filter_data[key].split(",") if v.strip()]
            
            filters = CompanyFilterParams.model_validate(filter_data)
            params = AttributeListParams.model_validate(request.data)
            
            values = await companies_service.list_attribute_values(
                session,
                filters,
                params,
                column_factory=lambda Company, CompanyMetadata: Company.name,
                array_mode=False,
            )
            
            response_data = {"results": values}
            await _send_success_response(websocket, request.request_id, request.action, response_data)
    
    except ValidationError as exc:
        first_error = exc.errors()[0] if exc.errors() else {}
        message = first_error.get("msg", "Invalid query parameters")
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            message,
            "validation_error",
        )
    except Exception as exc:
        logger.exception("Error listing company names via WebSocket: %s", exc)
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            f"An error occurred while listing company names: {str(exc)}",
            "list_error",
        )


async def _handle_list_industries(websocket: WebSocket, request: CompanyWebSocketRequest, user: User) -> None:
    """Handle list_industries action."""
    try:
        async with AsyncSessionLocal() as session:
            filter_data = request.data.copy()
            multi_value_keys = (
                "exclude_industries",
                "exclude_keywords",
                "exclude_technologies",
                "exclude_locations",
            )
            for key in multi_value_keys:
                if key in filter_data and isinstance(filter_data[key], str):
                    filter_data[key] = [v.strip() for v in filter_data[key].split(",") if v.strip()]
            
            filters = CompanyFilterParams.model_validate(filter_data)
            params = AttributeListParams.model_validate(request.data)
            separated = request.data.get("separated", False)
            
            column_factory = (
                (lambda Company, CompanyMetadata: Company.industries)
                if separated
                else (lambda Company, CompanyMetadata: func.array_to_string(Company.industries, ","))
            )
            
            values = await companies_service.list_attribute_values(
                session,
                filters,
                params,
                column_factory=column_factory,
                array_mode=separated,
            )
            
            if separated:
                deduped = _normalize_array_values(values)
                if params.limit:
                    deduped = deduped[: params.limit]
                response_data = {"results": deduped}
            else:
                filtered = [value for value in values if value]
                response_data = {"results": filtered}
            
            await _send_success_response(websocket, request.request_id, request.action, response_data)
    
    except ValidationError as exc:
        first_error = exc.errors()[0] if exc.errors() else {}
        message = first_error.get("msg", "Invalid query parameters")
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            message,
            "validation_error",
        )
    except Exception as exc:
        logger.exception("Error listing industries via WebSocket: %s", exc)
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            f"An error occurred while listing industries: {str(exc)}",
            "list_error",
        )


async def _handle_list_keywords(websocket: WebSocket, request: CompanyWebSocketRequest, user: User) -> None:
    """Handle list_keywords action."""
    try:
        async with AsyncSessionLocal() as session:
            filter_data = request.data.copy()
            multi_value_keys = (
                "exclude_industries",
                "exclude_keywords",
                "exclude_technologies",
                "exclude_locations",
            )
            for key in multi_value_keys:
                if key in filter_data and isinstance(filter_data[key], str):
                    filter_data[key] = [v.strip() for v in filter_data[key].split(",") if v.strip()]
            
            filters = CompanyFilterParams.model_validate(filter_data)
            params = AttributeListParams.model_validate(request.data)
            separated = request.data.get("separated", False)
            
            column_factory = (
                (lambda Company, CompanyMetadata: Company.keywords)
                if separated
                else (lambda Company, CompanyMetadata: func.array_to_string(Company.keywords, ","))
            )
            
            values = await companies_service.list_attribute_values(
                session,
                filters,
                params,
                column_factory=column_factory,
                array_mode=separated,
            )
            
            if separated:
                deduped = _normalize_array_values(values)
                if params.limit:
                    deduped = deduped[: params.limit]
                response_data = {"results": deduped}
            else:
                filtered = [value for value in values if value]
                response_data = {"results": filtered}
            
            await _send_success_response(websocket, request.request_id, request.action, response_data)
    
    except ValidationError as exc:
        first_error = exc.errors()[0] if exc.errors() else {}
        message = first_error.get("msg", "Invalid query parameters")
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            message,
            "validation_error",
        )
    except Exception as exc:
        logger.exception("Error listing keywords via WebSocket: %s", exc)
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            f"An error occurred while listing keywords: {str(exc)}",
            "list_error",
        )


async def _handle_list_technologies(websocket: WebSocket, request: CompanyWebSocketRequest, user: User) -> None:
    """Handle list_technologies action."""
    try:
        async with AsyncSessionLocal() as session:
            filter_data = request.data.copy()
            multi_value_keys = (
                "exclude_industries",
                "exclude_keywords",
                "exclude_technologies",
                "exclude_locations",
            )
            for key in multi_value_keys:
                if key in filter_data and isinstance(filter_data[key], str):
                    filter_data[key] = [v.strip() for v in filter_data[key].split(",") if v.strip()]
            
            filters = CompanyFilterParams.model_validate(filter_data)
            params = AttributeListParams.model_validate(request.data)
            separated = request.data.get("separated", False)
            
            column_factory = (
                (lambda Company, CompanyMetadata: Company.technologies)
                if separated
                else (lambda Company, CompanyMetadata: func.array_to_string(Company.technologies, ","))
            )
            
            values = await companies_service.list_attribute_values(
                session,
                filters,
                params,
                column_factory=column_factory,
                array_mode=separated,
            )
            
            if separated:
                deduped = _normalize_array_values(values)
                if params.limit:
                    deduped = deduped[: params.limit]
                response_data = {"results": deduped}
            else:
                filtered = [value for value in values if value]
                response_data = {"results": filtered}
            
            await _send_success_response(websocket, request.request_id, request.action, response_data)
    
    except ValidationError as exc:
        first_error = exc.errors()[0] if exc.errors() else {}
        message = first_error.get("msg", "Invalid query parameters")
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            message,
            "validation_error",
        )
    except Exception as exc:
        logger.exception("Error listing technologies via WebSocket: %s", exc)
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            f"An error occurred while listing technologies: {str(exc)}",
            "list_error",
        )


async def _handle_list_company_cities(websocket: WebSocket, request: CompanyWebSocketRequest, user: User) -> None:
    """Handle list_company_cities action."""
    try:
        async with AsyncSessionLocal() as session:
            filter_data = request.data.copy()
            multi_value_keys = (
                "exclude_industries",
                "exclude_keywords",
                "exclude_technologies",
                "exclude_locations",
            )
            for key in multi_value_keys:
                if key in filter_data and isinstance(filter_data[key], str):
                    filter_data[key] = [v.strip() for v in filter_data[key].split(",") if v.strip()]
            
            filters = CompanyFilterParams.model_validate(filter_data)
            params = AttributeListParams.model_validate(request.data)
            
            values = await companies_service.list_attribute_values(
                session,
                filters,
                params,
                column_factory=lambda Company, CompanyMetadata: CompanyMetadata.city,
                array_mode=False,
            )
            
            response_data = {"results": values}
            await _send_success_response(websocket, request.request_id, request.action, response_data)
    
    except ValidationError as exc:
        first_error = exc.errors()[0] if exc.errors() else {}
        message = first_error.get("msg", "Invalid query parameters")
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            message,
            "validation_error",
        )
    except Exception as exc:
        logger.exception("Error listing company cities via WebSocket: %s", exc)
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            f"An error occurred while listing company cities: {str(exc)}",
            "list_error",
        )


async def _handle_list_company_states(websocket: WebSocket, request: CompanyWebSocketRequest, user: User) -> None:
    """Handle list_company_states action."""
    try:
        async with AsyncSessionLocal() as session:
            filter_data = request.data.copy()
            multi_value_keys = (
                "exclude_industries",
                "exclude_keywords",
                "exclude_technologies",
                "exclude_locations",
            )
            for key in multi_value_keys:
                if key in filter_data and isinstance(filter_data[key], str):
                    filter_data[key] = [v.strip() for v in filter_data[key].split(",") if v.strip()]
            
            filters = CompanyFilterParams.model_validate(filter_data)
            params = AttributeListParams.model_validate(request.data)
            
            values = await companies_service.list_attribute_values(
                session,
                filters,
                params,
                column_factory=lambda Company, CompanyMetadata: CompanyMetadata.state,
                array_mode=False,
            )
            
            response_data = {"results": values}
            await _send_success_response(websocket, request.request_id, request.action, response_data)
    
    except ValidationError as exc:
        first_error = exc.errors()[0] if exc.errors() else {}
        message = first_error.get("msg", "Invalid query parameters")
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            message,
            "validation_error",
        )
    except Exception as exc:
        logger.exception("Error listing company states via WebSocket: %s", exc)
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            f"An error occurred while listing company states: {str(exc)}",
            "list_error",
        )


async def _handle_list_company_countries(websocket: WebSocket, request: CompanyWebSocketRequest, user: User) -> None:
    """Handle list_company_countries action."""
    try:
        async with AsyncSessionLocal() as session:
            filter_data = request.data.copy()
            multi_value_keys = (
                "exclude_industries",
                "exclude_keywords",
                "exclude_technologies",
                "exclude_locations",
            )
            for key in multi_value_keys:
                if key in filter_data and isinstance(filter_data[key], str):
                    filter_data[key] = [v.strip() for v in filter_data[key].split(",") if v.strip()]
            
            filters = CompanyFilterParams.model_validate(filter_data)
            params = AttributeListParams.model_validate(request.data)
            
            values = await companies_service.list_attribute_values(
                session,
                filters,
                params,
                column_factory=lambda Company, CompanyMetadata: CompanyMetadata.country,
                array_mode=False,
            )
            
            response_data = {"results": values}
            await _send_success_response(websocket, request.request_id, request.action, response_data)
    
    except ValidationError as exc:
        first_error = exc.errors()[0] if exc.errors() else {}
        message = first_error.get("msg", "Invalid query parameters")
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            message,
            "validation_error",
        )
    except Exception as exc:
        logger.exception("Error listing company countries via WebSocket: %s", exc)
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            f"An error occurred while listing company countries: {str(exc)}",
            "list_error",
        )


async def _handle_list_company_addresses(websocket: WebSocket, request: CompanyWebSocketRequest, user: User) -> None:
    """Handle list_company_addresses action."""
    try:
        async with AsyncSessionLocal() as session:
            filter_data = request.data.copy()
            multi_value_keys = (
                "exclude_industries",
                "exclude_keywords",
                "exclude_technologies",
                "exclude_locations",
            )
            for key in multi_value_keys:
                if key in filter_data and isinstance(filter_data[key], str):
                    filter_data[key] = [v.strip() for v in filter_data[key].split(",") if v.strip()]
            
            filters = CompanyFilterParams.model_validate(filter_data)
            params = AttributeListParams.model_validate(request.data)
            
            values = await companies_service.list_attribute_values(
                session,
                filters,
                params,
                column_factory=lambda Company, CompanyMetadata: Company.text_search,
                array_mode=False,
            )
            
            response_data = {"results": values}
            await _send_success_response(websocket, request.request_id, request.action, response_data)
    
    except ValidationError as exc:
        first_error = exc.errors()[0] if exc.errors() else {}
        message = first_error.get("msg", "Invalid query parameters")
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            message,
            "validation_error",
        )
    except Exception as exc:
        logger.exception("Error listing company addresses via WebSocket: %s", exc)
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            f"An error occurred while listing company addresses: {str(exc)}",
            "list_error",
        )


# ============================================================================
# Company Contact Operation Handlers (10 actions)
# ============================================================================

async def _handle_list_company_contacts(websocket: WebSocket, request: CompanyWebSocketRequest, user: User) -> None:
    """Handle list_company_contacts action."""
    if "company_uuid" not in request.data:
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            "Missing required field: company_uuid",
            "missing_field",
        )
        return
    
    try:
        async with AsyncSessionLocal() as session:
            company_uuid = request.data["company_uuid"]
            
            # Build filters from request data
            filter_data = request.data.copy()
            multi_value_keys = (
                "exclude_titles",
                "exclude_contact_locations",
                "exclude_seniorities",
                "exclude_departments",
            )
            for key in multi_value_keys:
                if key in filter_data and isinstance(filter_data[key], str):
                    filter_data[key] = [v.strip() for v in filter_data[key].split(",") if v.strip()]
            
            filters = CompanyContactFilterParams.model_validate(filter_data)
            
            # Resolve pagination
            limit = request.data.get("limit")
            offset = request.data.get("offset", 0)
            cursor = request.data.get("cursor")
            
            if limit is not None:
                page_limit = limit
            elif filters.page_size is not None:
                if settings.MAX_PAGE_SIZE is not None:
                    page_limit = min(filters.page_size, settings.MAX_PAGE_SIZE)
                else:
                    page_limit = filters.page_size
            else:
                page_limit = None  # Unlimited
            
            use_cursor = False
            resolved_offset = offset
            if cursor:
                try:
                    resolved_offset = decode_offset_cursor(cursor)
                    use_cursor = True
                except ValueError as exc:
                    await _send_error_response(
                        websocket,
                        request.request_id,
                        request.action,
                        f"Invalid cursor value: {str(exc)}",
                        "invalid_cursor",
                    )
                    return
            elif offset == 0 and filters.page is not None and page_limit is not None:
                resolved_offset = (filters.page - 1) * page_limit
            
            # Build request URL for pagination links
            request_url = request.data.get("request_url", f"http://localhost:8000/api/v1/companies/company/{company_uuid}/contacts/")
            
            page = await contacts_service.list_contacts_by_company(
                session,
                company_uuid,
                filters,
                limit=page_limit,
                offset=resolved_offset,
                request_url=request_url,
                use_cursor=use_cursor,
            )
            
            response_data = page.model_dump(mode='json')
            await _send_success_response(websocket, request.request_id, request.action, response_data)
    
    except ValidationError as exc:
        first_error = exc.errors()[0] if exc.errors() else {}
        message = first_error.get("msg", "Invalid query parameters")
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            message,
            "validation_error",
        )
    except Exception as exc:
        logger.exception("Error listing company contacts via WebSocket: %s", exc)
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            f"An error occurred while listing company contacts: {str(exc)}",
            "list_error",
        )


async def _handle_count_company_contacts(websocket: WebSocket, request: CompanyWebSocketRequest, user: User) -> None:
    """Handle count_company_contacts action."""
    if "company_uuid" not in request.data:
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            "Missing required field: company_uuid",
            "missing_field",
        )
        return
    
    try:
        async with AsyncSessionLocal() as session:
            company_uuid = request.data["company_uuid"]
            
            # Build filters from request data
            filter_data = request.data.copy()
            multi_value_keys = (
                "exclude_titles",
                "exclude_contact_locations",
                "exclude_seniorities",
                "exclude_departments",
            )
            for key in multi_value_keys:
                if key in filter_data and isinstance(filter_data[key], str):
                    filter_data[key] = [v.strip() for v in filter_data[key].split(",") if v.strip()]
            
            filters = CompanyContactFilterParams.model_validate(filter_data)
            count = await contacts_service.count_contacts_by_company(session, company_uuid, filters)
            
            response_data = count.model_dump(mode='json')
            await _send_success_response(websocket, request.request_id, request.action, response_data)
    
    except ValidationError as exc:
        first_error = exc.errors()[0] if exc.errors() else {}
        message = first_error.get("msg", "Invalid query parameters")
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            message,
            "validation_error",
        )
    except Exception as exc:
        logger.exception("Error counting company contacts via WebSocket: %s", exc)
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            f"An error occurred while counting company contacts: {str(exc)}",
            "count_error",
        )


async def _handle_get_company_contact_uuids(websocket: WebSocket, request: CompanyWebSocketRequest, user: User) -> None:
    """Handle get_company_contact_uuids action."""
    if "company_uuid" not in request.data:
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            "Missing required field: company_uuid",
            "missing_field",
        )
        return
    
    try:
        async with AsyncSessionLocal() as session:
            company_uuid = request.data["company_uuid"]
            
            # Build filters from request data
            filter_data = request.data.copy()
            multi_value_keys = (
                "exclude_titles",
                "exclude_contact_locations",
                "exclude_seniorities",
                "exclude_departments",
            )
            for key in multi_value_keys:
                if key in filter_data and isinstance(filter_data[key], str):
                    filter_data[key] = [v.strip() for v in filter_data[key].split(",") if v.strip()]
            
            filters = CompanyContactFilterParams.model_validate(filter_data)
            limit = request.data.get("limit")
            
            uuids = await contacts_service.get_uuids_by_company(session, company_uuid, filters, limit)
            
            response_data = UuidListResponse(count=len(uuids), uuids=uuids).model_dump(mode='json')
            await _send_success_response(websocket, request.request_id, request.action, response_data)
    
    except ValidationError as exc:
        first_error = exc.errors()[0] if exc.errors() else {}
        message = first_error.get("msg", "Invalid query parameters")
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            message,
            "validation_error",
        )
    except Exception as exc:
        logger.exception("Error getting company contact UUIDs via WebSocket: %s", exc)
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            f"An error occurred while getting company contact UUIDs: {str(exc)}",
            "uuids_error",
        )


async def _handle_company_contact_attribute(
    websocket: WebSocket,
    request: CompanyWebSocketRequest,
    user: User,
    attribute: str,
) -> None:
    """Helper handler for company contact attribute endpoints."""
    if "company_uuid" not in request.data:
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            "Missing required field: company_uuid",
            "missing_field",
        )
        return
    
    try:
        async with AsyncSessionLocal() as session:
            company_uuid = request.data["company_uuid"]
            
            # Build filters from request data
            filter_data = request.data.copy()
            multi_value_keys = (
                "exclude_titles",
                "exclude_contact_locations",
                "exclude_seniorities",
                "exclude_departments",
            )
            for key in multi_value_keys:
                if key in filter_data and isinstance(filter_data[key], str):
                    filter_data[key] = [v.strip() for v in filter_data[key].split(",") if v.strip()]
            
            filters = CompanyContactFilterParams.model_validate(filter_data)
            params = AttributeListParams.model_validate(request.data)
            
            values = await contacts_service.list_attribute_values_by_company(
                session,
                company_uuid,
                attribute,
                filters,
                params,
            )
            
            response_data = {"results": values}
            await _send_success_response(websocket, request.request_id, request.action, response_data)
    
    except ValidationError as exc:
        first_error = exc.errors()[0] if exc.errors() else {}
        message = first_error.get("msg", "Invalid query parameters")
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            message,
            "validation_error",
        )
    except Exception as exc:
        logger.exception("Error listing company contact attribute via WebSocket: %s", exc)
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            f"An error occurred while listing {attribute}: {str(exc)}",
            "list_error",
        )


async def _handle_list_company_contact_first_names(websocket: WebSocket, request: CompanyWebSocketRequest, user: User) -> None:
    """Handle list_company_contact_first_names action."""
    await _handle_company_contact_attribute(websocket, request, user, "first_name")


async def _handle_list_company_contact_last_names(websocket: WebSocket, request: CompanyWebSocketRequest, user: User) -> None:
    """Handle list_company_contact_last_names action."""
    await _handle_company_contact_attribute(websocket, request, user, "last_name")


async def _handle_list_company_contact_titles(websocket: WebSocket, request: CompanyWebSocketRequest, user: User) -> None:
    """Handle list_company_contact_titles action."""
    await _handle_company_contact_attribute(websocket, request, user, "title")


async def _handle_list_company_contact_seniorities(websocket: WebSocket, request: CompanyWebSocketRequest, user: User) -> None:
    """Handle list_company_contact_seniorities action."""
    await _handle_company_contact_attribute(websocket, request, user, "seniority")


async def _handle_list_company_contact_departments(websocket: WebSocket, request: CompanyWebSocketRequest, user: User) -> None:
    """Handle list_company_contact_departments action."""
    await _handle_company_contact_attribute(websocket, request, user, "department")


async def _handle_list_company_contact_email_statuses(websocket: WebSocket, request: CompanyWebSocketRequest, user: User) -> None:
    """Handle list_company_contact_email_statuses action."""
    await _handle_company_contact_attribute(websocket, request, user, "email_status")


# ============================================================================
# Unified WebSocket Endpoint
# ============================================================================

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):
    """
    Unified WebSocket endpoint for all company operations.
    
    This endpoint accepts messages with different actions:
    - Main operations: list_companies, get_company, count_companies, get_company_uuids, create_company, update_company, delete_company
    - Attribute lookups: list_company_names, list_industries, list_keywords, list_technologies, list_company_cities, list_company_states, list_company_countries, list_company_addresses
    - Company contacts: list_company_contacts, count_company_contacts, get_company_contact_uuids, and 7 attribute endpoints
    
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
            action_handlers = {
                # Main company operations
                "list_companies": _handle_list_companies,
                "get_company": _handle_get_company,
                "count_companies": _handle_count_companies,
                "get_company_uuids": _handle_get_company_uuids,
                "create_company": _handle_create_company,
                "update_company": _handle_update_company,
                "delete_company": _handle_delete_company,
                # Company attribute lookups
                "list_company_names": _handle_list_company_names,
                "list_industries": _handle_list_industries,
                "list_keywords": _handle_list_keywords,
                "list_technologies": _handle_list_technologies,
                "list_company_cities": _handle_list_company_cities,
                "list_company_states": _handle_list_company_states,
                "list_company_countries": _handle_list_company_countries,
                "list_company_addresses": _handle_list_company_addresses,
                # Company contact operations
                "list_company_contacts": _handle_list_company_contacts,
                "count_company_contacts": _handle_count_company_contacts,
                "get_company_contact_uuids": _handle_get_company_contact_uuids,
                "list_company_contact_first_names": _handle_list_company_contact_first_names,
                "list_company_contact_last_names": _handle_list_company_contact_last_names,
                "list_company_contact_titles": _handle_list_company_contact_titles,
                "list_company_contact_seniorities": _handle_list_company_contact_seniorities,
                "list_company_contact_departments": _handle_list_company_contact_departments,
                "list_company_contact_email_statuses": _handle_list_company_contact_email_statuses,
            }
            
            handler = action_handlers.get(request.action)
            if handler:
                await handler(websocket, request, user)
            else:
                await _send_error_response(
                    websocket,
                    request.request_id,
                    request.action,
                    f"Unknown action: {request.action}. Supported actions: {', '.join(sorted(action_handlers.keys()))}",
                    "unknown_action",
                )
    
    except WebSocketDisconnect:
        if user:
            connection_manager.disconnect(str(user.id))
        logger.info("WebSocket disconnected: user_id=%s", user.id if user else "unknown")
    except Exception as exc:
        logger.exception("Unexpected error in WebSocket endpoint: %s", exc)
        if user:
            connection_manager.disconnect(str(user.id))

