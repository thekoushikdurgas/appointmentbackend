"""WebSocket endpoints for Contacts API operations."""

import base64
import json
import shutil
import uuid
from pathlib import Path
from typing import Any, Iterable, List, Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_websocket
from app.repositories.user import UserProfileRepository
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.companies import Company, CompanyMetadata
from app.models.contacts import Contact, ContactMetadata
from app.models.imports import ImportJobStatus
from app.models.user import User
from app.schemas.common import CountResponse, CursorPage, UuidListResponse
from app.schemas.contacts import ContactCreate, ContactDetail, ContactListItem, ContactSimpleItem
from app.schemas.contacts_websocket import ContactsWebSocketRequest, ContactsWebSocketResponse
from app.schemas.filters import AttributeListParams, ContactFilterParams
from app.schemas.imports import ImportErrorRecord, ImportJobDetail, ImportJobWithErrors
from app.services.contacts_service import ContactsService
from app.services.import_service import ImportService
from app.tasks.import_tasks import process_contacts_import
from app.utils.cursor import decode_offset_cursor

router = APIRouter(prefix="/contacts", tags=["Contacts WebSocket"])
logger = get_logger(__name__)
settings = get_settings()
contacts_service = ContactsService()
import_service = ImportService()


class ContactsWebSocketManager:
    """Manages WebSocket connections for Contacts endpoints."""

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
connection_manager = ContactsWebSocketManager()


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
    response = ContactsWebSocketResponse(
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
    response = ContactsWebSocketResponse(
        request_id=request_id,
        action=action,
        status="success",
        data=data,
        error=None,
    )
    # Use mode='json' to serialize datetime objects to ISO format strings
    await connection_manager.send_message(websocket, response.model_dump(mode='json'))


async def _parse_websocket_message(websocket: WebSocket, text: str) -> Optional[ContactsWebSocketRequest]:
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
        request = ContactsWebSocketRequest.model_validate(data)
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


def _parse_iterable_like(value: Any) -> Iterable[str]:
    """Best effort parsing for list-like attribute payloads."""
    if value is None:
        return []
    if isinstance(value, str):
        # Split comma-separated values
        return [v.strip() for v in value.split(",") if v.strip()]
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if v]
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


async def _check_user_is_admin(user: User, session: AsyncSession) -> bool:
    """Check if a user is an admin."""
    profile_repo = UserProfileRepository()
    profile = await profile_repo.get_by_user_id(session, user.id)
    user_role = profile.role if profile and profile.role else "Member"
    return user_role == "Admin"


def _build_filter_params_from_data(data: dict) -> ContactFilterParams:
    """Build ContactFilterParams from WebSocket message data."""
    # Handle multi-value exclusion filters
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
    filter_dict = {}
    for key, value in data.items():
        if key in multi_value_keys and isinstance(value, str):
            # Split comma-separated string into list
            filter_dict[key] = [v.strip() for v in value.split(",") if v.strip()]
        else:
            filter_dict[key] = value
    
    return ContactFilterParams.model_validate(filter_dict)


async def _handle_list_contacts_action(websocket: WebSocket, request: ContactsWebSocketRequest) -> None:
    """Handle the list_contacts action."""
    try:
        async with AsyncSessionLocal() as session:
            # Build filter parameters from request data
            try:
                filters = _build_filter_params_from_data(request.data)
            except ValidationError as exc:
                await _send_error_response(
                    websocket,
                    request.request_id,
                    request.action,
                    f"Invalid filter parameters: {exc.errors()[0].get('msg', 'Validation error')}",
                    "validation_error",
                )
                return
            
            # Resolve pagination
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
            
            # Query contacts
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
            
            # Build response data
            response_data = {
                "next": page.next,
                "previous": page.previous,
                "results": [item.model_dump(mode='json') for item in page.results],
            }
            
            await _send_success_response(websocket, request.request_id, request.action, response_data)
    
    except Exception as exc:
        logger.exception("Error listing contacts via WebSocket: %s", exc)
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            f"An error occurred while listing contacts: {str(exc)}",
            "list_error",
        )


async def _handle_get_contact_action(websocket: WebSocket, request: ContactsWebSocketRequest) -> None:
    """Handle the get_contact action."""
    if "contact_uuid" not in request.data:
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            "Missing required field: contact_uuid",
            "missing_field",
        )
        return
    
    try:
        async with AsyncSessionLocal() as session:
            contact = await contacts_service.get_contact(session, request.data["contact_uuid"])
            if not contact:
                await _send_error_response(
                    websocket,
                    request.request_id,
                    request.action,
                    "Contact not found",
                    "not_found",
                )
                return
            
            response_data = contact.model_dump(mode='json')
            await _send_success_response(websocket, request.request_id, request.action, response_data)
    
    except Exception as exc:
        logger.exception("Error getting contact via WebSocket: %s", exc)
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            f"An error occurred while getting contact: {str(exc)}",
            "get_error",
        )


async def _handle_count_contacts_action(websocket: WebSocket, request: ContactsWebSocketRequest) -> None:
    """Handle the count_contacts action."""
    try:
        async with AsyncSessionLocal() as session:
            # Build filter parameters from request data
            try:
                filters = _build_filter_params_from_data(request.data)
            except ValidationError as exc:
                await _send_error_response(
                    websocket,
                    request.request_id,
                    request.action,
                    f"Invalid filter parameters: {exc.errors()[0].get('msg', 'Validation error')}",
                    "validation_error",
                )
                return
            
            count_response = await contacts_service.count_contacts(session, filters)
            
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


async def _handle_get_contact_uuids_action(websocket: WebSocket, request: ContactsWebSocketRequest) -> None:
    """Handle the get_contact_uuids action."""
    try:
        async with AsyncSessionLocal() as session:
            # Build filter parameters from request data
            try:
                filters = _build_filter_params_from_data(request.data)
            except ValidationError as exc:
                await _send_error_response(
                    websocket,
                    request.request_id,
                    request.action,
                    f"Invalid filter parameters: {exc.errors()[0].get('msg', 'Validation error')}",
                    "validation_error",
                )
                return
            
            limit = request.data.get("limit")
            uuids = await contacts_service.get_uuids_by_filters(session, filters, limit)
            
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


async def _handle_create_contact_action(websocket: WebSocket, request: ContactsWebSocketRequest, user: User) -> None:
    """Handle the create_contact action."""
    # Validate write key
    write_key = request.data.get("write_key")
    configured_key = (settings.CONTACTS_WRITE_KEY or "").strip()
    if not configured_key:
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            "Write key is not configured",
            "write_key_not_configured",
        )
        return
    if write_key != configured_key:
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            "Invalid write key",
            "invalid_write_key",
        )
        return
    
    # Validate admin access
    async with AsyncSessionLocal() as session:
        is_admin = await _check_user_is_admin(user, session)
        if not is_admin:
            await _send_error_response(
                websocket,
                request.request_id,
                request.action,
                "Admin access required",
                "admin_required",
            )
            return
    
    try:
        async with AsyncSessionLocal() as session:
            # Build ContactCreate from request data
            contact_data = {k: v for k, v in request.data.items() if k != "write_key"}
            payload = ContactCreate.model_validate(contact_data)
            
            contact = await contacts_service.create_contact(session, payload)
            
            response_data = contact.model_dump(mode='json')
            await _send_success_response(websocket, request.request_id, request.action, response_data)
    
    except ValidationError as exc:
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            f"Invalid contact data: {exc.errors()[0].get('msg', 'Validation error')}",
            "validation_error",
        )
    except Exception as exc:
        logger.exception("Error creating contact via WebSocket: %s", exc)
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            f"An error occurred while creating contact: {str(exc)}",
            "create_error",
        )


async def _handle_field_action(
    websocket: WebSocket,
    request: ContactsWebSocketRequest,
    column_factory,
    attribute_label: str,
    array_mode: bool = False,
) -> None:
    """Generic handler for field-specific actions."""
    try:
        async with AsyncSessionLocal() as session:
            # Build filter parameters
            try:
                filters = _build_filter_params_from_data(request.data)
            except ValidationError as exc:
                await _send_error_response(
                    websocket,
                    request.request_id,
                    request.action,
                    f"Invalid filter parameters: {exc.errors()[0].get('msg', 'Validation error')}",
                    "validation_error",
                )
                return
            
            # Build attribute params
            params_data = {
                "search": request.data.get("search"),
                "distinct": request.data.get("distinct", False),
                "limit": request.data.get("limit"),
                "offset": request.data.get("offset", 0),
            }
            params = AttributeListParams.model_validate(params_data)
            
            # Handle separated mode for array fields
            separated = request.data.get("separated", False)
            if separated and array_mode:
                effective_params = params.model_copy(update={"distinct": True}) if not params.distinct else params
            else:
                effective_params = params
            
            # Get values
            values = await contacts_service.list_attribute_values(
                session,
                filters,
                effective_params,
                column_factory=column_factory,
                array_mode=separated and array_mode,
            )
            
            # Post-process for separated mode
            if separated and array_mode:
                deduped = _normalize_array_values(values)
                if params.limit:
                    deduped = deduped[: params.limit]
                values = deduped
            
            # Apply distinct if requested
            if effective_params.distinct:
                seen = set()
                unique_values = []
                for value in values:
                    if value is None:
                        continue
                    normalized = value.lower() if isinstance(value, str) else str(value)
                    if normalized not in seen:
                        seen.add(normalized)
                        unique_values.append(value)
                values = unique_values
            
            response_data = {"results": values}
            await _send_success_response(websocket, request.request_id, request.action, response_data)
    
    except Exception as exc:
        logger.exception("Error getting field values via WebSocket: %s", exc)
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            f"An error occurred while getting field values: {str(exc)}",
            "field_error",
        )


async def _handle_get_titles_action(websocket: WebSocket, request: ContactsWebSocketRequest) -> None:
    """Handle the get_titles action."""
    await _handle_field_action(
        websocket,
        request,
        lambda Contact, Company, ContactMetadata, CompanyMetadata: Contact.title,
        "title",
    )


async def _handle_get_companies_action(websocket: WebSocket, request: ContactsWebSocketRequest) -> None:
    """Handle the get_companies action."""
    await _handle_field_action(
        websocket,
        request,
        lambda Contact, Company, ContactMetadata, CompanyMetadata: Company.name,
        "company",
    )


async def _handle_get_industries_action(websocket: WebSocket, request: ContactsWebSocketRequest) -> None:
    """Handle the get_industries action."""
    separated = request.data.get("separated", False)
    column_factory = (
        (lambda Contact, Company, ContactMetadata, CompanyMetadata: Company.industries)
        if separated
        else (lambda Contact, Company, ContactMetadata, CompanyMetadata: func.array_to_string(Company.industries, ","))
    )
    
    await _handle_field_action(websocket, request, column_factory, "industry", array_mode=True)


async def _handle_get_keywords_action(websocket: WebSocket, request: ContactsWebSocketRequest) -> None:
    """Handle the get_keywords action."""
    separated = request.data.get("separated", False)
    column_factory = (
        (lambda Contact, Company, ContactMetadata, CompanyMetadata: Company.keywords)
        if separated
        else (lambda Contact, Company, ContactMetadata, CompanyMetadata: func.array_to_string(Company.keywords, ","))
    )
    
    await _handle_field_action(websocket, request, column_factory, "keywords", array_mode=True)


async def _handle_get_technologies_action(websocket: WebSocket, request: ContactsWebSocketRequest) -> None:
    """Handle the get_technologies action.
    
    Technologies are always returned as individual values (one per technology),
    not as comma-separated strings.
    """
    # Always use array mode - technologies are always separated
    column_factory = (
        lambda Contact, Company, ContactMetadata, CompanyMetadata: Company.technologies
    )
    # Force separated mode by setting it in request data
    request.data["separated"] = True
    await _handle_field_action(websocket, request, column_factory, "technologies", array_mode=True)


async def _handle_get_company_addresses_action(websocket: WebSocket, request: ContactsWebSocketRequest) -> None:
    """Handle the get_company_addresses action."""
    await _handle_field_action(
        websocket,
        request,
        lambda Contact, Company, ContactMetadata, CompanyMetadata: Company.text_search,
        "company_address",
    )


async def _handle_get_contact_addresses_action(websocket: WebSocket, request: ContactsWebSocketRequest) -> None:
    """Handle the get_contact_addresses action."""
    await _handle_field_action(
        websocket,
        request,
        lambda Contact, Company, ContactMetadata, CompanyMetadata: Contact.text_search,
        "contact_address",
    )


async def _handle_get_import_info_action(websocket: WebSocket, request: ContactsWebSocketRequest) -> None:
    """Handle the get_import_info action."""
    response_data = {
        "message": "Upload a CSV file via POST to /api/v1/contacts/import/ to start a background import job."
    }
    await _send_success_response(websocket, request.request_id, request.action, response_data)


async def _handle_upload_contacts_csv_action(websocket: WebSocket, request: ContactsWebSocketRequest, user: User) -> None:
    """Handle the upload_contacts_csv action."""
    # Validate admin access
    async with AsyncSessionLocal() as session:
        is_admin = await _check_user_is_admin(user, session)
        if not is_admin:
            await _send_error_response(
                websocket,
                request.request_id,
                request.action,
                "Admin access required",
                "admin_required",
            )
            return
    
    # Validate file data
    if "file_data" not in request.data or "file_name" not in request.data:
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            "Missing required fields: file_data and file_name",
            "missing_field",
        )
        return
    
    file_name = request.data["file_name"]
    file_data = request.data["file_data"]  # Base64 encoded or binary string
    
    try:
        # Decode base64 if needed
        if isinstance(file_data, str):
            try:
                file_bytes = base64.b64decode(file_data)
            except Exception:
                # Try as raw binary string
                file_bytes = file_data.encode('utf-8') if isinstance(file_data, str) else file_data
        else:
            file_bytes = file_data
        
        if len(file_bytes) == 0:
            await _send_error_response(
                websocket,
                request.request_id,
                request.action,
                "Uploaded file is empty",
                "empty_file",
            )
            return
        
        # Save file
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        temp_filename = f"{uuid.uuid4()}_{file_name}"
        temp_path = upload_dir / temp_filename
        
        with temp_path.open("wb") as buffer:
            buffer.write(file_bytes)
        
        # Create import job and enqueue
        async with AsyncSessionLocal() as session:
            job_id = uuid.uuid4().hex
            job = await import_service.create_job(
                session,
                job_id=job_id,
                file_name=file_name,
                file_path=str(temp_path),
                total_rows=0,
            )
            
            # Enqueue background task
            try:
                process_contacts_import.delay(job.job_id, str(temp_path))
            except Exception as exc:
                logger.exception("Failed to enqueue import job: job_id=%s", job.job_id)
                temp_path.unlink(missing_ok=True)
                await import_service.set_status(
                    session,
                    job.job_id,
                    status=ImportJobStatus.failed,
                    message="Failed to enqueue background import task",
                )
                raise
        
        response_data = ImportJobDetail.model_validate(job).model_dump(mode='json')
        await _send_success_response(websocket, request.request_id, request.action, response_data)
    
    except Exception as exc:
        logger.exception("Error uploading CSV via WebSocket: %s", exc)
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            f"An error occurred while uploading CSV: {str(exc)}",
            "upload_error",
        )


async def _handle_get_import_status_action(websocket: WebSocket, request: ContactsWebSocketRequest) -> None:
    """Handle the get_import_status action."""
    if "job_id" not in request.data:
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            "Missing required field: job_id",
            "missing_field",
        )
        return
    
    try:
        async with AsyncSessionLocal() as session:
            include_errors = request.data.get("include_errors", False)
            job = await import_service.get_job(session, request.data["job_id"], include_errors=include_errors)
            
            if not job:
                await _send_error_response(
                    websocket,
                    request.request_id,
                    request.action,
                    "Import job not found",
                    "not_found",
                )
                return
            
            response_data = job.model_dump(mode='json')
            await _send_success_response(websocket, request.request_id, request.action, response_data)
    
    except Exception as exc:
        logger.exception("Error getting import status via WebSocket: %s", exc)
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            f"An error occurred while getting import status: {str(exc)}",
            "import_status_error",
        )


async def _handle_get_import_errors_action(websocket: WebSocket, request: ContactsWebSocketRequest) -> None:
    """Handle the get_import_errors action."""
    if "job_id" not in request.data:
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            "Missing required field: job_id",
            "missing_field",
        )
        return
    
    try:
        async with AsyncSessionLocal() as session:
            job = await import_service.get_job(session, request.data["job_id"], include_errors=True)
            
            if not job or not isinstance(job, ImportJobWithErrors):
                await _send_error_response(
                    websocket,
                    request.request_id,
                    request.action,
                    "Import job not found or has no errors",
                    "not_found",
                )
                return
            
            response_data = {"errors": [err.model_dump(mode='json') for err in job.errors]}
            await _send_success_response(websocket, request.request_id, request.action, response_data)
    
    except Exception as exc:
        logger.exception("Error getting import errors via WebSocket: %s", exc)
        await _send_error_response(
            websocket,
            request.request_id,
            request.action,
            f"An error occurred while getting import errors: {str(exc)}",
            "import_errors_error",
        )


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):
    """
    Unified WebSocket endpoint for all Contacts operations.
    
    This endpoint accepts messages with different actions:
    - "list_contacts": List contacts with filtering/pagination
    - "get_contact": Retrieve single contact by UUID
    - "count_contacts": Get contact count
    - "get_contact_uuids": Get contact UUIDs
    - "create_contact": Create new contact (admin only)
    - "get_titles": List titles
    - "get_companies": List companies
    - "get_industries": List industries
    - "get_keywords": List keywords
    - "get_technologies": List technologies
    - "get_company_addresses": List company addresses
    - "get_contact_addresses": List contact addresses
    - "get_import_info": Get import information
    - "upload_contacts_csv": Upload CSV for import
    - "get_import_status": Get import job status
    - "get_import_errors": Get import errors
    
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
            if request.action == "list_contacts":
                await _handle_list_contacts_action(websocket, request)
            elif request.action == "get_contact":
                await _handle_get_contact_action(websocket, request)
            elif request.action == "count_contacts":
                await _handle_count_contacts_action(websocket, request)
            elif request.action == "get_contact_uuids":
                await _handle_get_contact_uuids_action(websocket, request)
            elif request.action == "create_contact":
                await _handle_create_contact_action(websocket, request, user)
            elif request.action == "get_titles":
                await _handle_get_titles_action(websocket, request)
            elif request.action == "get_companies":
                await _handle_get_companies_action(websocket, request)
            elif request.action == "get_industries":
                await _handle_get_industries_action(websocket, request)
            elif request.action == "get_keywords":
                await _handle_get_keywords_action(websocket, request)
            elif request.action == "get_technologies":
                await _handle_get_technologies_action(websocket, request)
            elif request.action == "get_company_addresses":
                await _handle_get_company_addresses_action(websocket, request)
            elif request.action == "get_contact_addresses":
                await _handle_get_contact_addresses_action(websocket, request)
            elif request.action == "get_import_info":
                await _handle_get_import_info_action(websocket, request)
            elif request.action == "upload_contacts_csv":
                await _handle_upload_contacts_csv_action(websocket, request, user)
            elif request.action == "get_import_status":
                await _handle_get_import_status_action(websocket, request)
            elif request.action == "get_import_errors":
                await _handle_get_import_errors_action(websocket, request)
            else:
                await _send_error_response(
                    websocket,
                    request.request_id,
                    request.action,
                    f"Unknown action: {request.action}. Supported actions: list_contacts, get_contact, count_contacts, get_contact_uuids, create_contact, get_titles, get_companies, get_industries, get_keywords, get_technologies, get_company_addresses, get_contact_addresses, get_import_info, upload_contacts_csv, get_import_status, get_import_errors",
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

