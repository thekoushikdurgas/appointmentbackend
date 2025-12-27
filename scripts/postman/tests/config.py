"""Configuration management for API testing."""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Hardcoded test credentials (fallback if env vars not set)
DEFAULT_TEST_EMAIL = "test@example.com"
DEFAULT_TEST_PASSWORD = "testpass123"


class TestConfig:
    """Configuration for API testing."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        email: Optional[str] = None,
        password: Optional[str] = None,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        write_key: Optional[str] = None,
        timeout: int = 30,
        retry_max: int = 3,
        retry_backoff: float = 1.5,
        test_mode: str = "hybrid",
        output_dir: Optional[str] = None,
        auto_create_test_user: bool = True,
    ):
        """Initialize test configuration.
        
        Args:
            base_url: API base URL (default: from env or http://127.0.0.1:8000)
            email: Login email for real authentication (default: from env or DEFAULT_TEST_EMAIL)
            password: Login password for real authentication (default: from env or DEFAULT_TEST_PASSWORD)
            access_token: Pre-configured access token (fallback)
            refresh_token: Pre-configured refresh token (fallback)
            write_key: Pre-configured write key for v1 endpoints
            timeout: Request timeout in seconds
            retry_max: Maximum retry attempts
            retry_backoff: Exponential backoff multiplier
            test_mode: Test mode (smoke/comprehensive/hybrid)
            output_dir: Output directory for reports
            auto_create_test_user: Automatically create test user if credentials don't exist
        """
        self.base_url = base_url or os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
        
        # Priority: parameter > environment variable > default
        self.email = email or os.getenv("TEST_EMAIL") or os.getenv("API_TEST_EMAIL") or DEFAULT_TEST_EMAIL
        self.password = password or os.getenv("TEST_PASSWORD") or os.getenv("API_TEST_PASSWORD") or DEFAULT_TEST_PASSWORD
        self.access_token = access_token or os.getenv("ACCESS_TOKEN")
        self.refresh_token = refresh_token or os.getenv("REFRESH_TOKEN")
        self.write_key = write_key or os.getenv("WRITE_KEY")
        
        # Admin credentials (optional, for admin-only endpoints)
        self.admin_email = os.getenv("ADMIN_EMAIL") or os.getenv("TEST_ADMIN_EMAIL")
        self.admin_password = os.getenv("ADMIN_PASSWORD") or os.getenv("TEST_ADMIN_PASSWORD")
        
        self.timeout = timeout
        self.retry_max = retry_max
        self.retry_backoff = retry_backoff
        self.auto_create_test_user = auto_create_test_user
        
        if test_mode not in ["smoke", "comprehensive", "hybrid"]:
            raise ValueError(f"Invalid test_mode: {test_mode}. Must be one of: smoke, comprehensive, hybrid")
        self.test_mode = test_mode
        
        # Set output directory
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path(__file__).parent.parent / "test_reports"
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def has_auth_credentials(self) -> bool:
        """Check if authentication credentials are available."""
        return bool(self.email and self.password)
    
    def has_admin_credentials(self) -> bool:
        """Check if admin authentication credentials are available."""
        return bool(self.admin_email and self.admin_password)
    
    def has_preconfigured_tokens(self) -> bool:
        """Check if pre-configured tokens are available."""
        return bool(self.access_token or self.write_key)
    
    def can_authenticate(self) -> bool:
        """Check if any form of authentication is available."""
        return self.has_auth_credentials() or self.has_preconfigured_tokens()
    
    def validate_credentials(self) -> tuple[bool, Optional[str]]:
        """Validate that credentials are properly configured.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.has_auth_credentials() and not self.has_preconfigured_tokens():
            return False, "No authentication credentials or tokens configured"
        
        if self.email == DEFAULT_TEST_EMAIL and self.password == DEFAULT_TEST_PASSWORD:
            # Using default credentials - warn but allow
            return True, "Using default test credentials - ensure test user exists in database"
        
        return True, None

