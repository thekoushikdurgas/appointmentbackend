from functools import lru_cache
from typing import List, Optional

from pydantic import AnyHttpUrl, Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
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
    DATABASE_URL: Optional[PostgresDsn] = None

    # Security
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

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

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, value: Optional[str], values: dict) -> str:
        if value and isinstance(value, str):
            return value
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=values["POSTGRES_USER"],
            password=values["POSTGRES_PASS"],
            host=values["POSTGRES_HOST"],
            port=values["POSTGRES_PORT"],
            path=f"/{values['POSTGRES_DB']}",
        )

    @field_validator("REDIS_URL", mode="before")
    @classmethod
    def assemble_redis_url(cls, value: Optional[str], values: dict) -> str:
        if value and isinstance(value, str):
            return value
        return f"redis://{values['REDIS_HOST']}:{values['REDIS_PORT']}/{values['REDIS_DB']}"

    @field_validator("CELERY_BROKER_URL", "CELERY_RESULT_BACKEND", mode="before")
    @classmethod
    def default_celery_urls(cls, value: Optional[str], values: dict) -> str:
        if value and isinstance(value, str):
            return value
        redis_url = values.get("REDIS_URL")
        if not redis_url:
            redis_url = cls.assemble_redis_url(None, values)
        return redis_url


@lru_cache()
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()

