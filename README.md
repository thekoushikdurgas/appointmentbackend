# Appointment360 FastAPI Backend

This project is a production-ready FastAPI service that exposes the Appointment360 data APIs
and a high-throughput CSV import pipeline backed by Celery.

## Features

- FastAPI application structured with clear separation of concerns (API, services, repositories, models).
- Async SQLAlchemy (`asyncpg`) database layer targeting the existing Appointment360 Postgres schema.
- Comprehensive filtering, search, and aggregation endpoints derived from the Appointment360 Postman collection.
- Background CSV import processing using Celery workers, Redis broker/result backend, and persistent job tracking.
- Alembic-managed database migrations.
- Docker Compose environment for API, Celery worker, Redis, and optional Flower monitoring.
- Automated testing with `pytest` and async fixtures.

## Getting Started

### Prerequisites

- Python 3.11+
- Docker (optional, for containerized workflow)
- Access to the Appointment360 Postgres instance

### Installation

```bash
python -m venv .venv
.venv\\Scripts\\activate  # (Windows)
pip install -r requirements.txt
```

Copy the environment template and adjust values for your environment:

```bash
cp .env.example .env
```

### Running the Application

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Celery worker:

```bash
celery -A app.tasks.celery_app worker --loglevel=info
```

### Docker Compose

```bash
docker compose up --build
```

### Tests

```bash
pytest
```

## Project Structure

```
app/
├── api/                 # FastAPI routers (v1/endpoints)
├── core/                # Settings, logging, middleware
├── db/                  # Database session management and Base declarations
├── models/              # SQLAlchemy models
├── repositories/        # Query logic
├── schemas/             # Pydantic schemas
├── services/            # Business logic
├── tasks/               # Celery configuration & background tasks
└── utils/               # Shared utilities
```

## License

MIT © Appointment360

