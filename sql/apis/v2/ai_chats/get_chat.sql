-- ============================================================================
-- Endpoint: GET /api/v2/ai-chats/{chat_id}/
-- API Version: v2
-- Description: Get detailed information about a specific AI chat conversation, including all messages. Only the chat owner can access their chats.
-- ============================================================================
--
-- Path Parameters:
--   $1: chat_id (text, required) - Chat UUID identifier
--
-- Parameters:
--   $2: user_id (text, required) - User ID from authenticated session (for ownership verification)
--
-- Response Structure:
-- {
--   "id": "uuid",
--   "user_id": "user-uuid",
--   "title": "Who are my most recent leads?",
--   "messages": [
--     {
--       "sender": "ai",
--       "text": "Hello! I'm NexusAI, your smart CRM assistant. How can I help you find contacts today?"
--     },
--     {
--       "sender": "user",
--       "text": "Who are my most recent leads?",
--       "contacts": []
--     },
--     {
--       "sender": "ai",
--       "text": "Here are your most recent leads:",
--       "contacts": [...]
--     }
--   ],
--   "created_at": "2024-01-15T10:30:00Z",
--   "updated_at": "2024-01-15T11:45:00Z"
-- }
--
-- Response Codes:
--   200 OK: Chat retrieved successfully
--   401 Unauthorized: Authentication required
--   403 Forbidden: User does not own this chat
--   404 Not Found: Chat not found
--
-- Example Usage:
--   GET /api/v2/ai-chats/{chat_id}/
--   Authorization: Bearer <access_token>
-- ============================================================================

-- Query 1: Retrieve chat by ID with ownership verification
-- GET /api/v2/ai-chats/{chat_id}/
SELECT 
    id,
    user_id,
    title,
    messages,
    created_at,
    updated_at
FROM ai_chats
WHERE id = $1
    AND user_id = $2;  -- Verify ownership

-- Note: If the query returns no rows, the chat either doesn't exist
-- or the user doesn't own it. The application layer handles the
-- appropriate error response (404 Not Found or 403 Forbidden).

