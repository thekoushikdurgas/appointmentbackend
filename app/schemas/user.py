"""Pydantic schemas for user authentication and profile management."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# Geolocation Data Schema
class GeolocationData(BaseModel):
    """Schema for IP geolocation data from frontend."""

    ip: Optional[str] = None
    continent: Optional[str] = None
    continent_code: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    region: Optional[str] = None
    region_name: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    zip: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    timezone: Optional[str] = None
    offset: Optional[int] = None
    currency: Optional[str] = None
    isp: Optional[str] = None
    org: Optional[str] = None
    asname: Optional[str] = None
    reverse: Optional[str] = None
    device: Optional[str] = None
    proxy: Optional[bool] = None
    hosting: Optional[bool] = None


# Registration and Login Schemas
class UserRegister(BaseModel):
    """Schema for user registration request."""

    name: str = Field(..., max_length=255, description="User's full name")
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=8, max_length=72, description="User's password (max 72 characters due to bcrypt limitation)")
    geolocation: Optional[GeolocationData] = Field(None, description="IP geolocation data from frontend")


class UserLogin(BaseModel):
    """Schema for user login request."""

    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")
    geolocation: Optional[GeolocationData] = Field(None, description="IP geolocation data from frontend")


# Token Schemas
class TokenResponse(BaseModel):
    """Schema for token response."""

    access_token: str
    refresh_token: str
    user: "UserResponse"


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request."""

    refresh_token: str = Field(..., description="Refresh token")


class RefreshTokenResponse(BaseModel):
    """Schema for refresh token response."""

    access_token: str
    refresh_token: str


# User Response Schemas
class UserResponse(BaseModel):
    """Schema for user information in responses (for login/register)."""

    uuid: str = Field(..., description="User UUID")
    email: str

    model_config = ConfigDict(from_attributes=True)


class SessionUserResponse(BaseModel):
    """Schema for user information in session responses (includes last_sign_in_at)."""

    uuid: str = Field(..., description="User UUID")
    email: str
    last_sign_in_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Profile Schemas
class NotificationPreferences(BaseModel):
    """Schema for user notification preferences."""

    weeklyReports: Optional[bool] = True
    newLeadAlerts: Optional[bool] = True


class ProfileResponse(BaseModel):
    """Schema for full user profile response."""

    uuid: str = Field(..., description="User UUID")
    name: Optional[str] = None
    email: str
    role: Optional[str] = "Member"
    avatar_url: Optional[str] = None
    is_active: bool = True
    job_title: Optional[str] = None
    bio: Optional[str] = None
    timezone: Optional[str] = None
    notifications: Optional[NotificationPreferences] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProfileUpdate(BaseModel):
    """Schema for partial profile update."""

    name: Optional[str] = Field(None, max_length=255)
    job_title: Optional[str] = Field(None, max_length=255)
    bio: Optional[str] = None
    timezone: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = None
    notifications: Optional[NotificationPreferences] = None
    role: Optional[str] = Field(None, max_length=50)


# Session Schema
class SessionResponse(BaseModel):
    """Schema for current session information."""

    user: SessionUserResponse

    model_config = ConfigDict(from_attributes=True)


# Logout Schema
class LogoutRequest(BaseModel):
    """Schema for logout request."""

    refresh_token: Optional[str] = Field(None, description="Refresh token to blacklist")


class LogoutResponse(BaseModel):
    """Schema for logout response."""

    message: str


# Registration Response (includes message)
class RegisterResponse(BaseModel):
    """Schema for registration response."""

    access_token: str
    refresh_token: str
    user: UserResponse
    message: str


# Avatar Upload Response
class AvatarUploadResponse(BaseModel):
    """Schema for avatar upload response."""

    avatar_url: str
    profile: ProfileResponse
    message: str


# Super Admin User Management Schemas
class UserListItem(BaseModel):
    """Schema for user list item (for Super Admin)."""

    uuid: str = Field(..., description="User UUID")
    email: str
    name: Optional[str] = None
    role: Optional[str] = None
    credits: int = Field(default=0, description="User credits")
    subscription_plan: Optional[str] = None
    subscription_period: Optional[str] = None
    subscription_status: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    last_sign_in_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    """Schema for user list response."""

    users: list[UserListItem] = Field(default_factory=list, description="List of users")
    total: int = Field(..., description="Total number of users")


class UpdateUserRoleRequest(BaseModel):
    """Schema for updating user role."""

    role: str = Field(..., description="New role (SuperAdmin, Admin, FreeUser, ProUser)")


class UpdateUserCreditsRequest(BaseModel):
    """Schema for updating user credits."""

    credits: int = Field(..., ge=0, description="New credit amount")


class UserStatsResponse(BaseModel):
    """Schema for user statistics."""

    total_users: int
    active_users: int
    users_by_role: dict[str, int] = Field(default_factory=dict)
    users_by_plan: dict[str, int] = Field(default_factory=dict)


# User History Schemas
class UserHistoryItem(BaseModel):
    """Schema for a single user history record."""

    id: int
    user_id: str = Field(..., description="User ID (UUID format)")
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    event_type: str
    ip: Optional[str] = None
    continent: Optional[str] = None
    continent_code: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    region: Optional[str] = None
    region_name: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    zip: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None
    isp: Optional[str] = None
    org: Optional[str] = None
    asname: Optional[str] = None
    reverse: Optional[str] = None
    device: Optional[str] = None
    proxy: Optional[bool] = None
    hosting: Optional[bool] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class UserHistoryListResponse(BaseModel):
    """Schema for paginated user history list response."""

    items: list[UserHistoryItem] = Field(default_factory=list, description="List of user history records")
    total: int = Field(..., description="Total number of records")
    limit: int = Field(..., description="Limit applied")
    offset: int = Field(..., description="Offset applied")


# User Activity Schemas
class UserActivityItem(BaseModel):
    """Schema for a single user activity record."""

    id: int
    user_id: str = Field(..., description="User ID (UUID format)")
    service_type: str = Field(..., description="Service type: linkedin or email")
    action_type: str = Field(..., description="Action type: search or export")
    status: str = Field(..., description="Status: success, failed, or partial")
    request_params: Optional[dict] = Field(None, description="Request parameters as JSON object")
    result_count: int = Field(default=0, description="Number of results returned")
    result_summary: Optional[dict] = Field(None, description="Summary of results as JSON object")
    error_message: Optional[str] = Field(None, description="Error message if the activity failed")
    ip_address: Optional[str] = Field(None, description="IP address of the user")
    user_agent: Optional[str] = Field(None, description="User-Agent string from the request")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class UserActivityListResponse(BaseModel):
    """Schema for paginated user activity list response."""

    items: list[UserActivityItem] = Field(default_factory=list, description="List of user activity records")
    total: int = Field(..., description="Total number of records")
    limit: int = Field(..., description="Limit applied")
    offset: int = Field(..., description="Offset applied")


class ActivityStatsResponse(BaseModel):
    """Schema for user activity statistics."""

    total_activities: int = Field(..., description="Total number of activities")
    by_service_type: dict[str, int] = Field(default_factory=dict, description="Count by service type")
    by_action_type: dict[str, int] = Field(default_factory=dict, description="Count by action type")
    by_status: dict[str, int] = Field(default_factory=dict, description="Count by status")
    recent_activities: int = Field(default=0, description="Activities in the last 24 hours")