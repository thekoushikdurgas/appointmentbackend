"""Pydantic schemas for feature usage tracking."""

from typing import Dict

from pydantic import BaseModel, Field

from app.utils.logger import get_logger

logger = get_logger(__name__)


class FeatureUsageItem(BaseModel):
    """Schema for a single feature usage item."""
    
    used: int = Field(..., description="Current usage count", ge=0)
    limit: int = Field(..., description="Usage limit for this feature", ge=0)


class FeatureUsageResponse(BaseModel):
    """Schema for feature usage response - maps feature names to usage data.
    
    This matches the frontend expectation: Record<Feature, { used: number; limit: number }>
    """
    
    model_config = {"extra": "allow"}
    
    def model_dump(self, **kwargs) -> Dict[str, Dict[str, int]]:
        """Override to return as dict with feature keys."""
        data = super().model_dump(**kwargs)
        # Return all fields that match the feature usage structure
        return {k: v for k, v in data.items() if isinstance(v, dict) and "used" in v and "limit" in v}


class TrackUsageRequest(BaseModel):
    """Schema for tracking feature usage."""
    
    feature: str = Field(..., description="Feature name (e.g., AI_CHAT, EMAIL_FINDER)")
    amount: int = Field(1, description="Amount to increment usage by", ge=1)


class TrackUsageResponse(BaseModel):
    """Schema for track usage response."""
    
    feature: str = Field(..., description="Feature name")
    used: int = Field(..., description="Updated usage count", ge=0)
    limit: int = Field(..., description="Usage limit for this feature", ge=0)
    success: bool = Field(True, description="Whether tracking was successful")
