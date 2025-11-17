# Apollo WebSocket API Documentation

Complete WebSocket API documentation for Apollo.io URL analysis endpoints, providing real-time bidirectional communication for Apollo operations.

## Base URL

For production, use:

```txt
ws://54.87.173.234:8000
```

## Authentication

WebSocket connections are authenticated using JWT tokens passed as query parameters during the WebSocket handshake:

```
ws://host:port/api/v2/apollo/ws?token=<jwt_token>
```

**Important:** The token must be a valid access token obtained from the login or register endpoints.

## Unified WebSocket Endpoint

All Apollo WebSocket operations are handled through a single unified endpoint:

### WS /api/v2/apollo/ws - Unified Apollo WebSocket Endpoint

This endpoint handles all Apollo operations over a single persistent WebSocket connection. You can send multiple requests with different actions on the same connection.

**Connection URL:**
```
ws://host:port/api/v2/apollo/ws?token=<jwt_token>
```

**Supported Actions:**
- `analyze` - Analyze Apollo.io URLs
- `search_contacts` - Search contacts using Apollo URL parameters
- `count_contacts` - Count contacts matching Apollo URL parameters
- `get_uuids` - Get contact UUIDs matching Apollo URL parameters

## Message Format

All WebSocket messages use JSON format with the following structure:

**Request Message:**
```json
{
  "action": "analyze",
  "request_id": "req-123",
  "data": {
    "url": "https://app.apollo.io/#/people?..."
  }
}
```

**Response Message (Success):**
```json
{
  "request_id": "req-123",
  "action": "analyze",
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
  "action": "analyze",
  "status": "error",
  "data": null,
  "error": {
    "message": "Error description",
    "code": "error_code"
  }
}
```

## WebSocket Actions

### Action: analyze

Analyze an Apollo.io URL and return structured parameter breakdown.

**Request Message:**
```json
{
  "action": "analyze",
  "request_id": "req-123",
  "data": {
    "url": "https://app.apollo.io/#/people?contactEmailStatusV2[]=verified&personLocations[]=california&personTitles[]=CEO&organizationNumEmployeesRanges[]=11,50&page=1&sortByField=recommendations_score&sortAscending=false"
  }
}
```

**Request Data Fields:**
- `url` (string, required): Apollo.io URL to analyze. Must be from the `apollo.io` domain.

**Response Message (Success):**
```json
{
  "request_id": "req-123",
  "action": "analyze",
  "status": "success",
  "data": {
    "url": "https://app.apollo.io/#/people?...",
    "url_structure": {
      "base_url": "https://app.apollo.io",
      "hash_path": "/people",
      "query_string": "...",
      "has_query_params": true
    },
    "categories": [
      {
        "name": "Person Filters",
        "parameters": [
          {
            "name": "personTitles[]",
            "values": ["CEO"],
            "description": "Job titles to include",
            "category": "Person Filters"
          }
        ],
        "total_parameters": 1
      }
    ],
    "statistics": {
      "total_parameters": 7,
      "total_parameter_values": 7,
      "categories_used": 5,
      "categories": ["Pagination", "Sorting", "Person Filters", "Email Filters", "Organization Filters"]
    },
    "raw_parameters": {
      "contactEmailStatusV2[]": ["verified"],
      "personLocations[]": ["california"],
      "personTitles[]": ["CEO"],
      "organizationNumEmployeesRanges[]": ["11,50"],
      "page": ["1"],
      "sortByField": ["recommendations_score"],
      "sortAscending": ["false"]
    }
  }
}
```

The response data structure matches the REST API response format. Industry Tag IDs are automatically converted to readable industry names.

### Action: search_contacts

Search contacts using Apollo.io URL parameters.

**Request Message:**
```json
{
  "action": "search_contacts",
  "request_id": "req-456",
  "data": {
    "url": "https://app.apollo.io/#/people?personTitles[]=CEO&personLocations[]=california",
    "limit": 50,
    "offset": 0,
    "view": "simple",
    "include_company_name": "Acme Corp",
    "exclude_company_name": ["Test Inc"],
    "include_domain_list": ["example.com"],
    "exclude_domain_list": ["test.com"]
  }
}
```

**Request Data Fields:**
- `url` (string, required): Apollo.io URL to convert
- `limit` (integer, optional): Maximum number of results per page. If not provided, returns all matching contacts (no pagination limit).
- `offset` (integer, optional): Starting offset for results (default: 0)
- `cursor` (string, optional): Opaque cursor token for pagination
- `view` (string, optional): When "simple", returns ContactSimpleItem, otherwise ContactListItem
- `include_company_name` (string, optional): Include contacts whose company name matches (case-insensitive substring match)
- `exclude_company_name` (array, optional): Exclude contacts whose company name matches any provided value (case-insensitive)
- `include_domain_list` (array, optional): Include contacts whose company website domain matches any provided domain (case-insensitive)
- `exclude_domain_list` (array, optional): Exclude contacts whose company website domain matches any provided domain (case-insensitive)

**Response Message (Success):**
```json
{
  "request_id": "req-456",
  "action": "search_contacts",
  "status": "success",
  "data": {
    "next": "cursor_token_here",
    "previous": null,
    "results": [
      {
        "uuid": "398cce44-233d-5f7c-aea1-e4a6a79df10c",
        "first_name": "John",
        "last_name": "Doe",
        "title": "CEO",
        "company": "Tech Corp",
        "email": "john@techcorp.com",
        "email_status": "verified",
        "created_at": "2024-01-15T10:30:00",
        "updated_at": "2024-01-15T10:30:00"
      }
    ],
    "apollo_url": "https://app.apollo.io/#/people?...",
    "mapping_summary": {
      "total_apollo_parameters": 5,
      "mapped_parameters": 4,
      "unmapped_parameters": 1,
      "mapped_parameter_names": ["personTitles[]", "personLocations[]"],
      "unmapped_parameter_names": ["sortByField"]
    },
    "unmapped_categories": [
      {
        "name": "Sorting",
        "total_parameters": 1,
        "parameters": [
          {
            "name": "sortByField",
            "values": ["recommendations_score"],
            "category": "Sorting",
            "reason": "Unknown parameter (no mapping defined)"
          }
        ]
      }
    ]
  }
}
```

**Note:** The response includes the same mapping metadata as the REST API, showing which Apollo parameters were successfully mapped and which were not.

### Action: count_contacts

Count contacts matching Apollo.io URL parameters.

**Request Message:**
```json
{
  "action": "count_contacts",
  "request_id": "req-789",
  "data": {
    "url": "https://app.apollo.io/#/people?personTitles[]=CEO",
    "include_company_name": "Acme Corp",
    "exclude_company_name": ["Test Inc"],
    "include_domain_list": ["example.com"],
    "exclude_domain_list": ["test.com"]
  }
}
```

**Request Data Fields:**
- `url` (string, required): Apollo.io URL to convert
- `include_company_name` (string, optional): Include contacts whose company name matches (case-insensitive substring match)
- `exclude_company_name` (array, optional): Exclude contacts whose company name matches any provided value (case-insensitive)
- `include_domain_list` (array, optional): Include contacts whose company website domain matches any provided domain (case-insensitive)
- `exclude_domain_list` (array, optional): Exclude contacts whose company website domain matches any provided domain (case-insensitive)

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

### Action: get_uuids

Get contact UUIDs matching Apollo.io URL parameters.

**Request Message:**
```json
{
  "action": "get_uuids",
  "request_id": "req-abc",
  "data": {
    "url": "https://app.apollo.io/#/people?personTitles[]=CEO",
    "limit": 100,
    "include_company_name": "Acme Corp",
    "exclude_company_name": ["Test Inc"],
    "include_domain_list": ["example.com"],
    "exclude_domain_list": ["test.com"]
  }
}
```

**Request Data Fields:**
- `url` (string, required): Apollo.io URL to convert
- `limit` (integer, optional): Limit the number of UUIDs returned. If not provided, returns all matching UUIDs (unlimited).
- `include_company_name` (string, optional): Include contacts whose company name matches (case-insensitive substring match)
- `exclude_company_name` (array, optional): Exclude contacts whose company name matches any provided value (case-insensitive)
- `include_domain_list` (array, optional): Include contacts whose company website domain matches any provided domain (case-insensitive)
- `exclude_domain_list` (array, optional): Exclude contacts whose company website domain matches any provided domain (case-insensitive)

**Response Message (Success):**
```json
{
  "request_id": "req-abc",
  "action": "get_uuids",
  "status": "success",
  "data": {
    "count": 100,
    "uuids": [
      "398cce44-233d-5f7c-aea1-e4a6a79df10c",
      "498cce44-233d-5f7c-aea1-e4a6a79df10d",
      "598cce44-233d-5f7c-aea1-e4a6a79df10e"
    ]
  }
}
```

## WebSocket Client Examples

### JavaScript Example

```javascript
const token = "your_jwt_token_here";

// Connect to unified WebSocket endpoint
const ws = new WebSocket(`ws://54.87.173.234:8000/api/v2/apollo/ws?token=${token}`);

ws.onopen = () => {
  console.log("WebSocket connected");
  
  // Send analyze request
  ws.send(JSON.stringify({
    action: "analyze",
    request_id: "req-1",
    data: {
      url: "https://app.apollo.io/#/people?personTitles[]=CEO&personLocations[]=california"
    }
  }));
  
  // Send search contacts request
  setTimeout(() => {
    ws.send(JSON.stringify({
      action: "search_contacts",
      request_id: "req-2",
      data: {
        url: "https://app.apollo.io/#/people?personTitles[]=CEO",
        limit: 10
      }
    }));
  }, 1000);
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

async def apollo_websocket_client():
    token = "your_jwt_token_here"
    uri = f"ws://54.87.173.234:8000/api/v2/apollo/ws?token={token}"
    
    async with websockets.connect(uri) as websocket:
        # Send analyze request
        request = {
            "action": "analyze",
            "request_id": f"req-{int(asyncio.get_event_loop().time())}",
            "data": {
                "url": "https://app.apollo.io/#/people?personTitles[]=CEO&personLocations[]=california"
            }
        }
        
        await websocket.send(json.dumps(request))
        
        # Receive response
        response = await websocket.recv()
        data = json.loads(response)
        
        if data["status"] == "success":
            print("Analysis result:", data["data"])
        else:
            print("Error:", data["error"])
        
        # Send another request on the same connection
        search_request = {
            "action": "search_contacts",
            "request_id": f"req-{int(asyncio.get_event_loop().time()) + 1}",
            "data": {
                "url": "https://app.apollo.io/#/people?personTitles[]=CEO",
                "limit": 10
            }
        }
        
        await websocket.send(json.dumps(search_request))
        
        # Receive second response
        response2 = await websocket.recv()
        data2 = json.loads(response2)
        
        if data2["status"] == "success":
            print("Search result:", data2["data"])

# Run the client
asyncio.run(apollo_websocket_client())
```

## Connection Behavior

- **Persistent Connections**: Clients maintain a single WebSocket connection and can send multiple requests with different actions
- **Request Tracking**: Each request includes a `request_id` that is echoed in the response for correlation
- **Error Handling**: Errors are returned as JSON messages with `status: "error"` and error details
- **Connection Lifecycle**: Connections are automatically cleaned up when clients disconnect
- **Concurrent Requests**: Multiple requests can be sent on the same connection, but responses may arrive in any order (use `request_id` to match responses)
- **Action Routing**: The unified endpoint automatically routes messages to the appropriate handler based on the `action` field

## Parameter Mappings

The WebSocket endpoints use the same parameter mappings as the REST API. See the [REST API documentation](../api/apollo.md) for complete mapping details.

Key mappings include:
- `personTitles[]` → `title` (with title normalization)
- `personLocations[]` → `contact_location`
- `organizationNumEmployeesRanges[]` → `employees_min`, `employees_max`
- `contactEmailStatusV2[]` → `email_status`
- `organizationIndustryTagIds[]` → `industries` (Tag IDs converted to industry names)
- And many more...

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
  "action": "search_contacts",
  "status": "error",
  "data": null,
  "error": {
    "message": "Missing required field: url",
    "code": "missing_field"
  }
}
```

Common error codes:
- `missing_field` - Required field is missing from request data
- `invalid_json` - Request message is not valid JSON
- `validation_error` - Request data validation failed
- `unknown_action` - Action is not recognized
- `analysis_error` - Error during URL analysis
- `search_error` - Error during contact search
- `count_error` - Error during contact count
- `uuids_error` - Error during UUID retrieval

## Notes

- All datetime fields in responses are serialized as ISO format strings (e.g., `"2024-01-15T10:30:00"`)
- Industry Tag IDs are automatically converted to readable industry names in responses
- The unified endpoint supports all four actions on a single connection
- Request IDs should be unique per connection to properly track responses
- The connection remains open until explicitly closed by the client or server

