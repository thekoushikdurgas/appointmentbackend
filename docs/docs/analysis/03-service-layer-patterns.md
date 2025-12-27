# Service Layer Patterns Analysis

## Overview

The service layer orchestrates business logic, data transformations, and coordinates between API endpoints and repositories. This document analyzes service layer architecture, patterns, and implementations.

## 1. Service Layer Architecture

### Design Principles

**Separation of Concerns:**
- Services contain business logic
- Repositories handle data access
- Services coordinate multiple repositories when needed
- Services transform data between models and schemas

**Dependency Injection:**
- Services accept repositories as constructor parameters
- Default to creating repositories if not provided
- Enables testing with mock repositories

**Error Handling:**
- Services raise `HTTPException` for business logic errors
- Logging at service level for debugging
- Validation errors passed through from Pydantic

### Service Structure Pattern

**Standard Service Class:**
```python
class ServiceName:
    """Business logic for [domain]."""
    
    def __init__(self, repository: Optional[Repository] = None):
        """Initialize with repository dependency."""
        self.logger = get_logger(__name__)
        self.repository = repository or Repository()
    
    async def operation(self, session: AsyncSession, ...):
        """Business logic operation."""
        # 1. Validate/transform input
        # 2. Call repository
        # 3. Transform output
        # 4. Return result
```

## 2. ContactsService Analysis

### Purpose

Orchestrates contact-related business logic including:
- Contact CRUD operations
- Contact listing with filters and pagination
- Data transformation between models and schemas
- Company relationship handling

### Key Methods

#### `create_contact`
**Flow:**
1. Normalize input data (UUID, text fields, sequences)
2. Generate UUID if not provided
3. Normalize text fields (remove quotes, handle placeholders)
4. Validate numeric fields (non-negative)
5. Normalize sequences (industries, keywords, technologies)
6. Set timestamps
7. Call repository to create
8. Commit transaction
9. Retrieve and return hydrated detail

**Data Normalization:**
- `_normalize_text()`: Cleans text, removes quotes, handles placeholders
- `_normalize_sequence()`: Cleans arrays, removes empty values
- `_coalesce_text()`: Returns first non-empty value

#### `list_contacts`
**Flow:**
1. Log active filters
2. Warn if unlimited query (limit=None)
3. Call repository with filters, limit, offset
4. Transform repository results to schema objects
5. Build pagination links (next/previous)
6. Return `CursorPage` with results and metadata

**Pagination:**
- Supports both cursor and offset pagination
- Builds next link only if limit reached
- Builds previous link if offset > 0
- Uses `build_cursor_link()` or `build_pagination_link()`

#### `count_contacts`
**Flow:**
1. Call repository count method
2. Return `CountResponse` with count

#### `get_contact_by_uuid`
**Flow:**
1. Call repository to retrieve contact
2. Raise 404 if not found
3. Hydrate contact with related data
4. Return `ContactDetail`

### Data Transformation

#### `_hydrate_contact`
**Purpose:** Transform database models to API schema

**Process:**
1. Extract contact fields
2. Extract company fields (if company exists)
3. Extract contact metadata fields
4. Extract company metadata fields
5. Combine into `ContactListItem` or `ContactDetail`

**Handles:**
- Null company relationships
- Null metadata relationships
- Field mapping (e.g., `company.name` → `company`)
- Array field formatting (departments, industries, etc.)

## 3. ApolloAnalysisService Analysis

### Purpose

Analyzes Apollo.io URLs and maps parameters to contact filters. This is a complex service with multiple responsibilities.

### Key Methods

#### `analyze_url`
**Flow:**
1. Validate URL (not empty, is string, contains "apollo.io")
2. Check cache for existing analysis
3. Parse URL structure (base, hash path, query string)
4. Extract query parameters
5. Categorize parameters by type
6. Build parameter details with descriptions
7. Generate statistics
8. Cache result (1 hour TTL)
9. Return `ApolloUrlAnalysisResponse`

**URL Parsing:**
- Handles hash-based routing (`#/path?params`)
- Handles standard query strings
- URL-decodes parameter values
- Preserves multi-value parameters

**Parameter Categorization:**
- Maps parameters to categories (Person Filters, Organization Filters, etc.)
- Provides descriptions for each parameter
- Tracks uncategorized parameters in "Other"

**Caching:**
- Uses query cache with 1 hour TTL
- Normalizes URLs for consistent cache keys
- MD5 hash for cache key generation

#### `map_to_contact_filters`
**Purpose:** Convert Apollo parameters to `ContactFilterParams`

**Mapping Strategy:**

**1. Pagination & Sorting:**
- `page` → `page` (integer)
- `sortByField` + `sortAscending` → `ordering` (with `-` prefix for descending)

**2. Person Filters:**
- `personTitles[]` → `title` (comma-separated, OR logic)
- `personNotTitles[]` → `exclude_titles` (list)
- `personLocations[]` → `contact_location` (comma-separated)
- `personNotLocations[]` → `exclude_contact_locations` (list)
- `personSeniorities[]` → `seniority` (comma-separated)
- `personDepartmentOrSubdepartments[]` → `department` (comma-separated)

**3. Organization Filters:**
- `organizationNumEmployeesRanges[]` → `employees_min`, `employees_max`
- `organizationLocations[]` → `company_location` (comma-separated)
- `organizationNotLocations[]` → `exclude_company_locations` (list)
- `revenueRange[min/max]` → `annual_revenue_min`, `annual_revenue_max`

**4. Email Filters:**
- `contactEmailStatusV2[]` → `email_status` (comma-separated)

**5. Keyword Filters:**
- `qOrganizationKeywordTags[]` → `keywords` (comma-separated)
- `qNotOrganizationKeywordTags[]` → `exclude_keywords` (list)
- `qKeywords` → `search` (general search term)

**6. Special Handling:**

**Title Normalization:**
- `includeSimilarTitles=true` → Uses jumble mapping
- `_jumble_title()`: Splits title into words
- `_normalize_title()`: Sorts words alphabetically for matching

**Industry Tags:**
- `organizationIndustryTagIds[]` → Converts Tag IDs to industry names
- Uses `get_industry_names_from_ids()` utility
- Falls back to Tag IDs if conversion fails

**Unmapped Parameters:**
- Tracks parameters that can't be mapped
- Returns reason for unmapping (e.g., "ID-based filter", "Apollo-specific feature")
- Used for reporting and debugging

### Pattern Detection

**ApolloPatternDetector:**
- Detects common filter patterns
- Used for optimization hints
- Patterns include:
  - High frequency location filters
  - High frequency employee range filters
  - Executive search patterns
  - Combined filter patterns

## 4. CompaniesService Analysis

### Purpose

Similar to ContactsService but for company operations.

### Key Differences

**Company-Specific Fields:**
- `employees_count`, `annual_revenue`, `total_funding`
- `industries`, `keywords`, `technologies` (arrays)
- `address`, `text_search`

**Operations:**
- `create_company`: Creates company with metadata
- `update_company`: Partial updates
- `delete_company`: Soft delete (if implemented)
- `list_companies`: With filters and pagination
- `get_company_by_uuid`: Retrieves with metadata

### Data Normalization

Uses same normalization functions as ContactsService:
- `_normalize_text()`: Text field cleaning
- `_normalize_sequence()`: Array field cleaning
- Numeric validation (non-negative)

## 5. UserService Analysis

### Purpose

Handles user authentication and profile management.

### Key Methods

#### `register_user`
**Flow:**
1. Check if user exists (by email)
2. Hash password
3. Create user record
4. Create user profile with default values
5. Generate access and refresh tokens
6. Update `last_sign_in_at`
7. Return (user, access_token, refresh_token)

**Profile Creation:**
- Default role: "Member"
- Default notifications: All enabled
- Automatic creation on registration

#### `authenticate_user`
**Flow:**
1. Find user by email
2. Verify password
3. Check if user is active
4. Update `last_sign_in_at`
5. Generate tokens
6. Return (user, access_token, refresh_token)

#### `get_user_profile`
**Flow:**
1. Retrieve profile by user ID
2. If not found, create default profile
3. Convert avatar URL to full URL
4. Return `ProfileResponse`

**Avatar URL Handling:**
- Detects S3 keys vs local paths
- Generates presigned URLs for S3
- Prepends `BASE_URL` for local paths
- Handles full URLs (returns as-is)

#### `update_user_profile`
**Flow:**
1. Retrieve existing profile
2. Update provided fields (partial update)
3. Merge notification preferences (not replace)
4. Handle avatar upload (if provided)
5. Save and return updated profile

#### `upload_avatar`
**Flow:**
1. Validate file type (image)
2. Read file content
3. Upload to S3 or local storage
4. Update profile with avatar URL/key
5. Return avatar URL

**Storage:**
- S3: Uses `S3Service` with presigned URLs
- Local: Saves to `UPLOAD_DIR/avatars/`
- Returns appropriate URL format

## 6. ImportService Analysis

### Purpose

Manages contact import jobs and error tracking.

### Key Methods

#### `create_job`
**Flow:**
1. Create `ContactImportJob` record
2. Set initial status (pending)
3. Store file path and metadata
4. Commit transaction
5. Return job object

#### `set_status`
**Flow:**
1. Update job status
2. Update progress counters
3. Store error message (if any)
4. Commit transaction

**Status Values:**
- `pending`: Job created, not started
- `processing`: Currently processing
- `completed`: Successfully completed
- `failed`: Failed with errors

#### `increment_progress`
**Flow:**
1. Increment `processed_rows` counter
2. Update `error_count` if errors
3. Commit transaction

#### `add_error`
**Flow:**
1. Create `ContactImportError` record
2. Link to import job
3. Store error details (row, column, message)
4. Commit transaction

#### `get_job_with_errors`
**Flow:**
1. Retrieve job by ID
2. Retrieve associated errors
3. Combine into `ImportJobWithErrors`
4. Return result

## 7. ExportService Analysis

### Purpose

Manages contact/company export jobs and CSV generation.

### Key Methods

#### `create_export`
**Flow:**
1. Create `UserExport` record
2. Store UUIDs to export
3. Set status to `pending`
4. Commit transaction
5. Return export object

#### `generate_csv`
**Flow:**
1. Fetch contacts with all relations
2. Define CSV fieldnames
3. Write CSV to buffer
4. Upload to S3 or save locally
5. Return file path/key

**CSV Fields:**
- Contact fields (uuid, name, email, title, etc.)
- Company fields (name, employees, revenue, etc.)
- Metadata fields (phones, addresses, URLs, etc.)

**Storage:**
- S3: Uploads CSV file, returns S3 key
- Local: Saves to `UPLOAD_DIR/exports/`, returns file path

#### `get_export_download_url`
**Flow:**
1. Retrieve export by ID
2. Check if file exists
3. Generate presigned URL (S3) or local URL
4. Return download URL

## 8. Common Patterns Across Services

### Data Normalization Pattern

**Text Normalization:**
```python
def _normalize_text(value: Any, *, allow_placeholder: bool = False) -> Optional[str]:
    """Clean text values."""
    if value is None:
        return None
    text = str(value).strip()
    # Remove wrapping quotes
    # Handle placeholders
    # Return None if empty
    return text
```

**Sequence Normalization:**
```python
def _normalize_sequence(values: Optional[Iterable[Any]]) -> list[str]:
    """Clean array values."""
    if not values:
        return []
    cleaned = []
    for value in values:
        normalized = _normalize_text(value)
        if normalized:
            cleaned.append(normalized)
    return cleaned
```

### Error Handling Pattern

**Consistent Error Handling:**
```python
try:
    result = await repository.operation(session, ...)
    await session.commit()
    return result
except ValueError as exc:
    raise HTTPException(status_code=400, detail=str(exc)) from exc
except Exception as exc:
    logger.exception("Operation failed: %s", exc)
    raise HTTPException(status_code=500, detail="Operation failed") from exc
```

### Logging Pattern

**Structured Logging:**
- Entry logging with parameters
- Exit logging with results
- Warning for unlimited queries
- Error logging with exception details
- Debug logging for detailed flow

### Transaction Management

**Commit Pattern:**
- Services commit transactions after repository operations
- Explicit commits for clarity
- Rollback handled by `get_db()` dependency

## 9. Service Dependencies

### Repository Dependencies

**Single Repository:**
- `ContactsService` → `ContactRepository`
- `CompaniesService` → `CompanyRepository`
- `UserService` → `UserRepository`, `UserProfileRepository`

**Multiple Repositories:**
- `ImportService` → `ImportJobRepository`, `ImportErrorRepository`
- `ExportService` → `ContactRepository`, `CompanyRepository`

### External Service Dependencies

**S3Service:**
- Used by `UserService` (avatar uploads)
- Used by `ExportService` (CSV storage)
- Handles presigned URL generation

**Query Cache:**
- Used by `ApolloAnalysisService` (URL analysis caching)
- Redis-based caching with TTL

## 10. Data Transformation Patterns

### Model to Schema Transformation

**Hydration Pattern:**
```python
def _hydrate_contact(contact, company, contact_meta, company_meta):
    """Transform models to schema."""
    return ContactListItem(
        uuid=contact.uuid,
        first_name=contact.first_name,
        # ... extract all fields
        company=company.name if company else None,
        # ... handle nulls
    )
```

**Key Features:**
- Handles null relationships gracefully
- Maps nested fields (company.name → company)
- Formats arrays (departments, industries)
- Combines metadata fields

### Schema to Model Transformation

**Creation Pattern:**
```python
async def create_entity(session, payload: CreateSchema):
    """Create entity from schema."""
    data = payload.model_dump()
    # Normalize data
    # Set defaults
    # Create via repository
    # Return hydrated detail
```

## 11. Performance Considerations

### Caching

**ApolloAnalysisService:**
- Caches URL analysis results (1 hour TTL)
- Normalizes URLs for consistent keys
- Reduces redundant parsing

### Batch Operations

**ImportService:**
- Tracks progress in batches
- Increments counters efficiently
- Stores errors separately

### Query Optimization

**Services delegate to repositories:**
- Services don't optimize queries directly
- Repositories handle query optimization
- Services focus on business logic

## Summary

The service layer demonstrates:

1. **Clear Separation**: Business logic separated from data access
2. **Consistent Patterns**: Normalization, error handling, logging
3. **Data Transformation**: Model ↔ Schema conversion
4. **Transaction Management**: Explicit commits
5. **Dependency Injection**: Testable design
6. **Complex Logic**: Apollo URL parsing and mapping
7. **External Integration**: S3, caching, background tasks

Services act as the orchestration layer, coordinating repositories, transforming data, and implementing business rules while maintaining clean separation of concerns.

