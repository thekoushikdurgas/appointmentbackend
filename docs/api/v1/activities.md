# User Activities API Documentation

Complete API documentation for user activity tracking endpoints, including viewing activity history and statistics for LinkedIn and email service operations.

**Related Documentation:**

- [LinkedIn API](./linkdin.md) - For LinkedIn URL-based operations (activities are automatically tracked)
- [Email API](./email.md) - For email finder operations (activities are automatically tracked)
- [User API](./user.md) - For authentication endpoints
- [Usage API](./usage.md) - For feature usage tracking endpoints

## Table of Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [Activity Tracking Endpoints](#activity-tracking-endpoints)
  - [GET /api/v3/activities/](#get-apiv3activities---list-user-activities)
  - [GET /api/v3/activities/stats/](#get-apiv3activitiesstats---get-activity-statistics)
- [Activity Tracking Overview](#activity-tracking-overview)
- [Response Schemas](#response-schemas)
- [Use Cases](#use-cases)
- [Error Handling](#error-handling)

---

## Base URL

For production, use:

```txt
http://54.87.173.234:8000
```

**API Version:** All activity endpoints are under `/api/v3/activities/`

## Authentication

All activity endpoints require JWT authentication via the `Authorization` header:

```txt
Authorization: Bearer <access_token>
```

Tokens are obtained through the login or register endpoints.

## Role-Based Access Control

All activity endpoints are accessible to all authenticated users:

- **Free Users (`FreeUser`)**: ✅ Full access to view own activities
- **Pro Users (`ProUser`)**: ✅ Full access to view own activities
- **Admin (`Admin`)**: ✅ Full access to view own activities
- **Super Admin (`SuperAdmin`)**: ✅ Full access to view own activities

**Note:** Users can only view their own activities. There are no role-based restrictions on viewing activity history.

---

## Activity Tracking Endpoints

### GET /api/v3/activities/ - List User Activities

Get the current user's activity history with optional filtering and pagination.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Accept: application/json`

**Query Parameters:**

- `service_type` (string, optional): Filter by service type. Valid values: `linkedin`, `email`
- `action_type` (string, optional): Filter by action type. Valid values: `search`, `export`
- `status` (string, optional): Filter by status. Valid values: `success`, `failed`, `partial`
- `start_date` (timestamp, optional): Filter activities from this date onwards (ISO format, e.g., `2024-01-01T00:00:00Z`)
- `end_date` (timestamp, optional): Filter activities up to this date (ISO format, e.g., `2024-12-31T23:59:59Z`)
- `limit` (integer, optional, default: 100, min: 1, max: 1000): Maximum number of results per page
- `offset` (integer, optional, default: 0, min: 0): Starting offset for results

**Example Request:**

```bash
GET /api/v3/activities/?service_type=linkedin&action_type=search&limit=50&offset=0
Authorization: Bearer <access_token>
Accept: application/json
```

**Response:**

**Success (200 OK):**

```json
{
  "items": [
    {
      "id": 1,
      "user_id": "user-uuid",
      "service_type": "linkedin",
      "action_type": "search",
      "status": "success",
      "request_params": {
        "url": "https://linkedin.com/in/john-doe"
      },
      "result_count": 5,
      "result_summary": {
        "contacts": 3,
        "companies": 2
      },
      "error_message": null,
      "ip_address": "192.168.1.1",
      "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
      "created_at": "2024-01-15T10:30:00Z"
    },
    {
      "id": 2,
      "user_id": "user-uuid",
      "service_type": "email",
      "action_type": "export",
      "status": "success",
      "request_params": {
        "email_count": 10
      },
      "result_count": 8,
      "result_summary": {
        "export_id": "export-uuid",
        "status": "completed",
        "total_contacts": 10,
        "emails_found": 8,
        "emails_not_found": 2
      },
      "error_message": null,
      "ip_address": "192.168.1.1",
      "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
      "created_at": "2024-01-15T11:00:00Z"
    }
  ],
  "total": 150,
  "limit": 50,
  "offset": 0
}
```

**Response Codes:**

- `200 OK`: Activities retrieved successfully
- `400 Bad Request`: Invalid filter parameters (e.g., invalid enum values)
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Failed to retrieve activities

**Notes:**

- Results are ordered by `created_at` descending (most recent first)
- Users can only access their own activities (user_id is automatically set from current_user)
- All filter parameters are optional
- Date filters use ISO 8601 format with timezone (e.g., `2024-01-15T10:30:00Z`)

---

### GET /api/v3/activities/stats/ - Get Activity Statistics

Get activity statistics for the current user, including counts by service type, action type, status, and recent activities (last 24 hours).

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Accept: application/json`

**Query Parameters:**

- `start_date` (timestamp, optional): Filter statistics from this date onwards (ISO format, e.g., `2024-01-01T00:00:00Z`)
- `end_date` (timestamp, optional): Filter statistics up to this date (ISO format, e.g., `2024-12-31T23:59:59Z`)

**Example Request:**

```bash
GET /api/v3/activities/stats/?start_date=2024-01-01T00:00:00Z&end_date=2024-12-31T23:59:59Z
Authorization: Bearer <access_token>
Accept: application/json
```

**Response:**

**Success (200 OK):**

```json
{
  "total_activities": 150,
  "by_service_type": {
    "linkedin": 80,
    "email": 70
  },
  "by_action_type": {
    "search": 100,
    "export": 50
  },
  "by_status": {
    "success": 140,
    "failed": 10
  },
  "recent_activities": 25
}
```

**Response Codes:**

- `200 OK`: Statistics retrieved successfully
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Failed to retrieve activity statistics

**Notes:**

- `recent_activities` counts activities from the last 24 hours (not affected by date filters)
- Users can only access their own activity statistics
- All query parameters are optional
- Date filters use ISO 8601 format with timezone

---

## Activity Tracking Overview

The user activities system automatically tracks all LinkedIn and email service operations. Activities are logged automatically when you use the following endpoints.

**Note:** All operations that deduct credits (LinkedIn search/export, Email search/export, Contact export, Company export) are automatically tracked in the activities system. Credit deduction information is logged as part of the activity metadata.

### LinkedIn Activities

**Search Operations:**

- **Endpoint**: `POST /api/v2/linkedin/` (search)
- **Service Type**: `linkedin`
- **Action Type**: `search`
- **Tracked Data**:
  - Request parameters: LinkedIn URL searched
  - Result count: Total contacts + companies found
  - Result summary: Breakdown of contacts and companies

**Export Operations:**

- **Endpoint**: `POST /api/v2/linkedin/export`
- **Service Type**: `linkedin`
- **Action Type**: `export`
- **Tracked Data**:
  - Request parameters: LinkedIn URLs and count
  - Result count: Total records exported (updated when export completes)
  - Result summary: Export ID, status, contacts, companies, unmatched URLs

### Email Activities

**Search Operations:**

- **Endpoint**: `GET /api/v2/email/finder/`
- **Service Type**: `email`
- **Action Type**: `search`
- **Tracked Data**:
  - Request parameters: First name, last name, domain
  - Result count: Number of emails found
  - Result summary: Emails found count

**Export Operations:**

- **Endpoint**: `POST /api/v2/email/export`
- **Service Type**: `email`
- **Action Type**: `export`
- **Tracked Data**:
  - Request parameters: Email count
  - Result count: Number of emails found (updated when export completes)
  - Result summary: Export ID, status, total contacts, emails found/not found

### Activity Status

Activities can have the following statuses:

- **`success`**: Operation completed successfully
- **`failed`**: Operation failed (error_message contains details)
- **`partial`**: Operation completed with partial results (not currently used, reserved for future use)

### Activity Metadata

Each activity record includes:

- **Request Parameters**: JSON object storing the request parameters (e.g., LinkedIn URL, email search criteria)
- **Result Count**: Number of results returned
- **Result Summary**: JSON object with detailed result information
- **Error Message**: Error message if the operation failed (null for successful operations)
- **IP Address**: User's IP address (extracted from request headers)
- **User Agent**: User's browser/device information
- **Created At**: Timestamp when the activity was recorded

---

## Response Schemas

### UserActivityItem

Schema for a single activity record:

```typescript
{
  id: number;
  user_id: string;  // User UUID
  service_type: "linkedin" | "email";
  action_type: "search" | "export";
  status: "success" | "failed" | "partial";
  request_params: object | null;  // JSON object with request parameters
  result_count: number;
  result_summary: object | null;  // JSON object with result summary
  error_message: string | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;  // ISO 8601 timestamp
}
```

### UserActivityListResponse

Schema for paginated activity list:

```typescript
{
  items: UserActivityItem[];
  total: number;
  limit: number;
  offset: number;
}
```

### ActivityStatsResponse

Schema for activity statistics:

```typescript
{
  total_activities: number;
  by_service_type: {
    linkedin: number;
    email: number;
  };
  by_action_type: {
    search: number;
    export: number;
  };
  by_status: {
    success: number;
    failed: number;
    partial: number;
  };
  recent_activities: number;  // Activities in last 24 hours
}
```

---

## Use Cases

### 1. View Activity History

View all your recent LinkedIn and email operations:

```bash
GET /api/v3/activities/?limit=20
```

### 2. Filter by Service Type

View only LinkedIn activities:

```bash
GET /api/v3/activities/?service_type=linkedin
```

View only email activities:

```bash
GET /api/v3/activities/?service_type=email
```

### 3. Filter by Action Type

View only search operations:

```bash
GET /api/v3/activities/?action_type=search
```

View only export operations:

```bash
GET /api/v3/activities/?action_type=export
```

### 4. Filter by Status

View only successful operations:

```bash
GET /api/v3/activities/?status=success
```

View only failed operations:

```bash
GET /api/v3/activities/?status=failed
```

### 5. Filter by Date Range

View activities from a specific date range:

```bash
GET /api/v3/activities/?start_date=2024-01-01T00:00:00Z&end_date=2024-01-31T23:59:59Z
```

### 6. Combined Filters

View LinkedIn search activities from the last week:

```bash
GET /api/v3/activities/?service_type=linkedin&action_type=search&start_date=2024-01-08T00:00:00Z
```

### 7. Get Activity Statistics

Get overall activity statistics:

```bash
GET /api/v3/activities/stats/
```

Get statistics for a specific date range:

```bash
GET /api/v3/activities/stats/?start_date=2024-01-01T00:00:00Z&end_date=2024-01-31T23:59:59Z
```

---

## Error Handling

### Invalid Filter Parameters

**Request:**

```bash
GET /api/v3/activities/?service_type=invalid
```

**Response (400 Bad Request):**

```json
{
  "detail": "Invalid service_type: invalid. Must be 'linkedin' or 'email'"
}
```

### Unauthorized Access

**Request:**

```bash
GET /api/v3/activities/
# Missing Authorization header
```

**Response (401 Unauthorized):**

```json
{
  "detail": "Not authenticated"
}
```

### Server Error

**Response (500 Internal Server Error):**

```json
{
  "detail": "Failed to retrieve activities"
}
```

---

## Notes

- Activities are logged automatically when using LinkedIn and email endpoints - no additional API calls required
- Export activities are created when the export is initiated and updated when the export completes
- Failed operations are also logged with error messages for debugging
- All activities are tied to the authenticated user (users can only see their own activities)
- IP address and user agent are extracted from request headers automatically
- Request parameters and result summaries are stored as JSON for flexibility
- Activities are immutable once created (except for export completion updates)
- The system uses indexed queries for fast retrieval and filtering
