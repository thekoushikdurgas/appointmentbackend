# Appointment360 FastAPI Backend

This project is a production-ready FastAPI service that exposes the Appointment360 data APIs and a high-throughput CSV import pipeline using FastAPI's BackgroundTasks.

## Features

- FastAPI application structured with clear separation of concerns (API, services, repositories, models)
- Async SQLAlchemy (`asyncpg`) database layer targeting the Appointment360 Postgres schema
- Comprehensive filtering, search, and aggregation endpoints derived from the Appointment360 Postman collection
- Background CSV import processing using FastAPI's BackgroundTasks with task status tracking
- Docker Compose environment for API and PostgreSQL database
- Automated testing with `pytest` and async fixtures
- API versioning (v1 and v2) with JWT authentication
- Apollo.io integration for contact enrichment
- LinkedIn integration for profile lookup
- Email finder service
- AI chat functionality with Google Gemini
- **Big Data Optimizations**: Streaming responses, chunked file uploads, query caching, parallel processing, and database-level aggregations

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL database (or Supabase)
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
   - Secret keys
   - API keys for external services

### Running the Application

1. Start the API server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

2. Background tasks run automatically with the API server using FastAPI's BackgroundTasks.

### Docker Compose

To run the entire stack with Docker:

```bash
docker compose up --build
```

This will start:
- API server (port 8000)
- PostgreSQL database

### Service URLs

- **API Base**: http://127.0.0.1:8000
- **API Documentation**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc
- **Health Check**: http://127.0.0.1:8000/health
- **API v1**: http://127.0.0.1:8000/api/v1
- **API v2**: http://127.0.0.1:8000/api/v2

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
├── tasks/              # Background task modules
│   └── import_tasks.py # Import tasks
├── tests/              # Test suite
│   ├── unit/          # Unit tests
│   └── integration/   # Integration tests
└── utils/              # Shared utilities
    ├── cursor.py      # Cursor pagination
    ├── normalization.py  # Text normalization utilities (shared across services)
    └── filters.py     # Filter utilities
```

## API Documentation

### API Versions

- **v1**: Legacy endpoints for contacts, companies, and imports
  - Uses write keys for authorization (header-based)
- **v2**: Modern endpoints with JWT authentication
  - User management and authentication
  - Apollo.io integration
  - AI chat functionality
  - Export management
  - LinkedIn integration
  - Email finder

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

For complete API documentation, visit http://127.0.0.1:8000/docs when the server is running.

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

### Background task issues
- Check application logs for task execution errors
- Verify database connection for tasks that require database access
- Monitor memory usage for long-running tasks

For more troubleshooting tips, see [commands.txt](commands.txt).

## Big Data Handling

The backend includes comprehensive optimizations for handling large datasets efficiently:

### Streaming Responses
- **Streaming Endpoints**: `/api/v1/contacts/stream/` and `/api/v1/companies/stream/` for large dataset exports
- **Formats**: JSONL (newline-delimited JSON) and CSV
- **Memory Efficient**: Streams data in chunks without loading everything into memory

### Chunked File Uploads
- **Async File Handling**: Uses `aiofiles` for efficient chunked uploads
- **Memory Efficient**: Processes files in configurable chunks (default 1MB)
- **Progress Tracking**: Supports large file uploads without memory exhaustion

### Query Caching
- **In-Memory Caching**: Uses `cachetools.TTLCache` for efficient TTL-based caching with LRU eviction
- **Redis Backend**: Optional Redis backend for distributed caching across multiple workers
- **Automatic Invalidation**: Cache invalidation on data mutations with event-driven helpers
- **Cache-Aside Pattern**: Built-in utilities for cache-aside pattern implementation
- **Cache Warming**: Optional cache warming on startup for frequently accessed data
- **Configurable TTL and Maxsize**: Time-to-live and maximum cache size settings

### Parallel Processing
- **ThreadPoolExecutor**: For I/O-bound tasks (database queries, API calls)
- **ProcessPoolExecutor**: For CPU-intensive tasks (bypasses Python's GIL)
- **Batch Processing**: Utilities for processing large datasets in parallel batches

### Database Optimizations
- **Connection Pooling**: Optimized pool sizing and monitoring
- **Database-Level Aggregations**: Uses PostgreSQL `json_build_object` and array functions
- **Streaming Queries**: Server-side cursors for large result sets
- **Query Monitoring**: Automatic slow query detection and logging

See [Big Data Optimizations Documentation](docs/BIG_DATA_OPTIMIZATIONS.md) for detailed information.

## Documentation

- [Root README](../README.md) - Project overview
- [Commands Reference](commands.txt) - Development commands
- [Prompts Reference](promsts.txt) - Development prompts
- [API Documentation](docs/COMPLETE_API_DOCUMENTATION.md) - Complete API reference
- [Architecture Analysis](docs/analysis/) - Deep codebase analysis
- [Big Data Optimizations](docs/BIG_DATA_OPTIMIZATIONS.md) - Comprehensive guide to big data handling

## License

MIT © Appointment360
