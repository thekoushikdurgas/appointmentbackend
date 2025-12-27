# Connectra Migration Testing Checklist

## Overview
This checklist covers all areas that need testing after the Connectra migration. All read operations now go through Connectra API instead of direct PostgreSQL access.

## Pre-Testing Setup

- [ ] Ensure Connectra service is running and accessible
- [ ] Verify `CONNECTRA_URL` is correctly configured
- [ ] Verify `CONNECTRA_API_KEY` is set
- [ ] Test Connectra health endpoint: `GET /health`
- [ ] Verify PostgreSQL tables still exist (for write operations)

## Contact Endpoints Testing

### List Operations
- [ ] `GET /api/v1/contacts/` - List contacts with filters
- [ ] `GET /api/v1/contacts/?limit=10&offset=0` - Pagination
- [ ] `GET /api/v1/contacts/?first_name=John` - Filter by first name
- [ ] `GET /api/v1/contacts/?company=Acme` - Filter by company
- [ ] `GET /api/v1/contacts/?search=engineer` - Search functionality
- [ ] `GET /api/v1/contacts/?cursor=...` - Cursor-based pagination

### Single Contact Operations
- [ ] `GET /api/v1/contacts/{contact_uuid}/` - Get single contact
- [ ] Verify contact detail includes all fields
- [ ] Verify contact metadata is included
- [ ] Verify company information is populated

### Count Operations
- [ ] `GET /api/v1/contacts/count/` - Count all contacts
- [ ] `GET /api/v1/contacts/count/?first_name=John` - Count with filters

### VQL Query Operations
- [ ] `POST /api/v1/contacts/query` - VQL query endpoint
- [ ] `POST /api/v1/contacts/count` - VQL count endpoint
- [ ] Test complex VQL queries with multiple filters
- [ ] Test VQL queries with field selection

### Attribute List Operations
- [ ] `GET /api/v1/contacts/title/` - List titles
- [ ] `GET /api/v1/contacts/company/` - List companies
- [ ] `GET /api/v1/contacts/company_address/` - List company addresses
- [ ] `GET /api/v1/contacts/contact_address/` - List contact addresses
- [ ] `GET /api/v1/contacts/industry/` - List industries
- [ ] `GET /api/v1/contacts/keywords/` - List keywords
- [ ] `GET /api/v1/contacts/technologies/` - List technologies
- [ ] Test pagination on attribute lists
- [ ] Test search on attribute lists

### Company-Specific Contact Operations
- [ ] `GET /api/v1/companies/company/{company_uuid}/contacts/` - List contacts by company
- [ ] `GET /api/v1/companies/company/{company_uuid}/contacts/count/` - Count contacts by company
- [ ] Test filters on company contacts
- [ ] Test pagination on company contacts

## Company Endpoints Testing

### List Operations
- [ ] `GET /api/v1/companies/` - List companies with filters
- [ ] `GET /api/v1/companies/?limit=10&offset=0` - Pagination
- [ ] `GET /api/v1/companies/?name=Acme` - Filter by name
- [ ] `GET /api/v1/companies/?industries=Technology` - Filter by industry
- [ ] `GET /api/v1/companies/?search=software` - Search functionality

### Single Company Operations
- [ ] `GET /api/v1/companies/{company_uuid}/` - Get single company
- [ ] Verify company detail includes all fields
- [ ] Verify company metadata is included

### Count Operations
- [ ] `GET /api/v1/companies/count/` - Count all companies
- [ ] `GET /api/v1/companies/count/?name=Acme` - Count with filters

### VQL Query Operations
- [ ] `POST /api/v1/companies/query` - VQL query endpoint
- [ ] `POST /api/v1/companies/count` - VQL count endpoint
- [ ] Test complex VQL queries with multiple filters

### Attribute List Operations
- [ ] `GET /api/v1/companies/name/` - List company names
- [ ] `GET /api/v1/companies/industry/` - List industries
- [ ] Test pagination on attribute lists
- [ ] Test search on attribute lists

## Export Operations Testing

### Contact Exports
- [ ] `POST /api/v1/exports/contacts/` - Create contact export
- [ ] Verify export includes all contact fields
- [ ] Verify export includes contact metadata
- [ ] Verify export includes company information
- [ ] Test export with filters
- [ ] Test large exports (1000+ contacts)
- [ ] Verify CSV format is correct
- [ ] Verify S3 upload (if configured)

### Company Exports
- [ ] `POST /api/v1/exports/companies/` - Create company export
- [ ] Verify export includes all company fields
- [ ] Verify export includes company metadata
- [ ] Test export with filters
- [ ] Test large exports (1000+ companies)

## LinkedIn Search Testing

- [ ] `POST /api/v1/linkedin/search` - Search by LinkedIn URL
- [ ] Test contact search by LinkedIn URL
- [ ] Test company search by LinkedIn URL
- [ ] Test parallel search (`use_parallel=true`)
- [ ] Test sequential search (`use_parallel=false`)
- [ ] Verify response includes contacts and companies
- [ ] Test with multiple URLs

## Batch Operations Testing

- [ ] Test `batch_fetch_contacts_by_uuids()` with multiple UUIDs
- [ ] Test `batch_fetch_companies_by_uuids()` with multiple UUIDs
- [ ] Test `batch_fetch_contact_metadata_by_uuids()`
- [ ] Test `batch_fetch_company_metadata_by_uuids()`
- [ ] Test `fetch_companies_and_metadata_by_uuids()`
- [ ] Test `fetch_contacts_and_metadata_by_uuids()`
- [ ] Verify batch operations handle large batches (100+ UUIDs)
- [ ] Verify batch operations handle missing UUIDs gracefully

## Error Handling Testing

### Connectra Unavailable
- [ ] Test behavior when Connectra service is down
- [ ] Verify 503 Service Unavailable responses
- [ ] Verify error messages are clear
- [ ] Test timeout handling

### Invalid Requests
- [ ] Test with invalid UUIDs
- [ ] Test with invalid filter parameters
- [ ] Test with invalid VQL queries
- [ ] Verify appropriate error codes (400, 404, 422)

### Network Issues
- [ ] Test with slow Connectra responses
- [ ] Test with connection timeouts
- [ ] Test retry logic (if implemented)

## Performance Testing

- [ ] Compare response times before/after migration
- [ ] Test pagination performance with large datasets
- [ ] Test batch operation performance
- [ ] Test export performance with large datasets
- [ ] Monitor Connectra API call counts
- [ ] Verify no N+1 query problems

## Write Operations Testing

### Contact Write Operations
- [ ] `POST /api/v1/contacts/` - Create contact
- [ ] `PUT /api/v1/contacts/{contact_uuid}/` - Update contact (if exists)
- [ ] `DELETE /api/v1/contacts/{contact_uuid}/` - Delete contact (if exists)
- [ ] Verify writes still work (use PostgreSQL)

### Company Write Operations
- [ ] `POST /api/v1/companies/` - Create company
- [ ] `PUT /api/v1/companies/{company_uuid}/` - Update company
- [ ] `DELETE /api/v1/companies/{company_uuid}/` - Delete company
- [ ] Verify writes still work (use PostgreSQL)

## Sales Navigator Testing

- [ ] Test Sales Navigator scraping with Connectra lookups
- [ ] Verify contact existence checks use Connectra
- [ ] Verify company existence checks use Connectra
- [ ] Test contact creation/update flow

## Integration Testing

- [ ] Test full workflow: List → Filter → Get Detail → Export
- [ ] Test full workflow: Search → Get Detail → Update
- [ ] Test concurrent requests
- [ ] Test with real-world data volumes

## Regression Testing

- [ ] Verify all existing tests still pass
- [ ] Run full test suite
- [ ] Check for any broken functionality
- [ ] Verify API response formats haven't changed

## Documentation Testing

- [ ] Verify API documentation is up to date
- [ ] Check migration summary document
- [ ] Verify deprecation warnings are clear
- [ ] Check error message clarity

## Post-Migration Validation

- [ ] Verify no direct PostgreSQL reads for contacts/companies
- [ ] Verify Elasticsearch is completely removed
- [ ] Verify all feature flags are removed
- [ ] Check logs for any repository usage warnings
- [ ] Verify Connectra is the only data source for reads

## Notes

- All read operations must go through Connectra
- Write operations still use PostgreSQL (until Connectra supports writes)
- Attribute list operations have repository fallbacks (temporary)
- Error handling should return 503 when Connectra is unavailable
- Performance should be monitored closely

