# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

Project: Appointment360 FastAPI backend (async Python)

Commands you’ll use often

- Setup (Windows PowerShell shown)
  - Create venv and install runtime deps
    ```
    python -m venv venv
    venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    ```
  - Install dev tools (ruff, mypy, pytest, etc.) via extras
    ```
    pip install -e .[dev]
    ```
  - Configure environment
    ```
    copy .env.example .env
    # set DB/Redis values as needed
    ```

- Run API locally (auto-reload)
  ```
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
  ```

- Run Celery worker and Flower
  ```
  celery -A app.tasks.celery_app worker --loglevel=info
  celery -A app.tasks.celery_app flower --address=0.0.0.0 --port=5555
  ```

- Docker Compose (API + Celery + Redis + Postgres)
  ```
  docker compose up --build
  ```

- Database migrations (Alembic)
  ```
  # Create a new migration from model changes
  alembic revision --autogenerate -m "describe change"

  # Apply migrations to latest
  alembic upgrade head

  # Downgrade one step
  alembic downgrade -1
  ```
  Notes:
  - Alembic reads settings from app.core.config and swaps the async URL to sync automatically.
  - Ensure .env has Postgres connection details before running Alembic.

- Lint and type-check
  ```
  # Ruff (lint)
  ruff check .
  # Auto-fix trivial issues
  ruff check --fix .

  # MyPy (types)
  mypy app
  ```

- Tests (pytest configured in pyproject.toml)
  ```
  # Run all tests
  pytest

  # Run a single test
  pytest app/tests/test_root.py::test_api_root_metadata -q

  # Run tests by keyword
  pytest -k "contacts" -q

  # With coverage
  pytest --cov=app
  ```
  Notes:
  - Tests run against an in-memory SQLite database; FastAPI DB dependency is overridden in conftest.

High-level architecture

- FastAPI application (app/main.py)
  - Lifespan sets up logging and filesystem dirs.
  - Middleware: CORS, optional Proxy/Trusted host handling, plus custom LoggingMiddleware and TimingMiddleware.
  - Exception handling translates AppException to JSON.
  - Routers mounted under API_V1_PREFIX (default /api/v1).

- Configuration (app/core/config.py)
  - Pydantic Settings loads from environment/.env with sane defaults for local dev.
  - Assembles DATABASE_URL, REDIS_URL, and defaults Celery broker/backend to Redis if unset.
  - Centralized logging helpers and a log_function_call decorator for rich entry/exit logs.

- Persistence layer
  - SQLAlchemy async engine/session (app/db/session.py). FastAPI dependency get_db yields AsyncSession with rollback/close guarantees.
  - Declarative Base (app/db/base.py) imports app.models to ensure metadata is populated for Alembic/autogenerate.

- Domain model and access patterns
  - Models in app/models define tables (contacts, companies, related metadata, etc.).
  - Repositories (app/repositories) encapsulate query logic. A generic AsyncRepository provides common lookups; per-entity repos extend it.
  - Services (app/services) coordinate repositories and implement higher-level operations (e.g., ContactsService for list/count/create flow).

- API layer (app/api/v1)
  - Routers under endpoints/ expose resources like contacts and import helpers.
  - Query parsing/validation is handled with Pydantic schemas (app/schemas). Endpoints assemble filter params carefully to preserve multi-value inputs.
  - Pagination uses cursor-style helpers in app/utils/cursor.py (base64-encoded offset tokens) with safeguards for legacy formats.

- Background processing
  - Celery app configured in app/tasks/celery_app.py; tasks live in app/tasks and are auto-discovered.

- Migrations
  - Alembic managed in alembic/ with env.py reading Settings; versions under alembic/versions/.

- Testing strategy
  - httpx.AsyncClient + ASGITransport hit the in-process FastAPI app.
  - DB is overridden to SQLite in-memory for isolation and speed; tables are created/dropped per session and cleaned per test.
  - Headers like X-Contacts-Write-Key are injected from Settings in the test client when configured.

Operational notes for agents

- Environment
  - Copy .env.example to .env and set DB/Redis values to run the API against Postgres and Celery against Redis.
  - For local unit tests, external services are not required.

- Adding models/endpoints
  - Place new models under app/models; Base imports that package so Alembic autogenerate sees changes.
  - Add repository/service layers rather than querying in routers directly to keep separation of concerns.
  - Mount new routers in app/api/v1/api.py and expose under a sensible prefix.

- Health and docs
  - Unversioned health at /health; versioned at /api/v1/health/.
  - OpenAPI/Docs URLs are controlled by settings and are disabled in production unless explicitly configured.
