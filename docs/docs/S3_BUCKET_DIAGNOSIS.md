# S3 Bucket Diagnosis and Fixes

## Issues Identified from Logs

### Error Analysis (from `backend/logs/app.log`)

**Line 19:** `No files found in bucket 'tkdrawcsvdata' with prefix 'data'`

This indicates:
1. ✅ Bucket name is correct: `tkdrawcsvdata`
2. ❌ No files found with prefix `data/`
3. ⚠️  The file `data/apollo_sample_5000_cleaned.csv` does not exist at that path

### Possible Root Causes

1. **File doesn't exist in bucket** - The file may not have been uploaded yet
2. **File is at root level** - File might be `apollo_sample_5000_cleaned.csv` (without `data/` prefix)
3. **File is in different folder** - File might be in a different prefix like `raw/`, `processed/`, etc.
4. **Bucket is empty** - The bucket might not have any files yet
5. **Wrong bucket** - Files might be in a different bucket

## Fixes Implemented

### 1. Enhanced Error Handling in `download_csv_file()`

**Location:** `backend/app/services/s3_service.py`

**Changes:**
- When a file is not found, the system now lists **ALL files** in the bucket (up to 50)
- Shows similar files that might match what you're looking for
- Provides clear error messages indicating if bucket is empty
- Logs bucket name and all available files for debugging

**Benefits:**
- Easier to identify if file exists with different name/path
- Can see what files are actually in the bucket
- Helps diagnose bucket access issues

### 2. Enhanced Logging in `list_csv_files()`

**Location:** `backend/app/services/s3_service.py`

**Changes:**
- Verifies bucket exists before listing
- Counts total objects vs CSV files
- Warns if no CSV files found (with total object count)
- Better error messages for bucket access issues

**Benefits:**
- Can identify if bucket is empty
- Can see if files exist but aren't CSV
- Better diagnostics for permission issues

### 3. Enhanced Endpoint Logging

**Location:** `backend/app/api/v3/endpoints/s3.py`

**Changes:**
- Logs bucket name in all requests
- Shows file count in listing responses
- Better error context

## Next Steps to Resolve

### Step 1: Check What Files Actually Exist

When you make a request to `/api/v3/s3/files/data/apollo_sample_5000_cleaned.csv`, the enhanced error handling will now show:
- All files in the bucket (up to 50)
- Similar files that might match
- Whether the bucket is empty

**Action:** Make the request again and check the logs for the list of files.

### Step 2: Verify File Location

Based on the logs, you'll see:
- If files are at root level (e.g., `apollo_sample_5000_cleaned.csv`)
- If files are in different folders
- If the bucket is empty

**Action:** Use the file path shown in logs to access the file correctly.

### Step 3: Fix File Path if Needed

If the file exists but with a different path:
- **Root level:** Use `/api/v3/s3/files/apollo_sample_5000_cleaned.csv` (without `data/`)
- **Different folder:** Use the correct prefix, e.g., `/api/v3/s3/files/raw/apollo_sample_5000_cleaned.csv`

### Step 4: Upload File if Missing

If the bucket is empty or file doesn't exist:
- Upload the file to the `tkdrawcsvdata` bucket
- Ensure it's uploaded with the correct path (`data/apollo_sample_5000_cleaned.csv`)

## Testing

After making a request, check the logs for:

1. **Bucket verification:**
   ```
   Bucket 'tkdrawcsvdata' exists and is accessible
   ```

2. **File listing:**
   ```
   Found X total file(s) in bucket 'tkdrawcsvdata':
     - file1.csv
     - file2.csv
   ```

3. **Similar files:**
   ```
   Similar files found (might be what you're looking for):
     - apollo_sample_5000_cleaned.csv
   ```

## Configuration

The bucket name is configured in:
- **Config:** `backend/app/core/config.py` - `S3_V3_BUCKET_NAME = "tkdrawcsvdata"`
- **Can be overridden:** Set `S3_V3_BUCKET_NAME` environment variable

## Summary

✅ **Fixed:**
- Enhanced error messages to show all files in bucket
- Better logging for bucket access verification
- Improved diagnostics for file not found errors

⏳ **Pending:**
- Verify what files actually exist in `tkdrawcsvdata` bucket
- Confirm correct file paths
- Upload files if bucket is empty

🔍 **Next Action:**
Make a request to the endpoint and check the logs - they will now show all files in the bucket to help identify the correct path.

