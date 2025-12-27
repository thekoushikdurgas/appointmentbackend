# Analytics API Documentation

Complete API documentation for analytics and performance monitoring endpoints, including performance metrics submission for web vitals and custom metrics.

**Related Documentation:**

- [User API](../v1/user.md) - For authentication endpoints
- [Health API](../v1/health.md) - For health check and monitoring endpoints

## Table of Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [Analytics Endpoints](#analytics-endpoints)
  - [POST /api/v2/analytics/performance](#post-apiv2analyticsperformance---submit-performance-metric)
- [Response Schemas](#response-schemas)
- [Use Cases](#use-cases)
- [Error Handling](#error-handling)

---

## Base URL

For production, use:

```txt
http://34.229.94.175:8000
```

**API Version:** All analytics endpoints are under `/api/v2/analytics/`

## Authentication

All analytics endpoints require JWT authentication via the `Authorization` header:

```txt
Authorization: Bearer <access_token>
```

Tokens are obtained through the login or register endpoints.

## Role-Based Access Control

All analytics endpoints are accessible to all authenticated users regardless of role:

- **Free Users (`FreeUser`)**: ✅ Full access to all analytics endpoints
- **Pro Users (`ProUser`)**: ✅ Full access to all analytics endpoints
- **Admin (`Admin`)**: ✅ Full access to all analytics endpoints
- **Super Admin (`SuperAdmin`)**: ✅ Full access to all analytics endpoints

**Note:** There are no role-based restrictions on analytics functionality. All authenticated users can submit performance metrics.

---

## Analytics Endpoints

### POST /api/v2/analytics/performance - Submit Performance Metric

Submit a performance metric for analytics tracking. This endpoint accepts performance metrics such as Core Web Vitals (LCP, FID, CLS), custom metrics, and other performance measurements. Metrics can be stored in a database or sent to analytics services like Google Analytics, Mixpanel, or custom analytics platforms.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Request Body:**

```json
{
  "name": "LCP",
  "value": 2.5,
  "timestamp": 1703520000000,
  "metadata": {
    "url": "/dashboard",
    "user_agent": "Mozilla/5.0...",
    "connection_type": "4g"
  }
}
```

**Request Body Fields:**

- `name` (string, required): Metric name (e.g., "LCP", "FID", "CLS", "TTFB", "custom_metric")
- `value` (float, required): Metric value (e.g., 2.5 for LCP in seconds, 0.1 for CLS score)
- `timestamp` (integer, required): Timestamp in milliseconds (Unix timestamp * 1000)
- `metadata` (object, optional): Additional metadata about the metric (e.g., URL, user agent, connection type)

**Response:**

**Success (200 OK):**

```json
{
  "success": true,
  "message": "Metric received"
}
```

**Response Fields:**

- `success` (boolean): Whether the metric was successfully received
- `message` (string): Status message indicating the metric was received

**Error (400 Bad Request) - Missing Required Fields:**

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "name"],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```

**Error (401 Unauthorized):**

```json
{
  "detail": "Not authenticated"
}
```

**Error (500 Internal Server Error):**

```json
{
  "detail": "Failed to store performance metric: <error_message>"
}
```

**Status Codes:**

- `200 OK`: Metric received successfully (even if storage fails, endpoint returns success to not block client)
- `400 Bad Request`: Missing required fields (name, value, or timestamp)
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Server error occurred (but endpoint still returns success to client)

**Example Request:**

```bash
curl -X POST "http://34.229.94.175:8000/api/v2/analytics/performance" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "LCP",
    "value": 2.5,
    "timestamp": 1703520000000,
    "metadata": {
      "url": "/dashboard",
      "connection_type": "4g"
    }
  }'
```

**Example Metrics:**

**Core Web Vitals:**

```json
{
  "name": "LCP",
  "value": 2.5,
  "timestamp": 1703520000000,
  "metadata": {
    "url": "/dashboard"
  }
}
```

```json
{
  "name": "FID",
  "value": 50,
  "timestamp": 1703520000000,
  "metadata": {
    "url": "/dashboard"
  }
}
```

```json
{
  "name": "CLS",
  "value": 0.1,
  "timestamp": 1703520000000,
  "metadata": {
    "url": "/dashboard"
  }
}
```

**Custom Metrics:**

```json
{
  "name": "api_response_time",
  "value": 150,
  "timestamp": 1703520000000,
  "metadata": {
    "endpoint": "/api/v3/contacts/query",
    "method": "POST"
  }
}
```

**Notes:**

- The endpoint accepts performance metrics and stores them for analysis
- In production, metrics can be stored in a database or sent to analytics services (Google Analytics 4, Mixpanel, custom analytics)
- The endpoint returns success even if storage fails (to not block client requests)
- Timestamps should be in milliseconds (Unix timestamp * 1000)
- Metadata is optional and can contain any additional context about the metric
- Common metric names include Core Web Vitals: "LCP" (Largest Contentful Paint), "FID" (First Input Delay), "CLS" (Cumulative Layout Shift), "TTFB" (Time to First Byte)
- Custom metrics can use any name that describes the measurement

---

## Response Schemas

### PerformanceMetric

```json
{
  "name": "string",
  "value": 0.0,
  "timestamp": 0,
  "metadata": {}
}
```

**Field Descriptions:**

- `name` (string, required): Metric name (e.g., "LCP", "FID", "CLS", "TTFB", or custom metric name)
- `value` (float, required): Metric value (e.g., seconds for LCP, milliseconds for FID, score for CLS)
- `timestamp` (integer, required): Timestamp in milliseconds (Unix timestamp * 1000)
- `metadata` (object, optional): Additional metadata about the metric (e.g., URL, user agent, connection type, endpoint, method)

### PerformanceMetricResponse

```json
{
  "success": true,
  "message": "string"
}
```

**Field Descriptions:**

- `success` (boolean): Whether the metric was successfully received
- `message` (string): Status message indicating the metric was received

---

## Use Cases

### 1. Submit Core Web Vitals

Track Core Web Vitals (LCP, FID, CLS) for performance monitoring:

```bash
POST /api/v2/analytics/performance
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "LCP",
  "value": 2.5,
  "timestamp": 1703520000000,
  "metadata": {
    "url": "/dashboard"
  }
}
```

### 2. Track Custom Performance Metrics

Submit custom performance metrics for application-specific measurements:

```bash
POST /api/v2/analytics/performance
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "api_response_time",
  "value": 150,
  "timestamp": 1703520000000,
  "metadata": {
    "endpoint": "/api/v3/contacts/query",
    "method": "POST"
  }
}
```

### 3. Monitor Page Load Performance

Track page load times and other performance indicators:

```bash
POST /api/v2/analytics/performance
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "page_load_time",
  "value": 1.2,
  "timestamp": 1703520000000,
  "metadata": {
    "url": "/contacts",
    "connection_type": "4g"
  }
}
```

### 4. Batch Metric Submission

Submit multiple metrics in sequence:

```bash
# Submit LCP
POST /api/v2/analytics/performance
{
  "name": "LCP",
  "value": 2.5,
  "timestamp": 1703520000000
}

# Submit FID
POST /api/v2/analytics/performance
{
  "name": "FID",
  "value": 50,
  "timestamp": 1703520001000
}

# Submit CLS
POST /api/v2/analytics/performance
{
  "name": "CLS",
  "value": 0.1,
  "timestamp": 1703520002000
}
```

---

## Error Handling

### Missing Required Fields

**Request:**

```bash
POST /api/v2/analytics/performance
{
  "value": 2.5,
  "timestamp": 1703520000000
  // Missing name field
}
```

**Response (400 Bad Request):**

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "name"],
      "msg": "Field required",
      "input": {
        "value": 2.5,
        "timestamp": 1703520000000
      }
    }
  ]
}
```

### Invalid Timestamp

**Request:**

```bash
POST /api/v2/analytics/performance
{
  "name": "LCP",
  "value": 2.5,
  "timestamp": "invalid"
}
```

**Response (400 Bad Request):**

```json
{
  "detail": [
    {
      "type": "int_parsing",
      "loc": ["body", "timestamp"],
      "msg": "Input should be a valid integer",
      "input": "invalid"
    }
  ]
}
```

### Unauthorized Access

**Request:**

```bash
POST /api/v2/analytics/performance
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
  "detail": "Failed to store performance metric: <error_message>"
}
```

**Note:** Even if storage fails, the endpoint returns a 200 OK response with `success: true` to not block client requests. Errors are logged server-side.

---

## Notes

- All analytics endpoints require JWT authentication
- Performance metrics are submitted for analysis and monitoring
- In production, metrics can be stored in a database or sent to analytics services (Google Analytics 4, Mixpanel, custom analytics)
- The endpoint is designed to be non-blocking - it returns success even if storage fails
- Timestamps should be in milliseconds (Unix timestamp * 1000)
- Metadata is optional and can contain any additional context about the metric
- Common metric names include Core Web Vitals: "LCP", "FID", "CLS", "TTFB"
- Custom metrics can use any descriptive name
- All endpoints are accessible to all authenticated users regardless of role
- No credits are deducted for using analytics endpoints (unlimited usage)
- Metrics are typically aggregated and analyzed for performance dashboards and monitoring

