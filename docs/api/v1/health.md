# Health Check API Documentation

Complete API documentation for health check and monitoring endpoints, including VQL/Connectra service health and statistics.

**Related Documentation:**

- [Root API](./root.md) - For basic API health endpoint
- [User API](./user.md) - For authentication endpoints

## Table of Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [Health Check Endpoints](#health-check-endpoints)
  - [GET /api/v1/health/vql](#get-apiv1healthvql---check-vqlconnectra-health)
  - [GET /api/v1/health/vql/stats](#get-apiv1healthvqlstats---get-vql-statistics)
- [Response Schemas](#response-schemas)
- [Use Cases](#use-cases)
- [Error Handling](#error-handling)

---

## Base URL

For production, use:

```txt
http://34.229.94.175:8000
```

**API Version:** All health check endpoints are under `/api/v1/health/`

## Authentication

All health check endpoints require JWT authentication via the `Authorization` header:

```txt
Authorization: Bearer <access_token>
```

Tokens are obtained through the login or register endpoints.

## Role-Based Access Control

All health check endpoints are accessible to all authenticated users:

- **Free Users (`FreeUser`)**: ✅ Full access to health check endpoints
- **Pro Users (`ProUser`)**: ✅ Full access to health check endpoints
- **Admin (`Admin`)**: ✅ Full access to health check endpoints
- **Super Admin (`SuperAdmin`)**: ✅ Full access to health check endpoints

**Note:** Health check endpoints are primarily used for monitoring and diagnostics. All authenticated users can access these endpoints.

---

## Health Check Endpoints

### GET /api/v1/health/vql - Check VQL/Connectra Health

Check the health and status of the VQL/Connectra service. This endpoint verifies connectivity to the Connectra service and returns health status information.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Accept: application/json`

**Response:**

**Success (200 OK) - Connectra Healthy:**

```json
{
  "connectra_enabled": true,
  "connectra_status": "healthy",
  "connectra_base_url": "https://connectra.example.com",
  "connectra_details": {
    "status": "healthy",
    "version": "1.0.0",
    "uptime": 123456
  },
  "monitoring_available": true
}
```

**Success (200 OK) - Connectra Unavailable:**

```json
{
  "connectra_enabled": true,
  "connectra_status": "unavailable",
  "connectra_base_url": "https://connectra.example.com",
  "connectra_error": "Connection timeout",
  "monitoring_available": true
}
```

**Response Fields:**

- `connectra_enabled` (boolean): Whether Connectra is enabled (always true, as Connectra is now mandatory)
- `connectra_status` (string): Connectra service status. Possible values: `"healthy"`, `"unhealthy"`, `"unknown"`, `"unavailable"`
- `connectra_base_url` (string): Base URL of the Connectra service
- `connectra_details` (object, optional): Detailed health information from Connectra service (only present when status is "healthy")
  - `status` (string): Health status from Connectra
  - `version` (string, optional): Connectra service version
  - `uptime` (integer, optional): Service uptime in seconds
- `connectra_error` (string, optional): Error message if Connectra is unavailable
- `monitoring_available` (boolean): Whether VQL monitoring is available

**Error (401 Unauthorized):**

```json
{
  "detail": "Not authenticated"
}
```

**Error (500 Internal Server Error):**

```json
{
  "detail": "An error occurred while processing the request"
}
```

**Status Codes:**

- `200 OK`: Health check completed successfully
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Server error occurred

**Example Request:**

```bash
curl -X GET "http://34.229.94.175:8000/api/v1/health/vql" \
  -H "Authorization: Bearer <access_token>" \
  -H "Accept: application/json"
```

**Notes:**

- This endpoint checks the health of the Connectra service (VQL layer)
- Connectra is mandatory and always enabled
- The endpoint attempts to connect to Connectra and returns status information
- If Connectra is unavailable, the status will be "unavailable" with an error message
- Monitoring availability indicates whether VQL monitoring middleware is active

---

### GET /api/v1/health/vql/stats - Get VQL Statistics

Get VQL query statistics and metrics. This endpoint provides information about VQL query performance, success rates, and fallback rates.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Accept: application/json`

**Response:**

**Success (200 OK):**

```json
{
  "message": "VQL stats endpoint - requires middleware integration",
  "note": "Stats are tracked by VQLMonitoringMiddleware and can be accessed via monitoring dashboard"
}
```

**Response Fields:**

- `message` (string): Information message about the endpoint
- `note` (string): Additional information about accessing statistics

**Note:** This endpoint currently returns placeholder information. Full statistics are tracked by the VQLMonitoringMiddleware and can be accessed via the monitoring dashboard. The exact response structure may change as monitoring integration is completed.

**Error (401 Unauthorized):**

```json
{
  "detail": "Not authenticated"
}
```

**Error (500 Internal Server Error):**

```json
{
  "detail": "An error occurred while processing the request"
}
```

**Status Codes:**

- `200 OK`: Statistics endpoint accessed successfully
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Server error occurred

**Example Request:**

```bash
curl -X GET "http://34.229.94.175:8000/api/v1/health/vql/stats" \
  -H "Authorization: Bearer <access_token>" \
  -H "Accept: application/json"
```

**Notes:**

- This endpoint provides access to VQL query statistics
- Statistics are tracked by the VQLMonitoringMiddleware
- Full statistics can be accessed via the monitoring dashboard
- The endpoint may return additional metrics in future versions

---

## Response Schemas

### VQL Health Response

```json
{
  "connectra_enabled": true,
  "connectra_status": "healthy",
  "connectra_base_url": "string",
  "connectra_details": {},
  "connectra_error": "string",
  "monitoring_available": true
}
```

**Field Descriptions:**

- `connectra_enabled` (boolean): Whether Connectra is enabled (always true)
- `connectra_status` (string): Connectra service status (`"healthy"`, `"unhealthy"`, `"unknown"`, `"unavailable"`)
- `connectra_base_url` (string): Base URL of the Connectra service
- `connectra_details` (object, optional): Detailed health information from Connectra (only when status is "healthy")
- `connectra_error` (string, optional): Error message if Connectra is unavailable
- `monitoring_available` (boolean): Whether VQL monitoring is available

### VQL Stats Response

```json
{
  "message": "string",
  "note": "string"
}
```

**Field Descriptions:**

- `message` (string): Information message about the endpoint
- `note` (string): Additional information about accessing statistics

**Note:** The stats endpoint currently returns placeholder information. Full statistics are available via the monitoring dashboard.

---

## Use Cases

### 1. Check Connectra Service Health

Monitor the health of the Connectra service:

```bash
GET /api/v1/health/vql
Authorization: Bearer <access_token>
```

### 2. Monitor Service Availability

Set up automated health checks to monitor Connectra availability:

```bash
# Check health every minute
while true; do
  response=$(curl -X GET "http://34.229.94.175:8000/api/v1/health/vql" \
    -H "Authorization: Bearer <access_token>")
  
  status=$(echo $response | jq -r '.connectra_status')
  
  if [ "$status" != "healthy" ]; then
    echo "Alert: Connectra status is $status"
    # Send alert notification
  fi
  
  sleep 60
done
```

### 3. Get VQL Statistics

Access VQL query statistics:

```bash
GET /api/v1/health/vql/stats
Authorization: Bearer <access_token>
```

**Note:** Full statistics are available via the monitoring dashboard.

---

## Error Handling

### Unauthorized Access

**Request:**

```bash
GET /api/v1/health/vql
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
  "detail": "An error occurred while processing the request"
}
```

---

## Notes

- All health check endpoints require JWT authentication
- Connectra is mandatory and always enabled
- The VQL health endpoint checks connectivity to the Connectra service
- Health status can be: "healthy", "unhealthy", "unknown", or "unavailable"
- VQL statistics are tracked by the VQLMonitoringMiddleware
- Full statistics can be accessed via the monitoring dashboard
- The stats endpoint currently returns placeholder information
- All authenticated users can access health check endpoints
- These endpoints are primarily used for monitoring and diagnostics

