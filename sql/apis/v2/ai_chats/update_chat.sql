-- ============================================================================
-- Endpoint: PUT /api/v2/ai-chats/{chat_id}/
-- API Version: v2
-- Description: Update an existing AI chat conversation (typically to add new messages or update the title). All fields are optional - only provided fields will be updated. Only the chat owner can update their chats.
-- ============================================================================
--
-- Path Parameters:
--   $1: chat_id (text, required) - Chat UUID identifier
--
-- Parameters:
--   $2: user_id (text, required) - User ID from authenticated session (for ownership verification)
--   $3: title (text, optional, max 255 chars) - Chat title
--   $4: messages (jsonb, optional) - Complete list of messages (replaces existing messages)
--
-- Request Body Fields (All optional):
--   title (string, optional, max 255 characters) - Chat title
--   messages (array, optional) - Complete list of messages (replaces existing messages)
--
-- Message Format:
--   Each message must be an object with:
--   - sender (string, required): Must be either "user" or "ai"
--   - text (string, required): Message text content
--   - contacts (array, optional): Array of contact objects when AI returns search results
--
-- Response Structure:
-- {
--   "id": "uuid",
--   "user_id": "user-uuid",
--   "title": "Updated title (optional)",
--   "messages": [
--     {
--       "sender": "ai",
--       "text": "Hello! I'm NexusAI..."
--     },
--     {
--       "sender": "user",
--       "text": "Who are my most recent leads?"
--     },
--     {
--       "sender": "ai",
--       "text": "Here are your most recent leads:",
--       "contacts": []
--     },
--     {
--       "sender": "user",
--       "text": "Show me more details"
--     }
--   ],
--   "created_at": "2024-01-15T10:30:00Z",
--   "updated_at": "2024-01-15T11:45:00Z"
-- }
--
-- Response Codes:
--   200 OK: Chat updated successfully
--   400 Bad Request: Invalid request data
--   401 Unauthorized: Authentication required
--   403 Forbidden: User does not own this chat
--   404 Not Found: Chat not found
--
-- Note: When updating messages, provide the complete messages array.
-- It replaces existing messages, not appends.
--
-- Example Usage:
--   PUT /api/v2/ai-chats/{chat_id}/
--   Content-Type: application/json
--   Authorization: Bearer <access_token>
--   
--   {
--     "title": "Updated title (optional)",
--     "messages": [
--       {
--         "sender": "ai",
--         "text": "Hello! I'm NexusAI..."
--       },
--       {
--         "sender": "user",
--         "text": "Who are my most recent leads?"
--       }
--     ]
--   }
-- ============================================================================

-- Query 1: Update chat title and messages
-- PUT /api/v2/ai-chats/{chat_id}/ with both title and messages
UPDATE ai_chats
SET 
    title = COALESCE($3, title),
    messages = COALESCE($4, messages),
    updated_at = NOW()
WHERE id = $1
    AND user_id = $2  -- Verify ownership
RETURNING 
    id,
    user_id,
    title,
    messages,
    created_at,
    updated_at;

-- Query 2: Update only title
-- PUT /api/v2/ai-chats/{chat_id}/ with {"title": "New Title"}
UPDATE ai_chats
SET 
    title = $3,
    updated_at = NOW()
WHERE id = $1
    AND user_id = $2  -- Verify ownership
RETURNING 
    id,
    user_id,
    title,
    messages,
    created_at,
    updated_at;

-- Query 3: Update only messages
-- PUT /api/v2/ai-chats/{chat_id}/ with {"messages": [...]}
UPDATE ai_chats
SET 
    messages = $4,
    updated_at = NOW()
WHERE id = $1
    AND user_id = $2  -- Verify ownership
RETURNING 
    id,
    user_id,
    title,
    messages,
    created_at,
    updated_at;

-- Note: If the query returns no rows, the chat either doesn't exist
-- or the user doesn't own it. The application layer handles the
-- appropriate error response (404 Not Found or 403 Forbidden).

