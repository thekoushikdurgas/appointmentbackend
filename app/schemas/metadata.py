"""Metadata schemas shared across contact and company responses."""

from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.utils.logger import get_logger

logger = get_logger(__name__)


class ContactMetadataOut(BaseModel):
    """Expose enriched metadata fields linked to a contact."""

    uuid: str
    linkedin_url: Optional[str] = None
    linkedin_sales_url: Optional[str] = None
    facebook_url: Optional[str] = None
    twitter_url: Optional[str] = None
    website: Optional[str] = None
    work_direct_phone: Optional[str] = None
    home_phone: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    other_phone: Optional[str] = None
    stage: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

