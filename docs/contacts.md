# Contacts API Documentation

Complete API documentation for contact management endpoints, including listing, filtering, searching, field-specific queries, and import functionality.

## Base URL

```txt
http://107.21.188.21:8000
```

## Authentication

Most contact endpoints are publicly accessible (no authentication required). Import endpoints require admin authentication (IsAdminUser).

**Admin Authentication (for import endpoints):**

```txt
Authorization: Bearer <admin_access_token>
```

---

## Common Headers

- `X-Request-Id` (optional): Request tracking ID that will be echoed back in the response header

---

## Main Contact Endpoints

### GET /api/contacts/ - List Contacts

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

#### Numeric Range Filters

- `employees_min` (integer): Minimum number of employees
- `employees_max` (integer): Maximum number of employees
- `annual_revenue_min` (integer): Minimum annual revenue
- `annual_revenue_max` (integer): Maximum annual revenue
- `total_funding_min` (integer): Minimum total funding
- `total_funding_max` (integer): Maximum total funding
- `latest_funding_amount_min` (integer): Minimum latest funding amount
- `latest_funding_amount_max` (integer): Maximum latest funding amount

#### Date Range Filters (ISO datetime format)

- `created_at_after` (string): Filter contacts created after this date (ISO format: `2024-01-01T00:00:00Z`)
- `created_at_before` (string): Filter contacts created before this date
- `updated_at_after` (string): Filter contacts updated after this date
- `updated_at_before` (string): Filter contacts updated before this date

#### Search and Ordering

- `search` (string): Full-text search across multiple fields (first_name, last_name, title, company, email, city, state, country, etc.)
- `ordering` (string): Comma-separated fields to order by. Valid fields: `created_at`, `updated_at`, `employees`, `annual_revenue`, `total_funding`, `latest_funding_amount`, `first_name`, `last_name`, `title`, `company`, `email`, `city`, `state`, `country`, `company_address`, `company_city`, `company_state`, `company_country`, etc. Prepend `-` for descending.

#### Pagination Parameters

- `limit` (integer): Number of results per page (max 100, default: 25) - Used with custom ordering
- `offset` (integer): Offset for pagination (used when custom ordering is applied)
- `page_size` (integer): Page size for cursor pagination (used when ordering by created_at, default: 25, max: 100)

#### Advanced Controls

- `include_meta` (boolean): When `true`, includes the `meta_data` JSON column in list responses. Defaults to `false` for lean payloads.
- `use_replica` (boolean): When `true` and a replica database is configured, routes reads to that replica. Defaults to the `CONTACTS_DEFAULT_REPLICA_READ` setting.

**Response:**

**With Cursor Pagination (default ordering by created_at):**

```json
{
  "next": "http://107.21.188.21:8000/api/contacts/?cursor=cj0xJnN1YiI6IjE2ODAwMDAwMDAwMDAwMDAwMDAwMCJ9",
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
  "next": "http://107.21.188.21:8000/api/contacts/?ordering=-employees&limit=25&offset=25",
  "previous": "http://107.21.188.21:8000/api/contacts/?ordering=-employees&limit=25&offset=0",
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
GET /api/contacts/?first_name=John&country=United States&employees_min=50&ordering=-employees
GET /api/contacts/?search=technology&page_size=10
GET /api/contacts/?title=cto&company_name_for_emails=inc&industry=software&ordering=-employees,company&limit=25&offset=0
GET /api/contacts/?created_at_after=2024-01-01T00:00:00Z&ordering=-created_at
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

### GET /api/contacts/{id}/ - Retrieve Contact

Get detailed information about a specific contact by ID.

**Headers:**

- `X-Request-Id` (optional): Request tracking ID

**Path Parameters:**

- `id` (integer): Contact ID

**Query Parameters:**

- None

**Response:**

**Success (200 OK):**

```json
{
  "id": 1,
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

### GET /api/contacts/count/ - Get Contact Count

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
GET /api/contacts/count/
GET /api/contacts/count/?country=United States&city=San Francisco&employees_min=50
GET /api/contacts/count/?email_status=valid&industry=Technology
```

**Notes:**

- Unfiltered queries use PostgreSQL's estimated row count (very fast, cached for 5 minutes)
- Filtered queries use actual COUNT(*) which can be slow on large datasets
- For complex filters, the count operation may timeout - try simpler filters

---

### GET /api/contacts/analytics/ - Contact Analytics Snapshot

Returns high-level aggregates for dashboards or health checks. When Spark (Thrift/Livy) or Hadoop is configured the service streams results from those backends; otherwise it falls back to PostgreSQL/ORM aggregation.

**Query Parameters:**

- `limit` (integer, default `10`, max `50`): Number of top countries/industries to include.

**Response:**

```json
{
  "total_contacts": 125000,
  "top_countries": [{"country": "US", "total": 82000}, {"country": "GB", "total": 9000}],
  "top_industries": [{"industry": "software", "total": 55000}],
  "hadoop_job_configured": false,
  "generated_at": "2025-03-01T12:00:00Z",
  "limit": 10,
  "source": "spark"
}
```

**Notes:**

- Responses are cached for `CONTACTS_ANALYTICS_CACHE_TTL` seconds. Cached responses include the `X-Cache-Hit` header.
- When big data services are unavailable, the endpoint automatically switches to the ORM fallback and reports `"source": "django"`.
- Add `Cache-Control: no-cache` to force regeneration of analytics snapshots.

---

## Field-Specific Endpoints

These endpoints return only the `id` and the specific field value for each contact. Useful for getting unique values or searching specific fields.

### Common Query Parameters (for all field endpoints)

- `search` (string): Search term to filter results (case-insensitive, searches within the field)
- `distinct` (boolean): If `true`, returns only distinct field values (default: `false`)
- `limit` (integer): Number of results per page (max 100, default: 25)
- `offset` (integer): Offset for pagination

### GET /api/contacts/title/ - List Titles

Get list of contacts with only id and title field.

**Headers:**

- `X-Request-Id` (optional): Request tracking ID

**Query Parameters:**

- `search` (string): Search term to filter results (case-insensitive, searches within title field)
- `distinct` (boolean): If `true`, returns only distinct title values (default: `false`)
- `limit` (integer): Number of results per page (max 100, default: 25)
- `offset` (integer): Offset for pagination

**Response:**

```json
{
  "next": "http://107.21.188.21:8000/api/contacts/title/?limit=25&offset=25",
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
GET /api/contacts/title/?search=technology
GET /api/contacts/title/?distinct=true&limit=50
```

---

### GET /api/contacts/company/ - List Companies

Get list of contacts with only id and company field.

**Headers:**

- `X-Request-Id` (optional): Request tracking ID

**Query Parameters:**

- `search` (string): Search term to filter results (case-insensitive)
- `distinct` (boolean): If `true`, returns only distinct company values
- `limit` (integer): Number of results per page (max 100, default: 25)
- `offset` (integer): Offset for pagination

**Response:**

```json
{
  "next": "http://107.21.188.21:8000/api/contacts/company/?limit=25&offset=25",
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
GET /api/contacts/company/?search=tech
GET /api/contacts/company/?distinct=true
```

---

### GET /api/contacts/industry/ - List Industries

Get list of contacts with only id and industry field.

**Headers:**

- `X-Request-Id` (optional): Request tracking ID

**Query Parameters:**

- `search` (string): Search term to filter results (case-insensitive)
- `distinct` (boolean): If `true`, returns only distinct industry values
- `limit` (integer): Number of results per page (max 100, default: 25)
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

### GET /api/contacts/keywords/ - List Keywords

Get list of contacts with only id and keywords field. Supports expansion of comma-separated keywords.

**Headers:**

- `X-Request-Id` (optional): Request tracking ID

**Query Parameters:**

- `search` (string): Search term to filter results (case-insensitive)
  - When `separated=false`: Searches the comma-separated string
  - When `separated=true`: Uses two-stage filtering (pre-filter at DB level, then post-filter individual keywords after expansion)
- `separated` (boolean): If `true`, expands comma-separated keywords into individual records (one record per keyword). Each contact ID may appear multiple times.
- `distinct` (boolean): If `true`, returns only distinct keyword values. When combined with `separated=true`, returns unique individual keywords across all contacts.
- `limit` (integer): Number of results per page (max 100, default: 25)
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

### GET /api/contacts/technologies/ - List Technologies

Get list of contacts with only id and technologies field.

**Headers:**

- `X-Request-Id` (optional): Request tracking ID

**Query Parameters:**

- `search` (string): Search term to filter results (case-insensitive)
- `distinct` (boolean): If `true`, returns only distinct technology values
- `limit` (integer): Number of results per page (max 100, default: 25)
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

### GET /api/contacts/company_address/ - List Company Addresses

Return address text for related companies, sourced from the `Company.text_search` column.

**Headers:**

- `X-Request-Id` (optional): Request tracking ID

**Query Parameters:**

- `search` (string): Search term to filter results (case-insensitive)
- `distinct` (boolean): If `true`, returns only distinct company address values
- `limit` (integer): Number of results per page (max 100, default: 25)
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

### GET /api/contacts/contact_address/ - List Contact Addresses

Return person-level address text sourced from the `Contact.text_search` column.

**Headers:**

- `X-Request-Id` (optional): Request tracking ID

**Query Parameters:**

- `search` (string): Search term to filter results (case-insensitive)
- `distinct` (boolean): If `true`, returns only distinct contact address values
- `limit` (integer): Number of results per page (max 100, default: 25)
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

## Import Endpoints

These endpoints require admin authentication (IsAdminUser permission).

### GET /api/contacts/import/ - Get Import Information

Get information about the import endpoint.

**Headers:**

- `Authorization: Bearer <admin_access_token>` (required)

**Query Parameters:**

- None

**Response:**

```json
{
  "detail": "Upload contacts CSV via POST multipart/form-data with field 'file'."
}
```

**Status Codes:**

- `200 OK`: Success
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Admin access required

---

### POST /api/contacts/import/ - Upload Contacts CSV

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

**Success (201 Created):**

```json
{
  "job_id": 123
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

- `201 Created`: Upload successful, job created
- `400 Bad Request`: Invalid file or missing file field
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Admin access required

**Example Request:**

```bash
curl -X POST \
  http://107.21.188.21:8000/api/contacts/import \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -F "file=@contacts.csv"
```

**Notes:**

- The CSV file is saved to the uploads directory with a timestamp
- Processing happens asynchronously via Celery
- Use the job_id to check import status
- The import job is created with status "pending" and message "Queued"

---

### GET /api/contacts/import/{job_id}/ - Get Import Job Status

Get the status and details of an import job.

**Headers:**

- `Authorization: Bearer <admin_access_token>` (required)

**Query Parameters:**

- None

**Path Parameters:**

- `job_id` (integer): Import job ID

**Response:**

**Success (200 OK):**

```json
{
  "id": 123,
  "status": "completed",
  "total_rows": 10000,
  "success_count": 9850,
  "error_count": 150,
  "upload_file_path": "/path/to/uploads/contacts_20240101T120000Z.csv",
  "error_file_path": "/path/to/errors/job_123_errors.csv",
  "message": "Completed",
  "started_at": "2024-01-01T12:00:00Z",
  "finished_at": "2024-01-01T12:05:30Z",
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:05:30Z",
  "errors_url": "http://107.21.188.21:8000/api/contacts/import/123/errors/"
}
```

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

- The `errors_url` field provides a direct link to download error rows
- `error_file_path` will be empty if there are no errors
- `started_at` and `finished_at` are null until the job starts/completes

---

### GET /api/contacts/import/{job_id}/errors/ - Download Import Errors

Download a CSV file containing all rows that failed during import.

**Headers:**

- `Authorization: Bearer <admin_access_token>` (required)

**Query Parameters:**

- None

**Path Parameters:**

- `job_id` (integer): Import job ID

**Response:**

- CSV file download with error rows

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

- `200 OK`: Success, file downloaded
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Admin access required
- `404 Not Found`: Job not found or no error file available

**Example Request:**

```bash
curl -X GET \
  http://107.21.188.21:8000/api/contacts/import/123/errors/ \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -o errors.csv
```

**Notes:**

- The file is downloaded as an attachment
- The filename is based on the error file path
- If there are no errors, the endpoint returns 404
- The error CSV contains the original row data plus error messages

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
