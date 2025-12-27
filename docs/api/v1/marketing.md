# Marketing Pages API Documentation

Complete API documentation for marketing page endpoints, including public access to published pages and admin management of all pages.

**Related Documentation:**

- [Dashboard Pages API](./dashboard_pages.md) - For dashboard page endpoints
- [User API](./user.md) - For authentication endpoints

## Table of Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [Public Marketing Endpoints](#public-marketing-endpoints)
  - [GET /api/v4/marketing/{page_id}](#get-apiv4marketingpage_id---get-published-marketing-page)
  - [GET /api/v4/marketing/](#get-apiv4marketing---list-published-marketing-pages)
- [Admin Marketing Endpoints](#admin-marketing-endpoints)
  - [GET /api/v4/admin/marketing/](#get-apiv4adminmarketing---list-all-marketing-pages-admin)
  - [GET /api/v4/admin/marketing/{page_id}](#get-apiv4adminmarketingpage_id---get-any-marketing-page-admin)
  - [POST /api/v4/admin/marketing/](#post-apiv4adminmarketing---create-marketing-page-admin)
  - [PUT /api/v4/admin/marketing/{page_id}](#put-apiv4adminmarketingpage_id---update-marketing-page-admin)
  - [DELETE /api/v4/admin/marketing/{page_id}](#delete-apiv4adminmarketingpage_id---delete-marketing-page-admin)
  - [POST /api/v4/admin/marketing/{page_id}/publish](#post-apiv4adminmarketingpage_idpublish---publish-marketing-page-admin)
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

**API Version:** All marketing page endpoints are under `/api/v4/marketing/` or `/api/v4/admin/marketing/`

## Authentication

**Public Endpoints:**
- `GET /api/v4/marketing/{page_id}` - No authentication required (optional)
- `GET /api/v4/marketing/` - No authentication required

**Admin Endpoints:**
- All admin endpoints require JWT authentication via the `Authorization` header:
  ```txt
  Authorization: Bearer <access_token>
  ```
- Admin endpoints require Admin or SuperAdmin role

## Role-Based Access Control

**Public Endpoints:**
- **Unauthenticated users**: ✅ Can view published pages (locked components show upgrade prompts)
- **Authenticated users**: ✅ Can view published pages (content filtered by role)

**Admin Endpoints:**
- **Free Users (`FreeUser`)**: ❌ No access
- **Pro Users (`ProUser`)**: ❌ No access
- **Admin (`Admin`)**: ✅ Full access to all admin endpoints
- **Super Admin (`SuperAdmin`)**: ✅ Full access to all admin endpoints

---

## Public Marketing Endpoints

### GET /api/v4/marketing/{page_id} - Get Published Marketing Page

Get a published marketing page by page_id with access control. Public users (no auth) see all content with locked components showing upgrade prompts. Authenticated users see content filtered by their role.

**Headers:**

- `Authorization: Bearer <access_token>` (optional - for authenticated users)
- `Accept: application/json`

**Path Parameters:**

- `page_id` (string, required): Unique identifier for the marketing page

**Response:**

**Success (200 OK):**

```json
{
  "page_id": "example-page",
  "metadata": {
    "title": "Example Page",
    "description": "Example description",
    "keywords": ["example", "page"],
    "last_updated": "2024-01-15T10:30:00Z",
    "status": "published",
    "version": 1
  },
  "hero": {
    "title": "Hero Title",
    "subtitle": "Hero Subtitle",
    "description": "Hero description",
    "features": ["Feature 1", "Feature 2"],
    "cta_text": "Get Started",
    "cta_href": "/signup"
  },
  "sections": {},
  "hero_stats": null,
  "hero_table": null
}
```

**Response Fields:**

- `page_id` (string): Unique identifier for the page
- `metadata` (object): Page metadata including title, description, status, version
- `hero` (object): Hero section with title, subtitle, description, features, CTA
- `sections` (object): Page-specific sections (dict)
- `hero_stats` (array, optional): Hero statistics
- `hero_table` (object, optional): Hero table data

**Error (404 Not Found) - Page Not Found:**

```json
{
  "detail": "Marketing page 'example-page' not found"
}
```

This error occurs when:
- The page does not exist
- The page is not published (status is not "published")
- The page has been deleted

**Status Codes:**

- `200 OK`: Marketing page retrieved successfully
- `404 Not Found`: Page not found or not published

**Example Request:**

```bash
# Public access (no authentication)
curl -X GET "http://34.229.94.175:8000/api/v4/marketing/example-page"

# Authenticated access
curl -X GET "http://34.229.94.175:8000/api/v4/marketing/example-page" \
  -H "Authorization: Bearer <access_token>"
```

**Notes:**

- Only returns pages with status 'published'
- Public users see all content with locked components showing upgrade prompts
- Authenticated users see content filtered by their role
- Use admin endpoints to access drafts or deleted pages

---

### GET /api/v4/marketing/ - List Published Marketing Pages

List all published marketing pages. This endpoint only returns published pages. Use admin endpoints to access drafts.

**Headers:**

- `Accept: application/json`

**Query Parameters:**

- `include_drafts` (boolean, optional, default: false): Include draft pages (public endpoint ignores this parameter and always excludes drafts)

**Response:**

**Success (200 OK):**

```json
{
  "pages": [
    {
      "page_id": "example-page",
      "metadata": {
        "title": "Example Page",
        "description": "Example description",
        "keywords": ["example"],
        "last_updated": "2024-01-15T10:30:00Z",
        "status": "published",
        "version": 1
      },
      "hero": {
        "title": "Hero Title",
        "subtitle": "Hero Subtitle",
        "description": "Hero description",
        "features": [],
        "cta_text": null,
        "cta_href": null
      }
    }
  ],
  "total": 1
}
```

**Response Fields:**

- `pages` (array): List of marketing pages (MarketingPageResponse objects)
- `total` (integer): Total number of published pages

**Status Codes:**

- `200 OK`: Marketing pages retrieved successfully

**Example Request:**

```bash
curl -X GET "http://34.229.94.175:8000/api/v4/marketing/"
```

**Notes:**

- Only returns published pages (status = "published")
- Draft and deleted pages are excluded
- The `include_drafts` parameter is ignored (always false for public endpoint)
- No authentication required

---

## Admin Marketing Endpoints

### GET /api/v4/admin/marketing/ - List All Marketing Pages (Admin)

List all marketing pages including drafts and optionally deleted pages. Admin only.

**Headers:**

- `Authorization: Bearer <access_token>` (required, Admin or SuperAdmin)
- `Accept: application/json`

**Query Parameters:**

- `include_drafts` (boolean, optional, default: true): Include draft pages
- `include_deleted` (boolean, optional, default: false): Include deleted pages

**Response:**

**Success (200 OK):**

Same structure as public list endpoint, but may include drafts and deleted pages based on query parameters.

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

- `200 OK`: Marketing pages retrieved successfully
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Admin or SuperAdmin role required

**Example Request:**

```bash
curl -X GET "http://34.229.94.175:8000/api/v4/admin/marketing/?include_drafts=true&include_deleted=false" \
  -H "Authorization: Bearer <access_token>"
```

**Notes:**

- Returns all pages regardless of status (based on query parameters)
- Default includes drafts but excludes deleted pages
- Admin or SuperAdmin role required

---

### GET /api/v4/admin/marketing/{page_id} - Get Any Marketing Page (Admin)

Get any marketing page by page_id regardless of status (published, draft, or deleted). Admin only.

**Headers:**

- `Authorization: Bearer <access_token>` (required, Admin or SuperAdmin)
- `Accept: application/json`

**Path Parameters:**

- `page_id` (string, required): Unique identifier for the marketing page

**Response:**

**Success (200 OK):**

Same structure as public get endpoint, but may return pages with any status (published, draft, or deleted).

**Error (404 Not Found):**

```json
{
  "detail": "Marketing page 'example-page' not found"
}
```

**Error (403 Forbidden) - Not Admin:**

```json
{
  "detail": "You do not have permission to perform this action. Admin or SuperAdmin role required."
}
```

**Status Codes:**

- `200 OK`: Marketing page retrieved successfully
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Admin or SuperAdmin role required
- `404 Not Found`: Page not found

**Example Request:**

```bash
curl -X GET "http://34.229.94.175:8000/api/v4/admin/marketing/example-page" \
  -H "Authorization: Bearer <access_token>"
```

**Notes:**

- Returns pages regardless of status (published, draft, or deleted)
- Admin or SuperAdmin role required
- Includes deleted pages

---

### POST /api/v4/admin/marketing/ - Create Marketing Page (Admin)

Create a new marketing page. Pages are created as drafts by default unless status is explicitly set to 'published'. Admin only.

**Headers:**

- `Authorization: Bearer <access_token>` (required, Admin or SuperAdmin)
- `Content-Type: application/json`

**Request Body:**

```json
{
  "page_id": "example-page",
  "metadata": {
    "title": "Example Page",
    "description": "Example description",
    "keywords": ["example", "page"],
    "last_updated": "2024-01-15T10:30:00Z",
    "status": "draft",
    "version": 1
  },
  "hero": {
    "title": "Hero Title",
    "subtitle": "Hero Subtitle",
    "description": "Hero description",
    "features": ["Feature 1", "Feature 2"],
    "cta_text": "Get Started",
    "cta_href": "/signup"
  },
  "sections": {},
  "hero_stats": null,
  "hero_table": null
}
```

**Request Body Fields:**

- `page_id` (string, required): Unique identifier for the page
- `metadata` (object, optional): Page metadata (defaults to draft status if not provided)
- `hero` (object, required): Hero section
- `sections` (object, optional): Page-specific sections (default: empty dict)
- `hero_stats` (array, optional): Hero statistics
- `hero_table` (object, optional): Hero table data

**Response:**

**Success (201 Created):**

Returns the created MarketingPageResponse object.

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

- `201 Created`: Marketing page created successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Admin or SuperAdmin role required

**Example Request:**

```bash
curl -X POST "http://34.229.94.175:8000/api/v4/admin/marketing/" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "page_id": "example-page",
    "hero": {
      "title": "Hero Title",
      "description": "Hero description"
    }
  }'
```

**Notes:**

- Pages are created as drafts by default unless status is explicitly set to 'published'
- Admin or SuperAdmin role required
- The `page_id` must be unique

---

### PUT /api/v4/admin/marketing/{page_id} - Update Marketing Page (Admin)

Update an existing marketing page. Only provided fields will be updated. Version is automatically incremented. Admin only.

**Headers:**

- `Authorization: Bearer <access_token>` (required, Admin or SuperAdmin)
- `Content-Type: application/json`

**Path Parameters:**

- `page_id` (string, required): Unique identifier for the marketing page

**Request Body:**

All fields are optional (partial update):

```json
{
  "metadata": {
    "title": "Updated Title"
  },
  "hero": {
    "subtitle": "Updated Subtitle"
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
- `hero` (object, optional): Hero section (only provided fields will be updated)
- `sections` (object, optional): Page-specific sections
- `hero_stats` (array, optional): Hero statistics
- `hero_table` (object, optional): Hero table data

**Response:**

**Success (200 OK):**

Returns the updated MarketingPageResponse object.

**Error (404 Not Found):**

```json
{
  "detail": "Marketing page 'example-page' not found"
}
```

**Error (403 Forbidden) - Not Admin:**

```json
{
  "detail": "You do not have permission to perform this action. Admin or SuperAdmin role required."
}
```

**Status Codes:**

- `200 OK`: Marketing page updated successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Admin or SuperAdmin role required
- `404 Not Found`: Page not found

**Example Request:**

```bash
curl -X PUT "http://34.229.94.175:8000/api/v4/admin/marketing/example-page" \
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

### DELETE /api/v4/admin/marketing/{page_id} - Delete Marketing Page (Admin)

Delete a marketing page. By default, performs a soft delete (sets status to 'deleted'). Set hard_delete=true to permanently remove the page. Admin only.

**Headers:**

- `Authorization: Bearer <access_token>` (required, Admin or SuperAdmin)

**Path Parameters:**

- `page_id` (string, required): Unique identifier for the marketing page

**Query Parameters:**

- `hard_delete` (boolean, optional, default: false): Permanently delete instead of soft delete

**Response:**

**Success (204 No Content):**

No response body.

**Error (404 Not Found):**

```json
{
  "detail": "Marketing page 'example-page' not found"
}
```

**Error (403 Forbidden) - Not Admin:**

```json
{
  "detail": "You do not have permission to perform this action. Admin or SuperAdmin role required."
}
```

**Status Codes:**

- `204 No Content`: Marketing page deleted successfully
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Admin or SuperAdmin role required
- `404 Not Found`: Page not found

**Example Request:**

```bash
# Soft delete (default)
curl -X DELETE "http://34.229.94.175:8000/api/v4/admin/marketing/example-page" \
  -H "Authorization: Bearer <access_token>"

# Hard delete (permanent)
curl -X DELETE "http://34.229.94.175:8000/api/v4/admin/marketing/example-page?hard_delete=true" \
  -H "Authorization: Bearer <access_token>"
```

**Notes:**

- By default, performs a soft delete (sets status to 'deleted')
- Set `hard_delete=true` to permanently remove the page
- Admin or SuperAdmin role required
- Soft-deleted pages can be restored by updating the status

---

### POST /api/v4/admin/marketing/{page_id}/publish - Publish Marketing Page (Admin)

Publish a draft marketing page. Changes the page status from 'draft' to 'published'. Admin only.

**Headers:**

- `Authorization: Bearer <access_token>` (required, Admin or SuperAdmin)

**Path Parameters:**

- `page_id` (string, required): Unique identifier for the marketing page

**Response:**

**Success (200 OK):**

Returns the published MarketingPageResponse object with status set to 'published'.

**Error (404 Not Found):**

```json
{
  "detail": "Marketing page 'example-page' not found"
}
```

**Error (403 Forbidden) - Not Admin:**

```json
{
  "detail": "You do not have permission to perform this action. Admin or SuperAdmin role required."
}
```

**Status Codes:**

- `200 OK`: Marketing page published successfully
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Admin or SuperAdmin role required
- `404 Not Found`: Page not found

**Example Request:**

```bash
curl -X POST "http://34.229.94.175:8000/api/v4/admin/marketing/example-page/publish" \
  -H "Authorization: Bearer <access_token>"
```

**Notes:**

- Changes the page status from 'draft' to 'published'
- Once published, the page becomes visible to public users
- Admin or SuperAdmin role required
- Version is automatically incremented

---

## Response Schemas

### MarketingPageResponse

```json
{
  "page_id": "string",
  "metadata": {
    "title": "string",
    "description": "string",
    "keywords": ["string"],
    "last_updated": "2024-01-15T10:30:00Z",
    "status": "published",
    "version": 1
  },
  "hero": {
    "title": "string",
    "subtitle": "string",
    "description": "string",
    "features": ["string"],
    "cta_text": "string",
    "cta_href": "string"
  },
  "sections": {},
  "hero_stats": [{"key": "value"}],
  "hero_table": {}
}
```

**Field Descriptions:**

- `page_id` (string): Unique identifier for the page
- `metadata` (MarketingPageMetadata): Page metadata
  - `title` (string): Page title
  - `description` (string): Page description
  - `keywords` (array, optional): SEO keywords
  - `last_updated` (datetime): Last update timestamp
  - `status` (string): Page status ("published", "draft", or "deleted")
  - `version` (integer): Page version number
- `hero` (HeroSection): Hero section
  - `title` (string): Hero title
  - `subtitle` (string, optional): Hero subtitle
  - `description` (string): Hero description
  - `features` (array): List of feature highlights
  - `cta_text` (string, optional): Call-to-action button text
  - `cta_href` (string, optional): Call-to-action button link
- `sections` (object): Page-specific sections (dict)
- `hero_stats` (array, optional): Hero statistics
- `hero_table` (object, optional): Hero table data

### MarketingPageListResponse

```json
{
  "pages": [MarketingPageResponse],
  "total": 0
}
```

**Field Descriptions:**

- `pages` (array): List of marketing pages
- `total` (integer): Total number of pages

### MarketingPageCreate

```json
{
  "page_id": "string",
  "metadata": {},
  "hero": {},
  "sections": {},
  "hero_stats": [],
  "hero_table": {}
}
```

**Field Descriptions:**

- `page_id` (string, required): Unique identifier for the page
- `metadata` (MarketingPageMetadata, optional): Page metadata
- `hero` (HeroSection, required): Hero section
- `sections` (object, optional): Page-specific sections
- `hero_stats` (array, optional): Hero statistics
- `hero_table` (object, optional): Hero table data

### MarketingPageUpdate

```json
{
  "metadata": {},
  "hero": {},
  "sections": {},
  "hero_stats": [],
  "hero_table": {}
}
```

**Field Descriptions:**

All fields are optional - only provided fields will be updated.

---

## Access Control

Marketing pages support role-based access control:

- **Public users (no auth)**: See all content with locked components showing upgrade prompts
- **Authenticated users**: See content filtered by their role (FreeUser, ProUser, Admin, SuperAdmin)
- **Admin users**: Can access all pages including drafts and deleted pages via admin endpoints

**Access Control Metadata:**

Pages and sections can have access control metadata that specifies:
- `allowed_roles`: List of roles that can access the content
- `restriction_type`: Type of restriction ("full", "partial", "none", "hidden")
- `upgrade_message`: Message to show when content is locked
- `required_role`: Minimum required role to access content
- `redirect_path`: Path to redirect to if user lacks access
- `redirect_message`: Message to show when redirecting

---

## Use Cases

### 1. View Published Marketing Page (Public)

View a published marketing page without authentication:

```bash
GET /api/v4/marketing/example-page
```

### 2. View Published Marketing Page (Authenticated)

View a published marketing page with role-based filtering:

```bash
GET /api/v4/marketing/example-page
Authorization: Bearer <access_token>
```

### 3. List All Published Pages

Get a list of all published marketing pages:

```bash
GET /api/v4/marketing/
```

### 4. Create Marketing Page (Admin)

Create a new marketing page as a draft:

```bash
POST /api/v4/admin/marketing/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "page_id": "new-page",
  "hero": {
    "title": "New Page",
    "description": "Page description"
  }
}
```

### 5. Update Marketing Page (Admin)

Update an existing marketing page:

```bash
PUT /api/v4/admin/marketing/example-page
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "metadata": {
    "title": "Updated Title"
  }
}
```

### 6. Publish Draft Page (Admin)

Publish a draft marketing page:

```bash
POST /api/v4/admin/marketing/example-page/publish
Authorization: Bearer <access_token>
```

### 7. Delete Marketing Page (Admin)

Soft delete a marketing page:

```bash
DELETE /api/v4/admin/marketing/example-page
Authorization: Bearer <access_token>
```

Hard delete a marketing page:

```bash
DELETE /api/v4/admin/marketing/example-page?hard_delete=true
Authorization: Bearer <access_token>
```

---

## Error Handling

### Page Not Found

**Request:**

```bash
GET /api/v4/marketing/non-existent-page
```

**Response (404 Not Found):**

```json
{
  "detail": "Marketing page 'non-existent-page' not found"
}
```

### Unauthorized Access (Admin Endpoints)

**Request:**

```bash
GET /api/v4/admin/marketing/
# Missing Authorization header
```

**Response (401 Unauthorized):**

```json
{
  "detail": "Not authenticated"
}
```

### Forbidden Access (Not Admin)

**Request:**

```bash
GET /api/v4/admin/marketing/
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

- Public endpoints do not require authentication
- Public endpoints only return published pages
- Admin endpoints require Admin or SuperAdmin role
- Pages are created as drafts by default
- Version is automatically incremented on updates
- Soft delete sets status to 'deleted' (can be restored)
- Hard delete permanently removes the page
- Access control filtering is applied based on user role
- Public users see locked components with upgrade prompts
- Authenticated users see content filtered by their role

