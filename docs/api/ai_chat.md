# AI Chat API Documentation

Complete API documentation for AI chat conversation endpoints, including listing, creating, retrieving, updating, and deleting chat conversations.

## Base URL

```txt
http://localhost:8000
```

For production, use:

```txt
http://107.21.188.21:8000
```

## Authentication

All AI chat endpoints require JWT authentication via the `Authorization` header:

```txt
Authorization: Bearer <access_token>
```

Tokens are obtained through the login or register endpoints.

---

## CORS Testing

All endpoints support CORS (Cross-Origin Resource Sharing) for browser-based requests. For testing CORS headers, you can include an optional `Origin` header in your requests:

**Optional Header:**

- `Origin: http://localhost:3000` (or your frontend origin)

**Expected CORS Response Headers:**

- `Access-Control-Allow-Origin: http://localhost:3000` (matches the Origin header)
- `Access-Control-Allow-Credentials: true`
- `Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS, PATCH`
- `Access-Control-Allow-Headers: *`
- `Access-Control-Max-Age: 3600`

**Note:** The Origin header is optional and only needed when testing CORS behavior. The API automatically handles CORS preflight (OPTIONS) requests.

---

## AI Chat Endpoints

### GET /api/v2/ai-chats/ - List User's Chat History

Get a list of all AI chat conversations for the current user with pagination.

**Headers:**

- `Authorization: Bearer <access_token>` (required)

**Query Parameters:**

- `limit` (integer, optional): Number of results per page (default: 25, max: 100)
- `offset` (integer, optional): Offset for pagination (default: 0)
- `ordering` (string, optional): Order by field. Prepend `-` for descending. Valid fields: `created_at`, `updated_at`, `-created_at`, `-updated_at` (default: `-created_at`)

**Response:**

**Success (200 OK):**

```json
{
  "count": 10,
  "next": "http://107.21.188.21:8000/api/v2/ai-chats/?limit=25&offset=25",
  "previous": null,
  "results": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "title": "Who are my most recent leads?",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:35:00Z"
    },
    {
      "id": "223e4567-e89b-12d3-a456-426614174001",
      "title": "Find contacts in California...",
      "created_at": "2024-01-14T15:20:00Z",
      "updated_at": "2024-01-14T15:25:00Z"
    }
  ]
}
```

**Error (401 Unauthorized):**

```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Error (401 Unauthorized) - Invalid Token:**

```json
{
  "detail": "Given token not valid for any token type"
}
```

**Status Codes:**

- `200 OK`: Chat history retrieved successfully
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: An error occurred while processing the request

**Example Requests:**

```txt
GET /api/v2/ai-chats/
GET /api/v2/ai-chats/?limit=50&offset=0
GET /api/v2/ai-chats/?ordering=-updated_at&limit=10
```

**Notes:**

- Only returns chats owned by the authenticated user
- Default ordering is by `-created_at` (newest first)
- The response includes a count of total chats
- Pagination uses limit-offset pagination

---

### POST /api/v2/ai-chats/ - Create New Chat

Create a new AI chat conversation.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Request Body:**

```json
{
  "title": "Who are my most recent leads?",
  "messages": [
    {
      "sender": "ai",
      "text": "Hello! I'm NexusAI, your smart CRM assistant. How can I help you find contacts today?"
    },
    {
      "sender": "user",
      "text": "Who are my most recent leads?"
    },
    {
      "sender": "ai",
      "text": "Here are your most recent leads:",
      "contacts": []
    }
  ]
}
```

**Field Requirements:**

- `title` (string, optional): Chat title (max 255 characters, default: empty string)
- `messages` (array, optional): List of messages (default: empty list)

**Message Format:**

Each message in the `messages` array must be an object with:

- `sender` (string, required): Must be either `"user"` or `"ai"`
- `text` (string, required): Message text content
- `contacts` (array, optional): Array of contact objects when AI returns search results

**Response:**

**Success (201 Created):**

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": "223e4567-e89b-12d3-a456-426614174001",
  "title": "Who are my most recent leads?",
  "messages": [
    {
      "sender": "ai",
      "text": "Hello! I'm NexusAI, your smart CRM assistant. How can I help you find contacts today?"
    },
    {
      "sender": "user",
      "text": "Who are my most recent leads?"
    },
    {
      "sender": "ai",
      "text": "Here are your most recent leads:",
      "contacts": []
    }
  ],
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": null
}
```

**Error (400 Bad Request) - Invalid Message Format:**

```json
{
  "messages": ["Messages must be a list"]
}
```

Or:

```json
{
  "messages": ["Each message must be a dictionary"]
}
```

Or:

```json
{
  "messages": ["Each message must have 'sender' and 'text' fields"]
}
```

Or:

```json
{
  "messages": ["Sender must be 'user' or 'ai'"]
}
```

**Error (400 Bad Request) - Invalid Title:**

```json
{
  "title": ["Ensure this field has no more than 255 characters."]
}
```

**Error (401 Unauthorized):**

```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Status Codes:**

- `201 Created`: Chat created successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: An error occurred while processing the request

**Notes:**

- The user is automatically set from the authenticated user's token
- The chat ID is a UUID generated automatically
- Created and updated timestamps are set automatically
- Messages can be empty initially and added later via update

---

### GET /api/v2/ai-chats/{id}/ - Get Specific Chat

Get detailed information about a specific AI chat conversation, including all messages.

**Headers:**

- `Authorization: Bearer <access_token>` (required)

**Path Parameters:**

- `id` (string, UUID): Chat ID

**Query Parameters:**

- None

**Response:**

**Success (200 OK):**

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": "223e4567-e89b-12d3-a456-426614174001",
  "title": "Who are my most recent leads?",
  "messages": [
    {
      "sender": "ai",
      "text": "Hello! I'm NexusAI, your smart CRM assistant. How can I help you find contacts today?"
    },
    {
      "sender": "user",
      "text": "Who are my most recent leads?"
    },
    {
      "sender": "ai",
      "text": "Here are your most recent leads:",
      "contacts": [
        {
          "id": 1,
          "first_name": "John",
          "last_name": "Doe",
          "company": "Acme Corp",
          "email": "john@acme.com"
        }
      ]
    }
  ],
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:35:00Z"
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
  "detail": "You do not have permission to access this chat."
}
```

**Error (404 Not Found):**

```json
{
  "detail": "Not found."
}
```

**Status Codes:**

- `200 OK`: Chat retrieved successfully
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: User does not own this chat
- `404 Not Found`: Chat not found
- `500 Internal Server Error`: An error occurred while processing the request

**Notes:**

- Only the chat owner can access their chats
- The `user_id` in the response matches the authenticated user
- Messages are returned in the order they were added
- The `contacts` field in messages is optional and may contain contact search results

---

### PUT /api/v2/ai-chats/{id}/ - Update Chat

Update an existing AI chat conversation (typically to add new messages or update the title). All fields are optional - only provided fields will be updated.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Path Parameters:**

- `id` (string, UUID): Chat ID

**Request Body:**

```json
{
  "title": "Updated title (optional)",
  "messages": [
    {
      "sender": "ai",
      "text": "Hello! I'm NexusAI..."
    },
    {
      "sender": "user",
      "text": "Who are my most recent leads?"
    },
    {
      "sender": "ai",
      "text": "Here are your most recent leads:",
      "contacts": []
    },
    {
      "sender": "user",
      "text": "Show me more details"
    }
  ]
}
```

**Field Requirements:**

All fields are optional:

- `title` (string, optional): Chat title (max 255 characters)
- `messages` (array, optional): Complete list of messages (replaces existing messages)

**Message Format:**

Each message in the `messages` array must be an object with:

- `sender` (string, required): Must be either `"user"` or `"ai"`
- `text` (string, required): Message text content
- `contacts` (array, optional): Array of contact objects when AI returns search results

**Response:**

**Success (200 OK):**

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": "223e4567-e89b-12d3-a456-426614174001",
  "title": "Updated title",
  "messages": [
    {
      "sender": "ai",
      "text": "Hello! I'm NexusAI..."
    },
    {
      "sender": "user",
      "text": "Who are my most recent leads?"
    },
    {
      "sender": "ai",
      "text": "Here are your most recent leads:",
      "contacts": []
    },
    {
      "sender": "user",
      "text": "Show me more details"
    }
  ],
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:40:00Z"
}
```

**Error (400 Bad Request) - Invalid Message Format:**

```json
{
  "messages": ["Messages must be a list"]
}
```

Or:

```json
{
  "messages": ["Each message must be a dictionary"]
}
```

Or:

```json
{
  "messages": ["Each message must have 'sender' and 'text' fields"]
}
```

Or:

```json
{
  "messages": ["Sender must be 'user' or 'ai'"]
}
```

**Error (400 Bad Request) - Invalid Data:**

```json
{
  "detail": "Invalid request data"
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
  "detail": "You do not have permission to update this chat."
}
```

**Error (404 Not Found):**

```json
{
  "detail": "Not found."
}
```

**Status Codes:**

- `200 OK`: Chat updated successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: User does not own this chat
- `404 Not Found`: Chat not found
- `500 Internal Server Error`: An error occurred while processing the request

**Notes:**

- This is a partial update (PATCH-like behavior) - only provided fields are updated
- When updating `messages`, the entire messages array should be provided (it replaces the existing messages)
- The `updated_at` timestamp is automatically updated
- Only the chat owner can update their chats
- The `user_id` cannot be changed

---

### DELETE /api/v2/ai-chats/{id}/ - Delete Chat

Delete an AI chat conversation.

**Headers:**

- `Authorization: Bearer <access_token>` (required)

**Path Parameters:**

- `id` (string, UUID): Chat ID

**Query Parameters:**

- None

**Response:**

**Success (204 No Content):**

- Empty response body

**Error (401 Unauthorized):**

```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Error (403 Forbidden):**

```json
{
  "detail": "You do not have permission to delete this chat."
}
```

**Error (404 Not Found):**

```json
{
  "detail": "Not found."
}
```

**Status Codes:**

- `204 No Content`: Chat deleted successfully
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: User does not own this chat
- `404 Not Found`: Chat not found
- `500 Internal Server Error`: An error occurred while processing the request

**Notes:**

- Only the chat owner can delete their chats
- Deletion is permanent and cannot be undone
- The response has no body (204 No Content)

---

## Message Format

Messages in chat endpoints follow this structure:

```json
{
  "sender": "user" | "ai",
  "text": "Message text",
  "contacts": [] // Optional array of contact objects when AI returns search results
}
```

### Message Fields

- `sender` (string, required): Must be either `"user"` or `"ai"`
- `text` (string, required): The message content
- `contacts` (array, optional): Array of contact objects. Typically included when the AI responds with contact search results. Each contact object contains contact details like `id`, `first_name`, `last_name`, `company`, `email`, etc.

### Contact Object Fields (in messages)

When a message includes a `contacts` array, each contact object may contain the following fields (all optional):

- `id` (integer, optional): Contact ID
- `first_name` (string, optional): Contact's first name
- `last_name` (string, optional): Contact's last name
- `title` (string, optional): Contact's job title
- `company` (string, optional): Contact's company name
- `email` (string, optional): Contact's email address
- `city` (string, optional): Contact's city
- `state` (string, optional): Contact's state/province
- `country` (string, optional): Contact's country

**Note:** The contact object uses `extra="allow"` in its schema, meaning it may contain additional fields beyond those listed above.

### Example Message with Contacts

```json
{
  "sender": "ai",
  "text": "Here are the contacts matching your search:",
  "contacts": [
    {
      "id": 1,
      "first_name": "John",
      "last_name": "Doe",
      "title": "CEO",
      "company": "Acme Corp",
      "email": "john@acme.com",
      "city": "San Francisco",
      "state": "CA",
      "country": "United States"
    },
    {
      "id": 2,
      "first_name": "Jane",
      "last_name": "Smith",
      "title": "CTO",
      "company": "Tech Inc",
      "email": "jane@techinc.com",
      "city": "New York",
      "state": "NY",
      "country": "United States"
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

Or field-specific errors:

```json
{
  "field_name": ["Error message for this field"]
}
```

### 401 Unauthorized

```json
{
  "detail": "Authentication credentials were not provided."
}
```

Or:

```json
{
  "detail": "Given token not valid for any token type"
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
  "detail": "An error occurred while processing the request."
}
```

---

## Notes

- All timestamps are in ISO 8601 format (UTC): `YYYY-MM-DDTHH:MM:SSZ`
- Chat IDs are UUIDs (Universally Unique Identifiers)
- All chat operations verify that the user owns the chat before allowing access
- The `user_id` in chat responses should match the authenticated user's ID from the JWT token
- Messages are stored as a JSON array in the database
- The `title` field can be empty (default: empty string)
- Pagination uses limit-offset pagination with a default limit of 25 and maximum of 100
- The `contacts` field in messages is optional and is typically used when the AI returns search results
- When updating messages, provide the complete messages array (it replaces existing messages, not appends)

## Example Workflow

### 1. Create a new chat

```bash
POST /api/v2/ai-chats/
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "Find contacts in California",
  "messages": [
    {
      "sender": "ai",
      "text": "Hello! How can I help you?"
    },
    {
      "sender": "user",
      "text": "Find contacts in California"
    }
  ]
}
```

### 2. Get the chat details

```bash
GET /api/v2/ai-chats/{chat_id}/
Authorization: Bearer <token>
```

### 3. Update the chat with AI response

```bash
PUT /api/v2/ai-chats/{chat_id}/
Authorization: Bearer <token>
Content-Type: application/json

{
  "messages": [
    {
      "sender": "ai",
      "text": "Hello! How can I help you?"
    },
    {
      "sender": "user",
      "text": "Find contacts in California"
    },
    {
      "sender": "ai",
      "text": "Here are contacts in California:",
      "contacts": [...]
    }
  ]
}
```

### 4. List all chats

```bash
GET /api/v2/ai-chats/?limit=25&offset=0
Authorization: Bearer <token>
```

### 5. Delete a chat

```bash
DELETE /api/v2/ai-chats/{chat_id}/
Authorization: Bearer <token>
```
