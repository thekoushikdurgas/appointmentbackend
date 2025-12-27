# Verified Email Saving Verification Guide

## Overview

This document describes how to verify that verified emails from BulkMailVerifier are correctly saved to the contact table with only expected fields populated, and all other columns remain NULL.

## Expected Behavior

When a verified email is found via BulkMailVerifier and saved to the contact table:

### Fields That Should Be Populated:
- `uuid`: Generated deterministically from email + name
- `email`: The verified email address (always set)
- `email_status`: Set to `'valid'` (always set)
- `first_name`: From input (can be NULL if not provided)
- `last_name`: From input (can be NULL if not provided)
- `company_id`: From domain lookup (can be NULL if domain not available)
- `created_at`: Timestamp when contact was created
- `updated_at`: Timestamp when contact was last updated

### Fields That Should Remain NULL:
- `title`: Should be NULL
- `departments`: Should be NULL
- `mobile_phone`: Should be NULL
- `text_search`: Should be NULL
- `seniority`: Should be NULL or default value `'_'`

## Verification Methods

### 1. Database Query Verification

Run the SQL query in `backend/scripts/verify_verified_emails.sql`:

```bash
psql -d your_database -f backend/scripts/verify_verified_emails.sql
```

This query will:
- Show recent verified email contacts
- Check which fields are populated vs NULL
- Provide summary statistics
- Identify any unexpected data

### 2. Application Log Verification

Check application logs for save operations. Look for log entries like:

```
Upserted contact with verified email: uuid=<uuid> email=<email> first_name=<name> last_name=<name> company_id=<id>
Contact X/Y: Saved verified email to database: email=<email> uuid=<uuid> export_id=<id>
```

### 3. Manual Testing Scenarios

#### Test Case 1: Full Data (first_name, last_name, domain)
**Input:**
- first_name: "John"
- last_name: "Doe"
- domain: "example.com"
- verified_email: "john.doe@example.com"

**Expected Result:**
- Contact saved with: uuid, email, email_status='valid', first_name, last_name, company_id, created_at, updated_at
- NULL fields: title, departments, mobile_phone, text_search, seniority

#### Test Case 2: Minimal Data (only email)
**Input:**
- first_name: None
- last_name: None
- domain: None
- verified_email: "test@example.com"

**Expected Result:**
- Contact saved with: uuid, email, email_status='valid', created_at, updated_at
- NULL fields: first_name, last_name, company_id, title, departments, mobile_phone, text_search, seniority

#### Test Case 3: Partial Data (first_name only)
**Input:**
- first_name: "Jane"
- last_name: None
- domain: "example.com"
- verified_email: "jane@example.com"

**Expected Result:**
- Contact saved with: uuid, email, email_status='valid', first_name, company_id, created_at, updated_at
- NULL fields: last_name, title, departments, mobile_phone, text_search, seniority

## Code Implementation Review

### Key Function: `_upsert_contact_with_verified_email()`

**Location:** `backend/app/tasks/export_tasks.py` (lines 701-810)

**What it does:**
1. Validates email is not empty
2. Normalizes email to lowercase
3. Finds or creates company by domain (if domain provided)
4. Generates deterministic UUID from email + name
5. Creates contact_data dictionary with only intended fields
6. Upserts contact using SQLAlchemy's `on_conflict_do_update`
7. Only updates fields that are provided (doesn't overwrite with NULL)

**Contact Data Dictionary (lines 747-756):**
```python
contact_data = {
    "uuid": contact_uuid,
    "first_name": first_name.strip() if first_name and first_name.strip() else None,
    "last_name": last_name.strip() if last_name and last_name.strip() else None,
    "email": normalized_email,
    "email_status": "valid",
    "company_id": final_company_id,
    "created_at": server_time,
    "updated_at": server_time,
}
```

**Note:** This dictionary does NOT include:
- `title`
- `departments`
- `mobile_phone`
- `text_search`
- `seniority`

These fields will remain NULL in the database.

## Verification Checklist

- [ ] Run SQL verification query
- [ ] Check application logs for save operations
- [ ] Verify contacts exist in database with correct email_status
- [ ] Verify only expected fields are populated
- [ ] Verify other fields are NULL
- [ ] Test with different data scenarios (full, minimal, partial)
- [ ] Verify upsert behavior (updating existing contacts)
- [ ] Check error handling (failed saves don't break export)

## Troubleshooting

### Issue: Fields unexpectedly populated
**Check:**
- Review `update_dict` logic in `_upsert_contact_with_verified_email()`
- Verify `contact_data` dictionary doesn't include unexpected fields
- Check if existing contact had data that's being preserved

### Issue: Contacts not being saved
**Check:**
- Application logs for errors
- Verify BulkMailVerifier is returning verified emails
- Check database connection and session handling
- Review error handling in export process

### Issue: Company association not working
**Check:**
- Domain extraction is working correctly
- `_find_or_create_company_by_domain()` is being called
- Company creation/update logic is correct
- Check for company creation errors in logs

## Related Files

- `backend/app/tasks/export_tasks.py` - Main implementation
- `backend/app/models/contacts.py` - Contact model schema
- `backend/scripts/verify_verified_emails.sql` - Verification query
- `backend/logs/app.log` - Application logs

