"""Service for interacting with Truelist API."""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import Any, Dict, Iterable, Optional

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.schemas.email import EmailVerificationStatus
from app.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)

# In-memory cache for Truelist responses (LRU cache)
_truelist_cache: OrderedDict[str, tuple[Dict[str, Dict[str, Any]], float]] = OrderedDict()
_cache_max_size = 10000  # Cache up to 10k email verifications
_cache_ttl_seconds = 3600  # 1 hour TTL

# Shared httpx client for connection pooling (reused across requests)
_shared_http_client: Optional[httpx.AsyncClient] = None


class TruelistService:
    """Lightweight client for Truelist email verification APIs."""

    def __init__(self) -> None:
        self.base_url = (settings.TRUELIST_BASE_URL or "").rstrip("/")
        self.api_key = settings.TRUELIST_API_KEY

        if not self.api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "Truelist API key not configured. "
                    "Please set TRUELIST_API_KEY environment variable."
                ),
            )
        if not self.base_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Truelist base URL not configured. Please set TRUELIST_BASE_URL.",
            )

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": self.api_key,
            "Accept": "application/json",
        }

    def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create shared HTTP client for connection reuse."""
        global _shared_http_client
        if _shared_http_client is None or _shared_http_client.is_closed:
            _shared_http_client = httpx.AsyncClient(
                timeout=0.8,  # OPTIMIZED: Reduced to 0.8s for fast response (0.5s verification + 0.3s overhead)
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
            )
        return _shared_http_client

    @staticmethod
    def _map_status(email_state: str | None, email_sub_state: str | None) -> str:
        """
        Map Truelist email_state/email_sub_state to normalized status.
        
        Truelist states:
        - "ok" -> VALID
        - "invalid" -> INVALID
        - "risky" with "accept_all" -> CATCHALL (catchall domain)
        - "risky" with other sub_states -> UNKNOWN (needs review)
        - "unknown" or "pending" -> UNKNOWN
        - "disposable" or "role" in sub_state -> INVALID
        """
        state = (email_state or "").lower()
        sub_state = (email_sub_state or "").lower()

        if state == "ok":
            return EmailVerificationStatus.VALID.value
        if "invalid" in state:
            return EmailVerificationStatus.INVALID.value
        # Handle catchall: risky state with accept_all sub_state
        if state == "risky" and "accept_all" in sub_state:
            return EmailVerificationStatus.CATCHALL.value
        if "disposable" in sub_state or "role" in sub_state:
            return EmailVerificationStatus.INVALID.value
        if "unknown" in state or "pending" in state:
            return EmailVerificationStatus.UNKNOWN.value
        # Default risky or other states to UNKNOWN
        return EmailVerificationStatus.UNKNOWN.value

    async def verify_single_email(self, email: str) -> Dict[str, Any]:
        """
        Verify a single email via /api/v1/verify_inline.
        """
        results = await self.verify_emails([email])
        return results.get(email.lower().strip(), {"mapped_status": EmailVerificationStatus.UNKNOWN.value})

    async def verify_emails(self, emails: Iterable[str]) -> Dict[str, Dict[str, Any]]:
        """
        Verify up to 51 emails per call; chunk requests accordingly.
        Uses in-memory cache to avoid re-verifying same emails.
        """
        email_list = [e.strip() for e in emails if e and e.strip()]
        if not email_list:
            return {}

        # Check cache first
        global _truelist_cache
        aggregated: Dict[str, Dict[str, Any]] = {}
        emails_to_verify = []
        cache_hits = 0
        current_time = time.time()
        
        for email in email_list:
            email_key = email.lower().strip()
            if email_key in _truelist_cache:
                cached_result, timestamp = _truelist_cache[email_key]
                if current_time - timestamp < _cache_ttl_seconds:
                    # Cache hit - use cached result
                    aggregated[email_key] = cached_result
                    cache_hits += 1
                    # Move to end (LRU)
                    _truelist_cache.move_to_end(email_key)
                    continue
                else:
                    # Expired - remove from cache
                    del _truelist_cache[email_key]
            
            # Cache miss - need to verify
            emails_to_verify.append(email)
        
        # If all cached, return early
        if not emails_to_verify:
            return aggregated

        url = f"{self.base_url}/api/v1/verify_inline"
        headers = self._headers()

        client = self._get_http_client()
        for i in range(0, len(emails_to_verify), 51):
            chunk = emails_to_verify[i : i + 51]
            params = {"email": " ".join(chunk)}
            
            try:
                resp = await client.post(url, params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPStatusError as exc:
                raise HTTPException(
                    status_code=exc.response.status_code,
                    detail=f"Truelist verification failed: {exc.response.text}",
                ) from exc
            except Exception as exc:  # pragma: no cover
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to reach Truelist: {str(exc)}",
                ) from exc

            # Extract emails array from response
            truelist_emails_returned = data.get("emails", [])
            for item in truelist_emails_returned:
                address = (item.get("address") or "").lower().strip()
                email_state = item.get("email_state")
                email_sub_state = item.get("email_sub_state")
                mapped_status = self._map_status(email_state, email_sub_state)
                
                item["mapped_status"] = mapped_status
                aggregated[address] = item
                
                # Store in cache with LRU eviction
                while len(_truelist_cache) >= _cache_max_size:
                    _truelist_cache.popitem(last=False)  # Remove oldest
                _truelist_cache[address] = (item, time.time())

        return aggregated

    async def list_batches(self) -> Dict[str, Any]:
        """Retrieve all batches for the account."""
        url = f"{self.base_url}/api/v1/batches"
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(url, headers=self._headers())
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as exc:
                raise HTTPException(
                    status_code=exc.response.status_code,
                    detail=f"Truelist list batches failed: {exc.response.text}",
                ) from exc

    async def get_batch(self, batch_id: str) -> Dict[str, Any]:
        """Retrieve batch details."""
        url = f"{self.base_url}/api/v1/batches/{batch_id}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(url, headers=self._headers())
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as exc:
                raise HTTPException(
                    status_code=exc.response.status_code,
                    detail=f"Truelist get batch failed: {exc.response.text}",
                ) from exc

    async def download_csv(self, csv_url: str) -> str:
        """Download CSV content from a given URL."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.get(csv_url, headers=self._headers())
                resp.raise_for_status()
                return resp.text
            except httpx.HTTPStatusError as exc:
                raise HTTPException(
                    status_code=exc.response.status_code,
                    detail=f"Truelist download failed: {exc.response.text}",
                ) from exc
