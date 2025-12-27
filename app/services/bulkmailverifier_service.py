"""Service for interacting with BulkMailVerifier API."""

import csv
import io
import re
import time
from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.utils.logger import get_logger, log_error, log_external_api_call

settings = get_settings()
logger = get_logger(__name__)


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
            await self.login()

    def _validate_email_format(self, email: str) -> bool:
        """
        Validate email format before sending to API.
        
        Args:
            email: Email address to validate
            
        Returns:
            True if email format is valid, False otherwise
        """
        if not email or not isinstance(email, str):
            return False
        
        # Basic email regex pattern
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email.strip()):
            return False
        
        # Check length (RFC 5321 limit: 254 characters)
        if len(email) > 254:
            return False
        
        return True

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
        
        if catch_all_str in ("true", "1", "yes"):
            return "catchall"
        elif error or api_status_value == "invalid":
            return "invalid"
        elif api_status_value == "valid":
            return "valid"
        else:
            return "unknown"

    async def login(self) -> Dict[str, str]:
        """
        Authenticate with BulkMailVerifier API and get access token.
        
        Returns:
            Dictionary with 'access' and 'refresh' tokens
            
        Raises:
            HTTPException: If authentication fails
        """
        start_time = time.time()
        logger.debug("BulkMailVerifier login attempt")
        
        if not self.email or not self.password:
            error_msg = (
                "BulkMailVerifier credentials not configured. "
                "Please set BULKMAILVERIFIER_EMAIL and BULKMAILVERIFIER_PASSWORD environment variables."
            )
            logger.error(
                "BulkMailVerifier credentials not configured",
                extra={"context": {"has_email": bool(self.email), "has_password": bool(self.password)}}
            )
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
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                
                duration_ms = (time.time() - start_time) * 1000
                log_external_api_call(
                    service_name="BulkMailVerifier",
                    method="POST",
                    url=url,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                    request_data={"email": self.email},  # Don't log password
                    response_data={"has_access_token": bool(data.get("access"))},
                    logger_name="app.services.bulkmailverifier",
                )
                
                self._access_token = data.get("access")
                self._refresh_token = data.get("refresh")
                
                if not self._access_token:
                    logger.error(
                        "BulkMailVerifier login failed: no access token in response",
                        extra={"context": {"response_keys": list(data.keys())}}
                    )
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Failed to get access token from BulkMailVerifier",
                    )
                
                logger.info(
                    "BulkMailVerifier login successful",
                    extra={"performance": {"duration_ms": duration_ms}}
                )
                
                return {"access": self._access_token, "refresh": self._refresh_token}
                
        except httpx.HTTPStatusError as e:
            duration_ms = (time.time() - start_time) * 1000
            log_external_api_call(
                service_name="BulkMailVerifier",
                method="POST",
                url=url,
                status_code=e.response.status_code,
                duration_ms=duration_ms,
                request_data={"email": self.email},
                error=e,
                logger_name="app.services.bulkmailverifier",
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"BulkMailVerifier authentication failed: {e.response.text}",
            ) from e
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log_error(
                "BulkMailVerifier login failed",
                e,
                "app.services.bulkmailverifier",
                context={"duration_ms": duration_ms, "url": url}
            )
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
        start_time = time.time()
        
        # Validate email format before API call
        if not self._validate_email_format(email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid email format: {email}. Please provide a valid email address.",
            )
        
        logger.debug(
            "Email verification request",
            extra={"context": {"email": email}}
        )
        
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
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                duration_ms = (time.time() - start_time) * 1000
                mapped_status = self._map_verification_status(data)
                
                log_external_api_call(
                    service_name="BulkMailVerifier",
                    method="POST",
                    url=url,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                    request_data={"email": email},
                    response_data={"mapped_status": mapped_status, "result": data.get("result")},
                    logger_name="app.services.bulkmailverifier",
                )
                
                logger.info(
                    "Email verification completed",
                    extra={
                        "context": {
                            "email": email,
                            "status": mapped_status,
                        },
                        "performance": {"duration_ms": duration_ms}
                    }
                )
                
                result = data.copy()
                result["mapped_status"] = mapped_status
                return result
                
        except httpx.TimeoutException as e:
            duration_ms = (time.time() - start_time) * 1000
            log_external_api_call(
                service_name="BulkMailVerifier",
                method="POST",
                url=url,
                status_code=None,
                duration_ms=duration_ms,
                request_data={"email": email},
                error=e,
                logger_name="app.services.bulkmailverifier",
            )
            logger.error(
                "Email verification timeout",
                extra={
                    "context": {
                        "email": email,
                        "timeout_duration_ms": duration_ms,
                        "error_type": "TimeoutException",
                    }
                }
            )
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail=f"Email verification request timed out. Please try again.",
            ) from e
        except httpx.HTTPStatusError as e:
            duration_ms = (time.time() - start_time) * 1000
            
            # Handle 400 Bad Request - client error, not server error
            if e.response.status_code == 400:
                try:
                    error_response = e.response.json()
                    error_message = error_response.get("message") or error_response.get("error") or "Invalid email format or API request"
                except:
                    error_message = e.response.text or "Invalid email format or API request"
                
                log_external_api_call(
                    service_name="BulkMailVerifier",
                    method="POST",
                    url=url,
                    status_code=e.response.status_code,
                    duration_ms=duration_ms,
                    request_data={"email": email},
                    error=e,
                    logger_name="app.services.bulkmailverifier",
                )
                
                logger.warning(
                    "Email verification failed: bad request",
                    extra={
                        "context": {
                            "email": email,
                            "status_code": e.response.status_code,
                            "error_message": error_message,
                            "duration_ms": duration_ms,
                        }
                    }
                )
                
                # Return 400 to client instead of 500
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Email verification failed: {error_message}",
                ) from e
            
            # Handle 429 Too Many Requests - rate limiting
            if e.response.status_code == 429:
                log_external_api_call(
                    service_name="BulkMailVerifier",
                    method="POST",
                    url=url,
                    status_code=e.response.status_code,
                    duration_ms=duration_ms,
                    request_data={"email": email},
                    error=e,
                    logger_name="app.services.bulkmailverifier",
                )
                
                logger.warning(
                    "Email verification failed: rate limit exceeded",
                    extra={
                        "context": {
                            "email": email,
                            "status_code": e.response.status_code,
                            "duration_ms": duration_ms,
                            "error_type": "RateLimitError",
                        }
                    }
                )
                
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Email verification rate limit exceeded. Please try again later.",
                ) from e
            
            # Handle 401 Unauthorized - token might be expired, try to re-authenticate once
            if e.response.status_code == 401:
                try:
                    # Clear token and re-authenticate
                    self._access_token = None
                    await self._ensure_authenticated()
                    
                    # Retry the request
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.post(url, json=payload, headers={
                            "Authorization": f"Bearer {self._access_token}",
                            "Content-Type": "application/json",
                        })
                        response.raise_for_status()
                        data = response.json()
                        
                        duration_ms = (time.time() - start_time) * 1000
                        mapped_status = self._map_verification_status(data)
                        
                        log_external_api_call(
                            service_name="BulkMailVerifier",
                            method="POST",
                            url=url,
                            status_code=response.status_code,
                            duration_ms=duration_ms,
                            request_data={"email": email},
                            response_data={"mapped_status": mapped_status, "result": data.get("result")},
                            logger_name="app.services.bulkmailverifier",
                        )
                        
                        logger.info(
                            "Email verification completed (after retry)",
                            extra={
                                "context": {
                                    "email": email,
                                    "status": mapped_status,
                                },
                                "performance": {"duration_ms": duration_ms}
                            }
                        )
                        
                        result = data.copy()
                        result["mapped_status"] = mapped_status
                        return result
                except Exception as retry_error:
                    # If retry fails, log and raise original error
                    logger.warning(
                        "Retry after re-authentication failed",
                        extra={"context": {"email": email, "retry_error": str(retry_error)}}
                    )
                    # Fall through to raise original error
            
            # For other HTTP errors, log and raise as server error
            log_external_api_call(
                service_name="BulkMailVerifier",
                method="POST",
                url=url,
                status_code=e.response.status_code,
                duration_ms=duration_ms,
                request_data={"email": email},
                error=e,
                logger_name="app.services.bulkmailverifier",
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"BulkMailVerifier verification failed: {e.response.text}",
            ) from e
        except httpx.ConnectError as e:
            duration_ms = (time.time() - start_time) * 1000
            log_external_api_call(
                service_name="BulkMailVerifier",
                method="POST",
                url=url,
                status_code=None,
                duration_ms=duration_ms,
                request_data={"email": email},
                error=e,
                logger_name="app.services.bulkmailverifier",
            )
            logger.error(
                "Email verification failed: connection error",
                extra={
                    "context": {
                        "email": email,
                        "duration_ms": duration_ms,
                        "error_type": "ConnectError",
                        "error_message": str(e),
                    }
                }
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Email verification service is temporarily unavailable. Please try again later.",
            ) from e
        except httpx.RequestError as e:
            duration_ms = (time.time() - start_time) * 1000
            log_external_api_call(
                service_name="BulkMailVerifier",
                method="POST",
                url=url,
                status_code=None,
                duration_ms=duration_ms,
                request_data={"email": email},
                error=e,
                logger_name="app.services.bulkmailverifier",
            )
            logger.error(
                "Email verification failed: request error",
                extra={
                    "context": {
                        "email": email,
                        "duration_ms": duration_ms,
                        "error_type": "RequestError",
                        "error_message": str(e),
                    }
                }
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Email verification service request failed. Please try again later.",
            ) from e
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log_error(
                "Email verification failed: unexpected error",
                e,
                "app.services.bulkmailverifier",
                context={
                    "email": email,
                    "duration_ms": duration_ms,
                    "error_type": type(e).__name__,
                }
            )
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
        start_time = time.time()
        await self._ensure_authenticated()
        
        logger.debug(
            "Uploading file to BulkMailVerifier",
            extra={"context": {"email_count": len(emails)}}
        )
        
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
                    logger.error(
                        "BulkMailVerifier upload failed: no slug in response",
                        extra={"context": {"response_keys": list(data.keys())}}
                    )
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to get slug from BulkMailVerifier upload",
                    )
                
                duration_ms = (time.time() - start_time) * 1000
                log_external_api_call(
                    service_name="BulkMailVerifier",
                    method="POST",
                    url=url,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                    request_data={"email_count": len(emails)},
                    response_data={"slug": slug, "number_of_emails": number_of_emails},
                    logger_name="app.services.bulkmailverifier",
                )
                
                logger.info(
                    "File uploaded to BulkMailVerifier",
                    extra={
                        "context": {
                            "slug": slug,
                            "email_count": number_of_emails,
                        },
                        "performance": {"duration_ms": duration_ms}
                    }
                )
                
                return {
                    "slug": slug,
                    "number_of_emails": number_of_emails,
                    "status": upload_status,
                }
                
        except httpx.HTTPStatusError as e:
            duration_ms = (time.time() - start_time) * 1000
            log_external_api_call(
                service_name="BulkMailVerifier",
                method="POST",
                url=url,
                status_code=e.response.status_code,
                duration_ms=duration_ms,
                request_data={"email_count": len(emails)},
                error=e,
                logger_name="app.services.bulkmailverifier",
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"BulkMailVerifier upload failed: {e.response.text}",
            ) from e
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log_error(
                "File upload to BulkMailVerifier failed",
                e,
                "app.services.bulkmailverifier",
                context={"duration_ms": duration_ms, "email_count": len(emails)}
            )
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
        start_time = time.time()
        await self._ensure_authenticated()
        
        url = f"{self.base_url}/api/file/verify/{slug}/"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
        }
        
        logger.debug(
            "Starting BulkMailVerifier verification",
            extra={"context": {"slug": slug}}
        )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                duration_ms = (time.time() - start_time) * 1000
                log_external_api_call(
                    service_name="BulkMailVerifier",
                    method="POST",
                    url=url,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                    request_data={"slug": slug},
                    response_data=data,
                    logger_name="app.services.bulkmailverifier",
                )
                
                logger.info(
                    "Verification started",
                    extra={
                        "context": {"slug": slug},
                        "performance": {"duration_ms": duration_ms}
                    }
                )
                
                return data
                
        except httpx.HTTPStatusError as e:
            duration_ms = (time.time() - start_time) * 1000
            log_external_api_call(
                service_name="BulkMailVerifier",
                method="POST",
                url=url,
                status_code=e.response.status_code,
                duration_ms=duration_ms,
                request_data={"slug": slug},
                error=e,
                logger_name="app.services.bulkmailverifier",
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"BulkMailVerifier verification start failed: {e.response.text}",
            ) from e
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log_error(
                "Failed to start BulkMailVerifier verification",
                e,
                "app.services.bulkmailverifier",
                context={"duration_ms": duration_ms, "slug": slug}
            )
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
        start_time = time.time()
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
                
                duration_ms = (time.time() - start_time) * 1000
                log_external_api_call(
                    service_name="BulkMailVerifier",
                    method="POST",
                    url=url,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                    request_data={"slug": slug},
                    response_data={"status": data.get("status")},
                    logger_name="app.services.bulkmailverifier",
                )
                
                return data
                
        except httpx.HTTPStatusError as e:
            duration_ms = (time.time() - start_time) * 1000
            log_external_api_call(
                service_name="BulkMailVerifier",
                method="POST",
                url=url,
                status_code=e.response.status_code,
                duration_ms=duration_ms,
                request_data={"slug": slug},
                error=e,
                logger_name="app.services.bulkmailverifier",
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"BulkMailVerifier status check failed: {e.response.text}",
            ) from e
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log_error(
                "Failed to check BulkMailVerifier status",
                e,
                "app.services.bulkmailverifier",
                context={"duration_ms": duration_ms, "slug": slug}
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
        start_time = time.time()
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
                
                duration_ms = (time.time() - start_time) * 1000
                log_external_api_call(
                    service_name="BulkMailVerifier",
                    method="POST",
                    url=url,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                    request_data={"slug": slug},
                    response_data={"has_valid_file": bool(data.get("valid_email_file"))},
                    logger_name="app.services.bulkmailverifier",
                )
                
                return data
                
        except httpx.HTTPStatusError as e:
            duration_ms = (time.time() - start_time) * 1000
            log_external_api_call(
                service_name="BulkMailVerifier",
                method="POST",
                url=url,
                status_code=e.response.status_code,
                duration_ms=duration_ms,
                request_data={"slug": slug},
                error=e,
                logger_name="app.services.bulkmailverifier",
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"BulkMailVerifier get results failed: {e.response.text}",
            ) from e
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log_error(
                "Failed to get BulkMailVerifier results",
                e,
                "app.services.bulkmailverifier",
                context={"duration_ms": duration_ms, "slug": slug}
            )
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
        start_time = time.time()
        await self._ensure_authenticated()
        
        if not file_url or not isinstance(file_url, str) or not file_url.strip():
            logger.warning(
                "Invalid file URL provided for CSV download",
                extra={"context": {"error_context": error_context, "file_url": file_url}}
            )
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
                
                duration_ms = (time.time() - start_time) * 1000
                logger.info(
                    f"CSV download and parse completed: {error_context}",
                    extra={
                        "context": {
                            "error_context": error_context,
                            "email_count": len(emails),
                        },
                        "performance": {"duration_ms": duration_ms}
                    }
                )
                
                return emails
                
        except httpx.HTTPStatusError as e:
            duration_ms = (time.time() - start_time) * 1000
            log_external_api_call(
                service_name="BulkMailVerifier",
                method="GET",
                url=file_url,
                status_code=e.response.status_code,
                duration_ms=duration_ms,
                error=e,
                logger_name="app.services.bulkmailverifier",
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"BulkMailVerifier download failed: {e.response.text}",
            ) from e
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log_error(
                f"Failed to download {error_context}",
                e,
                "app.services.bulkmailverifier",
                context={"duration_ms": duration_ms, "file_url": file_url, "error_context": error_context}
            )
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
        start_time = time.time()
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
                
                duration_ms = (time.time() - start_time) * 1000
                logger.info(
                    "List deleted from BulkMailVerifier",
                    extra={
                        "context": {"slug": slug},
                        "performance": {"duration_ms": duration_ms}
                    }
                )
                
                return data
                
        except httpx.HTTPStatusError as e:
            duration_ms = (time.time() - start_time) * 1000
            # Don't raise exception for delete failures - list may already be deleted
            logger.warning(
                "BulkMailVerifier delete failed (non-critical)",
                extra={
                    "context": {
                        "slug": slug,
                        "status_code": e.response.status_code,
                        "error": str(e),
                    },
                    "performance": {"duration_ms": duration_ms}
                }
            )
            return {"status": "error", "message": str(e)}
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log_error(
                "BulkMailVerifier delete failed",
                e,
                "app.services.bulkmailverifier",
                context={"duration_ms": duration_ms, "slug": slug}
            )
            return {"status": "error", "message": str(e)}

    async def check_credits(self) -> Dict[str, Any]:
        """
        Check available email credits in the BulkMailVerifier account.
        
        Returns:
            Dictionary with credits information
            
        Raises:
            HTTPException: If credits check fails
        """
        start_time = time.time()
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
                    duration_ms = (time.time() - start_time) * 1000
                    log_external_api_call(
                        service_name="BulkMailVerifier",
                        method="POST",
                        url=url,
                        status_code=response.status_code,
                        duration_ms=duration_ms,
                        response_data={"has_credits": "credits" in data},
                        logger_name="app.services.bulkmailverifier",
                    )
                    return data
                except Exception as json_exc:
                    # If not JSON, return as text
                    text_data = response.text
                    duration_ms = (time.time() - start_time) * 1000
                    logger.debug(
                        "BulkMailVerifier credits response is not JSON",
                        extra={
                            "context": {"raw_response": text_data[:200]},
                            "performance": {"duration_ms": duration_ms}
                        }
                    )
                    return {"credits": text_data, "raw_response": text_data}
                
        except httpx.HTTPStatusError as e:
            duration_ms = (time.time() - start_time) * 1000
            log_external_api_call(
                service_name="BulkMailVerifier",
                method="POST",
                url=url,
                status_code=e.response.status_code,
                duration_ms=duration_ms,
                error=e,
                logger_name="app.services.bulkmailverifier",
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"BulkMailVerifier credits check failed: {e.response.text}",
            ) from e
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log_error(
                "Failed to check BulkMailVerifier credits",
                e,
                "app.services.bulkmailverifier",
                context={"duration_ms": duration_ms}
            )
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
        start_time = time.time()
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
                
                duration_ms = (time.time() - start_time) * 1000
                list_count = len(data.get("lists", [])) if isinstance(data, dict) else 0
                log_external_api_call(
                    service_name="BulkMailVerifier",
                    method="POST",
                    url=url,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                    response_data={"list_count": list_count},
                    logger_name="app.services.bulkmailverifier",
                )
                
                return data
                
        except httpx.HTTPStatusError as e:
            duration_ms = (time.time() - start_time) * 1000
            log_external_api_call(
                service_name="BulkMailVerifier",
                method="POST",
                url=url,
                status_code=e.response.status_code,
                duration_ms=duration_ms,
                error=e,
                logger_name="app.services.bulkmailverifier",
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"BulkMailVerifier get lists failed: {e.response.text}",
            ) from e
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log_error(
                "Failed to get BulkMailVerifier lists",
                e,
                "app.services.bulkmailverifier",
                context={"duration_ms": duration_ms}
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
        start_time = time.time()
        await self._ensure_authenticated()
        
        # Validate file_type
        valid_types = ["valid", "invalid", "c-all", "unknown"]
        if file_type not in valid_types:
            logger.warning(
                "Invalid file type requested for download",
                extra={"context": {"file_type": file_type, "valid_types": valid_types}}
            )
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
                duration_ms = (time.time() - start_time) * 1000
                log_external_api_call(
                    service_name="BulkMailVerifier",
                    method="GET",
                    url=url,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                    request_data={"file_type": file_type, "slug": slug},
                    response_data={"content_length": len(csv_content)},
                    logger_name="app.services.bulkmailverifier",
                )
                
                logger.info(
                    "Result file downloaded from BulkMailVerifier",
                    extra={
                        "context": {
                            "file_type": file_type,
                            "slug": slug,
                            "content_length": len(csv_content),
                        },
                        "performance": {"duration_ms": duration_ms}
                    }
                )
                
                return csv_content
                
        except httpx.HTTPStatusError as e:
            duration_ms = (time.time() - start_time) * 1000
            
            # Handle 500 from external service - might be temporary
            if e.response.status_code == 500:
                log_external_api_call(
                    service_name="BulkMailVerifier",
                    method="GET",
                    url=url,
                    status_code=e.response.status_code,
                    duration_ms=duration_ms,
                    request_data={"file_type": file_type, "slug": slug},
                    error=e,
                    logger_name="app.services.bulkmailverifier",
                )
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="BulkMailVerifier service is temporarily unavailable. The result file may not be ready yet. Please try again in a few moments.",
                ) from e
            
            # Handle 404 - file might not be ready yet
            if e.response.status_code == 404:
                log_external_api_call(
                    service_name="BulkMailVerifier",
                    method="GET",
                    url=url,
                    status_code=e.response.status_code,
                    duration_ms=duration_ms,
                    request_data={"file_type": file_type, "slug": slug},
                    error=e,
                    logger_name="app.services.bulkmailverifier",
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Result file not found. The verification might still be processing. Please check the verification status and try again later.",
                ) from e
            
            # Handle 400 - invalid request
            if e.response.status_code == 400:
                log_external_api_call(
                    service_name="BulkMailVerifier",
                    method="GET",
                    url=url,
                    status_code=e.response.status_code,
                    duration_ms=duration_ms,
                    request_data={"file_type": file_type, "slug": slug},
                    error=e,
                    logger_name="app.services.bulkmailverifier",
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid request: {e.response.text or 'Please check the file type and slug parameters.'}",
                ) from e
            
            # Other errors
            log_external_api_call(
                service_name="BulkMailVerifier",
                method="GET",
                url=url,
                status_code=e.response.status_code,
                duration_ms=duration_ms,
                request_data={"file_type": file_type, "slug": slug},
                error=e,
                logger_name="app.services.bulkmailverifier",
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to download result file: {e.response.text}",
            ) from e
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log_error(
                "Failed to download BulkMailVerifier result file",
                e,
                "app.services.bulkmailverifier",
                context={"duration_ms": duration_ms, "file_type": file_type, "slug": slug}
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to download file: {str(e)}",
            ) from e

