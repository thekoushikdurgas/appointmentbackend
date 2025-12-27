# Contacts API Documentation

Complete API documentation for contact management endpoints using VQL (Vivek Query Language) for flexible querying and filtering.

**Related Documentation:**

- [Companies API](./company.md) - For company management and company contact endpoints
- [Export API](./export.md) - For exporting contact data
- [User API](./user.md) - For authentication endpoints

## Table of Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [Contact Endpoints](#contact-endpoints)
  - [POST /api/v3/contacts/query](#post-apiv3contactsquery---query-contacts)
  - [POST /api/v3/contacts/count](#post-apiv3contactscount---count-contacts)
  - [GET /api/v3/contacts/filters](#get-apiv3contactsfilters---get-contact-filters)
  - [POST /api/v3/contacts/filters/data](#post-apiv3contactsfiltersdata---get-contact-filter-data)
  - [GET /api/v3/contacts/{contact_uuid}/](#get-apiv3contactscontact_uuid---retrieve-contact)
- [VQL Query Language](#vql-query-language)
- [Response Schemas](#response-schemas)
- [Error Handling](#error-handling)
- [Notes](#notes)

---

## Base URL

```txt
http://54.87.173.234:8000
```

**API Version:** All endpoints are under `/api/v3/contacts/`

## Authentication

All contact endpoints require JWT authentication via the `Authorization` header:

```txt
Authorization: Bearer <access_token>
```

Tokens are obtained through the login or register endpoints.

## Role-Based Access Control

All contact endpoints are accessible to all authenticated users:

- **Free Users (`FreeUser`)**: ✅ Full access to all contact endpoints
- **Pro Users (`ProUser`)**: ✅ Full access to all contact endpoints
- **Admin (`Admin`)**: ✅ Full access to all contact endpoints
- **Super Admin (`SuperAdmin`)**: ✅ Full access to all contact endpoints

---

## Contact Endpoints

### POST /api/v3/contacts/query - Query Contacts

Query contacts using VQL (Vivek Query Language). This endpoint replaces the old GET /contacts/ endpoint with a more flexible filter-based query system supporting complex conditions, field selection, and related entity population.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Request Body:**

```json
{
  "filters": {
    "and": [
{
        "field": "first_name",
        "operator": "contains",
        "value": "John"
      },
      {
        "field": "email_status",
        "operator": "eq",
        "value": "valid"
      }
    ]
  },
  "select_columns": ["uuid", "first_name", "last_name", "email", "title"],
  "company_config": {
    "populate": true,
    "select_columns": ["name", "employees_count"]
  },
  "limit": 25,
  "offset": 0,
  "sort_by": "created_at",
  "sort_direction": "desc"
}
```

**Request Body Fields:**

- `filters` (object, optional): Filter conditions using VQL filter structure
  - `conditions` (array): Array of filter conditions
    - `field` (string): Field name to filter on
    - `operator` (string): Comparison operator (equals, contains, gt, lt, etc.)
    - `value` (any): Value to compare against
  - `logic` (string): Logical operator connecting conditions ("AND" or "OR")
- `select_columns` (array[string], optional): Columns to select from main entity. If not provided, returns all columns.
- `company_config` (object, optional): Configuration for populating company data
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
  "next": "http://54.87.173.234:8000/api/v3/contacts/query?offset=25",
  "previous": null,
  "results": [
    {
      "uuid": "abc123-def456-ghi789",
      "first_name": "John",
      "last_name": "Doe",
      "email": "john.doe@example.com",
      "title": "CEO",
      "company": {
        "name": "Acme Corp",
        "employees_count": 100
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
- `results` (array): Array of contact objects matching the query
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
  "detail": "Invalid VQL query: filters.conditions[0].field: field is required"
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
POST /api/v3/contacts/query
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "filters": {
    "and": [
{
        "field": "first_name",
        "operator": "contains",
        "value": "John"
      }
    ]
  },
  "limit": 10
}

# Query with company population
POST /api/v3/contacts/query
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "filters": {
    "and": [
      {
        "field": "email_status",
        "operator": "eq",
        "value": "valid"
}
    ]
  },
  "company_config": {
    "populate": true,
    "select_columns": ["name", "employees_count"]
  },
  "limit": 25,
  "sort_by": "created_at",
  "sort_direction": "desc"
}
```

**Notes:**

- This endpoint replaces the old GET /api/v3/contacts/ endpoint
- Uses VQL (Vivek Query Language) for flexible querying
- Supports complex filter conditions with AND/OR logic
- Supports field selection to reduce response size
- Supports populating related entities (company, contact metadata)
- Uses limit-offset pagination

---

### POST /api/v3/contacts/count - Count Contacts

Count contacts matching a VQL query. This endpoint replaces the old GET /contacts/count/ endpoint.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Request Body:**

```json
{
  "filters": {
    "conditions": [
      {
        "field": "email_status",
        "operator": "equals",
        "value": "valid"
      }
    ],
    "logic": "AND"
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

- `count` (integer): Total number of contacts matching the query

**Error (400 Bad Request) - Invalid VQL Query:**

```json
{
  "detail": "Invalid VQL query: filters.conditions[0].field: field is required"
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
# Count all contacts
POST /api/v3/contacts/count
Authorization: Bearer <access_token>
Content-Type: application/json

{}

# Count with filters
POST /api/v3/contacts/count
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "filters": {
    "and": [
      {
        "field": "email_status",
        "operator": "eq",
        "value": "valid"
    },
    {
        "field": "first_name",
        "operator": "contains",
        "value": "John"
    }
  ]
  }
}
```

**Notes:**

- This endpoint replaces the old GET /api/v3/contacts/count/ endpoint
- Uses the same VQL filter structure as the query endpoint
- Returns exact count of matching contacts

---

### GET /api/v3/contacts/filters - Get Contact Filters

Get available filters for contacts. Returns a list of filter definitions with metadata about each filterable field.

**Headers:**

- `Authorization: Bearer <access_token>` (required)

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
GET /api/v3/contacts/filters
Authorization: Bearer <access_token>
```

**Notes:**

- Returns all available filterable fields for contacts
- Filter definitions include metadata for building filter UIs
- `direct_derived: true` filters extract values directly from records
- `direct_derived: false` filters use pre-computed values from filters_data table

---

### POST /api/v3/contacts/filters/data - Get Contact Filter Data

Get filter data values for a specific contact filter with optional search and pagination.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

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
# Get all department values
POST /api/v3/contacts/filters/data
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "service": "contact",
  "filter_key": "departments",
  "page": 1,
  "limit": 25
}

# Search for departments containing "Eng"
POST /api/v3/contacts/filters/data
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "service": "contact",
  "filter_key": "departments",
  "search_text": "Eng",
  "page": 1,
  "limit": 25
}

# Get seniority values
POST /api/v3/contacts/filters/data
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

- Use this endpoint to populate filter dropdowns and autocomplete fields
- `search_text` enables autocomplete-style filtering of filter values
- Supports pagination for filters with many distinct values
- Filter values are returned as strings suitable for use in VQL queries
- `direct_derived: true` filters extract values directly from records
- `direct_derived: false` filters use pre-computed values for faster access

---

### GET /api/v3/contacts/{contact_uuid}/ - Retrieve Contact

Get detailed information about a specific contact by UUID.

**Headers:**

- `Authorization: Bearer <access_token>` (required)

**Path Parameters:**

- `contact_uuid` (string, required): Contact UUID

**Response:**

**Success (200 OK):**

```json
{
  "uuid": "abc123-def456-ghi789",
  "first_name": "John",
  "last_name": "Doe",
  "company_id": "company-uuid-123",
  "email": "john.doe@example.com",
  "title": "CEO",
  "departments": ["executive"],
  "mobile_phone": "+1234567890",
  "email_status": "valid",
  "text_search": "San Francisco, CA",
  "seniority": "c-level",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

**Response Fields:**

- `uuid` (string): Contact UUID
- `first_name` (string, optional): Contact first name
- `last_name` (string, optional): Contact last name
- `company_id` (string, optional): UUID of the related company
- `email` (string, optional): Contact email address
- `title` (string, optional): Job title
- `departments` (array[string], optional): List of departments
- `mobile_phone` (string, optional): Mobile phone number
- `email_status` (string, optional): Email verification status
- `text_search` (string, optional): Free-form search text
- `seniority` (string, optional): Seniority level
- `created_at` (datetime, optional): Contact creation timestamp
- `updated_at` (datetime, optional): Contact last update timestamp

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

- `200 OK`: Contact retrieved successfully
- `401 Unauthorized`: Authentication required
- `404 Not Found`: Contact not found

**Example Request:**

```bash
GET /api/v3/contacts/abc123-def456-ghi789/
Authorization: Bearer <access_token>
```

**Notes:**

- Returns full contact details including all fields
- Contact must exist in the database

---

## VQL Query Language

VQL (Vivek Query Language) is a flexible query language for filtering and querying contacts. It supports:

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
        "field": "first_name",
        "operator": "contains",
        "value": "John"
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
        "field": "first_name",
        "operator": "contains",
        "value": "John"
    },
    {
        "field": "email_status",
        "operator": "eq",
        "value": "valid"
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
        "field": "title",
        "operator": "contains",
        "value": "CEO"
    },
    {
        "field": "title",
        "operator": "contains",
        "value": "CTO"
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
        "field": "email_status",
        "operator": "eq",
        "value": "valid"
      },
      {
        "or": [
          {
            "field": "title",
            "operator": "contains",
            "value": "CEO"
          },
          {
            "field": "title",
            "operator": "contains",
            "value": "CTO"
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

---

## Response Schemas

### ContactListItem

Schema for contact items in list responses:

```json
{
  "uuid": "string",
  "first_name": "string | null",
  "last_name": "string | null",
  "company_id": "string | null",
  "email": "string | null",
  "title": "string | null",
  "departments": ["string"] | null,
  "mobile_phone": "string | null",
  "email_status": "string | null",
  "text_search": "string | null",
  "seniority": "string | null",
  "created_at": "datetime | null",
  "updated_at": "datetime | null"
}
```

### ContactDetail

Schema for detailed contact information:

```json
{
  "uuid": "string",
  "first_name": "string | null",
  "last_name": "string | null",
  "company_id": "string | null",
  "email": "string | null",
  "title": "string | null",
  "departments": ["string"] | null,
  "mobile_phone": "string | null",
  "email_status": "string | null",
  "text_search": "string | null",
  "seniority": "string | null",
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
  "results": [ContactListItem],
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

**500 Internal Server Error:**

```json
{
  "detail": "An error occurred while processing the request. Please check your query parameters and try again."
}
```

---

## Notes

- All timestamps are in ISO 8601 format (UTC): `YYYY-MM-DDTHH:MM:SSZ`
- The VQL query endpoint replaces the old GET /api/v3/contacts/ endpoint
- The VQL count endpoint replaces the old GET /api/v3/contacts/count/ endpoint
- Field-specific endpoints and import endpoints have been removed - use VQL query endpoint with field selection instead
- VQL supports complex filter conditions with AND/OR logic
- Use `select_columns` to reduce response size by selecting only needed fields
- Use `company_config` and `contact_config` to populate related entity data
- Pagination uses limit-offset strategy
- All text searches are case-insensitive
