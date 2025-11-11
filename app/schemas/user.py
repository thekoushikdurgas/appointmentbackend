"""Pydantic schemas for user authentication and profile management."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# Registration and Login Schemas
class UserRegister(BaseModel):
    """Schema for user registration request."""

    name: str = Field(..., max_length=255, description="User's full name")
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=8, max_length=72, description="User's password (max 72 characters due to bcrypt limitation)")


class UserLogin(BaseModel):
    """Schema for user login request."""

    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")


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
    """Schema for user information in responses."""

    id: str = Field(..., description="User UUID")
    email: str

    model_config = ConfigDict(from_attributes=True)


# Profile Schemas
class NotificationPreferences(BaseModel):
    """Schema for user notification preferences."""

    weeklyReports: Optional[bool] = True
    newLeadAlerts: Optional[bool] = True


class ProfileResponse(BaseModel):
    """Schema for full user profile response."""

    id: str = Field(..., description="User UUID")
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

    user: UserResponse
    last_sign_in_at: Optional[datetime] = None

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

