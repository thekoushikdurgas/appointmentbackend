# Root API Documentation

Complete API documentation for root endpoints that expose API metadata and basic health information.

**Related Documentation:**

- [Health API](./health.md) - For detailed health check endpoints
- [User API](./user.md) - For authentication endpoints

## Table of Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [Root Endpoints](#root-endpoints)
  - [GET /api/v1/](#get-apiv1---get-api-metadata)
  - [GET /api/v1/health/](#get-apiv1health---get-api-health)
- [Response Schemas](#response-schemas)
- [Use Cases](#use-cases)
- [Error Handling](#error-handling)

---

## Base URL

For production, use:

```txt
http://54.87.173.234:8000
```

**API Version:** Root endpoints are under `/api/v1/`

## Authentication

Root endpoints do **not** require authentication. They are publicly accessible.

**Note:** These endpoints are designed to provide basic API information and do not expose sensitive data.

---

## Root Endpoints

### GET /api/v1/ - Get API Metadata

Get basic API metadata including project name, version, and documentation URL. This endpoint provides a lightweight descriptor for the API.

**Headers:**

- `Accept: application/json` (optional)

**Query Parameters:**

- Minimal filter parameters from `RootFilterParams` are supported (typically empty or minimal)

**Response:**

**Success (200 OK):**

```json
{
  "name": "Appointment360",
  "version": "1.0.0",
  "docs": "/docs"
}
```

**Response Fields:**

- `name` (string): Project name
- `version` (string): API version
- `docs` (string): Documentation URL path

**Status Codes:**

- `200 OK`: API metadata retrieved successfully

**Example Request:**

```bash
curl -X GET "http://54.87.173.234:8000/api/v1/"
```

**Notes:**

- This endpoint does not require authentication
- Returns basic API information
- The response structure is minimal and lightweight
- Query parameters from RootFilterParams are supported but typically unused

---

### GET /api/v1/health/ - Get API Health

Get basic API health status. This endpoint returns a lightweight health payload for the versioned API.

**Headers:**

- `Accept: application/json` (optional)

**Query Parameters:**

- Minimal filter parameters from `RootFilterParams` are supported (typically empty or minimal)

**Response:**

**Success (200 OK):**

```json
{
  "status": "healthy",
  "environment": "production"
}
```

**Response Fields:**

- `status` (string): API health status (typically "healthy")
- `environment` (string): Environment name (e.g., "production", "development", "staging")

**Status Codes:**

- `200 OK`: Health status retrieved successfully

**Example Request:**

```bash
curl -X GET "http://54.87.173.234:8000/api/v1/health/"
```

**Notes:**

- This endpoint does not require authentication
- Returns basic health information
- The response is lightweight and designed for quick health checks
- For detailed health information, use `/api/v1/health/vql` (requires authentication)
- Query parameters from RootFilterParams are supported but typically unused

---

## Response Schemas

### API Metadata Response

```json
{
  "name": "string",
  "version": "string",
  "docs": "string"
}
```

**Field Descriptions:**

- `name` (string): Project name
- `version` (string): API version
- `docs` (string): Documentation URL path

### API Health Response

```json
{
  "status": "string",
  "environment": "string"
}
```

**Field Descriptions:**

- `status` (string): API health status (typically "healthy")
- `environment` (string): Environment name (e.g., "production", "development", "staging")

---

## Use Cases

### 1. Get API Information

Retrieve basic API metadata:

```bash
GET /api/v1/
```

### 2. Quick Health Check

Perform a quick health check without authentication:

```bash
GET /api/v1/health/
```

### 3. Service Discovery

Use the root endpoint for service discovery:

```bash
# Get API information
curl -X GET "http://54.87.173.234:8000/api/v1/"

# Response:
# {
#   "name": "Appointment360",
#   "version": "1.0.0",
#   "docs": "/docs"
# }
```

### 4. Health Monitoring

Set up automated health monitoring:

```bash
# Check health every 30 seconds
while true; do
  response=$(curl -X GET "http://54.87.173.234:8000/api/v1/health/")
  
  status=$(echo $response | jq -r '.status')
  
  if [ "$status" != "healthy" ]; then
    echo "Alert: API status is $status"
    # Send alert notification
  fi
  
  sleep 30
done
```

---

## Error Handling

### Server Error

**Response (500 Internal Server Error):**

```json
{
  "detail": "An error occurred while processing the request"
}
```

**Note:** Root endpoints are designed to be highly available and should rarely return errors. If an error occurs, it typically indicates a server configuration issue.

---

## Notes

- Root endpoints do **not** require authentication
- These endpoints are publicly accessible
- The root endpoint (`/api/v1/`) provides basic API metadata
- The health endpoint (`/api/v1/health/`) provides basic health status
- For detailed health information, use `/api/v1/health/vql` (requires authentication)
- Query parameters from RootFilterParams are supported but typically unused
- These endpoints are designed to be lightweight and fast
- The response structure is minimal and does not expose sensitive information

