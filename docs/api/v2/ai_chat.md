# AI Chat API Documentation

Complete API documentation for AI chat conversation endpoints, including listing, creating, retrieving, updating, and deleting chat conversations.

**Related Documentation:**

- [User API](./user.md) - For authentication endpoints
- [Contacts API](./contacts.md) - For contact search functionality used in chat responses

## Table of Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [CORS Testing](#cors-testing)
- [AI Chat Endpoints](#ai-chat-endpoints)
  - [GET /api/v2/ai-chats/](#get-apiv2ai-chats---list-users-chat-history)
  - [POST /api/v2/ai-chats/](#post-apiv2ai-chats---create-new-chat)
  - [GET /api/v2/ai-chats/{chat_id}/](#get-apiv2ai-chatschat_id---get-specific-chat)
  - [PUT /api/v2/ai-chats/{chat_id}/](#put-apiv2ai-chatschat_id---update-chat)
  - [DELETE /api/v2/ai-chats/{chat_id}/](#delete-apiv2ai-chatschat_id---delete-chat)
  - [POST /api/v2/ai-chats/{chat_id}/message](#post-apiv2ai-chatschat_idmessage---send-message)
  - [POST /api/v2/ai-chats/{chat_id}/message/stream](#post-apiv2ai-chatschat_idmessagestream---stream-message)
  - [WebSocket /api/v2/ai-chats/ws/{chat_id}](#websocket-apiv2ai-chatswschat_id---realtime-chat)
- [Message Format](#message-format)
- [Rate Limiting](#rate-limiting)
- [Error Responses](#error-responses)
- [Notes](#notes)
- [Example Workflow](#example-workflow)

---

## Base URL

For production, use:

```txt
http://34.229.94.175:8000
```

**API Version:** All AI chat endpoints are under `/api/v2/ai-chats/`

## Authentication

All AI chat endpoints require JWT authentication via the `Authorization` header:

```txt
Authorization: Bearer <access_token>
```

Tokens are obtained through the login or register endpoints.

## Role-Based Access Control

All AI chat endpoints are accessible to all authenticated users regardless of role:

- **Free Users (`FreeUser`)**: ✅ Full access to all AI chat endpoints
- **Pro Users (`ProUser`)**: ✅ Full access to all AI chat endpoints
- **Admin (`Admin`)**: ✅ Full access to all AI chat endpoints
- **Super Admin (`SuperAdmin`)**: ✅ Full access to all AI chat endpoints

**Note:** There are no role-based restrictions on AI chat functionality. All authenticated users can create, read, update, and delete their own chat conversations.

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

- `limit` (integer, optional): Number of results per page (default: 25, max: 100, min: 1)
- `offset` (integer, optional): Offset for pagination (default: 0, min: 0)
- `ordering` (string, optional): Order by field. Prepend `-` for descending. Valid fields: `created_at`, `updated_at`, `-created_at`, `-updated_at` (default: `-created_at`)
- Filter parameters (optional): All query parameters from `AIChatFilterParams` are supported:
  - `title` (string, optional): Case-insensitive substring match against chat title
  - `search` (string, optional): General-purpose search term applied across chat text columns
  - `created_at_after` (datetime, optional): Filter chats created after the provided ISO timestamp (inclusive)
  - `created_at_before` (datetime, optional): Filter chats created before the provided ISO timestamp (inclusive)
  - `page` (integer, optional): Page number for pagination (used with page_size)
  - `page_size` (integer, optional): Number of results per page

**Response:**

**Success (200 OK):**

```json
{
  "count": 10,
  "next": "http://34.229.94.175:8000/api/v2/ai-chats/?limit=25&offset=25",
  "previous": null,
  "results": [
    {
      "uuid": "123e4567-e89b-12d3-a456-426614174000",
      "title": "Who are my most recent leads?",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:35:00Z"
    },
    {
      "uuid": "223e4567-e89b-12d3-a456-426614174001",
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
  "uuid": "123e4567-e89b-12d3-a456-426614174000",
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

### GET /api/v2/ai-chats/{chat_id}/ - Get Specific Chat

Get detailed information about a specific AI chat conversation, including all messages.

**Headers:**

- `Authorization: Bearer <access_token>` (required)

**Path Parameters:**

- `chat_id` (string, UUID): Chat ID

**Query Parameters:**

- Filter parameters (optional): All query parameters from `AIChatFilterParams` are supported:
  - `title` (string, optional): Case-insensitive substring match against chat title
  - `search` (string, optional): General-purpose search term applied across chat text columns
  - `created_at_after` (datetime, optional): Filter chats created after the provided ISO timestamp (inclusive)
  - `created_at_before` (datetime, optional): Filter chats created before the provided ISO timestamp (inclusive)
  - `page` (integer, optional): Page number for pagination (used with page_size)
  - `page_size` (integer, optional): Number of results per page
  - `ordering` (string, optional): Order by field. Prepend `-` for descending. Valid: `created_at`, `updated_at`, `-created_at`, `-updated_at`

**Response:**

**Success (200 OK):**

```json
{
  "uuid": "123e4567-e89b-12d3-a456-426614174000",
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
          "uuid": "123e4567-e89b-12d3-a456-426614174000",
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

### PUT /api/v2/ai-chats/{chat_id}/ - Update Chat

Update an existing AI chat conversation (typically to add new messages or update the title). All fields are optional - only provided fields will be updated.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Path Parameters:**

- `chat_id` (string, UUID): Chat ID

**Query Parameters:**

- Filter parameters (optional): All query parameters from `AIChatFilterParams` are supported (same as GET endpoint)

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
  "uuid": "123e4567-e89b-12d3-a456-426614174000",
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

### DELETE /api/v2/ai-chats/{chat_id}/ - Delete Chat

Delete an AI chat conversation.

**Headers:**

- `Authorization: Bearer <access_token>` (required)

**Path Parameters:**

- `chat_id` (string, UUID): Chat ID

**Query Parameters:**

- Filter parameters (optional): All query parameters from `AIChatFilterParams` are supported (same as GET endpoint)

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

### POST /api/v2/ai-chats/{chat_id}/message - Send Message

Send a message in a chat and get AI response. This endpoint adds the user's message to the chat, generates an AI response using Google Gemini, and returns the updated chat with both messages.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Path Parameters:**

- `chat_id` (string, UUID): Chat ID

**Request Body:**

```json
{
  "message": "Who are my most recent leads?",
  "model": "gemini-1.5-flash"
}
```

**Field Requirements:**

- `message` (string, required): User message text (min length: 1)
- `model` (string, optional): Model selection override. Valid values:
  - `gemini-1.5-flash` (default, fast and efficient)
  - `gemini-1.5-pro` (more capable, better reasoning)
  - `gemini-2.0-flash-exp` (experimental flash model)
  - `gemini-2.5-pro` (advanced reasoning)

**Response:**

**Success (200 OK):**

```json
{
  "uuid": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": "223e4567-e89b-12d3-a456-426614174001",
  "title": "Who are my most recent leads?",
  "messages": [
    {
      "sender": "user",
      "text": "Who are my most recent leads?"
    },
    {
      "sender": "ai",
      "text": "Here are your most recent leads: [AI response]"
    }
  ],
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:35:00Z"
}
```

**Error (400 Bad Request):**

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
  "detail": "You do not have permission to send messages in this chat."
}
```

**Error (404 Not Found):**

```json
{
  "detail": "Not found."
}
```

**Error (429 Too Many Requests):**

```json
{
  "detail": "Rate limit exceeded. Maximum 20 requests per 60 seconds."
}
```

**Status Codes:**

- `200 OK`: Message sent and AI response generated successfully
- `400 Bad Request`: Invalid request data (e.g., empty message)
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: User does not own this chat
- `404 Not Found`: Chat not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: AI service error (fallback response provided)

**Notes:**

- The AI response is generated using Google Gemini AI with proper chat session management
- Chat history is maintained across messages for context-aware responses
- If AI service is unavailable, a fallback error message is returned
- Only the chat owner can send messages
- Rate limiting applies: 20 requests per 60 seconds per user
- This is the recommended way to interact with AI chat (instead of manually updating messages)

---

### POST /api/v2/ai-chats/{chat_id}/message/stream - Stream Message

Send a message in a chat and stream AI response using Server-Sent Events (SSE). This endpoint provides real-time streaming of the AI response as it's generated, offering a better user experience for longer responses.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`
- `Accept: text/event-stream` (recommended)

**Path Parameters:**

- `chat_id` (string, UUID): Chat ID

**Request Body:**

```json
{
  "message": "Explain how neural networks work in detail",
  "model": "gemini-1.5-flash"
}
```

**Field Requirements:**

- `message` (string, required): User message text (min length: 1)
- `model` (string, optional): Model selection override (same as Send Message endpoint)

**Response:**

**Success (200 OK) - Server-Sent Events:**

The response is streamed as Server-Sent Events (SSE) with the following format:

```
data: Hello
data:  world
data: !
data: [DONE]
```

Each `data:` line contains a chunk of the AI response. The stream ends with `data: [DONE]`.

**Response Headers:**

- `Content-Type: text/event-stream`
- `Cache-Control: no-cache`
- `Connection: keep-alive`
- `X-Accel-Buffering: no`

**Error Responses:**

Same as Send Message endpoint (400, 401, 403, 404, 429, 500).

**Status Codes:**

- `200 OK`: Streaming started successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: User does not own this chat
- `404 Not Found`: Chat not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: AI service error

**Notes:**

- The response is streamed in real-time as the AI generates it
- Each chunk is sent as a separate SSE event
- The stream ends with `[DONE]` marker
- Chat is updated with the complete response after streaming completes
- Rate limiting applies: 20 requests per 60 seconds per user
- Use this endpoint for better UX when expecting longer responses

**Example Client Code (JavaScript):**

```javascript
const response = await fetch('/api/v2/ai-chats/{chat_id}/message/stream', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    message: 'Explain how neural networks work',
    model: 'gemini-1.5-flash'
  })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const chunk = decoder.decode(value);
  const lines = chunk.split('\n');
  
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = line.slice(6);
      if (data === '[DONE]') {
        console.log('Stream complete');
      } else {
        console.log('Chunk:', data);
        // Append to UI
      }
    }
  }
}
```

---

### WebSocket /api/v2/ai-chats/ws/{chat_id} - Real-time Chat

Establish a WebSocket connection for real-time bidirectional chat with streaming AI responses. This endpoint provides the best user experience for interactive conversations.

**Connection URL:**

```
ws://34.229.94.175:8000/api/v2/ai-chats/ws/{chat_id}?token=<jwt_token>
```

**Authentication:**

- Pass JWT token as query parameter: `?token=<your_jwt_token>`
- Token must be a valid access token from login/register endpoints

**Path Parameters:**

- `chat_id` (string, UUID): Chat ID (must be owned by authenticated user)

**Message Format:**

**Send to Server:**

```json
{
  "message": "Who are my most recent leads?",
  "model": "gemini-1.5-flash"
}
```

- `message` (string, required): User message text
- `model` (string, optional): Model selection override

**Receive from Server:**

1. **Connection Confirmation:**

```json
{
  "type": "connected",
  "chat_id": "123e4567-e89b-12d3-a456-426614174000",
  "message": "Connected to chat"
}
```

1. **Message Acknowledgment:**

```json
{
  "type": "message_received",
  "message": "Processing your message..."
}
```

1. **Streaming Chunks:**

```json
{
  "type": "chunk",
  "data": "Hello"
}
```

1. **Complete Response:**

```json
{
  "type": "complete",
  "data": "Hello! Here are your most recent leads: [full response]"
}
```

1. **Error:**

```json
{
  "type": "error",
  "message": "Error message describing what went wrong"
}
```

**Response Types:**

- `connected`: WebSocket connection established
- `message_received`: User message received and being processed
- `chunk`: Streaming chunk of AI response
- `complete`: Full AI response completed
- `error`: Error occurred during processing

**Status Codes:**

- `101 Switching Protocols`: WebSocket connection established
- `1008 Policy Violation`: Authentication failed or chat access denied

**Notes:**

- WebSocket connection must be authenticated with valid JWT token
- Chat ownership is verified before connection is accepted
- Multiple messages can be sent over the same connection
- Each message triggers a streaming AI response
- Connection automatically closes on error or disconnect
- Rate limiting applies per user (not per connection)

**Example Client Code (JavaScript):**

```javascript
const chatId = '123e4567-e89b-12d3-a456-426614174000';
const token = 'your_jwt_token';
const ws = new WebSocket(`ws://34.229.94.175:8000/api/v2/ai-chats/ws/${chatId}?token=${token}`);

ws.onopen = () => {
  console.log('WebSocket connected');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch (data.type) {
    case 'connected':
      console.log('Connected to chat:', data.chat_id);
      break;
    case 'message_received':
      console.log('Message received, processing...');
      break;
    case 'chunk':
      // Append chunk to UI
      appendToChat(data.data);
      break;
    case 'complete':
      console.log('Response complete:', data.data);
      break;
    case 'error':
      console.error('Error:', data.message);
      break;
  }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('WebSocket disconnected');
};

// Send a message
function sendMessage(message, model = null) {
  const payload = { message };
  if (model) payload.model = model;
  ws.send(JSON.stringify(payload));
}
```

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

- `uuid` (string, optional): Contact UUID
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
      "uuid": "123e4567-e89b-12d3-a456-426614174000",
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
      "uuid": "223e4567-e89b-12d3-a456-426614174001",
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

## Rate Limiting

All AI chat message endpoints (Send Message, Stream Message, WebSocket) are rate-limited to prevent abuse and control API costs.

**Rate Limit:** 20 requests per 60 seconds per user

**Rate Limit Headers:**

When a rate limit is exceeded, the response includes:

- `X-RateLimit-Limit`: Maximum requests allowed (20)
- `X-RateLimit-Window`: Time window in seconds (60)
- `Retry-After`: Seconds to wait before retrying (60)

**Rate Limit Error Response (429 Too Many Requests):**

```json
{
  "detail": "Rate limit exceeded. Maximum 20 requests per 60 seconds."
}
```

**Notes:**

- Rate limiting is applied per authenticated user (based on user UUID)
- Unauthenticated requests are rate-limited by IP address
- The limit resets after the time window expires
- WebSocket connections share the same rate limit as REST endpoints
- Rate limits are configurable via environment variables:
  - `AI_RATE_LIMIT_REQUESTS` (default: 20)
  - `AI_RATE_LIMIT_WINDOW` (default: 60)

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

### 429 Too Many Requests

```json
{
  "detail": "Rate limit exceeded. Maximum 20 requests per 60 seconds."
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
- The `user_id` in chat responses should match the authenticated user's UUID from the JWT token
- Messages are stored as a JSON array in the database
- The `title` field can be empty (default: empty string)
- Pagination uses limit-offset pagination with a default limit of 25 and maximum of 100
- The `contacts` field in messages is optional and is typically used when the AI returns search results
- When updating messages, provide the complete messages array (it replaces existing messages, not appends)
- AI chat endpoints support multiple Gemini models (flash, pro, etc.) via the `model` parameter
- Chat sessions maintain conversation history for context-aware responses
- Rate limiting applies to all message-sending endpoints (20 requests per 60 seconds per user)
- Streaming endpoints (SSE and WebSocket) provide real-time response delivery for better UX

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

### 5. Send a message (standard)

```bash
POST /api/v2/ai-chats/{chat_id}/message
Authorization: Bearer <token>
Content-Type: application/json

{
  "message": "Who are my most recent leads?",
  "model": "gemini-1.5-flash"
}
```

### 6. Send a message (streaming)

```bash
POST /api/v2/ai-chats/{chat_id}/message/stream
Authorization: Bearer <token>
Content-Type: application/json
Accept: text/event-stream

{
  "message": "Explain how neural networks work",
  "model": "gemini-1.5-pro"
}
```

### 7. Connect via WebSocket

```javascript
const ws = new WebSocket('ws://34.229.94.175:8000/api/v2/ai-chats/ws/{chat_id}?token=<jwt_token>');

ws.onopen = () => {
  ws.send(JSON.stringify({
    message: "Who are my most recent leads?",
    model: "gemini-1.5-flash"
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'chunk') {
    console.log('Chunk:', data.data);
  } else if (data.type === 'complete') {
    console.log('Complete:', data.data);
  }
};
```

### 8. Delete a chat

```bash
DELETE /api/v2/ai-chats/{chat_id}/
Authorization: Bearer <token>
```
