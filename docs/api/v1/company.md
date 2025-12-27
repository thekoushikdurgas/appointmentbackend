# Companies API Documentation

Complete API documentation for company management endpoints using VQL (Vivek Query Language) for flexible querying and filtering, plus company contact endpoints.

**Related Documentation:**

- [Contacts API](./contacts.md) - For contact management and VQL query language details
- [User API](./user.md) - For authentication endpoints
- [Export API](./export.md) - For exporting company data

## Table of Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [Company Endpoints](#company-endpoints)
  - [POST /api/v3/companies/query](#post-apiv3companiesquery---query-companies)
  - [POST /api/v3/companies/count](#post-apiv3companiescount---count-companies)
  - [GET /api/v3/companies/filters](#get-apiv3companiesfilters---get-company-filters)
  - [POST /api/v3/companies/filters/data](#post-apiv3companiesfiltersdata---get-company-filter-data)
  - [GET /api/v3/companies/{company_uuid}/](#get-apiv3companiescompany_uuid---retrieve-company)
- [Company Contacts Endpoints](#company-contacts-endpoints)
  - [GET /api/v3/companies/company/{company_uuid}/contacts/](#get-apiv3companiescompanycompany_uuidcontacts---list-company-contacts)
  - [GET /api/v3/companies/company/{company_uuid}/contacts/count/](#get-apiv3companiescompanycompany_uuidcontactscount---count-company-contacts)
  - [GET /api/v3/companies/company/{company_uuid}/contacts/filters](#get-apiv3companiescompanycompany_uuidcontactsfilters---get-company-contact-filters)
  - [POST /api/v3/companies/company/{company_uuid}/contacts/filters/data](#post-apiv3companiescompanycompany_uuidcontactsfiltersdata---get-company-contact-filter-data)
- [VQL Query Language](#vql-query-language)
- [Response Schemas](#response-schemas)
- [Error Handling](#error-handling)
- [Notes](#notes)

---

## Base URL

```txt
http://34.229.94.175:8000
```

**API Version:** All endpoints are under `/api/v3/companies/`

## Authentication

All company endpoints require JWT authentication via the `Authorization` header:

```txt
Authorization: Bearer <access_token>
```

Tokens are obtained through the login or register endpoints.

## Role-Based Access Control

All company endpoints are accessible to all authenticated users:

- **Free Users (`FreeUser`)**: ✅ Full access to all company endpoints
- **Pro Users (`ProUser`)**: ✅ Full access to all company endpoints
- **Admin (`Admin`)**: ✅ Full access to all company endpoints
- **Super Admin (`SuperAdmin`)**: ✅ Full access to all company endpoints

**Note:** Write operations (create, update, delete) are not available through the Companies API endpoints. Use the VQL query endpoint for read operations.

---

## Company Endpoints

### POST /api/v3/companies/query - Query Companies

Query companies using VQL (Vivek Query Language). This endpoint replaces the old GET /companies/ endpoint with a more flexible filter-based query system supporting complex conditions, field selection, and related entity population.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Request Body:**

```json
{
  "filters": {
    "and": [
      {
        "field": "name",
        "operator": "contains",
        "value": "Acme"
      },
      {
        "field": "employees_count",
        "operator": "gte",
        "value": 100
      }
    ]
  },
  "select_columns": ["uuid", "name", "employees_count", "annual_revenue"],
  "contact_config": {
    "populate": true,
    "select_columns": ["first_name", "last_name", "email"]
  },
  "limit": 25,
  "offset": 0,
  "sort_by": "created_at",
  "sort_direction": "desc"
}
```

**Request Body Fields:**

- `filters` (object, optional): Filter conditions using VQL filter structure
  - `and` (array): Array of conditions/filters - all must match
  - `or` (array): Array of conditions/filters - at least one must match
  - Each condition has:
    - `field` (string): Field name to filter on
    - `operator` (string): Comparison operator (eq, contains, gt, lt, etc.)
    - `value` (any): Value to compare against
- `select_columns` (array[string], optional): Columns to select from main entity. If not provided, returns all columns.
- `company_config` (object, optional): Configuration for populating related company data
  - `populate` (boolean): Whether to populate company data
  - `select_columns` (array[string]): Columns to select from company
- `contact_config` (object, optional): Configuration for populating related contact data
  - `populate` (boolean): Whether to populate contact data
  - `select_columns` (array[string]): Columns to select from contact
- `limit` (integer, optional, min: 1): Maximum number of results to return
- `offset` (integer, optional, min: 0, default: 0): Number of results to skip
- `sort_by` (string, optional): Field to sort by
- `sort_direction` (string, optional, default: "asc"): Sort direction - "asc" or "desc"

**Response:**

**Success (200 OK):**

```json
{
  "next": "http://34.229.94.175:8000/api/v3/companies/query?offset=25",
  "previous": null,
  "results": [
    {
      "uuid": "398cce44-233d-5f7c-aea1-e4a6a79df10c",
      "name": "Acme Corporation",
      "employees_count": 250,
      "annual_revenue": 50000000,
      "total_funding": 25000000,
      "industry": "Technology",
      "city": "San Francisco",
      "state": "CA",
      "country": "United States",
      "website": "https://acme.com",
      "linkedin_url": "https://linkedin.com/company/acme",
      "phone_number": "+1-415-555-0100",
      "technologies": ["Python", "AWS", "PostgreSQL"],
      "keywords": ["enterprise", "saas", "cloud"],
      "metadata": {
        "uuid": "398cce44-233d-5f7c-aea1-e4a6a79df10c",
        "linkedin_url": "https://linkedin.com/company/acme",
        "linkedin_sales_url": null,
        "facebook_url": null,
        "twitter_url": null,
        "website": "https://acme.com",
        "company_name_for_emails": null,
        "phone_number": "+1-415-555-0100",
        "latest_funding": null,
        "latest_funding_amount": null,
        "last_raised_at": null,
        "city": "San Francisco",
        "state": "CA",
        "country": "United States"
      }
    }
  ],
  "meta": {
    "strategy": "limit-offset",
    "count_mode": "exact",
    "count": 50,
    "filters_applied": true,
    "ordering": "-created_at",
    "returned_records": 25,
    "page_size": 25,
    "page_size_cap": 100,
    "using_replica": false
  }
}
```

**Response Fields:**

- `next` (string, optional): URL to fetch the next page of results (null if no more results)
- `previous` (string, optional): URL to fetch the previous page of results (null if on first page)
- `results` (array): Array of company objects matching the query
- `meta` (object): Metadata about the query execution
  - `strategy` (string): Pagination strategy used
  - `count_mode` (string): How count was calculated
  - `count` (integer): Total number of matching records
  - `filters_applied` (boolean): Whether filters were applied
  - `ordering` (string): Sort order used
  - `returned_records` (integer): Number of records returned in this page
  - `page_size` (integer): Page size used
  - `page_size_cap` (integer): Maximum page size allowed
  - `using_replica` (boolean): Whether read replica was used

**Error (400 Bad Request) - Invalid VQL Query:**

```json
{
  "detail": "Invalid VQL query: filters.and[0].field: field is required"
}
```

**Error (401 Unauthorized):**

```json
{
  "detail": "Not authenticated"
}
```

**Status Codes:**

- `200 OK`: Query executed successfully
- `400 Bad Request`: Invalid VQL query structure
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Server error during query execution

**Example Requests:**

```bash
# Simple query with filters
POST /api/v3/companies/query
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "filters": {
    "and": [
      {
        "field": "name",
        "operator": "contains",
        "value": "Acme"
      }
    ]
  },
  "limit": 10
}

# Query with contact population
POST /api/v3/companies/query
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "filters": {
    "and": [
      {
        "field": "employees_count",
        "operator": "gte",
        "value": 100
      }
    ]
  },
  "contact_config": {
    "populate": true,
    "select_columns": ["first_name", "last_name", "email"]
  },
  "limit": 25,
  "sort_by": "created_at",
  "sort_direction": "desc"
}
```

**Notes:**

- This endpoint replaces the old GET /api/v3/companies/ endpoint
- Uses VQL (Vivek Query Language) for flexible querying
- Supports complex filter conditions with AND/OR logic
- Supports field selection to reduce response size
- Supports populating related entities (company, contact metadata)
- Uses limit-offset pagination

---

### POST /api/v3/companies/count - Count Companies

Count companies matching a VQL query. This endpoint replaces the old GET /companies/count/ endpoint.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Request Body:**

```json
{
  "filters": {
    "and": [
      {
        "field": "employees_count",
        "operator": "gte",
        "value": 100
      }
    ]
  }
}
```

**Request Body Fields:**

- `filters` (object, optional): Filter conditions using VQL filter structure (same as query endpoint)

**Response:**

**Success (200 OK):**

```json
{
  "count": 1234
}
```

**Response Fields:**

- `count` (integer): Total number of companies matching the query

**Error (400 Bad Request) - Invalid VQL Query:**

```json
{
  "detail": "Invalid VQL query: filters.and[0].field: field is required"
}
```

**Error (401 Unauthorized):**

```json
{
  "detail": "Not authenticated"
}
```

**Status Codes:**

- `200 OK`: Count calculated successfully
- `400 Bad Request`: Invalid VQL query structure
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Server error during count operation

**Example Requests:**

```bash
# Count all companies
POST /api/v3/companies/count
Authorization: Bearer <access_token>
Content-Type: application/json

{}

# Count with filters
POST /api/v3/companies/count
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "filters": {
    "and": [
      {
        "field": "employees_count",
        "operator": "gte",
        "value": 100
      },
      {
        "field": "name",
        "operator": "contains",
        "value": "Tech"
      }
    ]
  }
}
```

**Notes:**

- This endpoint replaces the old GET /api/v3/companies/count/ endpoint
- Uses the same VQL filter structure as the query endpoint
- Returns exact count of matching companies

---

### GET /api/v3/companies/filters - Get Company Filters

Get available filters for companies. Returns a list of filter definitions with metadata about each filterable field.

**Headers:**

- `Authorization: Bearer <access_token>` (required)

**Response:**

**Success (200 OK):**

```json
{
  "data": [
    {
      "key": "name",
      "type": "text",
      "label": "Company Name",
      "direct_derived": false
    },
    {
      "key": "industries",
      "type": "keyword",
      "label": "Industries",
      "direct_derived": false
    },
    {
      "key": "employees_count",
      "type": "range",
      "label": "Employees Count",
      "direct_derived": true
    },
    {
      "key": "annual_revenue",
      "type": "range",
      "label": "Annual Revenue",
      "direct_derived": true
    }
  ]
}
```

**Response Fields:**

- `data` (array): Array of filter definition objects
  - `key` (string): Filter identifier used in queries (matches field names)
  - `type` (string): Filter type (text, keyword, range)
  - `label` (string): Human-readable name for UI display
  - `direct_derived` (boolean): Whether filter values are extracted directly from records (`true`) or stored in filters_data table (`false`)

**Error (401 Unauthorized):**

```json
{
  "detail": "Not authenticated"
}
```

**Status Codes:**

- `200 OK`: Filters retrieved successfully
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Server error during filter retrieval

**Example Request:**

```bash
GET /api/v3/companies/filters
Authorization: Bearer <access_token>
```

**Notes:**

- Returns all available filterable fields for companies
- Filter definitions include metadata for building filter UIs
- `direct_derived: true` filters extract values directly from records
- `direct_derived: false` filters use pre-computed values from filters_data table

---

### POST /api/v3/companies/filters/data - Get Company Filter Data

Get filter data values for a specific company filter with optional search and pagination.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Request Body:**

```json
{
  "service": "company",
  "filter_key": "industries",
  "search_text": "Soft",
  "page": 1,
  "limit": 25
}
```

**Request Body Fields:**

- `service` (string, required): Service name - must be `"contact"` or `"company"`
- `filter_key` (string, required): Filter key from the filters list (e.g., "industries", "technologies", "country")
- `search_text` (string, optional): Text to filter results (case-insensitive, partial match)
- `page` (integer, optional, default: 1, min: 1): Page number
- `limit` (integer, optional, default: 25, min: 1, max: 100): Results per page

**Response:**

**Success (200 OK):**

```json
{
  "data": [
    "Software",
    "Software Development",
    "Software as a Service (SaaS)"
  ]
}
```

**Response Fields:**

- `data` (array[string]): Array of filter values matching the search criteria

**Error (400 Bad Request) - Invalid Service:**

```json
{
  "detail": "Service must be 'contact' or 'company'"
}
```

**Error (401 Unauthorized):**

```json
{
  "detail": "Not authenticated"
}
```

**Error (422 Unprocessable Entity) - Validation Error:**

```json
{
  "detail": [
    {
      "loc": ["body", "filter_key"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**Status Codes:**

- `200 OK`: Filter data retrieved successfully
- `400 Bad Request`: Invalid service parameter
- `401 Unauthorized`: Authentication required
- `422 Unprocessable Entity`: Validation error in request body
- `500 Internal Server Error`: Server error during filter data retrieval

**Example Requests:**

```bash
# Get all industry values
POST /api/v3/companies/filters/data
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "service": "company",
  "filter_key": "industries",
  "page": 1,
  "limit": 25
}

# Search for industries containing "Soft"
POST /api/v3/companies/filters/data
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "service": "company",
  "filter_key": "industries",
  "search_text": "Soft",
  "page": 1,
  "limit": 25
}

# Get technology values
POST /api/v3/companies/filters/data
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "service": "company",
  "filter_key": "technologies",
  "page": 1,
  "limit": 100
}
```

**Notes:**

- Use this endpoint to populate filter dropdowns and autocomplete fields
- `search_text` enables autocomplete-style filtering of filter values
- Supports pagination for filters with many distinct values
- Filter values are returned as strings suitable for use in VQL queries
- `direct_derived: true` filters extract values directly from records
- `direct_derived: false` filters use pre-computed values for faster access

---

### GET /api/v3/companies/{company_uuid}/ - Retrieve Company

Get detailed information about a specific company by UUID.

**Headers:**

- `Authorization: Bearer <access_token>` (required)

**Path Parameters:**

- `company_uuid` (string, required): Company UUID

**Response:**

**Success (200 OK):**

```json
{
  "uuid": "398cce44-233d-5f7c-aea1-e4a6a79df10c",
  "name": "Acme Corporation",
  "employees_count": 250,
  "annual_revenue": 50000000,
  "total_funding": 25000000,
  "industry": "Technology",
    "city": "San Francisco",
    "state": "CA",
    "country": "United States",
    "website": "https://acme.com",
    "linkedin_url": "https://linkedin.com/company/acme",
  "phone_number": "+1-415-555-0100",
  "technologies": ["Python", "AWS", "PostgreSQL"],
  "keywords": ["enterprise", "saas", "cloud"],
  "metadata": {
    "uuid": "398cce44-233d-5f7c-aea1-e4a6a79df10c",
    "linkedin_url": "https://linkedin.com/company/acme",
    "linkedin_sales_url": null,
    "facebook_url": null,
    "twitter_url": null,
    "website": "https://acme.com",
    "company_name_for_emails": null,
    "phone_number": "+1-415-555-0100",
    "latest_funding": null,
    "latest_funding_amount": null,
    "last_raised_at": null,
    "city": "San Francisco",
    "state": "CA",
    "country": "United States"
  },
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

**Response Fields:**

- `uuid` (string): Company UUID
- `name` (string, optional): Company name
- `employees_count` (integer, optional): Number of employees
- `annual_revenue` (integer, optional): Annual revenue in dollars
- `total_funding` (integer, optional): Total funding in dollars
- `industries` (array[string], optional): List of industries
- `keywords` (array[string], optional): List of keywords
- `technologies` (array[string], optional): List of technologies
- `address` (string, optional): Company address
- `text_search` (string, optional): Free-form search text
- `created_at` (datetime, optional): Company creation timestamp
- `updated_at` (datetime, optional): Company last update timestamp

**Error (404 Not Found):**

```json
{
  "detail": "Not found."
}
```

**Error (401 Unauthorized):**

```json
{
  "detail": "Not authenticated"
}
```

**Status Codes:**

- `200 OK`: Company retrieved successfully
- `401 Unauthorized`: Authentication required
- `404 Not Found`: Company not found

**Example Request:**

```bash
GET /api/v3/companies/398cce44-233d-5f7c-aea1-e4a6a79df10c/
Authorization: Bearer <access_token>
```

**Notes:**

- Returns full company details including all fields
- Company must exist in the database

---

## Company Contacts Endpoints

List and filter contacts belonging to a specific company.

### GET /api/v3/companies/company/{company_uuid}/contacts/ - List Company Contacts

Return a paginated list of contacts for a specific company with optional filtering.

**Headers:**

- `Authorization: Bearer <access_token>` (required)

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
- `status` (string): Case-insensitive exact match against Contact.status
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
- `offset` (integer, >=0, default: 0): Zero-based offset into result set
- `cursor` (string, optional): Opaque cursor token for pagination
- `page` (integer, >=1): 1-indexed page number
- `page_size` (integer, >=1): Explicit page size override
- `distinct` (boolean, default: false): Return distinct contacts

**Response:**

**Success (200 OK):**

```json
{
  "next": "http://34.229.94.175:8000/api/v3/companies/company/abc-123-uuid/contacts/?title=engineer&seniority=senior&limit=25&offset=25",
  "previous": null,
  "results": [
    {
      "uuid": "contact-uuid-here",
      "first_name": "John",
      "last_name": "Doe",
      "company_id": "company-uuid-here",
      "email": "john.doe@example.com",
      "title": "Software Engineer",
      "seniority": "mid",
      "departments": ["Engineering", "R&D"],
      "email_status": "verified",
      "mobile_phone": "+1234567890",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-20T14:45:00Z"
    }
  ],
  "meta": {
    "strategy": "cursor",
    "count_mode": "estimated",
    "count": 42,
    "filters_applied": true,
    "ordering": "-created_at",
    "returned_records": 25,
    "page_size": 25,
    "page_size_cap": 100,
    "using_replica": false
  }
}
```

**Response Fields:**

- `next` (string, optional): URL to fetch the next page of results (null if no more results)
- `previous` (string, optional): URL to fetch the previous page of results (null if on first page)
- `results` (array): Array of contact items
- `meta` (object): Metadata about the query execution (same structure as company query endpoint)

**Cursor-based Pagination:**

When using cursor-based pagination (by providing a `cursor` parameter), the URLs will use cursor tokens:

```json
{
  "next": "http://34.229.94.175:8000/api/v3/companies/company/abc-123-uuid/contacts/?cursor=eyJvZmZzZXQiOjI1fQ==",
  "previous": "http://34.229.94.175:8000/api/v3/companies/company/abc-123-uuid/contacts/?cursor=eyJvZmZzZXQiOjB9",
  "results": [...]
}
```

**Error (404 Not Found) - Company not found:**

```json
{
  "detail": "Company not found"
}
```

**Error (400 Bad Request) - Invalid cursor:**

```json
{
  "detail": "Invalid cursor value"
}
```

**Error (401 Unauthorized):**

```json
{
  "detail": "Not authenticated"
}
```

**Status Codes:**

- `200 OK`: Success
- `400 Bad Request`: Invalid query parameters or cursor
- `401 Unauthorized`: Authentication required
- `404 Not Found`: Company not found
- `500 Internal Server Error`: Server error

**Example Requests:**

```bash
# List contacts for a company
GET /api/v3/companies/company/abc-123-uuid/contacts/?title=engineer&seniority=senior&limit=25
Authorization: Bearer <access_token>

# List with cursor pagination
GET /api/v3/companies/company/abc-123-uuid/contacts/?cursor=eyJvZmZzZXQiOjI1fQ==
Authorization: Bearer <access_token>
```

**Notes:**

- Returns contacts that belong to the specified company
- Supports all the same filter parameters as the main contacts endpoint (except company-level filters)
- Supports both limit-offset and cursor-based pagination
- When `limit` is not provided, returns all matching contacts (unlimited)

---

### GET /api/v3/companies/company/{company_uuid}/contacts/count/ - Count Company Contacts

Return the total count of contacts for a specific company matching filters.

**Headers:**

- `Authorization: Bearer <access_token>` (required)

**Path Parameters:**

- `company_uuid` (string, required): Company UUID identifier

**Query Parameters:**

Same as List Company Contacts endpoint (all filter parameters supported).

**Response:**

**Success (200 OK):**

```json
{
  "count": 42
}
```

**Response Fields:**

- `count` (integer): Total number of contacts matching the filters

**Error (404 Not Found) - Company not found:**

```json
{
  "detail": "Company not found"
}
```

**Error (401 Unauthorized):**

```json
{
  "detail": "Not authenticated"
}
```

**Status Codes:**

- `200 OK`: Success
- `401 Unauthorized`: Authentication required
- `404 Not Found`: Company not found
- `500 Internal Server Error`: Server error

**Example Request:**

```bash
GET /api/v3/companies/company/abc-123-uuid/contacts/count/?title=engineer
Authorization: Bearer <access_token>
```

**Notes:**

- Returns exact count of contacts matching the filters
- Supports all the same filter parameters as the list endpoint

---

### GET /api/v3/companies/company/{company_uuid}/contacts/filters - Get Company Contact Filters

Get available filters for contacts within a specific company. Returns a list of filter definitions with metadata about each filterable field.

**Headers:**

- `Authorization: Bearer <access_token>` (required)

**Path Parameters:**

- `company_uuid` (string, required): Company UUID identifier

**Response:**

**Success (200 OK):**

```json
{
  "data": [
    {
      "key": "first_name",
      "type": "text",
      "label": "First Name",
      "direct_derived": true
    },
    {
      "key": "departments",
      "type": "keyword",
      "label": "Departments",
      "direct_derived": false
    },
    {
      "key": "email_status",
      "type": "keyword",
      "label": "Email Status",
      "direct_derived": false
    }
  ]
}
```

**Response Fields:**

- `data` (array): Array of filter definition objects
  - `key` (string): Filter identifier used in queries (matches field names)
  - `type` (string): Filter type (text, keyword, range)
  - `label` (string): Human-readable name for UI display
  - `direct_derived` (boolean): Whether filter values are extracted directly from records (`true`) or stored in filters_data table (`false`)

**Error (404 Not Found) - Company not found:**

```json
{
  "detail": "Company not found"
}
```

**Error (401 Unauthorized):**

```json
{
  "detail": "Not authenticated"
}
```

**Status Codes:**

- `200 OK`: Filters retrieved successfully
- `401 Unauthorized`: Authentication required
- `404 Not Found`: Company not found
- `500 Internal Server Error`: Server error during filter retrieval

**Example Request:**

```bash
GET /api/v3/companies/company/abc-123-uuid/contacts/filters
Authorization: Bearer <access_token>
```

**Notes:**

- Returns all available filterable fields for contacts (same as `/api/v3/contacts/filters`)
- Filter definitions include metadata for building filter UIs
- `direct_derived: true` filters extract values directly from records
- `direct_derived: false` filters use pre-computed values from filters_data table

---

### POST /api/v3/companies/company/{company_uuid}/contacts/filters/data - Get Company Contact Filter Data

Get filter data values for contacts within a specific company with optional search and pagination. Values are scoped to only contacts belonging to the specified company.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Path Parameters:**

- `company_uuid` (string, required): Company UUID identifier

**Request Body:**

```json
{
  "service": "contact",
  "filter_key": "departments",
  "search_text": "Eng",
  "page": 1,
  "limit": 25
}
```

**Request Body Fields:**

- `service` (string, required): Service name - must be `"contact"` or `"company"`
- `filter_key` (string, required): Filter key from the filters list (e.g., "departments", "seniority", "email_status")
- `search_text` (string, optional): Text to filter results (case-insensitive, partial match)
- `page` (integer, optional, default: 1, min: 1): Page number
- `limit` (integer, optional, default: 25, min: 1, max: 100): Results per page

**Response:**

**Success (200 OK):**

```json
{
  "data": [
    "Engineering",
    "Engineering Operations",
    "Engineering Management"
  ]
}
```

**Response Fields:**

- `data` (array[string]): Array of filter values matching the search criteria, scoped to contacts in this company

**Error (400 Bad Request) - Invalid Service:**

```json
{
  "detail": "Service must be 'contact' or 'company'"
}
```

**Error (404 Not Found) - Company not found:**

```json
{
  "detail": "Company not found"
}
```

**Error (401 Unauthorized):**

```json
{
  "detail": "Not authenticated"
}
```

**Error (422 Unprocessable Entity) - Validation Error:**

```json
{
  "detail": [
    {
      "loc": ["body", "filter_key"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**Status Codes:**

- `200 OK`: Filter data retrieved successfully
- `400 Bad Request`: Invalid service parameter
- `401 Unauthorized`: Authentication required
- `404 Not Found`: Company not found
- `422 Unprocessable Entity`: Validation error in request body
- `500 Internal Server Error`: Server error during filter data retrieval

**Example Requests:**

```bash
# Get all department values for contacts in a company
POST /api/v3/companies/company/abc-123-uuid/contacts/filters/data
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "service": "contact",
  "filter_key": "departments",
  "page": 1,
  "limit": 25
}

# Search for departments containing "Eng" in a company
POST /api/v3/companies/company/abc-123-uuid/contacts/filters/data
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "service": "contact",
  "filter_key": "departments",
  "search_text": "Eng",
  "page": 1,
  "limit": 25
}

# Get seniority values for contacts in a company
POST /api/v3/companies/company/abc-123-uuid/contacts/filters/data
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "service": "contact",
  "filter_key": "seniority",
  "page": 1,
  "limit": 100
}
```

**Notes:**

- Filter values are scoped to only contacts within the specified company
- Use this endpoint to populate filter dropdowns and autocomplete fields for company contacts
- `search_text` enables autocomplete-style filtering of filter values
- Supports pagination for filters with many distinct values
- Filter values are returned as strings suitable for use in VQL queries
- Array fields (e.g., `departments`) are automatically flattened
- For large companies with many contacts, the endpoint queries up to 1000 contacts to extract distinct values

---

## VQL Query Language

VQL (Vivek Query Language) is a flexible query language for filtering and querying companies. It supports:

### Filter Operators

- `eq`: Equal (exact match)
- `ne`: Not equal
- `gt`: Greater than
- `gte`: Greater than or equal
- `lt`: Less than
- `lte`: Less than or equal
- `in`: Value is in array
- `nin`: Value is not in array
- `contains`: Array contains or string contains (case-insensitive)
- `ncontains`: Array doesn't contain or string doesn't contain
- `exists`: Field exists (not null)
- `nexists`: Field doesn't exist (is null)

### Filter Logic

VQL filters use `and` and `or` arrays to group conditions:

- `and`: Array of conditions - all must match
- `or`: Array of conditions - at least one must match

### Example Filter Structures

**Simple filter:**

```json
{
  "filters": {
    "and": [
      {
        "field": "name",
        "operator": "contains",
        "value": "Acme"
      }
    ]
  }
}
```

**Multiple conditions with AND:**

```json
{
  "filters": {
    "and": [
      {
        "field": "name",
        "operator": "contains",
        "value": "Acme"
      },
      {
        "field": "employees_count",
        "operator": "gte",
        "value": 100
      }
    ]
  }
}
```

**Multiple conditions with OR:**

```json
{
  "filters": {
    "or": [
      {
        "field": "name",
        "operator": "contains",
        "value": "Tech"
      },
      {
        "field": "name",
        "operator": "contains",
        "value": "Software"
      }
    ]
  }
}
```

**Nested AND/OR:**

```json
{
  "filters": {
    "and": [
      {
        "field": "employees_count",
        "operator": "gte",
        "value": 100
      },
      {
        "or": [
          {
            "field": "name",
            "operator": "contains",
            "value": "Tech"
          },
          {
            "field": "name",
            "operator": "contains",
            "value": "Software"
          }
        ]
      }
    ]
  }
}
```

**Numeric comparison:**

```json
{
  "filters": {
    "and": [
      {
        "field": "employees_count",
        "operator": "gte",
        "value": 100
      }
    ]
  }
}
```

**Array contains:**

```json
{
  "filters": {
    "and": [
      {
        "field": "industries",
        "operator": "contains",
        "value": "Technology"
      }
    ]
  }
}
```

---

## Response Schemas

### CompanyListItem

Schema for company items in list responses:

```json
{
  "uuid": "string",
  "name": "string | null",
  "employees_count": "integer | null",
  "annual_revenue": "integer | null",
  "total_funding": "integer | null",
  "industry": "string | null",
  "city": "string | null",
  "state": "string | null",
  "country": "string | null",
  "website": "string | null",
  "linkedin_url": "string | null",
  "phone_number": "string | null",
  "technologies": ["string"] | null,
  "keywords": ["string"] | null,
      "metadata": {
    "uuid": "string",
    "linkedin_url": "string | null",
    "linkedin_sales_url": "string | null",
    "facebook_url": "string | null",
    "twitter_url": "string | null",
    "website": "string | null",
    "company_name_for_emails": "string | null",
    "phone_number": "string | null",
    "latest_funding": "string | null",
    "latest_funding_amount": "integer | null",
    "last_raised_at": "string | null",
    "city": "string | null",
    "state": "string | null",
    "country": "string | null"
  } | null
}
```

### CompanyDetail

Schema for detailed company information (extends CompanyListItem):

```json
{
  "uuid": "string",
  "name": "string | null",
  "employees_count": "integer | null",
  "annual_revenue": "integer | null",
  "total_funding": "integer | null",
  "industry": "string | null",
  "city": "string | null",
  "state": "string | null",
  "country": "string | null",
  "website": "string | null",
  "linkedin_url": "string | null",
  "phone_number": "string | null",
  "technologies": ["string"] | null,
  "keywords": ["string"] | null,
  "metadata": {
    "uuid": "string",
    "linkedin_url": "string | null",
    "linkedin_sales_url": "string | null",
    "facebook_url": "string | null",
    "twitter_url": "string | null",
    "website": "string | null",
    "company_name_for_emails": "string | null",
    "phone_number": "string | null",
    "latest_funding": "string | null",
    "latest_funding_amount": "integer | null",
    "last_raised_at": "string | null",
    "city": "string | null",
    "state": "string | null",
    "country": "string | null"
  } | null,
  "created_at": "datetime | null",
  "updated_at": "datetime | null"
}
```

### CursorPage

Schema for paginated responses:

```json
{
  "next": "string | null",
  "previous": "string | null",
  "results": [CompanyListItem],
  "meta": {
    "strategy": "string",
    "count_mode": "string",
    "count": "integer",
    "filters_applied": "boolean",
    "ordering": "string",
    "returned_records": "integer",
    "page_size": "integer",
    "page_size_cap": "integer",
    "using_replica": "boolean"
  }
}
```

### CountResponse

Schema for count responses:

```json
{
  "count": "integer"
}
```

---

## Error Handling

### Common Error Responses

**400 Bad Request - Invalid VQL Query:**

```json
{
  "detail": "Invalid VQL query: <error details>"
}
```

**401 Unauthorized:**

```json
{
  "detail": "Not authenticated"
}
```

**404 Not Found:**

```json
{
  "detail": "Not found."
}
```

**404 Not Found - Company not found:**

```json
{
  "detail": "Company not found"
}
```

**500 Internal Server Error:**

```json
{
  "detail": "An error occurred while processing the request. Please check your query parameters and try again."
}
```

---

## Notes

- All timestamps are in ISO 8601 format (UTC): `YYYY-MM-DDTHH:MM:SSZ`
- The VQL query endpoint replaces the old GET /api/v3/companies/ endpoint
- The VQL count endpoint replaces the old GET /api/v3/companies/count/ endpoint
- Field-specific endpoints (name, industry, keywords, technologies, city, state, country, address) have been removed - use VQL query endpoint with field selection instead
- Write operations (create, update, delete) are not available through the Companies API endpoints
- VQL supports complex filter conditions with AND/OR logic
- Use `select_columns` to reduce response size by selecting only needed fields
- Use `company_config` and `contact_config` to populate related entity data
- Pagination uses limit-offset strategy for VQL endpoints
- Company contacts endpoints support both limit-offset and cursor-based pagination
- All text searches are case-insensitive
- Array fields (industries, keywords, technologies) support array contains operations in VQL
- Department values in company contact attribute endpoints are automatically expanded from array fields
