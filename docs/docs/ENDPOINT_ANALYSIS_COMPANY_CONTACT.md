# Company and Contact Endpoints Analysis

## Executive Summary

This document provides a comprehensive analysis of all endpoints related to **Companies** and **Contacts** sections in the Contact360 backend API.

## Total Endpoint Count

### **Company Endpoints: 35**
### **Contact Endpoints: 30**
### **Combined/Related Endpoints: 13**
### **GRAND TOTAL: 78 Endpoints**

---

## Detailed Breakdown by API Version

### **API Version 1 (v1)** - Core CRUD and Attribute Endpoints

#### **Company Endpoints (25 endpoints)**

**Core CRUD Operations (5 endpoints):**
1. `GET /api/v1/companies/` - List companies (paginated)
2. `GET /api/v1/companies/stream/` - Stream companies (JSONL/CSV)
3. `GET /api/v1/companies/{company_uuid}/` - Get company by UUID
4. `POST /api/v1/companies/` - Create company
5. `PUT /api/v1/companies/{company_uuid}/` - Update company
6. `DELETE /api/v1/companies/{company_uuid}/` - Delete company

**Count/Query Operations (3 endpoints):**
7. `GET /api/v1/companies/count/` - Count companies
8. `GET /api/v1/companies/count/uuids/` - Get company UUIDs

**Attribute List Endpoints (9 endpoints):**
9. `GET /api/v1/companies/name/` - List company names
10. `GET /api/v1/companies/industry/` - List industries
11. `GET /api/v1/companies/keywords/` - List keywords
12. `GET /api/v1/companies/technologies/` - List technologies
13. `GET /api/v1/companies/address/` - List company addresses
14. `GET /api/v1/companies/city/` - List cities
15. `GET /api/v1/companies/state/` - List states
16. `GET /api/v1/companies/country/` - List countries

**Company Contacts Endpoints (7 endpoints):**
17. `GET /api/v1/companies/company/{company_uuid}/contacts/` - List contacts for company
18. `GET /api/v1/companies/company/{company_uuid}/contacts/count/` - Count company contacts
19. `GET /api/v1/companies/company/{company_uuid}/contacts/count/uuids/` - Get contact UUIDs for company
20. `GET /api/v1/companies/company/{company_uuid}/contacts/first_name/` - List first names
21. `GET /api/v1/companies/company/{company_uuid}/contacts/last_name/` - List last names
22. `GET /api/v1/companies/company/{company_uuid}/contacts/title/` - List titles
23. `GET /api/v1/companies/company/{company_uuid}/contacts/seniority/` - List seniorities
24. `GET /api/v1/companies/company/{company_uuid}/contacts/department/` - List departments
25. `GET /api/v1/companies/company/{company_uuid}/contacts/email_status/` - List email statuses

#### **Contact Endpoints (16 endpoints)**

**Core CRUD Operations (4 endpoints):**
1. `GET /api/v1/contacts/` - List contacts (paginated, supports simple view)
2. `GET /api/v1/contacts/stream/` - Stream contacts (JSONL/CSV)
3. `GET /api/v1/contacts/{contact_uuid}/` - Get contact by UUID
4. `POST /api/v1/contacts/` - Create contact

**Count/Query Operations (2 endpoints):**
5. `GET /api/v1/contacts/count/` - Count contacts
6. `GET /api/v1/contacts/count/uuids/` - Get contact UUIDs

**Attribute List Endpoints (10 endpoints):**
7. `GET /api/v1/contacts/title/` - List titles (paginated)
8. `GET /api/v1/contacts/seniority/` - List seniorities (paginated)
9. `GET /api/v1/contacts/department/` - List departments (paginated)
10. `GET /api/v1/contacts/company/` - List company names (paginated)
11. `GET /api/v1/contacts/company/domain/` - List company domains (paginated)
12. `GET /api/v1/contacts/industry/` - List industries (paginated)
13. `GET /api/v1/contacts/keywords/` - List keywords (paginated)
14. `GET /api/v1/contacts/technologies/` - List technologies (paginated)
15. `GET /api/v1/contacts/company_address/` - List company addresses (paginated)
16. `GET /api/v1/contacts/contact_address/` - List contact addresses (paginated)

---

### **API Version 2 (v2)** - Extended Features

#### **Company-Related Endpoints (4 endpoints)**

**Gemini AI (1 endpoint):**
1. `POST /api/v2/gemini/company/summary` - Generate AI company summary

**Email Patterns (1 endpoint):**
2. `GET /api/v2/email-patterns/company/{company_uuid}` - Get email patterns for company

**Exports (1 endpoint):**
3. `POST /api/v2/exports/companies/export` - Export companies to CSV

**LinkedIn (1 endpoint - combined):**
4. `POST /api/v2/linkedin/export` - Export contacts/companies by LinkedIn URLs

#### **Contact-Related Endpoints (9 endpoints)**

**Email Finder (1 endpoint):**
1. `GET /api/v2/email/finder/` - Find emails by contact name and company domain

**Email Export (1 endpoint):**
2. `POST /api/v2/email/export` - Export emails for contacts

**Exports (2 endpoints):**
3. `POST /api/v2/exports/contacts/export` - Export contacts to CSV
4. `POST /api/v2/exports/contacts/export/chunked` - Chunked contact export

**LinkedIn (2 endpoints - combined):**
5. `POST /api/v2/linkedin/` - Search contacts/companies by LinkedIn URL
6. `POST /api/v2/linkedin/` - Upsert contact/company by LinkedIn URL

**Email Patterns (2 endpoints):**
7. `POST /api/v2/email-patterns/analyze/{company_uuid}` - Analyze email patterns for company
8. `POST /api/v2/email-patterns/import` - Import email patterns (affects contacts)

---

### **API Version 3 (v3)** - Data Pipeline and Analysis

#### **Company Endpoints (10 endpoints)**

**Analysis (2 endpoints):**
1. `GET /api/v3/analysis/company/{uuid}` - Analyze single company
2. `POST /api/v3/analysis/company/batch/` - Analyze batch of companies

**Cleanup (2 endpoints):**
3. `POST /api/v3/cleanup/company/single/{uuid}` - Clean single company
4. `POST /api/v3/cleanup/company/batch/` - Clean batch of companies

**Data Pipeline (4 endpoints):**
5. `POST /api/v3/data-pipeline/ingest/companies/local` - Ingest companies from local CSV
6. `POST /api/v3/data-pipeline/ingest/companies/s3` - Ingest companies from S3
7. `POST /api/v3/data-pipeline/clean/companies` - Clean companies table
8. `POST /api/v3/data-pipeline/analyze/company-names` - Analyze company names

**Validation (2 endpoints):**
9. `GET /api/v3/validation/company/{uuid}` - Validate single company
10. `POST /api/v3/validation/company/batch/` - Validate batch of companies

#### **Contact Endpoints (10 endpoints)**

**Analysis (2 endpoints):**
1. `GET /api/v3/analysis/contact/{uuid}` - Analyze single contact
2. `POST /api/v3/analysis/contact/batch/` - Analyze batch of contacts

**Cleanup (2 endpoints):**
3. `POST /api/v3/cleanup/contact/single/{uuid}` - Clean single contact
4. `POST /api/v3/cleanup/contact/batch/` - Clean batch of contacts

**Data Pipeline (2 endpoints):**
5. `POST /api/v3/data-pipeline/ingest/contacts/local` - Ingest contacts from local CSV
6. `POST /api/v3/data-pipeline/ingest/contacts/s3` - Ingest contacts from S3
7. `POST /api/v3/data-pipeline/clean/contacts` - Clean contacts table

**Email Patterns (2 endpoints):**
8. `GET /api/v3/email-pattern/contact/{uuid}` - Get email pattern for contact
9. `POST /api/v3/email-pattern/contact/batch/` - Get email patterns for batch of contacts

**Validation (2 endpoints):**
10. `GET /api/v3/validation/contact/{uuid}` - Validate single contact
11. `POST /api/v3/validation/contact/batch/` - Validate batch of contacts

---

## Endpoint Categories Summary

### By Functionality:

**CRUD Operations:**
- Companies: 6 endpoints (List, Stream, Get, Create, Update, Delete)
- Contacts: 4 endpoints (List, Stream, Get, Create)
- **Total: 10 endpoints**

**Query/Count Operations:**
- Companies: 3 endpoints (Count, UUIDs, Stream)
- Contacts: 2 endpoints (Count, UUIDs)
- **Total: 5 endpoints**

**Attribute Listing:**
- Companies: 9 endpoints (Name, Industry, Keywords, Technologies, Address, City, State, Country)
- Contacts: 10 endpoints (Title, Seniority, Department, Company, Company Domain, Industry, Keywords, Technologies, Company Address, Contact Address)
- **Total: 19 endpoints**

**Company-Contact Relationships:**
- Company Contacts: 7 endpoints (List, Count, UUIDs, First Name, Last Name, Title, Seniority, Department, Email Status)
- **Total: 7 endpoints**

**Export Operations:**
- Companies: 1 endpoint
- Contacts: 2 endpoints
- Combined: 1 endpoint (LinkedIn)
- **Total: 4 endpoints**

**Email Operations:**
- Email Finder: 1 endpoint
- Email Export: 1 endpoint
- Email Patterns: 5 endpoints
- **Total: 7 endpoints**

**Data Pipeline:**
- Companies: 4 endpoints (Ingest Local, Ingest S3, Clean, Analyze)
- Contacts: 3 endpoints (Ingest Local, Ingest S3, Clean)
- **Total: 7 endpoints**

**Analysis:**
- Companies: 2 endpoints (Single, Batch)
- Contacts: 2 endpoints (Single, Batch)
- **Total: 4 endpoints**

**Cleanup:**
- Companies: 2 endpoints (Single, Batch)
- Contacts: 2 endpoints (Single, Batch)
- **Total: 4 endpoints**

**Validation:**
- Companies: 2 endpoints (Single, Batch)
- Contacts: 2 endpoints (Single, Batch)
- **Total: 4 endpoints**

**AI/ML Features:**
- Company Summary: 1 endpoint (Gemini)
- **Total: 1 endpoint**

**LinkedIn Integration:**
- Search/Upsert: 2 endpoints (combined contacts/companies)
- Export: 1 endpoint (combined)
- **Total: 3 endpoints**

---

## Key Observations

1. **API Versioning Strategy:**
   - **V1**: Core CRUD, filtering, and attribute listing (most comprehensive)
   - **V2**: Extended features (exports, email operations, LinkedIn, AI)
   - **V3**: Data pipeline, analysis, cleanup, and validation operations

2. **Endpoint Patterns:**
   - Most endpoints support pagination (cursor-based or offset-based)
   - Batch operations are common in V3
   - Streaming endpoints available for large datasets
   - Attribute endpoints support filtering and distinct values

3. **Authentication & Authorization:**
   - All endpoints require authentication (JWT)
   - Different permission levels: Free users, Pro users, Admin, Super Admin
   - Free users can create and read, Pro+ can update/delete

4. **Data Relationships:**
   - Strong relationship between Companies and Contacts
   - Company endpoints include sub-endpoints for managing contacts within companies
   - Email patterns link contacts to companies

5. **Performance Optimizations:**
   - Streaming endpoints for large result sets
   - Cursor-based pagination
   - Query caching support
   - Batch operations for bulk processing

---

## Recommendations

1. **Documentation:** Consider creating OpenAPI/Swagger documentation for all endpoints
2. **Testing:** Ensure comprehensive test coverage for all 78 endpoints
3. **Monitoring:** Track usage patterns to identify most-used endpoints for optimization
4. **Consistency:** Some endpoints use different pagination styles - consider standardizing
5. **Version Management:** Plan migration path from V1 to V2/V3 for deprecated features

---

## File Locations

- **V1 Company Endpoints:** `backend/app/api/v1/endpoints/companies.py`
- **V1 Contact Endpoints:** `backend/app/api/v1/endpoints/contacts.py`
- **V2 Exports:** `backend/app/api/v2/endpoints/exports.py`
- **V2 Email:** `backend/app/api/v2/endpoints/email.py`
- **V2 Email Patterns:** `backend/app/api/v2/endpoints/email_patterns.py`
- **V2 Gemini:** `backend/app/api/v2/endpoints/gemini.py`
- **V2 LinkedIn:** `backend/app/api/v2/endpoints/linkedin.py`
- **V3 Analysis:** `backend/app/api/v3/endpoints/analysis.py`
- **V3 Cleanup:** `backend/app/api/v3/endpoints/cleanup.py`
- **V3 Data Pipeline:** `backend/app/api/v3/endpoints/data_pipeline.py`
- **V3 Email Pattern:** `backend/app/api/v3/endpoints/email_pattern.py`
- **V3 Validation:** `backend/app/api/v3/endpoints/validation.py`

---

*Generated: 2024-12-23*
*Last Updated: Analysis of Contact360 Backend API*

