# API Layer Architecture Analysis

## Overview

The API layer is organized into two versions (v1 and v2) with clear separation of concerns. This document analyzes the API versioning structure, authentication patterns, and endpoint implementations.

## 1. API Versioning Structure

### Version Organization

**API v1 (`app/api/v1/api.py`):**

- Legacy endpoints for contacts, companies, and imports
- Uses write keys for authorization (header-based)
- Organized by resource type
- REST API endpoints for contacts and companies

**API v2 (`app/api/v2/api.py`):**

- Modern endpoints with JWT authentication
- User management and authentication
- Apollo.io integration
- AI chat functionality
- Export management
- REST API endpoints for Apollo operations

### Router Aggregation Pattern

Both versions use FastAPI's `APIRouter` pattern:

```python
# v1
api_router = APIRouter()
api_router.include_router(root.router)
api_router.include_router(contacts.router)
api_router.include_router(companies.router)
api_router.include_router(imports.router)

# v2
api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(ai_chats.router)
api_router.include_router(apollo.router)
api_router.include_router(exports.router, prefix="/exports")
```

**Key Features:**

- Modular router organization
- Prefix-based grouping
- Tag-based OpenAPI documentation
- Clear separation of concerns

## 2. Authentication and Authorization

### OAuth2 Token Authentication (`app/api/deps.py`)

**Token Scheme:**

- Uses `OAuth2PasswordBearer` with `auto_error=False`
- Token extracted from `Authorization: Bearer <token>` header
- Token URL: `/api/v2/auth/login`

### Authentication Dependencies

#### `get_current_user`

**Purpose:** Extract and validate JWT token, retrieve user from database

**Flow:**

1. Extract token from `Authorization` header
2. Decode token using `decode_token()`
3. Validate token type is "access"
4. Extract user ID from token payload
5. Query database for user by UUID
6. Return `User` object or raise `HTTPException(401)`

**Error Handling:**

- No token → 401 Unauthorized
- Invalid token → 401 Unauthorized
- Missing user ID → 401 Unauthorized
- User not found → 401 Unauthorized

#### `get_current_active_user`

**Purpose:** Ensure user account is active

**Flow:**

1. Depends on `get_current_user`
2. Checks `user.is_active` flag
3. Returns user if active, raises 400 if inactive

#### `get_current_admin`

**Purpose:** Ensure user has admin role

**Flow:**

1. Depends on `get_current_user`
2. Retrieves user profile
3. Checks profile role (defaults to "Member" if no profile)
4. Returns user if role is "Admin", raises 403 if not

**Role System:**

- Default role: "Member"
- Admin role: "Admin"
- Role stored in `user_profiles` table

### Write Key Authentication (v1)

**Contacts Write Key:**

- Header: `X-Contacts-Write-Key`
- Dependency: `require_contacts_write_key()`
- Validates against `settings.CONTACTS_WRITE_KEY`

**Companies Write Key:**

- Header: `X-Companies-Write-Key`
- Dependency: `require_companies_write_key()`
- Validates against `settings.COMPANIES_WRITE_KEY`

**Usage:**

- Used for v1 endpoints that modify data
- Simpler than JWT for API-to-API communication
- Legacy authentication method

## 3. Endpoint Implementation Patterns

### Filter Resolution Pattern

**Common Pattern:**
```python
async def resolve_contact_filters(request: Request) -> ContactFilterParams:
    """Build filter parameters from query string."""
    query_params = request.query_params
    data = dict(query_params)
    
    # Handle multi-value parameters
    multi_value_keys = ("exclude_company_ids", "exclude_titles", ...)
    for key in multi_value_keys:
        values = query_params.getlist(key)
        if values:
            data[key] = values
    
    # Validate with Pydantic
    try:
        return ContactFilterParams.model_validate(data)
    except ValidationError as exc:
        # Extract first error message
        first_error = exc.errors()[0] if exc.errors() else {}
        message = first_error.get("msg", "Invalid query parameters")
        raise HTTPException(status_code=400, detail=message) from exc
```

**Features:**

- Handles multi-value query parameters
- Pydantic validation
- User-friendly error messages
- Consistent error handling

### Pagination Resolution Pattern

**Common Pattern:**
```python
def _resolve_pagination(filters: FilterParams, limit: Optional[int]) -> Optional[int]:
    """Choose appropriate page size."""
    # Explicit limit takes precedence
    if limit is not None:
        return limit
    
    # Filter page_size with optional cap
    if filters.page_size is not None:
        if settings.MAX_PAGE_SIZE is not None:
            return min(filters.page_size, settings.MAX_PAGE_SIZE)
        return filters.page_size
    
    # Default from settings
    return settings.DEFAULT_PAGE_SIZE
```

**Priority Order:**

1. Explicit `limit` query parameter (no cap)
2. `page_size` in filters (with cap if configured)
3. `DEFAULT_PAGE_SIZE` from settings

### Endpoint Structure Pattern

**Standard Endpoint:**
```python
@router.get("/endpoint/", response_model=ResponseModel)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
async def endpoint_name(
    filters: FilterParams = Depends(resolve_filters),
    limit: Optional[int] = Query(None),
    offset: int = Query(0),
    cursor: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),  # v2 only
    session: AsyncSession = Depends(get_db),
) -> ResponseModel:
    """Endpoint documentation."""
    # Implementation
```

**Common Dependencies:**

- `filters`: Query parameter validation
- `limit`, `offset`, `cursor`: Pagination
- `current_user`: Authentication (v2)
- `session`: Database session

### Error Handling Pattern

**Consistent Error Handling:**
```python
try:
    result = await service.method(session, ...)
    return result
except HTTPException:
    raise  # Re-raise HTTP exceptions
except Exception as exc:
    logger.exception("Operation failed: %s", exc)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Operation failed"
    ) from exc
```

**Features:**

- Preserves HTTP exceptions
- Logs unexpected errors
- Returns user-friendly messages
- Maintains exception chain

## 4. Contacts Endpoints (v1)

### Endpoint Categories

**Core Operations:**

- `GET /contacts/` - List contacts with filters
- `GET /contacts/count/` - Count matching contacts
- `GET /contacts/{uuid}/` - Retrieve single contact
- `POST /contacts/` - Create contact (requires write key)
- `GET /contacts/uuids/` - Get contact UUIDs

**Attribute Lists:**

- `GET /contacts/titles/` - List unique titles
- `GET /contacts/companies/` - List unique companies
- `GET /contacts/industries/` - List unique industries
- `GET /contacts/keywords/` - List unique keywords
- `GET /contacts/technologies/` - List unique technologies
- `GET /contacts/departments/` - List unique departments
- `GET /contacts/seniority/` - List unique seniority levels
- `GET /contacts/company-addresses/` - List company addresses
- `GET /contacts/contact-addresses/` - List contact addresses
- `GET /contacts/company-domains/` - List company domains

### Special Filter Resolvers

**Industry/Keywords/Technologies:**

- Always enforce `distinct=True`
- Remove `distinct` from query params to prevent override
- Force `distinct=True` in validated params

**Purpose:** Ensure unique values in attribute lists

## 5. Companies Endpoints (v1)

### Endpoint Categories

**Core Operations:**

- `GET /companies/` - List companies with filters
- `GET /companies/count/` - Count matching companies
- `GET /companies/{uuid}/` - Retrieve single company
- `POST /companies/` - Create company (requires write key)
- `PUT /companies/{uuid}/` - Update company (requires write key)
- `DELETE /companies/{uuid}/` - Delete company (requires write key)
- `GET /companies/uuids/` - Get company UUIDs

**Attribute Lists:**

- `GET /companies/names/` - List unique company names
- `GET /companies/industries/` - List unique industries
- `GET /companies/keywords/` - List unique keywords
- `GET /companies/technologies/` - List unique technologies
- `GET /companies/addresses/` - List unique addresses
- `GET /companies/cities/` - List unique cities
- `GET /companies/states/` - List unique states
- `GET /companies/countries/` - List unique countries

**Company Contacts:**

- `GET /companies/{uuid}/contacts/` - List contacts for company
- `GET /companies/{uuid}/contacts/count/` - Count contacts for company
- `GET /companies/{uuid}/contacts/attributes/` - List contact attributes

## 6. Apollo Endpoints (v2)

### Endpoint Categories

**URL Analysis:**

- `POST /apollo/analyze` - Analyze Apollo.io URL and extract parameters
- Returns parameter categories, mappings, and statistics

**Contact Operations:**

- `POST /apollo/contacts` - Search contacts using Apollo URL parameters
- `POST /apollo/contacts/count` - Count contacts matching Apollo URL
- `POST /apollo/contacts/count/uuids` - Get UUIDs matching Apollo URL

**Features:**

- Converts Apollo.io People Search URLs to contact filters
- Tracks mapped and unmapped parameters
- Supports additional query parameters for filtering
- Cursor-based pagination

**Error Response:**
```json
{
    "action": "search_contacts",
    "status": "error",
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid URL"
    }
}
```

## 8. Authentication Endpoints (v2)

### Endpoints

**Registration:**

- `POST /auth/register/` - Register new user
- Returns access and refresh tokens
- Creates user profile automatically

**Login:**

- `POST /auth/login/` - Authenticate user
- Returns access and refresh tokens
- Updates `last_sign_in_at` timestamp

**Session:**

- `GET /auth/session/` - Get current session info
- Requires authentication
- Returns user and profile information

**Token Refresh:**

- `POST /auth/refresh/` - Refresh access token
- Requires refresh token
- Returns new access token

**Logout:**

- `POST /auth/logout/` - Logout user
- Invalidates refresh token (if implemented)

## 9. User Endpoints (v2)

### Endpoints

**Profile Management:**

- `GET /users/profile/` - Get user profile
- `PUT /users/profile/` - Update user profile
- `POST /users/profile/avatar/` - Upload avatar image

**Admin Operations:**

- `POST /users/promote-to-admin/` - Promote user to admin (admin only)

**Features:**

- Automatic profile creation if missing
- Partial updates (only provided fields)
- S3 or local file storage for avatars
- Presigned URLs for S3 avatars

## 10. Key Patterns and Conventions

### Dependency Injection Pattern

**Database Session:**

- Always injected via `Depends(get_db)`
- Automatic commit on success
- Automatic rollback on exception

**Authentication:**

- v1: Write keys via headers
- v2: JWT tokens via `get_current_user`

**Filter Parameters:**

- Resolved via dependency functions
- Pydantic validation
- Multi-value parameter handling

### Logging Pattern

**Function Logging:**

- `@log_function_call` decorator on endpoints
- Logs entry, exit, arguments, and results
- Configurable log levels

**Request Logging:**

- LoggingMiddleware logs all requests
- TimingMiddleware logs request duration
- Structured logging with context

### Error Response Pattern

**Consistent Structure:**
```json
{
    "detail": "Error message",
    "error_code": "ERROR_CODE"  // For AppException
}
```

**HTTP Status Codes:**

- 200: Success
- 201: Created
- 400: Bad Request (validation errors)
- 401: Unauthorized (authentication required)
- 403: Forbidden (insufficient permissions)
- 404: Not Found
- 422: Unprocessable Entity (validation errors)
- 500: Internal Server Error

### Response Model Pattern

**Pydantic Models:**

- Request models: Input validation
- Response models: Output serialization
- Filter models: Query parameter validation
- Common models: Shared structures (CountResponse, CursorPage, etc.)

## 11. API Version Differences

### v1 Characteristics

- Write key authentication
- Legacy endpoints
- Direct service calls

### v2 Characteristics

- JWT authentication
- User management
- Apollo integration
- AI chat functionality
- Export management

## Summary

The API layer demonstrates:

1. **Clear Versioning**: Separate v1 and v2 with different authentication
2. **Consistent Patterns**: Filter resolution, pagination, error handling
3. **Security**: JWT authentication, role-based access control
5. **Developer Experience**: Comprehensive logging, clear error messages, OpenAPI docs

The architecture supports both legacy API clients (v1) and modern authenticated clients (v2), with clear migration path.

