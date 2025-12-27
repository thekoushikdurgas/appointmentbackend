"""VQL query schemas for API requests."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.core.vql.structures import PopulateConfig, VQLQuery
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Re-export VQLQuery for API use
__all__ = [
    "VQLQuery",
    "VQLCompanyConfig",
    "VQLCountResponse",
    "VQLFilterDataResponse",
    "VQLFilterDefinition",
    "VQLFiltersResponse",
    "VQLKeywordMatch",
    "VQLOrderBy",
    "VQLRangeQuery",
    "VQLTextMatch",
    "VQLWhere",
]

# Type alias for company configuration (same as PopulateConfig)
VQLCompanyConfig = PopulateConfig


class VQLCountResponse(BaseModel):
    """Response schema for VQL count queries."""

    count: int = Field(..., description="Total count of matching records")

    model_config = {"extra": "forbid"}


class VQLFilterDefinition(BaseModel):
    """Schema for a single filter definition."""

    # Use a flexible model that accepts any fields since filter definitions
    # can have various structures depending on the filter type
    model_config = {"extra": "allow"}

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Return filter definition as dictionary."""
        return super().model_dump(**kwargs)


class VQLFiltersResponse(BaseModel):
    """Response schema for VQL filters endpoint."""

    data: List[VQLFilterDefinition] = Field(..., description="List of filter definitions")

    model_config = {"extra": "forbid"}


class VQLFilterDataResponse(BaseModel):
    """Response schema for VQL filter data endpoint."""

    data: List[str] = Field(..., description="List of filter data values")

    model_config = {"extra": "forbid"}


class VQLTextMatch(BaseModel):
    """Schema for VQL text match conditions."""

    text_value: str = Field(..., description="Text value to match")
    filter_key: str = Field(..., description="Field name to filter on")
    search_type: str = Field(default="shuffle", description="Search type (e.g., 'shuffle')")
    fuzzy: bool = Field(default=True, description="Whether to use fuzzy matching")

    model_config = {"extra": "forbid"}


class VQLKeywordMatch(BaseModel):
    """Schema for VQL keyword match conditions."""

    must: Optional[Dict[str, Any]] = Field(None, description="Keyword matches that must match")
    must_not: Optional[Dict[str, Any]] = Field(None, description="Keyword matches that must not match")

    model_config = {"extra": "forbid"}


class VQLRangeQuery(BaseModel):
    """Schema for VQL range query conditions."""

    must: Dict[str, Dict[str, Any]] = Field(..., description="Range conditions that must match")

    model_config = {"extra": "forbid"}


class VQLWhere(BaseModel):
    """Schema for VQL where clause."""

    text_matches: Optional[Dict[str, List[VQLTextMatch]]] = Field(
        None, description="Text match conditions with must/must_not lists"
    )
    keyword_match: Optional[VQLKeywordMatch] = Field(None, description="Keyword match conditions")
    range_query: Optional[VQLRangeQuery] = Field(None, description="Range query conditions")

    model_config = {"extra": "forbid"}


class VQLOrderBy(BaseModel):
    """Schema for VQL order by clause."""

    order_by: str = Field(..., description="Field name to order by")
    order_direction: str = Field(default="asc", description="Order direction: 'asc' or 'desc'")

    model_config = {"extra": "forbid"}

