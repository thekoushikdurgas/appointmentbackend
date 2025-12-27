"""Authentication handler for API testing."""

import time
import uuid
from typing import Optional, Dict, Any
import requests
from .config import TestConfig


class AuthHandler:
    """Handles authentication for API testing."""
    
    def __init__(self, config: TestConfig):
        """Initialize authentication handler.
        
        Args:
            config: Test configuration
        """
        self.config = config
        self.base_url = config.base_url
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.write_key: Optional[str] = config.write_key
        self.token_expires_at: Optional[float] = None
        self._authenticated = False
        self._last_refresh_attempt: Optional[float] = None
        self._refresh_backoff_seconds = 1.0
        
        # Admin authentication (separate from regular user)
        self.admin_access_token: Optional[str] = None
        self.admin_refresh_token: Optional[str] = None
        self.admin_token_expires_at: Optional[float] = None
        self._admin_authenticated = False
    
    def authenticate(self) -> bool:
        """Authenticate using real login or pre-configured tokens.
        
        Returns:
            True if authentication successful, False otherwise
        """
        # Try real authentication first
        if self.config.has_auth_credentials():
            # Ensure test user exists if auto-create is enabled
            if self.config.auto_create_test_user:
                self.ensure_test_user_exists()
            
            if self._login():
                return True
        
        # Fallback to pre-configured tokens
        if self.config.has_preconfigured_tokens():
            self.access_token = self.config.access_token
            self.refresh_token = self.config.refresh_token
            self.write_key = self.config.write_key
            self._authenticated = True
            return True
        
        return False
    
    def ensure_test_user_exists(self) -> bool:
        """Create test user if it doesn't exist.
        
        Returns:
            True if user exists or was created, False otherwise
        """
        # First, try to login to see if user exists
        if self._login():
            return True
        
        # If login fails, try to register the user
        try:
            # Normalize base_url (remove trailing slash)
            base_url = self.base_url.rstrip('/')
            url = f"{base_url}/api/v1/auth/register/"
            # Generate unique email if using default
            email = self.config.email
            if email == "test@example.com":
                email = f"test_{uuid.uuid4().hex[:8]}@example.com"
                self.config.email = email
            
            payload = {
                "name": "Test User",
                "email": email,
                "password": self.config.password,
                "geolocation": None
            }
            
            response = requests.post(
                url,
                json=payload,
                headers={"Origin": "localhost:3000"},
                timeout=self.config.timeout
            )
            
            # 201 = created, 422 = validation error (might mean user exists)
            if response.status_code in [201, 422]:
                # Try login again after registration attempt
                return self._login()
            
            return False
        except Exception as e:
            # If registration fails, just try login (user might exist)
            return self._login()
    
    def _login(self) -> bool:
        """Perform real login via API.
        
        Returns:
            True if login successful, False otherwise
        """
        try:
            # Normalize base_url (remove trailing slash)
            base_url = self.base_url.rstrip('/')
            url = f"{base_url}/api/v1/auth/login/"
            payload = {
                "email": self.config.email,
                "password": self.config.password,
                "geolocation": None
            }
            
            response = requests.post(
                url,
                json=payload,
                headers={"Origin": "localhost:3000"},
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                
                # Assume token expires in 1 hour (adjust based on your JWT settings)
                self.token_expires_at = time.time() + 3600
                self._authenticated = True
                return True
            
            return False
        except Exception as e:
            print(f"Login failed: {e}")
            return False
    
    def refresh_access_token(self) -> bool:
        """Refresh the access token using refresh token with exponential backoff.
        
        Returns:
            True if refresh successful, False otherwise
        """
        if not self.refresh_token:
            return False
        
        # Implement exponential backoff to avoid rapid retries
        current_time = time.time()
        if self._last_refresh_attempt:
            time_since_last = current_time - self._last_refresh_attempt
            if time_since_last < self._refresh_backoff_seconds:
                # Too soon to retry
                return False
        
        self._last_refresh_attempt = current_time
        
        try:
            # Normalize base_url (remove trailing slash)
            base_url = self.base_url.rstrip('/')
            url = f"{base_url}/api/v1/auth/refresh/"
            payload = {
                "refresh_token": self.refresh_token
            }
            
            response = requests.post(
                url,
                json=payload,
                headers={"Origin": "localhost:3000"},
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token", self.refresh_token)
                
                # Assume token expires in 1 hour
                self.token_expires_at = time.time() + 3600
                # Reset backoff on success
                self._refresh_backoff_seconds = 1.0
                return True
            else:
                # Increase backoff on failure (max 60 seconds)
                self._refresh_backoff_seconds = min(self._refresh_backoff_seconds * 2, 60.0)
                return False
        except Exception as e:
            print(f"Token refresh failed: {e}")
            # Increase backoff on exception
            self._refresh_backoff_seconds = min(self._refresh_backoff_seconds * 2, 60.0)
            return False
    
    def get_or_refresh_token(self) -> Optional[str]:
        """Get valid token, refreshing if expired.
        
        Returns:
            Access token string or None if unavailable
        """
        # Check if token is expired or about to expire (within 5 minutes)
        if self.token_expires_at and time.time() >= (self.token_expires_at - 300):
            if not self.refresh_access_token():
                # If refresh fails, try to re-authenticate
                if self.config.has_auth_credentials():
                    self._login()
        
        return self.access_token
    
    def get_auth_headers(self, api_version: str, method: str, endpoint: str = "", requires_admin: bool = False, requires_auth: bool = False) -> Dict[str, str]:
        """Get authentication headers for a request.
        
        Args:
            api_version: API version (v1, v2, v3, v4, global)
            method: HTTP method
            endpoint: Endpoint path (optional, used to detect VQL endpoints)
            requires_admin: Whether this endpoint requires admin authentication
            requires_auth: Whether this endpoint requires regular user authentication
        
        Returns:
            Dictionary of headers
        """
        headers = {
            "Origin": "localhost:3000",
        }
        
        # Use admin token if required and available
        if requires_admin and self._admin_authenticated and self.admin_access_token:
            headers["Authorization"] = f"Bearer {self.admin_access_token}"
            return headers
        
        # If endpoint requires authentication, always add Bearer token
        if requires_auth:
            token = self.get_or_refresh_token()
            if token:
                headers["Authorization"] = f"Bearer {token}"
                return headers
        
        # Auto-detect endpoints that require authentication based on patterns
        # These endpoints use get_current_user or get_current_super_admin in their route definitions
        # Match exact endpoint paths that require auth (not sub-paths)
        if endpoint == "/api/v1/auth/user-info/" or endpoint.endswith("/api/v1/auth/user-info/"):
            token = self.get_or_refresh_token()
            if token:
                headers["Authorization"] = f"Bearer {token}"
                return headers
        elif endpoint == "/api/v1/billing/" or endpoint.endswith("/api/v1/billing/"):
            # Only the root billing endpoint requires auth, not /billing/plans/ etc.
            token = self.get_or_refresh_token()
            if token:
                headers["Authorization"] = f"Bearer {token}"
                return headers
        elif "/api/v1/health/vql/stats" in endpoint:
            token = self.get_or_refresh_token()
            if token:
                headers["Authorization"] = f"Bearer {token}"
                return headers
        elif "/api/v1/billing/admin/" in endpoint:
            # Admin endpoints require super admin auth, but we'll use regular token if admin not available
            # The endpoint will return 403 if not admin, which is better than 401
            token = self.get_or_refresh_token()
            if token:
                headers["Authorization"] = f"Bearer {token}"
                return headers
        
        # v1 VQL POST endpoints use Bearer token (not X-Write-Key)
        is_vql_endpoint = api_version == "v1" and method == "POST" and ('/query' in endpoint or '/count' in endpoint) and ('/contacts/' in endpoint or '/companies/' in endpoint)
        
        if is_vql_endpoint or api_version in ["v2", "v3", "v4"]:
            # Get or refresh token
            token = self.get_or_refresh_token()
            if token:
                headers["Authorization"] = f"Bearer {token}"
        
        # v1 non-VQL write operations (if any remain) would use X-Write-Key
        # But currently all v1 write operations are removed (moved to Connectra)
        # So this is kept for backward compatibility only
        elif api_version == "v1" and method in ["POST", "PUT", "DELETE", "PATCH"]:
            if self.write_key:
                headers["X-Write-Key"] = self.write_key
        
        return headers
    
    def authenticate_admin(self) -> bool:
        """Authenticate as admin user.
        
        Returns:
            True if admin authentication successful, False otherwise
        """
        if not self.config.has_admin_credentials():
            return False
        
        try:
            # Normalize base_url (remove trailing slash)
            base_url = self.base_url.rstrip('/')
            url = f"{base_url}/api/v1/auth/login/"
            payload = {
                "email": self.config.admin_email,
                "password": self.config.admin_password,
                "geolocation": None
            }
            
            response = requests.post(
                url,
                json=payload,
                headers={"Origin": "localhost:3000"},
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                self.admin_access_token = data.get("access_token")
                self.admin_refresh_token = data.get("refresh_token")
                self.admin_token_expires_at = time.time() + 3600
                self._admin_authenticated = True
                return True
            
            return False
        except Exception as e:
            print(f"Admin login failed: {e}")
            return False
    
    def handle_401(self) -> bool:
        """Handle 401 Unauthorized response by refreshing token.
        
        Returns:
            True if token was refreshed, False otherwise
        """
        if self.refresh_token:
            return self.refresh_access_token()
        elif self.config.has_auth_credentials():
            return self._login()
        return False
    
    def is_authenticated(self) -> bool:
        """Check if authentication is active."""
        return self._authenticated and (self.access_token or self.write_key)
    
    def is_admin_authenticated(self) -> bool:
        """Check if admin authentication is active."""
        return self._admin_authenticated and bool(self.admin_access_token)

