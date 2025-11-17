# Contacts WebSocket API Documentation

Complete WebSocket API documentation for Contacts endpoints, providing real-time bidirectional communication for contact management operations.

## Base URL

For production, use:

```txt
ws://54.87.173.234:8000
```

## Authentication

WebSocket connections are authenticated using JWT tokens passed as query parameters during the WebSocket handshake:

```
ws://host:port/api/v1/contacts/ws?token=<jwt_token>
```

**Important:** The token must be a valid access token obtained from the login or register endpoints.

**Admin Authentication:** For write operations (`create_contact`, `upload_contacts_csv`), the user must have admin privileges. The `create_contact` action also requires a `write_key` in the request data.

## Unified WebSocket Endpoint

All Contacts WebSocket operations are handled through a single unified endpoint:

### WS /api/v1/contacts/ws - Unified Contacts WebSocket Endpoint

This endpoint handles all Contacts operations over a single persistent WebSocket connection. You can send multiple requests with different actions on the same connection.

**Connection URL:**
```
ws://host:port/api/v1/contacts/ws?token=<jwt_token>
```

**Supported Actions (22 total):**

**Main Contact Endpoints (5):**

- `list_contacts` - List contacts with filtering/pagination
- `get_contact` - Retrieve single contact by UUID
- `count_contacts` - Get contact count
- `get_contact_uuids` - Get contact UUIDs
- `create_contact` - Create new contact (admin only)

**Field-Specific Endpoints (13):**

- `get_titles` - List titles
- `get_companies` - List companies
- `get_industries` - List industries
- `get_keywords` - List keywords
- `get_technologies` - List technologies
- `get_company_addresses` - List company addresses
- `get_contact_addresses` - List contact addresses
- `get_cities` - List contact cities
- `get_states` - List contact states
- `get_countries` - List contact countries
- `get_company_cities` - List company cities
- `get_company_states` - List company states
- `get_company_countries` - List company countries

**Import Endpoints (4):**

- `get_import_info` - Get import information
- `upload_contacts_csv` - Upload CSV for import (admin only)
- `get_import_status` - Get import job status
- `get_import_errors` - Get import errors

## Message Format

All WebSocket messages use JSON format with the following structure:

**Request Message:**
```json
{
  "action": "list_contacts",
  "request_id": "req-123",
  "data": {
    // Request payload (varies by action)
  }
}
```

**Response Message (Success):**
```json
{
  "request_id": "req-123",
  "action": "list_contacts",
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
  "action": "list_contacts",
  "status": "error",
  "data": null,
  "error": {
    "message": "Error description",
    "code": "error_code"
  }
}
```

## WebSocket Actions

### Action: list_contacts

List contacts with optional filtering, searching, and ordering.

**Request Message:**
```json
{
  "action": "list_contacts",
  "request_id": "req-123",
  "data": {
    "first_name": "John",
    "country": "United States",
    "employees_min": 50,
    "limit": 25,
    "offset": 0,
    "cursor": "cursor_token_here",
    "view": "simple",
    "ordering": "-employees,company"
  }
}
```

**Request Data Fields:**

All filter parameters from the REST API are supported. See the [REST API documentation](../api/contacts.md) for complete filter details. Key fields include:

- **Text Filters:** `first_name`, `last_name`, `title`, `company`, `email`, `city`, `state`, `country`, etc.
- **Numeric Filters:** `employees_min`, `employees_max`, `annual_revenue_min`, `annual_revenue_max`, etc.
- **Exclusion Filters:** `exclude_titles`, `exclude_seniorities`, `exclude_departments`, etc. (as arrays or comma-separated strings)
- **Pagination:** `limit` (integer, optional), `offset` (integer, default: 0), `cursor` (string, optional)
- **View:** `view` (string, optional): When "simple", returns simplified contact data
- **Ordering:** `ordering` (string, optional): Comma-separated fields to order by

**Response Message (Success):**
```json
{
  "request_id": "req-123",
  "action": "list_contacts",
  "status": "success",
  "data": {
    "next": "cursor_token_here",
    "previous": null,
    "results": [
      {
        "uuid": "abc123-def456-ghi789",
        "first_name": "John",
        "last_name": "Doe",
        "title": "CEO",
        "company": "Acme Corp",
        "email": "john@acme.com",
        "email_status": "valid",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
      }
    ]
  }
}
```

### Action: get_contact

Get detailed information about a specific contact by UUID.

**Request Message:**
```json
{
  "action": "get_contact",
  "request_id": "req-456",
  "data": {
    "contact_uuid": "abc123-def456-ghi789"
  }
}
```

**Request Data Fields:**

- `contact_uuid` (string, required): Contact UUID

**Response Message (Success):**
```json
{
  "request_id": "req-456",
  "action": "get_contact",
  "status": "success",
  "data": {
    "uuid": "abc123-def456-ghi789",
    "first_name": "John",
    "last_name": "Doe",
    "title": "CEO",
    "company": "Acme Corp",
    "email": "john@acme.com",
    "email_status": "valid",
    "seniority": "c-level",
    "departments": "executive",
    "city": "San Francisco",
    "state": "CA",
    "country": "United States",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
}
```

### Action: count_contacts

Get the total count of contacts, optionally filtered.

**Request Message:**
```json
{
  "action": "count_contacts",
  "request_id": "req-789",
  "data": {
    "country": "United States",
    "city": "San Francisco",
    "employees_min": 50
  }
}
```

**Request Data Fields:**

All filter parameters from the REST API are supported. See the [REST API documentation](../api/contacts.md) for complete filter details.

**Response Message (Success):**
```json
{
  "request_id": "req-789",
  "action": "count_contacts",
  "status": "success",
  "data": {
    "count": 1234
  }
}
```

### Action: get_contact_uuids

Get a list of contact UUIDs that match the provided filters.

**Request Message:**
```json
{
  "action": "get_contact_uuids",
  "request_id": "req-abc",
  "data": {
    "country": "United States",
    "email_status": "valid",
    "limit": 1000
  }
}
```

**Request Data Fields:**

All filter parameters from the REST API are supported, plus:

- `limit` (integer, optional): Maximum number of UUIDs to return. If not provided, returns all matching UUIDs (unlimited).

**Response Message (Success):**
```json
{
  "request_id": "req-abc",
  "action": "get_contact_uuids",
  "status": "success",
  "data": {
    "count": 100,
    "uuids": [
      "uuid1",
      "uuid2",
      "uuid3"
    ]
  }
}
```

### Action: create_contact

Create a new contact. Requires admin authentication and write key.

**Request Message:**
```json
{
  "action": "create_contact",
  "request_id": "req-create",
  "data": {
    "write_key": "your_write_key_here",
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
}
```

**Request Data Fields:**

- `write_key` (string, required): Write authorization key
- All fields from `ContactCreate` schema (see REST API documentation)

**Response Message (Success):**
```json
{
  "request_id": "req-create",
  "action": "create_contact",
  "status": "success",
  "data": {
    "uuid": "abc123-def456-ghi789",
    "first_name": "John",
    "last_name": "Doe",
    "title": "CEO",
    "company": "Acme Corp",
    "email": "john@example.com",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
}
```

### Action: get_titles

Get list of contacts with only id and title field.

**Request Message:**
```json
{
  "action": "get_titles",
  "request_id": "req-titles",
  "data": {
    "search": "technology",
    "distinct": true,
    "limit": 50,
    "offset": 0
  }
}
```

**Request Data Fields:**

- `search` (string, optional): Search term to filter results (case-insensitive)
- `distinct` (boolean, optional): If `true`, returns only distinct title values (default: `false`)
- `limit` (integer, optional): Maximum number of results. If not provided, returns all matching values (unlimited)
- `offset` (integer, optional): Offset for pagination (default: 0)
- All filter parameters from the REST API are supported

**Response Message (Success):**
```json
{
  "request_id": "req-titles",
  "action": "get_titles",
  "status": "success",
  "data": {
    "results": [
      "CEO",
      "CTO",
      "VP Engineering"
    ]
  }
}
```

### Action: get_companies

Get list of contacts with only id and company field.

**Request Message:**
```json
{
  "action": "get_companies",
  "request_id": "req-companies",
  "data": {
    "search": "tech",
    "distinct": true
  }
}
```

**Request Data Fields:**

- Same as `get_titles` action

**Response Message (Success):**
```json
{
  "request_id": "req-companies",
  "action": "get_companies",
  "status": "success",
  "data": {
    "results": [
      "Acme Corp",
      "Tech Inc",
      "Software Solutions"
    ]
  }
}
```

### Action: get_industries

Get list of contacts with only id and industry field.

**Request Message:**
```json
{
  "action": "get_industries",
  "request_id": "req-industries",
  "data": {
    "search": "technology",
    "distinct": true,
    "separated": true
  }
}
```

**Request Data Fields:**

- Same as `get_titles`, plus:
- `separated` (boolean, optional): If `true`, expands comma-separated industries into individual records (default: `false`)

**Response Message (Success):**
```json
{
  "request_id": "req-industries",
  "action": "get_industries",
  "status": "success",
  "data": {
    "results": [
      "Technology",
      "Healthcare",
      "Finance"
    ]
  }
}
```

### Action: get_keywords

Get list of contacts with only id and keywords field. Supports expansion of comma-separated keywords.

**Request Message:**
```json
{
  "action": "get_keywords",
  "request_id": "req-keywords",
  "data": {
    "search": "cloud",
    "separated": true,
    "distinct": true
  }
}
```

**Request Data Fields:**

- Same as `get_industries` action

**Response Message (Success):**
```json
{
  "request_id": "req-keywords",
  "action": "get_keywords",
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

### Action: get_technologies

Get list of contacts with only id and technologies field.

**Request Message:**
```json
{
  "action": "get_technologies",
  "request_id": "req-technologies",
  "data": {
    "search": "python",
    "separated": true,
    "distinct": true
  }
}
```

**Request Data Fields:**

- Same as `get_industries` action

**Response Message (Success):**
```json
{
  "request_id": "req-technologies",
  "action": "get_technologies",
  "status": "success",
  "data": {
    "results": [
      "Python",
      "Django",
      "PostgreSQL"
    ]
  }
}
```

### Action: get_company_addresses

Return address text for related companies, sourced from the `Company.text_search` column.

**Request Message:**
```json
{
  "action": "get_company_addresses",
  "request_id": "req-company-addr",
  "data": {
    "search": "San Francisco",
    "distinct": true
  }
}
```

**Request Data Fields:**

- Same as `get_titles` action

**Response Message (Success):**
```json
{
  "request_id": "req-company-addr",
  "action": "get_company_addresses",
  "status": "success",
  "data": {
    "results": [
      "123 Main St, San Francisco, CA",
      "456 Oak Ave, Denver, CO"
    ]
  }
}
```

### Action: get_contact_addresses

Return person-level address text sourced from the `Contact.text_search` column.

**Request Message:**
```json
{
  "action": "get_contact_addresses",
  "request_id": "req-contact-addr",
  "data": {
    "search": "Austin",
    "distinct": true
  }
}
```

**Request Data Fields:**

- Same as `get_titles` action

**Response Message (Success):**
```json
{
  "request_id": "req-contact-addr",
  "action": "get_contact_addresses",
  "status": "success",
  "data": {
    "results": [
      "789 Market St, San Francisco, CA",
      "456 Sample Ave, Denver, CO"
    ]
  }
}
```

### Action: get_cities

Get list of contact cities.

**Request Message:**
```json
{
  "action": "get_cities",
  "request_id": "req-cities",
  "data": {
    "search": "San",
    "distinct": true
  }
}
```

**Request Data Fields:**

- Same as `get_titles` action

**Response Message (Success):**
```json
{
  "request_id": "req-cities",
  "action": "get_cities",
  "status": "success",
  "data": {
    "results": [
      "San Francisco",
      "New York",
      "Austin"
    ]
  }
}
```

### Action: get_states

Get list of contact states.

**Request Message:**
```json
{
  "action": "get_states",
  "request_id": "req-states",
  "data": {
    "distinct": true
  }
}
```

**Request Data Fields:**

- Same as `get_titles` action

**Response Message (Success):**
```json
{
  "request_id": "req-states",
  "action": "get_states",
  "status": "success",
  "data": {
    "results": [
      "CA",
      "NY",
      "TX"
    ]
  }
}
```

### Action: get_countries

Get list of contact countries.

**Request Message:**
```json
{
  "action": "get_countries",
  "request_id": "req-countries",
  "data": {
    "distinct": true
  }
}
```

**Request Data Fields:**

- Same as `get_titles` action

**Response Message (Success):**
```json
{
  "request_id": "req-countries",
  "action": "get_countries",
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

### Action: get_company_cities

Get list of company cities.

**Request Message:**
```json
{
  "action": "get_company_cities",
  "request_id": "req-company-cities",
  "data": {
    "distinct": true
  }
}
```

**Request Data Fields:**

- Same as `get_titles` action

**Response Message (Success):**
```json
{
  "request_id": "req-company-cities",
  "action": "get_company_cities",
  "status": "success",
  "data": {
    "results": [
      "San Francisco",
      "New York",
      "Austin"
    ]
  }
}
```

### Action: get_company_states

Get list of company states.

**Request Message:**
```json
{
  "action": "get_company_states",
  "request_id": "req-company-states",
  "data": {
    "distinct": true
  }
}
```

**Request Data Fields:**

- Same as `get_titles` action

**Response Message (Success):**
```json
{
  "request_id": "req-company-states",
  "action": "get_company_states",
  "status": "success",
  "data": {
    "results": [
      "CA",
      "NY",
      "TX"
    ]
  }
}
```

### Action: get_company_countries

Get list of company countries.

**Request Message:**
```json
{
  "action": "get_company_countries",
  "request_id": "req-company-countries",
  "data": {
    "distinct": true
  }
}
```

**Request Data Fields:**

- Same as `get_titles` action

**Response Message (Success):**
```json
{
  "request_id": "req-company-countries",
  "action": "get_company_countries",
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

### Action: get_import_info

Get information about the import endpoint.

**Request Message:**
```json
{
  "action": "get_import_info",
  "request_id": "req-import-info",
  "data": {}
}
```

**Response Message (Success):**
```json
{
  "request_id": "req-import-info",
  "action": "get_import_info",
  "status": "success",
  "data": {
    "message": "Upload a CSV file via POST to /api/v1/contacts/import/ to start a background import job."
  }
}
```

### Action: upload_contacts_csv

Upload a CSV file to import contacts. The file is processed asynchronously via Celery. Requires admin authentication.

**Request Message:**
```json
{
  "action": "upload_contacts_csv",
  "request_id": "req-upload",
  "data": {
    "file_name": "contacts.csv",
    "file_data": "base64_encoded_file_content_here"
  }
}
```

**Request Data Fields:**

- `file_name` (string, required): Name of the CSV file
- `file_data` (string, required): Base64-encoded file content

**Response Message (Success):**
```json
{
  "request_id": "req-upload",
  "action": "upload_contacts_csv",
  "status": "success",
  "data": {
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
}
```

### Action: get_import_status

Get the status and details of an import job.

**Request Message:**
```json
{
  "action": "get_import_status",
  "request_id": "req-import-status",
  "data": {
    "job_id": "abc123def456",
    "include_errors": false
  }
}
```

**Request Data Fields:**

- `job_id` (string, required): Import job ID (UUID)
- `include_errors` (boolean, optional): If `true`, includes error records in the response (default: `false`)

**Response Message (Success):**
```json
{
  "request_id": "req-import-status",
  "action": "get_import_status",
  "status": "success",
  "data": {
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
}
```

**Status Values:**

- `pending`: Job is queued but not started
- `processing`: Job is currently processing
- `completed`: Job finished successfully
- `failed`: Job failed with an error

### Action: get_import_errors

Download error records for an import job.

**Request Message:**
```json
{
  "action": "get_import_errors",
  "request_id": "req-import-errors",
  "data": {
    "job_id": "abc123def456"
  }
}
```

**Request Data Fields:**

- `job_id` (string, required): Import job ID (UUID)

**Response Message (Success):**
```json
{
  "request_id": "req-import-errors",
  "action": "get_import_errors",
  "status": "success",
  "data": {
    "errors": [
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
  }
}
```

## WebSocket Client Examples

### JavaScript Example

```javascript
const token = "your_jwt_token_here";

// Connect to unified WebSocket endpoint
const ws = new WebSocket(`ws://54.87.173.234:8000/api/v1/contacts/ws?token=${token}`);

ws.onopen = () => {
  console.log("WebSocket connected");
  
  // Send list_contacts request
  ws.send(JSON.stringify({
    action: "list_contacts",
    request_id: "req-1",
    data: {
      first_name: "John",
      country: "United States",
      limit: 10
    }
  }));
  
  // Send get_contact request
  setTimeout(() => {
    ws.send(JSON.stringify({
      action: "get_contact",
      request_id: "req-2",
      data: {
        contact_uuid: "abc123-def456-ghi789"
      }
    }));
  }, 1000);
  
  // Send count_contacts request
  setTimeout(() => {
    ws.send(JSON.stringify({
      action: "count_contacts",
      request_id: "req-3",
      data: {
        country: "United States"
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

async def contacts_websocket_client():
    token = "your_jwt_token_here"
    uri = f"ws://54.87.173.234:8000/api/v1/contacts/ws?token={token}"
    
    async with websockets.connect(uri) as websocket:
        # Send list_contacts request
        request = {
            "action": "list_contacts",
            "request_id": f"req-{int(asyncio.get_event_loop().time())}",
            "data": {
                "first_name": "John",
                "country": "United States",
                "limit": 10
            }
        }
        
        await websocket.send(json.dumps(request))
        
        # Receive response
        response = await websocket.recv()
        data = json.loads(response)
        
        if data["status"] == "success":
            print("List contacts result:", data["data"])
        else:
            print("Error:", data["error"])
        
        # Send another request on the same connection
        get_request = {
            "action": "get_contact",
            "request_id": f"req-{int(asyncio.get_event_loop().time()) + 1}",
            "data": {
                "contact_uuid": "abc123-def456-ghi789"
            }
        }
        
        await websocket.send(json.dumps(get_request))
        
        # Receive second response
        response2 = await websocket.recv()
        data2 = json.loads(response2)
        
        if data2["status"] == "success":
            print("Get contact result:", data2["data"])

# Run the client
asyncio.run(contacts_websocket_client())
```

## Connection Behavior

- **Persistent Connections**: Clients maintain a single WebSocket connection and can send multiple requests with different actions
- **Request Tracking**: Each request includes a `request_id` that is echoed in the response for correlation
- **Error Handling**: Errors are returned as JSON messages with `status: "error"` and error details
- **Connection Lifecycle**: Connections are automatically cleaned up when clients disconnect
- **Concurrent Requests**: Multiple requests can be sent on the same connection, but responses may arrive in any order (use `request_id` to match responses)
- **Action Routing**: The unified endpoint automatically routes messages to the appropriate handler based on the `action` field

## Filter Parameters

All filter parameters from the REST API are supported. See the [REST API documentation](../api/contacts.md) for complete filter details. Key filter categories include:

- **Text Filters**: `first_name`, `last_name`, `title`, `company`, `email`, `city`, `state`, `country`, etc.
- **Numeric Filters**: `employees_min`, `employees_max`, `annual_revenue_min`, `annual_revenue_max`, etc.
- **Exclusion Filters**: `exclude_titles`, `exclude_seniorities`, `exclude_departments`, etc. (can be arrays or comma-separated strings)
- **Date Range Filters**: `created_at_after`, `created_at_before`, `updated_at_after`, `updated_at_before`
- **Search and Ordering**: `search` (full-text search), `ordering` (comma-separated fields)

## WebSocket vs REST API

**Use WebSocket when:**

- You need real-time bidirectional communication
- You want to send multiple requests without re-establishing connections
- You're building a real-time application or dashboard
- You need to handle multiple operations in a single session

**Use REST API when:**

- You need simple request/response patterns
- You're making one-off requests
- You prefer stateless HTTP semantics
- You're integrating with systems that don't support WebSockets

## Error Handling

WebSocket errors are returned in the standard error response format:

```json
{
  "request_id": "req-123",
  "action": "list_contacts",
  "status": "error",
  "data": null,
  "error": {
    "message": "Missing required field: contact_uuid",
    "code": "missing_field"
  }
}
```

Common error codes:

- `missing_field` - Required field is missing from request data
- `invalid_json` - Request message is not valid JSON
- `validation_error` - Request data validation failed
- `unknown_action` - Action is not recognized
- `list_error` - Error during contact listing
- `get_error` - Error during contact retrieval
- `count_error` - Error during contact count
- `uuids_error` - Error during UUID retrieval
- `create_error` - Error during contact creation
- `field_error` - Error during field value retrieval
- `admin_required` - Admin access required for this action
- `invalid_write_key` - Invalid write key provided
- `write_key_not_configured` - Write key is not configured
- `upload_error` - Error during CSV upload
- `import_status_error` - Error during import status retrieval
- `import_errors_error` - Error during import errors retrieval
- `not_found` - Resource not found

## Notes

- All datetime fields in responses are serialized as ISO format strings (e.g., `"2024-01-15T10:30:00Z"`)
- The unified endpoint supports all 22 actions on a single connection
- Request IDs should be unique per connection to properly track responses
- The connection remains open until explicitly closed by the client or server
- For CSV uploads, files must be base64-encoded in the `file_data` field
- Import jobs are processed asynchronously. Check job status using the `get_import_status` action
- All text searches are case-insensitive
- Pagination limits are enforced (max 100 items per page when limit is not explicitly set)
- Field-specific endpoints support `distinct` mode to return only unique values
- Array fields (industries, keywords, technologies) support `separated` mode to expand comma-separated values
