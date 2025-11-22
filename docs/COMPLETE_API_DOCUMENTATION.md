# Complete API Documentation

## Table of Contents

1. [Authentication](#authentication)
2. [API Version 1 Endpoints](#api-version-1-endpoints)
3. [API Version 2 Endpoints](#api-version-2-endpoints)
4. [WebSocket Endpoints](#websocket-endpoints)
5. [Common Schemas](#common-schemas)

---

## Authentication

### Headers

All authenticated endpoints require:

- **Authorization**: `Bearer <access_token>`
  - Token obtained from `/api/v2/auth/login/` or `/api/v2/auth/register/`
  - Token expires after 30 minutes (configurable)
  - Format: `Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

### Write Operations Headers

For write operations (create/update/delete), additional headers may be required:

- **X-Contacts-Write-Key**: Required for contact write operations (admin only)
- **X-Companies-Write-Key**: Required for company write operations (admin only)

---

## API Version 1 Endpoints

Base URL: `/api/v1`

### Root Endpoints

#### GET `/`

**Description**: Return API metadata

**Headers**: None required

**Query Parameters**: None

**Response**: 

```json
{
  "name": "Contact360 API",
  "version": "0.1.0",
  "docs": "/docs"
}
```

#### GET `/health/`

**Description**: Health check endpoint

**Headers**: None required

**Query Parameters**: None

**Response**:

```json
{
  "status": "healthy",
  "environment": "development"
}
```

---

### Contacts Endpoints

Base URL: `/api/v1/contacts`

#### GET `/`

**Description**: List contacts with filtering and pagination

**Headers**:

- `Authorization: Bearer <token>` (required)

**Query Parameters**:

- `limit` (int, optional, ge=1): Maximum number of results per page
- `offset` (int, optional, ge=0, default=0): Starting offset for results
- `cursor` (string, optional): Opaque cursor token for pagination
- `view` (string, optional): When "simple", returns ContactSimpleItem, otherwise ContactListItem
- All ContactFilterParams fields (see Common Schemas section)

**Response**: `CursorPage[ContactListItem | ContactSimpleItem]`

```json
{
  "next": "http://...",
  "previous": "http://...",
  "results": [...]
}
```

#### GET `/count/`

**Description**: Get total count of contacts matching filters

**Headers**:

- `Authorization: Bearer <token>` (required)

**Query Parameters**: All ContactFilterParams fields

**Response**: `CountResponse`

```json
{
  "count": 12345
}
```

#### GET `/count/uuids/`

**Description**: Get contact UUIDs matching filters

**Headers**:

- `Authorization: Bearer <token>` (required)

**Query Parameters**:

- `limit` (int, optional, ge=1): Limit number of UUIDs returned
- All ContactFilterParams fields

**Response**: `UuidListResponse`

```json
{
  "count": 100,
  "uuids": ["uuid1", "uuid2", ...]
}
```

#### POST `/`

**Description**: Create a new contact (admin only)

**Headers**:

- `Authorization: Bearer <token>` (required, admin)
- `X-Contacts-Write-Key: <key>` (required)

**Body**: `ContactCreate`

```json
{
  "uuid": "optional-uuid",
  "first_name": "John",
  "last_name": "Doe",
  "company_id": "company-uuid",
  "email": "john@example.com",
  "title": "Software Engineer",
  "departments": ["Engineering"],
  "mobile_phone": "+1234567890",
  "email_status": "verified",
  "text_search": "location text",
  "seniority": "Senior"
}
```

**Response**: `ContactDetail` (201 Created)

#### GET `/{contact_uuid}/`

**Description**: Retrieve a single contact by UUID

**Headers**:

- `Authorization: Bearer <token>` (required)

**Path Parameters**:

- `contact_uuid` (string, required): Contact UUID

**Response**: `ContactDetail`

#### GET `/title/`

**Description**: List contact titles

**Headers**:

- `Authorization: Bearer <token>` (required)

**Query Parameters**: 

- All ContactFilterParams fields
- All AttributeListParams fields (limit, offset, distinct, ordering, search)

**Response**: `List[str]`

#### GET `/company/`

**Description**: List company names (from Company table only)

**Headers**:

- `Authorization: Bearer <token>` (required)

**Query Parameters**: AttributeListParams fields

**Response**: `CursorPage[str]`

#### GET `/industry/`

**Description**: List industries (from Company table, always distinct=true)

**Headers**:

- `Authorization: Bearer <token>` (required)

**Query Parameters**:

- `company` (list[str], optional): Filter by company name(s). Supports multiple values or comma-separated
- AttributeListParams fields

**Response**: `CursorPage[str]`

#### GET `/keywords/`

**Description**: List keywords (from Company table, always distinct=true)

**Headers**:

- `Authorization: Bearer <token>` (required)

**Query Parameters**:

- `company` (list[str], optional): Filter by company name(s)
- AttributeListParams fields

**Response**: `CursorPage[str]`

#### GET `/technologies/`

**Description**: List technologies

**Headers**:

- `Authorization: Bearer <token>` (required)

**Query Parameters**:

- `separated` (bool, optional, default=false): If true, returns individual technology values
- ContactFilterParams fields
- AttributeListParams fields

**Response**: `List[str]`

#### GET `/company_address/`

**Description**: List company addresses

**Headers**:

- `Authorization: Bearer <token>` (required)

**Query Parameters**: ContactFilterParams and AttributeListParams fields

**Response**: `List[str]`

#### GET `/contact_address/`

**Description**: List contact addresses

**Headers**:

- `Authorization: Bearer <token>` (required)

**Query Parameters**: ContactFilterParams and AttributeListParams fields

**Response**: `List[str]`


---

### Companies Endpoints

Base URL: `/api/v1/companies`

#### GET `/`

**Description**: List companies with filtering and pagination

**Headers**:

- `Authorization: Bearer <token>` (required)

**Query Parameters**:

- `limit` (int, optional, ge=1)
- `offset` (int, optional, ge=0, default=0)
- `cursor` (string, optional)
- All CompanyFilterParams fields

**Response**: `CursorPage[CompanyListItem]`

#### GET `/count/`

**Description**: Get total count of companies matching filters

**Headers**:

- `Authorization: Bearer <token>` (required)

**Query Parameters**: All CompanyFilterParams fields

**Response**: `CountResponse`

#### GET `/count/uuids/`

**Description**: Get company UUIDs matching filters

**Headers**:

- `Authorization: Bearer <token>` (required)

**Query Parameters**:

- `limit` (int, optional, ge=1)
- All CompanyFilterParams fields

**Response**: `UuidListResponse`

#### POST `/`

**Description**: Create a new company (admin only)

**Headers**:

- `Authorization: Bearer <token>` (required, admin)
- `X-Companies-Write-Key: <key>` (required)

**Body**: `CompanyCreate`

```json
{
  "uuid": "optional-uuid",
  "name": "Acme Corp",
  "employees_count": 100,
  "industries": ["Technology"],
  "keywords": ["AI", "ML"],
  "address": "123 Main St",
  "annual_revenue": 10000000,
  "total_funding": 5000000,
  "technologies": ["Python", "PostgreSQL"],
  "text_search": "location text"
}
```

**Response**: `CompanyDetail` (201 Created)

#### PUT `/{company_uuid}/`

**Description**: Update an existing company (admin only)

**Headers**:

- `Authorization: Bearer <token>` (required, admin)
- `X-Companies-Write-Key: <key>` (required)

**Path Parameters**:

- `company_uuid` (string, required)

**Body**: `CompanyUpdate` (all fields optional)

**Response**: `CompanyDetail`

#### DELETE `/{company_uuid}/`

**Description**: Delete a company (admin only)

**Headers**:

- `Authorization: Bearer <token>` (required, admin)
- `X-Companies-Write-Key: <key>` (required)

**Path Parameters**:

- `company_uuid` (string, required)

**Response**: 204 No Content

#### GET `/{company_uuid}/`

**Description**: Retrieve a single company by UUID

**Headers**:

- `Authorization: Bearer <token>` (required)

**Path Parameters**:

- `company_uuid` (string, required)

**Response**: `CompanyDetail`

#### GET `/name/`

**Description**: List company names

**Headers**:

- `Authorization: Bearer <token>` (required)

**Query Parameters**: CompanyFilterParams and AttributeListParams fields

**Response**: `List[str]`

#### GET `/industry/`

**Description**: List industries

**Headers**:

- `Authorization: Bearer <token>` (required)

**Query Parameters**:

- `separated` (bool, optional, default=false)
- CompanyFilterParams and AttributeListParams fields

**Response**: `List[str]`

#### GET `/keywords/`

**Description**: List keywords

**Headers**:

- `Authorization: Bearer <token>` (required)

**Query Parameters**:

- `separated` (bool, optional, default=false)
- CompanyFilterParams and AttributeListParams fields

**Response**: `List[str]`

#### GET `/technologies/`

**Description**: List technologies

**Headers**:

- `Authorization: Bearer <token>` (required)

**Query Parameters**:

- `separated` (bool, optional, default=false)
- CompanyFilterParams and AttributeListParams fields

**Response**: `List[str]`

#### GET `/address/`

**Description**: List company addresses

**Headers**:

- `Authorization: Bearer <token>` (required)

**Query Parameters**: CompanyFilterParams and AttributeListParams fields

**Response**: `List[str]`

#### GET `/city/`

**Description**: List company cities

**Headers**:

- `Authorization: Bearer <token>` (required)

**Query Parameters**: CompanyFilterParams and AttributeListParams fields

**Response**: `List[str]`

#### GET `/state/`

**Description**: List company states

**Headers**:

- `Authorization: Bearer <token>` (required)

**Query Parameters**: CompanyFilterParams and AttributeListParams fields

**Response**: `List[str]`

#### GET `/country/`

**Description**: List company countries

**Headers**:

- `Authorization: Bearer <token>` (required)

**Query Parameters**: CompanyFilterParams and AttributeListParams fields

**Response**: `List[str]`

#### GET `/company/{company_uuid}/contacts/`

**Description**: List contacts for a specific company

**Headers**:

- `Authorization: Bearer <token>` (required)

**Path Parameters**:

- `company_uuid` (string, required)

**Query Parameters**:

- `limit` (int, optional, ge=1)
- `offset` (int, optional, ge=0, default=0)
- `cursor` (string, optional)
- All CompanyContactFilterParams fields

**Response**: `CursorPage[ContactListItem]`

#### GET `/company/{company_uuid}/contacts/count/`

**Description**: Count contacts for a specific company

**Headers**:

- `Authorization: Bearer <token>` (required)

**Path Parameters**:

- `company_uuid` (string, required)

**Query Parameters**: All CompanyContactFilterParams fields

**Response**: `CountResponse`

#### GET `/company/{company_uuid}/contacts/count/uuids/`

**Description**: Get contact UUIDs for a specific company

**Headers**:

- `Authorization: Bearer <token>` (required)

**Path Parameters**:

- `company_uuid` (string, required)

**Query Parameters**:

- `limit` (int, optional, ge=1)
- All CompanyContactFilterParams fields

**Response**: `UuidListResponse`

#### GET `/company/{company_uuid}/contacts/first_name/`

**Description**: List first names for company contacts

**Headers**:

- `Authorization: Bearer <token>` (required)

**Path Parameters**:

- `company_uuid` (string, required)

**Query Parameters**: CompanyContactFilterParams and AttributeListParams fields

**Response**: `List[str]`

#### GET `/company/{company_uuid}/contacts/last_name/`

**Description**: List last names for company contacts

**Headers**:

- `Authorization: Bearer <token>` (required)

**Path Parameters**:

- `company_uuid` (string, required)

**Query Parameters**: CompanyContactFilterParams and AttributeListParams fields

**Response**: `List[str]`

#### GET `/company/{company_uuid}/contacts/title/`

**Description**: List titles for company contacts

**Headers**:

- `Authorization: Bearer <token>` (required)

**Path Parameters**:

- `company_uuid` (string, required)

**Query Parameters**: CompanyContactFilterParams and AttributeListParams fields

**Response**: `List[str]`

#### GET `/company/{company_uuid}/contacts/seniority/`

**Description**: List seniorities for company contacts

**Headers**:

- `Authorization: Bearer <token>` (required)

**Path Parameters**:

- `company_uuid` (string, required)

**Query Parameters**: CompanyContactFilterParams and AttributeListParams fields

**Response**: `List[str]`

#### GET `/company/{company_uuid}/contacts/department/`

**Description**: List departments for company contacts

**Headers**:

- `Authorization: Bearer <token>` (required)

**Path Parameters**:

- `company_uuid` (string, required)

**Query Parameters**: CompanyContactFilterParams and AttributeListParams fields

**Response**: `List[str]`

#### GET `/company/{company_uuid}/contacts/email_status/`

**Description**: List email statuses for company contacts

**Headers**:

- `Authorization: Bearer <token>` (required)

**Path Parameters**:

- `company_uuid` (string, required)

**Query Parameters**: CompanyContactFilterParams and AttributeListParams fields

**Response**: `List[str]`

---

### Imports Endpoints

Base URL: `/api/v1/contacts/import`

#### GET `/`

**Description**: Get import instructions

**Headers**:

- `Authorization: Bearer <token>` (required)

**Response**: `MessageResponse`

#### POST `/`

**Description**: Upload CSV file for contact import (admin only)

**Headers**:

- `Authorization: Bearer <token>` (required, admin)
- `Content-Type: multipart/form-data` (required)

**Body**: Form data with file

- `file` (file, required): CSV file to upload

**Response**: `ImportJobDetail` (202 Accepted)

#### GET `/{job_id}/`

**Description**: Get import job details

**Headers**:

- `Authorization: Bearer <token>` (required)

**Path Parameters**:

- `job_id` (string, required)

**Query Parameters**:

- `include_errors` (bool, optional, default=false): Include error records

**Response**: `ImportJobDetail | ImportJobWithErrors`

#### GET `/{job_id}/errors/`

**Description**: Get import job errors

**Headers**:

- `Authorization: Bearer <token>` (required)

**Path Parameters**:

- `job_id` (string, required)

**Response**: `List[ImportErrorRecord]`

---

## API Version 2 Endpoints

Base URL: `/api/v2`

### Authentication Endpoints

Base URL: `/api/v2/auth`

#### POST `/register/`

**Description**: Register a new user account

**Headers**: None required

**Body**: `UserRegister`

```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "securepassword123"
}
```

**Response**: `RegisterResponse` (201 Created)

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "user-uuid",
    "email": "john@example.com"
  },
  "message": "Registration successful! Please check your email to verify your account."
}
```

#### POST `/login/`

**Description**: Authenticate user and receive tokens

**Headers**: None required

**Body**: `UserLogin`

```json
{
  "email": "john@example.com",
  "password": "securepassword123"
}
```

**Response**: `TokenResponse`

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "user-uuid",
    "email": "john@example.com"
  }
}
```

#### POST `/logout/`

**Description**: Logout current user

**Headers**:

- `Authorization: Bearer <token>` (required)

**Body**: `LogoutRequest`

```json
{
  "refresh_token": "optional-refresh-token"
}
```

**Response**: `LogoutResponse`

```json
{
  "message": "Logout successful"
}
```

#### GET `/session/`

**Description**: Get current user session information

**Headers**:

- `Authorization: Bearer <token>` (required)

**Response**: `SessionResponse`

```json
{
  "user": {
    "id": "user-uuid",
    "email": "john@example.com"
  },
  "last_sign_in_at": "2024-01-01T00:00:00Z"
}
```

#### POST `/refresh/`

**Description**: Refresh access token using refresh token

**Headers**: None required

**Body**: `RefreshTokenRequest`

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response**: `RefreshTokenResponse`

```json
{
  "access_token": "new-access-token",
  "refresh_token": "new-refresh-token"
}
```

---

### Users Endpoints

Base URL: `/api/v2/users`

#### GET `/profile/`

**Description**: Get current user profile

**Headers**:

- `Authorization: Bearer <token>` (required)

**Response**: `ProfileResponse`

```json
{
  "id": "user-uuid",
  "name": "John Doe",
  "email": "john@example.com",
  "role": "Member",
  "avatar_url": "http://...",
  "is_active": true,
  "job_title": "Software Engineer",
  "bio": "Bio text",
  "timezone": "UTC",
  "notifications": {
    "weeklyReports": true,
    "newLeadAlerts": true
  },
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

#### PUT `/profile/`

**Description**: Update current user profile (partial update)

**Headers**:

- `Authorization: Bearer <token>` (required)

**Body**: `ProfileUpdate` (all fields optional)

```json
{
  "name": "John Doe Updated",
  "job_title": "Senior Software Engineer",
  "bio": "Updated bio",
  "timezone": "America/New_York",
  "avatar_url": "http://...",
  "notifications": {
    "weeklyReports": false,
    "newLeadAlerts": true
  },
  "role": "Admin"
}
```

**Response**: `ProfileResponse`

#### POST `/profile/avatar/`

**Description**: Upload avatar image

**Headers**:

- `Authorization: Bearer <token>` (required)
- `Content-Type: multipart/form-data` (required)

**Body**: Form data

- `avatar` (file, required): Image file (JPEG, PNG, GIF, WebP, max 5MB)

**Response**: `AvatarUploadResponse`

```json
{
  "avatar_url": "http://...",
  "profile": {...},
  "message": "Avatar uploaded successfully"
}
```

#### POST `/promote-to-admin/`

**Description**: Promote current user to admin role

**Headers**:

- `Authorization: Bearer <token>` (required)

**Response**: `ProfileResponse`

---

### AI Chat Endpoints

Base URL: `/api/v2/ai-chats`

#### GET `/`

**Description**: List AI chat conversations for current user

**Headers**:

- `Authorization: Bearer <token>` (required)

**Query Parameters**:

- `limit` (int, optional, ge=1, le=100, default=25): Number of results per page
- `offset` (int, optional, ge=0, default=0): Offset for pagination
- `ordering` (string, optional, default="-created_at"): Order by field (created_at, updated_at, -created_at, -updated_at)

**Response**: `PaginatedAIChatResponse`

```json
{
  "count": 10,
  "next": "http://...",
  "previous": "http://...",
  "results": [...]
}
```

#### POST `/`

**Description**: Create a new AI chat conversation

**Headers**:

- `Authorization: Bearer <token>` (required)

**Body**: `AIChatCreate`

```json
{
  "title": "Chat Title",
  "messages": [
    {
      "sender": "user",
      "text": "Hello",
      "contacts": null
    }
  ]
}
```

**Response**: `AIChatResponse` (201 Created)

#### GET `/{chat_id}/`

**Description**: Get detailed AI chat conversation

**Headers**:

- `Authorization: Bearer <token>` (required)

**Path Parameters**:

- `chat_id` (string, required): Chat UUID

**Response**: `AIChatResponse`

#### PUT `/{chat_id}/`

**Description**: Update AI chat conversation (partial update)

**Headers**:

- `Authorization: Bearer <token>` (required)

**Path Parameters**:

- `chat_id` (string, required)

**Body**: `AIChatUpdate` (all fields optional)

```json
{
  "title": "Updated Title",
  "messages": [...]
}
```

**Response**: `AIChatResponse`

#### DELETE `/{chat_id}/`

**Description**: Delete AI chat conversation

**Headers**:

- `Authorization: Bearer <token>` (required)

**Path Parameters**:

- `chat_id` (string, required)

**Response**: 204 No Content

---

### Apollo Endpoints

Base URL: `/api/v2/apollo`

#### POST `/analyze`

**Description**: Analyze Apollo.io URL and return structured parameter breakdown

**Headers**:

- `Authorization: Bearer <token>` (required)

**Body**: `ApolloUrlAnalysisRequest`

```json
{
  "url": "https://app.apollo.io/#/people?personTitles[]=CEO&..."
}
```

**Response**: `ApolloUrlAnalysisResponse`

```json
{
  "url": "...",
  "url_structure": {
    "base_url": "https://app.apollo.io",
    "hash_path": "/people",
    "query_string": "...",
    "has_query_params": true
  },
  "categories": [...],
  "statistics": {
    "total_parameters": 10,
    "total_parameter_values": 15,
    "categories_used": 5,
    "categories": [...]
  },
  "raw_parameters": {...}
}
```

#### POST `/contacts`

**Description**: Search contacts using Apollo.io URL parameters

**Headers**:

- `Authorization: Bearer <token>` (required)

**Body**: `ApolloUrlAnalysisRequest`

```json
{
  "url": "https://app.apollo.io/#/people?..."
}
```

**Query Parameters**:

- `limit` (int, optional, ge=1): Maximum number of results
- `offset` (int, optional, ge=0): Starting offset
- `cursor` (string, optional): Cursor token
- `view` (string, optional): "simple" for ContactSimpleItem, otherwise ContactListItem
- `include_company_name` (string, optional): Include contacts whose company name matches
- `exclude_company_name` (list[str], optional): Exclude contacts whose company name matches
- `include_domain_list` (list[str], optional): Include contacts whose company domain matches
- `exclude_domain_list` (list[str], optional): Exclude contacts whose company domain matches

**Response**: `ApolloContactsSearchResponse[ContactListItem | ContactSimpleItem]`

```json
{
  "next": "http://...",
  "previous": "http://...",
  "results": [...],
  "apollo_url": "...",
  "mapping_summary": {
    "total_apollo_parameters": 10,
    "mapped_parameters": 8,
    "unmapped_parameters": 2,
    "mapped_parameter_names": [...],
    "unmapped_parameter_names": [...]
  },
  "unmapped_categories": [...]
}
```

#### POST `/contacts/count`

**Description**: Count contacts matching Apollo.io URL parameters

**Headers**:

- `Authorization: Bearer <token>` (required)

**Body**: `ApolloUrlAnalysisRequest`

**Query Parameters**:

- `include_company_name` (string, optional)
- `exclude_company_name` (list[str], optional)
- `include_domain_list` (list[str], optional)
- `exclude_domain_list` (list[str], optional)

**Response**: `CountResponse`

#### POST `/contacts/count/uuids`

**Description**: Get contact UUIDs matching Apollo.io URL parameters

**Headers**:

- `Authorization: Bearer <token>` (required)

**Body**: `ApolloUrlAnalysisRequest`

**Query Parameters**:

- `limit` (int, optional, ge=1)
- `include_company_name` (string, optional)
- `exclude_company_name` (list[str], optional)
- `include_domain_list` (list[str], optional)
- `exclude_domain_list` (list[str], optional)

**Response**: `UuidListResponse`

---

### Exports Endpoints

Base URL: `/api/v2/exports`

#### POST `/contacts/export`

**Description**: Create CSV export of selected contacts

**Headers**:

- `Authorization: Bearer <token>` (required)

**Body**: `ContactExportRequest`

```json
{
  "contact_uuids": ["uuid1", "uuid2", ...]
}
```

**Response**: `ContactExportResponse` (201 Created)

```json
{
  "export_id": "export-uuid",
  "download_url": "http://...?token=...",
  "expires_at": "2024-01-02T00:00:00Z",
  "contact_count": 100,
  "status": "completed"
}
```

#### POST `/companies/export`

**Description**: Create CSV export of selected companies

**Headers**:

- `Authorization: Bearer <token>` (required)

**Body**: `CompanyExportRequest`

```json
{
  "company_uuids": ["uuid1", "uuid2", ...]
}
```

**Response**: `CompanyExportResponse` (201 Created)

#### GET `/`

**Description**: List all exports for current user

**Headers**:

- `Authorization: Bearer <token>` (required)

**Response**: `ExportListResponse`

```json
{
  "exports": [...],
  "total": 5
}
```

#### GET `/{export_id}/download`

**Description**: Download export CSV file

**Headers**:

- `Authorization: Bearer <token>` (required)

**Path Parameters**:

- `export_id` (string, required)

**Query Parameters**:

- `token` (string, required): Signed URL token for authentication

**Response**: File download (CSV)

#### DELETE `/files`

**Description**: Delete all CSV files (admin only)

**Headers**:

- `Authorization: Bearer <token>` (required, admin)

**Response**:

```json
{
  "message": "CSV files deleted successfully",
  "deleted_count": 10
}
```

---

## WebSocket Endpoints

All WebSocket endpoints require authentication via query parameter:

- Connection URL: `ws://host:port/path?token=<jwt_token>`
- Token must be a valid access token from login/register endpoints

### Contacts WebSocket

Base URL: `ws://host:port/api/v1/contacts/ws`

**Connection**: `ws://host:port/api/v1/contacts/ws?token=<jwt_token>`

**Supported Actions** (22 total):

#### Main Contact Operations (5):

1. **list_contacts** - List contacts with filtering/pagination
2. **get_contact** - Retrieve single contact by UUID
3. **count_contacts** - Get contact count
4. **get_contact_uuids** - Get contact UUIDs
5. **create_contact** - Create new contact (admin only, requires write_key)

#### Field-Specific Endpoints (13):

6. **get_titles** - List titles
7. **get_companies** - List companies
8. **get_industries** - List industries
9. **get_keywords** - List keywords
10. **get_technologies** - List technologies
11. **get_company_addresses** - List company addresses
12. **get_contact_addresses** - List contact addresses

#### Import Operations (4):

13. **get_import_info** - Get import information
14. **upload_contacts_csv** - Upload CSV for import (admin only)
15. **get_import_status** - Get import job status
16. **get_import_errors** - Get import errors

**Request Format**:

```json
{
  "action": "list_contacts",
  "request_id": "unique-request-id",
  "data": {
    // Action-specific data matching REST API parameters
  }
}
```

**Response Format**:

```json
{
  "request_id": "unique-request-id",
  "action": "list_contacts",
  "status": "success",
  "data": {
    // Response data
  },
  "error": null
}
```

**Error Response Format**:

```json
{
  "request_id": "unique-request-id",
  "action": "list_contacts",
  "status": "error",
  "data": null,
  "error": {
    "message": "Error message",
    "code": "error_code"
  }
}
```

---

### Companies WebSocket

Base URL: `ws://host:port/api/v1/companies/ws`

**Connection**: `ws://host:port/api/v1/companies/ws?token=<jwt_token>`

**Supported Actions** (28 total):

#### Main Company Operations (7):

1. **list_companies** - List companies with filtering/pagination
2. **get_company** - Retrieve single company by UUID
3. **count_companies** - Get company count
4. **get_company_uuids** - Get company UUIDs
5. **create_company** - Create new company (admin only, requires write_key)
6. **update_company** - Update company (admin only, requires write_key)
7. **delete_company** - Delete company (admin only, requires write_key)

#### Company Attribute Lookups (8):

8. **list_company_names** - List company names
9. **list_industries** - List industries
10. **list_keywords** - List keywords
11. **list_technologies** - List technologies
12. **list_company_cities** - List company cities
13. **list_company_states** - List company states
14. **list_company_countries** - List company countries
15. **list_company_addresses** - List company addresses

#### Company Contact Operations (13):

16. **list_company_contacts** - List contacts for a company
17. **count_company_contacts** - Count contacts for a company
18. **get_company_contact_uuids** - Get contact UUIDs for a company
19. **list_company_contact_first_names** - List first names
20. **list_company_contact_last_names** - List last names
21. **list_company_contact_titles** - List titles
22. **list_company_contact_seniorities** - List seniorities
23. **list_company_contact_departments** - List departments
24. **list_company_contact_email_statuses** - List email statuses

**Request/Response Format**: Same as Contacts WebSocket

---

### Apollo WebSocket

Base URL: `ws://host:port/api/v2/apollo/ws`

**Connection**: `ws://host:port/api/v2/apollo/ws?token=<jwt_token>`

**Supported Actions** (4 total):

1. **analyze** - Analyze Apollo.io URL
2. **search_contacts** - Search contacts using Apollo URL parameters
3. **count_contacts** - Count contacts matching Apollo URL parameters
4. **get_uuids** - Get contact UUIDs matching Apollo URL parameters

**Request Format**:

```json
{
  "action": "analyze",
  "request_id": "unique-request-id",
  "data": {
    "url": "https://app.apollo.io/#/people?..."
    // Additional action-specific data
  }
}
```

**Response Format**: Same as Contacts WebSocket

---

## Common Schemas

### ContactFilterParams

All fields are optional. Used for filtering contacts.

**String Filters**:

- `first_name` (string): Case-insensitive substring match
- `last_name` (string): Case-insensitive substring match
- `title` (string): Case-insensitive substring match
- `seniority` (string): Case-insensitive substring match
- `department` (string): Substring match in departments array
- `email_status` (string): Case-insensitive substring match
- `email` (string): Case-insensitive substring match
- `company` (string): Case-insensitive substring match against Company.name
- `include_company_name` (string): Case-insensitive substring match (inclusion)
- `exclude_company_name` (list[string]): Exclude matching company names
- `company_name_for_emails` (string): Case-insensitive substring match
- `company_location` (string): Company text-search column
- `contact_location` (string): Contact text-search column
- `technologies` (string): Substring match in technologies array
- `technologies_uids` (string): Technology UIDs substring match
- `keywords` (string): Substring match in keywords array
- `keywords_and` (string): Keywords with AND logic
- `industries` (string): Substring match in industries array
- `search` (string): General-purpose search term
- `city` (string): Substring match against ContactMetadata.city
- `state` (string): Substring match against ContactMetadata.state
- `country` (string): Substring match against ContactMetadata.country
- `company_address` (string): Substring match against Company.text_search
- `company_city` (string): Substring match against CompanyMetadata.city
- `company_state` (string): Substring match against CompanyMetadata.state
- `company_country` (string): Substring match against CompanyMetadata.country
- `company_phone` (string): Substring match against CompanyMetadata.phone_number
- `person_linkedin_url` (string): Substring match
- `website` (string): Substring match
- `company_linkedin_url` (string): Substring match
- `facebook_url` (string): Substring match
- `twitter_url` (string): Substring match
- `stage` (string): Substring match
- `work_direct_phone` (string): Substring match
- `home_phone` (string): Substring match
- `mobile_phone` (string): Substring match
- `corporate_phone` (string): Substring match
- `other_phone` (string): Substring match

**Numeric Filters**:

- `employees_count` (int, ge=0): Exact match
- `employees_min` (int, ge=0): Lower bound
- `employees_max` (int, ge=0): Upper bound
- `annual_revenue` (int, ge=0): Exact match
- `annual_revenue_min` (int, ge=0): Lower bound
- `annual_revenue_max` (int, ge=0): Upper bound
- `total_funding` (int, ge=0): Exact match
- `total_funding_min` (int, ge=0): Lower bound
- `total_funding_max` (int, ge=0): Upper bound
- `latest_funding_amount_min` (int, ge=0): Lower bound
- `latest_funding_amount_max` (int, ge=0): Upper bound

**List Filters**:

- `exclude_company_ids` (list[string]): Exclude company UUIDs
- `exclude_titles` (list[string]): Exclude titles
- `exclude_company_locations` (list[string]): Exclude company locations
- `exclude_contact_locations` (list[string]): Exclude contact locations
- `exclude_seniorities` (list[string]): Exclude seniorities
- `exclude_departments` (list[string]): Exclude departments
- `exclude_technologies` (list[string]): Exclude technologies
- `exclude_keywords` (list[string]): Exclude keywords
- `exclude_industries` (list[string]): Exclude industries
- `include_domain_list` (list[string]): Include company domains
- `exclude_domain_list` (list[string]): Exclude company domains
- `keyword_search_fields` (list[string]): Fields for keyword search
- `keyword_exclude_fields` (list[string]): Fields to exclude from keyword search

**Pagination/Ordering**:

- `ordering` (string): Ordering key (see repository ordering_map)
- `page` (int, ge=1): 1-indexed page number
- `page_size` (int, ge=1): Page size override
- `cursor` (string): Opaque cursor token
- `distinct` (bool, default=false): Request distinct contacts

**Date Filters**:

- `created_at_after` (datetime): Filter contacts created after (ISO timestamp)
- `created_at_before` (datetime): Filter contacts created before (ISO timestamp)
- `updated_at_after` (datetime): Filter contacts updated after (ISO timestamp)
- `updated_at_before` (datetime): Filter contacts updated before (ISO timestamp)

### CompanyFilterParams

Similar structure to ContactFilterParams but for companies. Key differences:

- No contact-specific fields
- Includes: `name`, `employees_count`, `industries`, `keywords`, `technologies`, `address`, etc.
- Exclusion filters: `exclude_industries`, `exclude_keywords`, `exclude_technologies`, `exclude_locations`

### CompanyContactFilterParams

Filter parameters for contacts within a specific company context:

- Only contact-specific filters (no company filters)
- Includes: `first_name`, `last_name`, `title`, `seniority`, `department`, `email_status`, etc.
- Exclusion filters: `exclude_titles`, `exclude_contact_locations`, `exclude_seniorities`, `exclude_departments`

### AttributeListParams

Used for attribute list endpoints:

- `limit` (int, optional, ge=1): Maximum number of results
- `offset` (int, optional, ge=0, default=0): Starting offset
- `distinct` (bool, optional, default=false): Return distinct values
- `ordering` (string, optional): Order by field
- `search` (string, optional): Search term

### ContactCreate

All fields optional except as noted:

- `uuid` (string, optional): Contact UUID (auto-generated if not provided)
- `first_name` (string, optional)
- `last_name` (string, optional)
- `company_id` (string, optional): Company UUID
- `email` (string, optional)
- `title` (string, optional)
- `departments` (list[string], optional)
- `mobile_phone` (string, optional)
- `email_status` (string, optional)
- `text_search` (string, optional)
- `seniority` (string, optional)

### CompanyCreate

All fields optional:

- `uuid` (string, optional)
- `name` (string, optional)
- `employees_count` (int, optional)
- `industries` (list[string], optional)
- `keywords` (list[string], optional)
- `address` (string, optional)
- `annual_revenue` (int, optional)
- `total_funding` (int, optional)
- `technologies` (list[string], optional)
- `text_search` (string, optional)

### CompanyUpdate

Same fields as CompanyCreate (all optional, partial update)

---

## Notes

1. **Pagination**: 
   - Use `limit` and `offset` for basic pagination
   - Use `cursor` for cursor-based pagination (more efficient)
   - Use `page` and `page_size` for page-based pagination
   - Priority: cursor > explicit offset > page calculation

2. **Authentication**:
   - Most endpoints require Bearer token authentication
   - Admin-only endpoints require user role = "Admin"
   - Write operations require additional write keys in headers

3. **WebSocket**:
   - All WebSocket endpoints use the same request/response format
   - Actions match REST API functionality
   - Single persistent connection can handle multiple requests

4. **Filter Parameters**:
   - All filter parameters support case-insensitive matching where applicable
   - List parameters can be provided as comma-separated strings or arrays
   - Date filters accept ISO 8601 format timestamps

5. **Response Formats**:
   - Success responses return 200 OK (or 201 Created for POST)
   - Error responses return appropriate HTTP status codes with error details
   - WebSocket responses include status field ("success" or "error")

