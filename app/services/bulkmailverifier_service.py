"""Service for interacting with BulkMailVerifier API."""

import csv
import io
from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings

settings = get_settings()


class BulkMailVerifierService:
    """Service for BulkMailVerifier API operations."""

    def __init__(self) -> None:
        """Initialize the service with configuration."""
        self.base_url = settings.BULKMAILVERIFIER_BASE_URL
        self.email = settings.BULKMAILVERIFIER_EMAIL
        self.password = settings.BULKMAILVERIFIER_PASSWORD
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None

    async def _ensure_authenticated(self) -> None:
        """Ensure we have a valid access token, login if needed."""
        if not self._access_token:
            print(f"[BULKMAILVERIFIER] No access token found, logging in...")
            await self.login()
        else:
            print(f"[BULKMAILVERIFIER] Using existing access token")

    def _map_verification_status(self, data: Dict) -> str:
        """
        Map API response to verification status.
        
        Priority: catch_all > error/invalid > valid > unknown
        
        Args:
            data: API response dictionary
            
        Returns:
            Mapped status string: "catchall", "invalid", "valid", or "unknown"
        """
        api_result = data.get("result", "")
        api_status = data.get("status", "")
        api_status_value = (api_result or api_status or "").lower()
        error = data.get("error", False)
        catch_all = data.get("catch_all") or data.get("catchAll") or data.get("CatchAll") or "False"
        catch_all_str = str(catch_all).lower()
        
        print(f"[MAP_STATUS] Mapping status: result={api_result}, status={api_status}, error={error}, catch_all={catch_all_str}")
        
        if catch_all_str in ("true", "1", "yes"):
            print(f"[MAP_STATUS] Mapped to: catchall")
            return "catchall"
        elif error or api_status_value == "invalid":
            print(f"[MAP_STATUS] Mapped to: invalid")
            return "invalid"
        elif api_status_value == "valid":
            print(f"[MAP_STATUS] Mapped to: valid")
            return "valid"
        else:
            print(f"[MAP_STATUS] Mapped to: unknown")
            return "unknown"

    async def login(self) -> Dict[str, str]:
        """
        Authenticate with BulkMailVerifier API and get access token.
        
        Returns:
            Dictionary with 'access' and 'refresh' tokens
            
        Raises:
            HTTPException: If authentication fails
        """
        print(f"[BULKMAILVERIFIER] Attempting login to {self.base_url}/api/token/")
        if not self.email or not self.password:
            error_msg = (
                "BulkMailVerifier credentials not configured. "
                "Please set BULKMAILVERIFIER_EMAIL and BULKMAILVERIFIER_PASSWORD environment variables."
            )
            print(f"[BULKMAILVERIFIER] ✗ Login failed: credentials not configured")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg,
            )

        url = f"{self.base_url}/api/token/"
        payload = {
            "email": self.email,
            "password": self.password,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                print(f"[BULKMAILVERIFIER] Sending login request to {url}")
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                
                self._access_token = data.get("access")
                self._refresh_token = data.get("refresh")
                
                if not self._access_token:
                    print(f"[BULKMAILVERIFIER] ✗ Login failed: No access token in response")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Failed to get access token from BulkMailVerifier",
                    )
                
                print(f"[BULKMAILVERIFIER] ✓ Login successful, access token obtained (length: {len(self._access_token) if self._access_token else 0})")
                return {"access": self._access_token, "refresh": self._refresh_token}
                
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"BulkMailVerifier authentication failed: {e.response.text}",
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to connect to BulkMailVerifier: {str(e)}",
            ) from e

    async def verify_single_email(self, email: str) -> Dict[str, Any]:
        """
        Verify a single email address using the direct verification endpoint.
        
        Args:
            email: Email address to verify
            
        Returns:
            Dictionary with verification result including:
            - status: "valid", "invalid", "catchall", or "unknown"
            - error: Boolean indicating if there was an error
            - catch_all: String "True" or "False"
            - Other fields from API response
            
        Raises:
            HTTPException: If verification fails
        """
        print(f"[BULKMAILVERIFIER] Verifying single email: {email}")
        await self._ensure_authenticated()
        
        url = f"{self.base_url}/api/email/verify/"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "email": email,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                print(f"[BULKMAILVERIFIER] Sending verification request to {url} for {email}")
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                print(f"[BULKMAILVERIFIER] Received response for {email}: {data}")
                
                mapped_status = self._map_verification_status(data)
                result = data.copy()
                result["mapped_status"] = mapped_status
                print(f"[BULKMAILVERIFIER] Final result for {email}: mapped_status={mapped_status}")
                return result
                
        except httpx.HTTPStatusError as e:
            print(f"[BULKMAILVERIFIER] ✗ HTTP error verifying {email}: {e.response.status_code} - {e.response.text}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"BulkMailVerifier verification failed: {e.response.text}",
            ) from e
        except Exception as e:
            print(f"[BULKMAILVERIFIER] ✗ Exception verifying {email}: {type(e).__name__}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to verify email: {str(e)}",
            ) from e

    async def upload_file(self, emails: List[str]) -> Dict[str, Any]:
        """
        Upload a CSV file with emails to BulkMailVerifier.
        
        Args:
            emails: List of email addresses to verify
            
        Returns:
            Dictionary with 'slug' and 'number_of_emails'
            
        Raises:
            HTTPException: If upload fails
        """
        await self._ensure_authenticated()
        
        # Create CSV file in memory
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(["email"])  # Header
        for email in emails:
            writer.writerow([email])
        
        csv_content = csv_buffer.getvalue()
        csv_buffer.close()
        
        url = f"{self.base_url}/api/file/upload/"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
        }
        
        files = {
            "email_file": ("emails.csv", csv_content.encode("utf-8"), "text/csv"),
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    files=files,
                )
                response.raise_for_status()
                data = response.json()
                
                slug = data.get("slug")
                number_of_emails = data.get("number_of_emails")
                upload_status = data.get("status", "unknown")
                
                if not slug:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to get slug from BulkMailVerifier upload",
                    )
                
                return {
                    "slug": slug,
                    "number_of_emails": number_of_emails,
                    "status": upload_status,
                }
                
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"BulkMailVerifier upload failed: {e.response.text}",
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload to BulkMailVerifier: {str(e)}",
            ) from e

    async def start_verification(self, slug: str) -> Dict[str, Any]:
        """
        Start the verification process for an uploaded file.
        
        Args:
            slug: The slug returned from upload_file
            
        Returns:
            Dictionary with verification status
            
        Raises:
            HTTPException: If verification start fails
        """
        await self._ensure_authenticated()
        
        url = f"{self.base_url}/api/file/verify/{slug}/"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                return data
                
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"BulkMailVerifier verification start failed: {e.response.text}",
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to start verification: {str(e)}",
            ) from e

    async def get_status(self, slug: str) -> Dict[str, Any]:
        """
        Get the verification status for an uploaded file.
        
        Args:
            slug: The slug returned from upload_file
            
        Returns:
            Dictionary with status information including:
            - status: "Verifying" or "Completed"
            - total_verified: Number of emails verified
            - total_emails: Total number of emails
            - percentage: Percentage complete
            
        Raises:
            HTTPException: If status check fails
        """
        await self._ensure_authenticated()
        
        url = f"{self.base_url}/api/file/status/{slug}/"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                return data
                
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"BulkMailVerifier status check failed: {e.response.text}",
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to check status: {str(e)}",
            ) from e

    async def get_results(self, slug: str) -> Dict[str, str]:
        """
        Get the result file URLs for a completed verification.
        
        Args:
            slug: The slug returned from upload_file
            
        Returns:
            Dictionary with file URLs:
            - valid_email_file: URL to valid emails CSV
            - invalid_email_file: URL to invalid emails CSV
            - catchall_email_file: URL to catchall emails CSV
            - unknown_email_file: URL to unknown emails CSV
            
        Raises:
            HTTPException: If getting results fails
        """
        await self._ensure_authenticated()
        
        url = f"{self.base_url}/api/file/result/{slug}/"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                return data
                
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"BulkMailVerifier get results failed: {e.response.text}",
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get results: {str(e)}",
            ) from e

    async def _download_and_parse_csv(self, file_url: str, error_context: str) -> List[str]:
        """
        Download and parse a CSV file from BulkMailVerifier.
        
        Args:
            file_url: URL to the CSV file
            error_context: Context for error messages (e.g., "valid emails")
            
        Returns:
            List of email addresses from the CSV
            
        Raises:
            HTTPException: If download or parsing fails
        """
        await self._ensure_authenticated()
        
        if not file_url or not isinstance(file_url, str) or not file_url.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file_url: URL is required and cannot be None or empty",
            )
        
        headers = {"Authorization": f"Bearer {self._access_token}"}

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(file_url, headers=headers)
                response.raise_for_status()
                
                csv_reader = csv.DictReader(io.StringIO(response.text))
                emails = []
                for row in csv_reader:
                    email = row.get("email") or row.get("Email")
                    if email:
                        emails.append(email.strip())
                
                return emails
                
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"BulkMailVerifier download failed: {e.response.text}",
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to download {error_context}: {str(e)}",
            ) from e

    async def download_valid_emails(self, file_url: str) -> List[str]:
        """Download and parse the valid emails CSV file."""
        return await self._download_and_parse_csv(file_url, "valid emails")

    async def download_invalid_emails(self, file_url: str) -> List[str]:
        """Download and parse the invalid emails CSV file."""
        return await self._download_and_parse_csv(file_url, "invalid emails")

    async def download_catchall_emails(self, file_url: str) -> List[str]:
        """Download and parse the catchall emails CSV file."""
        return await self._download_and_parse_csv(file_url, "catchall emails")

    async def download_unknown_emails(self, file_url: str) -> List[str]:
        """Download and parse the unknown emails CSV file."""
        return await self._download_and_parse_csv(file_url, "unknown emails")

    async def delete_list(self, slug: str) -> Dict[str, str]:
        """
        Delete an uploaded file/list from BulkMailVerifier.
        
        Args:
            slug: The slug returned from upload_file
            
        Returns:
            Dictionary with deletion status
            
        Raises:
            HTTPException: If deletion fails
        """
        await self._ensure_authenticated()
        
        url = f"{self.base_url}/api/file/delete/{slug}/"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                return data
                
        except httpx.HTTPStatusError as e:
            # Don't raise exception for delete failures - list may already be deleted
            return {"status": "error", "message": str(e)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def check_credits(self) -> Dict[str, Any]:
        """
        Check available email credits in the BulkMailVerifier account.
        
        Returns:
            Dictionary with credits information
            
        Raises:
            HTTPException: If credits check fails
        """
        await self._ensure_authenticated()
        
        url = f"{self.base_url}/api/check/credits/"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # POST with empty formdata as per Postman collection
                response = await client.post(url, headers=headers, data={})
                response.raise_for_status()
                
                # Try to parse as JSON first, fallback to text
                try:
                    data = response.json()
                    return data
                except Exception:
                    # If not JSON, return as text
                    text_data = response.text
                    return {"credits": text_data, "raw_response": text_data}
                
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"BulkMailVerifier credits check failed: {e.response.text}",
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to check credits: {str(e)}",
            ) from e

    async def get_all_lists(self) -> Dict[str, Any]:
        """
        Get all uploaded email lists from BulkMailVerifier.
        
        Returns:
            Dictionary with 'lists' array containing list information:
            - slug: Unique identifier
            - status: Verification status (Completed, Verifying, etc.)
            - total_emails: Total number of emails
            - total_verified: Number of verified emails
            - retry: Retry count
            - valid_emails: Number of valid emails
            - invalid_emails: Number of invalid emails
            - catchall_emails: Number of catchall emails
            - unknown_emails: Number of unknown emails
            
        Raises:
            HTTPException: If getting lists fails
        """
        await self._ensure_authenticated()
        
        url = f"{self.base_url}/api/lists/"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # POST with empty formdata as per Postman collection
                response = await client.post(url, headers=headers, data={})
                response.raise_for_status()
                data = response.json()
                
                return data
                
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"BulkMailVerifier get lists failed: {e.response.text}",
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get lists: {str(e)}",
            ) from e

    async def download_result_file(self, file_type: str, slug: str) -> str:
        """
        Download a result file from BulkMailVerifier.
        
        Args:
            file_type: Type of file to download - one of: "valid", "invalid", "c-all", "unknown"
            slug: The slug returned from upload_file
            
        Returns:
            CSV content as string
            
        Raises:
            HTTPException: If download fails
        """
        await self._ensure_authenticated()
        
        # Validate file_type
        valid_types = ["valid", "invalid", "c-all", "unknown"]
        if file_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file_type. Must be one of: {', '.join(valid_types)}",
            )
        
        url = f"{self.base_url}/api/download/{file_type}/{slug}/"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                
                # Return CSV content as string
                csv_content = response.text
                return csv_content
                
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"BulkMailVerifier download failed: {e.response.text}",
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to download file: {str(e)}",
            ) from e

