# API Endpoint to SQL File Mapping

This document maps all API endpoints to their corresponding SQL documentation files in the `sql/apis` directory.

## API Version 1 Endpoints

### Root Endpoints (`/api/v1/`)

| Endpoint | Method | SQL File | Status |
|----------|--------|----------|--------|
| `/` | GET | `system/root_metadata.sql` | ✅ Exists |
| `/health/` | GET | `system/health_check.sql` | ✅ Exists |

### Contacts Endpoints (`/api/v1/contacts/`)

| Endpoint | Method | SQL File | Status |
|----------|--------|----------|--------|
| `/` | GET | `v1/contacts/core/list_contacts.sql` | ✅ Exists |
| `/count/` | GET | `v1/contacts/core/count_contacts.sql` | ✅ Exists |
| `/count/uuids/` | GET | `v1/contacts/core/get_contact_uuids.sql` | ✅ Exists |
| `/` | POST | `v1/contacts/core/create_contact.sql` | ✅ Exists |
| `/{contact_uuid}/` | GET | `v1/contacts/core/retrieve_contact.sql` | ✅ Exists |
| `/title/` | GET | `v1/contacts/attributes/list_titles.sql` | ✅ Exists |
| `/company/` | GET | `v1/contacts/attributes/list_companies.sql` | ✅ Exists |
| `/industry/` | GET | `v1/contacts/attributes/list_industries.sql` | ✅ Exists |
| `/keywords/` | GET | `v1/contacts/attributes/list_keywords.sql` | ✅ Exists |
| `/technologies/` | GET | `v1/contacts/attributes/list_technologies.sql` | ✅ Exists |
| `/company_address/` | GET | `v1/contacts/attributes/list_company_addresses.sql` | ✅ Exists |
| `/contact_address/` | GET | `v1/contacts/attributes/list_contact_addresses.sql` | ✅ Exists |
| `/department/` | GET | `v1/contacts/attributes/list_departments.sql` | ✅ Exists |
| `/seniority/` | GET | `v1/contacts/attributes/list_seniority.sql` | ✅ Exists |
| `/company/domain/` | GET | `v1/contacts/attributes/list_company_domains.sql` | ✅ Exists |

**Total: 15 endpoints - All have SQL files**

### Companies Endpoints (`/api/v1/companies/`)

| Endpoint | Method | SQL File | Status |
|----------|--------|----------|--------|
| `/` | GET | `v1/companies/core/list_companies.sql` | ✅ Exists |
| `/count/` | GET | `v1/companies/core/count_companies.sql` | ✅ Exists |
| `/count/uuids/` | GET | `v1/companies/core/get_company_uuids.sql` | ✅ Exists |
| `/` | POST | `v1/companies/core/create_company.sql` | ✅ Exists |
| `/{company_uuid}/` | PUT | `v1/companies/core/update_company.sql` | ✅ Exists |
| `/{company_uuid}/` | DELETE | `v1/companies/core/delete_company.sql` | ✅ Exists |
| `/{company_uuid}/` | GET | `v1/companies/core/retrieve_company.sql` | ✅ Exists |
| `/name/` | GET | `v1/companies/attributes/list_names.sql` | ✅ Exists |
| `/industry/` | GET | `v1/companies/attributes/list_industries.sql` | ✅ Exists |
| `/keywords/` | GET | `v1/companies/attributes/list_keywords.sql` | ✅ Exists |
| `/technologies/` | GET | `v1/companies/attributes/list_technologies.sql` | ✅ Exists |
| `/address/` | GET | `v1/companies/attributes/list_addresses.sql` | ✅ Exists |
| `/city/` | GET | `v1/companies/attributes/list_cities.sql` | ✅ Exists |
| `/state/` | GET | `v1/companies/attributes/list_states.sql` | ✅ Exists |
| `/country/` | GET | `v1/companies/attributes/list_countries.sql` | ✅ Exists |
| `/company/{company_uuid}/contacts/` | GET | `v1/companies/contacts/list_company_contacts.sql` | ✅ Exists |
| `/company/{company_uuid}/contacts/count/` | GET | `v1/companies/contacts/count_company_contacts.sql` | ✅ Exists |
| `/company/{company_uuid}/contacts/count/uuids/` | GET | `v1/companies/contacts/list_contact_attributes.sql` | ⚠️ Needs verification |
| `/company/{company_uuid}/contacts/first_name/` | GET | ❌ Missing | ❌ Missing |
| `/company/{company_uuid}/contacts/last_name/` | GET | ❌ Missing | ❌ Missing |
| `/company/{company_uuid}/contacts/title/` | GET | ❌ Missing | ❌ Missing |
| `/company/{company_uuid}/contacts/seniority/` | GET | ❌ Missing | ❌ Missing |
| `/company/{company_uuid}/contacts/department/` | GET | ❌ Missing | ❌ Missing |
| `/company/{company_uuid}/contacts/email_status/` | GET | ❌ Missing | ❌ Missing |

**Total: 24 endpoints - 18 have SQL files, 6 missing**

### Imports Endpoints (`/api/v1/contacts/import/`)

| Endpoint | Method | SQL File | Status |
|----------|--------|----------|--------|
| `/` | GET | `v1/imports/import_info.sql` | ✅ Exists |
| `/` | POST | `v1/imports/upload_import.sql` | ✅ Exists |
| `/{job_id}/` | GET | `v1/imports/import_job_detail.sql` | ✅ Exists |
| `/{job_id}/errors/` | GET | `v1/imports/import_errors.sql` | ✅ Exists |

**Total: 4 endpoints - All have SQL files**

## API Version 2 Endpoints

### Authentication Endpoints (`/api/v2/auth/`)

| Endpoint | Method | SQL File | Status |
|----------|--------|----------|--------|
| `/register/` | POST | `v2/auth/register.sql` | ✅ Exists |
| `/login/` | POST | `v2/auth/login.sql` | ✅ Exists |
| `/logout/` | POST | `v2/auth/logout.sql` | ✅ Exists |
| `/session/` | GET | `v2/auth/session.sql` | ✅ Exists |
| `/refresh/` | POST | `v2/auth/refresh_token.sql` | ✅ Exists |

**Total: 5 endpoints - All have SQL files**

### Users Endpoints (`/api/v2/users/`)

| Endpoint | Method | SQL File | Status |
|----------|--------|----------|--------|
| `/profile/` | GET | `v2/users/get_profile.sql` | ✅ Exists |
| `/profile/` | PUT | `v2/users/update_profile.sql` | ✅ Exists |
| `/profile/avatar/` | POST | `v2/users/upload_avatar.sql` | ✅ Exists |
| `/promote-to-admin/` | POST | `v2/users/promote_to_admin.sql` | ✅ Exists |

**Total: 4 endpoints - All have SQL files**

### AI Chats Endpoints (`/api/v2/ai-chats/`)

| Endpoint | Method | SQL File | Status |
|----------|--------|----------|--------|
| `/` | GET | `v2/ai_chats/list_chats.sql` | ✅ Exists |
| `/` | POST | `v2/ai_chats/create_chat.sql` | ✅ Exists |
| `/{chat_id}/` | GET | `v2/ai_chats/get_chat.sql` | ✅ Exists |
| `/{chat_id}/` | PUT | `v2/ai_chats/update_chat.sql` | ✅ Exists |
| `/{chat_id}/` | DELETE | `v2/ai_chats/delete_chat.sql` | ✅ Exists |

**Total: 5 endpoints - All have SQL files**

### Apollo Endpoints (`/api/v2/apollo/`)

| Endpoint | Method | SQL File | Status |
|----------|--------|----------|--------|
| `/analyze` | POST | `v2/apollo/analyze_url.sql` | ✅ Exists |
| `/analyze/count` | POST | `v2/apollo/analyze_url.sql` | ⚠️ Uses same file |
| `/contacts` | POST | `v2/apollo/search_contacts.sql` | ✅ Exists |
| `/contacts/count` | POST | `v2/apollo/count_contacts.sql` | ✅ Exists |
| `/contacts/count/uuids` | POST | `v2/apollo/get_contact_uuids.sql` | ✅ Exists |

**Total: 5 endpoints - All have SQL files (analyze/count shares analyze_url.sql)**

### Exports Endpoints (`/api/v2/exports/`)

| Endpoint | Method | SQL File | Status |
|----------|--------|----------|--------|
| `/contacts/export` | POST | `v2/exports/create_contact_export.sql` | ✅ Exists |
| `/companies/export` | POST | `v2/exports/create_company_export.sql` | ✅ Exists |
| `/` | GET | `v2/exports/list_exports.sql` | ✅ Exists |
| `/{export_id}/download` | GET | `v2/exports/download_export.sql` | ✅ Exists |
| `/files` | DELETE | `v2/exports/delete_all_csv_files.sql` | ✅ Exists |

**Total: 5 endpoints - All have SQL files**

### Email Finder Endpoints (`/api/v2/email/`)

| Endpoint | Method | SQL File | Status |
|----------|--------|----------|--------|
| `/finder/` | GET | `v2/email_finder/find_emails.sql` | ✅ Exists |

**Total: 1 endpoint - ✅ All have SQL files**

## Summary

### V1 Endpoints

- **Root**: 2 endpoints - ✅ All have SQL files
- **Contacts**: 15 endpoints - ✅ All have SQL files
- **Companies**: 24 endpoints - ⚠️ 18 have SQL files, 6 missing
- **Imports**: 4 endpoints - ✅ All have SQL files
- **V1 Total**: 45 endpoints - 39 have SQL files, 6 missing

### V2 Endpoints

- **Auth**: 5 endpoints - ✅ All have SQL files
- **Users**: 4 endpoints - ✅ All have SQL files
- **AI Chats**: 5 endpoints - ✅ All have SQL files
- **Apollo**: 5 endpoints - ✅ All have SQL files
- **Exports**: 5 endpoints - ✅ All have SQL files
- **Email Finder**: 1 endpoint - ✅ All have SQL files
- **V2 Total**: 25 endpoints - ✅ All have SQL files

### Overall Summary

- **Total Endpoints**: 70
- **Endpoints with SQL files**: 64
- **Missing SQL files**: 6 (all in companies/company/{uuid}/contacts/ attributes)

## Missing SQL Files to Create

1. `v1/companies/contacts/list_first_names.sql` - GET `/company/{company_uuid}/contacts/first_name/`
2. `v1/companies/contacts/list_last_names.sql` - GET `/company/{company_uuid}/contacts/last_name/`
3. `v1/companies/contacts/list_titles.sql` - GET `/company/{company_uuid}/contacts/title/`
4. `v1/companies/contacts/list_seniorities.sql` - GET `/company/{company_uuid}/contacts/seniority/`
5. `v1/companies/contacts/list_departments.sql` - GET `/company/{company_uuid}/contacts/department/`
6. `v1/companies/contacts/list_email_statuses.sql` - GET `/company/{company_uuid}/contacts/email_status/`

## Notes

- WebSocket endpoints are not included as they don't use SQL queries directly
- Some endpoints share SQL files (e.g., Apollo analyze and analyze/count)
- The `list_contact_attributes.sql` file may need to be split or renamed to match specific attribute endpoints
