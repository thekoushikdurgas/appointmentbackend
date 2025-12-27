"""AI-specific configuration for Gemini models."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.utils.logger import get_logger

logger = get_logger(__name__)


class AISettings(BaseSettings):
    """AI-specific settings for Gemini models."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Gemini API Configuration
    GEMINI_API_KEY: str = Field(..., description="Google Gemini API key")
    
    # Model Selection
    GEMINI_MODEL: str = Field(
        default="gemini-1.5-flash",
        description="Default Gemini model to use (gemini-1.5-flash, gemini-1.5-pro, gemini-2.0-flash-exp, etc.)"
    )
    
    # Generation Parameters
    GEMINI_TEMPERATURE: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Temperature for response generation (0.0-2.0)"
    )
    
    GEMINI_MAX_OUTPUT_TOKENS: int = Field(
        default=2048,
        ge=1,
        le=8192,
        description="Maximum number of tokens in the response"
    )
    
    GEMINI_TOP_P: float = Field(
        default=0.95,
        ge=0.0,
        le=1.0,
        description="Top-p sampling parameter"
    )
    
    GEMINI_TOP_K: int = Field(
        default=40,
        ge=1,
        description="Top-k sampling parameter"
    )
    
    # System Instructions
    GEMINI_SYSTEM_INSTRUCTION: str = Field(
        default="""You are NexusAI, a smart CRM assistant for Contact360. You help users with:
- Finding contacts matching specific criteria (titles, locations, industries, etc.)
- Searching for leads in specific industries or locations
- Getting insights about companies
- Answering questions about CRM data
- Natural language queries about contacts and companies

Be helpful, concise, and professional. When users ask about finding contacts or leads, provide guidance on what criteria they can use. If they ask specific questions about data, acknowledge that you can help them search once they provide the criteria.""",
        description="System instruction/persona for the AI assistant"
    )
    
    # Retry Configuration
    GEMINI_MAX_RETRIES: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Maximum number of retries for failed API calls"
    )
    
    GEMINI_RETRY_DELAY: float = Field(
        default=1.0,
        ge=0.1,
        description="Initial delay in seconds for retry (exponential backoff)"
    )
    
    # Rate Limiting (for AI endpoints)
    AI_RATE_LIMIT_REQUESTS: int = Field(
        default=20,
        ge=1,
        description="Maximum requests per time window"
    )
    
    AI_RATE_LIMIT_WINDOW: int = Field(
        default=60,
        ge=1,
        description="Time window in seconds for rate limiting"
    )


@lru_cache()
def get_ai_settings() -> AISettings:
    """Get cached AI settings instance."""
    return AISettings()

