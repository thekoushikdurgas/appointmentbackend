"""Service for interacting with IcyPeas email search API."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


class IcyPeasService:
    """Service for IcyPeas email finder API.

    Two-step process:
    1. POST /api/email-search -> returns search id
    2. Poll /api/bulk-single-searchs/read with id until status is DEBITED
    """

    def __init__(self) -> None:
        self.base_url = (settings.ICYPEAS_BASE_URL or "https://app.icypeas.com/api").rstrip("/")
        self.api_key = settings.ICYPEAS_API_KEY

        if not self.api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "IcyPeas API key not configured. "
                    "Please set ICYPEAS_API_KEY environment variable."
                ),
            )

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _initiate_search(
        self,
        first_name: str,
        last_name: str,
        domain: str,
    ) -> Optional[str]:
        """Initiate IcyPeas email search and return search id if successful."""
        url = f"{self.base_url}/email-search"
        payload = {
            "firstname": first_name,
            "lastname": last_name,
            "domainOrCompany": domain,
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.post(url, json=payload, headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPStatusError as exc:
                raise HTTPException(
                    status_code=exc.response.status_code,
                    detail=f"IcyPeas email-search failed: {exc.response.text}",
                ) from exc
            except Exception as exc:  # pragma: no cover
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to reach IcyPeas: {str(exc)}",
                ) from exc

        if not data.get("success"):
            # Check if it's an insufficient credits error - if so, raise to fail fast
            validation_errors = data.get("validationErrors") or []
            for error in validation_errors:
                if error.get("type") == "InsufficientCredits":
                    raise HTTPException(
                        status_code=status.HTTP_402_PAYMENT_REQUIRED,
                        detail="IcyPeas insufficient credits - service unavailable",
                    )
            
            return None

        item = data.get("item") or {}
        search_id = item.get("_id")
        return search_id

    async def _poll_result(
        self,
        search_id: str,
        max_attempts: int = 5,
        poll_interval: float = 0.3,  # Start with shorter interval
    ) -> Optional[Dict[str, Any]]:
        """Poll IcyPeas for search results using exponential backoff.
        
        Returns as soon as status is FOUND or DEBITED (optimized for speed).
        Uses exponential backoff: 0.3s, 0.5s, 0.8s, 1.0s, 1.5s
        """
        url = f"{self.base_url}/bulk-single-searchs/read"
        payload = {"id": search_id}

        # Exponential backoff intervals (in seconds)
        backoff_intervals = [0.3, 0.5, 0.8, 1.0, 1.5]

        async with httpx.AsyncClient(timeout=15.0) as client:
            for attempt in range(max_attempts):
                try:
                    resp = await client.post(url, json=payload, headers=self._headers())
                    resp.raise_for_status()
                    data = resp.json()
                except httpx.HTTPStatusError as exc:
                    raise HTTPException(
                        status_code=exc.response.status_code,
                        detail=f"IcyPeas bulk-single-searchs/read failed: {exc.response.text}",
                    ) from exc
                except Exception as exc:  # pragma: no cover
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Failed to reach IcyPeas: {str(exc)}",
                    ) from exc

                if not data.get("success"):
                    # If not successful, wait and retry
                    if attempt < max_attempts - 1:
                        interval = backoff_intervals[min(attempt, len(backoff_intervals) - 1)]
                        await asyncio.sleep(interval)
                    continue

                items = data.get("items") or []
                if not items:
                    if attempt < max_attempts - 1:
                        interval = backoff_intervals[min(attempt, len(backoff_intervals) - 1)]
                        await asyncio.sleep(interval)
                    continue

                item = items[0]
                status_value = item.get("status")
                results = item.get("results") or {}

                # Return immediately if status is FOUND or DEBITED (both indicate results are ready)
                if status_value in ("FOUND", "DEBITED"):
                    # Extract best email from results
                    return self._extract_best_email(results)

                # Status is NONE or other, wait and retry
                if attempt < max_attempts - 1:
                    interval = backoff_intervals[min(attempt, len(backoff_intervals) - 1)]
                    await asyncio.sleep(interval)

            # Max attempts reached
            return None

    @staticmethod
    def _extract_best_email(results: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract the best email from IcyPeas results based on certainty."""
        emails = (results or {}).get("emails") or []
        if not emails:
            return None

        # Define ordering for certainty
        certainty_rank = {
            "ultra_sure": 3,
            "sure": 2,
            "probable": 1,
        }

        def score(email_obj: Dict[str, Any]) -> int:
            certainty = (email_obj.get("certainty") or "").lower()
            return certainty_rank.get(certainty, 0)

        best = max(emails, key=score)
        if score(best) == 0:
            # No meaningful certainty
            return None

        return best

    async def search_email(
        self,
        first_name: str,
        last_name: str,
        domain: str,
        max_attempts: int = 5,
        poll_interval: float = 0.3,  # Optimized: exponential backoff starting at 0.3s
    ) -> Optional[Dict[str, Any]]:
        """Public helper to perform full IcyPeas email search flow.

        Returns best email object or None.
        Uses optimized exponential backoff polling for faster response.
        """
        search_id = await self._initiate_search(first_name, last_name, domain)
        if not search_id:
            return None

        return await self._poll_result(
            search_id=search_id,
            max_attempts=max_attempts,
            poll_interval=poll_interval,
        )
