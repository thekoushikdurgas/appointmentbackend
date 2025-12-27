# Appointment360 API Documentation

Complete API documentation for the Appointment360 backend API, organized by API version.

## Documentation Structure

This documentation is organized into API versions:

- **[v1 Documentation](./v1/)** - Core API endpoints (v1 and v3)
- **[v2 Documentation](./v2/)** - Extended features and analytics

## Quick Navigation

### Core APIs (v1/v3)

#### Authentication & User Management
- [User API](./v1/user.md) - Authentication, registration, profile management
- [Root API](./v1/root.md) - API metadata and basic information
- [Health API](./v1/health.md) - Health checks and monitoring

#### Data Management
- [Contacts API](./v1/contacts.md) - Contact management and querying
- [Companies API](./v1/company.md) - Company management and querying
- [Activities API](./v1/activities.md) - Activity tracking

#### File Operations
- [S3 File Operations API](./v1/s3.md) - List, download, and read CSV files from S3
- [Large File Upload API](./v1/upload.md) - Upload large files (5GB+) to S3 using multipart uploads
- [Export API](./v1/export.md) - Export contacts and companies to CSV

#### Email & Communication
- [Email API](./v1/email.md) - Email finding, verification, and bulk operations
- [LinkedIn API](./v1/linkdin.md) - LinkedIn integration features

#### Business Features
- [Billing API](./v1/billing.md) - Subscription and billing management
- [Marketing API](./v1/marketing.md) - Marketing campaign features
- [Dashboard Pages API](./v1/dashboard_pages.md) - Dashboard customization
- [Scrape API](./v1/scrape.md) - Web scraping features

#### System
- [Usage Tracking API](./v1/usage.md) - Feature usage tracking
- [Environment Variables](./v1/ENVIRONMENT_VARIABLES.md) - Configuration reference

### Extended Features (v2)

- [Analytics API](./v2/analytics.md) - Performance metrics and analytics
- [AI Chat API](./v2/ai_chat.md) - AI-powered chat features
- [Gemini API](./v2/gemini.md) - Google Gemini integration

## API Versions

### Version 1 (`/api/v1/`)
Legacy endpoints and basic operations:
- User authentication
- Usage tracking
- Health checks
- Root metadata

### Version 2 (`/api/v2/`)
Extended features:
- Analytics and performance monitoring
- AI chat functionality
- Gemini integration

### Version 3 (`/api/v3/`)
Modern, feature-rich endpoints:
- Contacts and companies management
- Email finding and verification
- S3 file operations
- Large file uploads
- Export operations
- LinkedIn integration

## Base URL

For production, use:

```txt
http://34.229.94.175:8000
```

## Authentication

Most endpoints require JWT authentication via the `Authorization` header:

```txt
Authorization: Bearer <access_token>
```

Tokens are obtained through the login or register endpoints in the [User API](./v1/user.md).

**Note:** Some endpoints (like root and health) are publicly accessible and do not require authentication.

## Getting Started

1. **Authentication**: Start with the [User API](./v1/user.md) to register/login and obtain access tokens
2. **Explore Data**: Use [Contacts API](./v1/contacts.md) and [Companies API](./v1/company.md) to query data
3. **File Operations**: 
   - Upload large files using [Large File Upload API](./v1/upload.md)
   - List and download files using [S3 File Operations API](./v1/s3.md)
   - Export data using [Export API](./v1/export.md)
4. **Email Features**: Use [Email API](./v1/email.md) for email finding and verification
5. **Configuration**: Review [Environment Variables](./v1/ENVIRONMENT_VARIABLES.md) for setup

## Common Workflows

### Uploading Large Files

1. Use [Large File Upload API](./v1/upload.md) to upload files up to 10GB
2. Files are stored in S3 under `uploads/{user_id}/`
3. List uploaded files using [S3 File Operations API](./v1/s3.md)
4. Download files using S3 File Operations API

### Exporting Data

1. Use [Export API](./v1/export.md) to create exports
2. Check export status
3. Download completed exports
4. Large exports are stored in S3 and can be accessed via S3 File Operations API

### Email Finding

1. Use [Email API](./v1/email.md) to find emails by name and domain
2. Verify emails using bulk or single verification endpoints
3. Export verified emails to CSV

## Error Handling

All APIs follow consistent error response formats:

- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Authentication required or invalid token
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation errors
- `500 Internal Server Error`: Server error

See individual API documentation for specific error responses.

## Rate Limiting

Some endpoints may have rate limits. Check individual API documentation for details.

## Support

For issues or questions:
1. Check the specific API documentation
2. Review [Environment Variables](./v1/ENVIRONMENT_VARIABLES.md) for configuration
3. Check error responses for detailed messages

---

**Last Updated**: Documentation maintained alongside codebase updates

