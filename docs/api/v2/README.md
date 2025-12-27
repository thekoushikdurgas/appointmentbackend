# API v2 Documentation Index

Complete documentation for Appointment360 API v2 endpoints.

## Overview

API v2 provides extended features including analytics, AI chat functionality, and integrations with external services.

## Documentation Files

- **[Analytics API](./analytics.md)** - Performance metrics submission and monitoring
- **[AI Chat API](./ai_chat.md)** - AI-powered chat features and conversations
- **[Gemini API](./gemini.md)** - Google Gemini integration

## API Version

All v2 endpoints are under `/api/v2/`

## Base URL

For production, use:

```txt
http://34.229.94.175:8000
```

## Authentication

All v2 endpoints require JWT authentication via the `Authorization` header:

```txt
Authorization: Bearer <access_token>
```

Tokens are obtained through the login or register endpoints in the [User API](../v1/user.md).

## Quick Reference

### Analytics
- Performance metrics submission
- Web vitals tracking
- Custom metrics

### AI Chat
- Conversational AI features
- Chat history management
- Context-aware responses

### Gemini
- Google Gemini API integration
- AI-powered features

## Related Documentation

- [API v1 Documentation](../v1/) - Core API endpoints
- [Main API Documentation](../README.md) - Overview and navigation

---

**Note**: This documentation is maintained alongside the codebase. For the most up-to-date information, refer to the individual API documentation files.

