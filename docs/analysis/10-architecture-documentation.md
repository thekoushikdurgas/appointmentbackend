# Architecture Documentation

## Overview

This document provides comprehensive architecture documentation including request flows, authentication patterns, system diagrams, and component interactions.

## 1. System Architecture

### High-Level Architecture

```
┌─────────────┐
│   Client    │
│  (Browser/  │
│   Mobile)   │
└──────┬──────┘
       │ HTTP
       │
┌──────▼─────────────────────────────────────┐
│         FastAPI Application                 │
│  ┌──────────────────────────────────────┐  │
│  │         Middleware Stack              │  │
│  │  - CORS                               │  │
│  │  - Logging                            │  │
│  │  - Timing                             │  │
│  │  - Compression                        │  │
│  └──────────────────────────────────────┘  │
│  ┌──────────────────────────────────────┐  │
│  │         API Layer (v1/v2)             │  │
│  │  - REST Endpoints                     │  │
│  └──────────────────────────────────────┘  │
│  ┌──────────────────────────────────────┐  │
│  │         Service Layer                │  │
│  │  - Business Logic                    │  │
│  │  - Data Transformation               │  │
│  └──────────────────────────────────────┘  │
│  ┌──────────────────────────────────────┐  │
│  │         Repository Layer             │  │
│  │  - Data Access                      │  │
│  │  - Query Building                   │  │
│  └──────────────────────────────────────┘  │
└──────┬─────────────────────────────────────┘
       │
       ├─────────────────┬─────────────────┐
       │                 │                 │
┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐
│ PostgreSQL  │  │    Redis    │  │  AWS S3     │
│  Database    │  │   (Celery)   │  │  (Storage)  │
└─────────────┘  └──────────────┘  └─────────────┘
```

## 2. Request Flow

### Standard REST Request Flow

```
1. Client Request
   ↓
2. Middleware Stack
   - CORS (if needed)
   - Trusted Host (if needed)
   - Timing (start timer)
   - Logging (log request)
   - Compression (if enabled)
   ↓
3. API Endpoint
   - Route matching
   - Parameter validation
   - Dependency injection (auth, session)
   ↓
4. Service Layer
   - Business logic
   - Data validation
   - Data transformation
   ↓
5. Repository Layer
   - Query building
   - Conditional JOINs
   - Filter application
   ↓
6. Database
   - Query execution
   - Result retrieval
   ↓
7. Repository Layer
   - Result normalization
   ↓
8. Service Layer
   - Data hydration
   - Response building
   ↓
9. API Endpoint
   - Response serialization
   ↓
10. Middleware Stack
    - Timing (end timer, add header)
    - Logging (log response)
    ↓
11. Client Response
```

## 3. Authentication Flow

### JWT Authentication (v2)

```
1. User Login
   POST /api/v2/auth/login
   ↓
2. UserService.authenticate_user()
   - Verify email/password
   - Check user active
   - Update last_sign_in_at
   ↓
3. Token Generation
   - create_access_token() (30 min)
   - create_refresh_token() (7 days)
   ↓
4. Response
   - Return tokens + user info
   ↓
5. Client Storage
   - Store tokens (localStorage/cookies)
   ↓
6. Subsequent Requests
   - Include Bearer token in Authorization header
   ↓
7. get_current_user() Dependency
   - Extract token
   - Decode token
   - Validate token type
   - Retrieve user from database
   ↓
8. Endpoint Execution
   - User available as current_user
```

### Write Key Authentication (v1)

```
1. API Request
   - Include X-Contacts-Write-Key header
   ↓
2. require_contacts_write_key() Dependency
   - Extract header value
   - Compare with settings.CONTACTS_WRITE_KEY
   ↓
3. Validation
   - Match → Continue
   - Mismatch → 403 Forbidden
```

## 4. Data Flow

### Contact List Request

```
Request: GET /api/v1/contacts/?company=TechCorp&limit=25
   ↓
1. API Endpoint
   - resolve_contact_filters() → ContactFilterParams
   - _resolve_pagination() → limit=25
   ↓
2. ContactsService.list_contacts()
   - Validate filters
   - Call repository
   ↓
3. ContactRepository.list_contacts()
   - Determine JOINs needed
     * company filter → needs Company join
   - Build query with conditional JOIN
   - Apply filters
   - Apply ordering
   - Execute query
   ↓
4. Database Query
   SELECT c.*, co.*, cm.*, com.*
   FROM contacts c
   LEFT JOIN companies co ON c.company_id = co.uuid
   WHERE co.name ILIKE '%TechCorp%'
   ORDER BY c.created_at DESC
   LIMIT 25 OFFSET 0
   ↓
5. Result Processing
   - Normalize to 4-tuple
   - Return to service
   ↓
6. ContactsService
   - _hydrate_contact() for each row
   - Build pagination links
   - Return CursorPage
   ↓
7. API Response
   {
     "next": "...",
     "previous": null,
     "results": [...]
   }
```

### Apollo URL Search Flow

```
Request: POST /api/v2/apollo/contacts
Body: {"url": "https://app.apollo.io/#/people?personTitles[]=CEO"}
   ↓
1. API Endpoint
   - Validate request body
   - Extract Apollo URL
   ↓
2. ApolloAnalysisService.analyze_url()
   - Parse URL structure
   - Extract parameters
   - Categorize parameters
   - Cache result (1 hour)
   ↓
3. ApolloAnalysisService.map_to_contact_filters()
   - Convert Apollo params → ContactFilterParams
   - personTitles[] → title filter
   - Track unmapped parameters
   ↓
4. ContactsService.list_contacts()
   - Use converted filters
   - Call repository
   ↓
5. ContactRepository.list_contacts()
   - Conditional JOINs based on filters
   - Execute query
   ↓
6. Response Building
   - Contact results
   - Mapping summary
   - Unmapped parameters
   ↓
7. API Response
   {
     "results": [...],
     "apollo_url": "...",
     "mapping_summary": {...},
     "unmapped_categories": [...]
   }
```

## 5. Background Task Flow

### Import Task Flow

```
1. API Request
   POST /api/v1/contacts/import/
   - Upload CSV file
   ↓
2. ImportService.create_job()
   - Create ContactImportJob record
   - Status: pending
   ↓
3. Queue Celery Task
   process_contacts_import.delay(job_id, file_path)
   ↓
4. Celery Worker
   - Pick up task from imports queue
   - Execute async function
   ↓
5. CSV Processing
   - Read CSV file
   - For each row:
     * Parse data
     * Upsert company
     * Upsert contact
     * Track errors
   - Update progress every 200 rows
   ↓
6. Completion
   - Set status: completed/failed
   - Update final counters
   - Store errors
   ↓
7. Client Polling
   GET /api/v1/contacts/import/{job_id}/
   - Check status
   - Get progress
   - Retrieve errors
```

### Export Task Flow

```
1. API Request
   POST /api/v2/exports/contacts/export
   - Provide contact UUIDs
   ↓
2. ExportService.create_export()
   - Create UserExport record
   - Status: pending
   ↓
3. Queue Celery Task
   process_contact_export.delay(export_id, contact_uuids)
   ↓
4. Celery Worker
   - Pick up task from exports queue
   - Execute async function
   ↓
5. CSV Generation
   - Fetch contacts with relations
   - Generate CSV in memory
   - Upload to S3 or save locally
   ↓
6. Completion
   - Update export with file path
   - Set status: completed
   - Generate download URL
   ↓
7. Client Retrieval
   GET /api/v2/exports/{export_id}/download
   - Get presigned URL
   - Download file
```

## 6. Component Interactions

### Service-Repository Interaction

```
Service Layer
  ↓ calls
Repository Layer
  ↓ uses
Database Session
  ↓ executes
SQLAlchemy ORM
  ↓ generates
SQL Queries
  ↓ executes
PostgreSQL
```

### Apollo Integration Flow

```
API Endpoint
  ↓
ApolloAnalysisService
  ├─ analyze_url() → URL parsing
  └─ map_to_contact_filters() → Filter conversion
       ↓
ContactsService
  ↓
ContactRepository
  ↓
Database
```

### Celery Task Flow

```
API Endpoint
  ↓
Service Layer
  ↓ creates
Import/Export Job
  ↓ queues
Celery Task
  ↓ executes
Background Processing
  ↓ updates
Job Status
  ↓
Client Polling
```

## 7. Database Schema Relationships

### Entity Relationships

```
User (1) ──┐
           │
           ├── (1:1) ── UserProfile
           │
           └── (1:N) ── UserExport

Contact (N) ── (N:1) ── Company (1) ── (1:1) ── CompanyMetadata
    │                                              │
    └── (1:1) ── ContactMetadata                  │
                                                   │
ContactImportJob (1) ── (1:N) ── ContactImportError
```

### Key Relationships

**Contact ↔ Company:**
- Many-to-one (N contacts → 1 company)
- Foreign key: `Contact.company_id → Company.uuid`
- Optional (contact can exist without company)

**Contact ↔ ContactMetadata:**
- One-to-one
- Linked by UUID
- Optional (not all contacts have metadata)

**Company ↔ CompanyMetadata:**
- One-to-one
- Linked by UUID
- Optional

**User ↔ UserProfile:**
- One-to-one
- Linked by user_id
- Cascade delete

**ContactImportJob ↔ ContactImportError:**
- One-to-many
- Cascade delete errors

## 8. Security Architecture

### Authentication Layers

**Layer 1: API Gateway (Optional)**
- External authentication
- Rate limiting
- DDoS protection

**Layer 2: FastAPI Middleware**
- CORS validation
- Host validation
- Request logging

**Layer 3: Endpoint Authentication**
- JWT token validation (v2)
- Write key validation (v1)

**Layer 4: Authorization**
- Role-based access control
- Admin checks
- Resource ownership

### Security Measures

**Password Security:**
- bcrypt hashing
- 72-byte limit handling
- Secure password verification

**Token Security:**
- JWT with expiration
- Access/refresh token separation
- Token type validation

**API Security:**
- Write keys for v1
- Bearer tokens for v2

## 9. Error Handling Architecture

### Error Flow

```
Exception Raised
   ↓
Service/Repository Layer
   ↓
HTTPException (if applicable)
   ↓
FastAPI Exception Handler
   ↓
JSON Response
   {
     "detail": "Error message",
     "error_code": "ERROR_CODE"
   }
```

### Error Types

**Validation Errors:**
- Pydantic validation
- 422 Unprocessable Entity
- Field-level error details

**Authentication Errors:**
- 401 Unauthorized
- Missing/invalid token
- User not found

**Authorization Errors:**
- 403 Forbidden
- Insufficient permissions
- Admin-only operations

**Not Found Errors:**
- 404 Not Found
- Resource doesn't exist
- UUID not found

**Server Errors:**
- 500 Internal Server Error
- Unexpected exceptions
- Logged with stack trace

## 10. Caching Architecture

### Cache Layers

**Layer 1: Query Cache (Redis)**
- Apollo URL analysis (1 hour TTL)
- Query results (optional, 5 min TTL)
- Key: MD5 hash of parameters

**Layer 2: In-Memory Cache**
- Title normalization cache
- Industry mapping cache
- Module-level caching

**Layer 3: Database Query Cache**
- PostgreSQL query cache
- Index usage
- Connection pooling

## 11. Deployment Architecture

### Production Setup

```
┌─────────────┐
│   Load      │
│  Balancer   │
└──────┬──────┘
       │
   ┌───┴───┐
   │       │
┌──▼──┐ ┌──▼──┐
│ API │ │ API │
│  1  │ │  2  │
└──┬──┘ └──┬──┘
   │       │
   └───┬───┘
       │
┌──────▼──────┐
│  PostgreSQL │
│  (RDS)      │
└─────────────┘

┌─────────────┐
│   Redis     │
│  (ElastiCache)│
└─────────────┘

┌─────────────┐
│  Celery     │
│  Workers    │
└─────────────┘

┌─────────────┐
│   AWS S3    │
│  (Storage)  │
└─────────────┘
```

## 12. Scalability Considerations

### Horizontal Scaling

**API Servers:**
- Stateless design
- Load balancer distribution
- Shared database/Redis

**Celery Workers:**
- Multiple workers per queue
- Queue-based distribution
- Independent scaling

### Vertical Scaling

**Database:**
- Connection pooling (25 base + 50 overflow)
- Query optimization
- Index strategy

**Redis:**
- Connection pooling
- Memory management
- TTL-based expiration

## Summary

The architecture demonstrates:

1. **Layered Design**: Clear separation of concerns
2. **Scalability**: Horizontal and vertical scaling support
3. **Security**: Multi-layer authentication and authorization
4. **Performance**: Caching, connection pooling, query optimization
5. **Reliability**: Error handling, background tasks, monitoring
6. **Flexibility**: Multiple API versions, authentication methods

The system is designed for production use with comprehensive error handling, monitoring, and scalability features.

