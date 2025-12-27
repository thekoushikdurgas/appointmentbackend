"""HTTP client for Connectra VQL API integration."""

import json
import logging
import time
from typing import Any, Dict, List, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import get_settings
from app.core.vql.structures import VQLCondition, VQLFilter, VQLOperator, VQLQuery
from app.schemas.vql import (
    VQLCompanyConfig,
    VQLCountResponse,
    VQLFilterDataResponse,
    VQLFiltersResponse,
    VQLQuery,
)
from app.utils.logger import get_logger, log_external_api_call

logger = get_logger(__name__)
settings = get_settings()


def _fix_filter_aliases(filters_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively fix filter aliases to ensure 'and'/'or' are used instead of 'and_'/'or_'.
    
    This is a safety measure in case Pydantic's by_alias=True doesn't work recursively
    for nested VQLFilter objects.
    
    Args:
        filters_dict: Filter dictionary that may contain 'and_' or 'or_' keys
        
    Returns:
        Filter dictionary with 'and'/'or' keys
    """
    if not isinstance(filters_dict, dict):
        return filters_dict
    
    fixed = {}
    for key, value in filters_dict.items():
        if key == "and_":
            fixed["and"] = [_fix_filter_aliases(item) if isinstance(item, dict) else item 
                            for item in value] if isinstance(value, list) else value
        elif key == "or_":
            fixed["or"] = [_fix_filter_aliases(item) if isinstance(item, dict) else item 
                          for item in value] if isinstance(value, list) else value
        elif isinstance(value, dict):
            fixed[key] = _fix_filter_aliases(value)
        elif isinstance(value, list):
            fixed[key] = [_fix_filter_aliases(item) if isinstance(item, dict) else item 
                         for item in value]
        else:
            fixed[key] = value
    return fixed


class ConnectraClientError(Exception):
    """Base exception for Connectra client errors."""

    pass


class ConnectraClient:
    """HTTP client for interacting with Connectra VQL API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        """
        Initialize Connectra client.

        Args:
            base_url: Connectra API base URL (defaults to CONNECTRA_BASE_URL from settings)
            api_key: API key for authentication (defaults to CONNECTRA_API_KEY from settings)
            timeout: Request timeout in seconds (defaults to CONNECTRA_TIMEOUT from settings)
        """
        self.base_url = (base_url or settings.CONNECTRA_BASE_URL).rstrip("/")
        self.api_key = api_key or settings.CONNECTRA_API_KEY
        self.timeout = timeout or settings.CONNECTRA_TIMEOUT

        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _ensure_client(self):
        """Ensure HTTP client is initialized."""
        if self._client is None:
            logger.debug(
                "Initializing httpx client",
                extra={
                    "context": {
                        "base_url": self.base_url,
                        "has_api_key": bool(self.api_key)
                    }
                }
            )
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"X-API-Key": self.api_key} if self.api_key else {},
                follow_redirects=True,
            )

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Connectra API with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            json_data: Request body data

        Returns:
            Response JSON data

        Raises:
            ConnectraClientError: If request fails
        """
        logger.debug(
            "_make_request called",
            extra={
                "context": {
                    "method": method,
                    "endpoint": endpoint,
                    "base_url": self.base_url,
                    "full_url": f"{self.base_url}{endpoint}"
                }
            }
        )
        await self._ensure_client()
        url = f"{self.base_url}{endpoint}"
        request_start_time = time.time()

        try:
            response = await self._client.request(
                method=method,
                url=url,
                headers=self._get_headers(),
                json=json_data,
                follow_redirects=True,
            )
            logger.debug(
                "Response received",
                extra={
                    "context": {
                        "status_code": response.status_code,
                        "url": str(response.url),
                        "has_redirect": hasattr(response, "history") and len(response.history) > 0
                    }
                }
            )
            response.raise_for_status()
            response_json = response.json()
            duration_ms = (time.time() - request_start_time) * 1000
            
            # Log successful API call
            log_external_api_call(
                service_name="Connectra",
                method=method,
                url=url,
                status_code=response.status_code,
                duration_ms=duration_ms,
                request_data=json_data,
                response_data={"has_data": bool(response_json.get("data")) if isinstance(response_json, dict) else False},
                logger_name="app.clients.connectra",
            )
            
            logger.debug(
                "Response JSON parsed",
                extra={
                    "context": {
                        "keys": list(response_json.keys()) if isinstance(response_json, dict) else "not_dict",
                        "has_success": isinstance(response_json, dict) and "success" in response_json,
                        "has_count": isinstance(response_json, dict) and "count" in response_json
                    }
                }
            )
            return response_json
        except httpx.HTTPStatusError as exc:
            duration_ms = (time.time() - request_start_time) * 1000
            logger.debug(
                "HTTP status error",
                extra={
                    "context": {
                        "status_code": exc.response.status_code,
                        "url": str(exc.response.url),
                        "is_redirect": exc.response.status_code in [301, 302, 303, 307, 308]
                    }
                }
            )
            error_msg = f"Connectra API error: {exc.response.status_code}"
            error_detail = None
            try:
                error_body = exc.response.json()
                error_detail = error_body.get('error', 'Unknown error')
                error_msg += f" - {error_detail}"
            except Exception:
                error_detail = exc.response.text
                error_msg += f" - {error_detail}"
            
            # Enhanced error logging with request details
            logger.error(
                error_msg,
                extra={
                    "context": {
                        "method": method,
                        "endpoint": endpoint,
                        "status_code": exc.response.status_code,
                        "error_detail": error_detail,
                        "request_limit": json_data.get("limit") if json_data else None,
                        "request_offset": json_data.get("offset") if json_data else None,
                        "request_has_filters": bool(json_data.get("filters")) if json_data else False,
                    }
                }
            )
            
            log_external_api_call(
                service_name="Connectra",
                method=method,
                url=url,
                status_code=exc.response.status_code,
                duration_ms=duration_ms,
                request_data=json_data,
                error=exc,
                logger_name="app.clients.connectra",
            )
            
            raise ConnectraClientError(error_msg) from exc
        except httpx.RequestError as exc:
            duration_ms = (time.time() - request_start_time) * 1000
            log_external_api_call(
                service_name="Connectra",
                method=method,
                url=url,
                duration_ms=duration_ms,
                request_data=json_data,
                error=exc,
                logger_name="app.clients.connectra",
            )
            error_msg = f"Connectra API request failed: {str(exc)}"
            raise ConnectraClientError(error_msg) from exc

    async def search_contacts(
        self, vql_query: VQLQuery
    ) -> Dict[str, Any]:
        """
        Search contacts using VQL query.

        Args:
            vql_query: VQL query object

        Returns:
            Response data with contacts
        """
        # Use by_alias=True to ensure nested VQLFilter uses "and"/"or" instead of "and_"/"or_"
        query_dict = vql_query.model_dump(exclude_none=True, by_alias=True, mode="json")
        # Safety check: recursively fix any remaining "and_"/"or_" keys (shouldn't happen but ensures correctness)
        query_dict = _fix_filter_aliases(query_dict)
        return await self._make_request("POST", "/contacts", json_data=query_dict)

    async def search_companies(
        self, vql_query: VQLQuery
    ) -> Dict[str, Any]:
        """
        Search companies using VQL query.

        Args:
            vql_query: VQL query object

        Returns:
            Response data with companies
        """
        # Use by_alias=True to ensure nested VQLFilter uses "and"/"or" instead of "and_"/"or_"
        query_dict = vql_query.model_dump(exclude_none=True, by_alias=True, mode="json")
        # Safety check: recursively fix any remaining "and_"/"or_" keys (shouldn't happen but ensures correctness)
        query_dict = _fix_filter_aliases(query_dict)
        return await self._make_request("POST", "/companies", json_data=query_dict)

    async def count_contacts(self, vql_query: VQLQuery) -> int:
        """
        Count contacts matching VQL query.

        Args:
            vql_query: VQL query object

        Returns:
            Total count of matching contacts
        """
        # Use by_alias=True to ensure nested VQLFilter uses "and"/"or" instead of "and_"/"or_"
        query_dict = vql_query.model_dump(exclude_none=True, by_alias=True, mode="json")
        # Safety check: recursively fix any remaining "and_"/"or_" keys (shouldn't happen but ensures correctness)
        query_dict = _fix_filter_aliases(query_dict)
        response_data = await self._make_request(
            "POST", "/contacts/count", json_data=query_dict
        )
        # Filter out extra fields (like "success") before validation
        # The API returns {"count": int, "success": bool}, but VQLCountResponse only accepts "count"
        filtered_data = {"count": response_data.get("count")} if isinstance(response_data, dict) else response_data
        count_response = VQLCountResponse(**filtered_data)
        return count_response.count

    async def count_companies(self, vql_query: VQLQuery) -> int:
        """
        Count companies matching VQL query.

        Args:
            vql_query: VQL query object

        Returns:
            Total count of matching companies
        """
        logger.debug("count_companies called")
        # Use by_alias=True to ensure nested VQLFilter uses "and"/"or" instead of "and_"/"or_"
        query_dict = vql_query.model_dump(exclude_none=True, by_alias=True, mode="json")
        # Safety check: recursively fix any remaining "and_"/"or_" keys (shouldn't happen but ensures correctness)
        query_dict = _fix_filter_aliases(query_dict)
        response_data = await self._make_request(
            "POST", "/companies/count", json_data=query_dict
        )
        logger.debug(
            "Response data before validation",
            extra={
                "context": {
                    "response_keys": list(response_data.keys()) if isinstance(response_data, dict) else "not_dict",
                    "has_success": isinstance(response_data, dict) and "success" in response_data,
                    "has_count": isinstance(response_data, dict) and "count" in response_data
                }
            }
        )
        # Filter out extra fields (like "success") before validation
        # The API returns {"count": int, "success": bool}, but VQLCountResponse only accepts "count"
        filtered_data = {"count": response_data.get("count")} if isinstance(response_data, dict) else response_data
        logger.debug(
            "Filtered response data for validation",
            extra={"context": {"filtered_data": filtered_data}}
        )
        try:
            count_response = VQLCountResponse(**filtered_data)
            logger.debug(
                "VQLCountResponse validation succeeded",
                extra={"context": {"count": count_response.count}}
            )
            return count_response.count
        except Exception as validation_error:
            logger.debug(
                "VQLCountResponse validation failed",
                extra={
                    "context": {
                        "error_type": type(validation_error).__name__,
                        "error_message": str(validation_error),
                        "response_data": response_data,
                        "filtered_data": filtered_data
                    }
                }
            )
            raise

    async def get_filters(self, service: str) -> List[Dict[str, Any]]:
        """
        Get available filters for a service.

        Args:
            service: Service name ("contact" or "company")

        Returns:
            List of filter definitions
        """
        # Properly pluralize service name
        service_plural = "companies" if service == "company" else "contacts"
        response_data = await self._make_request("GET", f"/{service_plural}/filters")
        logger.debug(
            "Response data before VQLFiltersResponse creation",
            extra={
                "context": {
                    "service": service,
                    "response_keys": list(response_data.keys()) if isinstance(response_data, dict) else "not_dict",
                    "has_success": isinstance(response_data, dict) and "success" in response_data,
                    "has_data": isinstance(response_data, dict) and "data" in response_data,
                    "success_value": response_data.get("success") if isinstance(response_data, dict) else None
                }
            }
        )
        # Filter out extra fields like 'success' that are not in the model
        filtered_data = {k: v for k, v in response_data.items() if k in ["data"]}
        logger.debug(
            "Filtered data for VQLFiltersResponse",
            extra={
                "context": {
                    "filtered_keys": list(filtered_data.keys()),
                    "original_keys": list(response_data.keys()) if isinstance(response_data, dict) else []
                }
            }
        )
        filters_response = VQLFiltersResponse(**filtered_data)
        return [filter_def.model_dump() for filter_def in filters_response.data]

    async def get_filter_data(
        self,
        service: str,
        filter_key: str,
        search_text: Optional[str] = None,
        page: int = 1,
        limit: int = 25,
    ) -> List[str]:
        """
        Get filter data values for a specific filter.

        Args:
            service: Service name ("contact" or "company")
            filter_key: Filter key from filters list
            search_text: Optional text to filter results
            page: Page number
            limit: Results per page

        Returns:
            List of filter values
        """
        request_data: Dict[str, Any] = {
            "service": service,
            "filter_key": filter_key,
            "page": page,
            "limit": limit,
        }
        if search_text:
            request_data["search_text"] = search_text

        # Properly pluralize service name
        service_plural = "companies" if service == "company" else "contacts"
        response_data = await self._make_request(
            "POST", f"/{service_plural}/filters/data", json_data=request_data
        )
        # Filter out extra fields like 'success' that are not in the model
        filtered_data = {k: v for k, v in response_data.items() if k in ["data"]}
        filter_data_response = VQLFilterDataResponse(**filtered_data)
        return filter_data_response.data

    async def health_check(self) -> Dict[str, Any]:
        """
        Check Connectra service health.

        Returns:
            Health check response
        """
        return await self._make_request("GET", "/health")

    async def get_contact_by_uuid(
        self, contact_uuid: str
    ) -> Dict[str, Any]:
        """
        Get a single contact by UUID using VQL.

        Args:
            contact_uuid: Contact UUID

        Returns:
            Contact data from VQL response
        """

        # Build VQL query with UUID filter
        condition = VQLCondition(
            field="uuid",
            operator=VQLOperator.EQ,
            value=contact_uuid
        )
        filter_obj = VQLFilter(and_=[condition])
        vql_query = VQLQuery(
            filters=filter_obj,
            limit=1,
            offset=0
        )

        response = await self.search_contacts(vql_query)
        data = response.get("data", [])
        if not data:
            raise ConnectraClientError(f"Contact with UUID {contact_uuid} not found")
        return data[0]

    async def get_company_by_uuid(
        self, company_uuid: str
    ) -> Dict[str, Any]:
        """
        Get a single company by UUID using VQL.

        Args:
            company_uuid: Company UUID

        Returns:
            Company data from VQL response
        """

        # Build VQL query with UUID filter
        condition = VQLCondition(
            field="uuid",
            operator=VQLOperator.EQ,
            value=company_uuid
        )
        filter_obj = VQLFilter(and_=[condition])
        vql_query = VQLQuery(
            filters=filter_obj,
            limit=1,
            offset=0
        )

        response = await self.search_companies(vql_query)
        data = response.get("data", [])
        if not data:
            raise ConnectraClientError(f"Company with UUID {company_uuid} not found")
        return data[0]

    async def search_by_linkedin_url(
        self, linkedin_url: str, entity_type: str = "contact"
    ) -> Dict[str, Any]:
        """
        Search for contacts or companies by LinkedIn URL.

        Args:
            linkedin_url: LinkedIn URL to search for
            entity_type: "contact" or "company"

        Returns:
            VQL response with matching records
        """

        # Build VQL query with linkedin_url filter
        # For contacts, use "linkedin_url" field
        # For companies, use "linkedin_url" field
        field_name = "linkedin_url"
        condition = VQLCondition(
            field=field_name,
            operator=VQLOperator.EQ,  # Exact match for LinkedIn URLs
            value=linkedin_url
        )
        filter_obj = VQLFilter(and_=[condition])
        vql_query = VQLQuery(filters=filter_obj)

        if entity_type == "contact":
            return await self.search_contacts(vql_query)
        else:
            return await self.search_companies(vql_query)

    async def batch_search_by_uuids(
        self,
        uuids: List[str],
        entity_type: str = "contact",
        batch_size: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Batch search for contacts or companies by UUID list.

        Args:
            uuids: List of UUIDs to search for
            entity_type: "contact" or "company"
            batch_size: Number of UUIDs per batch query

        Returns:
            List of all matching records
        """

        all_results = []

        # Process in batches to avoid query size limits
        for i in range(0, len(uuids), batch_size):
            batch_uuids = uuids[i:i + batch_size]

            # Build VQL query with IN operator
            condition = VQLCondition(
                field="uuid",
                operator=VQLOperator.IN,
                value=batch_uuids
            )
            filter_obj = VQLFilter(and_=[condition])
            vql_query = VQLQuery(
                filters=filter_obj,
                limit=batch_size,
                offset=0
            )

            if entity_type == "contact":
                response = await self.search_contacts(vql_query)
            else:
                response = await self.search_companies(vql_query)

            data = response.get("data", [])
            all_results.extend(data)

        return all_results

    async def batch_get_contacts_by_uuids(
        self,
        contact_uuids: List[str],
        batch_size: int = 100,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Batch fetch contacts by UUIDs and return as dictionary.

        Args:
            contact_uuids: List of contact UUIDs to fetch
            batch_size: Number of UUIDs per batch query

        Returns:
            Dictionary mapping contact UUID to contact data
        """
        results = await self.batch_search_by_uuids(
            contact_uuids,
            entity_type="contact",
            batch_size=batch_size
        )
        return {item.get("uuid"): item for item in results if item.get("uuid")}

    async def batch_get_companies_by_uuids(
        self,
        company_uuids: List[str],
        batch_size: int = 100,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Batch fetch companies by UUIDs and return as dictionary.

        Args:
            company_uuids: List of company UUIDs to fetch
            batch_size: Number of UUIDs per batch query

        Returns:
            Dictionary mapping company UUID to company data
        """
        results = await self.batch_search_by_uuids(
            company_uuids,
            entity_type="company",
            batch_size=batch_size
        )
        return {item.get("uuid"): item for item in results if item.get("uuid")}

    # ==================== WRITE OPERATIONS ====================
    
    # Contact write methods
    async def create_contact(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new contact via Connectra API.

        Args:
            data: Contact data dictionary

        Returns:
            Created contact data
        """
        return await self._make_request("POST", "/contacts/create", json_data=data)

    async def update_contact(self, uuid: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing contact via Connectra API.

        Args:
            uuid: Contact UUID
            data: Contact update data

        Returns:
            Updated contact data
        """
        return await self._make_request("PUT", f"/contacts/{uuid}", json_data=data)

    async def delete_contact(self, uuid: str) -> None:
        """
        Delete a contact via Connectra API.

        Args:
            uuid: Contact UUID
        """
        await self._make_request("DELETE", f"/contacts/{uuid}")

    async def upsert_contact(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Upsert (create or update) a contact via Connectra API.

        Args:
            data: Contact data dictionary

        Returns:
            Upserted contact data with is_new flag
        """
        return await self._make_request("POST", "/contacts/upsert", json_data=data)

    async def bulk_upsert_contacts(self, contacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Bulk upsert contacts via Connectra API.

        Args:
            contacts: List of contact data dictionaries

        Returns:
            Bulk operation result with created/updated counts
        """
        return await self._make_request("POST", "/contacts/bulk", json_data={"contacts": contacts})

    # Company write methods
    async def create_company(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new company via Connectra API.

        Args:
            data: Company data dictionary

        Returns:
            Created company data
        """
        return await self._make_request("POST", "/companies/create", json_data=data)

    async def update_company(self, uuid: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing company via Connectra API.

        Args:
            uuid: Company UUID
            data: Company update data

        Returns:
            Updated company data
        """
        return await self._make_request("PUT", f"/companies/{uuid}", json_data=data)

    async def delete_company(self, uuid: str) -> None:
        """
        Delete a company via Connectra API.

        Args:
            uuid: Company UUID
        """
        await self._make_request("DELETE", f"/companies/{uuid}")

    async def upsert_company(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Upsert (create or update) a company via Connectra API.

        Args:
            data: Company data dictionary

        Returns:
            Upserted company data with is_new flag
        """
        return await self._make_request("POST", "/companies/upsert", json_data=data)

    async def bulk_upsert_companies(self, companies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Bulk upsert companies via Connectra API.

        Args:
            companies: List of company data dictionaries

        Returns:
            Bulk operation result with created/updated counts
        """
        return await self._make_request("POST", "/companies/bulk", json_data={"companies": companies})

