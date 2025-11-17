# Company WebSocket API Documentation

Complete WebSocket API documentation for company management endpoints, providing real-time bidirectional communication for company operations.

## Base URL

For production, use:

```txt
ws://54.87.173.234:8000
```

## Authentication

WebSocket connections are authenticated using JWT tokens passed as query parameters during the WebSocket handshake:

```
ws://host:port/api/v1/companies/ws?token=<jwt_token>
```

**Important:** The token must be a valid access token obtained from the login or register endpoints.

**Write Operations:** For create, update, and delete operations, you must:
1. Be authenticated as an admin user
2. Include the `write_key` or `X-Companies-Write-Key` field in the request `data` object

## Unified WebSocket Endpoint

All company WebSocket operations are handled through a single unified endpoint:

### WS /api/v1/companies/ws - Unified Company WebSocket Endpoint

This endpoint handles all company operations over a single persistent WebSocket connection. You can send multiple requests with different actions on the same connection.

**Connection URL:**
```
ws://host:port/api/v1/companies/ws?token=<jwt_token>
```

**Supported Actions (25 total):**

**Main Company Operations (7):**
- `list_companies` - List companies with filtering/pagination
- `get_company` - Retrieve single company by UUID
- `count_companies` - Count companies matching filters
- `get_company_uuids` - Get company UUIDs matching filters
- `create_company` - Create new company (requires admin + write key)
- `update_company` - Update existing company (requires admin + write key)
- `delete_company` - Delete company (requires admin + write key)

**Company Attribute Lookups (8):**
- `list_company_names` - List distinct company names
- `list_industries` - List distinct industries
- `list_keywords` - List distinct keywords
- `list_technologies` - List distinct technologies
- `list_company_cities` - List distinct cities
- `list_company_states` - List distinct states
- `list_company_countries` - List distinct countries
- `list_company_addresses` - List distinct addresses

**Company Contact Operations (10):**
- `list_company_contacts` - List contacts for a company
- `count_company_contacts` - Count contacts for a company
- `get_company_contact_uuids` - Get contact UUIDs for a company
- `list_company_contact_first_names` - List distinct first names
- `list_company_contact_last_names` - List distinct last names
- `list_company_contact_titles` - List distinct titles
- `list_company_contact_seniorities` - List distinct seniorities
- `list_company_contact_departments` - List distinct departments
- `list_company_contact_email_statuses` - List distinct email statuses

## Message Format

All WebSocket messages use JSON format with the following structure:

**Request Message:**
```json
{
  "action": "list_companies",
  "request_id": "req-123",
  "data": {
    "name": "Acme",
    "limit": 50
  }
}
```

**Response Message (Success):**
```json
{
  "request_id": "req-123",
  "action": "list_companies",
  "status": "success",
  "data": {
    // Response payload (varies by action)
  }
}
```

**Error Response:**
```json
{
  "request_id": "req-123",
  "action": "list_companies",
  "status": "error",
  "data": null,
  "error": {
    "message": "Error description",
    "code": "error_code"
  }
}
```

## WebSocket Actions

### Action: list_companies

List companies with optional filtering, searching, and ordering.

**Request Message:**
```json
{
  "action": "list_companies",
  "request_id": "req-1",
  "data": {
    "name": "Acme",
    "employees_min": 100,
    "industries": "Technology,Software",
    "limit": 50,
    "offset": 0,
    "ordering": "-employees_count"
  }
}
```

**Request Data Fields:**

All filter parameters from the REST API `/api/v1/companies/` endpoint are supported:
- Text filters: `name`, `address`, `company_location`, `city`, `state`, `country`, `phone_number`, `website`, `linkedin_url`, `facebook_url`, `twitter_url`
- Exact match: `employees_count`, `annual_revenue`, `total_funding`
- Numeric ranges: `employees_min`, `employees_max`, `annual_revenue_min`, `annual_revenue_max`, `total_funding_min`, `total_funding_max`
- Array filters: `industries`, `keywords`, `technologies` (comma-separated or arrays)
- Exclusion filters: `exclude_industries`, `exclude_keywords`, `exclude_technologies` (arrays)
- Date ranges: `created_at_after`, `created_at_before`, `updated_at_after`, `updated_at_before`
- Search and ordering: `search`, `ordering`
- Pagination: `limit`, `offset`, `cursor`, `page`, `page_size`
- Advanced: `distinct`, `request_url`

**Response Message (Success):**
```json
{
  "request_id": "req-1",
  "action": "list_companies",
  "status": "success",
  "data": {
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
          "website": "https://acme.com"
        },
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-15T10:30:00Z"
      }
    ]
  }
}
```

---

### Action: get_company

Retrieve a single company by UUID.

**Request Message:**
```json
{
  "action": "get_company",
  "request_id": "req-2",
  "data": {
    "company_uuid": "398cce44-233d-5f7c-aea1-e4a6a79df10c"
  }
}
```

**Request Data Fields:**
- `company_uuid` (string, required): Company UUID

**Response Message (Success):**
```json
{
  "request_id": "req-2",
  "action": "get_company",
  "status": "success",
  "data": {
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
      "linkedin_url": "https://linkedin.com/company/acme"
    },
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

---

### Action: count_companies

Count companies matching filters.

**Request Message:**
```json
{
  "action": "count_companies",
  "request_id": "req-3",
  "data": {
    "industries": "Technology",
    "employees_min": 100
  }
}
```

**Request Data Fields:**

All filter parameters from `list_companies` are supported (except pagination parameters).

**Response Message (Success):**
```json
{
  "request_id": "req-3",
  "action": "count_companies",
  "status": "success",
  "data": {
    "count": 15000
  }
}
```

---

### Action: get_company_uuids

Get company UUIDs matching filters.

**Request Message:**
```json
{
  "action": "get_company_uuids",
  "request_id": "req-4",
  "data": {
    "industries": "Technology",
    "employees_min": 100,
    "limit": 500
  }
}
```

**Request Data Fields:**

All filter parameters from `list_companies` are supported, plus:
- `limit` (integer, optional): Maximum number of UUIDs to return. If not provided, returns all matching UUIDs (unlimited).

**Response Message (Success):**
```json
{
  "request_id": "req-4",
  "action": "get_company_uuids",
  "status": "success",
  "data": {
    "count": 567,
    "uuids": [
      "398cce44-233d-5f7c-aea1-e4a6a79df10c",
      "498cce44-233d-5f7c-aea1-e4a6a79df10d",
      "598cce44-233d-5f7c-aea1-e4a6a79df10e"
    ]
  }
}
```

---

### Action: create_company

Create a new company. Requires admin authentication and write key.

**Request Message:**
```json
{
  "action": "create_company",
  "request_id": "req-5",
  "data": {
    "write_key": "your_write_key_here",
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
      "website": "https://acme.com"
    }
  }
}
```

**Request Data Fields:**

All fields are optional:
- `write_key` or `X-Companies-Write-Key` (string, required for write operations): Write authorization key
- `uuid` (string, optional): Company UUID (auto-generated if not provided)
- `name`, `employees_count`, `industries`, `keywords`, `address`, `annual_revenue`, `total_funding`, `technologies`, `text_search`
- `metadata` (object, optional): Metadata fields (city, state, country, phone_number, website, linkedin_url, facebook_url, twitter_url)

**Response Message (Success):**
```json
{
  "request_id": "req-5",
  "action": "create_company",
  "status": "success",
  "data": {
    // CompanyDetail object (same structure as get_company response)
  }
}
```

---

### Action: update_company

Update an existing company. Requires admin authentication and write key.

**Request Message:**
```json
{
  "action": "update_company",
  "request_id": "req-6",
  "data": {
    "write_key": "your_write_key_here",
    "company_uuid": "398cce44-233d-5f7c-aea1-e4a6a79df10c",
    "name": "Acme Corporation Updated",
    "employees_count": 300,
    "annual_revenue": 60000000,
    "industries": ["Technology", "Software", "AI"]
  }
}
```

**Request Data Fields:**
- `write_key` or `X-Companies-Write-Key` (string, required): Write authorization key
- `company_uuid` (string, required): Company UUID to update
- All other fields are optional (partial update)

**Response Message (Success):**
```json
{
  "request_id": "req-6",
  "action": "update_company",
  "status": "success",
  "data": {
    // Updated CompanyDetail object
  }
}
```

---

### Action: delete_company

Delete a company. Requires admin authentication and write key.

**Request Message:**
```json
{
  "action": "delete_company",
  "request_id": "req-7",
  "data": {
    "write_key": "your_write_key_here",
    "company_uuid": "398cce44-233d-5f7c-aea1-e4a6a79df10c"
  }
}
```

**Request Data Fields:**
- `write_key` or `X-Companies-Write-Key` (string, required): Write authorization key
- `company_uuid` (string, required): Company UUID to delete

**Response Message (Success):**
```json
{
  "request_id": "req-7",
  "action": "delete_company",
  "status": "success",
  "data": {}
}
```

---

### Action: list_company_names

List distinct company names.

**Request Message:**
```json
{
  "action": "list_company_names",
  "request_id": "req-8",
  "data": {
    "search": "acme",
    "limit": 50,
    "offset": 0,
    "ordering": "value"
  }
}
```

**Request Data Fields:**

All filter parameters from `list_companies` are supported, plus:
- `search` (string): Search term to filter results
- `distinct` (boolean, default: true): Return only distinct values
- `limit` (integer): Maximum number of results
- `offset` (integer): Offset for pagination
- `ordering` (string): Sort order (`value`, `-value`, `count`, `-count`)

**Response Message (Success):**
```json
{
  "request_id": "req-8",
  "action": "list_company_names",
  "status": "success",
  "data": {
    "results": [
      "Acme Corporation",
      "Tech Innovations Inc"
    ]
  }
}
```

---

### Action: list_industries

List distinct industries.

**Request Message:**
```json
{
  "action": "list_industries",
  "request_id": "req-9",
  "data": {
    "separated": true,
    "ordering": "-count",
    "limit": 100
  }
}
```

**Request Data Fields:**

All filter parameters from `list_companies` are supported, plus:
- `separated` (boolean, default: false): If `true`, expands array into individual industry values
- `search`, `distinct`, `limit`, `offset`, `ordering`

**Response Message (Success):**
```json
{
  "request_id": "req-9",
  "action": "list_industries",
  "status": "success",
  "data": {
    "results": [
      "Technology",
      "Software",
      "Healthcare"
    ]
  }
}
```

---

### Action: list_keywords

List distinct keywords.

**Request Message:**
```json
{
  "action": "list_keywords",
  "request_id": "req-10",
  "data": {
    "separated": true,
    "search": "cloud",
    "limit": 100
  }
}
```

**Request Data Fields:**

Same as `list_industries` (supports `separated` parameter).

**Response Message (Success):**
```json
{
  "request_id": "req-10",
  "action": "list_keywords",
  "status": "success",
  "data": {
    "results": [
      "enterprise",
      "saas",
      "cloud"
    ]
  }
}
```

---

### Action: list_technologies

List distinct technologies.

**Request Message:**
```json
{
  "action": "list_technologies",
  "request_id": "req-11",
  "data": {
    "separated": true,
    "search": "python",
    "ordering": "-count"
  }
}
```

**Request Data Fields:**

Same as `list_industries` (supports `separated` parameter).

**Response Message (Success):**
```json
{
  "request_id": "req-11",
  "action": "list_technologies",
  "status": "success",
  "data": {
    "results": [
      "Python",
      "AWS",
      "PostgreSQL"
    ]
  }
}
```

---

### Action: list_company_cities

List distinct company cities.

**Request Message:**
```json
{
  "action": "list_company_cities",
  "request_id": "req-12",
  "data": {
    "search": "san",
    "limit": 50,
    "ordering": "-count"
  }
}
```

**Request Data Fields:**

All filter parameters from `list_companies` are supported, plus:
- `search`, `distinct`, `limit`, `offset`, `ordering`

**Response Message (Success):**
```json
{
  "request_id": "req-12",
  "action": "list_company_cities",
  "status": "success",
  "data": {
    "results": [
      "San Francisco",
      "New York",
      "Los Angeles"
    ]
  }
}
```

---

### Action: list_company_states

List distinct company states.

**Request Message:**
```json
{
  "action": "list_company_states",
  "request_id": "req-13",
  "data": {
    "limit": 50,
    "ordering": "-count"
  }
}
```

**Request Data Fields:**

Same as `list_company_cities`.

**Response Message (Success):**
```json
{
  "request_id": "req-13",
  "action": "list_company_states",
  "status": "success",
  "data": {
    "results": [
      "California",
      "New York",
      "Texas"
    ]
  }
}
```

---

### Action: list_company_countries

List distinct company countries.

**Request Message:**
```json
{
  "action": "list_company_countries",
  "request_id": "req-14",
  "data": {
    "limit": 50,
    "ordering": "-count"
  }
}
```

**Request Data Fields:**

Same as `list_company_cities`.

**Response Message (Success):**
```json
{
  "request_id": "req-14",
  "action": "list_company_countries",
  "status": "success",
  "data": {
    "results": [
      "United States",
      "United Kingdom",
      "Canada"
    ]
  }
}
```

---

### Action: list_company_addresses

List distinct company addresses.

**Request Message:**
```json
{
  "action": "list_company_addresses",
  "request_id": "req-15",
  "data": {
    "search": "San Francisco",
    "limit": 50
  }
}
```

**Request Data Fields:**

Same as `list_company_cities`.

**Response Message (Success):**
```json
{
  "request_id": "req-15",
  "action": "list_company_addresses",
  "status": "success",
  "data": {
    "results": [
      "San Francisco CA United States",
      "New York NY United States"
    ]
  }
}
```

---

### Action: list_company_contacts

List contacts for a specific company.

**Request Message:**
```json
{
  "action": "list_company_contacts",
  "request_id": "req-16",
  "data": {
    "company_uuid": "398cce44-233d-5f7c-aea1-e4a6a79df10c",
    "title": "engineer",
    "seniority": "senior",
    "limit": 25,
    "offset": 0
  }
}
```

**Request Data Fields:**
- `company_uuid` (string, required): Company UUID identifier

All contact filter parameters from the REST API are supported:
- Contact identity: `first_name`, `last_name`, `title`, `seniority`, `department`, `email_status`, `email`, `contact_location`
- Contact metadata: `work_direct_phone`, `home_phone`, `mobile_phone`, `other_phone`, `city`, `state`, `country`, `person_linkedin_url`, `website`, `facebook_url`, `twitter_url`, `stage`
- Exclusion filters: `exclude_titles`, `exclude_contact_locations`, `exclude_seniorities`, `exclude_departments` (arrays)
- Temporal: `created_at_after`, `created_at_before`, `updated_at_after`, `updated_at_before`
- Search and ordering: `search`, `ordering`
- Pagination: `limit`, `offset`, `cursor`, `page`, `page_size`, `distinct`

**Response Message (Success):**
```json
{
  "request_id": "req-16",
  "action": "list_company_contacts",
  "status": "success",
  "data": {
    "next": "http://54.87.173.234:8000/api/v1/companies/company/abc-123-uuid/contacts/?cursor=...",
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
}
```

---

### Action: count_company_contacts

Count contacts for a specific company.

**Request Message:**
```json
{
  "action": "count_company_contacts",
  "request_id": "req-17",
  "data": {
    "company_uuid": "398cce44-233d-5f7c-aea1-e4a6a79df10c",
    "title": "engineer"
  }
}
```

**Request Data Fields:**
- `company_uuid` (string, required): Company UUID identifier
- All contact filter parameters from `list_company_contacts` are supported (except pagination)

**Response Message (Success):**
```json
{
  "request_id": "req-17",
  "action": "count_company_contacts",
  "status": "success",
  "data": {
    "count": 42
  }
}
```

---

### Action: get_company_contact_uuids

Get contact UUIDs for a specific company.

**Request Message:**
```json
{
  "action": "get_company_contact_uuids",
  "request_id": "req-18",
  "data": {
    "company_uuid": "398cce44-233d-5f7c-aea1-e4a6a79df10c",
    "title": "engineer",
    "limit": 100
  }
}
```

**Request Data Fields:**
- `company_uuid` (string, required): Company UUID identifier
- All contact filter parameters from `list_company_contacts` are supported, plus:
- `limit` (integer, optional): Maximum number of UUIDs to return. If not provided, returns all matching UUIDs (unlimited).

**Response Message (Success):**
```json
{
  "request_id": "req-18",
  "action": "get_company_contact_uuids",
  "status": "success",
  "data": {
    "count": 45,
    "uuids": [
      "contact-uuid-1",
      "contact-uuid-2",
      "contact-uuid-3"
    ]
  }
}
```

---

### Action: list_company_contact_first_names

List distinct first names for contacts in a company.

**Request Message:**
```json
{
  "action": "list_company_contact_first_names",
  "request_id": "req-19",
  "data": {
    "company_uuid": "398cce44-233d-5f7c-aea1-e4a6a79df10c",
    "search": "john",
    "limit": 25,
    "distinct": true
  }
}
```

**Request Data Fields:**
- `company_uuid` (string, required): Company UUID identifier
- All contact filter parameters are supported, plus:
- `search`, `distinct`, `limit`, `offset`, `ordering`

**Response Message (Success):**
```json
{
  "request_id": "req-19",
  "action": "list_company_contact_first_names",
  "status": "success",
  "data": {
    "results": [
      "John",
      "Jane",
      "Michael",
      "Sarah"
    ]
  }
}
```

---

### Action: list_company_contact_last_names

List distinct last names for contacts in a company.

**Request Message:**
```json
{
  "action": "list_company_contact_last_names",
  "request_id": "req-20",
  "data": {
    "company_uuid": "398cce44-233d-5f7c-aea1-e4a6a79df10c",
    "limit": 25
  }
}
```

**Request Data Fields:**

Same as `list_company_contact_first_names`.

**Response Message (Success):**
```json
{
  "request_id": "req-20",
  "action": "list_company_contact_last_names",
  "status": "success",
  "data": {
    "results": [
      "Doe",
      "Smith",
      "Johnson"
    ]
  }
}
```

---

### Action: list_company_contact_titles

List distinct titles for contacts in a company.

**Request Message:**
```json
{
  "action": "list_company_contact_titles",
  "request_id": "req-21",
  "data": {
    "company_uuid": "398cce44-233d-5f7c-aea1-e4a6a79df10c",
    "search": "engineer",
    "limit": 50
  }
}
```

**Request Data Fields:**

Same as `list_company_contact_first_names`.

**Response Message (Success):**
```json
{
  "request_id": "req-21",
  "action": "list_company_contact_titles",
  "status": "success",
  "data": {
    "results": [
      "Software Engineer",
      "Senior Manager",
      "Director of Engineering",
      "VP of Sales"
    ]
  }
}
```

---

### Action: list_company_contact_seniorities

List distinct seniorities for contacts in a company.

**Request Message:**
```json
{
  "action": "list_company_contact_seniorities",
  "request_id": "req-22",
  "data": {
    "company_uuid": "398cce44-233d-5f7c-aea1-e4a6a79df10c",
    "limit": 25
  }
}
```

**Request Data Fields:**

Same as `list_company_contact_first_names`.

**Response Message (Success):**
```json
{
  "request_id": "req-22",
  "action": "list_company_contact_seniorities",
  "status": "success",
  "data": {
    "results": [
      "junior",
      "mid",
      "senior",
      "executive"
    ]
  }
}
```

---

### Action: list_company_contact_departments

List distinct departments for contacts in a company.

**Request Message:**
```json
{
  "action": "list_company_contact_departments",
  "request_id": "req-23",
  "data": {
    "company_uuid": "398cce44-233d-5f7c-aea1-e4a6a79df10c",
    "limit": 25
  }
}
```

**Request Data Fields:**

Same as `list_company_contact_first_names`. Departments are automatically expanded from array fields.

**Response Message (Success):**
```json
{
  "request_id": "req-23",
  "action": "list_company_contact_departments",
  "status": "success",
  "data": {
    "results": [
      "Engineering",
      "Sales",
      "Marketing",
      "R&D",
      "Operations"
    ]
  }
}
```

---

### Action: list_company_contact_email_statuses

List distinct email statuses for contacts in a company.

**Request Message:**
```json
{
  "action": "list_company_contact_email_statuses",
  "request_id": "req-24",
  "data": {
    "company_uuid": "398cce44-233d-5f7c-aea1-e4a6a79df10c",
    "limit": 25
  }
}
```

**Request Data Fields:**

Same as `list_company_contact_first_names`.

**Response Message (Success):**
```json
{
  "request_id": "req-24",
  "action": "list_company_contact_email_statuses",
  "status": "success",
  "data": {
    "results": [
      "verified",
      "unverified",
      "bounced",
      "catch_all"
    ]
  }
}
```

---

## WebSocket Client Examples

### JavaScript Example

```javascript
const token = "your_jwt_token_here";

// Connect to unified WebSocket endpoint
const ws = new WebSocket(`ws://54.87.173.234:8000/api/v1/companies/ws?token=${token}`);

ws.onopen = () => {
  console.log("WebSocket connected");
  
  // Send list companies request
  ws.send(JSON.stringify({
    action: "list_companies",
    request_id: "req-1",
    data: {
      name: "Acme",
      employees_min: 100,
      limit: 50
    }
  }));
  
  // Send get company request
  setTimeout(() => {
    ws.send(JSON.stringify({
      action: "get_company",
      request_id: "req-2",
      data: {
        company_uuid: "398cce44-233d-5f7c-aea1-e4a6a79df10c"
      }
    }));
  }, 1000);
  
  // Send count companies request
  setTimeout(() => {
    ws.send(JSON.stringify({
      action: "count_companies",
      request_id: "req-3",
      data: {
        industries: "Technology",
        employees_min: 100
      }
    }));
  }, 2000);
};

ws.onmessage = (event) => {
  const response = JSON.parse(event.data);
  
  if (response.status === "success") {
    console.log(`Response for ${response.action}:`, response.data);
  } else {
    console.error(`Error for ${response.action}:`, response.error);
  }
};

ws.onerror = (error) => {
  console.error("WebSocket error:", error);
};

ws.onclose = (event) => {
  console.log("WebSocket closed:", event.code, event.reason);
};
```

### Python Example

```python
import asyncio
import json
import websockets

async def company_websocket_client():
    token = "your_jwt_token_here"
    uri = f"ws://54.87.173.234:8000/api/v1/companies/ws?token={token}"
    
    async with websockets.connect(uri) as websocket:
        # Send list companies request
        request = {
            "action": "list_companies",
            "request_id": f"req-{int(asyncio.get_event_loop().time())}",
            "data": {
                "name": "Acme",
                "employees_min": 100,
                "limit": 50
            }
        }
        
        await websocket.send(json.dumps(request))
        
        # Receive response
        response = await websocket.recv()
        data = json.loads(response)
        
        if data["status"] == "success":
            print("List companies result:", data["data"])
        else:
            print("Error:", data["error"])
        
        # Send another request on the same connection
        get_request = {
            "action": "get_company",
            "request_id": f"req-{int(asyncio.get_event_loop().time()) + 1}",
            "data": {
                "company_uuid": "398cce44-233d-5f7c-aea1-e4a6a79df10c"
            }
        }
        
        await websocket.send(json.dumps(get_request))
        
        # Receive second response
        response2 = await websocket.recv()
        data2 = json.loads(response2)
        
        if data2["status"] == "success":
            print("Get company result:", data2["data"])

# Run the client
asyncio.run(company_websocket_client())
```

## Connection Behavior

- **Persistent Connections**: Clients maintain a single WebSocket connection and can send multiple requests with different actions
- **Request Tracking**: Each request includes a `request_id` that is echoed in the response for correlation
- **Error Handling**: Errors are returned as JSON messages with `status: "error"` and error details
- **Connection Lifecycle**: Connections are automatically cleaned up when clients disconnect
- **Concurrent Requests**: Multiple requests can be sent on the same connection, but responses may arrive in any order (use `request_id` to match responses)
- **Action Routing**: The unified endpoint automatically routes messages to the appropriate handler based on the `action` field

## Error Handling

WebSocket errors are returned in the standard error response format:

```json
{
  "request_id": "req-123",
  "action": "list_companies",
  "status": "error",
  "data": null,
  "error": {
    "message": "Missing required field: company_uuid",
    "code": "missing_field"
  }
}
```

Common error codes:
- `missing_field` - Required field is missing from request data
- `invalid_json` - Request message is not valid JSON
- `validation_error` - Request data validation failed
- `unknown_action` - Action is not recognized
- `forbidden` - User does not have permission (for write operations)
- `not_found` - Company or resource not found
- `list_error` - Error during list operation
- `get_error` - Error during get operation
- `count_error` - Error during count operation
- `uuids_error` - Error during UUID retrieval
- `create_error` - Error during create operation
- `update_error` - Error during update operation
- `delete_error` - Error during delete operation
- `invalid_cursor` - Invalid cursor token for pagination

## Notes

- All datetime fields in responses are serialized as ISO format strings (e.g., `"2024-01-15T10:30:00"`)
- The unified endpoint supports all 25 actions on a single connection
- Request IDs should be unique per connection to properly track responses
- The connection remains open until explicitly closed by the client or server
- Write operations (create, update, delete) require both admin authentication and the write key
- Array filters (industries, keywords, technologies) can be provided as comma-separated strings or arrays
- Exclusion filters accept arrays of values
- The `separated` parameter in attribute endpoints expands array values into individual records
- Department values in company contact attribute endpoints are automatically expanded from array fields

