"""Pydantic schemas for Apollo.io URL analysis."""

from typing import Any, Generic, List, Optional, TypeVar, Union

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.schemas.contacts import ContactListItem, ContactSimpleItem

T = TypeVar("T")


class ApolloUrlAnalysisRequest(BaseModel):
    """Schema for Apollo URL analysis request."""

    url: str = Field(..., description="Apollo.io URL to analyze")


class ParameterDetail(BaseModel):
    """Schema for individual parameter details."""

    name: str = Field(..., description="Parameter name")
    values: List[str] = Field(..., description="List of parameter values found in URL")
    description: str = Field(..., description="Human-readable description of the parameter")
    category: str = Field(..., description="Category this parameter belongs to")


class ParameterCategory(BaseModel):
    """Schema for a category of parameters."""

    name: str = Field(..., description="Category name")
    parameters: List[ParameterDetail] = Field(..., description="Parameters in this category")
    total_parameters: int = Field(..., description="Total number of parameters in this category")


class UrlStructure(BaseModel):
    """Schema for URL structure breakdown."""

    base_url: str = Field(..., description="Base URL (e.g., https://app.apollo.io)")
    hash_path: Optional[str] = Field(None, description="Hash path (e.g., /people)")
    query_string: Optional[str] = Field(None, description="Full query string")
    has_query_params: bool = Field(..., description="Whether the URL has query parameters")


class AnalysisStatistics(BaseModel):
    """Schema for analysis statistics."""

    total_parameters: int = Field(..., description="Total number of unique parameters found")
    total_parameter_values: int = Field(..., description="Total number of parameter values (including duplicates)")
    categories_used: int = Field(..., description="Number of parameter categories used")
    categories: List[str] = Field(..., description="List of category names found")


class ApolloUrlAnalysisResponse(BaseModel):
    """Schema for Apollo URL analysis response."""

    url: str = Field(..., description="Original URL that was analyzed")
    url_structure: UrlStructure = Field(..., description="URL structure breakdown")
    categories: List[ParameterCategory] = Field(..., description="Categorized parameters")
    statistics: AnalysisStatistics = Field(..., description="Analysis statistics")
    raw_parameters: dict[str, List[str]] = Field(
        ..., description="Raw parameter dictionary (parameter name -> list of values)"
    )

    model_config = ConfigDict(from_attributes=True)


class UnmappedParameter(BaseModel):
    """Schema for unmapped Apollo parameter details."""

    name: str = Field(..., description="Parameter name from Apollo URL")
    values: List[str] = Field(..., description="Parameter values from Apollo URL")
    category: str = Field(..., description="Apollo parameter category")
    reason: str = Field(..., description="Reason why this parameter was not mapped")


class UnmappedCategory(BaseModel):
    """Schema for unmapped Apollo category details."""

    name: str = Field(..., description="Category name from Apollo URL")
    parameters: List[UnmappedParameter] = Field(..., description="Unmapped parameters in this category")
    total_parameters: int = Field(..., description="Total unmapped parameters in this category")


class MappingSummary(BaseModel):
    """Schema for Apollo URL to contacts filter mapping summary."""

    total_apollo_parameters: int = Field(..., description="Total number of parameters in Apollo URL")
    mapped_parameters: int = Field(..., description="Number of parameters successfully mapped to filters")
    unmapped_parameters: int = Field(..., description="Number of parameters that could not be mapped")
    mapped_parameter_names: List[str] = Field(..., description="Names of parameters that were mapped")
    unmapped_parameter_names: List[str] = Field(..., description="Names of parameters that were not mapped")


class ApolloContactsSearchResponse(BaseModel, Generic[T]):
    """Schema for Apollo contacts search response with mapping metadata."""

    next: Optional[str] = Field(None, description="URL for next page of results")
    previous: Optional[str] = Field(None, description="URL for previous page of results")
    results: List[T] = Field(..., description="List of contact results")
    
    # Apollo mapping metadata
    apollo_url: str = Field(..., description="Original Apollo URL that was converted")
    mapping_summary: MappingSummary = Field(..., description="Summary of parameter mapping")
    unmapped_categories: List[UnmappedCategory] = Field(
        ..., description="Categories and parameters that were not mapped to filters"
    )

    model_config = ConfigDict(from_attributes=True)


class ApolloWebSocketRequest(BaseModel):
    """Schema for WebSocket request messages."""

    action: str = Field(..., description="Action to perform: analyze, search_contacts, count_contacts, get_uuids")
    request_id: str = Field(..., description="Client-generated request ID for tracking responses")
    data: dict[str, Any] = Field(..., description="Request payload matching REST API structure")


class ApolloWebSocketResponse(BaseModel):
    """Schema for WebSocket response messages."""

    request_id: str = Field(..., description="Echo of client's request_id")
    action: str = Field(..., description="Echo of action from request")
    status: str = Field(..., description="Response status: success or error")
    data: Optional[dict[str, Any]] = Field(None, description="Response payload (present when status=success)")
    error: Optional[dict[str, Any]] = Field(None, description="Error details (present when status=error)")
