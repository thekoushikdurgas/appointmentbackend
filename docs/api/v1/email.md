# Email Finder API Documentation

Complete API documentation for email finder operations, including searching for contact emails by first name, last name, and company domain.

**Related Documentation:**

- [Contacts API](./contacts.md) - For general contact management endpoints
- [Companies API](./company.md) - For general company management endpoints
- [LinkedIn API](./linkdin.md) - For LinkedIn URL-based operations
- [User API](./user.md) - For authentication endpoints

## Table of Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [Email Finder Endpoints](#email-finder-endpoints)
  - [GET /api/v3/email/finder/](#get-apiv3emailfinder---find-emails-by-name-and-domain)
- [Email Export Endpoints](#email-export-endpoints)
  - [POST /api/v3/email/export](#post-apiv3emailexport---export-emails-to-csv)
  - [POST /api/v3/email/single/](#post-apiv3emailsingle---get-single-email)
- [Email Verifier Endpoints](#email-verifier-endpoints)
  - [POST /api/v3/email/bulk/verifier/](#post-apiv3emailbulkverifier---verify-multiple-emails)
  - [POST /api/v3/email/single/verifier/](#post-apiv3emailsingleverifier---verify-single-email)
  - [POST /api/v3/email/verifier/](#post-apiv3emailverifier---verify-emails-synchronously)
  - [POST /api/v3/email/verifier/single/](#post-apiv3emailverifiersingle---find-single-valid-email)
- [Bulk Mail Verifier Management Endpoints](#bulk-mail-verifier-management-endpoints)
  - [GET /api/v3/email/bulk/download/{file_type}/{slug}/](#get-apiv3emailbulkdownloadfile_typeslug---download-bulk-mail-verifier-files)
- [Response Schemas](#response-schemas)
- [Use Cases](#use-cases)
- [Error Handling](#error-handling)

---

## Base URL

For production, use:

```txt
http://34.229.94.175:8000
```

**API Version:** All email finder endpoints are under `/api/v3/email/`

## Authentication

All email finder endpoints require JWT authentication via the `Authorization` header:

```txt
Authorization: Bearer <access_token>
```

Tokens are obtained through the login or register endpoints.

## Role-Based Access Control

All email finder endpoints are accessible to all authenticated users regardless of role:

- **Free Users (`FreeUser`)**: ✅ Full access to all email finder endpoints
- **Pro Users (`ProUser`)**: ✅ Full access to all email finder endpoints
- **Admin (`Admin`)**: ✅ Full access to all email finder endpoints (unlimited credits)
- **Super Admin (`SuperAdmin`)**: ✅ Full access to all email finder endpoints (unlimited credits)

**Note:** There are no role-based restrictions on email finder functionality. All authenticated users can find and verify emails.

## Credit Deduction

Credits are automatically deducted after successful operations:

- **SuperAdmin & Admin**: Unlimited credits (no deduction)
- **FreeUser & ProUser**: Credits are deducted after successful operations:
  - **Search operations**: 1 credit per search request
  - **Export operations**: 1 credit per contact exported

**Important Notes:**

- Credits are deducted **after** successful operation completion
- Negative credit balances are allowed (credits can go below 0)
- Failed operations do not deduct credits
- Export credits are deducted when the export is queued (1 credit per contact in the request)

---

## Email Finder Endpoints

### GET /api/v3/email/finder/ - Find Emails by Name and Domain

Find contact emails by first name, last name, and company domain. This endpoint searches for contacts matching the provided name criteria whose company website domain matches the provided domain/website. Only returns contacts that have email addresses.

**Credit Deduction:** 1 credit is deducted after a successful search (FreeUser and ProUser only). SuperAdmin and Admin have unlimited credits.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Accept: application/json`

**Query Parameters:**

- `first_name` (string, required): Contact first name (case-insensitive partial match)
- `last_name` (string, required): Contact last name (case-insensitive partial match)
- `domain` (string, optional): Company domain or website URL. Can use `website` parameter instead.
- `website` (string, optional): Company website URL (alias for `domain` parameter)

**Domain Parameter Formats:**

The `domain` or `website` parameter accepts various formats:

- Full URL: `https://www.example.com` or `http://example.com`
- Domain with www: `www.example.com`
- Plain domain: `example.com`

The endpoint automatically extracts and normalizes the domain from the input, removing:

- Protocols (`http://`, `https://`)
- `www.` prefix
- Port numbers
- Paths and query strings

**Example Requests:**

```bash
# Using domain parameter
GET /api/v3/email/finder/?first_name=John&last_name=Doe&domain=example.com
Authorization: Bearer <access_token>

# Using website parameter with full URL
GET /api/v3/email/finder/?first_name=John&last_name=Doe&website=https://www.example.com
Authorization: Bearer <access_token>

# Using domain parameter with www
GET /api/v3/email/finder/?first_name=John&last_name=Doe&domain=www.example.com
Authorization: Bearer <access_token>
```

**Response:**

**Success (200 OK):**

```json
{
  "emails": [
    {
      "uuid": "abc123",
      "email": "john.doe@example.com"
    },
    {
      "uuid": "def456",
      "email": "jane.smith@example.com"
    }
  ],
  "total": 2
}
```

The response contains a simple list of email results, each with:

- `uuid` (string): Contact UUID
- `email` (string): Email address from Contact.email

**Error Responses:**

**400 Bad Request - Missing first_name:**

```json
{
  "detail": "first_name is required and cannot be empty"
}
```

**400 Bad Request - Missing last_name:**

```json
{
  "detail": "last_name is required and cannot be empty"
}
```

**400 Bad Request - Missing domain/website:**

```json
{
  "detail": "Either domain or website parameter is required"
}
```

**400 Bad Request - Invalid domain:**

```json
{
  "detail": "Could not extract valid domain from: invalid-domain"
}
```

**401 Unauthorized:**

```json
{
  "detail": "Not authenticated"
}
```

**404 Not Found - Company not found:**

```json
{
  "detail": "No companies found with domain: example.com"
}
```

This error occurs when no companies in the database match the provided domain. The domain has been successfully extracted and validated, but no companies exist with that domain in the `companies_metadata` table.

**404 Not Found - Contact not found:**

```json
{
  "detail": "No contacts found with name 'John Doe' for companies with domain: example.com"
}
```

This error occurs when companies exist for the domain, but no contacts match the provided first name and last name criteria. The search was performed across all companies with the matching domain, but no contacts were found.

**500 Internal Server Error - General error:**

```json
{
  "detail": "Failed to find emails"
}
```

**Status Codes:**

- `200 OK`: Emails found successfully
- `400 Bad Request`: Invalid parameters (missing first_name, last_name, domain/website, or invalid domain format)
- `401 Unauthorized`: Authentication required
- `404 Not Found`: No companies found for the domain, or no contacts found matching the name criteria
- `500 Internal Server Error`: Server error occurred

---

## Email Export Endpoints

### POST /api/v3/email/export - Export Emails to CSV

Export emails for a list of contacts to CSV. Processes a list of contacts and attempts to find their email addresses using a two-step approach: first tries to find emails in the database using the email finder service, then falls back to email verification if not found.

**Credit Deduction:** Credits are deducted when the export is queued successfully. 1 credit is deducted per contact in the request (FreeUser and ProUser only). SuperAdmin and Admin have unlimited credits.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`
- `Accept: text/csv, application/json`

**Request Body (minimal example):**

```json
{
  "contacts": [
    {
      "first_name": "John",
      "last_name": "Doe",
      "domain": "amazon.com",
      "email": "john.doe@old-example.com"
    },
    {
      "first_name": "Jane",
      "last_name": "Smith",
      "website": "https://www.amazon.com"
    }
  ],
  "mapping": {
    "first_name": "first_name",
    "last_name": "last_name",
    "domain": "domain",
    "website": null,
    "email": "email"
  }
}
```

**Request Body (with full CSV context, e.g. Apollo file):**

```json
{
  "contacts": [
    {
      "first_name": "Phil",
      "last_name": "Denlinger",
      "website": "https://dcs-tech.com",
      "email": "phil.denlinger@dcs-tech.com"
    }
    // ...
  ],
  "mapping": {
    "first_name": "first_name",
    "last_name": "last_name",
    "domain": "website",
    "website": null,
    "email": "email"
  },
  "raw_headers": [
    "first_name",
    "last_name",
    "title",
    "company",
    "company_name_for_emails",
    "email",
    "email_status",
    "primary_email_catch_all_status",
    "seniority",
    "departments",
    "work_direct_phone",
    "home_phone",
    "mobile_phone",
    "corporate_phone",
    "other_phone",
    "stage",
    "employees",
    "industry",
    "keywords",
    "person_linkedin_url",
    "website",
    "company_linkedin_url",
    "facebook_url",
    "twitter_url",
    "city",
    "state",
    "country",
    "company_address",
    "company_city",
    "company_state",
    "company_country",
    "company_phone",
    "technologies",
    "annual_revenue",
    "total_funding",
    "latest_funding",
    "Latest_funding_amount",
    "last_raised_at"
  ],
  "rows": [
    {
      "first_name": "Phil",
      "last_name": "Denlinger",
      "title": "President, Owner",
      "company": "DCS Technologies",
      "company_name_for_emails": "DCS",
      "email": "phil.denlinger@dcs-tech.com",
      "email_status": "Verified",
      "primary_email_catch_all_status": "Not Catch-all",
      "seniority": "Owner",
      "departments": "",
      "work_direct_phone": "",
      "home_phone": "",
      "mobile_phone": "",
      "corporate_phone": "+1 937-743-4060",
      "other_phone": "",
      "stage": "Cold",
      "employees": "18",
      "industry": "information technology & services",
      "keywords": "...",
      "person_linkedin_url": "http://www.linkedin.com/in/phil-denlinger-a318b23b",
      "website": "https://dcs-tech.com",
      "company_linkedin_url": "http://www.linkedin.com/company/dcs-technologies-corp",
      "facebook_url": "https://facebook.com/pages/DCS-Technologies/216781388346711",
      "twitter_url": "",
      "city": "Miamisburg",
      "state": "Ohio",
      "country": "United States",
      "company_address": "6501 State Route 123, Franklin, Ohio, United States, 45005-4519",
      "company_city": "Franklin",
      "company_state": "Ohio",
      "company_country": "United States",
      "company_phone": "+1 937-743-4060",
      "technologies": "\"Outlook, Hubspot, DoubleClick, ...\"",
      "annual_revenue": "9427000",
      "total_funding": "",
      "latest_funding": "",
      "Latest_funding_amount": "",
      "last_raised_at": ""
    }
    // one entry per contact
  ]
}
```

**Request Fields:**

- `contacts` (array, required): List of contacts to export. Minimum: 1 contact.
  Each contact must have:
  - `first_name` (string, required): Contact first name
  - `last_name` (string, required): Contact last name
  - `domain` (string, optional): Company domain or website URL. Can use `website` parameter instead.
  - `website` (string, optional): Company website URL (alias for `domain` parameter)
  - `email` (string, optional): Existing email from the source data. When provided, the system will try to verify and reuse it before generating new emails.
- `mapping` (object, optional): Column mapping metadata from the original CSV, with keys:
  - `first_name`, `last_name`, `domain`, `website`, `email` (each value is the original CSV column name or `null`).
- `raw_headers` (array of strings, optional): Ordered list of all CSV headers from the original file. When present (for example, an Apollo CSV upload), the export CSV will use this exact header order and preserve all columns.
- `rows` (array of objects, optional): Raw CSV rows keyed by header name. When provided, `rows.length` must equal `contacts.length`. Each row should include all original CSV columns and values.

**Note:**
- At least one of `domain` or `website` must be provided for each contact.
- The `mapping` object is recommended when the request originates from a CSV upload, but not required.
- When `raw_headers` and `rows` are provided, the service preserves all original CSV columns per row and only updates the `email` value with the found/verified email address (or leaves it empty if not found).

**How It Works:**

1. For each contact in the list:
   - If an `email` value is provided, first verifies that email and reuses it when valid
   - Otherwise, first tries to find emails in the database using the email finder service
   - If not found (404), tries email verification using the single email verifier
   - If still not found, leaves email empty
2. Creates or updates related `Contact`, `ContactMetadata`, `Company`, and `CompanyMetadata` records using mapped and derived fields from each raw CSV row (e.g. title, departments, phones, location, industries, technologies, revenue, funding, URLs).
3. For any remaining unmapped columns, appends `key: value` pairs into search-friendly text fields on the contact and/or company (e.g. `Contact.text_search`, `Company.text_search`) so no data is lost.
4. Generates a CSV file:
   - If `raw_headers`/`rows` were provided, the CSV mirrors the original file: same header order and columns, with only the `email` value updated.
   - Otherwise, falls back to a minimal CSV with columns: `first_name`, `last_name`, `domain`, `email`.
5. Returns the CSV file as a downloadable response once the background job completes.

**Response:**

**Success (201 Created):**

Returns JSON response with export metadata:

```json
{
  "export_id": "f2186bc9-68f9-4c49-b607-bf6f21b70a69",
  "download_url": "http://localhost:8000/api/v2/exports/f2186bc9-68f9-4c49-b607-bf6f21b70a69/download?token=...",
  "expires_at": "2025-11-29T21:21:05.112091Z",
  "contact_count": 2,
  "company_count": 0,
  "status": "pending"
}
```

**Response Fields:**

- `export_id` (string): Unique identifier for the export job
- `download_url` (string): URL to download the CSV file once processing completes (includes signed token)
- `expires_at` (datetime): Expiration time of the download URL (24 hours from creation)
- `contact_count` (integer): Number of contacts in the export
- `company_count` (integer): Always 0 for email exports
- `status` (string): Export status - one of: `pending`, `processing`, `completed`, `failed`, `cancelled`

**CSV File Format:**

- When called with full CSV context (`raw_headers` + `rows`), the CSV file (available via `download_url` once status is `"completed"`) will:
  - Use the original `raw_headers` as the header row (same order and column names as the uploaded CSV).
  - Preserve all original column values for each row.
  - Only update the `email` column with the verified/found email (or leave it empty if no email could be found).

- When called without `raw_headers`/`rows`, the CSV contains the minimal set of columns:

  - `first_name`: Contact first name
  - `last_name`: Contact last name
  - `domain`: Extracted/normalized domain
  - `email`: Found email address (empty if not found)

**Example CSV Output (minimal mode):**

```csv
first_name,last_name,domain,email
John,Doe,example.com,john.doe@example.com
Jane,Smith,example.com,jane.smith@example.com
```

**Error Responses:**

**400 Bad Request - Missing first_name:**

```json
{
  "detail": "Name fields must be non-empty strings"
}
```

**400 Bad Request - Missing domain/website:**

```json
{
  "detail": "Either domain or website must be provided"
}
```

**400 Bad Request - Empty contacts list:**

```json
{
  "detail": "contacts list cannot be empty"
}
```

**Status Codes:**

- `201 Created`: Export job created successfully
- `400 Bad Request`: Invalid parameters (missing first_name, last_name, domain/website, or invalid domain format)
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Failed to create export

**How It Works:**

1. **Immediate Response:** Endpoint returns immediately with export metadata (status: "pending")
2. **Background Processing:** A background task processes each contact:
   - First tries to find emails in the database using the email finder service
   - If not found (404), tries email verification using the single email verifier
   - If still not found, leaves email empty
3. **Progress Tracking:** Export status and progress are updated during processing
4. **CSV Generation:** Once all contacts are processed, CSV file is generated and saved
5. **Completion:** Export status changes to "completed" and CSV is available via download_url

**Checking Export Status:**

Use `GET /api/v3/exports/{export_id}/status` to check the export status and progress:

```json
{
  "export_id": "f2186bc9-68f9-4c49-b607-bf6f21b70a69",
  "status": "processing",
  "progress_percentage": 50.0,
  "estimated_time": 30,
  "download_url": null,
  "expires_at": null
}
```

**Use Cases:**

1. **Bulk email export:** Export emails for multiple contacts in a single request
2. **Lead generation:** Find and export emails for a list of prospects
3. **Data enrichment:** Enrich contact lists with email addresses
4. **CSV download:** Get a downloadable CSV file with contact and email information
5. **Asynchronous processing:** Process large contact lists without blocking the API response

**Notes:**

- The endpoint returns immediately with export metadata (201 Created)
- Background task processes contacts sequentially
- For large lists, processing time may be significant but doesn't block the API response
- Users can check export status via `GET /api/v2/exports/{export_id}/status`
- CSV file is available via download_url once status is "completed"
- Domain/website is automatically normalized using the same logic as the email finder endpoint

---

### POST /api/v3/email/single/ - Get Single Email

Get a single email address for a contact using two-step approach. Attempts to find an email address for a single contact by first trying to find emails in the database, then falling back to email verification if not found.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`
- `Accept: application/json`

**Request Body:**

```json
{
  "first_name": "John",
  "last_name": "Doe",
  "domain": "example.com"
}
```

**Request Fields:**

- `first_name` (string, required): Contact first name
- `last_name` (string, required): Contact last name
- `domain` (string, optional): Company domain or website URL. Can use `website` parameter instead.
- `website` (string, optional): Company website URL (alias for `domain` parameter)

**Note:** At least one of `domain` or `website` must be provided.

**Domain Parameter Formats:**

Same as the email finder endpoint - accepts full URLs, domains with www, or plain domains. The endpoint automatically extracts and normalizes the domain.

**How It Works:**

1. First tries to find emails in the database using the email finder service
2. If not found (404), tries email verification using the single email verifier
3. If still not found, returns null for email

**Response:**

**Success (200 OK) - Email found via finder:**

```json
{
  "email": "john.doe@example.com",
  "source": "finder"
}
```

**Success (200 OK) - Email found via verifier:**

```json
{
  "email": "john.doe@example.com",
  "source": "verifier"
}
```

**Success (200 OK) - No email found:**

```json
{
  "email": null,
  "source": null
}
```

**Response Fields:**

- `email` (string | null): The email address found, or null if no email was found
- `source` (string | null): Source of the email: `"finder"` (database), `"verifier"` (email verification), or null if not found

**Error Responses:**

**400 Bad Request - Missing first_name:**

```json
{
  "detail": "Name fields must be non-empty strings"
}
```

**400 Bad Request - Missing last_name:**

```json
{
  "detail": "Name fields must be non-empty strings"
}
```

**400 Bad Request - Missing domain/website:**

```json
{
  "detail": "Either domain or website must be provided"
}
```

**400 Bad Request - Invalid domain:**

```json
{
  "detail": "Could not extract valid domain from: invalid-domain"
}
```

**Status Codes:**

- `200 OK`: Email lookup completed successfully
- `400 Bad Request`: Invalid parameters (missing first_name, last_name, domain/website, or invalid domain format)
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Failed to get email

**Use Cases:**

1. **Single email lookup:** Find email for a single contact quickly
2. **Quick email discovery:** Get email address with source information
3. **Contact enrichment:** Enrich a single contact with email address
4. **Real-time lookup:** Find email address in real-time for a contact

**Notes:**

- The endpoint uses the same two-step approach as the export endpoint but returns JSON instead of CSV
- The `source` field indicates whether the email was found in the database (`finder`) or through email verification (`verifier`)
- If email verification credentials are not configured, the endpoint will only use the finder service

---

## Bulk Mail Verifier Management Endpoints

### GET /api/v3/email/bulk/download/{file_type}/{slug}/ - Download Provider Files

Download a CSV file containing verification results for a specific list/batch.

**Headers:**

- `Authorization: Bearer <access_token>` (required)

**Path Parameters:**

- `file_type` (string, required): Type of file to download. Valid values:
  - `valid`: Valid email addresses
  - `invalid`: Invalid email addresses
  - `c-all`: Catchall email addresses
  - `unknown`: Unknown email addresses
- `slug` (string, required): Slug identifier for the list (obtained from the lists endpoint)

**Query Parameters:**

- `provider` (string, required): Email verification provider. Valid values:
  - `bulkmailverifier`: Use BulkMailVerifier service
  - `truelist`: Use Truelist service

**Response:**

**Success (200 OK):**

Returns a CSV file with the following headers:

- `email`: Email address
- `status`: Verification status (valid, invalid, catchall, unknown)

**Example CSV Content:**

```csv
email,status
john@example.com,valid
jane@example.com,invalid
test@example.com,catchall
unknown@example.com,unknown
```

**Error (400 Bad Request) - Invalid File Type:**

```json
{
  "detail": "Invalid file_type. Must be one of: valid, invalid, c-all, unknown"
}
```

**Error (400 Bad Request) - Unsupported Provider:**

```json
{
  "detail": "Unsupported provider: <provider_name>"
}
```

**Error (404 Not Found) - List Not Found:**

```json
{
  "detail": "List not found or file not available"
}
```

**Error (404 Not Found) - No CSV Available (Truelist):**

```json
{
  "detail": "No downloadable CSV available for this batch"
}
```

**Error (500 Internal Server Error) - Credentials Not Configured (BulkMailVerifier):**

```json
{
  "detail": "BulkMailVerifier credentials not configured. Please configure BULKMAILVERIFIER_EMAIL and BULKMAILVERIFIER_PASSWORD environment variables."
}
```

**Error (500 Internal Server Error) - Credentials Not Configured (Truelist):**

```json
{
  "detail": "Truelist API key not configured. Please set TRUELIST_API_KEY."
}
```

**Error (500 Internal Server Error) - Failed to Download:**

```json
{
  "detail": "Failed to download file"
}
```

**Notes:**

- Requires provider credentials to be configured
- BulkMailVerifier uses `file_type` + `slug`
- Truelist ignores `file_type` and downloads the first available CSV URL (`annotated_csv_url`, then `highest_reach_csv_url`, then `safest_bet_csv_url`)
- Returns CSV content directly (Content-Type `text/csv`)

**Status Codes:**

- `200 OK`: File downloaded successfully (CSV content)
- `400 Bad Request`: Invalid file_type parameter or unsupported provider
- `401 Unauthorized`: Authentication required
- `404 Not Found`: List not found, file not available, or no CSV available for batch (Truelist)
- `500 Internal Server Error`: Failed to download file or credentials not configured

**Example Requests:**

```bash
# Download valid emails (BulkMailVerifier)
GET /api/v3/email/bulk/download/valid/list-slug-123/?provider=bulkmailverifier
Authorization: Bearer <access_token>

# Download invalid emails (BulkMailVerifier)
GET /api/v3/email/bulk/download/invalid/list-slug-123/?provider=bulkmailverifier
Authorization: Bearer <access_token>

# Download catchall emails (BulkMailVerifier)
GET /api/v3/email/bulk/download/c-all/list-slug-123/?provider=bulkmailverifier
Authorization: Bearer <access_token>

# Download unknown emails (BulkMailVerifier)
GET /api/v3/email/bulk/download/unknown/list-slug-123/?provider=bulkmailverifier
Authorization: Bearer <access_token>

# Download CSV from Truelist (file_type is ignored, downloads first available CSV)
GET /api/v3/email/bulk/download/valid/batch-id-123/?provider=truelist
Authorization: Bearer <access_token>
```

**Notes:**

- Requires BulkMailVerifier API credentials to be configured
- The file_type must match one of the valid values (valid, invalid, c-all, unknown)
- The slug must be a valid list identifier from the lists endpoint
- Returns CSV content directly (not JSON)
- Content-Type header will be `text/csv`

---

## Response Schemas

### SimpleEmailFinderResponse

```json
{
  "emails": [
    {
      "uuid": "string",
      "email": "string"
    }
  ],
  "total": 0
}
```

**Field Descriptions:**

- `emails` (array): List of email results, each containing:
  - `uuid` (string): Contact UUID
  - `email` (string): Email address from `Contact.email`
- `total` (integer): Total number of emails found

### EmailVerifierRequest

```json
{
  "first_name": "string",
  "last_name": "string",
  "domain": "string",
  "website": "string",
  "provider": "bulkmailverifier",
  "email_count": 1000,
  "max_retries": 10
}
```

**Field Descriptions:**

- `first_name` (string, required): Contact first name
- `last_name` (string, required): Contact last name
- `domain` (string, optional): Company domain or website URL
- `website` (string, optional): Company website URL (alias for domain)
- `provider` (string, required): Email verification provider. Allowed: `bulkmailverifier`, `truelist`.
- `email_count` (integer, optional): Number of random email combinations to generate per batch. Default: 1000. Minimum: 1. No upper limit.
- `max_retries` (integer, optional): Maximum number of batches to process if no valid emails found. Default: from config. Minimum: 1. No upper limit.

### EmailVerificationStatus

Enumeration of email verification statuses:

- `valid`: Email address is valid and deliverable
- `invalid`: Email address is invalid or undeliverable
- `catchall`: Domain accepts all emails (catchall domain)
- `unknown`: Verification status could not be determined

### VerifiedEmailResult

```json
{
  "email": "string",
  "status": "valid"
}
```

**Field Descriptions:**

- `email` (string): Email address that was verified
- `status` (string): Verification status (`valid`, `invalid`, `catchall`, or `unknown`)

### BulkEmailVerifierRequest

```json
{
  "provider": "bulkmailverifier",
  "emails": ["string"],
  "mapping": {},
  "raw_headers": ["string"],
  "rows": [{}],
  "email_column": "string"
}
```

**Field Descriptions:**

- `provider` (string, required): Email verification provider. Allowed: `bulkmailverifier`, `truelist`.
- `emails` (array[string], required): List of email addresses to verify. Minimum: 1 email. Maximum: 10000 emails. If CSV context is provided, emails can be extracted from CSV rows instead.
- `mapping` (object, optional): Column mapping metadata describing how the original CSV columns map to the normalized email field.
- `raw_headers` (array[string], optional): Ordered list of all CSV headers from the original file. When provided, a CSV file will be generated preserving this exact header order and all original columns.
- `rows` (array[object], optional): Raw CSV rows keyed by header name. When provided, `len(rows)` must equal `len(emails)` or emails will be extracted from rows.
- `email_column` (string, optional): Explicit column name containing email addresses. If not provided, will auto-detect from `raw_headers`.

### BulkEmailVerifierResponse

```json
{
  "results": [
    {
      "email": "string",
      "status": "valid"
    }
  ],
  "total": 0,
  "valid_count": 0,
  "invalid_count": 0,
  "catchall_count": 0,
  "unknown_count": 0,
  "download_url": "string",
  "export_id": "string",
  "expires_at": "datetime"
}
```

**Field Descriptions:**

- `results` (array): List of verification results for each email
- `total` (integer): Total number of emails verified
- `valid_count` (integer): Number of valid emails
- `invalid_count` (integer): Number of invalid emails
- `catchall_count` (integer): Number of catchall emails
- `unknown_count` (integer): Number of unknown emails
- `download_url` (string, optional): Signed URL for downloading CSV file with verification results. Only present when CSV context provided.
- `export_id` (string, optional): Export ID for tracking CSV file. Only present when CSV context provided.
- `expires_at` (datetime, optional): Timestamp when the download URL expires (24 hours from creation). Only present when CSV context provided.

### SingleEmailVerifierRequest

```json
{
  "email": "string",
  "provider": "bulkmailverifier"
}
```

**Field Descriptions:**

- `email` (string, required): Single email address to verify. Must be a valid email format.
- `provider` (string, required): Email verification provider. Allowed: `bulkmailverifier`, `truelist`.

### SingleEmailVerifierResponse

```json
{
  "result": {
    "email": "string",
    "status": "valid"
  }
}
```

**Field Descriptions:**

- `result` (object): Verification result for the email
  - `email` (string): Email address that was verified
  - `status` (string): Verification status (`valid`, `invalid`, `catchall`, or `unknown`)

### SingleEmailVerifierFindResponse

```json
{
  "valid_email": "string"
}
```

**Field Descriptions:**

- `valid_email` (string | null): The single valid email address found, or null if no valid email was found after all batches

### SingleEmailRequest

```json
{
  "first_name": "string",
  "last_name": "string",
  "domain": "string",
  "website": "string",
  "provider": "bulkmailverifier"
}
```

**Field Descriptions:**

- `first_name` (string, required): Contact first name
- `last_name` (string, required): Contact last name
- `domain` (string, optional): Company domain or website URL. Can use `website` parameter instead.
- `website` (string, optional): Company website URL (alias for `domain` parameter)
- `provider` (string, required): Email verification provider. Allowed: `bulkmailverifier`, `truelist`.

**Note:** At least one of `domain` or `website` must be provided.

### SingleEmailResponse

```json
{
  "email": "string",
  "source": "string"
}
```

**Field Descriptions:**

- `email` (string | null): The email address found, or null if no email was found
- `source` (string | null): Source of the email: `"finder"` (database), `"verifier"` (email verification), or null if not found

### EmailExportContact

```json
{
  "first_name": "string",
  "last_name": "string",
  "domain": "string",
  "website": "string",
  "email": "string"
}
```

**Field Descriptions:**

- `first_name` (string, required): Contact first name
- `last_name` (string, required): Contact last name
- `domain` (string, optional): Company domain or website URL. Can use `website` parameter instead.
- `website` (string, optional): Company website URL (alias for `domain` parameter)
- `email` (string, optional): Existing email address from the source data. If provided, the system verifies this email first and reuses it when valid.

**Note:** At least one of `domain` or `website` must be provided.

### EmailExportRequest

```json
{
  "contacts": [
    {
      "first_name": "string",
      "last_name": "string",
      "domain": "string",
      "website": "string",
      "email": "string"
    }
  ],
  "mapping": {
    "first_name": "first_name",
    "last_name": "last_name",
    "domain": "domain",
    "website": "website",
    "email": "email"
  }
}
```

**Field Descriptions:**

- `contacts` (array[EmailExportContact], required): List of contacts to export. Minimum: 1 contact.
- `mapping` (object, optional): Column mapping metadata from the original CSV with keys:
  - `first_name`, `last_name`, `domain`, `website`, `email` (each is the original CSV column name or `null`).

### EmailVerifierResponse

```json
{
  "valid_emails": ["string"],
  "total_valid": 0,
  "generated_emails": ["string"],
  "total_generated": 0,
  "total_batches_processed": 0
}
```

**Field Descriptions:**

- `valid_emails` (array): List of verified valid email addresses
- `total_valid` (integer): Total number of valid emails found
- `generated_emails` (array): List of all generated email addresses (for reference)
- `total_generated` (integer): Total number of emails generated
- `total_batches_processed` (integer): Total number of batches processed

---

## Use Cases

### 1. Find Email by Contact Name and Company Domain

**Scenario:** You know a contact's first name, last name, and their company's website, and want to find their email address.

**Example:**

```bash
GET /api/v3/email/finder/?first_name=John&last_name=Smith&domain=acme.com
```

**Use Case:** Sales prospecting, lead enrichment, contact verification

### 2. Find Multiple Emails for Same Name at Different Companies

**Scenario:** You want to find all contacts named "John Doe" across different companies with specific domains.

**Example:**

```bash
# Search for John Doe at example.com
GET /api/v3/email/finder/?first_name=John&last_name=Doe&domain=example.com

# Search for John Doe at another company
GET /api/v3/email/finder/?first_name=John&last_name=Doe&domain=another-company.com
```

**Use Case:** Contact discovery, email verification across multiple companies

### 3. Domain Extraction from Full URLs

**Scenario:** You have a full company website URL and want to find contacts.

**Example:**

```bash
# Full URL with protocol and path
GET /api/v3/email/finder/?first_name=Jane&last_name=Smith&website=https://www.example.com/about-us
```

The endpoint automatically extracts `example.com` from the URL.

**Use Case:** Integration with external systems that provide full URLs

### 4. Partial Name Matching

**Scenario:** You know part of a contact's name and want to find matching emails.

**Example:**

```bash
# Partial first name match
GET /api/v3/email/finder/?first_name=John&last_name=Smith&domain=example.com
# This will match "John", "Johnny", "Johnson", etc.
```

**Use Case:** Flexible name searching when exact spelling is unknown

### 5. Verify Multiple Email Addresses

**Scenario:** You have a list of email addresses and want to verify which ones are valid, invalid, catchall, or unknown using BulkMailVerifier.

**Example:**

```bash
# Verify multiple emails
POST /api/v3/email/bulk/verifier/
{
  "emails": [
    "john.doe@example.com",
    "jane.smith@example.com",
    "invalid@example.com"
  ]
}
```

**Use Case:** Email validation, lead verification, data cleaning, email list verification

**How It Works:**

1. The system verifies all provided emails through BulkMailVerifier direct email verification API (`/api/email/verify/`) in batches of 20 emails processed concurrently
2. Each email is verified individually and mapped to its verification status (valid, invalid, catchall, unknown)
3. The endpoint returns detailed results for each email with status counts immediately after all verifications complete

**Response:** Returns verification status for each email with summary counts (valid_count, invalid_count, catchall_count, unknown_count).

### 6. Verify Single Email Address

**Scenario:** You want to verify a single email address and get its verification status.

**Example:**

```bash
# Verify single email
POST /api/v3/email/single/verifier/
{
  "email": "john.doe@example.com"
}
```

**Use Case:** Single email validation, real-time verification, email format validation, quick email check

**How It Works:**

1. The system verifies the email through BulkMailVerifier direct email verification API (`/api/email/verify/`)
2. The email is verified synchronously and the status is determined immediately
3. The endpoint returns the verification result for the single email

**Response:** Returns verification result with email and status (valid, invalid, catchall, or unknown).

### 7. Find Single Valid Email Quickly

**Scenario:** You want to generate random email combinations for a contact and get the first valid email found as quickly as possible, without waiting for all verifications to complete.

**Example:**

```bash
# Find first valid email
POST /api/v3/email/verifier/single/
{
  "first_name": "John",
  "last_name": "Doe",
  "domain": "example.com"
}
```

**Use Case:** Quick email discovery, fast lead generation, efficient verification when you only need one valid email

**How It Works:**

1. The system generates random email combinations (default: 1000, configurable via `email_count`) using various patterns (firstname.lastname, f.lastname, firstname123, etc.)
2. Emails are verified sequentially one at a time through BulkMailVerifier direct email verification API (`/api/email/verify/`)
3. The system stops immediately when the first VALID email is found and returns it
4. If no valid email found in current batch, automatically generates a new batch and continues (up to `max_retries` limit, default: from config)
5. The endpoint returns the first valid email found, or null if none found after all batches

**Key Advantages:**

- **Faster response:** Stops immediately on first valid email (doesn't wait for batch to complete)
- **More efficient:** Saves API credits by not verifying all emails when you only need one
- **Sequential verification:** Verifies one at a time for optimal early stopping
- **Single result:** Returns only the first valid email, not a list

**Response:** Returns the first valid email found immediately, or null if none found after all batches.

### 8. Export Emails to CSV

**Scenario:** You have a list of contacts and want to export their email addresses to a CSV file. The system will try to find emails in the database first, then use email verification if not found.

**Example:**

```bash
POST /api/v3/email/export
{
  "contacts": [
    {
      "first_name": "John",
      "last_name": "Doe",
      "domain": "example.com"
    },
    {
      "first_name": "Jane",
      "last_name": "Smith",
      "website": "https://www.example.com"
    }
  ]
}
```

**Use Case:** Bulk email export, lead generation, data enrichment, CSV download

**How It Works:**

1. For each contact in the list:
   - First tries to find emails in the database using the email finder service
   - If not found (404), tries email verification using the single email verifier
   - If still not found, leaves email empty
2. Generates a CSV file with columns: `first_name`, `last_name`, `domain`, `email`
3. Returns the CSV file as a downloadable response

**Response:** Returns a CSV file with all contacts and their found email addresses (or empty if not found).

### 9. Get Single Email with Source

**Scenario:** You want to find an email address for a single contact and know where it came from (database or verification).

**Example:**

```bash
POST /api/v3/email/single/
{
  "first_name": "John",
  "last_name": "Doe",
  "domain": "example.com"
}
```

**Use Case:** Single email lookup, quick email discovery, contact enrichment, real-time lookup

**How It Works:**

1. First tries to find emails in the database using the email finder service
2. If not found (404), tries email verification using the single email verifier
3. If still not found, returns null for email

**Response:** Returns JSON with email address and source (`finder` or `verifier`), or null if not found.

### 10. Generate and Verify Random Email Combinations

**Scenario:** You want to generate random email combinations for a contact and verify which ones are valid using BulkMailVerifier. The verification is performed synchronously and results are returned directly.

**Example:**

```bash
# Verify emails synchronously
POST /api/v3/email/verifier/
{
  "first_name": "John",
  "last_name": "Doe",
  "domain": "example.com"
}
```

**Use Case:** Email discovery, lead generation, contact enrichment

**How It Works:**

1. The system generates random email combinations (default: 1000, configurable via `email_count`) using various patterns (firstname.lastname, f.lastname, firstname123, etc.)
2. Emails are verified through BulkMailVerifier direct email verification API (`/api/email/verify/`) in batches of 20 emails processed concurrently
3. The system processes batches synchronously and waits for all verifications to complete
4. Valid emails are extracted and returned directly in the response
5. If no valid emails are found, the system automatically generates a new batch and retries (up to `max_retries` limit, default: from config)
6. The endpoint returns verified results immediately after completion

**Configuration Parameters:**

- **email_count**: Controls how many random email combinations are generated per batch. Minimum: 1. No upper limit. Higher values may find more emails but take longer to verify. Recommended: 500-2000 for most use cases, but can be set to any value >= 1.
- **max_retries**: Controls how many batches to process before giving up if no valid emails are found. Minimum: 1. No upper limit. Higher values increase the chance of finding valid emails but consume more API credits and time.

---

## Error Handling

### Validation Errors

All validation errors return `400 Bad Request` with descriptive error messages:

- **Missing first_name:** `"first_name is required and cannot be empty"`
- **Missing last_name:** `"last_name is required and cannot be empty"`
- **Missing domain/website:** `"Either domain or website parameter is required"`
- **Empty domain/website:** `"Domain or website cannot be empty"`
- **Invalid domain format:** `"Could not extract valid domain from: <input>"`

### Authentication Errors

- **401 Unauthorized:** Missing or invalid authentication token

### Not Found Errors

The endpoint returns `404 Not Found` in two scenarios:

1. **Company not found:** When no companies in the database match the provided domain
   - Error message: `"No companies found with domain: {domain}"`
   - This occurs after domain extraction and validation, but before searching for contacts
   - Indicates the domain is valid but no companies exist with that domain

2. **Contact not found:** When companies exist for the domain, but no contacts match the name criteria
   - Error message: `"No contacts found with name '{first_name} {last_name}' for companies with domain: {domain}"`
   - This occurs after confirming companies exist, but the contact search returns no results
   - Indicates the domain has companies, but no contacts match the provided first and last name

### Server Errors

- **500 Internal Server Error - General error:** Unexpected server error occurred during email search
  - Error message: `"Failed to find emails"`

---

## Email Verifier Endpoints

All verifier-related endpoints require a `provider` that selects the verification service:

- `bulkmailverifier`
- `truelist`

Include `provider` in the request body (for POST verifiers) or as a query parameter where noted.

### POST /api/v3/email/bulk/verifier/ - Verify Multiple Emails

Verify multiple email addresses through BulkMailVerifier service. Accepts a list of email addresses and returns verification status for each email (valid, invalid, catchall, unknown). Supports CSV context preservation: when CSV context is provided, generates a downloadable CSV file with original columns plus verification status.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`
- `Accept: application/json`

**Request Body (minimal example):**

```json
{
  "provider": "bulkmailverifier",
  "emails": [
    "john.doe@example.com",
    "jane.smith@example.com",
    "invalid@example.com"
  ]
}
```

**Request Body (with full CSV context):**

```json
{
  "provider": "bulkmailverifier",
  "emails": [
    "john.doe@example.com",
    "jane.smith@example.com",
    "invalid@example.com"
  ],
  "mapping": {
    "email": "email"
  },
  "raw_headers": [
    "first_name",
    "last_name",
    "company",
    "email",
    "title",
    "city",
    "state"
  ],
  "rows": [
    {
      "first_name": "John",
      "last_name": "Doe",
      "company": "Tech Corp",
      "email": "john.doe@example.com",
      "title": "Software Engineer",
      "city": "San Francisco",
      "state": "CA"
    },
    {
      "first_name": "Jane",
      "last_name": "Smith",
      "company": "Tech Corp",
      "email": "jane.smith@example.com",
      "title": "Product Manager",
      "city": "New York",
      "state": "NY"
    },
    {
      "first_name": "Test",
      "last_name": "User",
      "company": "Tech Corp",
      "email": "invalid@example.com",
      "title": "Developer",
      "city": "Boston",
      "state": "MA"
    }
  ],
  "email_column": "email"
}
```

**Request Fields:**

- `provider` (string, required): Email verification provider. Allowed: `bulkmailverifier`, `truelist`.
- `emails` (array[string], required): List of email addresses to verify. Minimum: 1 email. Maximum: 10000 emails. If CSV context is provided, emails can be extracted from CSV rows instead.
- `mapping` (object, optional): Column mapping metadata describing how the original CSV columns map to the normalized email field.
- `raw_headers` (array[string], optional): Ordered list of all CSV headers from the original file. When provided, a CSV file will be generated preserving this exact header order and all original columns.
- `rows` (array[object], optional): Raw CSV rows keyed by header name. When provided, `len(rows)` must equal `len(emails)` or emails will be extracted from rows. Each row should include all original CSV columns and values.
- `email_column` (string, optional): Explicit column name containing email addresses. If not provided, will auto-detect from `raw_headers` (searches for columns containing "email").

**Example Request:**

```bash
POST /api/v3/email/bulk/verifier/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "emails": [
    "john.doe@example.com",
    "jane.smith@example.com",
    "invalid@example.com"
  ]
}
```

**Response:**

**Success (200 OK) - Without CSV context:**

```json
{
  "results": [
    {
      "email": "john.doe@example.com",
      "status": "valid"
    },
    {
      "email": "jane.smith@example.com",
      "status": "invalid"
    },
    {
      "email": "invalid@example.com",
      "status": "catchall"
    }
  ],
  "total": 3,
  "valid_count": 1,
  "invalid_count": 1,
  "catchall_count": 1,
  "unknown_count": 0,
  "download_url": null,
  "export_id": null,
  "expires_at": null
}
```

**Success (200 OK) - With CSV context:**

```json
{
  "results": [
    {
      "email": "john.doe@example.com",
      "status": "valid"
    },
    {
      "email": "jane.smith@example.com",
      "status": "invalid"
    },
    {
      "email": "invalid@example.com",
      "status": "catchall"
    }
  ],
  "total": 3,
  "valid_count": 1,
  "invalid_count": 1,
  "catchall_count": 1,
  "unknown_count": 0,
  "download_url": "http://34.229.94.175:8000/api/v2/exports/abc123-def456-ghi789/download?token=...",
  "export_id": "abc123-def456-ghi789",
  "expires_at": "2024-12-21T10:30:00Z"
}
```

**Response Fields:**

- `results` (array): List of verification results, each containing:
  - `email` (string): Email address that was verified
  - `status` (string): Verification status (`valid`, `invalid`, `catchall`, or `unknown`)
- `total` (integer): Total number of emails verified
- `valid_count` (integer): Number of valid emails
- `invalid_count` (integer): Number of invalid emails
- `catchall_count` (integer): Number of catchall emails
- `unknown_count` (integer): Number of unknown emails
- `download_url` (string, optional): Signed URL for downloading CSV file with verification results. Only present when CSV context provided.
- `export_id` (string, optional): Export ID for tracking CSV file. Only present when CSV context provided.
- `expires_at` (datetime, optional): Timestamp when the download URL expires (24 hours from creation). Only present when CSV context provided.

**Status Values:**

- `valid`: Email address is valid and deliverable
- `invalid`: Email address is invalid or undeliverable
- `catchall`: Domain accepts all emails (catchall domain)
- `unknown`: Verification status could not be determined

**Error Responses:**

**400 Bad Request - Empty emails list:**

```json
{
  "detail": "emails list cannot be empty"
}
```

**400 Bad Request - Invalid email format:**

```json
{
  "detail": "Invalid email format: invalid-email"
}
```

**400 Bad Request - Exceeds limit:**

```json
{
  "detail": "emails list cannot exceed 10000 emails"
}
```

**500 Internal Server Error - Credentials not configured:**

```json
{
  "detail": "BulkMailVerifier credentials not configured. Please configure BULKMAILVERIFIER_EMAIL and BULKMAILVERIFIER_PASSWORD environment variables."
}
```

**Status Codes:**

- `200 OK`: Email verification completed successfully
- `400 Bad Request`: Invalid parameters (empty emails list, invalid email format, or exceeds 10000 email limit)
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Failed to verify emails (BulkMailVerifier API error, credentials not configured, etc.)

**CSV File Generation (when CSV context provided):**

When `raw_headers` and `rows` are provided, the endpoint generates a downloadable CSV file in addition to the JSON response:

- **CSV Structure:** The CSV file preserves all original CSV columns from `raw_headers` and `rows`
- **Verification Status:** Adds a `verification_status` column with values: `valid`, `invalid`, `catchall`, or `unknown`
- **Column Preservation:** All original CSV columns and values are preserved; only the `verification_status` column is added
- **Download:** Use the `download_url` from the response to download the CSV file (expires after 24 hours)

**Example CSV Output (with CSV context):**

```csv
first_name,last_name,company,email,title,city,state,verification_status
John,Doe,Tech Corp,john.doe@example.com,Software Engineer,San Francisco,CA,valid
Jane,Smith,Tech Corp,jane.smith@example.com,Product Manager,New York,NY,invalid
Test,User,Tech Corp,invalid@example.com,Developer,Boston,MA,catchall
```

**Note:** The endpoint performs verification synchronously using direct API calls. Verification time depends on the number of emails (processed in batches of 20 concurrently). All emails are verified through BulkMailVerifier direct email verification API (`/api/email/verify/`). When CSV context is provided, CSV file generation happens synchronously after verification completes.

---

### POST /api/v3/email/single/verifier/ - Verify Single Email

Verify a single email address through BulkMailVerifier service. Accepts one email address and returns its verification status (valid, invalid, catchall, unknown).

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`
- `Accept: application/json`

**Request Body:**

```json
{
  "email": "john.doe@example.com"
}
```

**Request Fields:**

- `email` (string, required): Single email address to verify. Must be a valid email format.

**Example Request:**

```bash
POST /api/v3/email/single/verifier/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "email": "john.doe@example.com"
}
```

**Response:**

**Success (200 OK):**

```json
{
  "result": {
    "email": "john.doe@example.com",
    "status": "valid"
  }
}
```

**Response Fields:**

- `result` (object): Verification result containing:
  - `email` (string): Email address that was verified
  - `status` (string): Verification status (`valid`, `invalid`, `catchall`, or `unknown`)

**Status Values:**

- `valid`: Email address is valid and deliverable
- `invalid`: Email address is invalid or undeliverable
- `catchall`: Domain accepts all emails (catchall domain)
- `unknown`: Verification status could not be determined

**Error Responses:**

**400 Bad Request - Missing email:**

```json
{
  "detail": "field required"
}
```

**400 Bad Request - Invalid email format:**

```json
{
  "detail": "value is not a valid email address"
}
```

**500 Internal Server Error - Credentials not configured:**

```json
{
  "detail": "BulkMailVerifier credentials not configured. Please configure BULKMAILVERIFIER_EMAIL and BULKMAILVERIFIER_PASSWORD environment variables."
}
```

**Status Codes:**

- `200 OK`: Email verification completed successfully
- `400 Bad Request`: Invalid parameters (missing email or invalid email format)
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Failed to verify email (BulkMailVerifier API error, credentials not configured, etc.)

**Note:** The endpoint performs verification synchronously using direct API calls. The email is verified through BulkMailVerifier direct email verification API (`/api/email/verify/`).

---

### POST /api/v3/email/verifier/single/ - Find Single Valid Email

Verify emails sequentially and return immediately when first VALID email is found. Generates random email combinations based on first name, last name, and domain, then verifies them sequentially one at a time through BulkMailVerifier direct email verification API (`/api/email/verify/`). Stops immediately when the first VALID email is found and returns it.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`
- `Accept: application/json`

**Request Body:**

```json
{
  "first_name": "John",
  "last_name": "Doe",
  "domain": "example.com",
  "email_count": 1000,
  "max_retries": 10
}
```

**Request Fields:**

- `first_name` (string, required): Contact first name
- `last_name` (string, required): Contact last name
- `domain` (string, optional): Company domain or website URL. Can use `website` parameter instead.
- `website` (string, optional): Company website URL (alias for `domain` parameter)
- `email_count` (integer, optional): Number of random email combinations to generate per batch. Default: 1000. Minimum: 1. No upper limit.
- `max_retries` (integer, optional): Maximum number of batches to process if no valid emails found. Default: from `BULKMAILVERIFIER_MAX_RETRIES` config (typically 10). Minimum: 1. No upper limit. If not provided, uses the default from configuration.

**Domain Parameter Formats:**

Same as the email finder endpoint - accepts full URLs, domains with www, or plain domains. The endpoint automatically extracts and normalizes the domain.

**Example Request:**

```bash
POST /api/v3/email/verifier/single/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "first_name": "John",
  "last_name": "Doe",
  "domain": "example.com",
  "email_count": 1000,
  "max_retries": 10
}
```

**How It Works:**

1. Generates random email combinations (default: 1000, configurable via `email_count`) using various patterns (firstname.lastname, f.lastname, firstname123, etc.)
2. Verifies emails sequentially one at a time through BulkMailVerifier direct email verification API (`/api/email/verify/`)
3. Stops immediately when the first VALID email is found and returns it
4. If no valid email found in current batch, generates new batch and continues (up to `max_retries` limit)
5. Returns the first valid email found, or null if none found after all batches

**Key Difference from `/email/verifier/`:**

- Verifies emails sequentially (one at a time) instead of in concurrent batches
- Stops immediately on first VALID email (doesn't wait for batch to complete)
- Returns only the single valid email found, not a list
- More efficient for finding just one valid email quickly

**Response:**

**Success (200 OK) - Valid email found:**

```json
{
  "valid_email": "john.doe@example.com"
}
```

**Success (200 OK) - No valid email found:**

```json
{
  "valid_email": null
}
```

**Response Fields:**

- `valid_email` (string | null): The first valid email address found, or null if no valid email was found after all batches

**Error Responses:**

**400 Bad Request - Missing first_name:**

```json
{
  "detail": "first_name is required and cannot be empty"
}
```

**400 Bad Request - Missing last_name:**

```json
{
  "detail": "last_name is required and cannot be empty"
}
```

**400 Bad Request - Missing domain/website:**

```json
{
  "detail": "Either domain or website parameter is required"
}
```

**400 Bad Request - Invalid domain:**

```json
{
  "detail": "Could not extract valid domain from: invalid-domain"
}
```

**400 Bad Request - Invalid email_count:**

```json
{
  "detail": "email_count must be at least 1"
}
```

**400 Bad Request - Invalid max_retries:**

```json
{
  "detail": "max_retries must be at least 1"
}
```

**500 Internal Server Error - Credentials not configured:**

```json
{
  "detail": "BulkMailVerifier credentials not configured. Please configure BULKMAILVERIFIER_EMAIL and BULKMAILVERIFIER_PASSWORD environment variables."
}
```

**Status Codes:**

- `200 OK`: Email verification completed successfully (valid email found or none found)
- `400 Bad Request`: Invalid parameters
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Failed to verify emails (BulkMailVerifier API error, credentials not configured, etc.)

**Use Cases:**

1. **Quick email discovery:** Find just one valid email address quickly
2. **Fast lead generation:** Get the first valid email without waiting for all verifications
3. **Efficient verification:** Stop as soon as a valid email is found to save API credits
4. **Single email lookup:** When you only need one valid email, not multiple

**Note:** The endpoint performs verification sequentially (one email at a time) and stops immediately when the first VALID email is found. This is more efficient than verifying all emails when you only need one valid result. Verification time depends on the position of the first valid email in the generated list.

---

### POST /api/v3/email/verifier/ - Verify Emails Synchronously

Verify emails synchronously by generating random email combinations based on first name, last name, and domain, then verifying them through BulkMailVerifier direct email verification API (`/api/email/verify/`) in batches. The endpoint processes emails in batches of 20 concurrently and returns verified results directly in the response.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`
- `Accept: application/json`

**Request Body:**

```json
{
  "first_name": "John",
  "last_name": "Doe",
  "domain": "example.com",
  "email_count": 1000,
  "max_retries": 10
}
```

**Request Fields:**

- `first_name` (string, required): Contact first name
- `last_name` (string, required): Contact last name
- `domain` (string, optional): Company domain or website URL. Can use `website` parameter instead.
- `website` (string, optional): Company website URL (alias for `domain` parameter)
- `email_count` (integer, optional): Number of random email combinations to generate per batch. Default: 1000. Minimum: 1. No upper limit.
- `max_retries` (integer, optional): Maximum number of batches to process if no valid emails found. Default: from `BULKMAILVERIFIER_MAX_RETRIES` config (typically 10). Minimum: 1. No upper limit. If not provided, uses the default from configuration.

**Domain Parameter Formats:**

Same as the email finder endpoint - accepts full URLs, domains with www, or plain domains. The endpoint automatically extracts and normalizes the domain.

**Example Request:**

```bash
POST /api/v3/email/verifier/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "first_name": "John",
  "last_name": "Doe",
  "domain": "example.com",
  "email_count": 1000,
  "max_retries": 10
}
```

**Parameter Examples:**

```bash
# Using default values (1000 emails per batch, 10 max retries from config)
{
  "first_name": "John",
  "last_name": "Doe",
  "domain": "example.com"
}

# Custom email count (500 emails per batch)
{
  "first_name": "John",
  "last_name": "Doe",
  "domain": "example.com",
  "email_count": 500
}

# Custom max retries (5 batches maximum)
{
  "first_name": "John",
  "last_name": "Doe",
  "domain": "example.com",
  "max_retries": 5
}

# Both custom parameters
{
  "first_name": "John",
  "last_name": "Doe",
  "domain": "example.com",
  "email_count": 2000,
  "max_retries": 20
}
```

**Response:**

**Success (200 OK):**

```json
{
  "valid_emails": [
    "john.doe@example.com",
    "j.doe@example.com"
  ],
  "total_valid": 2,
  "generated_emails": [
    "john.doe@example.com",
    "j.doe@example.com",
    "john.doe123@example.com",
    "invalid@example.com"
  ],
  "total_generated": 4,
  "total_batches_processed": 1
}
```

**Note:** The endpoint performs verification synchronously using direct API calls in batches of 20 emails processed concurrently. Verification time depends on the number of emails generated. The response includes both verified valid emails and all generated emails for reference.

**Error Responses:**

**400 Bad Request - Missing first_name:**

```json
{
  "detail": "first_name is required and cannot be empty"
}
```

**400 Bad Request - Missing last_name:**

```json
{
  "detail": "last_name is required and cannot be empty"
}
```

**400 Bad Request - Missing domain/website:**

```json
{
  "detail": "Either domain or website parameter is required"
}
```

**400 Bad Request - Invalid domain:**

```json
{
  "detail": "Could not extract valid domain from: invalid-domain"
}
```

**400 Bad Request - Invalid email_count:**

```json
{
  "detail": "email_count must be at least 1"
}
```

**400 Bad Request - Invalid max_retries:**

```json
{
  "detail": "max_retries must be at least 1"
}
```

**Response Fields:**

- `valid_emails` (array): List of verified valid email addresses
- `total_valid` (integer): Total number of valid emails found
- `generated_emails` (array): List of all generated email addresses (for reference)
- `total_generated` (integer): Total number of emails generated
- `total_batches_processed` (integer): Total number of batches processed

**Status Codes:**

- `200 OK`: Email verification completed successfully
- `400 Bad Request`: Invalid parameters
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Failed to verify emails (BulkMailVerifier API error, timeout, etc.)

---

## Implementation Details

### Domain Extraction

The endpoint uses the same domain extraction logic as the company domain listing endpoint:

1. Removes protocol (`http://`, `https://`)
2. Extracts hostname (everything before first `/`)
3. Removes port numbers
4. Removes `www.` prefix
5. Converts to lowercase

**Examples:**

- `` `https://www.example.com` `` → `` `example.com` ``
- `` `http://example.com:8080/path` `` → `` `example.com` ``
- `www.example.com` → `example.com`
- `example.com` → `example.com`

### Name Matching

- **Case-insensitive:** Matches are case-insensitive
- **Partial matching:** Uses `ILIKE` with `%name%` pattern
- **Both names required:** Both first_name and last_name must match

### Email Filtering

- Only contacts with non-empty email addresses are returned
- Filters out contacts where `Contact.email IS NULL` or empty string

### Database Queries

The endpoint uses a 3-step subquery approach for optimal performance:

**Step 1: Find company UUIDs from companies_metadata table**

- Uses optimized dual search strategy:
  - **Strategy 1 (Primary):** Match against `normalized_domain` column (FAST - uses index)
  - **Strategy 2 (Fallback):** Extract domain from `website` column using SQL functions and match (SLOW - only if Strategy 1 finds nothing)
- Prioritizes indexed `normalized_domain` column for optimal performance
- Only uses website extraction when `normalized_domain` is NULL/empty

**Step 2: Find company UUIDs from companies table**

- Validates that companies exist in the main companies table
- Uses cached company UUIDs from Step 1 (no subquery re-execution)
- Filters by `uuid IN (cached UUID list)`

**Step 3: Find contact (uuid, email) pairs from contacts table**

- Uses cached company UUIDs from Step 2 (no subquery re-execution)
- Filters by `company_id IN (cached UUID list)` - uses direct list filtering instead of nested subqueries
- Filters by `first_name ILIKE '%{first_name}%'` (case-insensitive partial match)
- Filters by `last_name ILIKE '%{last_name}%'` (case-insensitive partial match)
- Filters by `email IS NOT NULL AND email != ''`
- Returns only `uuid` and `email` columns
- Diagnostic queries are optional and combined into single query when no results found

**Field Extraction:**
The repository extracts and logs the following fields for debugging:

- `uuid` (contact UUID)
- `email` (contact email)
- `first_name` (contact first name)
- `last_name` (contact last name)
- `company_id` (company UUID)

**Performance Optimizations (Updated):**

- **Index Optimizations:**
  - Uses `idx_companies_metadata_normalized_domain` index in Step 1 (critical optimization)
  - Uses `idx_companies_metadata_normalized_domain_uuid` composite index for faster Step 1 lookups
  - Uses `idx_contacts_company_id` index in Step 3
  - Uses `idx_contacts_company_name_email` composite index for optimized Step 3 queries
  - Uses trigram indexes (`idx_contacts_first_name_trgm`, `idx_contacts_last_name_trgm`) for name matching
- **Query Optimizations:**
  - Prioritizes `normalized_domain` column (indexed) over website extraction (unindexed)
  - Only uses website extraction as fallback when `normalized_domain` is NULL/empty
  - Caches company UUIDs from Step 1 to avoid re-executing subqueries in Step 2 and Step 3
  - Uses direct UUID list filtering instead of nested subqueries (eliminates subquery re-execution)
  - Removed redundant company existence check (saves significant query time)
  - Diagnostic queries are optional and combined into single query using conditional aggregation
- **Expected Performance:**
  - Response time improved from ~6 minutes to ~15-30 seconds (90%+ improvement)
  - Optimized for selective domains (when few companies match the domain)

---

## Related Endpoints

- **GET /api/v3/contacts/company/domain/**: List all company domains
- **POST /api/v3/contacts/query**: Search contacts with filters
- **POST /api/v3/linkedin/**: Search by LinkedIn URL

---

## Notes

- The endpoint only returns contacts that have email addresses in the database
- Domain matching is case-insensitive
- Name matching uses partial matching (substring search)
- The endpoint extracts domains from `CompanyMetadata.website` field using dual search strategy
- The endpoint requires both first_name and last_name to be provided
- Returns simple (uuid, email) pairs for efficient data transfer
- Comprehensive logging is included throughout the flow for debugging purposes

## Activity Tracking

All email finder and export operations are automatically tracked in the user activities system. Each operation creates an activity record with:

- **Service Type**: `email`
- **Action Type**: `search` (for finder operations) or `export` (for export operations)
- **Request Parameters**: Stored as JSON (e.g., `{"first_name": "John", "last_name": "Doe", "domain": "example.com"}`)
- **Result Count**: Number of results returned
- **Result Summary**: Detailed summary (e.g., `{"emails_found": 5}`)
- **Status**: `success`, `failed`, or `partial`
- **IP Address**: User's IP address (extracted from request headers)
- **User Agent**: User's browser/device information

**Activity Tracking Endpoints:**

- **GET /api/v3/activities/**: View your activity history with filtering and pagination
- **GET /api/v3/activities/stats/**: Get activity statistics (counts by service type, action type, status, and recent activities)

**Example Activity Record:**

```json
{
  "id": 1,
  "user_id": "user-uuid",
  "service_type": "email",
  "action_type": "search",
  "status": "success",
  "request_params": {
    "first_name": "John",
    "last_name": "Doe",
    "domain": "example.com"
  },
  "result_count": 5,
  "result_summary": {
    "emails_found": 5
  },
  "error_message": null,
  "ip_address": "192.168.1.1",
  "user_agent": "Mozilla/5.0...",
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Notes:**

- Activities are logged automatically - no additional API calls required
- Export activities are updated when exports complete (result_count and result_summary are updated)
- Failed operations are also logged with error messages
- All activities are tied to the authenticated user
