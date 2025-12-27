# Feature Usage Tracking API Documentation

Complete API documentation for feature usage tracking endpoints, including tracking feature usage and retrieving current usage limits.

**Related Documentation:**
- [User API](./user.md) - For user authentication and profile management
- [Activities API](./activities.md) - For activity tracking
- [Billing API](./billing.md) - For subscription and billing information

## Table of Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [Feature Usage Endpoints](#feature-usage-endpoints)
  - [GET /api/v1/usage/current/](#get-apiv1usagecurrent---get-current-feature-usage)
  - [POST /api/v1/usage/track/](#post-apiv1usagetrack---track-feature-usage)
  - [POST /api/v2/usage/reset](#post-apiv2usagereset---reset-feature-usage)
- [Feature Types](#feature-types)
- [Response Schemas](#response-schemas)
- [Use Cases](#use-cases)
- [Error Handling](#error-handling)

---

## Base URL

For production, use:

```txt
http://34.229.94.175:8000
```

**API Version:** All usage endpoints are under `/api/v1/usage/`

## Authentication

All usage endpoints require JWT authentication via the `Authorization` header:

```txt
Authorization: Bearer <access_token>
```

Tokens are obtained through the login or register endpoints.

## Role-Based Access Control

All usage endpoints are accessible to all authenticated users:

- **Free Users (`FreeUser`)**: ✅ Full access to track and view own usage
- **Pro Users (`ProUser`)**: ✅ Full access to track and view own usage
- **Admin (`Admin`)**: ✅ Full access to track and view own usage
- **Super Admin (`SuperAdmin`)**: ✅ Full access to track and view own usage

**Note:** Users can only track and view their own feature usage. Usage limits are automatically determined based on the user's role.

---

## Feature Usage Endpoints

### GET /api/v1/usage/current/ - Get Current Feature Usage

Get the current feature usage for all features for the authenticated user. Returns usage counts and limits for each feature.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Accept: application/json`

**Query Parameters:**

None

**Example Request:**

```bash
GET /api/v1/usage/current/
Authorization: Bearer <access_token>
Accept: application/json
```

**Response:**

**Success (200 OK):**

```json
{
  "AI_CHAT": {
    "used": 0,
    "limit": 999999
  },
  "BULK_EXPORT": {
    "used": 0,
    "limit": 999999
  },
  "API_KEYS": {
    "used": 0,
    "limit": 999999
  },
  "TEAM_MANAGEMENT": {
    "used": 0,
    "limit": 999999
  },
  "EMAIL_FINDER": {
    "used": 5,
    "limit": 10
  },
  "VERIFIER": {
    "used": 2,
    "limit": 5
  },
  "LINKEDIN": {
    "used": 3,
    "limit": 5
  },
  "DATA_SEARCH": {
    "used": 15,
    "limit": 20
  },
  "ADVANCED_FILTERS": {
    "used": 0,
    "limit": 999999
  },
  "AI_SUMMARIES": {
    "used": 0,
    "limit": 999999
  },
  "SAVE_SEARCHES": {
    "used": 0,
    "limit": 999999
  },
  "BULK_VERIFICATION": {
    "used": 0,
    "limit": 999999
  }
}
```

**Response Fields:**

- Each feature name maps to an object with:
  - `used` (integer): Current usage count for this feature (0 or greater)
  - `limit` (integer): Usage limit for this feature. A value of `999999` indicates unlimited usage (for Pro users and above)

**Response Codes:**

- `200 OK`: Usage data retrieved successfully
- `401 Unauthorized`: Authentication required
- `404 Not Found`: User profile not found
- `500 Internal Server Error`: Failed to retrieve usage data

**Notes:**

- Usage limits are automatically determined based on the user's role:
  - **Free Users**: Limited usage per feature (e.g., 10 for EMAIL_FINDER, 5 for VERIFIER)
  - **Pro Users and Above**: Unlimited usage (limit = 999999) for most features
- Usage resets monthly based on the billing period
- If a feature has no usage record, it returns `used: 0` with the appropriate limit
- The limit value `999999` should be treated as unlimited in the frontend

---

### POST /api/v1/usage/track/ - Track Feature Usage

Track feature usage for the authenticated user. Increments the usage count for the specified feature by the given amount.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`
- `Accept: application/json`

**Request Body:**

```json
{
  "feature": "EMAIL_FINDER",
  "amount": 1
}
```

**Field Requirements:**

- `feature` (string, required): Feature name. Valid values: `AI_CHAT`, `BULK_EXPORT`, `API_KEYS`, `TEAM_MANAGEMENT`, `EMAIL_FINDER`, `VERIFIER`, `LINKEDIN`, `DATA_SEARCH`, `ADVANCED_FILTERS`, `AI_SUMMARIES`, `SAVE_SEARCHES`, `BULK_VERIFICATION`
- `amount` (integer, optional, default: 1, min: 1): Amount to increment usage by

**Example Request:**

```bash
POST /api/v1/usage/track/
Authorization: Bearer <access_token>
Content-Type: application/json
Accept: application/json

{
  "feature": "EMAIL_FINDER",
  "amount": 1
}
```

**Response:**

**Success (200 OK):**

```json
{
  "feature": "EMAIL_FINDER",
  "used": 6,
  "limit": 10,
  "success": true
}
```

**Response Fields:**

- `feature` (string): Feature name that was tracked
- `used` (integer): Updated usage count after tracking
- `limit` (integer): Usage limit for this feature. A value of `999999` indicates unlimited usage
- `success` (boolean): Whether tracking was successful (always `true` for successful requests)

**Response Codes:**

- `200 OK`: Usage tracked successfully
- `400 Bad Request`: Invalid feature name or amount
- `401 Unauthorized`: Authentication required
- `404 Not Found`: User profile not found
- `500 Internal Server Error`: Failed to track usage

**Notes:**

- Usage is automatically capped at the limit (cannot exceed limit)
- For unlimited features (Pro users), usage can increment without limit
- If the feature doesn't have a usage record, one is automatically created
- Usage tracking is idempotent - multiple calls with the same parameters will increment usage each time
- The usage count is reset monthly based on the billing period

---

### POST /api/v2/usage/reset - Reset Feature Usage

Reset the usage counter for a specific feature to zero. This endpoint allows users to manually reset their usage count for a particular feature, useful for testing or administrative purposes.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`
- `Accept: application/json`

**Request Body:**

```json
{
  "feature": "EMAIL_FINDER"
}
```

**Request Body Fields:**

- `feature` (string, required): Feature name to reset. Valid values: `AI_CHAT`, `BULK_EXPORT`, `API_KEYS`, `TEAM_MANAGEMENT`, `EMAIL_FINDER`, `VERIFIER`, `LINKEDIN`, `DATA_SEARCH`, `ADVANCED_FILTERS`, `AI_SUMMARIES`, `SAVE_SEARCHES`, `BULK_VERIFICATION`

**Example Request:**

```bash
POST /api/v2/usage/reset
Authorization: Bearer <access_token>
Content-Type: application/json
Accept: application/json

{
  "feature": "EMAIL_FINDER"
}
```

**Response:**

**Success (200 OK):**

```json
{
  "feature": "EMAIL_FINDER",
  "used": 0,
  "limit": 10,
  "success": true
}
```

**Response Fields:**

- `feature` (string): Feature name that was reset
- `used` (integer): Updated usage count after reset (always 0)
- `limit` (integer): Usage limit for this feature. A value of `999999` indicates unlimited usage
- `success` (boolean): Whether reset was successful (always `true` for successful requests)

**Error (400 Bad Request) - Invalid Feature Name:**

```json
{
  "detail": "Invalid feature: INVALID_FEATURE"
}
```

**Error (401 Unauthorized):**

```json
{
  "detail": "Not authenticated"
}
```

**Error (404 Not Found) - User Profile Not Found:**

```json
{
  "detail": "User profile not found for user_id: <user_id>"
}
```

**Error (500 Internal Server Error):**

```json
{
  "detail": "Failed to reset usage: <error_message>"
}
```

**Response Codes:**

- `200 OK`: Usage reset successfully
- `400 Bad Request`: Invalid feature name
- `401 Unauthorized`: Authentication required
- `404 Not Found`: User profile not found
- `500 Internal Server Error`: Failed to reset usage

**Notes:**

- Resetting usage sets the usage count to 0 for the specified feature
- The usage limit remains unchanged (based on user role)
- If the feature doesn't have a usage record, one is created with `used: 0`
- This endpoint is useful for testing, debugging, or administrative resets
- Usage will still reset automatically monthly based on the billing period
- Only the authenticated user can reset their own usage

---

## Feature Types

The following features are tracked:

| Feature | Free User Limit | Pro User Limit | Description |
|---------|----------------|----------------|-------------|
| `AI_CHAT` | 0 | Unlimited | AI chat functionality |
| `BULK_EXPORT` | 0 | Unlimited | Bulk export operations |
| `API_KEYS` | 0 | Unlimited | API key management |
| `TEAM_MANAGEMENT` | 0 | Unlimited | Team management features (Admin only) |
| `EMAIL_FINDER` | 10 | Unlimited | Email finder searches |
| `VERIFIER` | 5 | Unlimited | Email verification |
| `LINKEDIN` | 5 | Unlimited | LinkedIn profile lookups |
| `DATA_SEARCH` | 20 | Unlimited | Data search operations |
| `ADVANCED_FILTERS` | 0 | Unlimited | Advanced filtering features |
| `AI_SUMMARIES` | 0 | Unlimited | AI-generated summaries |
| `SAVE_SEARCHES` | 0 | Unlimited | Save search functionality |
| `BULK_VERIFICATION` | 0 | Unlimited | Bulk email verification |

**Note:** A limit of `0` means the feature is not available to free users. A limit of `999999` (returned as unlimited) means the feature has no usage restrictions for Pro users and above.

---

## Response Schemas

### FeatureUsageResponse

Schema for current usage response:

```typescript
{
  [feature: string]: {
    used: number;    // Current usage count (0 or greater)
    limit: number;   // Usage limit (999999 = unlimited)
  }
}
```

Example:

```json
{
  "EMAIL_FINDER": {
    "used": 5,
    "limit": 10
  },
  "VERIFIER": {
    "used": 2,
    "limit": 5
  }
}
```

### TrackUsageRequest

Schema for track usage request:

```typescript
{
  feature: string;  // Feature name (e.g., "EMAIL_FINDER")
  amount: number;    // Amount to increment (default: 1, min: 1)
}
```

### TrackUsageResponse

Schema for track usage response:

```typescript
{
  feature: string;   // Feature name
  used: number;      // Updated usage count
  limit: number;     // Usage limit (999999 = unlimited)
  success: boolean;   // Whether tracking was successful
}
```

### ResetUsageRequest

Schema for reset usage request:

```typescript
{
  feature: string;  // Feature name (e.g., "EMAIL_FINDER")
}
```

### ResetUsageResponse

Schema for reset usage response:

```typescript
{
  feature: string;   // Feature name
  used: number;      // Updated usage count (always 0 after reset)
  limit: number;     // Usage limit (999999 = unlimited)
  success: boolean;   // Whether reset was successful
}
```

---

## Use Cases

### 1. Get Current Usage

Check current usage for all features:

```bash
GET /api/v1/usage/current/
```

### 2. Track Feature Usage

Track usage when a user performs an action:

```bash
POST /api/v1/usage/track/
{
  "feature": "EMAIL_FINDER",
  "amount": 1
}
```

### 3. Track Multiple Usage

Track multiple uses at once:

```bash
POST /api/v1/usage/track/
{
  "feature": "DATA_SEARCH",
  "amount": 5
}
```

### 4. Check Usage Before Action

1. Get current usage
2. Check if user has remaining usage
3. Perform action if allowed
4. Track usage after successful action

### 5. Reset Feature Usage

Reset usage counter for a specific feature (useful for testing or administrative purposes):

```bash
POST /api/v2/usage/reset
{
  "feature": "EMAIL_FINDER"
}
```

---

## Error Handling

### Invalid Feature Name

**Request:**

```bash
POST /api/v1/usage/track/
{
  "feature": "INVALID_FEATURE",
  "amount": 1
}
```

**Response (400 Bad Request):**

```json
{
  "detail": "Invalid feature: INVALID_FEATURE"
}
```

### Invalid Amount

**Request:**

```bash
POST /api/v1/usage/track/
{
  "feature": "EMAIL_FINDER",
  "amount": 0
}
```

**Response (400 Bad Request):**

```json
{
  "detail": [
    {
      "type": "greater_than_equal",
      "loc": ["body", "amount"],
      "msg": "Input should be greater than or equal to 1",
      "input": 0
    }
  ]
}
```

### Unauthorized Access

**Request:**

```bash
GET /api/v1/usage/current/
# Missing Authorization header
```

**Response (401 Unauthorized):**

```json
{
  "detail": "Not authenticated"
}
```

### User Profile Not Found

**Response (404 Not Found):**

```json
{
  "detail": "User profile not found for user_id: <user_id>"
}
```

### Server Error

**Response (500 Internal Server Error) - Get Current Usage:**

```json
{
  "detail": "Failed to retrieve feature usage"
}
```

**Response (500 Internal Server Error) - Track Usage:**

```json
{
  "detail": "Failed to track feature usage"
}
```

### Invalid Feature Name (Reset)

**Request:**

```bash
POST /api/v2/usage/reset
{
  "feature": "INVALID_FEATURE"
}
```

**Response (400 Bad Request):**

```json
{
  "detail": "Invalid feature: INVALID_FEATURE"
}
```

### Server Error (Reset)

**Response (500 Internal Server Error) - Reset Usage:**

```json
{
  "detail": "Failed to reset usage: <error_message>"
}
```

---

## Notes

- Usage limits are automatically determined based on the user's role (FreeUser, ProUser, Admin, SuperAdmin)
- Usage resets monthly based on the billing period (period_start and period_end)
- Pro users and above get unlimited usage (limit = 999999) for most features
- Free users have limited usage per feature as defined in the feature limits configuration
- Usage tracking is automatic - the frontend should call the track endpoint after successful feature usage
- The system automatically creates usage records when first tracking a feature
- Usage counts are capped at the limit (cannot exceed limit for limited features)
- The reset endpoint allows manual reset of usage counters (useful for testing or administrative purposes)
- Resetting usage sets the count to 0 but does not change the limit
- All timestamps are in ISO 8601 format (UTC)
- The limit value `999999` should be treated as unlimited in frontend applications (can be converted to `Infinity`)
