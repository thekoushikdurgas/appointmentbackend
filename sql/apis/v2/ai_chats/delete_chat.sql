-- ============================================================================
-- Endpoint: DELETE /api/v2/ai-chats/{chat_id}/
-- API Version: v2
-- Description: Delete an AI chat conversation. Only the chat owner can delete their chats. Deletion is permanent and cannot be undone.
-- ============================================================================
--
-- Path Parameters:
--   $1: chat_id (text, required) - Chat UUID identifier
--
-- Parameters:
--   $2: user_id (text, required) - User ID from authenticated session (for ownership verification)
--
-- Response Codes:
--   204 No Content: Chat deleted successfully (no response body)
--   401 Unauthorized: Authentication required
--   403 Forbidden: User does not own this chat
--   404 Not Found: Chat not found
--
-- Note: The response has no body (204 No Content).
-- The application layer verifies ownership before deletion.
--
-- Example Usage:
--   DELETE /api/v2/ai-chats/{chat_id}/
--   Authorization: Bearer <access_token>
-- ============================================================================

-- Query 1: Delete chat by ID with ownership verification
-- DELETE /api/v2/ai-chats/{chat_id}/
DELETE FROM ai_chats
WHERE id = $1
    AND user_id = $2  -- Verify ownership
RETURNING id;

-- Note: If the query returns no rows, the chat either doesn't exist
-- or the user doesn't own it. The application layer handles the
-- appropriate error response (404 Not Found or 403 Forbidden).
-- On success, the endpoint returns 204 No Content with no response body.

