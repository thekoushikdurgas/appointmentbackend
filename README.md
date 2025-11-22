# Contact360 FastAPI Backend

This project is a production-ready FastAPI service that exposes the Contact360 data APIs and a high-throughput CSV import pipeline backed by Celery.

## Features

- FastAPI application structured with clear separation of concerns (API, services, repositories, models)
- Async SQLAlchemy (`asyncpg`) database layer targeting the Contact360 Postgres schema
- Comprehensive filtering, search, and aggregation endpoints derived from the Contact360 Postman collection
- Background CSV import processing using Celery workers, Redis broker/result backend, and persistent job tracking
- Docker Compose environment for API, Celery worker, Redis, and optional Flower monitoring
- Automated testing with `pytest` and async fixtures
- API versioning (v1 and v2) with JWT authentication
- WebSocket support for real-time updates
- Apollo.io integration for contact enrichment
- LinkedIn integration for profile lookup
- Email finder service
- AI chat functionality with Google Gemini

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL database (or Supabase)
- Redis (for Celery)
- Docker (optional, for containerized workflow)

### Installation

1. Create virtual environment:

```bash
python -m venv venv
```

2. Activate virtual environment:

```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. Install dependencies:

```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install -e ".[dev]"
```

4. Copy environment template:

```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

5. Edit `.env` file with your configuration:
   - Database connection (PostgreSQL/Supabase)
   - Redis connection
   - Secret keys
   - API keys for external services

### Running the Application

1. Start the API server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

2. Start Celery worker (in a separate terminal):

```bash
celery -A app.tasks.celery_app worker --loglevel=info
```

3. Start Celery beat scheduler (optional, for scheduled tasks):

```bash
celery -A app.tasks.celery_app beat --loglevel=info
```

4. Start Flower monitor (optional, for Celery monitoring):

```bash
celery -A app.tasks.celery_app flower --port=5555
```

### Docker Compose

To run the entire stack with Docker:

```bash
docker compose up --build
```

This will start:
- API server (port 8000)
- Celery worker
- Redis
- Flower (port 5555)

### Service URLs

- **API Base**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **API v1**: http://localhost:8000/api/v1
- **API v2**: http://localhost:8000/api/v2
- **Flower**: http://localhost:5555

## Development

### Commands

For detailed commands, see [commands.txt](commands.txt).

**Common commands:**
```bash
# Run tests
pytest
pytest --cov=app --cov-report=term-missing

# Code quality
ruff check app
ruff format app
mypy app

# Database operations
psql "postgresql://$POSTGRES_USER:$POSTGRES_PASS@$POSTGRES_HOST:$POSTGRES_PORT/$POSTGRES_DB" -c '\dt'
```

### Prompts

For development prompts and instructions, see [promsts.txt](promsts.txt).

## Project Structure

```
app/
├── api/                 # FastAPI routers
│   ├── v1/             # API version 1 (legacy endpoints)
│   │   └── endpoints/  # Contact, company, import endpoints
│   └── v2/             # API version 2 (modern endpoints)
│       └── endpoints/  # Auth, users, AI chats, Apollo, exports, LinkedIn, email
├── core/               # Settings, logging, middleware
│   ├── config.py      # Application configuration
│   ├── logging.py     # Logging setup
│   ├── middleware.py  # Custom middleware
│   └── exceptions.py  # Exception handlers
├── db/                 # Database session management and Base declarations
│   ├── base.py        # SQLAlchemy Base
│   └── session.py     # Database session
├── models/             # SQLAlchemy models
│   ├── contact.py     # Contact model
│   ├── company.py     # Company model
│   └── user.py        # User model
├── repositories/       # Query logic
│   ├── base.py        # Base repository
│   ├── contact.py     # Contact repository
│   └── company.py     # Company repository
├── schemas/            # Pydantic schemas
│   ├── contact.py     # Contact schemas
│   ├── company.py     # Company schemas
│   └── user.py        # User schemas
├── services/           # Business logic
│   ├── contact.py     # Contact service
│   ├── company.py     # Company service
│   ├── apollo.py      # Apollo.io integration
│   └── import.py      # Import service
├── tasks/              # Celery configuration & background tasks
│   ├── celery_app.py  # Celery app configuration
│   └── import_tasks.py # Import tasks
├── tests/              # Test suite
│   ├── unit/          # Unit tests
│   └── integration/   # Integration tests
└── utils/              # Shared utilities
    ├── cursor.py      # Cursor pagination
    └── filters.py     # Filter utilities
```

## API Documentation

### API Versions

- **v1**: Legacy endpoints for contacts, companies, and imports
  - Uses write keys for authorization (header-based)
  - WebSocket support for contacts and companies
- **v2**: Modern endpoints with JWT authentication
  - User management and authentication
  - Apollo.io integration
  - AI chat functionality
  - Export management
  - LinkedIn integration
  - Email finder
  - WebSocket support for Apollo operations

### Key Endpoints

**Authentication:**
- `POST /api/v2/auth/register` - Register new user
- `POST /api/v2/auth/login` - Login user
- `GET /api/v2/auth/me` - Get current user

**Contacts:**
- `GET /api/v1/contacts/` - List contacts with filters
- `GET /api/v1/contacts/{uuid}/` - Get contact by UUID
- `POST /api/v1/contacts/` - Create contact (requires write key)
- `GET /api/v1/contacts/count/` - Count contacts

**Companies:**
- `GET /api/v1/companies/` - List companies with filters
- `GET /api/v1/companies/{uuid}/` - Get company by UUID
- `POST /api/v1/companies/` - Create company (requires write key)

**AI Chats:**
- `GET /api/v2/ai-chats/` - List AI chat conversations
- `POST /api/v2/ai-chats/` - Create new chat
- `POST /api/v2/ai-chats/{chat_id}/messages` - Send message

**Apollo:**
- `GET /api/v2/apollo/` - Search contacts via Apollo.io
- `POST /api/v2/apollo/` - Create Apollo search

**Exports:**
- `GET /api/v2/exports/` - List export jobs
- `POST /api/v2/exports/` - Create export job

For complete API documentation, visit http://localhost:8000/docs when the server is running.

See [docs/COMPLETE_API_DOCUMENTATION.md](docs/COMPLETE_API_DOCUMENTATION.md) for detailed API documentation.

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Run specific test file
pytest app/tests/test_contacts.py -vv

# Run integration tests
pytest app/tests/integration/test_api_endpoints.py --api-base-url http://0.0.0.0:8000
```

## Environment Variables

Required variables in `.env`:

```env
# Database
DATABASE_URL=postgresql://user:password@host:port/database
# Or individual variables:
POSTGRES_USER=user
POSTGRES_PASS=password
POSTGRES_HOST=host
POSTGRES_PORT=5432
POSTGRES_DB=database

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-here

# External APIs
APOLLO_API_KEY=your-apollo-api-key
GEMINI_API_KEY=your-gemini-api-key
LINKEDIN_API_KEY=your-linkedin-api-key
```

See `.env.example` for complete list of environment variables.

## Deployment

See [deploy/](deploy/) directory for deployment configurations and systemd service files.

## Troubleshooting

### API won't start
- Check Python version: `python --version` (should be 3.11+)
- Verify virtual environment is activated
- Check `.env` file exists and has correct values
- Verify all dependencies installed: `pip list`

### Database connection issues
- Verify PostgreSQL is running
- Check connection string in `.env`
- Test connection: `psql "postgresql://..."`

### Celery worker issues
- Check Redis is running: `redis-cli ping`
- Verify Celery configuration in `app/tasks/celery_app.py`
- Check Redis connection in `.env`
- View worker logs: `celery -A app.tasks.celery_app worker --loglevel=debug`

For more troubleshooting tips, see [commands.txt](commands.txt).

## Documentation

- [Root README](../README.md) - Project overview
- [Commands Reference](commands.txt) - Development commands
- [Prompts Reference](promsts.txt) - Development prompts
- [API Documentation](docs/COMPLETE_API_DOCUMENTATION.md) - Complete API reference
- [Architecture Analysis](docs/analysis/) - Deep codebase analysis

## License

MIT © Contact360
