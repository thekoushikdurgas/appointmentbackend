# Export API Documentation

Complete API documentation for contact and company export endpoints, including CSV generation, export listing, and secure download via signed URLs.

**Related Documentation:**
- [Contacts API](./contacts.md) - For contact management and filtering
- [Companies API](./company.md) - For company management and filtering
- [User API](./user.md) - For authentication endpoints

## Table of Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [CORS Testing](#cors-testing)
- [Export Endpoints](#export-endpoints)
  - [POST /api/v2/exports/contacts/export](#post-apiv2exportscontactsexport---create-contact-export)
  - [GET /api/v2/exports/{export_id}/download](#get-apiv2exportsexport_iddownload---download-export)
  - [POST /api/v2/exports/companies/export](#post-apiv2exportscompaniesexport---create-company-export)
  - [GET /api/v2/exports/](#get-apiv2exports---list-exports)
  - [DELETE /api/v2/exports/files](#delete-apiv2exportsfiles---delete-all-csv-files-admin-only)
- [Export Type Values](#export-type-values)
- [Export Status Values](#export-status-values)
- [Security Considerations](#security-considerations)
- [Example Workflows](#example-workflows)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Best Practices](#best-practices)

---

## Base URL

For production, use:

```txt
http://54.87.173.234:8000
```

**API Version:** All export endpoints are under `/api/v2/exports/`

## Authentication

All export endpoints require JWT authentication via the `Authorization` header:

```txt
Authorization: Bearer <access_token>
```

Tokens are obtained through the login or register endpoints.

---

## CORS Testing

All endpoints support CORS (Cross-Origin Resource Sharing) for browser-based requests. For testing CORS headers, you can include an optional `Origin` header in your requests:

**Optional Header:**

- `Origin: http://localhost:3000` (or your frontend origin)

**Expected CORS Response Headers:**

- `Access-Control-Allow-Origin: http://localhost:3000` (matches the Origin header)
- `Access-Control-Allow-Credentials: true`
- `Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS, PATCH`
- `Access-Control-Allow-Headers: *`
- `Access-Control-Max-Age: 3600`

**Note:** The Origin header is optional and only needed when testing CORS behavior. The API automatically handles CORS preflight (OPTIONS) requests.

---

## Export Endpoints

### POST /api/v2/exports/contacts/export - Create Contact Export

Create a CSV export of selected contacts. Accepts a list of contact UUIDs and generates a CSV file containing all contact, company, contact metadata, and company metadata fields. Returns a signed temporary download URL that expires after 24 hours.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Request Body:**

```json
{
  "contact_uuids": [
    "abc123-def456-ghi789",
    "xyz789-uvw456-rst123"
  ]
}
```

**Request Body Fields:**

- `contact_uuids` (array[string], required, min: 1): List of contact UUIDs to export. At least one UUID is required.

**Response:**

**Success (201 Created):**

```json
{
  "export_id": "f4b8c3f5-1111-4f9b-aaaa-123456789abc",
  "download_url": "http://54.87.173.234:8000/api/v2/exports/f4b8c3f5-1111-4f9b-aaaa-123456789abc/download?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_at": "2024-12-20T10:30:00Z",
  "contact_count": 2,
  "status": "completed"
}
```

**Response Fields:**

- `export_id` (string, UUID): Unique identifier for the export
- `download_url` (string): Signed temporary download URL that expires after 24 hours. Includes the token as a query parameter.
- `expires_at` (datetime, ISO 8601): Timestamp when the download URL expires (24 hours from creation)
- `contact_count` (integer): Number of contacts included in the export
- `status` (string): Export status. Possible values: `pending`, `processing`, `completed`, `failed`

**Error (400 Bad Request) - No Contact UUIDs:**

```json
{
  "detail": "At least one contact UUID is required"
}
```

**Error (401 Unauthorized) - Missing Authentication:**

```json
{
  "detail": "Not authenticated"
}
```

**Error (500 Internal Server Error) - CSV Generation Failed:**

```json
{
  "detail": "Failed to generate CSV: <error_message>"
}
```

**Error (500 Internal Server Error) - Export Creation Failed:**

```json
{
  "detail": "Failed to create export"
}
```

**CSV Fields Included:**

The generated CSV file includes the following fields:

**Contact Fields:**

- `contact_uuid`: Contact UUID
- `contact_first_name`: Contact's first name
- `contact_last_name`: Contact's last name
- `contact_company_id`: UUID of the related company
- `contact_email`: Contact's email address
- `contact_title`: Contact's job title
- `contact_departments`: Comma-separated list of departments
- `contact_mobile_phone`: Contact's mobile phone number
- `contact_email_status`: Email verification status
- `contact_text_search`: Free-form search text (e.g., location information)
- `contact_seniority`: Contact's seniority level
- `contact_created_at`: Contact creation timestamp
- `contact_updated_at`: Contact last update timestamp

**Contact Metadata Fields:**

- `contact_metadata_linkedin_url`: LinkedIn profile URL
- `contact_metadata_facebook_url`: Facebook profile URL
- `contact_metadata_twitter_url`: Twitter profile URL
- `contact_metadata_website`: Personal website URL
- `contact_metadata_work_direct_phone`: Work direct phone number
- `contact_metadata_home_phone`: Home phone number
- `contact_metadata_other_phone`: Other phone number
- `contact_metadata_city`: City
- `contact_metadata_state`: State/Province
- `contact_metadata_country`: Country
- `contact_metadata_stage`: Contact stage/status

**Company Fields:**

- `company_uuid`: Company UUID
- `company_name`: Company name
- `company_employees_count`: Number of employees
- `company_industries`: Comma-separated list of industries
- `company_keywords`: Comma-separated list of keywords
- `company_address`: Company address
- `company_annual_revenue`: Annual revenue in integer dollars
- `company_total_funding`: Total funding in integer dollars
- `company_technologies`: Comma-separated list of technologies
- `company_text_search`: Free-form search text (e.g., location information)
- `company_created_at`: Company creation timestamp
- `company_updated_at`: Company last update timestamp

**Company Metadata Fields:**

- `company_metadata_linkedin_url`: Company LinkedIn URL
- `company_metadata_facebook_url`: Company Facebook URL
- `company_metadata_twitter_url`: Company Twitter URL
- `company_metadata_website`: Company website URL
- `company_metadata_company_name_for_emails`: Company name used for emails
- `company_metadata_phone_number`: Company phone number
- `company_metadata_latest_funding`: Latest funding round information
- `company_metadata_latest_funding_amount`: Latest funding amount in integer dollars
- `company_metadata_last_raised_at`: Last funding date
- `company_metadata_city`: Company city
- `company_metadata_state`: Company state/province
- `company_metadata_country`: Company country

**Notes:**

- The export is processed synchronously and returns immediately with a download URL
- The download URL expires after 24 hours from creation
- If a contact UUID doesn't exist, it will be skipped (not cause the entire export to fail)
- Array fields (departments, industries, keywords, technologies) are formatted as comma-separated values in the CSV
- All timestamps are in ISO 8601 format (UTC)
- Missing or null values are represented as empty strings in the CSV

---

### GET /api/v2/exports/{export_id}/download - Download Export

Download a CSV export file using a signed URL. The token must be valid and the export must belong to the requesting user. The export must not have expired.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Accept: text/csv` (optional, for CSV file download)

**Path Parameters:**

- `export_id` (string, UUID, required): Export ID

**Query Parameters:**

- `token` (string, required): Signed URL token for authentication. This token is included in the `download_url` returned by the Create Contact Export endpoint.

**Example Request:**

```txt
GET /api/v2/exports/f4b8c3f5-1111-4f9b-aaaa-123456789abc/download?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Authorization: Bearer <access_token>
```

**Response:**

**Success (200 OK):**

The response is a CSV file with the following headers:

- `Content-Type: text/csv`
- `Content-Disposition: attachment; filename="export_<export_id>.csv"`

The response body contains the CSV file content.

**Error (400 Bad Request) - Export Not Ready:**

```json
{
  "detail": "Export is not ready (status: processing)"
}
```

**Error (401 Unauthorized) - Invalid Token:**

```json
{
  "detail": "Invalid or expired download token"
}
```

**Error (403 Forbidden) - Token Mismatch:**

```json
{
  "detail": "Token does not match export or user"
}
```

**Error (404 Not Found) - Export Not Found:**

```json
{
  "detail": "Export not found or access denied"
}
```

**Error (404 Not Found) - File Not Found:**

```json
{
  "detail": "Export file not found"
}
```

**Error (410 Gone) - Export Expired:**

```json
{
  "detail": "Export has expired"
}
```

**Error (500 Internal Server Error) - File Path Missing:**

```json
{
  "detail": "Export file not found"
}
```

**Notes:**

- The download URL expires after 24 hours from creation
- Only the user who created the export can download it
- The response is a CSV file with `Content-Disposition` header for file download
- Use the full `download_url` from the Create Contact Export response, which includes the token as a query parameter
- The signed URL token is validated to ensure it matches the export ID and user ID
- The export must have status `completed` to be downloadable
- If the export has expired, a 410 Gone response is returned

---

### POST /api/v2/exports/companies/export - Create Company Export

Create a CSV export of selected companies. Accepts a list of company UUIDs and generates a CSV file containing all company and company metadata fields. Returns a signed temporary download URL that expires after 24 hours.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Request Body:**

```json
{
  "company_uuids": [
    "abc123-def456-ghi789",
    "xyz789-uvw456-rst123"
  ]
}
```

**Request Body Fields:**

- `company_uuids` (array[string], required, min: 1): List of company UUIDs to export. At least one UUID is required.

**Response:**

**Success (201 Created):**

```json
{
  "export_id": "f4b8c3f5-2222-4f9b-bbbb-123456789abc",
  "download_url": "http://54.87.173.234:8000/api/v2/exports/f4b8c3f5-2222-4f9b-bbbb-123456789abc/download?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_at": "2024-12-20T10:30:00Z",
  "company_count": 2,
  "status": "completed"
}
```

**Response Fields:**

- `export_id` (string, UUID): Unique identifier for the export
- `download_url` (string): Signed temporary download URL that expires after 24 hours. Includes the token as a query parameter.
- `expires_at` (datetime, ISO 8601): Timestamp when the download URL expires (24 hours from creation)
- `company_count` (integer): Number of companies included in the export
- `status` (string): Export status. Possible values: `pending`, `processing`, `completed`, `failed`

**Error (400 Bad Request) - No Company UUIDs:**

```json
{
  "detail": "At least one company UUID is required"
}
```

**Error (401 Unauthorized) - Missing Authentication:**

```json
{
  "detail": "Not authenticated"
}
```

**Error (500 Internal Server Error) - CSV Generation Failed:**

```json
{
  "detail": "Failed to generate CSV: <error_message>"
}
```

**CSV Fields Included:**

The generated CSV file includes the following fields:

**Company Fields:**

- `company_uuid`: Company UUID
- `company_name`: Company name
- `company_employees_count`: Number of employees
- `company_industries`: Comma-separated list of industries
- `company_keywords`: Comma-separated list of keywords
- `company_address`: Company address
- `company_annual_revenue`: Annual revenue in integer dollars
- `company_total_funding`: Total funding in integer dollars
- `company_technologies`: Comma-separated list of technologies
- `company_text_search`: Free-form search text (e.g., location information)
- `company_created_at`: Company creation timestamp
- `company_updated_at`: Company last update timestamp

**Company Metadata Fields:**

- `company_metadata_linkedin_url`: Company LinkedIn URL
- `company_metadata_facebook_url`: Company Facebook URL
- `company_metadata_twitter_url`: Company Twitter URL
- `company_metadata_website`: Company website URL
- `company_metadata_company_name_for_emails`: Company name used for emails
- `company_metadata_phone_number`: Company phone number
- `company_metadata_latest_funding`: Latest funding round information
- `company_metadata_latest_funding_amount`: Latest funding amount in integer dollars
- `company_metadata_last_raised_at`: Last funding date
- `company_metadata_city`: Company city
- `company_metadata_state`: Company state/province
- `company_metadata_country`: Company country

**Notes:**

- The export is processed synchronously and returns immediately with a download URL
- The download URL expires after 24 hours from creation
- If a company UUID doesn't exist, it will be skipped (not cause the entire export to fail)
- Array fields (industries, keywords, technologies) are formatted as comma-separated values in the CSV
- All timestamps are in ISO 8601 format (UTC)
- Missing or null values are represented as empty strings in the CSV

---

### GET /api/v2/exports/ - List Exports

List all exports for the current user. Returns all exports created by the authenticated user, ordered by creation date (newest first). Includes both contact and company exports.

**Headers:**

- `Authorization: Bearer <access_token>` (required)

**Response:**

**Success (200 OK):**

```json
{
  "exports": [
    {
      "export_id": "f4b8c3f5-1111-4f9b-aaaa-123456789abc",
      "user_id": "user-123",
      "export_type": "contacts",
      "file_path": "/path/to/export.csv",
      "file_name": "export_f4b8c3f5-1111-4f9b-aaaa-123456789abc.csv",
      "contact_count": 2,
      "contact_uuids": ["abc123-def456-ghi789", "xyz789-uvw456-rst123"],
      "company_count": 0,
      "company_uuids": null,
      "status": "completed",
      "created_at": "2024-12-19T10:30:00Z",
      "expires_at": "2024-12-20T10:30:00Z",
      "download_url": "http://54.87.173.234:8000/api/v2/exports/f4b8c3f5-1111-4f9b-aaaa-123456789abc/download?token=..."
    },
    {
      "export_id": "f4b8c3f5-2222-4f9b-bbbb-123456789abc",
      "user_id": "user-123",
      "export_type": "companies",
      "file_path": "/path/to/export.csv",
      "file_name": "export_f4b8c3f5-2222-4f9b-bbbb-123456789abc.csv",
      "contact_count": 0,
      "contact_uuids": null,
      "company_count": 3,
      "company_uuids": ["def456-ghi789-jkl012", "mno345-pqr678-stu901"],
      "status": "completed",
      "created_at": "2024-12-18T15:20:00Z",
      "expires_at": "2024-12-19T15:20:00Z",
      "download_url": "http://54.87.173.234:8000/api/v2/exports/f4b8c3f5-2222-4f9b-bbbb-123456789abc/download?token=..."
    }
  ],
  "total": 2
}
```

**Response Fields:**

- `exports` (array): List of export records, ordered by `created_at` descending (newest first)
- `total` (integer): Total number of exports for the user

**Each export object contains:**

- `export_id` (string, UUID): Unique identifier for the export
- `user_id` (string): ID of the user who created the export
- `export_type` (string): Type of export - either `"contacts"` or `"companies"`
- `file_path` (string, optional): Path to the CSV file on the server
- `file_name` (string, optional): Name of the CSV file
- `contact_count` (integer): Number of contacts in the export (0 for company exports)
- `contact_uuids` (array[string], optional): List of contact UUIDs (null for company exports)
- `company_count` (integer): Number of companies in the export (0 for contact exports)
- `company_uuids` (array[string], optional): List of company UUIDs (null for contact exports)
- `status` (string): Export status - `pending`, `completed`, or `failed`
- `created_at` (datetime, ISO 8601): When the export was created
- `expires_at` (datetime, ISO 8601, optional): When the download URL expires
- `download_url` (string, optional): Signed download URL (null if export is not completed)

**Error (401 Unauthorized) - Missing Authentication:**

```json
{
  "detail": "Not authenticated"
}
```

**Error (500 Internal Server Error) - Failed to List Exports:**

```json
{
  "detail": "Failed to list exports"
}
```

**Notes:**

- Returns all exports for the authenticated user, regardless of export type
- Exports are ordered by creation date, newest first
- Only exports created by the current user are returned
- Expired exports are still included in the list (check `expires_at` to determine if download is still available)

---

### DELETE /api/v2/exports/files - Delete All CSV Files (Admin Only)

Delete all CSV files from the exports directory. This endpoint is restricted to admin users only and deletes all CSV files system-wide. Optionally cleans up expired export records from the database.

**Headers:**

- `Authorization: Bearer <access_token>` (required, admin role)

**Response:**

**Success (200 OK):**

```json
{
  "message": "CSV files deleted successfully",
  "deleted_count": 15
}
```

**Response Fields:**

- `message` (string): Success message
- `deleted_count` (integer): Number of CSV files deleted

**Error (401 Unauthorized) - Missing Authentication:**

```json
{
  "detail": "Not authenticated"
}
```

**Error (403 Forbidden) - Not Admin:**

```json
{
  "detail": "You do not have permission to perform this action. Admin role required."
}
```

**Error (500 Internal Server Error) - Failed to Delete Files:**

```json
{
  "detail": "Failed to delete CSV files"
}
```

**Notes:**

- This endpoint requires admin authentication
- Deletes all CSV files from the exports directory, regardless of ownership
- Optionally cleans up expired export records from the database
- Use with caution as this operation cannot be undone
- Individual file deletion failures are logged but do not stop the overall operation

---

## Export Type Values

The export type field can have the following values:

- `contacts`: Export contains contact data
- `companies`: Export contains company data

## Export Status Values

The export status field can have the following values:

- `pending`: Export is queued but not yet started
- `completed`: Export is ready for download
- `failed`: Export generation failed

---

## Security Considerations

1. **Signed URLs**: Download URLs are signed with a token that includes the export ID and user ID. This ensures that only the user who created the export can download it.

2. **Token Expiration**: Download tokens expire after 24 hours. After expiration, a new export must be created to generate a new download URL.

3. **User Verification**: The API verifies that the token matches both the export ID and the authenticated user ID before allowing download.

4. **File Access**: Export files are stored in a secure location and are only accessible through the signed URL endpoint.

---

## Example Workflows

### Contact Export Workflow

**Step 1: Create Contact Export**

```bash
curl -X POST "http://54.87.173.234:8000/api/v2/exports/contacts/export" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "contact_uuids": [
      "abc123-def456-ghi789",
      "xyz789-uvw456-rst123"
    ]
  }'
```

**Response:**

```json
{
  "export_id": "f4b8c3f5-1111-4f9b-aaaa-123456789abc",
  "download_url": "http://54.87.173.234:8000/api/v2/exports/f4b8c3f5-1111-4f9b-aaaa-123456789abc/download?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_at": "2024-12-20T10:30:00Z",
  "contact_count": 2,
  "status": "completed"
}
```

**Step 2: Download Export**

```bash
curl -X GET "http://54.87.173.234:8000/api/v2/exports/f4b8c3f5-1111-4f9b-aaaa-123456789abc/download?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Authorization: Bearer <access_token>" \
  -H "Accept: text/csv" \
  -o export.csv
```

The CSV file will be downloaded to `export.csv`.

### Company Export Workflow

**Step 1: Create Company Export**

```bash
curl -X POST "http://54.87.173.234:8000/api/v2/exports/companies/export" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "company_uuids": [
      "def456-ghi789-jkl012",
      "mno345-pqr678-stu901"
    ]
  }'
```

**Response:**

```json
{
  "export_id": "f4b8c3f5-2222-4f9b-bbbb-123456789abc",
  "download_url": "http://54.87.173.234:8000/api/v2/exports/f4b8c3f5-2222-4f9b-bbbb-123456789abc/download?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_at": "2024-12-20T10:30:00Z",
  "company_count": 2,
  "status": "completed"
}
```

**Step 2: Download Export**

```bash
curl -X GET "http://54.87.173.234:8000/api/v2/exports/f4b8c3f5-2222-4f9b-bbbb-123456789abc/download?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Authorization: Bearer <access_token>" \
  -H "Accept: text/csv" \
  -o company_export.csv
```

### List Exports Workflow

**List All Exports**

```bash
curl -X GET "http://54.87.173.234:8000/api/v2/exports/" \
  -H "Authorization: Bearer <access_token>"
```

**Response:**

```json
{
  "exports": [
    {
      "export_id": "f4b8c3f5-1111-4f9b-aaaa-123456789abc",
      "user_id": "user-123",
      "export_type": "contacts",
      "contact_count": 2,
      "company_count": 0,
      "status": "completed",
      "created_at": "2024-12-19T10:30:00Z",
      "expires_at": "2024-12-20T10:30:00Z",
      "download_url": "http://54.87.173.234:8000/api/v2/exports/f4b8c3f5-1111-4f9b-aaaa-123456789abc/download?token=..."
    }
  ],
  "total": 1
}
```

---

## Error Handling

All endpoints return standard HTTP status codes:

- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request data or export not ready
- `401 Unauthorized`: Authentication required or invalid token
- `403 Forbidden`: Token does not match export or user
- `404 Not Found`: Export or file not found
- `410 Gone`: Export has expired
- `500 Internal Server Error`: Server error during export creation or CSV generation

Error responses follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

---

## Rate Limiting

Currently, there are no rate limits on export endpoints. However, exports are processed synchronously, so large exports may take longer to complete. Consider implementing client-side rate limiting for production use.

---

## Best Practices

1. **Store Download URLs**: Save the `download_url` from the create response immediately, as it cannot be regenerated without creating a new export.

2. **Handle Expiration**: Check the `expires_at` timestamp and download the file before it expires. If expired, create a new export.

3. **Error Handling**: Implement proper error handling for failed exports. Check the `status` field and handle `failed` status appropriately.

4. **Large Exports**: For large numbers of contacts, consider batching exports or implementing pagination on the client side.

5. **File Storage**: Downloaded CSV files should be stored securely on the client side if needed for later use, as the download URL expires after 24 hours.
