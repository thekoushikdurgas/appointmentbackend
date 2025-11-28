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


class ParameterValueWithCount(BaseModel):
    """Schema for a parameter value with its contact count."""

    value: str = Field(..., description="Parameter value")
    count: int = Field(..., description="Number of contacts matching this specific value")


class ParameterDetailWithCount(BaseModel):
    """Schema for individual parameter details with contact counts."""

    name: str = Field(..., description="Parameter name")
    values: List[ParameterValueWithCount] = Field(..., description="List of parameter values with their counts")
    description: str = Field(..., description="Human-readable description of the parameter")
    category: str = Field(..., description="Category this parameter belongs to")
    count: int = Field(..., description="Total number of contacts matching this parameter (all values combined)")


class ParameterCategoryWithCount(BaseModel):
    """Schema for a category of parameters with contact counts."""

    name: str = Field(..., description="Category name")
    parameters: List[ParameterDetailWithCount] = Field(..., description="Parameters in this category with counts")
    total_parameters: int = Field(..., description="Total number of parameters in this category")
    count: int = Field(..., description="Total number of contacts matching any parameter in this category")


class ApolloUrlAnalysisWithCountResponse(BaseModel):
    """Schema for Apollo URL analysis response with contact counts."""

    url: str = Field(..., description="Original URL that was analyzed")
    url_structure: UrlStructure = Field(..., description="URL structure breakdown")
    categories: List[ParameterCategoryWithCount] = Field(..., description="Categorized parameters with counts")
    statistics: AnalysisStatistics = Field(..., description="Analysis statistics")
    raw_parameters: dict[str, List[str]] = Field(
        ..., description="Raw parameter dictionary (parameter name -> list of values)"
    )

    model_config = ConfigDict(from_attributes=True)