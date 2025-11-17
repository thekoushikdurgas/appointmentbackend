"""Pydantic schemas for Contacts WebSocket API."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class ContactsWebSocketRequest(BaseModel):
    """Schema for WebSocket request messages."""

    action: str = Field(
        ...,
        description="Action to perform. Supported actions: list_contacts, get_contact, count_contacts, "
        "get_contact_uuids, create_contact, get_titles, get_companies, get_industries, get_keywords, "
        "get_technologies, get_company_addresses, get_contact_addresses, get_cities, get_states, "
        "get_countries, get_company_cities, get_company_states, get_company_countries, get_import_info, "
        "upload_contacts_csv, get_import_status, get_import_errors",
    )
    request_id: str = Field(..., description="Client-generated request ID for tracking responses")
    data: dict[str, Any] = Field(..., description="Request payload matching REST API structure")


class ContactsWebSocketResponse(BaseModel):
    """Schema for WebSocket response messages."""

    request_id: str = Field(..., description="Echo of client's request_id")
    action: str = Field(..., description="Echo of action from request")
    status: str = Field(..., description="Response status: success or error")
    data: Optional[dict[str, Any]] = Field(
        None, description="Response payload (present when status=success)"
    )
    error: Optional[dict[str, Any]] = Field(
        None, description="Error details (present when status=error)"
    )

