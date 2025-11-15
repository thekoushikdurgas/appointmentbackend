# Companies API Documentation

Complete API documentation for company management endpoints, including listing, filtering, searching, field-specific queries, and CRUD operations.

## Base URL

```txt
http://54.87.173.234:8000
```

**API Version:** All endpoints are under `/api/v1/companies/`

## Authentication

All company endpoints require user authentication. Write operations (create, update, delete) require admin authentication and the `X-Companies-Write-Key` header.

**User Authentication (for read endpoints):**

```txt
Authorization: Bearer <access_token>
```

**Admin Authentication (for write endpoints):**

```txt
Authorization: Bearer <admin_access_token>
X-Companies-Write-Key: <write_key>  (required for POST/PUT/DELETE /api/v1/companies/)
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

## Main Company Endpoints

### GET /api/v1/companies/ - List Companies

Retrieve a paginated list of companies with optional filtering, searching, and ordering.

**Headers:**

- `X-Request-Id` (optional): Request tracking ID

**Query Parameters:**

#### Text Filters (case-insensitive contains)

All text filters support partial matching:

- `name` (string): Filter by company name
- `address` (string): Filter by company address
- `company_location` (string): Filter by company location text (searches Company.text_search covering address, city, state, country)
- `city` (string): Filter by company city (from CompanyMetadata)
- `state` (string): Filter by company state (from CompanyMetadata)
- `country` (string): Filter by company country (from CompanyMetadata)
- `phone_number` (string): Filter by company phone number
- `website` (string): Filter by company website
- `linkedin_url` (string): Filter by company LinkedIn URL
- `facebook_url` (string): Filter by company Facebook URL
- `twitter_url` (string): Filter by company Twitter URL

#### Exact Match Filters

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

#### Array Filters (comma-separated for OR logic)

- `industries` (string): Filter by industries (comma-separated for OR logic)
- `keywords` (string): Filter by keywords (comma-separated for OR logic)
- `technologies` (string): Filter by technologies (comma-separated for OR logic)

#### Exclusion Filters (multi-value, case-insensitive)

These filters exclude companies matching any of the provided values:

- `exclude_industries` (array of strings): Exclude companies in specified industries
- `exclude_keywords` (array of strings): Exclude companies with specified keywords
- `exclude_technologies` (array of strings): Exclude companies using specified technologies

**Note:** Exclusion filters accept multiple values as comma-separated strings or repeated query parameters (e.g., `?exclude_industries=Retail&exclude_industries=Healthcare` or `?exclude_industries=Retail,Healthcare`)

#### Date Range Filters (ISO datetime format)

- `created_at_after` (string): Filter companies created after this date (ISO format: `2024-01-01T00:00:00Z`)
- `created_at_before` (string): Filter companies created before this date
- `updated_at_after` (string): Filter companies updated after this date
- `updated_at_before` (string): Filter companies updated before this date

#### Search and Ordering

- `search` (string): Full-text search across multiple fields (name, address, city, state, country, industries, keywords, technologies, etc.)
- `ordering` (string): Sort results by field. Valid fields: `created_at`, `updated_at`, `name`, `employees_count`, `annual_revenue`, `total_funding`. Prepend `-` for descending.

#### Pagination Parameters

- `limit` (integer, optional): Number of results per page. **If not provided, returns all matching companies (unlimited).** When provided, limits results to the specified number (capped at MAX_PAGE_SIZE).
- `offset` (integer): Offset for pagination
- `page` (integer): 1-indexed page number (converts to offset)
- `page_size` (integer): Page size override (max 100, default: 25)
- `cursor` (string): Opaque cursor token for cursor-based pagination

#### Advanced Controls

- `distinct` (boolean): Return distinct companies based on primary key (boolean)

**Response:**

**Success (200 OK):**

```json
{
  "next": "http://54.87.173.234:8000/api/v1/companies/?cursor=...",
  "previous": null,
  "results": [
    {
      "id": 1,
      "uuid": "398cce44-233d-5f7c-aea1-e4a6a79df10c",
      "name": "Acme Corporation",
      "employees_count": 250,
      "annual_revenue": 50000000,
      "total_funding": 25000000,
      "industries": ["Technology", "Software"],
      "keywords": ["enterprise", "saas", "cloud"],
      "technologies": ["Python", "AWS", "PostgreSQL"],
      "address": "123 Main St, San Francisco, CA 94105",
      "metadata": {
        "city": "San Francisco",
        "state": "CA",
        "country": "United States",
        "phone_number": "+1-415-555-0100",
        "website": "https://acme.com",
        "linkedin_url": "https://linkedin.com/company/acme",
        "facebook_url": "https://facebook.com/acme",
        "twitter_url": "https://twitter.com/acme"
      },
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

**Error Response (400 Bad Request):**

```json
{
  "detail": "Invalid ordering field(s): invalid_field. Valid fields are: created_at, updated_at, name, employees_count, annual_revenue, total_funding"
}
```

**Status Codes:**

- `200 OK`: Success
- `400 Bad Request`: Invalid query parameters
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Server error

**Example Requests:**

```txt
GET /api/v1/companies/?name=Acme&employees_min=100&ordering=-employees_count
GET /api/v1/companies/?search=technology&industries=Software&limit=50
GET /api/v1/companies/?city=San Francisco&state=CA&annual_revenue_min=10000000
GET /api/v1/companies/?keywords=saas&technologies=AWS&ordering=-total_funding
```

**Notes:**

- Default ordering is by `-created_at` (newest first)
- All text searches are case-insensitive
- Multiple filters can be combined with `&`
- Array filters (industries, keywords, technologies) use comma-separated values for OR logic

---

### GET /api/v1/companies/{uuid}/ - Retrieve Company

Get detailed information about a specific company by UUID.

**Headers:**

- `X-Request-Id` (optional): Request tracking ID

**Path Parameters:**

- `uuid` (string): Company UUID

**Response:**

**Success (200 OK):**

```json
{
  "id": 1,
  "uuid": "398cce44-233d-5f7c-aea1-e4a6a79df10c",
  "name": "Acme Corporation",
  "employees_count": 250,
  "annual_revenue": 50000000,
  "total_funding": 25000000,
  "industries": ["Technology", "Software"],
  "keywords": ["enterprise", "saas", "cloud"],
  "technologies": ["Python", "AWS", "PostgreSQL"],
  "address": "123 Main St, San Francisco, CA 94105",
  "text_search": "San Francisco CA United States",
  "metadata": {
    "city": "San Francisco",
    "state": "CA",
    "country": "United States",
    "phone_number": "+1-415-555-0100",
    "website": "https://acme.com",
    "linkedin_url": "https://linkedin.com/company/acme",
    "facebook_url": "https://facebook.com/acme",
    "twitter_url": "https://twitter.com/acme"
  },
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
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
- `404 Not Found`: Company not found

**Example Requests:**

```bash
# Retrieve by UUID
curl -X GET "http://54.87.173.234:8000/api/v1/companies/398cce44-233d-5f7c-aea1-e4a6a79df10c/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### GET /api/v1/companies/count/ - Get Company Count

Get the total count of companies, optionally filtered.

**Headers:**

- `X-Request-Id` (optional): Request tracking ID

**Query Parameters:**

All filter parameters from `/api/v1/companies/` are supported.

**Response:**

**Success (200 OK):**

```json
{
  "count": 15000
}
```

**Status Codes:**

- `200 OK`: Success
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Error counting companies

**Example Requests:**

```txt
GET /api/v1/companies/count/
GET /api/v1/companies/count/?industries=Technology&employees_min=100
GET /api/v1/companies/count/?city=San Francisco&annual_revenue_min=10000000
```

---

### GET /api/v1/companies/count/uuids/ - Get Company UUIDs

Get a list of company UUIDs that match the provided filters. Returns count and list of UUIDs. Useful for bulk operations or exporting specific company sets.

**Headers:**

- `X-Request-Id` (optional): Request tracking ID

**Query Parameters:**

**This endpoint accepts ALL the same query parameters as `/api/v1/companies/count/` endpoint, plus an additional parameter:**

- `limit` (integer, optional): Maximum number of UUIDs to return. **If not provided, returns all matching UUIDs (unlimited).** When provided, limits results to the specified number.

All filter parameters from `/api/v1/companies/` are supported:

- All text filters (name, search, etc.)
- All numeric range filters (employees_min, employees_max, annual_revenue_min, annual_revenue_max, total_funding_min, total_funding_max, etc.)
- All array filters (industries, keywords, technologies, etc.)
- All exclude filters (exclude_industries, exclude_keywords, exclude_technologies, exclude_locations, etc.)
- All location filters (city, state, country, address, company_location, etc.)
- All contact information filters (phone_number, website, linkedin_url, facebook_url, twitter_url, etc.)
- All date range filters (created_at_after, created_at_before, updated_at_after, updated_at_before, etc.)
- Distinct parameter

**Response:**

**Success (200 OK):**

```json
{
  "count": 567,
  "uuids": [
    "398cce44-233d-5f7c-aea1-e4a6a79df10c",
    "498cce44-233d-5f7c-aea1-e4a6a79df10d",
    "598cce44-233d-5f7c-aea1-e4a6a79df10e"
  ]
}
```

**Status Codes:**

- `200 OK`: Success
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Error retrieving UUIDs

**Example Requests:**

```txt
GET /api/v1/companies/count/uuids/
GET /api/v1/companies/count/uuids/?industries=Technology&employees_min=100
GET /api/v1/companies/count/uuids/?search=software&limit=500
```

**Notes:**

- Returns only UUIDs, not full company data (efficient for bulk operations)
- **Accepts all the same filter parameters as `/api/v1/companies/count/` endpoint**
- Useful for exporting specific company sets or bulk updates
- When `limit` is not provided, returns all matching UUIDs (unlimited)

---

### POST /api/v1/companies/ - Create Company

Create a new company. Requires admin authentication and the `X-Companies-Write-Key` header.

**Headers:**

- `Authorization: Bearer <admin_access_token>` (required)
- `X-Companies-Write-Key: <write_key>` (required)
- `X-Request-Id` (optional): Request tracking ID

**Request Body:**

All fields are optional:

```json
{
  "uuid": "optional-uuid-or-auto-generated",
  "name": "Acme Corporation",
  "employees_count": 250,
  "industries": ["Technology", "Software"],
  "keywords": ["enterprise", "saas", "cloud"],
  "address": "123 Main St",
  "annual_revenue": 50000000,
  "total_funding": 25000000,
  "technologies": ["Python", "AWS", "PostgreSQL"],
  "text_search": "San Francisco CA United States",
  "metadata": {
    "city": "San Francisco",
    "state": "CA",
    "country": "United States",
    "phone_number": "+1-415-555-0100",
    "website": "https://acme.com",
    "linkedin_url": "https://linkedin.com/company/acme",
    "facebook_url": "https://facebook.com/acme",
    "twitter_url": "https://twitter.com/acme"
  }
}
```

**Response:**

**Success (201 Created):**

Returns a `CompanyDetail` object (same structure as GET /api/v1/companies/{uuid}/).

**Error (403 Forbidden):**

```json
{
  "detail": "Forbidden"
}
```

**Status Codes:**

- `201 Created`: Company created successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Missing or invalid write key

---

### PUT /api/v1/companies/{company_uuid}/ - Update Company

Update an existing company. Requires admin authentication and the `X-Companies-Write-Key` header.

**Headers:**

- `Authorization: Bearer <admin_access_token>` (required)
- `X-Companies-Write-Key: <write_key>` (required)
- `X-Request-Id` (optional): Request tracking ID

**Path Parameters:**

- `company_uuid` (string): Company UUID

**Request Body:**

All fields are optional (partial update):

```json
{
  "name": "Acme Corporation Updated",
  "employees_count": 300,
  "annual_revenue": 60000000,
  "industries": ["Technology", "Software", "AI"],
  "metadata": {
    "city": "San Francisco",
    "state": "CA",
    "phone_number": "+1-415-555-0200"
  }
}
```

**Response:**

**Success (200 OK):**

Returns the updated `CompanyDetail` object.

**Error (404 Not Found):**

```json
{
  "detail": "Not found."
}
```

**Status Codes:**

- `200 OK`: Company updated successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Missing or invalid write key
- `404 Not Found`: Company not found

---

### DELETE /api/v1/companies/{company_uuid}/ - Delete Company

Delete a company. Requires admin authentication and the `X-Companies-Write-Key` header.

**Headers:**

- `Authorization: Bearer <admin_access_token>` (required)
- `X-Companies-Write-Key: <write_key>` (required)
- `X-Request-Id` (optional): Request tracking ID

**Path Parameters:**

- `company_uuid` (string): Company UUID

**Response:**

**Success (204 No Content):**

No response body.

**Error (404 Not Found):**

```json
{
  "detail": "Not found."
}
```

**Status Codes:**

- `204 No Content`: Company deleted successfully
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Missing or invalid write key
- `404 Not Found`: Company not found

---

## Attribute Lookup Endpoints

These endpoints return distinct values for specific company attributes. Useful for building filter dropdowns and autocomplete fields.

### Common Query Parameters (for all attribute endpoints)

- `search` (string): Search term to filter results (case-insensitive)
- `distinct` (boolean): If `true`, returns only distinct values (default: `true`)
- `separated` (boolean): If `true`, expands array columns into individual records (for industries, keywords, technologies)
- `limit` (integer, optional): Maximum number of results. **If not provided, returns all matching values (unlimited).** When provided, limits results to the specified number.
- `offset` (integer): Offset for pagination
- `ordering` (string): Sort order. Valid values: `value`, `-value`, `count`, `-count`

### GET /api/v1/companies/name/ - List Company Names

Get list of distinct company names.

**Response:**

```json
{
  "next": null,
  "previous": null,
  "results": [
    {
      "value": "Acme Corporation",
      "count": 1
    },
    {
      "value": "Tech Innovations Inc",
      "count": 1
    }
  ]
}
```

**Example Requests:**

```txt
GET /api/v1/companies/name/?search=acme
GET /api/v1/companies/name/?ordering=value&limit=50
```

---

### GET /api/v1/companies/industry/ - List Industries

Get list of distinct industries.

**Query Parameters:**

- `separated` (boolean): If `true`, expands array into individual industry values

**Response:**

**Without separated:**

```json
{
  "next": null,
  "previous": null,
  "results": [
    {
      "value": "Technology, Software",
      "count": 150
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
      "value": "Technology",
      "count": 200
    },
    {
      "value": "Software",
      "count": 180
    }
  ]
}
```

**Example Requests:**

```txt
GET /api/v1/companies/industry/?separated=true&ordering=-count
GET /api/v1/companies/industry/?search=tech&distinct=true
```

---

### GET /api/v1/companies/keywords/ - List Keywords

Get list of distinct company keywords.

**Query Parameters:**

- `separated` (boolean): If `true`, expands array into individual keyword values

**Response:**

```json
{
  "next": null,
  "previous": null,
  "results": [
    {
      "value": "enterprise",
      "count": 500
    },
    {
      "value": "saas",
      "count": 450
    }
  ]
}
```

**Example Requests:**

```txt
GET /api/v1/companies/keywords/?separated=true&search=cloud
GET /api/v1/companies/keywords/?ordering=-count&limit=100
```

---

### GET /api/v1/companies/technologies/ - List Technologies

Get list of distinct technologies used by companies.

**Query Parameters:**

- `separated` (boolean): If `true`, expands array into individual technology values

**Response:**

```json
{
  "next": null,
  "previous": null,
  "results": [
    {
      "value": "Python",
      "count": 300
    },
    {
      "value": "AWS",
      "count": 250
    }
  ]
}
```

**Example Requests:**

```txt
GET /api/v1/companies/technologies/?separated=true&search=python
GET /api/v1/companies/technologies/?ordering=-count
```

---

### GET /api/v1/companies/city/ - List Company Cities

Get list of distinct company cities.

**Response:**

```json
{
  "next": null,
  "previous": null,
  "results": [
    {
      "value": "San Francisco",
      "count": 500
    },
    {
      "value": "New York",
      "count": 450
    }
  ]
}
```

**Example Requests:**

```txt
GET /api/v1/companies/city/?search=san
GET /api/v1/companies/city/?ordering=-count&limit=50
```

---

### GET /api/v1/companies/state/ - List Company States

Get list of distinct company states.

**Response:**

```json
{
  "next": null,
  "previous": null,
  "results": [
    {
      "value": "California",
      "count": 800
    },
    {
      "value": "New York",
      "count": 600
    }
  ]
}
```

---

### GET /api/v1/companies/country/ - List Company Countries

Get list of distinct company countries.

**Response:**

```json
{
  "next": null,
  "previous": null,
  "results": [
    {
      "value": "United States",
      "count": 5000
    },
    {
      "value": "United Kingdom",
      "count": 800
    }
  ]
}
```

---

### GET /api/v1/companies/address/ - List Company Addresses

Get list of distinct company addresses (from Company.text_search).

**Response:**

```json
{
  "next": null,
  "previous": null,
  "results": [
    {
      "value": "San Francisco CA United States",
      "count": 150
    }
  ]
}
```

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
  "detail": "Forbidden"
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
  "detail": "An error occurred while processing the request."
}
```

---

## Notes

- All timestamps are in ISO 8601 format (UTC): `YYYY-MM-DDTHH:MM:SSZ`
- All text searches are case-insensitive
- Pagination limits are enforced (max 100 items per page)
- The `X-Request-Id` header, if provided, will be echoed back in the response headers
- Array fields (industries, keywords, technologies) support comma-separated values for OR logic
- Exclusion filters accept multiple values as comma-separated strings or repeated parameters
- Write operations require both admin authentication and the `X-Companies-Write-Key` header
- The `separated` parameter in attribute endpoints expands array values into individual records

---

## Company Contacts Endpoints

List and filter contacts belonging to a specific company.

### List Contacts for Company

**Endpoint:** `GET /api/v1/companies/company/{company_uuid}/contacts/`

**Description:** Return a paginated list of contacts for a specific company with optional filtering.

**Authentication:** Required (Bearer token)

**Path Parameters:**

- `company_uuid` (string, required): Company UUID identifier

**Query Parameters:**

*Contact Identity Filters:*

- `first_name` (string): Case-insensitive substring match against Contact.first_name
- `last_name` (string): Case-insensitive substring match against Contact.last_name
- `title` (string): Case-insensitive substring match against Contact.title
- `seniority` (string): Case-insensitive substring match against Contact.seniority
- `department` (string): Substring match against Contact.departments array
- `email_status` (string): Case-insensitive substring match against Contact.email_status
- `email` (string): Case-insensitive substring match against Contact.email
- `contact_location` (string): Contact text-search column covering person-level location metadata

*Contact Metadata Filters:*

- `work_direct_phone` (string): Substring match against ContactMetadata.work_direct_phone
- `home_phone` (string): Substring match against ContactMetadata.home_phone
- `mobile_phone` (string): Substring match against Contact.mobile_phone
- `other_phone` (string): Substring match against ContactMetadata.other_phone
- `city` (string): Substring match against ContactMetadata.city
- `state` (string): Substring match against ContactMetadata.state
- `country` (string): Substring match against ContactMetadata.country
- `person_linkedin_url` (string): Substring match against ContactMetadata.linkedin_url
- `website` (string): Substring match against ContactMetadata.website
- `facebook_url` (string): Substring match against ContactMetadata.facebook_url
- `twitter_url` (string): Substring match against ContactMetadata.twitter_url
- `stage` (string): Substring match against ContactMetadata.stage

*Exclusion Filters:*

- `exclude_titles` (array[string]): Exclude contacts whose title matches any provided value
- `exclude_contact_locations` (array[string]): Exclude contacts whose contact location matches
- `exclude_seniorities` (array[string]): Exclude contacts whose seniority matches
- `exclude_departments` (array[string]): Exclude contacts whose departments include any value

*Temporal Filters:*

- `created_at_after` (datetime): Filter contacts created after timestamp (inclusive)
- `created_at_before` (datetime): Filter contacts created before timestamp (inclusive)
- `updated_at_after` (datetime): Filter contacts updated after timestamp (inclusive)
- `updated_at_before` (datetime): Filter contacts updated before timestamp (inclusive)

*Search and Ordering:*

- `search` (string): General-purpose search term applied across contact text columns
- `ordering` (string): Sort field (e.g., `first_name`, `-created_at`, `title`)

*Pagination:*

- `limit` (integer, optional): Number of items per page. **If not provided, returns all matching contacts (unlimited).** When provided, limits results to the specified number.
- `offset` (integer, >=0): Zero-based offset into result set
- `cursor` (string): Opaque cursor token for pagination
- `page` (integer, >=1): 1-indexed page number
- `page_size` (integer, >=1): Explicit page size override
- `distinct` (boolean, default: false): Return distinct contacts

**Response:** `200 OK`

```json
{
  "next": "http://54.87.173.234:8000/api/v1/companies/company/abc-123-uuid/contacts/?title=engineer&seniority=senior&limit=25&offset=25",
  "previous": null,
  "results": [
    {
      "id": 123,
      "uuid": "contact-uuid-here",
      "first_name": "John",
      "last_name": "Doe",
      "email": "john.doe@example.com",
      "title": "Software Engineer",
      "seniority": "mid",
      "departments": ["Engineering", "R&D"],
      "email_status": "verified",
      "mobile_phone": "+1234567890",
      "company": {
        "uuid": "company-uuid-here",
        "name": "Example Corp"
      },
      "metadata": {
        "city": "San Francisco",
        "state": "CA",
        "country": "United States",
        "linkedin_url": "https://linkedin.com/in/johndoe"
      },
      "created_at": "2024-01-15T10:30:00",
      "updated_at": "2024-01-20T14:45:00"
    }
  ]
}
```

**Pagination Notes:**

- `next`: Full URL to fetch the next page of results (null if no more results)
- `previous`: Full URL to fetch the previous page of results (null if on first page)
- `results`: Array of contact items

**Cursor-based Pagination:**
When using cursor-based pagination (by providing a `cursor` parameter), the URLs will use cursor tokens:

```json
{
  "next": "http://54.87.173.234:8000/api/v1/companies/company/abc-123-uuid/contacts/?cursor=eyJvZmZzZXQiOjI1fQ==",
  "previous": "http://54.87.173.234:8000/api/v1/companies/company/abc-123-uuid/contacts/?cursor=eyJvZmZzZXQiOjB9",
  "results": [...]
}
```

**Example Request:**

```bash
curl -X GET "http://54.87.173.234:8000/api/v1/companies/company/abc-123-uuid/contacts/?title=engineer&seniority=senior&limit=25" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### Count Contacts for Company

**Endpoint:** `GET /api/v1/companies/company/{company_uuid}/contacts/count/`

**Description:** Return the total count of contacts for a specific company matching filters.

**Authentication:** Required (Bearer token)

**Path Parameters:**

- `company_uuid` (string, required): Company UUID identifier

**Query Parameters:** Same as List Contacts endpoint (all filter parameters supported)

**Response:** `200 OK`

```json
{
  "count": 42
}
```

**Example Request:**

```bash
curl -X GET "http://54.87.173.234:8000/api/v1/companies/company/abc-123-uuid/contacts/count/?title=engineer" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### Get Contact UUIDs for Company

**Endpoint:** `GET /api/v1/companies/company/{company_uuid}/contacts/count/uuids/`

**Description:** Return a list of contact UUIDs for a specific company that match the provided filters. Returns count and list of UUIDs. Useful for bulk operations on company contacts.

**Authentication:** Required (Bearer token)

**Path Parameters:**

- `company_uuid` (string, required): Company UUID identifier

**Query Parameters:**

**This endpoint accepts ALL the same query parameters as `/api/v1/companies/company/{company_uuid}/contacts/count/` endpoint, plus an additional parameter:**

- `limit` (integer, optional): Maximum number of UUIDs to return. **If not provided, returns all matching UUIDs (unlimited).** When provided, limits results to the specified number.

All filter parameters from the list contacts endpoint are supported (title, first_name, last_name, email, seniority, department, search, etc.).

**Response:** `200 OK`

```json
{
  "count": 45,
  "uuids": [
    "contact-uuid-1",
    "contact-uuid-2",
    "contact-uuid-3"
  ]
}
```

**Example Request:**

```bash
curl -X GET "http://54.87.173.234:8000/api/v1/companies/company/abc-123-uuid/contacts/count/uuids/?title=engineer" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Notes:**

- Returns only UUIDs, not full contact data (efficient for bulk operations)
- Supports all the same filters as the list contacts endpoint
- Useful for exporting specific contact sets or bulk updates
- When `limit` is not provided, returns all matching UUIDs (unlimited)

---

### Company Contact Attribute Endpoints

Retrieve distinct values for specific contact attributes within a company.

#### List First Names

**Endpoint:** `GET /api/v1/companies/company/{company_uuid}/contacts/first_name/`

**Description:** Return distinct first name values for contacts in a specific company.

**Authentication:** Required (Bearer token)

**Path Parameters:**

- `company_uuid` (string, required): Company UUID identifier

**Query Parameters:**

- All CompanyContactFilterParams for filtering base contacts
- `distinct` (boolean, default: true): Return unique values
- `limit` (integer, default: 25): Maximum number of results
- `offset` (integer, default: 0): Offset for pagination
- `ordering` (string): Sort order (`value`, `-value`, `count`, `-count`)
- `search` (string): Case-insensitive search term

**Response:** `200 OK`

```json
["John", "Jane", "Michael", "Sarah"]
```

---

#### List Last Names

**Endpoint:** `GET /api/v1/companies/company/{company_uuid}/contacts/last_name/`

**Description:** Return distinct last name values for contacts in a specific company.

**Parameters:** Same as List First Names

**Response:** Array of strings

---

#### List Titles

**Endpoint:** `GET /api/v1/companies/company/{company_uuid}/contacts/title/`

**Description:** Return distinct title values for contacts in a specific company.

**Parameters:** Same as List First Names

**Response:** Array of strings

**Example:**

```json
["Software Engineer", "Senior Manager", "Director of Engineering", "VP of Sales"]
```

---

#### List Seniorities

**Endpoint:** `GET /api/v1/companies/company/{company_uuid}/contacts/seniority/`

**Description:** Return distinct seniority values for contacts in a specific company.

**Parameters:** Same as List First Names

**Response:** Array of strings

**Example:**

```json
["junior", "mid", "senior", "executive"]
```

---

#### List Departments

**Endpoint:** `GET /api/v1/companies/company/{company_uuid}/contacts/department/`

**Description:** Return distinct department values for contacts in a specific company. Departments are stored as arrays and are automatically expanded into individual values.

**Parameters:** Same as List First Names

**Response:** Array of strings

**Example:**

```json
["Engineering", "Sales", "Marketing", "R&D", "Operations"]
```

---

#### List Email Statuses

**Endpoint:** `GET /api/v1/companies/company/{company_uuid}/contacts/email_status/`

**Description:** Return distinct email status values for contacts in a specific company.

**Parameters:** Same as List First Names

**Response:** Array of strings

**Example:**

```json
["verified", "unverified", "bounced", "catch_all"]
```

---

### Error Responses

**404 Not Found** - Company not found

```json
{
  "detail": "Company not found"
}
```

**400 Bad Request** - Invalid query parameters

```json
{
  "detail": "Invalid query parameters"
}
```

**401 Unauthorized** - Missing or invalid authentication

```json
{
  "detail": "Not authenticated"
}
```

---

### Notes

- All company contact endpoints require user authentication
- The `company_uuid` must be a valid UUID for an existing company
- All filter parameters from the main contacts endpoint are supported except company-level filters
- Pagination works the same way as the main contacts endpoint
- Attribute endpoints support the same filtering as the list endpoint
- Department values are automatically expanded from array fields

