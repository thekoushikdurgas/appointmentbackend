# Large File Upload API Documentation

Complete API documentation for large file upload endpoints using S3 multipart uploads, supporting files up to 10GB with resumable uploads.

**Related Documentation:**

- [S3 File Operations API](./s3.md) - For listing and downloading files from S3
- [Export API](./export.md) - For exporting contacts and companies to CSV
- [Environment Variables](./ENVIRONMENT_VARIABLES.md) - For upload configuration settings

## Table of Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [Upload Endpoints](#upload-endpoints)
  - [POST /api/v3/upload/initiate](#post-apiv3uploadinitiate---initiate-multipart-upload)
  - [GET /api/v3/upload/presigned-url/{upload_id}/{part_number}](#get-apiv3uploadpresigned-urlupload_idpart_number---get-presigned-url)
  - [POST /api/v3/upload/parts](#post-apiv3uploadparts---register-uploaded-part)
  - [POST /api/v3/upload/complete](#post-apiv3uploadcomplete---complete-upload)
  - [POST /api/v3/upload/abort](#post-apiv3uploadabort---abort-upload)
  - [GET /api/v3/upload/status/{upload_id}](#get-apiv3uploadstatusupload_id---get-upload-status)
- [Response Schemas](#response-schemas)
- [Use Cases](#use-cases)
- [Error Handling](#error-handling)

---

## Base URL

For production, use:

```txt
http://34.229.94.175:8000
```

**API Version:** All upload endpoints are under `/api/v3/upload`

## Authentication

All upload endpoints require JWT authentication via the `Authorization` header:

```txt
Authorization: Bearer <access_token>
```

Tokens are obtained through the login or register endpoints.

## Role-Based Access Control

All upload endpoints are accessible to all authenticated users:

- **Free Users (`FreeUser`)**: ✅ Full access to upload operations
- **Pro Users (`ProUser`)**: ✅ Full access to upload operations
- **Admin (`Admin`)**: ✅ Full access to upload operations
- **Super Admin (`SuperAdmin`)**: ✅ Full access to upload operations

---

## Upload Endpoints

### POST /api/v3/upload/initiate - Initiate Multipart Upload

Initialize a new multipart upload session for a large file.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Request Body:**

```json
{
  "filename": "large-dataset.csv",
  "file_size": 5368709120,
  "content_type": "text/csv"
}
```

**Response (200 OK):**

```json
{
  "upload_id": "550e8400-e29b-41d4-a716-446655440000",
  "file_key": "uploads/123/20240115_143022_large-dataset.csv",
  "s3_upload_id": "abc123xyz",
  "chunk_size": 104857600,
  "num_parts": 52
}
```

**Response Codes:**

- `200 OK`: Upload session created successfully
- `400 Bad Request`: File size exceeds limit
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Failed to initiate upload

**Notes:**

- Maximum file size: 10GB (configurable via `S3_MULTIPART_MAX_FILE_SIZE`)
- Default chunk size: 100MB (configurable via `S3_MULTIPART_CHUNK_SIZE`)
- Files are stored under `uploads/{user_id}/{timestamp}_{filename}`

---

### GET /api/v3/upload/presigned-url/{upload_id}/{part_number} - Get Presigned URL

Get a presigned URL for uploading a specific part of the file directly to S3.

**Headers:**

- `Authorization: Bearer <access_token>` (required)

**Path Parameters:**

- `upload_id` (string, required): Upload session identifier from `/initiate`
- `part_number` (integer, required, min: 1): Part number (1-indexed)

**Response (200 OK):**

```json
{
  "presigned_url": "https://bucket.s3.amazonaws.com/uploads/...?X-Amz-Algorithm=...",
  "part_number": 1,
  "already_uploaded": false
}
```

If part was already uploaded:

```json
{
  "presigned_url": null,
  "part_number": 1,
  "already_uploaded": true,
  "etag": "d41d8cd98f00b204e9800998ecf8427e"
}
```

**Response Codes:**

- `200 OK`: Presigned URL generated successfully
- `404 Not Found`: Upload session not found or expired
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Failed to generate URL

**Notes:**

- Presigned URLs expire after 1 hour (configurable via `S3_MULTIPART_URL_EXPIRATION`)
- If a part was already uploaded, the response includes the existing ETag
- Upload parts directly to S3 using PUT request with the presigned URL

---

### POST /api/v3/upload/parts - Register Uploaded Part

Register a successfully uploaded part with its ETag. Called after uploading a chunk to S3.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Request Body:**

```json
{
  "upload_id": "550e8400-e29b-41d4-a716-446655440000",
  "part_number": 1,
  "etag": "d41d8cd98f00b204e9800998ecf8427e"
}
```

**Response (200 OK):**

```json
{
  "status": "part_registered",
  "part_number": 1
}
```

**Response Codes:**

- `200 OK`: Part registered successfully
- `404 Not Found`: Upload session not found
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Failed to register part

**Notes:**

- ETag is obtained from the S3 PUT response header
- Remove quotes from ETag before sending (e.g., `"etag"` → `etag`)

---

### POST /api/v3/upload/complete - Complete Upload

Complete the multipart upload by combining all uploaded parts.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Request Body:**

```json
{
  "upload_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response (200 OK):**

```json
{
  "status": "completed",
  "file_key": "uploads/123/20240115_143022_large-dataset.csv",
  "s3_url": "https://bucket.s3.us-east-1.amazonaws.com/uploads/123/20240115_143022_large-dataset.csv",
  "location": "https://bucket.s3.us-east-1.amazonaws.com/uploads/123/20240115_143022_large-dataset.csv"
}
```

**Response Codes:**

- `200 OK`: Upload completed successfully
- `400 Bad Request`: No parts uploaded
- `404 Not Found`: Upload session not found
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Failed to complete upload

**Notes:**

- All parts must be uploaded before completing
- Session is automatically cleaned up after completion
- File becomes available in S3 immediately after completion

---

### POST /api/v3/upload/abort - Abort Upload

Abort an incomplete multipart upload and clean up resources.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Request Body:**

```json
{
  "upload_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response (200 OK):**

```json
{
  "status": "aborted",
  "upload_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response Codes:**

- `200 OK`: Upload aborted successfully (or session not found)
- `401 Unauthorized`: Authentication required

**Notes:**

- Aborts the multipart upload in S3
- Cleans up the upload session
- Prevents orphaned multipart uploads and associated costs

---

### GET /api/v3/upload/status/{upload_id} - Get Upload Status

Get the current status of an upload session, including which parts have been uploaded. Used for resuming interrupted uploads.

**Headers:**

- `Authorization: Bearer <access_token>` (required)

**Path Parameters:**

- `upload_id` (string, required): Upload session identifier

**Response (200 OK):**

```json
{
  "upload_id": "550e8400-e29b-41d4-a716-446655440000",
  "file_key": "uploads/123/20240115_143022_large-dataset.csv",
  "file_size": 5368709120,
  "chunk_size": 104857600,
  "uploaded_parts": [1, 2, 3, 4, 5],
  "total_parts": 52,
  "uploaded_bytes": 524288000,
  "status": "in_progress"
}
```

**Response Codes:**

- `200 OK`: Upload status retrieved successfully
- `404 Not Found`: Upload session not found or expired
- `401 Unauthorized`: Authentication required

**Notes:**

- Session expires after 24 hours (configurable via `UPLOAD_SESSION_TTL`)
- Use `uploaded_parts` to determine which parts need to be uploaded
- Status can be: `in_progress`, `completed`, or `aborted`

---

## Response Schemas

### InitiateUploadResponse

```typescript
{
  upload_id: string;        // Unique upload identifier
  file_key: string;         // S3 object key (path)
  s3_upload_id: string;     // S3 multipart upload ID
  chunk_size: number;       // Chunk size in bytes
  num_parts: number;        // Total number of parts
}
```

### PresignedUrlResponse

```typescript
{
  presigned_url: string | null;  // Presigned URL for uploading part
  part_number: number;           // Part number (1-indexed)
  already_uploaded: boolean;      // Whether part was already uploaded
  etag?: string;                  // ETag if already uploaded
}
```

### CompleteUploadResponse

```typescript
{
  status: string;           // Upload status ("completed")
  file_key: string;        // S3 object key (path)
  s3_url: string;          // Public S3 URL
  location?: string;       // S3 location URL
}
```

### UploadStatusResponse

```typescript
{
  upload_id: string;       // Upload session identifier
  file_key: string;        // S3 object key (path)
  file_size: number;       // Total file size in bytes
  chunk_size: number;      // Chunk size in bytes
  uploaded_parts: number[]; // List of uploaded part numbers
  total_parts: number;     // Total number of parts
  uploaded_bytes: number;  // Total bytes uploaded
  status: string;          // Upload status
}
```

---

## Use Cases

### 1. Upload a 5GB File

```bash
# Step 1: Initiate upload
POST /api/v3/upload/initiate
{
  "filename": "large-dataset.csv",
  "file_size": 5368709120,
  "content_type": "text/csv"
}

# Step 2: For each part (1 to num_parts):
#   a. Get presigned URL
GET /api/v3/upload/presigned-url/{upload_id}/{part_number}

#   b. Upload chunk directly to S3
PUT {presigned_url}
Body: <chunk data>

#   c. Register part with ETag
POST /api/v3/upload/parts
{
  "upload_id": "...",
  "part_number": 1,
  "etag": "..."
}

# Step 3: Complete upload
POST /api/v3/upload/complete
{
  "upload_id": "..."
}
```

### 2. Resume Interrupted Upload

```bash
# Step 1: Get upload status
GET /api/v3/upload/status/{upload_id}

# Step 2: Upload only missing parts (not in uploaded_parts array)
#   Follow steps 2a-2c from Use Case 1 for missing parts only

# Step 3: Complete upload
POST /api/v3/upload/complete
{
  "upload_id": "..."
}
```

### 3. Cancel Upload

```bash
POST /api/v3/upload/abort
{
  "upload_id": "..."
}
```

---

## Error Handling

### File Size Exceeds Limit

**Request:**

```bash
POST /api/v3/upload/initiate
{
  "filename": "huge-file.csv",
  "file_size": 15000000000  // 15GB
}
```

**Response (400 Bad Request):**

```json
{
  "detail": "File size exceeds 10GB limit"
}
```

### Upload Session Not Found

**Request:**

```bash
GET /api/v3/upload/status/invalid-upload-id
```

**Response (404 Not Found):**

```json
{
  "detail": "Upload session not found or expired"
}
```

### No Parts Uploaded

**Request:**

```bash
POST /api/v3/upload/complete
{
  "upload_id": "..."
}
# When no parts have been uploaded
```

**Response (400 Bad Request):**

```json
{
  "detail": "No parts uploaded"
}
```

### Server Error

**Response (500 Internal Server Error):**

```json
{
  "detail": "Failed to initiate upload: <error message>"
}
```

---

## Notes

- All endpoints require JWT authentication
- Upload sessions expire after 24 hours of inactivity
- Maximum file size: 10GB (configurable)
- Default chunk size: 100MB (configurable)
- Supports resumable uploads via status endpoint
- Presigned URLs expire after 1 hour
- Files are stored in S3 under `uploads/{user_id}/{timestamp}_{filename}`
- Automatic cleanup of expired sessions prevents orphaned uploads

