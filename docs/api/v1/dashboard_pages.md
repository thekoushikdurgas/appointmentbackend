# Dashboard Pages API Documentation

Complete API documentation for dashboard page endpoints, including authenticated access to pages with role-based filtering and admin management of all pages.

**Related Documentation:**

- [Marketing Pages API](./marketing.md) - For marketing page endpoints
- [User API](./user.md) - For authentication endpoints

## Table of Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [Dashboard Page Endpoints](#dashboard-page-endpoints)
  - [GET /api/v4/dashboard-pages/{page_id}](#get-apiv4dashboard-pagespage_id---get-dashboard-page)
  - [GET /api/v4/dashboard-pages/](#get-apiv4dashboard-pages---list-dashboard-pages)
- [Admin Dashboard Page Endpoints](#admin-dashboard-page-endpoints)
  - [GET /api/v4/admin/dashboard-pages/](#get-apiv4admindashboard-pages---list-all-dashboard-pages-admin)
  - [GET /api/v4/admin/dashboard-pages/{page_id}](#get-apiv4admindashboard-pagespage_id---get-any-dashboard-page-admin)
  - [POST /api/v4/admin/dashboard-pages/](#post-apiv4admindashboard-pages---create-dashboard-page-admin)
  - [PUT /api/v4/admin/dashboard-pages/{page_id}](#put-apiv4admindashboard-pagespage_id---update-dashboard-page-admin)
  - [DELETE /api/v4/admin/dashboard-pages/{page_id}](#delete-apiv4admindashboard-pagespage_id---delete-dashboard-page-admin)
- [Response Schemas](#response-schemas)
- [Access Control](#access-control)
- [Use Cases](#use-cases)
- [Error Handling](#error-handling)

---

## Base URL

For production, use:

```txt
http://34.229.94.175:8000
```

**API Version:** All dashboard page endpoints are under `/api/v4/dashboard-pages/` or `/api/v4/admin/dashboard-pages/`

## Authentication

**All dashboard page endpoints require JWT authentication:**

```txt
Authorization: Bearer <access_token>
```

Tokens are obtained through the login or register endpoints.

**Admin Endpoints:**
- Admin endpoints require Admin or SuperAdmin role

## Role-Based Access Control

**Public Endpoints (Authenticated Users Only):**
- **Free Users (`FreeUser`)**: ✅ Can view dashboard pages (content filtered by role)
- **Pro Users (`ProUser`)**: ✅ Can view dashboard pages (content filtered by role)
- **Admin (`Admin`)**: ✅ Can view dashboard pages (content filtered by role)
- **Super Admin (`SuperAdmin`)**: ✅ Can view dashboard pages (content filtered by role)

**Admin Endpoints:**
- **Free Users (`FreeUser`)**: ❌ No access
- **Pro Users (`ProUser`)**: ❌ No access
- **Admin (`Admin`)**: ✅ Full access to all admin endpoints
- **Super Admin (`SuperAdmin`)**: ✅ Full access to all admin endpoints

**Note:** All dashboard page endpoints require authentication. Content is filtered based on user role using access control metadata.

---

## Dashboard Page Endpoints

### GET /api/v4/dashboard-pages/{page_id} - Get Dashboard Page

Get a dashboard page by page_id with access control. Requires authentication. Returns page data filtered by user role.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Accept: application/json`

**Path Parameters:**

- `page_id` (string, required): Unique identifier for the dashboard page (e.g., "finder")

**Response:**

**Success (200 OK):**

```json
{
  "page_id": "finder",
  "metadata": {
    "title": "Email Finder",
    "description": "Find email addresses for contacts",
    "route": "/finder",
    "last_updated": "2024-01-15T10:30:00Z",
    "version": 1
  },
  "access_control": {
    "allowed_roles": ["FreeUser", "ProUser", "Admin", "SuperAdmin"],
    "restriction_type": "none",
    "upgrade_message": null,
    "required_role": null,
    "redirect_path": null,
    "redirect_message": null
  },
  "sections": {}
}
```

**Response Fields:**

- `page_id` (string): Unique identifier for the page (e.g., "finder")
- `metadata` (object): Page metadata including title, description, route, version
- `access_control` (object): Access control configuration
  - `allowed_roles` (array): List of roles that can access this page
  - `restriction_type` (string): Type of restriction ("full", "partial", "none", "hidden")
  - `upgrade_message` (string, optional): Message to show when content is locked
  - `required_role` (string, optional): Minimum required role to access content
  - `redirect_path` (string, optional): Path to redirect to if user lacks access
  - `redirect_message` (string, optional): Message to show when redirecting
- `sections` (object): Page sections with nested access control (dict)

**Error (401 Unauthorized):**

```json
{
  "detail": "Not authenticated"
}
```

**Error (404 Not Found):**

```json
{
  "detail": "Dashboard page 'finder' not found"
}
```

**Status Codes:**

- `200 OK`: Dashboard page retrieved successfully
- `401 Unauthorized`: Authentication required
- `404 Not Found`: Page not found

**Example Request:**

```bash
curl -X GET "http://34.229.94.175:8000/api/v4/dashboard-pages/finder" \
  -H "Authorization: Bearer <access_token>" \
  -H "Accept: application/json"
```

**Notes:**

- Requires authentication
- Returns page data filtered by user role
- Access control is applied at both page and section levels
- Sections and components within sections can have their own access control

---

### GET /api/v4/dashboard-pages/ - List Dashboard Pages

List all dashboard pages. Requires authentication. Returns pages filtered by user role.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Accept: application/json`

**Response:**

**Success (200 OK):**

```json
{
  "pages": [
    {
      "page_id": "finder",
      "metadata": {
        "title": "Email Finder",
        "description": "Find email addresses for contacts",
        "route": "/finder",
        "last_updated": "2024-01-15T10:30:00Z",
        "version": 1
      },
      "access_control": {
        "allowed_roles": ["FreeUser", "ProUser", "Admin", "SuperAdmin"],
        "restriction_type": "none"
      },
      "sections": {}
    }
  ],
  "total": 1
}
```

**Response Fields:**

- `pages` (array): List of dashboard pages (DashboardPageResponse objects)
- `total` (integer): Total number of pages accessible to the user

**Error (401 Unauthorized):**

```json
{
  "detail": "Not authenticated"
}
```

**Status Codes:**

- `200 OK`: Dashboard pages retrieved successfully
- `401 Unauthorized`: Authentication required

**Example Request:**

```bash
curl -X GET "http://34.229.94.175:8000/api/v4/dashboard-pages/" \
  -H "Authorization: Bearer <access_token>" \
  -H "Accept: application/json"
```

**Notes:**

- Requires authentication
- Returns pages filtered by user role
- Only pages accessible to the user's role are returned
- Pages are filtered based on access control metadata

---

## Admin Dashboard Page Endpoints

### GET /api/v1/admin/dashboard-pages/ - List All Dashboard Pages (Admin)

List all dashboard pages without filtering. Admin only.

**Headers:**

- `Authorization: Bearer <access_token>` (required, Admin or SuperAdmin)
- `Accept: application/json`

**Response:**

**Success (200 OK):**

Same structure as public list endpoint, but includes all pages without role-based filtering.

**Error (401 Unauthorized):**

```json
{
  "detail": "Not authenticated"
}
```

**Error (403 Forbidden) - Not Admin:**

```json
{
  "detail": "You do not have permission to perform this action. Admin or SuperAdmin role required."
}
```

**Status Codes:**

- `200 OK`: Dashboard pages retrieved successfully
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Admin or SuperAdmin role required

**Example Request:**

```bash
curl -X GET "http://34.229.94.175:8000/api/v1/admin/dashboard-pages/" \
  -H "Authorization: Bearer <access_token>" \
  -H "Accept: application/json"
```

**Notes:**

- Returns all pages without filtering
- Admin or SuperAdmin role required
- Full page data is returned without access control filtering

---

### GET /api/v1/admin/dashboard-pages/{page_id} - Get Any Dashboard Page (Admin)

Get any dashboard page by page_id without filtering. Returns full page data without access control filtering. Admin only.

**Headers:**

- `Authorization: Bearer <access_token>` (required, Admin or SuperAdmin)
- `Accept: application/json`

**Path Parameters:**

- `page_id` (string, required): Unique identifier for the dashboard page

**Response:**

**Success (200 OK):**

Same structure as public get endpoint, but returns full page data without access control filtering.

**Error (404 Not Found):**

```json
{
  "detail": "Dashboard page 'finder' not found"
}
```

**Error (403 Forbidden) - Not Admin:**

```json
{
  "detail": "You do not have permission to perform this action. Admin or SuperAdmin role required."
}
```

**Status Codes:**

- `200 OK`: Dashboard page retrieved successfully
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Admin or SuperAdmin role required
- `404 Not Found`: Page not found

**Example Request:**

```bash
curl -X GET "http://34.229.94.175:8000/api/v1/admin/dashboard-pages/finder" \
  -H "Authorization: Bearer <access_token>" \
  -H "Accept: application/json"
```

**Notes:**

- Returns full page data without access control filtering
- Admin or SuperAdmin role required
- All sections and components are returned regardless of access control

---

### POST /api/v1/admin/dashboard-pages/ - Create Dashboard Page (Admin)

Create a new dashboard page. Admin only.

**Headers:**

- `Authorization: Bearer <access_token>` (required, Admin or SuperAdmin)
- `Content-Type: application/json`

**Request Body:**

```json
{
  "page_id": "finder",
  "metadata": {
    "title": "Email Finder",
    "description": "Find email addresses for contacts",
    "route": "/finder"
  },
  "access_control": {
    "allowed_roles": ["FreeUser", "ProUser", "Admin", "SuperAdmin"],
    "restriction_type": "none"
  },
  "sections": {}
}
```

**Request Body Fields:**

- `page_id` (string, required): Unique identifier for the page (e.g., "finder")
- `metadata` (object, optional): Page metadata
  - `title` (string, required): Page title
  - `description` (string, required): Page description
  - `route` (string, required): Frontend route path (e.g., "/finder")
- `access_control` (object, optional): Access control configuration
- `sections` (object, optional): Page sections (default: empty dict)

**Response:**

**Success (201 Created):**

Returns the created DashboardPageResponse object.

**Error (400 Bad Request):**

```json
{
  "detail": "Invalid request data"
}
```

**Error (403 Forbidden) - Not Admin:**

```json
{
  "detail": "You do not have permission to perform this action. Admin or SuperAdmin role required."
}
```

**Status Codes:**

- `201 Created`: Dashboard page created successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Admin or SuperAdmin role required

**Example Request:**

```bash
curl -X POST "http://34.229.94.175:8000/api/v1/admin/dashboard-pages/" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "page_id": "finder",
    "metadata": {
      "title": "Email Finder",
      "description": "Find email addresses",
      "route": "/finder"
    }
  }'
```

**Notes:**

- Admin or SuperAdmin role required
- The `page_id` must be unique
- Metadata route should match the frontend route path

---

### PUT /api/v1/admin/dashboard-pages/{page_id} - Update Dashboard Page (Admin)

Update an existing dashboard page. Only provided fields will be updated. Version is automatically incremented. Admin only.

**Headers:**

- `Authorization: Bearer <access_token>` (required, Admin or SuperAdmin)
- `Content-Type: application/json`

**Path Parameters:**

- `page_id` (string, required): Unique identifier for the dashboard page

**Request Body:**

All fields are optional (partial update):

```json
{
  "metadata": {
    "title": "Updated Title"
  },
  "access_control": {
    "allowed_roles": ["ProUser", "Admin", "SuperAdmin"]
  },
  "sections": {
    "new_section": {
      "content": "New section content"
    }
  }
}
```

**Request Body Fields:**

- `metadata` (object, optional): Page metadata (only provided fields will be updated)
- `access_control` (object, optional): Access control configuration
- `sections` (object, optional): Page sections

**Response:**

**Success (200 OK):**

Returns the updated DashboardPageResponse object.

**Error (404 Not Found):**

```json
{
  "detail": "Dashboard page 'finder' not found"
}
```

**Error (403 Forbidden) - Not Admin:**

```json
{
  "detail": "You do not have permission to perform this action. Admin or SuperAdmin role required."
}
```

**Status Codes:**

- `200 OK`: Dashboard page updated successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Admin or SuperAdmin role required
- `404 Not Found`: Page not found

**Example Request:**

```bash
curl -X PUT "http://34.229.94.175:8000/api/v1/admin/dashboard-pages/finder" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "metadata": {
      "title": "Updated Title"
    }
  }'
```

**Notes:**

- Only provided fields will be updated (partial update)
- Version is automatically incremented on update
- Admin or SuperAdmin role required

---

### DELETE /api/v1/admin/dashboard-pages/{page_id} - Delete Dashboard Page (Admin)

Delete a dashboard page. Admin only.

**Headers:**

- `Authorization: Bearer <access_token>` (required, Admin or SuperAdmin)

**Path Parameters:**

- `page_id` (string, required): Unique identifier for the dashboard page

**Response:**

**Success (204 No Content):**

No response body.

**Error (404 Not Found):**

```json
{
  "detail": "Dashboard page 'finder' not found"
}
```

**Error (403 Forbidden) - Not Admin:**

```json
{
  "detail": "You do not have permission to perform this action. Admin or SuperAdmin role required."
}
```

**Status Codes:**

- `204 No Content`: Dashboard page deleted successfully
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Admin or SuperAdmin role required
- `404 Not Found`: Page not found

**Example Request:**

```bash
curl -X DELETE "http://34.229.94.175:8000/api/v1/admin/dashboard-pages/finder" \
  -H "Authorization: Bearer <access_token>"
```

**Notes:**

- Admin or SuperAdmin role required
- Deletion is permanent (no soft delete for dashboard pages)

---

## Response Schemas

### DashboardPageResponse

```json
{
  "page_id": "string",
  "metadata": {
    "title": "string",
    "description": "string",
    "route": "string",
    "last_updated": "2024-01-15T10:30:00Z",
    "version": 1
  },
  "access_control": {
    "allowed_roles": ["string"],
    "restriction_type": "string",
    "upgrade_message": "string",
    "required_role": "string",
    "redirect_path": "string",
    "redirect_message": "string"
  },
  "sections": {}
}
```

**Field Descriptions:**

- `page_id` (string): Unique identifier for the page (e.g., "finder")
- `metadata` (DashboardPageMetadata): Page metadata
  - `title` (string): Page title
  - `description` (string): Page description
  - `route` (string): Frontend route path (e.g., "/finder")
  - `last_updated` (datetime): Last update timestamp
  - `version` (integer): Page version number
- `access_control` (DashboardPageAccessControl): Access control configuration
  - `allowed_roles` (array): List of roles that can access this page
  - `restriction_type` (string): Type of restriction ("full", "partial", "none", "hidden")
  - `upgrade_message` (string, optional): Message to show when content is locked
  - `required_role` (string, optional): Minimum required role to access content
  - `redirect_path` (string, optional): Path to redirect to if user lacks access
  - `redirect_message` (string, optional): Message to show when redirecting
- `sections` (object): Page sections with nested access control (dict)

### DashboardPageListResponse

```json
{
  "pages": [DashboardPageResponse],
  "total": 0
}
```

**Field Descriptions:**

- `pages` (array): List of dashboard pages
- `total` (integer): Total number of pages

### DashboardPageCreate

```json
{
  "page_id": "string",
  "metadata": {},
  "access_control": {},
  "sections": {}
}
```

**Field Descriptions:**

- `page_id` (string, required): Unique identifier for the page
- `metadata` (DashboardPageMetadata, optional): Page metadata
- `access_control` (DashboardPageAccessControl, optional): Access control configuration
- `sections` (object, optional): Page sections

### DashboardPageUpdate

```json
{
  "metadata": {},
  "access_control": {},
  "sections": {}
}
```

**Field Descriptions:**

All fields are optional - only provided fields will be updated.

---

## Access Control

Dashboard pages support role-based access control at multiple levels:

- **Page-level access control**: Controls access to the entire page
- **Section-level access control**: Controls access to individual sections within a page
- **Component-level access control**: Controls access to components within sections

**Access Control Configuration:**

- `allowed_roles`: List of roles that can access the content (empty list means accessible to all)
- `restriction_type`: Type of restriction
  - `"full"`: Content is locked, shows upgrade prompt
  - `"partial"`: Content shows teaser/preview
  - `"none"`: No restriction, full access
  - `"hidden"`: Content is not shown
- `upgrade_message`: Message to show when content is locked
- `required_role`: Minimum required role to access content
- `redirect_path`: Path to redirect to if user lacks access (e.g., "/billing")
- `redirect_message`: Message to show when redirecting

**Filtering Behavior:**

- Public endpoints return pages filtered by user role
- Admin endpoints return full page data without filtering
- Sections and components are filtered based on access control metadata

---

## Use Cases

### 1. View Dashboard Page

Get a dashboard page with role-based filtering:

```bash
GET /api/v4/dashboard-pages/finder
Authorization: Bearer <access_token>
```

### 2. List Accessible Dashboard Pages

Get a list of all dashboard pages accessible to the user:

```bash
GET /api/v4/dashboard-pages/
Authorization: Bearer <access_token>
```

### 3. Create Dashboard Page (Admin)

Create a new dashboard page:

```bash
POST /api/v1/admin/dashboard-pages/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "page_id": "new-page",
  "metadata": {
    "title": "New Page",
    "description": "Page description",
    "route": "/new-page"
  }
}
```

### 4. Update Dashboard Page (Admin)

Update an existing dashboard page:

```bash
PUT /api/v1/admin/dashboard-pages/finder
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "metadata": {
    "title": "Updated Title"
  }
}
```

### 5. Delete Dashboard Page (Admin)

Delete a dashboard page:

```bash
DELETE /api/v1/admin/dashboard-pages/finder
Authorization: Bearer <access_token>
```

---

## Error Handling

### Unauthorized Access

**Request:**

```bash
GET /api/v4/dashboard-pages/finder
# Missing Authorization header
```

**Response (401 Unauthorized):**

```json
{
  "detail": "Not authenticated"
}
```

### Page Not Found

**Request:**

```bash
GET /api/v4/dashboard-pages/non-existent-page
Authorization: Bearer <access_token>
```

**Response (404 Not Found):**

```json
{
  "detail": "Dashboard page 'non-existent-page' not found"
}
```

### Forbidden Access (Not Admin)

**Request:**

```bash
GET /api/v1/admin/dashboard-pages/
Authorization: Bearer <free_user_token>
```

**Response (403 Forbidden):**

```json
{
  "detail": "You do not have permission to perform this action. Admin or SuperAdmin role required."
}
```

---

## Notes

- All dashboard page endpoints require authentication
- Public endpoints return pages filtered by user role
- Admin endpoints require Admin or SuperAdmin role
- Admin endpoints return full page data without filtering
- Access control is applied at page, section, and component levels
- Version is automatically incremented on updates
- Deletion is permanent (no soft delete)
- The `page_id` must be unique
- Metadata route should match the frontend route path

