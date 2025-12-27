# API Reorganization Migration Summary

**Date**: 2025-01-XX  
**Status**: ✅ Completed

## Overview

This document summarizes the major reorganization of API endpoints across versions v1, v2, v3, and v4. The reorganization was done to improve API structure, logical grouping, and maintainability.

## New API Structure

### V1 - User, Auth & System Endpoints (42 endpoints)

**Purpose**: All user-related, authentication, billing, usage tracking, and system endpoints.

**Endpoints**:
- **Authentication** (`/api/v1/auth/`): register, login, logout, session, refresh
- **Users** (`/api/v1/users/`): profile, avatar, admin promotion, user management, stats, history
- **Billing** (`/api/v1/billing/`): subscriptions, plans, addons, invoices, admin management
- **Usage** (`/api/v1/usage/`): current usage, track usage
- **Health** (`/api/v1/health/`): VQL health check, VQL stats
- **Root** (`/api/v1/`): root endpoint, health endpoint

**Files**:
- `backend/app/api/v1/endpoints/auth.py`
- `backend/app/api/v1/endpoints/users.py`
- `backend/app/api/v1/endpoints/billing.py`
- `backend/app/api/v1/endpoints/usage.py`
- `backend/app/api/v1/endpoints/health.py`
- `backend/app/api/v1/endpoints/root.py`

### V2 - AI Features Only (10 endpoints)

**Purpose**: All AI-related endpoints including chat and Gemini integration.

**Endpoints**:
- **AI Chats** (`/api/v2/ai-chats/`): CRUD operations, message streaming
- **AI Chat WebSocket** (`/api/v2/ai-chats/ws/{chat_id}`): real-time chat
- **Gemini** (`/api/v2/gemini/`): email analyze, company summary

**Files**:
- `backend/app/api/v2/endpoints/ai_chats.py`
- `backend/app/api/v2/endpoints/ai_chat_websocket.py`
- `backend/app/api/v2/endpoints/gemini.py`

### V3 - Data Operations (36 endpoints)

**Purpose**: All data query, export, and integration endpoints.

**Endpoints**:
- **Companies** (`/api/v3/companies/`): query, count, detail, contacts-related
- **Contacts** (`/api/v3/contacts/`): query, count, detail
- **Email** (`/api/v3/email/`): finder, verifier, bulk operations, export
- **Exports** (`/api/v3/exports/`): contacts/companies export, status, download
- **LinkedIn** (`/api/v3/linkedin/`): LinkedIn URL-based search
- **Activities** (`/api/v3/activities/`): user activity history
- **S3** (`/api/v3/s3/`): file list, file download
- **Sales Navigator** (`/api/v3/sales-navigator/`): scrape Sales Navigator HTML

**Files**:
- `backend/app/api/v3/endpoints/companies.py`
- `backend/app/api/v3/endpoints/contacts.py`
- `backend/app/api/v3/endpoints/email.py`
- `backend/app/api/v3/endpoints/exports.py`
- `backend/app/api/v3/endpoints/linkedin.py`
- `backend/app/api/v3/endpoints/activities.py`
- `backend/app/api/v3/endpoints/s3.py`
- `backend/app/api/v3/endpoints/sales_navigator.py`

### V4 - Admin & Marketing (15 endpoints)

**Purpose**: Public marketing pages and admin management endpoints.

**Endpoints**:
- **Marketing** (`/api/v4/marketing/`): public marketing pages
- **Dashboard Pages** (`/api/v4/dashboard-pages/`): public dashboard pages
- **Admin Marketing** (`/api/v4/admin/marketing/`): admin marketing page management
- **Admin Dashboard Pages** (`/api/v4/admin/dashboard-pages/`): admin dashboard page management

**Files**:
- `backend/app/api/v4/endpoints/marketing.py`
- `backend/app/api/v4/endpoints/dashboard_pages.py`
- `backend/app/api/v4/endpoints/admin_marketing.py`
- `backend/app/api/v4/endpoints/admin_dashboard_pages.py`

## Migration Path

### Endpoints Moved from V2 → V1

| Old Path | New Path | Endpoint File |
|----------|----------|---------------|
| `/api/v2/auth/*` | `/api/v1/auth/*` | `auth.py` |
| `/api/v2/users/*` | `/api/v1/users/*` | `users.py` |
| `/api/v2/billing/*` | `/api/v1/billing/*` | `billing.py` |
| `/api/v2/usage/*` | `/api/v1/usage/*` | `usage.py` |

### Endpoints Moved from V2 → V3

| Old Path | New Path | Endpoint File |
|----------|----------|---------------|
| `/api/v2/email/*` | `/api/v3/email/*` | `email.py` |
| `/api/v2/exports/*` | `/api/v3/exports/*` | `exports.py` |
| `/api/v2/linkedin/*` | `/api/v3/linkedin/*` | `linkedin.py` |
| `/api/v2/activities/*` | `/api/v3/activities/*` | `activities.py` |

### Endpoints Moved from V1 → V3

| Old Path | New Path | Endpoint File |
|----------|----------|---------------|
| `/api/v1/companies/*` | `/api/v3/companies/*` | `companies.py` |
| `/api/v1/contacts/*` | `/api/v3/contacts/*` | `contacts.py` |

### Endpoints Moved from V4 → V3

| Old Path | New Path | Endpoint File |
|----------|----------|---------------|
| `/api/v4/sales-navigator/*` | `/api/v3/sales-navigator/*` | `sales_navigator.py` |

### Endpoints Moved from V1 → V4

| Old Path | New Path | Endpoint File |
|----------|----------|---------------|
| `/api/v1/marketing/*` | `/api/v4/marketing/*` | `marketing.py` |
| `/api/v1/dashboard-pages/*` | `/api/v4/dashboard-pages/*` | `dashboard_pages.py` |
| `/api/v1/admin/marketing/*` | `/api/v4/admin/marketing/*` | `admin_marketing.py` |
| `/api/v1/admin/dashboard-pages/*` | `/api/v4/admin/dashboard-pages/*` | `admin_dashboard_pages.py` |

## Breaking Changes

⚠️ **IMPORTANT**: This reorganization introduces breaking changes. All client applications must update their API endpoint paths.

### Authentication Endpoints

**Before**:
- `POST /api/v2/auth/register`
- `POST /api/v2/auth/login`
- `POST /api/v2/auth/logout`
- `GET /api/v2/auth/session`
- `POST /api/v2/auth/refresh`

**After**:
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/session`
- `POST /api/v1/auth/refresh`

### User Endpoints

**Before**:
- `GET /api/v2/users/profile`
- `PUT /api/v2/users/profile`
- `GET /api/v2/users/`

**After**:
- `GET /api/v1/users/profile`
- `PUT /api/v1/users/profile`
- `GET /api/v1/users/`

### Billing Endpoints

**Before**:
- `GET /api/v2/billing/`
- `GET /api/v2/billing/plans/`
- `POST /api/v2/billing/subscribe/`

**After**:
- `GET /api/v1/billing/`
- `GET /api/v1/billing/plans/`
- `POST /api/v1/billing/subscribe/`

### Data Endpoints

**Before**:
- `POST /api/v1/companies/query`
- `POST /api/v1/contacts/query`
- `GET /api/v2/email/finder/`
- `POST /api/v2/exports/contacts/export`

**After**:
- `POST /api/v3/companies/query`
- `POST /api/v3/contacts/query`
- `GET /api/v3/email/finder/`
- `POST /api/v3/exports/contacts/export`

## Files Modified

### Router Files
- `backend/app/api/v1/api.py` - Updated to include auth, users, billing, usage, health, root
- `backend/app/api/v2/api.py` - Updated to only include ai_chats, ai_chat_websocket, gemini
- `backend/app/api/v3/api.py` - Updated to include companies, contacts, email, exports, linkedin, activities, s3, sales_navigator
- `backend/app/api/v4/api.py` - Updated to include marketing, dashboard_pages, admin_marketing, admin_dashboard_pages

### Endpoint Files Moved
- All endpoint files were copied to their new locations
- Original files were deleted after successful migration

## Verification

✅ All router files compile successfully  
✅ No linter errors  
✅ File structure matches target organization  
✅ Router registrations updated correctly  

## Next Steps

1. **Update Client Applications**: All frontend and external clients must update their API endpoint paths
2. **Update Documentation**: API documentation files need to be updated with new paths
3. **Update Postman Collections**: Postman collection generator script needs path updates
4. **Update Tests**: Integration tests may need endpoint path updates
5. **Consider Deprecation**: If maintaining backward compatibility, add deprecation warnings

## Rollback Plan

If rollback is needed:
1. Restore endpoint files from git history
2. Revert router file changes
3. Restore original API structure

## Notes

- All endpoint functionality remains unchanged - only paths have changed
- Authentication mechanisms remain the same
- Request/response schemas remain unchanged
- Database models and services remain unchanged

