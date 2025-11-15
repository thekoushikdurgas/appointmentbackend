# Contacts API Documentation

Complete API documentation for contact management endpoints, including listing, filtering, searching, field-specific queries, and import functionality.

## Base URL

```txt
http://54.87.173.234:8000
```

**API Version:** All endpoints are under `/api/v1/contacts/`

## Authentication

All contact endpoints require user authentication. Import endpoints require admin authentication.

**User Authentication (for all endpoints):**

```txt
Authorization: Bearer <access_token>
```

**Admin Authentication (for import and write endpoints):**

```txt
Authorization: Bearer <admin_access_token>
X-Contacts-Write-Key: <write_key>  (required for POST /api/v1/contacts/)
```

---

## Common Headers

- `X-Request-Id` (optional): Request tracking ID that will be echoed back in the response header
- `Origin` (optional): Origin header for CORS testing. Include this header to verify CORS response headers. Example: `Origin: http://localhost:3000`

### CORS Testing

All endpoints support CORS (Cross-Origin Resource Sharing) for browser-based requests. When testing CORS, include an `Origin` header in your requests.

**Expected CORS Response Headers:**

- `Access-Control-Allow-Origin: <origin>` (matches the Origin header value)
- `Access-Control-Allow-Credentials: true`
- `Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS, PATCH`
- `Access-Control-Allow-Headers: *`
- `Access-Control-Max-Age: 3600`

**Note:** The Origin header is optional and only needed when testing CORS behavior. The API automatically handles CORS preflight (OPTIONS) requests.

---

## Main Contact Endpoints

### GET /api/v1/contacts/ - List Contacts

Retrieve a paginated list of contacts with optional filtering, searching, and ordering.

**Headers:**

- `X-Request-Id` (optional): Request tracking ID

**Query Parameters:**

#### Text Filters (case-insensitive contains)

All text filters support partial matching:

- `first_name` (string): Filter by first name
- `last_name` (string): Filter by last name
- `title` (string): Filter by job title
- `company` (string): Filter by company name
- `company_name_for_emails` (string): Filter by company email name
- `email` (string): Filter by email address
- `departments` (string): Filter by departments
- `work_direct_phone` (string): Filter by work direct phone
- `home_phone` (string): Filter by home phone
- `mobile_phone` (string): Filter by mobile phone
- `corporate_phone` (string): Filter by corporate phone
- `other_phone` (string): Filter by other phone
- `city` (string): Filter by person city
- `state` (string): Filter by person state
- `country` (string): Filter by person country
- `technologies` (string): Filter by technologies
- `keywords` (string): Filter by keywords
- `person_linkedin_url` (string): Filter by person LinkedIn URL
- `website` (string): Filter by website
- `company_linkedin_url` (string): Filter by company LinkedIn URL
- `facebook_url` (string): Filter by Facebook URL
- `twitter_url` (string): Filter by Twitter URL
- `company_address` (string): Filter by company address
- `company_city` (string): Filter by company city
- `company_state` (string): Filter by company state
- `company_country` (string): Filter by company country
- `company_phone` (string): Filter by company phone
- `industry` (string): Filter by industry
- `latest_funding` (string): Filter by latest funding info
- `last_raised_at` (string): Filter by last raised date

#### Exact Match Filters (case-insensitive exact)

- `email_status` (string): Filter by email status (exact match)
- `primary_email_catch_all_status` (string): Filter by catch-all status
- `stage` (string): Filter by stage (exact match)
- `seniority` (string): Filter by seniority (exact match)
- `employees_count` (integer): Exact match for number of employees
- `annual_revenue` (integer): Exact match for annual revenue (in dollars)
- `total_funding` (integer): Exact match for total funding (in dollars)

#### Numeric Range Filters

- `employees_min` (integer): Minimum number of employees
- `employees_max` (integer): Maximum number of employees
- `annual_revenue_min` (integer): Minimum annual revenue (in dollars)
- `annual_revenue_max` (integer): Maximum annual revenue (in dollars)
- `total_funding_min` (integer): Minimum total funding (in dollars)
- `total_funding_max` (integer): Maximum total funding (in dollars)
- `latest_funding_amount_min` (integer): Minimum latest funding amount (in dollars)
- `latest_funding_amount_max` (integer): Maximum latest funding amount (in dollars)

#### Location Filters

- `company_location` (string): Filter by company location text (searches Company.text_search covering address, city, state, country)
- `contact_location` (string): Filter by contact location text (searches Contact.text_search covering person-level location metadata)

#### Exclusion Filters (multi-value, case-insensitive)

These filters exclude contacts matching any of the provided values:

- `exclude_company_ids` (array of strings): Exclude contacts from specified company UUIDs
- `exclude_titles` (array of strings): Exclude contacts with specified titles
- `exclude_company_locations` (array of strings): Exclude contacts from companies in specified locations
- `exclude_contact_locations` (array of strings): Exclude contacts in specified locations
- `exclude_seniorities` (array of strings): Exclude contacts with specified seniority levels
- `exclude_departments` (array of strings): Exclude contacts in specified departments
- `exclude_technologies` (array of strings): Exclude contacts from companies using specified technologies
- `exclude_keywords` (array of strings): Exclude contacts from companies with specified keywords
- `exclude_industries` (array of strings): Exclude contacts from companies in specified industries

**Note:** Exclusion filters accept multiple values as comma-separated strings or repeated query parameters (e.g., `?exclude_titles=Intern&exclude_titles=Junior` or `?exclude_titles=Intern,Junior`)

#### Date Range Filters (ISO datetime format)

- `created_at_after` (string): Filter contacts created after this date (ISO format: `2024-01-01T00:00:00Z`)
- `created_at_before` (string): Filter contacts created before this date
- `updated_at_after` (string): Filter contacts updated after this date
- `updated_at_before` (string): Filter contacts updated before this date

#### Search and Ordering

- `search` (string): Full-text search across multiple fields (first_name, last_name, title, company, email, city, state, country, etc.)
- `ordering` (string): Comma-separated fields to order by. Valid fields: `created_at`, `updated_at`, `employees`, `annual_revenue`, `total_funding`, `latest_funding_amount`, `first_name`, `last_name`, `title`, `company`, `email`, `city`, `state`, `country`, `company_address`, `company_city`, `company_state`, `company_country`, etc. Prepend `-` for descending.

#### Pagination Parameters

- `limit` (integer, optional): Number of results per page. **If not provided, returns all matching contacts (unlimited).** When provided, limits results to the specified number (capped at MAX_PAGE_SIZE).
- `offset` (integer): Offset for pagination (used when custom ordering is applied)
- `page_size` (integer): Page size for cursor pagination (used when ordering by created_at, default: 25, max: 100)

#### Advanced Controls

- `view` (string): When set to `"simple"`, returns simplified contact data (`ContactSimpleItem`) with only essential fields (id, uuid, first_name, last_name, title, location, company_name, person_linkedin_url, company_domain). Omit for full `ContactListItem` response.
- `include_meta` (boolean): When `true`, includes the `meta_data` JSON column in list responses. Defaults to `false` for lean payloads.
- `use_replica` (boolean): When `true` and a replica database is configured, routes reads to that replica. Defaults to the `CONTACTS_DEFAULT_REPLICA_READ` setting.

**Response:**

**With Cursor Pagination (default ordering by created_at):**

```json
{
  "next": "http://54.87.173.234:8000/api/v1/contacts/?cursor=cj0xJnN1YiI6IjE2ODAwMDAwMDAwMDAwMDAwMDAwMCJ9",
  "previous": null,
  "results": [
    {
      "id": 1,
      "first_name": "John",
      "last_name": "Doe",
      "title": "CEO",
      "company": "Acme Corp",
      "email": "john@acme.com",
      "email_status": "valid",
      "primary_email_catch_all_status": "",
      "seniority": "c-level",
      "departments": "executive",
      "work_direct_phone": "+1234567890",
      "home_phone": "",
      "mobile_phone": "+1234567891",
      "corporate_phone": "",
      "other_phone": "",
      "stage": "lead",
      "employees": 100,
      "industry": "Technology",
      "keywords": "enterprise, saas, cloud",
      "person_linkedin_url": "https://linkedin.com/in/johndoe",
      "website": "https://acme.com",
      "company_linkedin_url": "https://linkedin.com/company/acme",
      "facebook_url": "",
      "twitter_url": "",
      "city": "San Francisco",
      "state": "CA",
      "country": "United States",
      "company_address": "123 Main St",
      "company_city": "San Francisco",
      "company_state": "CA",
      "company_country": "United States",
      "company_phone": "+1234567892",
      "technologies": "Python, Django, PostgreSQL",
      "annual_revenue": 10000000,
      "total_funding": 50000000,
      "latest_funding": "Series B",
      "latest_funding_amount": 20000000,
      "last_raised_at": "2023-06-01",
      "meta_data": {},
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

**Response Metadata (`meta` block):**

Every list response now ships with a `meta` section describing how the data was produced. Typical fields include:

```json
"meta": {
  "strategy": "cursor",
  "count_mode": "estimated",
  "count": 125000,
  "filters_applied": false,
  "ordering": "-created_at",
  "returned_records": 25,
  "page_size": 25,
  "page_size_cap": 100,
  "using_replica": false
}
```

**With Limit-Offset Pagination (custom ordering):**

```json
{
  "next": "http://54.87.173.234:8000/api/v1/contacts/?ordering=-employees&limit=25&offset=25",
  "previous": "http://54.87.173.234:8000/api/v1/contacts/?ordering=-employees&limit=25&offset=0",
  "results": [
    {
      "id": 1,
      "first_name": "John",
      "last_name": "Doe",
      ...
    }
  ]
}
```

**With view=simple:**

```json
{
  "next": "http://54.87.173.234:8000/api/v1/contacts/?view=simple&cursor=...",
  "previous": null,
  "results": [
    {
      "id": 1,
      "uuid": "abc123-def456-ghi789",
      "first_name": "John",
      "last_name": "Doe",
      "title": "CEO",
      "location": {
        "city": "San Francisco",
        "state": "CA",
        "country": "United States"
      },
      "company_name": "Acme Corp",
      "person_linkedin_url": "https://linkedin.com/in/johndoe",
      "company_domain": "https://acme.com"
    }
  ]
}
```

**Error Response (400 Bad Request):**

```json
{
  "detail": "Invalid ordering field(s): invalid_field. Valid fields are: created_at, updated_at, employees, annual_revenue, total_funding, latest_funding_amount, first_name, last_name, title, company, email, city, state, country, company_address, company_city, company_state, company_country, ..."
}
```

**Error Response (500 Internal Server Error):**

```json
{
  "detail": "An error occurred while processing the request. Please check your query parameters and try again."
}
```

**Status Codes:**

- `200 OK`: Success
- `400 Bad Request`: Invalid query parameters (e.g., invalid ordering field)
- `500 Internal Server Error`: Server error

**Example Requests:**

```txt
GET /api/v1/contacts/?first_name=John&country=United States&employees_min=50&ordering=-employees
GET /api/v1/contacts/?search=technology&page_size=10
GET /api/v1/contacts/?title=cto&company_name_for_emails=inc&industry=software&ordering=-employees,company&limit=25&offset=0
GET /api/v1/contacts/?created_at_after=2024-01-01T00:00:00Z&ordering=-created_at
GET /api/v1/contacts/?view=simple&company=Acme&limit=10
```

**Notes:**

- Default ordering is by `-created_at` (newest first), which uses cursor pagination for better performance
- Custom ordering uses limit-offset pagination
- Cursor pagination does not include a count (for performance)
- Limit-offset pagination also does not include a count (optimized for performance)
- All text searches are case-insensitive
- Multiple filters can be combined with `&`
- Title substring searches now use a trigram GIN index and `email_status` exact matches use a functional index on `UPPER(email_status)`, keeping combinations like `?title=manager&email_status=Verified` under three seconds on production-sized datasets.
- Responses are cached for short periods. A cache hit adds `X-Cache-Hit` to the response headers; send `Cache-Control: no-cache` to bypass.

---

### GET /api/v1/contacts/{contact_uuid}/ - Retrieve Contact

Get detailed information about a specific contact by UUID.

**Headers:**

- `X-Request-Id` (optional): Request tracking ID

**Path Parameters:**

- `contact_uuid` (string): Contact UUID

**Query Parameters:**

- None

**Response:**

**Success (200 OK):**

```json
{
  "uuid": "abc123-def456-ghi789",
  "first_name": "John",
  "last_name": "Doe",
  "title": "CEO",
  "company": "Acme Corp",
  "company_name_for_emails": "Acme Corp",
  "email": "john@acme.com",
  "email_status": "valid",
  "primary_email_catch_all_status": "",
  "seniority": "c-level",
  "departments": "executive",
  "work_direct_phone": "+1234567890",
  "home_phone": "",
  "mobile_phone": "+1234567891",
  "corporate_phone": "",
  "other_phone": "",
  "stage": "lead",
  "employees": 100,
  "industry": "Technology",
  "keywords": "enterprise, saas, cloud",
  "person_linkedin_url": "https://linkedin.com/in/johndoe",
  "website": "https://acme.com",
  "company_linkedin_url": "https://linkedin.com/company/acme",
  "facebook_url": "",
  "twitter_url": "",
  "city": "San Francisco",
  "state": "CA",
  "country": "United States",
  "company_address": "123 Main St",
  "company_city": "San Francisco",
  "company_state": "CA",
  "company_country": "United States",
  "company_phone": "+1234567892",
  "technologies": "Python, Django, PostgreSQL",
  "annual_revenue": 10000000,
  "total_funding": 50000000,
  "latest_funding": "Series B",
  "latest_funding_amount": 20000000,
  "last_raised_at": "2023-06-01",
  "meta_data": {},
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

**Error (404 Not Found):**

```json
{
  "detail": "Not found."
}
```

**Status Codes:**

- `200 OK`: Success
- `404 Not Found`: Contact not found

---

### GET /api/v1/contacts/count/ - Get Contact Count

Get the total count of contacts, optionally filtered. Uses PostgreSQL estimated count for unfiltered queries (fast) and actual count for filtered queries (accurate).

**Headers:**

- `X-Request-Id` (optional): Request tracking ID

**Query Parameters:**

All filter parameters from `/api/contacts/` are supported:

- All text filters (first_name, last_name, title, company, etc.)
- All exact filters (email_status, stage, seniority, etc.)
- All numeric range filters (employees_min, employees_max, etc.)
- All date range filters (created_at_after, created_at_before, etc.)

**Response:**

**Unfiltered (uses PostgreSQL estimate, cached for 5 minutes):**

```json
{
  "count": 50000
}
```

**Filtered (uses actual count):**

```json
{
  "count": 1234
}
```

**Error Response (500 Internal Server Error):**

```json
{
  "detail": "Error counting contacts. The query may be too complex or timeout. Please try with simpler filters."
}
```

Or:

```json
{
  "detail": "Error counting contacts. Please try again later."
}
```

**Status Codes:**

- `200 OK`: Success
- `500 Internal Server Error`: Error counting contacts

**Example Requests:**

```txt
GET /api/v1/contacts/count/
GET /api/v1/contacts/count/?country=United States&city=San Francisco&employees_min=50
GET /api/v1/contacts/count/?email_status=valid&industry=Technology
```

**Notes:**

- Unfiltered queries use PostgreSQL's estimated row count (very fast, cached for 5 minutes)
- Filtered queries use actual COUNT(*) which can be slow on large datasets
- For complex filters, the count operation may timeout - try simpler filters

---

### GET /api/v1/contacts/count/uuids/ - Get Contact UUIDs

Get a list of contact UUIDs that match the provided filters. Returns count and list of UUIDs. Useful for bulk operations or exporting specific contact sets.

**Headers:**

- `X-Request-Id` (optional): Request tracking ID

**Query Parameters:**

**This endpoint accepts ALL the same query parameters as `/api/v1/contacts/count/` endpoint, plus an additional parameter:**

- `limit` (integer, optional): Maximum number of UUIDs to return. **If not provided, returns all matching UUIDs (unlimited).** When provided, limits results to the specified number.

All filter parameters from `/api/v1/contacts/` are supported:

- All text filters (first_name, last_name, title, company, etc.)
- All exact filters (email_status, stage, seniority, etc.)
- All numeric range filters (employees_min, employees_max, etc.)
- All date range filters (created_at_after, created_at_before, updated_at_after, updated_at_before, etc.)
- All exclude filters (exclude_titles, exclude_seniorities, exclude_departments, exclude_company_locations, exclude_contact_locations, exclude_technologies, exclude_keywords, exclude_industries, exclude_company_ids, etc.)
- Search and distinct parameters

**Response:**

```json
{
  "count": 1234,
  "uuids": ["uuid1", "uuid2", "uuid3", ...]
}
```

**Status Codes:**

- `200 OK`: Success
- `400 Bad Request`: Invalid query parameters
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Error retrieving UUIDs

**Example Requests:**

```txt
GET /api/v1/contacts/count/uuids/
GET /api/v1/contacts/count/uuids/?country=United States&city=San Francisco&employees_min=50
GET /api/v1/contacts/count/uuids/?email_status=valid&industry=Technology&limit=1000
```

**Notes:**

- Returns all matching UUIDs by default (unlimited) unless `limit` parameter is provided
- Useful for bulk operations, exports, or when you only need UUIDs without full contact data
- All the same filtering capabilities as the count endpoint

---

### POST /api/v1/contacts/ - Create Contact

Create a new contact. Requires admin authentication and the `X-Contacts-Write-Key` header.

**Headers:**

- `Authorization: Bearer <admin_access_token>` (required)
- `X-Contacts-Write-Key: <write_key>` (required)
- `X-Request-Id` (optional): Request tracking ID

**Request Body:**

```json
{
  "uuid": "optional-uuid-or-auto-generated",
  "first_name": "John",
  "last_name": "Doe",
  "company_id": "company-uuid",
  "email": "john@example.com",
  "title": "CEO",
  "departments": ["executive"],
  "mobile_phone": "+1234567890",
  "email_status": "valid",
  "text_search": "San Francisco, CA",
  "seniority": "c-level"
}
```

**Response:**

**Success (201 Created):**

Returns a `ContactDetail` object (same structure as GET /api/v1/contacts/{id}/).

**Error (403 Forbidden):**

```json
{
  "detail": "Forbidden"
}
```

**Status Codes:**

- `201 Created`: Contact created successfully
- `403 Forbidden`: Missing or invalid write key
- `401 Unauthorized`: Authentication required

---

## Field-Specific Endpoints

These endpoints return only the `id` and the specific field value for each contact. Useful for getting unique values or searching specific fields.

### Common Query Parameters (for all field endpoints)

- `search` (string): Search term to filter results (case-insensitive, searches within the field)
- `distinct` (boolean): If `true`, returns only distinct field values (default: `false`)
- `limit` (integer, optional): Maximum number of results. **If not provided, returns all matching values (unlimited).** When provided, limits results to the specified number.
- `offset` (integer): Offset for pagination

### GET /api/v1/contacts/title/ - List Titles

Get list of contacts with only id and title field.

**Headers:**

- `X-Request-Id` (optional): Request tracking ID

**Query Parameters:**

- `search` (string): Search term to filter results (case-insensitive, searches within title field)
- `distinct` (boolean): If `true`, returns only distinct title values (default: `false`)
- `limit` (integer, optional): Maximum number of results. **If not provided, returns all matching values (unlimited).** When provided, limits results to the specified number.
- `offset` (integer): Offset for pagination

**Response:**

```json
{
  "next": "http://54.87.173.234:8000/api/v1/contacts/title/?limit=25&offset=25",
  "previous": null,
  "results": [
    {
      "id": 1,
      "title": "CEO"
    },
    {
      "id": 2,
      "title": "CTO"
    }
  ]
}
```

**Status Codes:**

- `200 OK`: Success
- `400 Bad Request`: Invalid parameters
- `500 Internal Server Error`: Server error

**Example Requests:**

```txt
GET /api/v1/contacts/title/?search=technology
GET /api/v1/contacts/title/?distinct=true&limit=50
```

---

### GET /api/v1/contacts/company/ - List Companies

Get list of contacts with only id and company field.

**Headers:**

- `X-Request-Id` (optional): Request tracking ID

**Query Parameters:**

- `search` (string): Search term to filter results (case-insensitive)
- `distinct` (boolean): If `true`, returns only distinct company values
- `limit` (integer, optional): Maximum number of results. **If not provided, returns all matching values (unlimited).** When provided, limits results to the specified number.
- `offset` (integer): Offset for pagination

**Response:**

```json
{
  "next": "http://54.87.173.234:8000/api/v1/contacts/company/?limit=25&offset=25",
  "previous": null,
  "results": [
    {
      "id": 1,
      "company": "Acme Corp"
    },
    {
      "id": 2,
      "company": "Tech Inc"
    }
  ]
}
```

**Status Codes:**

- `200 OK`: Success

**Example Requests:**

```txt
GET /api/v1/contacts/company/?search=tech
GET /api/v1/contacts/company/?distinct=true
```

---

### GET /api/v1/contacts/industry/ - List Industries

Get list of contacts with only id and industry field.

**Headers:**

- `X-Request-Id` (optional): Request tracking ID

**Query Parameters:**

- `search` (string): Search term to filter results (case-insensitive)
- `distinct` (boolean): If `true`, returns only distinct industry values
- `separated` (boolean): If `true`, expands comma-separated industries into individual records (one record per industry). Each contact ID may appear multiple times.
- `limit` (integer, optional): Maximum number of results. **If not provided, returns all matching values (unlimited).** When provided, limits results to the specified number.
- `offset` (integer): Offset for pagination

**Response:**

```json
{
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "industry": "Technology"
    },
    {
      "id": 2,
      "industry": "Healthcare"
    }
  ]
}
```

**Status Codes:**

- `200 OK`: Success

---

### GET /api/v1/contacts/keywords/ - List Keywords

Get list of contacts with only id and keywords field. Supports expansion of comma-separated keywords.

**Headers:**

- `X-Request-Id` (optional): Request tracking ID

**Query Parameters:**

- `search` (string): Search term to filter results (case-insensitive)
  - When `separated=false`: Searches the comma-separated string
  - When `separated=true`: Uses two-stage filtering (pre-filter at DB level, then post-filter individual keywords after expansion)
- `separated` (boolean): If `true`, expands comma-separated keywords into individual records (one record per keyword). Each contact ID may appear multiple times.
- `distinct` (boolean): If `true`, returns only distinct keyword values. When combined with `separated=true`, returns unique individual keywords across all contacts.
- `limit` (integer, optional): Maximum number of results. **If not provided, returns all matching values (unlimited).** When provided, limits results to the specified number.
- `offset` (integer): Offset for pagination

**Response:**

**Without separated (default):**

```json
{
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "keywords": "enterprise, saas, cloud"
    },
    {
      "id": 2,
      "keywords": "startup, technology"
    }
  ]
}
```

**With separated=true:**

```json
{
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "keywords": "enterprise"
    },
    {
      "id": 1,
      "keywords": "saas"
    },
    {
      "id": 1,
      "keywords": "cloud"
    },
    {
      "id": 2,
      "keywords": "startup"
    },
    {
      "id": 2,
      "keywords": "technology"
    }
  ]
}
```

**With separated=true and distinct=true:**

```json
{
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "keywords": "enterprise"
    },
    {
      "id": 1,
      "keywords": "saas"
    },
    {
      "id": 1,
      "keywords": "cloud"
    },
    {
      "id": 2,
      "keywords": "startup"
    },
    {
      "id": 2,
      "keywords": "technology"
    }
  ]
}
```

**Status Codes:**

- `200 OK`: Success
- `400 Bad Request`: Invalid parameters
- `500 Internal Server Error`: Server error

**Example Requests:**

```txt
GET /api/contacts/keywords/?search=technology
GET /api/contacts/keywords/?separated=true
GET /api/contacts/keywords/?separated=true&search=cloud&distinct=true
```

**Notes:**

- When `separated=true`, the endpoint processes data in batches to avoid loading all contacts into memory
- The `search` parameter works differently when `separated=true`: it first pre-filters at the database level, then post-filters individual keywords after expansion
- Empty keywords are skipped when expanding

---

### GET /api/v1/contacts/technologies/ - List Technologies

Get list of contacts with only id and technologies field.

**Headers:**

- `X-Request-Id` (optional): Request tracking ID

**Query Parameters:**

- `search` (string): Search term to filter results (case-insensitive)
- `distinct` (boolean): If `true`, returns only distinct technology values
- `separated` (boolean): If `true`, expands comma-separated technologies into individual records (one record per technology). Each contact ID may appear multiple times.
- `limit` (integer, optional): Maximum number of results. **If not provided, returns all matching values (unlimited).** When provided, limits results to the specified number.
- `offset` (integer): Offset for pagination

**Response:**

```json
{
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "technologies": "Python, Django, PostgreSQL"
    },
    {
      "id": 2,
      "technologies": "JavaScript, React, Node.js"
    }
  ]
}
```

**Status Codes:**

- `200 OK`: Success

---

### GET /api/v1/contacts/company_address/ - List Company Addresses

Return address text for related companies, sourced from the `Company.text_search` column.

**Headers:**

- `X-Request-Id` (optional): Request tracking ID

**Query Parameters:**

- `search` (string): Search term to filter results (case-insensitive)
- `distinct` (boolean): If `true`, returns only distinct company address values
- `limit` (integer, optional): Maximum number of results. **If not provided, returns all matching values (unlimited).** When provided, limits results to the specified number.
- `offset` (integer): Offset for pagination

**Response:**

```json
{
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "company_address": "123 Main St, Austin, TX"
    },
    {
      "id": 2,
      "company_address": "456 Oak Ave, Denver, CO"
    }
  ]
}
```

**Status Codes:**

- `200 OK`: Success

---

### GET /api/v1/contacts/contact_address/ - List Contact Addresses

Return person-level address text sourced from the `Contact.text_search` column.

**Headers:**

- `X-Request-Id` (optional): Request tracking ID

**Query Parameters:**

- `search` (string): Search term to filter results (case-insensitive)
- `distinct` (boolean): If `true`, returns only distinct contact address values
- `limit` (integer, optional): Maximum number of results. **If not provided, returns all matching values (unlimited).** When provided, limits results to the specified number.
- `offset` (integer): Offset for pagination

**Response:**

```json
{
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "contact_address": "789 Market St, San Francisco, CA"
    },
    {
      "id": 2,
      "contact_address": "456 Sample Ave, Denver, CO"
    }
  ]
}
```

**Status Codes:**

- `200 OK`: Success

---

### GET /api/v1/contacts/city/ - List Contact Cities

Get list of contacts with only id and city field (from ContactMetadata).

**Headers:**

- `X-Request-Id` (optional): Request tracking ID

**Query Parameters:**

- `search` (string): Search term to filter results (case-insensitive)
- `distinct` (boolean): If `true`, returns only distinct city values
- `limit` (integer, optional): Maximum number of results. **If not provided, returns all matching values (unlimited).** When provided, limits results to the specified number.
- `offset` (integer): Offset for pagination

**Response:**

```json
{
  "next": null,
  "previous": null,
  "results": [
    "San Francisco",
    "New York",
    "Austin"
  ]
}
```

**Status Codes:**

- `200 OK`: Success

---

### GET /api/v1/contacts/state/ - List Contact States

Get list of contacts with only id and state field (from ContactMetadata).

**Headers:**

- `X-Request-Id` (optional): Request tracking ID

**Query Parameters:**

- `search` (string): Search term to filter results (case-insensitive)
- `distinct` (boolean): If `true`, returns only distinct state values
- `limit` (integer, optional): Maximum number of results. **If not provided, returns all matching values (unlimited).** When provided, limits results to the specified number.
- `offset` (integer): Offset for pagination

**Response:**

```json
{
  "next": null,
  "previous": null,
  "results": [
    "CA",
    "NY",
    "TX"
  ]
}
```

**Status Codes:**

- `200 OK`: Success

---

### GET /api/v1/contacts/country/ - List Contact Countries

Get list of contacts with only id and country field (from ContactMetadata).

**Headers:**

- `X-Request-Id` (optional): Request tracking ID

**Query Parameters:**

- `search` (string): Search term to filter results (case-insensitive)
- `distinct` (boolean): If `true`, returns only distinct country values
- `limit` (integer, optional): Maximum number of results. **If not provided, returns all matching values (unlimited).** When provided, limits results to the specified number.
- `offset` (integer): Offset for pagination

**Response:**

```json
{
  "next": null,
  "previous": null,
  "results": [
    "United States",
    "United Kingdom",
    "Canada"
  ]
}
```

**Status Codes:**

- `200 OK`: Success

---

### GET /api/v1/contacts/company_city/ - List Company Cities

Get list of contacts with only id and company city field (from CompanyMetadata).

**Headers:**

- `X-Request-Id` (optional): Request tracking ID

**Query Parameters:**

- `search` (string): Search term to filter results (case-insensitive)
- `distinct` (boolean): If `true`, returns only distinct company city values
- `limit` (integer, optional): Maximum number of results. **If not provided, returns all matching values (unlimited).** When provided, limits results to the specified number.
- `offset` (integer): Offset for pagination

**Response:**

```json
{
  "next": null,
  "previous": null,
  "results": [
    "San Francisco",
    "New York",
    "Austin"
  ]
}
```

**Status Codes:**

- `200 OK`: Success

---

### GET /api/v1/contacts/company_state/ - List Company States

Get list of contacts with only id and company state field (from CompanyMetadata).

**Headers:**

- `X-Request-Id` (optional): Request tracking ID

**Query Parameters:**

- `search` (string): Search term to filter results (case-insensitive)
- `distinct` (boolean): If `true`, returns only distinct company state values
- `limit` (integer, optional): Maximum number of results. **If not provided, returns all matching values (unlimited).** When provided, limits results to the specified number.
- `offset` (integer): Offset for pagination

**Response:**

```json
{
  "next": null,
  "previous": null,
  "results": [
    "CA",
    "NY",
    "TX"
  ]
}
```

**Status Codes:**

- `200 OK`: Success

---

### GET /api/v1/contacts/company_country/ - List Company Countries

Get list of contacts with only id and company country field (from CompanyMetadata).

**Headers:**

- `X-Request-Id` (optional): Request tracking ID

**Query Parameters:**

- `search` (string): Search term to filter results (case-insensitive)
- `distinct` (boolean): If `true`, returns only distinct company country values
- `limit` (integer, optional): Maximum number of results. **If not provided, returns all matching values (unlimited).** When provided, limits results to the specified number.
- `offset` (integer): Offset for pagination

**Response:**

```json
{
  "next": null,
  "previous": null,
  "results": [
    "United States",
    "United Kingdom",
    "Canada"
  ]
}
```

**Status Codes:**

- `200 OK`: Success

---

## Import Endpoints

These endpoints require admin authentication (IsAdminUser permission).

### GET /api/v1/contacts/import/ - Get Import Information

Get information about the import endpoint.

**Headers:**

- `Authorization: Bearer <admin_access_token>` (required)

**Query Parameters:**

- None

**Response:**

```json
{
  "message": "Upload a CSV file via POST to /api/v1/contacts/import/ to start a background import job."
}
```

**Status Codes:**

- `200 OK`: Success
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Admin access required

---

### POST /api/v1/contacts/import/ - Upload Contacts CSV

Upload a CSV file to import contacts. The file is processed asynchronously via Celery.

**Headers:**

- `Authorization: Bearer <admin_access_token>` (required)
- `Content-Type: multipart/form-data`

**Query Parameters:**

- None

**Request Body:**

Form data with field `file` containing the CSV file:

```txt
file: [CSV file]
```

**Response:**

**Success (202 Accepted):**

```json
{
  "job_id": "abc123def456",
  "status": "pending",
  "total_rows": 0,
  "success_count": 0,
  "error_count": 0,
  "upload_file_path": "/path/to/uploads/uuid_filename.csv",
  "error_file_path": null,
  "message": "Queued",
  "started_at": null,
  "finished_at": null,
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

**Error (400 Bad Request) - Missing File:**

```json
{
  "file": ["This field is required."]
}
```

**Error (400 Bad Request) - Invalid File:**

```json
{
  "file": ["The submitted file is empty."]
}
```

**Error (401 Unauthorized):**

```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Error (403 Forbidden):**

```json
{
  "detail": "You do not have permission to perform this action."
}
```

**Status Codes:**

- `202 Accepted`: Upload successful, job created and queued
- `400 Bad Request`: Invalid file or missing file field
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Admin access required
- `422 Unprocessable Entity`: File name is required
- `500 Internal Server Error`: Server error during upload or job creation

**Example Request:**

```bash
curl -X POST \
  http://54.87.173.234:8000/api/v1/contacts/import/ \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -F "file=@contacts.csv"
```

**Notes:**

- The CSV file is saved to the uploads directory with a timestamp
- Processing happens asynchronously via Celery
- Use the job_id to check import status
- The import job is created with status "pending" and message "Queued"

---

### GET /api/v1/contacts/import/{job_id}/ - Get Import Job Status

Get the status and details of an import job.

**Headers:**

- `Authorization: Bearer <admin_access_token>` (required)

**Query Parameters:**

- None

**Path Parameters:**

- `job_id` (string): Import job ID (UUID)

**Response:**

**Success (200 OK):**

```json
{
  "job_id": "abc123def456",
  "status": "completed",
  "total_rows": 10000,
  "success_count": 9850,
  "error_count": 150,
  "upload_file_path": "/path/to/uploads/uuid_filename.csv",
  "error_file_path": "/path/to/errors/job_abc123def456_errors.csv",
  "message": "Completed",
  "started_at": "2024-01-01T12:00:00Z",
  "finished_at": "2024-01-01T12:05:30Z",
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:05:30Z"
}
```

**With errors (when include_errors=true):**

```json
{
  "job_id": "abc123def456",
  "status": "completed",
  "total_rows": 10000,
  "success_count": 9850,
  "error_count": 150,
  "upload_file_path": "/path/to/uploads/uuid_filename.csv",
  "error_file_path": "/path/to/errors/job_abc123def456_errors.csv",
  "message": "Completed",
  "started_at": "2024-01-01T12:00:00Z",
  "finished_at": "2024-01-01T12:05:30Z",
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:05:30Z",
  "errors": [
    {
      "row_number": 5,
      "error_message": "Invalid email format",
      "row_data": {...}
    }
  ]
}
```

**Query Parameters:**

- `include_errors` (boolean): If `true`, includes error records in the response

**Status Values:**

- `pending`: Job is queued but not started
- `running`: Job is currently processing
- `completed`: Job finished successfully
- `failed`: Job failed with an error

**Error (401 Unauthorized):**

```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Error (403 Forbidden):**

```json
{
  "detail": "You do not have permission to perform this action."
}
```

**Error (404 Not Found):**

```json
{
  "detail": "Not found."
}
```

**Status Codes:**

- `200 OK`: Success
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Admin access required
- `404 Not Found`: Job not found

**Notes:**

- `error_file_path` will be null if there are no errors
- `started_at` and `finished_at` are null until the job starts/completes
- Use `include_errors=true` query parameter to get error details in the response

---

### GET /api/v1/contacts/import/{job_id}/errors/ - Get Import Errors

Download a CSV file containing all rows that failed during import.

**Headers:**

- `Authorization: Bearer <admin_access_token>` (required)

**Query Parameters:**

- None

**Path Parameters:**

- `job_id` (string): Import job ID (UUID)

**Response:**

**Success (200 OK):**

Returns a JSON array of error records:

```json
[
  {
    "row_number": 5,
    "error_message": "Invalid email format",
    "row_data": {
      "first_name": "John",
      "email": "invalid-email"
    }
  },
  {
    "row_number": 12,
    "error_message": "Missing required field: company_id",
    "row_data": {
      "first_name": "Jane"
    }
  }
]
```

**Error (401 Unauthorized):**

```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Error (403 Forbidden):**

```json
{
  "detail": "You do not have permission to perform this action."
}
```

**Error (404 Not Found):**

```json
{
  "detail": "Not found."
}
```

**Status Codes:**

- `200 OK`: Success, errors returned
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Admin access required
- `404 Not Found`: Job not found or no errors available

**Example Request:**

```bash
curl -X GET \
  http://54.87.173.234:8000/api/v1/contacts/import/abc123def456/errors/ \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

**Notes:**

- Returns an empty array if there are no errors
- Each error record includes the row number, error message, and the original row data

---

## Error Responses

All endpoints may return the following common error responses:

### 400 Bad Request

```json
{
  "detail": "Error message describing what went wrong"
}
```

### 401 Unauthorized

```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden

```json
{
  "detail": "You do not have permission to perform this action."
}
```

### 404 Not Found

```json
{
  "detail": "Not found."
}
```

### 500 Internal Server Error

```json
{
  "detail": "An error occurred while processing the request. Please check your query parameters and try again."
}
```

---

## Scalability & Environment Configuration

- `CONTACTS_CACHE_ENABLED` (default `true`): Toggle caching for contact list, field, and analytics endpoints.
- `CONTACTS_LIST_CACHE_TTL`, `CONTACTS_FIELD_CACHE_TTL`, `CONTACTS_ANALYTICS_CACHE_TTL`: Control cache lifetimes (seconds) for each endpoint family.
- `DB_CONTACTS_REPLICA_URL` / `CONTACTS_REPLICA_URL`: Optional Postgres connection string for read replicas. Use `CONTACTS_REPLICA_ALIAS` (default `contacts_replica`) to name the database entry.
- `CONTACTS_DEFAULT_REPLICA_READ` (default `false`): When enabled, contact reads prefer the replica unless `Cache-Control: no-cache` or `?use_replica=false` is supplied.
- `CONTACTS_HIVE_TABLE`, `CONTACTS_HIVE_DATABASE`, `CONTACTS_THRIFT_HOST`, `CONTACTS_LIVY_URL`, `CONTACTS_HADOOP_BIN`, `CONTACTS_HADOOP_JOB_JAR`: Configure Spark/Hadoop integrations for the analytics endpoint.

These knobs allow the API to scale horizontally, offload heavy reads to replicas, and delegate aggregations to distributed compute clusters.

---

## Notes

- All timestamps are in ISO 8601 format (UTC): `YYYY-MM-DDTHH:MM:SSZ`
- All text searches are case-insensitive
- Pagination limits are enforced (max 100 items per page)
- The `X-Request-Id` header, if provided, will be echoed back in the response headers
- Field-specific endpoints only return `id` and the specified field to minimize response size
- The `keywords` field supports comma-separated values and can be expanded using `separated=true`
- Import jobs are processed asynchronously. Check job status using the job detail endpoint
- Cursor pagination (default) is optimized for large datasets and doesn't include count
- Limit-offset pagination (custom ordering) also doesn't include count for performance
- Contact count endpoint uses PostgreSQL estimates for unfiltered queries (fast) and actual count for filtered queries (accurate)
