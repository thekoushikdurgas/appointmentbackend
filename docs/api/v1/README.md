# API v1 Documentation Index

Complete documentation for Appointment360 API v1 and v3 endpoints.

## Overview

The v1 documentation folder contains documentation for both legacy v1 endpoints and modern v3 endpoints. This organization reflects the evolution of the API while maintaining backward compatibility.

## API Versions

- **v1** (`/api/v1/`): Legacy endpoints for basic operations
- **v3** (`/api/v3/`): Modern, feature-rich endpoints

## Documentation Files

### Authentication & User Management

- **[User API](./user.md)** - User authentication, registration, profile management, and role-based access
- **[Root API](./root.md)** - API metadata and basic information
- **[Health API](./health.md)** - Health checks and system monitoring

### Data Management

- **[Contacts API](./contacts.md)** - Contact management, querying, filtering, and CRUD operations
- **[Companies API](./company.md)** - Company management, querying, filtering, and CRUD operations
- **[Activities API](./activities.md)** - Activity tracking and history

### File Operations

- **[S3 File Operations API](./s3.md)** - List, download, and read CSV files from S3 buckets
- **[Large File Upload API](./upload.md)** - Upload large files (5GB+) to S3 using multipart uploads with resumable support
- **[Export API](./export.md)** - Export contacts and companies to CSV files

### Email & Communication

- **[Email API](./email.md)** - Email finding, verification, bulk operations, and export
- **[LinkedIn API](./linkdin.md)** - LinkedIn integration and data retrieval

### Business Features

- **[Billing API](./billing.md)** - Subscription management, billing, and payment processing
- **[Marketing API](./marketing.md)** - Marketing campaign features and management
- **[Dashboard Pages API](./dashboard_pages.md)** - Dashboard customization and page management
- **[Scrape API](./scrape.md)** - Web scraping features and data extraction

### System & Configuration

- **[Usage Tracking API](./usage.md)** - Feature usage tracking and limits
- **[Environment Variables](./ENVIRONMENT_VARIABLES.md)** - Complete configuration reference

## Common Workflows

### File Upload Workflow

1. **Upload Large Files**: Use [Large File Upload API](./upload.md) to upload files up to 10GB
   - Files are chunked and uploaded in parallel
   - Supports resumable uploads
   - Files stored in S3 under `uploads/{user_id}/`

2. **List Files**: Use [S3 File Operations API](./s3.md) to list uploaded files
   - Filter by prefix
   - Get file metadata

3. **Download Files**: Use [S3 File Operations API](./s3.md) to download files
   - Full file download
   - Paginated data reading for large CSV files

### Export Workflow

1. **Create Export**: Use [Export API](./export.md) to create contact/company exports
   - Supports chunked exports for large datasets
   - Background processing

2. **Check Status**: Monitor export progress via status endpoint

3. **Download Export**: Download completed exports
   - Exports stored in S3
   - Accessible via S3 File Operations API

### Email Finding Workflow

1. **Find Emails**: Use [Email API](./email.md) to find emails by name and domain
2. **Verify Emails**: Use bulk or single verification endpoints
3. **Export Results**: Export verified emails to CSV

## Quick Reference

### Base URL
```
http://34.229.94.175:8000
```

### Authentication
Most endpoints require JWT authentication:
```
Authorization: Bearer <access_token>
```

### API Version Endpoints

| Feature | v1 Endpoints | v3 Endpoints |
|---------|-------------|--------------|
| Users | `/api/v1/users/` | `/api/v3/users/` |
| Contacts | - | `/api/v3/contacts/` |
| Companies | - | `/api/v3/companies/` |
| Email | - | `/api/v3/email/` |
| S3 Files | - | `/api/v3/s3/files` |
| Upload | - | `/api/v3/upload/` |
| Exports | - | `/api/v3/exports/` |
| Usage | `/api/v1/usage/` | - |

## Related Documentation

- [API v2 Documentation](../v2/) - Extended features (Analytics, AI Chat, Gemini)
- [Main API Documentation](../README.md) - Overview and navigation

---

**Note**: This documentation is maintained alongside the codebase. For the most up-to-date information, refer to the individual API documentation files.

