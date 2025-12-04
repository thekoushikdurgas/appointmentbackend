"""Application configuration objects and helpers."""

from functools import lru_cache
from typing import List, Optional
from urllib.parse import quote_plus

from pydantic import AnyHttpUrl, Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.logging import get_logger, log_function_call


logger = get_logger(__name__)


class Settings(BaseSettings):
    """Runtime configuration sourced from environment and defaults."""
    # Project
    PROJECT_NAME: str = "Contact360 API"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "Async FastAPI backend for Contact360 - Contact Management System"
    ENVIRONMENT: str = "development"  # development | staging | production
    DEBUG: bool = True

    # API
    API_V1_STR: str = "/api"
    API_V1_PREFIX: str = "/api/v1"
    API_V2_PREFIX: str = "/api/v2"
    API_V3_PREFIX: str = "/api/v3"
    API_V4_PREFIX: str = "/api/v4"
    DOCS_URL: Optional[str] = "/docs"
    REDOC_URL: Optional[str] = "/redoc"

    # Database
    POSTGRES_USER: str = Field("postgres", alias="POSTGRES_USER")
    POSTGRES_PASS: str = Field("", alias="POSTGRES_PASS")
    POSTGRES_HOST: str = Field(
        "ayan.calum4mgqi7l.us-east-1.rds.amazonaws.com", alias="POSTGRES_HOST"
    )
    POSTGRES_PORT: int = Field(5432, alias="POSTGRES_PORT")
    POSTGRES_DB: str = Field("postgres", alias="POSTGRES_DB")
    DATABASE_ECHO: bool = Field(False, alias="DATABASE_ECHO")
    DATABASE_POOL_SIZE: int = 25  # Increased for large datasets
    DATABASE_MAX_OVERFLOW: int = 50  # Increased for high concurrency
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 1800
    DATABASE_POOL_PRE_PING: bool = True  # Verify connections before using
    DATABASE_POOL_RESET_ON_RETURN: str = "commit"  # Better connection reuse
    # Connection pool monitoring
    ENABLE_POOL_MONITORING: bool = Field(True, alias="ENABLE_POOL_MONITORING")  # Enable pool statistics tracking
    POOL_MONITORING_INTERVAL: int = Field(60, alias="POOL_MONITORING_INTERVAL")  # Log pool stats every N seconds
    DATABASE_URL: Optional[str] = None
    DATABASE_REPLICA_URL: Optional[str] = Field(None, alias="DATABASE_REPLICA_URL", description="Optional replica database URL for read operations")
    USE_REPLICA: bool = Field(False, alias="USE_REPLICA", description="Whether to use replica database for read operations")
    # Query compression and caching
    ENABLE_QUERY_COMPRESSION: bool = True  # Enable PostgreSQL query compression
    QUERY_CACHE_TTL: int = 300  # Query result cache TTL in seconds
    ENABLE_QUERY_CACHING: bool = False  # Enable in-memory query caching
    ENABLE_QUERY_MONITORING: bool = True  # Enable query performance monitoring
    SLOW_QUERY_THRESHOLD: float = 1.0  # Threshold in seconds for logging slow queries
    USE_APPROXIMATE_COUNTS: bool = False  # Use approximate counts for very large unfiltered queries
    APOLLO_COUNT_MAX_CONCURRENT: int = 50  # Maximum concurrent count queries for Apollo analyze/count endpoint
    @field_validator("DEBUG", mode="before")
    @classmethod
    def normalize_debug(cls, value):
        """Normalize string debug flags into Boolean values."""
        logger.debug("Entering Settings.normalize_debug value=%r", value)
        if isinstance(value, bool) or value is None:
            logger.debug("Exiting Settings.normalize_debug result=%r", value)
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "on"}:
                logger.debug("Exiting Settings.normalize_debug result=True")
                return True
            if normalized in {"false", "0", "no", "off"}:
                logger.debug("Exiting Settings.normalize_debug result=False")
                return False
        default = cls.model_fields["DEBUG"].default
        logger.debug("Exiting Settings.normalize_debug result(default)=%r", default)
        return default


    # Security
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"
    CONTACTS_WRITE_KEY: str = "change-this-write-key"
    COMPANIES_WRITE_KEY: str = "change-this-write-key"

    # CORS
    # Allowed origins for browser-based clients (frontend applications)
    # - Local development (Next.js on port 3000)
    # - Backend API by IP (54.87.173.234)
    # - Frontend EC2 IP (23.22.149.143)
    # - Production domain (contact360.io)
    ALLOWED_ORIGINS: List[AnyHttpUrl] = [
        # Local development
        AnyHttpUrl("http://localhost:3000"),
        AnyHttpUrl("http://127.0.0.1:3000"),
        AnyHttpUrl("http://127.0.0.1:8000"),
        # Backend API (by IP)
        AnyHttpUrl("http://54.87.173.234"),
        AnyHttpUrl("http://54.87.173.234:8000"),
        # Frontend EC2 IP (Contact360 frontend host)
        AnyHttpUrl("http://23.22.149.143"),
        AnyHttpUrl("http://23.22.149.143:3000"),
        AnyHttpUrl("http://3.95.58.90"),
        # Production domain (Contact360)
        AnyHttpUrl("http://contact360.io"),
        AnyHttpUrl("https://contact360.io"),
        AnyHttpUrl("http://www.contact360.io"),
        AnyHttpUrl("https://www.contact360.io"),
    ]
    TRUSTED_HOSTS: List[str] = [
        "54.87.173.234",
        "3.95.58.90",
        "54.87.173.234:8000",
        "localhost",
        "127.0.0.1",
        "testserver",
    ]
    ROOT_PATH: str = ""
    USE_PROXY_HEADERS: bool = True
    FORWARDED_ALLOW_IPS: str = "*"


    # File uploads
    UPLOAD_DIR: str = "./uploads"
    MEDIA_URL: str = "/media"
    BASE_URL: str = "http://54.87.173.234:8000"  # Base URL for generating full avatar URLs

    # AWS S3 Configuration
    AWS_ACCESS_KEY_ID: Optional[str] = Field(None, alias="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(None, alias="AWS_SECRET_ACCESS_KEY")
    AWS_REGION: str = Field("us-east-1", alias="AWS_REGION")
    S3_BUCKET_NAME: Optional[str] = Field(None, alias="S3_BUCKET_NAME")
    S3_V3_BUCKET_NAME: str = Field("tkdrawcsvdata", alias="S3_V3_BUCKET_NAME", description="S3 bucket name for v3 API CSV file operations")
    S3_AVATARS_PREFIX: str = Field("avatars/", alias="S3_AVATARS_PREFIX")
    S3_EXPORTS_PREFIX: str = Field("exports/", alias="S3_EXPORTS_PREFIX")
    S3_USE_PRESIGNED_URLS: bool = Field(True, alias="S3_USE_PRESIGNED_URLS")
    S3_PRESIGNED_URL_EXPIRATION: int = Field(3600, alias="S3_PRESIGNED_URL_EXPIRATION")  # 1 hour in seconds

    # BulkMailVerifier Configuration
    BULKMAILVERIFIER_EMAIL: Optional[str] = Field("mr.ayansaha@gmail.com", alias="BULKMAILVERIFIER_EMAIL")
    BULKMAILVERIFIER_PASSWORD: Optional[str] = Field("Bangalore@2020", alias="BULKMAILVERIFIER_PASSWORD")
    BULKMAILVERIFIER_BASE_URL: str = Field(
        "https://app.bulkmailverifier.com", alias="BULKMAILVERIFIER_BASE_URL"
    )
    BULKMAILVERIFIER_MAX_RETRIES: int = Field(
        10,
        alias="BULKMAILVERIFIER_MAX_RETRIES",
        description="DEPRECATED: This setting is no longer used. The system now checks all unique email patterns once without retries.",
    )

    # Gemini AI Configuration
    GEMINI_API_KEY: Optional[str] = Field(None, alias="GEMINI_API_KEY")

    # Pagination defaults
    # Best practice: Use reasonable defaults to prevent memory exhaustion and improve performance.
    # DEFAULT_PAGE_SIZE: Default number of items per page (50-100 is recommended for most APIs)
    # MAX_PAGE_SIZE: Maximum allowed page size to prevent abuse and memory issues
    DEFAULT_PAGE_SIZE: Optional[int] = 100  # Default to 100 items per page (was None = unlimited)
    MAX_PAGE_SIZE: int = 1000  # Maximum page size limit (was None = no cap)

    # Response compression
    ENABLE_RESPONSE_COMPRESSION: bool = True
    COMPRESSION_MIN_SIZE: int = 1000  # Minimum response size to compress (bytes)
    
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Big Data Handling Configuration
    # Streaming configuration
    STREAMING_CHUNK_SIZE: int = Field(1024 * 1024, alias="STREAMING_CHUNK_SIZE")  # 1MB default chunk size for streaming responses
    ENABLE_STREAMING_QUERIES: bool = Field(True, alias="ENABLE_STREAMING_QUERIES")  # Enable streaming for large database queries
    MAX_STREAMING_RESULTS: Optional[int] = Field(None, alias="MAX_STREAMING_RESULTS")  # Maximum results to stream (None = unlimited)
    
    # File upload configuration
    MAX_UPLOAD_CHUNK_SIZE: int = Field(1024 * 1024, alias="MAX_UPLOAD_CHUNK_SIZE")  # 1MB default chunk size for file uploads
    MAX_UPLOAD_SIZE: Optional[int] = Field(None, alias="MAX_UPLOAD_SIZE")  # Maximum file upload size in bytes (None = unlimited)
    
    # Parallel processing configuration
    PARALLEL_PROCESSING_WORKERS: int = Field(4, alias="PARALLEL_PROCESSING_WORKERS")  # Number of workers for parallel processing
    PARALLEL_PROCESSING_MAX_WORKERS: int = Field(8, alias="PARALLEL_PROCESSING_MAX_WORKERS")  # Maximum workers for parallel processing
    ENABLE_PARALLEL_PROCESSING: bool = Field(True, alias="ENABLE_PARALLEL_PROCESSING")  # Enable parallel processing utilities
    
    # Background tasks configuration
    MAX_CONCURRENT_BACKGROUND_TASKS: int = Field(10, alias="MAX_CONCURRENT_BACKGROUND_TASKS")  # Maximum concurrent background tasks
    BACKGROUND_TASK_TIMEOUT: float = Field(30.0, alias="BACKGROUND_TASK_TIMEOUT")  # Timeout in seconds for waiting for tasks during shutdown
    
    # Redis caching configuration (optional)
    REDIS_URL: Optional[str] = Field(None, alias="REDIS_URL", description="Redis connection URL for caching (e.g., redis://localhost:6379/0)")
    ENABLE_REDIS_CACHE: bool = Field(False, alias="ENABLE_REDIS_CACHE", description="Enable Redis backend for query cache (requires REDIS_URL)")
    
    # In-memory caching configuration (using cachetools)
    CACHE_MAX_SIZE: int = Field(1000, alias="CACHE_MAX_SIZE", description="Maximum number of entries in in-memory cache (LRU eviction)")
    ENABLE_CACHE_WARMING: bool = Field(False, alias="ENABLE_CACHE_WARMING", description="Enable cache warming on application startup")
    CACHE_WARMING_QUERIES: List[str] = Field(default_factory=list, alias="CACHE_WARMING_QUERIES", description="List of cache keys to warm on startup (e.g., ['contacts:popular', 'companies:active'])")
    
    # Streaming configuration
    STREAMING_BATCH_SIZE: int = Field(1000, alias="STREAMING_BATCH_SIZE")  # Batch size for streaming database queries
    
    # HTTP Cache Configuration
    ENABLE_HTTP_CACHE: bool = Field(True, alias="ENABLE_HTTP_CACHE", description="Enable HTTP cache headers (ETag, Cache-Control)")
    HTTP_CACHE_MAX_AGE: int = Field(300, alias="HTTP_CACHE_MAX_AGE", description="Default max-age for HTTP cache headers (seconds)")
    HTTP_CACHE_PUBLIC: bool = Field(True, alias="HTTP_CACHE_PUBLIC", description="Whether HTTP cache is public (True) or private (False)")
    HTTP_CACHE_MUST_REVALIDATE: bool = Field(False, alias="HTTP_CACHE_MUST_REVALIDATE", description="Whether cache must revalidate before using stale data")
    HTTP_CACHE_STATIC_MAX_AGE: int = Field(31536000, alias="HTTP_CACHE_STATIC_MAX_AGE", description="Max-age for static content (1 year in seconds)")
    HTTP_CACHE_API_MAX_AGE: int = Field(300, alias="HTTP_CACHE_API_MAX_AGE", description="Max-age for API responses (5 minutes in seconds)")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @classmethod
    def _value_from_info(cls, info: ValidationInfo, field_name: str):
        """Safely extract an input value from the validator context."""
        data_source = getattr(info, "data", None) or {}
        logger.debug(
            "Entering Settings._value_from_info field_name=%s data_keys=%s",
            field_name,
            sorted(data_source.keys()),
        )
        if field_name in data_source:
            value = data_source[field_name]
            logger.debug(
                "Exiting Settings._value_from_info result(from-data)=%r", value
            )
            return value
        default = cls.model_fields[field_name].default
        logger.debug("Exiting Settings._value_from_info result(default)=%r", default)
        return default

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, value: Optional[str], info: ValidationInfo) -> str:
        """Build a SQLAlchemy async URL from component environment variables."""
        logger.debug(
            "Entering Settings.assemble_db_url provided=%s", bool(value and isinstance(value, str))
        )
        if value and isinstance(value, str):
            logger.debug("Exiting Settings.assemble_db_url using provided URL.")
            return value
        username = cls._value_from_info(info, "POSTGRES_USER")
        password = cls._value_from_info(info, "POSTGRES_PASS")
        host = cls._value_from_info(info, "POSTGRES_HOST")
        port = cls._value_from_info(info, "POSTGRES_PORT")
        db_name = cls._value_from_info(info, "POSTGRES_DB")

        user_part = quote_plus(str(username))
        if password:
            user_part = f"{user_part}:{quote_plus(str(password))}"
        database_part = quote_plus(str(db_name))
        assembled = f"postgresql+asyncpg://{user_part}@{host}:{port}/{database_part}"
        logger.debug(
            "Exiting Settings.assemble_db_url result=%s",
            assembled.replace(str(password) if password else "", "***") if password else assembled,
        )
        return assembled


    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value):
        """Allow comma-separated origin strings to be provided via environment."""
        if isinstance(value, str):
            items = [item.strip() for item in value.split(",") if item.strip()]
            logger.debug(
                "Parsing ALLOWED_ORIGINS from string count=%s", len(items)
            )
            return items
        return value

    @field_validator("TRUSTED_HOSTS", mode="before")
    @classmethod
    def parse_trusted_hosts(cls, value):
        """Allow comma-separated trusted hosts via environment configuration."""
        if isinstance(value, str):
            items = [item.strip() for item in value.split(",") if item.strip()]
            logger.debug(
                "Parsing TRUSTED_HOSTS from string count=%s", len(items)
            )
            return items
        return value

    @field_validator("MAX_PAGE_SIZE", mode="after")
    @classmethod
    def validate_max_page_size(cls, value: int) -> int:
        """Ensure MAX_PAGE_SIZE is positive."""
        if value <= 0:
            raise ValueError("MAX_PAGE_SIZE must be greater than 0")
        return value


@log_function_call(logger=logger, log_result=True)
@lru_cache()
def get_settings() -> Settings:
    """Return a cached settings instance."""
    logger.debug("Creating Settings instance.")
    return Settings()

