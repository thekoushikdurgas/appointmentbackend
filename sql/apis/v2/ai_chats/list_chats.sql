-- ============================================================================
-- Endpoint: GET /api/v2/ai-chats/
-- API Version: v2
-- Description: Get a list of all AI chat conversations for the current user with pagination. Only returns chats owned by the authenticated user. Default ordering is by -created_at (newest first).
-- ============================================================================
--
-- Parameters:
--   $1: user_id (text, required) - User ID from authenticated session
--
-- Query Parameters (All optional):
--   limit (integer, >=1, default: 25, max: 100) - Number of results per page
--   offset (integer, >=0, default: 0) - Offset for pagination
--   ordering (text, default: "-created_at") - Order by field. Prepend '-' for descending. Valid fields: created_at, updated_at, -created_at, -updated_at
--
-- Response Structure:
-- {
--   "count": 10,
--   "next": "http://54.87.173.234:8000/api/v2/ai-chats/?limit=25&offset=25",
--   "previous": null,
--   "results": [
--     {
--       "id": "uuid",
--       "title": "Who are my most recent leads?",
--       "created_at": "2024-01-15T10:30:00Z"
--     }
--   ]
-- }
--
-- Response Codes:
--   200 OK: Chat history retrieved successfully
--   401 Unauthorized: Authentication required
--   500 Internal Server Error: An error occurred while processing the request
--
-- Example Usage:
--   GET /api/v2/ai-chats/?limit=25&offset=0&ordering=-created_at
--   Authorization: Bearer <access_token>
-- ============================================================================

-- ORM Implementation Notes:
--   The AIChatRepository.list_by_user_id() uses simple queries:
--   - No conditional JOINs (single table query)
--   - Filters by user_id for ownership verification
--   - Default ordering: created_at DESC (newest first)
--   - Supports optional filters via AIChatFilterParams

-- Query 1: List chats with default pagination (limit=25, offset=0, ordering=-created_at)
-- GET /api/v2/ai-chats/
SELECT 
    id,
    title,
    created_at
FROM ai_chats
WHERE user_id = $1
ORDER BY created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 2: List chats with custom limit
-- GET /api/v2/ai-chats/?limit=50
SELECT 
    id,
    title,
    created_at
FROM ai_chats
WHERE user_id = $1
ORDER BY created_at DESC NULLS LAST
LIMIT 50
OFFSET 0;

-- Query 3: List chats with offset
-- GET /api/v2/ai-chats/?offset=25
SELECT 
    id,
    title,
    created_at
FROM ai_chats
WHERE user_id = $1
ORDER BY created_at DESC NULLS LAST
LIMIT 25
OFFSET 25;

-- Query 4: List chats with ordering=created_at (ascending)
-- GET /api/v2/ai-chats/?ordering=created_at
SELECT 
    id,
    title,
    created_at
FROM ai_chats
WHERE user_id = $1
ORDER BY created_at ASC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 5: List chats with ordering=-updated_at (descending by updated_at)
-- GET /api/v2/ai-chats/?ordering=-updated_at
SELECT 
    id,
    title,
    created_at
FROM ai_chats
WHERE user_id = $1
ORDER BY updated_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 6: List chats with ordering=updated_at (ascending by updated_at)
-- GET /api/v2/ai-chats/?ordering=updated_at
SELECT 
    id,
    title,
    created_at
FROM ai_chats
WHERE user_id = $1
ORDER BY updated_at ASC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 7: Get total count for pagination
-- Used internally to calculate next/previous links
SELECT COUNT(*) as count
FROM ai_chats
WHERE user_id = $1;

