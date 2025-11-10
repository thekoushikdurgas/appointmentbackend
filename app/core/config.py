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
    PROJECT_NAME: str = "Appointment360 API"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "Async FastAPI backend for Appointment360 data APIs"
    ENVIRONMENT: str = "development"  # development | staging | production
    DEBUG: bool = True

    # API
    API_V1_STR: str = "/api"
    API_V1_PREFIX: str = "/api/v1"
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
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 1800
    DATABASE_URL: Optional[str] = None
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

    # CORS
    ALLOWED_ORIGINS: List[AnyHttpUrl] = [
        AnyHttpUrl("http://localhost:3000"),
        AnyHttpUrl("http://localhost:8000"),
    ]

    # Celery / Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_URL: Optional[str] = None
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    CELERY_TASK_TIME_LIMIT: int = 60 * 30  # 30 minutes
    CELERY_TASK_SOFT_TIME_LIMIT: int = 60 * 25

    # File uploads
    UPLOAD_DIR: str = "./uploads"

    # Pagination defaults
    DEFAULT_PAGE_SIZE: int = 25
    MAX_PAGE_SIZE: int = 100

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

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

    @field_validator("REDIS_URL", mode="before")
    @classmethod
    def assemble_redis_url(cls, value: Optional[str], info: ValidationInfo) -> str:
        """Build a Redis connection URL from component environment variables."""
        logger.debug(
            "Entering Settings.assemble_redis_url provided=%s", bool(value and isinstance(value, str))
        )
        if value and isinstance(value, str):
            logger.debug("Exiting Settings.assemble_redis_url using provided URL.")
            return value
        host = cls._value_from_info(info, "REDIS_HOST")
        port = cls._value_from_info(info, "REDIS_PORT")
        db = cls._value_from_info(info, "REDIS_DB")
        redis_url = f"redis://{host}:{port}/{db}"
        logger.debug("Exiting Settings.assemble_redis_url result=%s", redis_url)
        return redis_url

    @field_validator("CELERY_BROKER_URL", "CELERY_RESULT_BACKEND", mode="before")
    @classmethod
    def default_celery_urls(cls, value: Optional[str], info: ValidationInfo) -> str:
        """Default Celery broker/result URLs to Redis when unset."""
        logger.debug(
            "Entering Settings.default_celery_urls provided=%s", bool(value and isinstance(value, str))
        )
        if value and isinstance(value, str):
            logger.debug("Exiting Settings.default_celery_urls using provided value.")
            return value
        redis_url = cls._value_from_info(info, "REDIS_URL")
        if redis_url:
            logger.debug(
                "Exiting Settings.default_celery_urls reusing redis_url=%s", redis_url
            )
            return redis_url
        assembled = cls.assemble_redis_url(None, info)
        logger.debug(
            "Exiting Settings.default_celery_urls assembled redis_url=%s", assembled
        )
        return assembled


@log_function_call(logger=logger, log_result=True)
@lru_cache()
def get_settings() -> Settings:
    """Return a cached settings instance."""
    logger.debug("Creating Settings instance.")
    return Settings()

