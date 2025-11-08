<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

## Complete FastAPI Project Structure for Production-Ready Applications

Based on best practices from the FastAPI community and production deployments, here's a comprehensive file structure that fully leverages FastAPI's capabilities for building scalable, maintainable applications.

## Directory Structure

```
fastapi-project/
├── .env                          # Environment variables (not committed to git)
├── .env.example                  # Example environment file (template)
├── .gitignore                    # Git ignore file
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Docker configuration
├── docker-compose.yml            # Docker Compose for multi-container setup
├── README.md                     # Project documentation
├── alembic.ini                   # Database migration configuration
├── pytest.ini                    # Pytest configuration
├── .coveragerc                   # Code coverage configuration
│
├── app/                          # Main application directory
│   ├── __init__.py
│   ├── main.py                   # FastAPI app initialization & startup
│   │
│   ├── api/                      # API layer
│   │   ├── __init__.py
│   │   ├── deps.py               # Shared dependencies (DB session, auth)
│   │   │
│   │   ├── v1/                   # API version 1
│   │   │   ├── __init__.py
│   │   │   ├── api.py            # API router aggregator
│   │   │   │
│   │   │   └── endpoints/        # Individual endpoint modules
│   │   │       ├── __init__.py
│   │   │       ├── auth.py       # Authentication endpoints
│   │   │       ├── users.py      # User management endpoints
│   │   │       ├── items.py      # Item/resource endpoints
│   │   │       └── health.py     # Health check endpoints
│   │   │
│   │   └── v2/                   # API version 2 (future)
│   │       └── __init__.py
│   │
│   ├── core/                     # Core application configuration
│   │   ├── __init__.py
│   │   ├── config.py             # Settings & environment variables
│   │   ├── security.py           # Security utilities (JWT, OAuth2)
│   │   ├── logging.py            # Logging configuration
│   │   └── events.py             # Startup/shutdown events
│   │
│   ├── models/                   # Database models (SQLAlchemy)
│   │   ├── __init__.py
│   │   ├── base.py               # Base model class
│   │   ├── user.py               # User model
│   │   └── item.py               # Item model
│   │
│   ├── schemas/                  # Pydantic schemas (request/response)
│   │   ├── __init__.py
│   │   ├── user.py               # User schemas
│   │   ├── item.py               # Item schemas
│   │   ├── token.py              # Token schemas
│   │   └── common.py             # Common/shared schemas
│   │
│   ├── crud/                     # Database CRUD operations
│   │   ├── __init__.py
│   │   ├── base.py               # Base CRUD class
│   │   ├── user.py               # User CRUD operations
│   │   └── item.py               # Item CRUD operations
│   │
│   ├── db/                       # Database configuration
│   │   ├── __init__.py
│   │   ├── base.py               # Import all models for Alembic
│   │   ├── session.py            # Database session management
│   │   └── init_db.py            # Database initialization
│   │
│   ├── services/                 # Business logic layer
│   │   ├── __init__.py
│   │   ├── user_service.py       # User business logic
│   │   ├── email_service.py      # Email sending logic
│   │   └── storage_service.py    # File storage logic
│   │
│   ├── tasks/                    # Background tasks (Celery)
│   │   ├── __init__.py
│   │   ├── celery_app.py         # Celery configuration
│   │   ├── email_tasks.py        # Email background tasks
│   │   └── data_processing.py    # Data processing tasks
│   │
│   ├── middleware/               # Custom middleware
│   │   ├── __init__.py
│   │   ├── cors.py               # CORS configuration
│   │   ├── request_logging.py    # Request/response logging
│   │   └── rate_limiting.py      # Rate limiting middleware
│   │
│   ├── utils/                    # Utility functions
│   │   ├── __init__.py
│   │   ├── email.py              # Email utilities
│   │   ├── validators.py         # Custom validators
│   │   └── helpers.py            # Helper functions
│   │
│   └── static/                   # Static files (if needed)
│       └── images/
│
├── alembic/                      # Database migrations
│   ├── versions/                 # Migration files
│   ├── env.py                    # Alembic environment
│   └── script.py.mako            # Migration template
│
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── conftest.py               # Pytest fixtures
│   ├── test_main.py              # Main app tests
│   │
│   ├── api/                      # API endpoint tests
│   │   ├── __init__.py
│   │   ├── test_auth.py
│   │   ├── test_users.py
│   │   └── test_items.py
│   │
│   ├── crud/                     # CRUD operation tests
│   │   ├── __init__.py
│   │   └── test_user_crud.py
│   │
│   ├── services/                 # Service layer tests
│   │   ├── __init__.py
│   │   └── test_user_service.py
│   │
│   └── utils/                    # Utility function tests
│       ├── __init__.py
│       └── test_validators.py
│
└── scripts/                      # Utility scripts
    ├── init_db.py                # Database initialization
    ├── seed_data.py              # Seed test data
    └── deploy.sh                 # Deployment script
```


## Key Files Explained with Examples

### 1. **app/main.py** - Application Entry Point

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1.api import api_router
from app.db.session import engine
from app.db.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    await init_db()
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```


### 2. **app/core/config.py** - Configuration Management[^1][^2][^3]

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional


class Settings(BaseSettings):
    # Project info
    PROJECT_NAME: str = "FastAPI Application"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database
    DATABASE_URL: str
    DB_ECHO_LOG: bool = False
    
    # Redis (for caching/Celery)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # Email
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[str] = None
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # File storage
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )


settings = Settings()
```


### 3. **app/db/session.py** - Database Session Management[^4][^5]

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO_LOG,
    future=True,
    pool_pre_ping=True,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db() -> AsyncSession:
    """Dependency for getting async database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```


### 4. **app/api/deps.py** - Shared Dependencies[^6][^2]

```python
from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import verify_token
from app.db.session import get_db
from app.crud.user import user_crud
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await user_crud.get(db, id=int(user_id))
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Ensure user is active"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
```


### 5. **app/core/security.py** - Security Utilities[^7][^8]

```python
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password"""
    return pwd_context.hash(password)
```


### 6. **app/models/user.py** - Database Model[^2][^1]

```python
from sqlalchemy import Boolean, Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```


### 7. **app/schemas/user.py** - Pydantic Schemas[^1][^2]

```python
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


# Shared properties
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    is_active: bool = True


# Properties to receive on user creation
class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


# Properties to receive on user update
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None


# Properties shared by models stored in DB
class UserInDBBase(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# Properties to return to client
class User(UserInDBBase):
    pass


# Properties stored in DB
class UserInDB(UserInDBBase):
    hashed_password: str
```


### 8. **app/crud/base.py** - Generic CRUD Operations[^2][^1]

```python
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get(self, db: AsyncSession, id: Any) -> Optional[ModelType]:
        result = await db.execute(select(self.model).filter(self.model.id == id))
        return result.scalars().first()

    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        result = await db.execute(select(self.model).offset(skip).limit(limit))
        return result.scalars().all()

    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        obj_data = jsonable_encoder(db_obj)
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def remove(self, db: AsyncSession, *, id: int) -> ModelType:
        obj = await self.get(db, id=id)
        await db.delete(obj)
        await db.flush()
        return obj
```


### 9. **app/api/v1/endpoints/users.py** - API Endpoints[^6][^2]

```python
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_active_user
from app.crud.user import user_crud
from app.schemas.user import User, UserCreate, UserUpdate
from app.models.user import User as UserModel

router = APIRouter()


@router.get("/", response_model=List[User])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Retrieve users.
    """
    users = await user_crud.get_multi(db, skip=skip, limit=limit)
    return users


@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create new user.
    """
    user = await user_crud.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="User with this email already exists"
        )
    user = await user_crud.create(db, obj_in=user_in)
    return user


@router.get("/{user_id}", response_model=User)
async def read_user_by_id(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Get a specific user by id.
    """
    user = await user_crud.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Update a user.
    """
    user = await user_crud.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = await user_crud.update(db, db_obj=user, obj_in=user_in)
    return user
```


### 10. **app/middleware/request_logging.py** - Custom Middleware[^9][^10]

```python
import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log request
        logger.info(f"Request: {request.method} {request.url.path}")
        
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            f"Response: {response.status_code} | "
            f"Time: {process_time:.4f}s | "
            f"Path: {request.url.path}"
        )
        
        response.headers["X-Process-Time"] = str(process_time)
        return response
```


### 11. **app/tasks/celery_app.py** - Celery Configuration[^11][^12][^13]

```python
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.task_routes = {
    "app.tasks.email_tasks.*": "email-queue",
    "app.tasks.data_processing.*": "processing-queue"
}

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
```


### 12. **app/tasks/email_tasks.py** - Background Tasks[^12][^14]

```python
from app.tasks.celery_app import celery_app
from app.utils.email import send_email


@celery_app.task(name="send_welcome_email")
def send_welcome_email_task(email: str, username: str):
    """Send welcome email to new user"""
    subject = "Welcome to our platform!"
    body = f"Hello {username}, welcome to our application!"
    
    send_email(
        to_email=email,
        subject=subject,
        body=body
    )
    return f"Email sent to {email}"


@celery_app.task(name="send_password_reset_email")
def send_password_reset_email_task(email: str, reset_token: str):
    """Send password reset email"""
    subject = "Password Reset Request"
    body = f"Use this token to reset your password: {reset_token}"
    
    send_email(
        to_email=email,
        subject=subject,
        body=body
    )
    return f"Password reset email sent to {email}"
```


### 13. **tests/conftest.py** - Test Fixtures[^15][^16]

```python
import pytest
import asyncio
from typing import AsyncGenerator
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import app
from app.db.session import Base, get_db
from app.core.config import settings

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(TEST_DATABASE_URL, echo=True)
TestingSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestingSessionLocal() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()
```


### 14. **Dockerfile** - Container Configuration[^17][^18]

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./app ./app
COPY ./alembic ./alembic
COPY ./alembic.ini .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```


### 15. **docker-compose.yml** - Multi-Container Setup[^18][^11][^17]

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:password@db:5432/appdb
      - REDIS_HOST=redis
      - CELERY_BROKER_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./app:/app/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=appdb
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  celery_worker:
    build: .
    command: celery -A app.tasks.celery_app worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:password@db:5432/appdb
      - REDIS_HOST=redis
      - CELERY_BROKER_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  flower:
    build: .
    command: celery -A app.tasks.celery_app flower --port=5555
    ports:
      - "5555:5555"
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
    depends_on:
      - redis
      - celery_worker

volumes:
  postgres_data:
```


### 16. **requirements.txt** - Dependencies

```
fastapi==0.110.0
uvicorn[standard]==0.27.1
sqlalchemy[asyncio]==2.0.27
asyncpg==0.29.0
alembic==1.13.1
pydantic==2.6.1
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9
celery==5.3.6
redis==5.0.1
flower==2.0.1
pytest==8.0.0
pytest-asyncio==0.23.5
httpx==0.26.0
python-dotenv==1.0.1
```


### 17. **.env.example** - Environment Template[^3][^19]

```
# Project
PROJECT_NAME=FastAPI Application
VERSION=1.0.0
API_V1_STR=/api/v1

# Security
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname
DB_ECHO_LOG=False

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# CORS
ALLOWED_ORIGINS=["http://localhost:3000","http://localhost:8000"]

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAILS_FROM_EMAIL=noreply@example.com

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```


### 18. **app/core/logging.py** - Logging Configuration[^20][^21]

```python
import logging
import sys
from pathlib import Path


def setup_logging():
    """Configure logging for the application"""
    
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("logs/app.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set specific log levels for different modules
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)
```


## Project Structure Benefits

This comprehensive structure provides several key advantages:[^22][^23][^1][^2]

**Separation of Concerns**: Each directory has a clear, single responsibility (models, schemas, CRUD, endpoints)[^1][^2]

**Scalability**: Organized by feature/domain makes it easy to add new modules without cluttering existing code[^24][^25]

**Version Control**: API versioning (v1, v2) allows backward compatibility while adding new features[^26]

**Testability**: Dedicated test directory mirrors app structure, making tests easy to locate and maintain[^16][^15]

**Security**: Centralized security configuration with proper JWT authentication and password hashing[^8][^7]

**Asynchronous Support**: Full async/await implementation with SQLAlchemy async engine for high performance[^5][^4]

**Background Tasks**: Celery integration for handling long-running processes without blocking requests[^14][^13][^12]

**Dependency Injection**: Reusable dependencies for database sessions, authentication, and authorization[^6][^2]

**Configuration Management**: Environment-based settings using Pydantic for type safety[^19][^27][^3]

**Middleware Stack**: Custom middleware for logging, CORS, and rate limiting[^10][^28][^9]

**Containerization**: Docker and Docker Compose for consistent development and deployment[^17][^18]

**Database Migrations**: Alembic integration for managing schema changes systematically[^1]

**Monitoring**: Flower integration for monitoring Celery tasks in real-time[^13][^11]

This structure follows industry best practices and scales from small projects to large enterprise applications. It provides clear separation between API routes, business logic, data access, and external services, making the codebase maintainable and developer-friendly.
<span style="display:none">[^29][^30][^31][^32][^33][^34][^35][^36][^37][^38][^39][^40][^41][^42][^43][^44][^45][^46][^47][^48][^49][^50][^51][^52][^53][^54][^55][^56][^57][^58][^59][^60][^61][^62][^63][^64][^65][^66][^67][^68][^69][^70][^71][^72][^73][^74][^75][^76][^77][^78][^79][^80][^81][^82][^83][^84][^85][^86]</span>

<div align="center">⁂</div>

[^1]: https://github.com/zhanymkanov/fastapi-best-practices

[^2]: https://stackoverflow.com/questions/64943693/what-are-the-best-practices-for-structuring-a-fastapi-project

[^3]: https://fastapi.tiangolo.com/advanced/settings/

[^4]: https://github.com/tiangolo/fastapi/discussions/4302

[^5]: https://timothy.hashnode.dev/from-zero-to-production-setting-up-a-sql-database-with-async-engine-in-fastapi

[^6]: https://fastapi.tiangolo.com/tutorial/bigger-applications/

[^7]: https://www.geeksforgeeks.org/python/login-registration-system-with-jwt-in-fastapi/

[^8]: https://www.youtube.com/watch?v=KxR3OONvDvo

[^9]: https://fastapi.tiangolo.com/tutorial/middleware/

[^10]: https://semaphore.io/blog/custom-middleware-fastapi

[^11]: https://ieeexplore.ieee.org/document/11028389/

[^12]: https://testdriven.io/blog/fastapi-and-celery/

[^13]: https://github.com/SteliosGian/fastapi-celery-redis-flower

[^14]: https://www.youtube.com/watch?v=eAHAKowv6hk

[^15]: https://codesignal.com/learn/courses/model-serving-with-fastapi/lessons/testing-fastapi-applications-with-pytest

[^16]: https://testdriven.io/blog/fastapi-crud/

[^17]: https://accuweb.cloud/resource/articles/setup-fastapi-application-using-docker-compose

[^18]: https://www.digitalocean.com/community/tutorials/create-fastapi-app-using-docker-compose

[^19]: https://www.getorchestra.io/guides/fastapi-and-environment-variables-a-detailed-tutorial

[^20]: https://www.linkedin.com/pulse/best-practices-logging-fastapi-applications-manikandan-parasuraman-96n2c

[^21]: https://stackoverflow.com/questions/77001129/how-to-configure-fastapi-logging-so-that-it-works-both-with-uvicorn-locally-and

[^22]: https://dev.to/mohammad222pr/structuring-a-fastapi-project-best-practices-53l6

[^23]: https://www.projectpro.io/article/fastapi-projects/847

[^24]: https://www.reddit.com/r/FastAPI/comments/uxnso3/fastapi_large_app_structure/

[^25]: https://dev.to/timo_reusch/how-i-structure-big-fastapi-projects-260e

[^26]: https://christophergs.com/tutorials/ultimate-fastapi-tutorial-pt-8-project-structure-api-versioning/

[^27]: https://stackoverflow.com/questions/61582142/test-pydantic-settings-in-fastapi

[^28]: https://sailokesh.hashnode.dev/enable-and-configure-cors-in-fastapi

[^29]: https://fepbl.com/index.php/ijmer/article/view/936

[^30]: https://www.cambridge.org/core/product/identifier/S2059866123005666/type/journal_article

[^31]: https://journals.lww.com/10.34067/KID.0000000000000277

[^32]: https://www.euppublishing.com/doi/10.3366/ijhac.2024.0325

[^33]: https://www.c5k.com/9-1-19-article/jitmbh24002

[^34]: https://allacademicresearch.com/index.php/AJAIMLDSMIS/article/view/128/

[^35]: https://link.springer.com/10.1007/978-1-0716-2883-6_1

[^36]: http://www.tandfonline.com/doi/abs/10.1080/09544120100000011

[^37]: https://www.frontiersin.org/articles/10.3389/frsle.2023.1329405/full

[^38]: https://cdnsciencepub.com/doi/10.1139/cjfr-2024-0085

[^39]: https://zenodo.org/record/4550441/files/MAP-EuroPlop2020aPaper.pdf

[^40]: http://arxiv.org/pdf/2401.07053.pdf

[^41]: https://joss.theoj.org/papers/10.21105/joss.05350.pdf

[^42]: https://zenodo.org/record/4550449/files/MAP-EuroPlop2020bPaper.pdf

[^43]: https://www.mdpi.com/2078-2489/11/2/108/pdf

[^44]: https://arxiv.org/pdf/2303.13828.pdf

[^45]: https://arxiv.org/pdf/2502.09766.pdf

[^46]: https://arxiv.org/pdf/2202.00057.pdf

[^47]: https://www.reddit.com/r/FastAPI/comments/1g5zl81/looking_for_projects_best_practices/

[^48]: https://dev.to/mrchike/fastapi-in-production-build-scale-deploy-series-a-codebase-design-ao3

[^49]: https://dl.acm.org/doi/10.1145/3382025.3414986

[^50]: https://ieeexplore.ieee.org/document/11020617/

[^51]: https://dl.acm.org/doi/10.1145/3328905.3329507

[^52]: http://ieeexplore.ieee.org/document/7857781/

[^53]: https://ieeexplore.ieee.org/document/10743930/

[^54]: https://link.springer.com/10.1007/978-3-030-89159-6_10

[^55]: https://dl.acm.org/doi/10.1145/384197.384223

[^56]: https://www.semanticscholar.org/paper/a60c48318c06014dafed77015d46b2d67d33e71e

[^57]: https://www.semanticscholar.org/paper/15706afd138505bb963d69f8bbeebb0491024a89

[^58]: https://dl.acm.org/doi/10.1145/3491085.3502277

[^59]: https://www.mdpi.com/1424-8220/12/7/8544/pdf

[^60]: https://arxiv.org/pdf/1309.1515.pdf

[^61]: http://arxiv.org/pdf/1301.1085.pdf

[^62]: http://thescipub.com/pdf/10.3844/jcssp.2005.7.18

[^63]: https://journals.sagepub.com/doi/pdf/10.1155/2016/2702789

[^64]: https://arxiv.org/pdf/1604.04823.pdf

[^65]: https://peerj.com/articles/cs-545.pdf

[^66]: http://arxiv.org/pdf/2301.05522.pdf

[^67]: https://fastapi.tiangolo.com/advanced/middleware/

[^68]: https://stackoverflow.com/questions/71525132/how-to-write-a-custom-fastapi-middleware-class

[^69]: https://www.youtube.com/watch?v=P3zdVdb-yn8

[^70]: https://www.getorchestra.io/guides/fastapi-middleware-a-comprehensive-guide

[^71]: http://mdcs.knuba.edu.ua/article/view/309467

[^72]: https://www.semanticscholar.org/paper/5192d0b5b8d1cc463e9873929cad222462962d23

[^73]: https://arxiv.org/pdf/2203.06559.pdf

[^74]: https://arxiv.org/pdf/2301.05861.pdf

[^75]: https://arxiv.org/pdf/2203.08323.pdf

[^76]: https://arxiv.org/pdf/2305.05920.pdf

[^77]: http://arxiv.org/pdf/2309.00595.pdf

[^78]: https://arxiv.org/pdf/2002.04688.pdf

[^79]: http://arxiv.org/pdf/2411.08203.pdf

[^80]: https://stackoverflow.com/questions/74508774/whats-the-difference-between-fastapi-background-tasks-and-celery-tasks

[^81]: https://fastapi.tiangolo.com/tutorial/background-tasks/

[^82]: https://testdriven.io/courses/fastapi-celery/intro/

[^83]: https://docs.pydantic.dev/latest/concepts/pydantic_settings/

[^84]: https://fastapi.xiniushu.com/hy/advanced/settings/

[^85]: https://gpttutorpro.com/fastapi-security-authentication-authorization-and-cors/

[^86]: https://www.youtube.com/watch?v=TI1jU2YbIPA

