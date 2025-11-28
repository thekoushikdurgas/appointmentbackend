"""Service for interacting with BulkMailVerifier API."""

import csv
import io
from typing import Dict, List, Optional

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class BulkMailVerifierService:
    """Service for BulkMailVerifier API operations."""

    def __init__(self) -> None:
        """Initialize the service with configuration."""
        self.logger = get_logger(__name__)
        self.base_url = settings.BULKMAILVERIFIER_BASE_URL
        self.email = settings.BULKMAILVERIFIER_EMAIL
        self.password = settings.BULKMAILVERIFIER_PASSWORD
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None

    async def _ensure_authenticated(self) -> None:
        """Ensure we have a valid access token, login if needed."""
        if not self._access_token:
            self.logger.debug("Authentication: Access token not found, initiating login")
            await self.login()
        else:
            self.logger.debug("Authentication: Access token present, skipping login")

    async def login(self) -> Dict[str, str]:
        """
        Authenticate with BulkMailVerifier API and get access token.
        
        Returns:
            Dictionary with 'access' and 'refresh' tokens
            
        Raises:
            HTTPException: If authentication fails
        """
        if not self.email or not self.password:
            error_msg = (
                "BulkMailVerifier credentials not configured. "
                "Please set BULKMAILVERIFIER_EMAIL and BULKMAILVERIFIER_PASSWORD environment variables."
            )
            self.logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg,
            )

        self.logger.info("Login: Authenticating with BulkMailVerifier API: base_url=%s email=%s", self.base_url, self.email)
        
        url = f"{self.base_url}/api/token/"
        payload = {
            "email": self.email,
            "password": self.password,
        }
        self.logger.debug("Login: Request URL=%s payload_keys=%s", url, list(payload.keys()))

        try:
            import time
            start_time = time.time()
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
                elapsed_time = time.time() - start_time
                self.logger.debug("Login: HTTP request completed: status_code=%d elapsed_time=%.2fs", response.status_code, elapsed_time)
                response.raise_for_status()
                data = response.json()
                
                self._access_token = data.get("access")
                self._refresh_token = data.get("refresh")
                token_present = bool(self._access_token)
                refresh_token_present = bool(self._refresh_token)
                
                if not self._access_token:
                    self.logger.error("Login: Authentication succeeded but access token is missing from response")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Failed to get access token from BulkMailVerifier",
                    )
                
                self.logger.info(
                    "Login: Successfully authenticated: access_token_present=%s refresh_token_present=%s elapsed_time=%.2fs",
                    token_present,
                    refresh_token_present,
                    elapsed_time,
                )
                return {"access": self._access_token, "refresh": self._refresh_token}
                
        except httpx.HTTPStatusError as e:
            self.logger.error(
                "Login: BulkMailVerifier login failed: status_code=%d response_text=%s url=%s",
                e.response.status_code,
                e.response.text,
                url,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"BulkMailVerifier authentication failed: {e.response.text}",
            ) from e
        except Exception as e:
            self.logger.exception(
                "Login: Unexpected error during BulkMailVerifier login: error=%s type=%s url=%s",
                str(e),
                type(e).__name__,
                url,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to connect to BulkMailVerifier: {str(e)}",
            ) from e

    async def verify_single_email(self, email: str) -> Dict[str, any]:
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
        await self._ensure_authenticated()
        
        self.logger.info("Verify single email: Verifying email=%s", email)
        
        url = f"{self.base_url}/api/email/verify/"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "email": email,
        }
        self.logger.debug("Verify single email: Request URL=%s email=%s", url, email)

        try:
            import time
            start_time = time.time()
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                elapsed_time = time.time() - start_time
                self.logger.debug(
                    "Verify single email: HTTP request completed: status_code=%d elapsed_time=%.2fs",
                    response.status_code,
                    elapsed_time,
                )
                response.raise_for_status()
                data = response.json()
                
                # Extract key fields (handle different possible field names)
                # API may return either "result" or "status" field - check both
                api_result = data.get("result", "")
                api_status = data.get("status", "")
                # Use result if present, otherwise fallback to status
                api_status_value = (api_result or api_status or "").lower()
                error = data.get("error", False)
                # Check for catch_all in different possible formats
                catch_all = data.get("catch_all") or data.get("catchAll") or data.get("CatchAll") or "False"
                
                # Map API response to our status enum
                # Priority: catch_all > error/invalid > valid > unknown
                catch_all_str = str(catch_all).lower()
                if catch_all_str in ("true", "1", "yes"):
                    mapped_status = "catchall"
                elif error or api_status_value == "invalid":
                    mapped_status = "invalid"
                elif api_status_value == "valid":
                    mapped_status = "valid"
                else:
                    mapped_status = "unknown"
                
                self.logger.info(
                    "Verify single email: Verification completed: email=%s result=%s status=%s api_status_value=%s mapped_status=%s error=%s catch_all=%s elapsed_time=%.2fs",
                    email,
                    api_result,
                    api_status,
                    api_status_value,
                    mapped_status,
                    error,
                    catch_all,
                    elapsed_time,
                )
                self.logger.debug(
                    "Verify single email: Full API response: %s | Extracted fields: result=%s status=%s error=%s catch_all=%s",
                    data,
                    api_result,
                    api_status,
                    error,
                    catch_all,
                )
                
                # Add mapped status to response
                result = data.copy()
                result["mapped_status"] = mapped_status
                
                return result
                
        except httpx.HTTPStatusError as e:
            self.logger.error(
                "Verify single email: BulkMailVerifier verification failed: status_code=%d response_text=%s email=%s url=%s",
                e.response.status_code,
                e.response.text,
                email,
                url,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"BulkMailVerifier verification failed: {e.response.text}",
            ) from e
        except Exception as e:
            self.logger.exception(
                "Verify single email: Unexpected error during verification: error=%s type=%s email=%s url=%s",
                str(e),
                type(e).__name__,
                email,
                url,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to verify email: {str(e)}",
            ) from e

    async def upload_file(self, emails: List[str]) -> Dict[str, any]:
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
        
        self.logger.info("Upload: Preparing to upload %d emails to BulkMailVerifier", len(emails))
        
        # Create CSV file in memory
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(["email"])  # Header
        for email in emails:
            writer.writerow([email])
        
        csv_content = csv_buffer.getvalue()
        csv_size_bytes = len(csv_content.encode("utf-8"))
        csv_buffer.close()
        self.logger.debug(
            "Upload: CSV file created: rows=%d size_bytes=%d size_kb=%.2f",
            len(emails) + 1,  # +1 for header
            csv_size_bytes,
            csv_size_bytes / 1024,
        )
        
        url = f"{self.base_url}/api/file/upload/"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
        }
        self.logger.debug("Upload: Request URL=%s headers_present=%s", url, bool(headers.get("Authorization")))
        
        files = {
            "email_file": ("emails.csv", csv_content.encode("utf-8"), "text/csv"),
        }

        try:
            import time
            start_time = time.time()
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    files=files,
                )
                elapsed_time = time.time() - start_time
                self.logger.debug(
                    "Upload: HTTP request completed: status_code=%d elapsed_time=%.2fs response_size=%d",
                    response.status_code,
                    elapsed_time,
                    len(response.content) if response.content else 0,
                )
                response.raise_for_status()
                data = response.json()
                
                slug = data.get("slug")
                number_of_emails = data.get("number_of_emails")
                upload_status = data.get("status", "unknown")
                
                if not slug:
                    self.logger.error("Upload: Response received but slug is missing: response_keys=%s", list(data.keys()))
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to get slug from BulkMailVerifier upload",
                    )
                
                self.logger.info(
                    "Upload: Successfully uploaded file: slug=%s emails=%d status=%s elapsed_time=%.2fs",
                    slug,
                    number_of_emails,
                    upload_status,
                    elapsed_time,
                )
                self.logger.debug("Upload: Full upload response: %s", data)
                
                return {
                    "slug": slug,
                    "number_of_emails": number_of_emails,
                    "status": upload_status,
                }
                
        except httpx.HTTPStatusError as e:
            self.logger.error(
                "Upload: BulkMailVerifier upload failed: status_code=%d response_text=%s url=%s emails_count=%d",
                e.response.status_code,
                e.response.text,
                url,
                len(emails),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"BulkMailVerifier upload failed: {e.response.text}",
            ) from e
        except Exception as e:
            self.logger.exception(
                "Upload: Unexpected error during BulkMailVerifier upload: error=%s type=%s url=%s emails_count=%d",
                str(e),
                type(e).__name__,
                url,
                len(emails),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload to BulkMailVerifier: {str(e)}",
            ) from e

    async def start_verification(self, slug: str) -> Dict[str, any]:
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
        
        self.logger.info("Start verification: Starting verification for slug=%s", slug)
        
        url = f"{self.base_url}/api/file/verify/{slug}/"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
        }
        self.logger.debug("Start verification: Request URL=%s", url)

        try:
            import time
            start_time = time.time()
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers)
                elapsed_time = time.time() - start_time
                self.logger.debug(
                    "Start verification: HTTP request completed: status_code=%d elapsed_time=%.2fs",
                    response.status_code,
                    elapsed_time,
                )
                response.raise_for_status()
                data = response.json()
                
                file_status = data.get("File Status", data.get("status", "Unknown"))
                self.logger.info(
                    "Start verification: Verification started successfully: slug=%s status=%s elapsed_time=%.2fs",
                    slug,
                    file_status,
                    elapsed_time,
                )
                self.logger.debug("Start verification: Full response: %s", data)
                
                return data
                
        except httpx.HTTPStatusError as e:
            self.logger.error(
                "Start verification: BulkMailVerifier start verification failed: status_code=%d response_text=%s slug=%s url=%s",
                e.response.status_code,
                e.response.text,
                slug,
                url,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"BulkMailVerifier verification start failed: {e.response.text}",
            ) from e
        except Exception as e:
            self.logger.exception(
                "Start verification: Unexpected error starting verification: error=%s type=%s slug=%s url=%s",
                str(e),
                type(e).__name__,
                slug,
                url,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to start verification: {str(e)}",
            ) from e

    async def get_status(self, slug: str) -> Dict[str, any]:
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
        self.logger.debug("Get status: Request URL=%s slug=%s", url, slug)

        try:
            import time
            start_time = time.time()
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers)
                elapsed_time = time.time() - start_time
                self.logger.debug(
                    "Get status: HTTP request completed: status_code=%d elapsed_time=%.3fs",
                    response.status_code,
                    elapsed_time,
                )
                response.raise_for_status()
                data = response.json()
                
                status_value = data.get("status", "unknown")
                total_verified = data.get("total_verified")
                total_emails = data.get("total_emails")
                percentage = data.get("percentage", 0)
                
                self.logger.debug(
                    "Get status: slug=%s status=%s verified=%s/%s percentage=%s%% elapsed_time=%.3fs",
                    slug,
                    status_value,
                    total_verified,
                    total_emails,
                    percentage,
                    elapsed_time,
                )
                
                return data
                
        except httpx.HTTPStatusError as e:
            self.logger.error(
                "Get status: BulkMailVerifier status check failed: status_code=%d response_text=%s slug=%s url=%s",
                e.response.status_code,
                e.response.text,
                slug,
                url,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"BulkMailVerifier status check failed: {e.response.text}",
            ) from e
        except Exception as e:
            self.logger.exception(
                "Get status: Unexpected error checking status: error=%s type=%s slug=%s url=%s",
                str(e),
                type(e).__name__,
                slug,
                url,
            )
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
        
        self.logger.info("Get results: Getting results for slug=%s", slug)
        
        url = f"{self.base_url}/api/file/result/{slug}/"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
        }
        self.logger.debug("Get results: Request URL=%s", url)

        try:
            import time
            start_time = time.time()
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers)
                elapsed_time = time.time() - start_time
                self.logger.debug(
                    "Get results: HTTP request completed: status_code=%d elapsed_time=%.2fs",
                    response.status_code,
                    elapsed_time,
                )
                response.raise_for_status()
                data = response.json()
                
                results_status = data.get("status", "unknown")
                file_urls = {
                    "valid_email_file": bool(data.get("valid_email_file")),
                    "invalid_email_file": bool(data.get("invalid_email_file")),
                    "catchall_email_file": bool(data.get("catchall_email_file")),
                    "unknown_email_file": bool(data.get("unknown_email_file")),
                }
                
                self.logger.info(
                    "Get results: Results retrieved successfully: slug=%s status=%s elapsed_time=%.2fs",
                    slug,
                    results_status,
                    elapsed_time,
                )
                self.logger.debug("Get results: Available file URLs: %s", file_urls)
                self.logger.debug("Get results: Full response keys: %s", list(data.keys()))
                
                return data
                
        except httpx.HTTPStatusError as e:
            self.logger.error(
                "Get results: BulkMailVerifier get results failed: status_code=%d response_text=%s slug=%s url=%s",
                e.response.status_code,
                e.response.text,
                slug,
                url,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"BulkMailVerifier get results failed: {e.response.text}",
            ) from e
        except Exception as e:
            self.logger.exception(
                "Get results: Unexpected error getting results: error=%s type=%s slug=%s url=%s",
                str(e),
                type(e).__name__,
                slug,
                url,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get results: {str(e)}",
            ) from e

    async def download_valid_emails(self, file_url: str) -> List[str]:
        """
        Download and parse the valid emails CSV file.
        
        Args:
            file_url: URL to the valid emails CSV file
            
        Returns:
            List of valid email addresses
            
        Raises:
            HTTPException: If download or parsing fails
        """
        await self._ensure_authenticated()
        
        # Validate file_url parameter
        if not file_url or not isinstance(file_url, str) or not file_url.strip():
            error_msg = "Invalid file_url: URL is required and cannot be None or empty"
            self.logger.error("Download: %s", error_msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg,
            )
        
        self.logger.info("Download: Starting download of valid emails from URL=%s", file_url)
        
        headers = {
            "Authorization": f"Bearer {self._access_token}",
        }
        self.logger.debug("Download: Request headers present=%s", bool(headers.get("Authorization")))

        try:
            import time
            start_time = time.time()
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(file_url, headers=headers)
                elapsed_time = time.time() - start_time
                response_size = len(response.content) if response.content else 0
                self.logger.debug(
                    "Download: HTTP request completed: status_code=%d response_size=%d bytes elapsed_time=%.2fs",
                    response.status_code,
                    response_size,
                    elapsed_time,
                )
                response.raise_for_status()
                
                # Parse CSV content
                csv_content = response.text
                csv_size = len(csv_content)
                csv_reader = csv.DictReader(io.StringIO(csv_content))
                
                valid_emails = []
                rows_parsed = 0
                rows_with_email = 0
                for row in csv_reader:
                    rows_parsed += 1
                    # CSV format: email,result
                    email = row.get("email") or row.get("Email")
                    if email:
                        valid_emails.append(email.strip())
                        rows_with_email += 1
                
                self.logger.info(
                    "Download: Download and parsing completed: valid_emails=%d rows_parsed=%d rows_with_email=%d csv_size=%d bytes elapsed_time=%.2fs",
                    len(valid_emails),
                    rows_parsed,
                    rows_with_email,
                    csv_size,
                    elapsed_time,
                )
                if valid_emails:
                    self.logger.debug("Download: Sample valid emails (first 3): %s", valid_emails[:3])
                return valid_emails
                
        except httpx.HTTPStatusError as e:
            self.logger.error(
                "Download: BulkMailVerifier download failed: status_code=%d response_text=%s file_url=%s",
                e.response.status_code,
                e.response.text,
                file_url,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"BulkMailVerifier download failed: {e.response.text}",
            ) from e
        except Exception as e:
            self.logger.exception(
                "Download: Unexpected error downloading valid emails: error=%s type=%s file_url=%s",
                str(e),
                type(e).__name__,
                file_url,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to download valid emails: {str(e)}",
            ) from e

    async def download_invalid_emails(self, file_url: str) -> List[str]:
        """
        Download and parse the invalid emails CSV file.
        
        Args:
            file_url: URL to the invalid emails CSV file
            
        Returns:
            List of invalid email addresses
            
        Raises:
            HTTPException: If download or parsing fails
        """
        await self._ensure_authenticated()
        
        # Validate file_url parameter
        if not file_url or not isinstance(file_url, str) or not file_url.strip():
            error_msg = "Invalid file_url: URL is required and cannot be None or empty"
            self.logger.error("Download: %s", error_msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg,
            )
        
        self.logger.info("Download: Starting download of invalid emails from URL=%s", file_url)
        
        headers = {
            "Authorization": f"Bearer {self._access_token}",
        }
        self.logger.debug("Download: Request headers present=%s", bool(headers.get("Authorization")))

        try:
            import time
            start_time = time.time()
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(file_url, headers=headers)
                elapsed_time = time.time() - start_time
                response_size = len(response.content) if response.content else 0
                self.logger.debug(
                    "Download: HTTP request completed: status_code=%d response_size=%d bytes elapsed_time=%.2fs",
                    response.status_code,
                    response_size,
                    elapsed_time,
                )
                response.raise_for_status()
                
                # Parse CSV content
                csv_content = response.text
                csv_size = len(csv_content)
                csv_reader = csv.DictReader(io.StringIO(csv_content))
                
                invalid_emails = []
                rows_parsed = 0
                rows_with_email = 0
                for row in csv_reader:
                    rows_parsed += 1
                    # CSV format: email,result
                    email = row.get("email") or row.get("Email")
                    if email:
                        invalid_emails.append(email.strip())
                        rows_with_email += 1
                
                self.logger.info(
                    "Download: Download and parsing completed: invalid_emails=%d rows_parsed=%d rows_with_email=%d csv_size=%d bytes elapsed_time=%.2fs",
                    len(invalid_emails),
                    rows_parsed,
                    rows_with_email,
                    csv_size,
                    elapsed_time,
                )
                if invalid_emails:
                    self.logger.debug("Download: Sample invalid emails (first 3): %s", invalid_emails[:3])
                return invalid_emails
                
        except httpx.HTTPStatusError as e:
            self.logger.error(
                "Download: BulkMailVerifier download failed: status_code=%d response_text=%s file_url=%s",
                e.response.status_code,
                e.response.text,
                file_url,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"BulkMailVerifier download failed: {e.response.text}",
            ) from e
        except Exception as e:
            self.logger.exception(
                "Download: Unexpected error downloading invalid emails: error=%s type=%s file_url=%s",
                str(e),
                type(e).__name__,
                file_url,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to download invalid emails: {str(e)}",
            ) from e

    async def download_catchall_emails(self, file_url: str) -> List[str]:
        """
        Download and parse the catchall emails CSV file.
        
        Args:
            file_url: URL to the catchall emails CSV file
            
        Returns:
            List of catchall email addresses
            
        Raises:
            HTTPException: If download or parsing fails
        """
        await self._ensure_authenticated()
        
        # Validate file_url parameter
        if not file_url or not isinstance(file_url, str) or not file_url.strip():
            error_msg = "Invalid file_url: URL is required and cannot be None or empty"
            self.logger.error("Download: %s", error_msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg,
            )
        
        self.logger.info("Download: Starting download of catchall emails from URL=%s", file_url)
        
        headers = {
            "Authorization": f"Bearer {self._access_token}",
        }
        self.logger.debug("Download: Request headers present=%s", bool(headers.get("Authorization")))

        try:
            import time
            start_time = time.time()
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(file_url, headers=headers)
                elapsed_time = time.time() - start_time
                response_size = len(response.content) if response.content else 0
                self.logger.debug(
                    "Download: HTTP request completed: status_code=%d response_size=%d bytes elapsed_time=%.2fs",
                    response.status_code,
                    response_size,
                    elapsed_time,
                )
                response.raise_for_status()
                
                # Parse CSV content
                csv_content = response.text
                csv_size = len(csv_content)
                csv_reader = csv.DictReader(io.StringIO(csv_content))
                
                catchall_emails = []
                rows_parsed = 0
                rows_with_email = 0
                for row in csv_reader:
                    rows_parsed += 1
                    # CSV format: email,result
                    email = row.get("email") or row.get("Email")
                    if email:
                        catchall_emails.append(email.strip())
                        rows_with_email += 1
                
                self.logger.info(
                    "Download: Download and parsing completed: catchall_emails=%d rows_parsed=%d rows_with_email=%d csv_size=%d bytes elapsed_time=%.2fs",
                    len(catchall_emails),
                    rows_parsed,
                    rows_with_email,
                    csv_size,
                    elapsed_time,
                )
                if catchall_emails:
                    self.logger.debug("Download: Sample catchall emails (first 3): %s", catchall_emails[:3])
                return catchall_emails
                
        except httpx.HTTPStatusError as e:
            self.logger.error(
                "Download: BulkMailVerifier download failed: status_code=%d response_text=%s file_url=%s",
                e.response.status_code,
                e.response.text,
                file_url,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"BulkMailVerifier download failed: {e.response.text}",
            ) from e
        except Exception as e:
            self.logger.exception(
                "Download: Unexpected error downloading catchall emails: error=%s type=%s file_url=%s",
                str(e),
                type(e).__name__,
                file_url,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to download catchall emails: {str(e)}",
            ) from e

    async def download_unknown_emails(self, file_url: str) -> List[str]:
        """
        Download and parse the unknown emails CSV file.
        
        Args:
            file_url: URL to the unknown emails CSV file
            
        Returns:
            List of unknown email addresses
            
        Raises:
            HTTPException: If download or parsing fails
        """
        await self._ensure_authenticated()
        
        # Validate file_url parameter
        if not file_url or not isinstance(file_url, str) or not file_url.strip():
            error_msg = "Invalid file_url: URL is required and cannot be None or empty"
            self.logger.error("Download: %s", error_msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg,
            )
        
        self.logger.info("Download: Starting download of unknown emails from URL=%s", file_url)
        
        headers = {
            "Authorization": f"Bearer {self._access_token}",
        }
        self.logger.debug("Download: Request headers present=%s", bool(headers.get("Authorization")))

        try:
            import time
            start_time = time.time()
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(file_url, headers=headers)
                elapsed_time = time.time() - start_time
                response_size = len(response.content) if response.content else 0
                self.logger.debug(
                    "Download: HTTP request completed: status_code=%d response_size=%d bytes elapsed_time=%.2fs",
                    response.status_code,
                    response_size,
                    elapsed_time,
                )
                response.raise_for_status()
                
                # Parse CSV content
                csv_content = response.text
                csv_size = len(csv_content)
                csv_reader = csv.DictReader(io.StringIO(csv_content))
                
                unknown_emails = []
                rows_parsed = 0
                rows_with_email = 0
                for row in csv_reader:
                    rows_parsed += 1
                    # CSV format: email,result
                    email = row.get("email") or row.get("Email")
                    if email:
                        unknown_emails.append(email.strip())
                        rows_with_email += 1
                
                self.logger.info(
                    "Download: Download and parsing completed: unknown_emails=%d rows_parsed=%d rows_with_email=%d csv_size=%d bytes elapsed_time=%.2fs",
                    len(unknown_emails),
                    rows_parsed,
                    rows_with_email,
                    csv_size,
                    elapsed_time,
                )
                if unknown_emails:
                    self.logger.debug("Download: Sample unknown emails (first 3): %s", unknown_emails[:3])
                return unknown_emails
                
        except httpx.HTTPStatusError as e:
            self.logger.error(
                "Download: BulkMailVerifier download failed: status_code=%d response_text=%s file_url=%s",
                e.response.status_code,
                e.response.text,
                file_url,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"BulkMailVerifier download failed: {e.response.text}",
            ) from e
        except Exception as e:
            self.logger.exception(
                "Download: Unexpected error downloading unknown emails: error=%s type=%s file_url=%s",
                str(e),
                type(e).__name__,
                file_url,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to download unknown emails: {str(e)}",
            ) from e

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
        
        self.logger.info("Delete: Deleting list with slug=%s", slug)
        
        url = f"{self.base_url}/api/file/delete/{slug}/"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
        }
        self.logger.debug("Delete: Request URL=%s", url)

        try:
            import time
            start_time = time.time()
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers)
                elapsed_time = time.time() - start_time
                self.logger.debug(
                    "Delete: HTTP request completed: status_code=%d elapsed_time=%.2fs",
                    response.status_code,
                    elapsed_time,
                )
                response.raise_for_status()
                data = response.json()
                
                delete_status = data.get("status", "unknown")
                self.logger.info(
                    "Delete: List deleted successfully: slug=%s status=%s elapsed_time=%.2fs",
                    slug,
                    delete_status,
                    elapsed_time,
                )
                self.logger.debug("Delete: Full delete response: %s", data)
                return data
                
        except httpx.HTTPStatusError as e:
            self.logger.warning(
                "Delete: BulkMailVerifier delete failed (may already be deleted): status_code=%d response_text=%s slug=%s url=%s",
                e.response.status_code,
                e.response.text,
                slug,
                url,
            )
            # Don't raise exception for delete failures - list may already be deleted
            return {"status": "error", "message": str(e)}
        except Exception as e:
            self.logger.warning(
                "Delete: Unexpected error deleting list: error=%s type=%s slug=%s url=%s",
                str(e),
                type(e).__name__,
                slug,
                url,
            )
            return {"status": "error", "message": str(e)}

    async def check_credits(self) -> Dict[str, any]:
        """
        Check available email credits in the BulkMailVerifier account.
        
        Returns:
            Dictionary with credits information
            
        Raises:
            HTTPException: If credits check fails
        """
        await self._ensure_authenticated()
        
        self.logger.info("Check credits: Checking available email credits")
        
        url = f"{self.base_url}/api/check/credits/"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
        }
        self.logger.debug("Check credits: Request URL=%s", url)

        try:
            import time
            start_time = time.time()
            async with httpx.AsyncClient(timeout=30.0) as client:
                # POST with empty formdata as per Postman collection
                response = await client.post(url, headers=headers, data={})
                elapsed_time = time.time() - start_time
                self.logger.debug(
                    "Check credits: HTTP request completed: status_code=%d elapsed_time=%.2fs",
                    response.status_code,
                    elapsed_time,
                )
                response.raise_for_status()
                
                # Try to parse as JSON first, fallback to text
                try:
                    data = response.json()
                    
                    # Log the credits value and type for debugging
                    credits_value = data.get("credits")
                    credits_type = type(credits_value).__name__ if credits_value is not None else "None"
                    self.logger.debug(
                        "Check credits: Credits value=%s type=%s full_response=%s",
                        credits_value,
                        credits_type,
                        data,
                    )
                    
                    self.logger.info(
                        "Check credits: Credits retrieved successfully: credits=%s type=%s elapsed_time=%.2fs",
                        credits_value,
                        credits_type,
                        elapsed_time,
                    )
                    return data
                except Exception:
                    # If not JSON, return as text
                    text_data = response.text
                    self.logger.info(
                        "Check credits: Credits retrieved (text format): elapsed_time=%.2fs",
                        elapsed_time,
                    )
                    self.logger.debug("Check credits: Text response: %s", text_data)
                    return {"credits": text_data, "raw_response": text_data}
                
        except httpx.HTTPStatusError as e:
            self.logger.error(
                "Check credits: BulkMailVerifier credits check failed: status_code=%d response_text=%s url=%s",
                e.response.status_code,
                e.response.text,
                url,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"BulkMailVerifier credits check failed: {e.response.text}",
            ) from e
        except Exception as e:
            self.logger.exception(
                "Check credits: Unexpected error checking credits: error=%s type=%s url=%s",
                str(e),
                type(e).__name__,
                url,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to check credits: {str(e)}",
            ) from e

    async def get_all_lists(self) -> Dict[str, any]:
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
        
        self.logger.info("Get all lists: Retrieving all uploaded lists")
        
        url = f"{self.base_url}/api/lists/"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
        }
        self.logger.debug("Get all lists: Request URL=%s", url)

        try:
            import time
            start_time = time.time()
            async with httpx.AsyncClient(timeout=30.0) as client:
                # POST with empty formdata as per Postman collection
                response = await client.post(url, headers=headers, data={})
                elapsed_time = time.time() - start_time
                self.logger.debug(
                    "Get all lists: HTTP request completed: status_code=%d elapsed_time=%.2fs",
                    response.status_code,
                    elapsed_time,
                )
                response.raise_for_status()
                data = response.json()
                
                lists_count = len(data.get("lists", []))
                self.logger.info(
                    "Get all lists: Lists retrieved successfully: count=%d elapsed_time=%.2fs",
                    lists_count,
                    elapsed_time,
                )
                self.logger.debug("Get all lists: Full response: %s", data)
                
                return data
                
        except httpx.HTTPStatusError as e:
            self.logger.error(
                "Get all lists: BulkMailVerifier get lists failed: status_code=%d response_text=%s url=%s",
                e.response.status_code,
                e.response.text,
                url,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"BulkMailVerifier get lists failed: {e.response.text}",
            ) from e
        except Exception as e:
            self.logger.exception(
                "Get all lists: Unexpected error getting lists: error=%s type=%s url=%s",
                str(e),
                type(e).__name__,
                url,
            )
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
        
        self.logger.info("Download result file: Downloading %s file for slug=%s", file_type, slug)
        
        url = f"{self.base_url}/api/download/{file_type}/{slug}/"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
        }
        self.logger.debug("Download result file: Request URL=%s", url)

        try:
            import time
            start_time = time.time()
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(url, headers=headers)
                elapsed_time = time.time() - start_time
                response_size = len(response.content) if response.content else 0
                self.logger.debug(
                    "Download result file: HTTP request completed: status_code=%d response_size=%d bytes elapsed_time=%.2fs",
                    response.status_code,
                    response_size,
                    elapsed_time,
                )
                response.raise_for_status()
                
                # Return CSV content as string
                csv_content = response.text
                self.logger.info(
                    "Download result file: File downloaded successfully: file_type=%s slug=%s size=%d bytes elapsed_time=%.2fs",
                    file_type,
                    slug,
                    response_size,
                    elapsed_time,
                )
                return csv_content
                
        except httpx.HTTPStatusError as e:
            self.logger.error(
                "Download result file: BulkMailVerifier download failed: status_code=%d response_text=%s file_type=%s slug=%s url=%s",
                e.response.status_code,
                e.response.text,
                file_type,
                slug,
                url,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"BulkMailVerifier download failed: {e.response.text}",
            ) from e
        except Exception as e:
            self.logger.exception(
                "Download result file: Unexpected error downloading file: error=%s type=%s file_type=%s slug=%s url=%s",
                str(e),
                type(e).__name__,
                file_type,
                slug,
                url,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to download file: {str(e)}",
            ) from e

