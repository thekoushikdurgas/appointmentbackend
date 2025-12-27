# Environment Variables Reference

Complete reference for all environment variables used in the Appointment360 backend application.

## Table of Contents

- [Database Configuration](#database-configuration)
- [AWS S3 Configuration](#aws-s3-configuration)
- [Large File Upload Configuration](#large-file-upload-configuration)
- [Authentication & Security](#authentication--security)
- [Server Configuration](#server-configuration)
- [File Upload Configuration](#file-upload-configuration)

---

## Database Configuration

### `DATABASE_URL`

PostgreSQL database connection string.

**Format:**
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```

**Required:** Yes  
**Default:** None

---

## AWS S3 Configuration

### `AWS_ACCESS_KEY_ID`

AWS access key ID for S3 operations.

**Required:** Yes (if using S3)  
**Default:** None

### `AWS_SECRET_ACCESS_KEY`

AWS secret access key for S3 operations.

**Required:** Yes (if using S3)  
**Default:** None

### `AWS_REGION`

AWS region for S3 bucket.

**Required:** No  
**Default:** `us-east-1`

### `S3_BUCKET_NAME`

Primary S3 bucket name for file storage.

**Required:** Yes (if using S3)  
**Default:** None

### `S3_V3_BUCKET_NAME`

S3 bucket name for v3 API CSV file operations.

**Required:** No  
**Default:** `tkdrawcsvdata`

### `S3_AVATARS_PREFIX`

S3 prefix for avatar images.

**Required:** No  
**Default:** `avatars/`

### `S3_EXPORTS_PREFIX`

S3 prefix for exported files.

**Required:** No  
**Default:** `exports/`

### `S3_USE_PRESIGNED_URLS`

Whether to use presigned URLs for S3 file access.

**Required:** No  
**Default:** `true`

### `S3_PRESIGNED_URL_EXPIRATION`

Presigned URL expiration time in seconds.

**Required:** No  
**Default:** `3600` (1 hour)

---

## Large File Upload Configuration

### `S3_UPLOAD_PREFIX`

S3 prefix for uploaded files via multipart upload.

**Required:** No  
**Default:** `uploads/`

**Example:**
```bash
S3_UPLOAD_PREFIX=uploads/
```

### `S3_MULTIPART_CHUNK_SIZE`

Chunk size for multipart uploads in bytes.

**Required:** No  
**Default:** `104857600` (100MB)

**Recommended Values:**
- Small files (< 1GB): `52428800` (50MB)
- Medium files (1-5GB): `104857600` (100MB)
- Large files (5-10GB): `104857600` (100MB)

**Example:**
```bash
S3_MULTIPART_CHUNK_SIZE=104857600
```

### `S3_MULTIPART_MAX_FILE_SIZE`

Maximum file size for multipart uploads in bytes.

**Required:** No  
**Default:** `10737418240` (10GB)

**Note:** AWS S3 supports up to 5TB per object, but this limit can be adjusted based on your needs.

**Example:**
```bash
S3_MULTIPART_MAX_FILE_SIZE=10737418240
```

### `S3_MULTIPART_URL_EXPIRATION`

Presigned URL expiration time for multipart upload parts in seconds.

**Required:** No  
**Default:** `3600` (1 hour)

**Note:** Should be long enough to allow upload of all parts. For very large files, consider increasing this value.

**Example:**
```bash
S3_MULTIPART_URL_EXPIRATION=3600
```

### `UPLOAD_SESSION_TTL`

Upload session time-to-live in seconds. Sessions expire after this period of inactivity.

**Required:** No  
**Default:** `86400` (24 hours)

**Note:** Expired sessions cannot be resumed. For production, consider using Redis with TTL instead of in-memory storage.

**Example:**
```bash
UPLOAD_SESSION_TTL=86400
```

---

## Authentication & Security

### `SECRET_KEY`

Secret key for JWT token signing and encryption.

**Required:** Yes  
**Default:** None

**Security Note:** Must be a strong, random string. Never commit to version control.

### `ALGORITHM`

JWT algorithm for token signing.

**Required:** No  
**Default:** `HS256`

### `ACCESS_TOKEN_EXPIRE_MINUTES`

Access token expiration time in minutes.

**Required:** No  
**Default:** `30`

### `REFRESH_TOKEN_EXPIRE_DAYS`

Refresh token expiration time in days.

**Required:** No  
**Default:** `7`

---

## Server Configuration

### `BASE_URL`

Base URL for generating full avatar URLs and other absolute URLs.

**Required:** No  
**Default:** `http://localhost:8000`

**Example:**
```bash
BASE_URL=http://54.87.173.234:8000
```

### `USE_PROXY_HEADERS`

Whether to use proxy headers for request information.

**Required:** No  
**Default:** `true`

### `FORWARDED_ALLOW_IPS`

Comma-separated list of allowed proxy IPs.

**Required:** No  
**Default:** `*`

---

## File Upload Configuration

### `UPLOAD_DIR`

Local directory for file uploads (when not using S3).

**Required:** No  
**Default:** `./uploads`

### `MEDIA_URL`

URL prefix for media files.

**Required:** No  
**Default:** `/media`

### `MAX_UPLOAD_CHUNK_SIZE`

Maximum chunk size for local chunked uploads in bytes.

**Required:** No  
**Default:** Varies

### `MAX_UPLOAD_SIZE`

Maximum upload size in bytes.

**Required:** No  
**Default:** Varies

---

## Example `.env` File

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/appointment360

# AWS S3
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket-name
S3_V3_BUCKET_NAME=tkdrawcsvdata
S3_AVATARS_PREFIX=avatars/
S3_EXPORTS_PREFIX=exports/
S3_USE_PRESIGNED_URLS=true
S3_PRESIGNED_URL_EXPIRATION=3600

# Large File Upload
S3_UPLOAD_PREFIX=uploads/
S3_MULTIPART_CHUNK_SIZE=104857600
S3_MULTIPART_MAX_FILE_SIZE=10737418240
S3_MULTIPART_URL_EXPIRATION=3600
UPLOAD_SESSION_TTL=86400

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Server
BASE_URL=http://localhost:8000
USE_PROXY_HEADERS=true
FORWARDED_ALLOW_IPS=*

# File Upload
UPLOAD_DIR=./uploads
MEDIA_URL=/media
```

---

## Production Recommendations

1. **Use Redis for Session Storage**: Replace in-memory `UploadSessionManager` with Redis for production scalability.

2. **Increase Session TTL**: For large file uploads, consider increasing `UPLOAD_SESSION_TTL` to 48-72 hours.

3. **Monitor S3 Costs**: Large file uploads can incur S3 storage and request costs. Monitor usage regularly.

4. **Set Appropriate Chunk Sizes**: Balance between upload speed and number of requests. 100MB is a good default.

5. **Use Environment-Specific Values**: Use different values for development, staging, and production environments.

6. **Secure Secrets**: Never commit `.env` files to version control. Use secret management services in production.

---

## Notes

- All file size values are in bytes
- All time values are in seconds unless otherwise specified
- Boolean values can be `true`, `false`, `1`, or `0`
- Environment variables are case-sensitive
- Use `.env` file for local development
- Use environment variables or secret management for production

