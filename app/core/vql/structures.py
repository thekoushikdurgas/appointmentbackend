"""VQL data structures for query representation."""

from __future__ import annotations

from enum import Enum
from typing import Any, List, Optional, Union

from pydantic import BaseModel, Field

from app.utils.logger import get_logger

logger = get_logger(__name__)


class VQLOperator(str, Enum):
    """Supported VQL operators for filtering."""

    EQ = "eq"  # Equal
    NE = "ne"  # Not equal
    GT = "gt"  # Greater than
    GTE = "gte"  # Greater than or equal
    LT = "lt"  # Less than
    LTE = "lte"  # Less than or equal
    IN = "in"  # In list
    NIN = "nin"  # Not in list
    CONTAINS = "contains"  # Array contains or string contains
    NCONTAINS = "ncontains"  # Array doesn't contain or string doesn't contain
    EXISTS = "exists"  # Field exists (not null)
    NEXISTS = "nexists"  # Field doesn't exist (is null)


class VQLCondition(BaseModel):
    """A single filter condition with field, operator, and value."""

    field: str = Field(..., description="Field name to filter on")
    operator: VQLOperator = Field(..., description="Operator to apply")
    value: Any = Field(..., description="Value to compare against")

    model_config = {"extra": "forbid"}


class VQLFilter(BaseModel):
    """Filter group supporting AND/OR logic."""

    and_: Optional[List[Union[VQLCondition, "VQLFilter"]]] = Field(
        None, alias="and", description="AND group of conditions/filters"
    )
    or_: Optional[List[Union[VQLCondition, "VQLFilter"]]] = Field(
        None, alias="or", description="OR group of conditions/filters"
    )

    model_config = {"extra": "forbid", "populate_by_name": True}


# Update forward reference
VQLFilter.model_rebuild()


class PopulateConfig(BaseModel):
    """Configuration for populating related entities."""

    populate: bool = Field(default=False, description="Whether to populate related entity")
    select_columns: Optional[List[str]] = Field(
        None, description="Specific columns to select from related entity"
    )

    model_config = {"extra": "forbid"}


class VQLQuery(BaseModel):
    """Complete VQL query with filters, selection, and pagination."""

    filters: Optional[VQLFilter] = Field(None, description="Filter conditions")
    select_columns: Optional[List[str]] = Field(
        None, description="Columns to select from main entity"
    )
    company_config: Optional[PopulateConfig] = Field(
        None, description="Configuration for populating company data"
    )
    contact_config: Optional[PopulateConfig] = Field(
        None, description="Configuration for populating contact data"
    )
    limit: Optional[int] = Field(None, ge=1, description="Maximum number of results")
    offset: int = Field(default=0, ge=0, description="Offset for pagination")
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_direction: Optional[str] = Field(
        default="asc", pattern="^(asc|desc)$", description="Sort direction (asc/desc)"
    )

    model_config = {"extra": "forbid"}

