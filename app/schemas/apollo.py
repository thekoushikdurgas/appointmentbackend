"""Pydantic schemas for Apollo.io URL analysis."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


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

