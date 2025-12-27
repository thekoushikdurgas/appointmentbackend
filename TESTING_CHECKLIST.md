# Testing Checklist for Error Resolution & Logging Enhancements

This checklist helps verify all the improvements made to error handling, logging, and performance monitoring.

## ✅ Critical Bug Fixes

### 1. Avatar Upload Endpoint
- [ ] Test avatar upload with valid image files (JPEG, PNG, WebP)
- [ ] Test avatar upload with invalid file types (should fail with proper error)
- [ ] Test avatar upload with files > 5MB (should fail with proper error)
- [ ] Test avatar upload timeout (should timeout after 10s with proper error)
- [ ] Verify avatar upload logs include: file validation, S3/local storage, profile update, cleanup
- [ ] Verify performance metrics are logged for slow uploads (>2s)

**Test Command:**
```bash
curl -X POST "http://localhost:8000/api/v1/users/profile/avatar/" \
  -H "Authorization: Bearer <token>" \
  -F "avatar=@test_image.jpg"
```

### 2. Authentication Endpoints
- [ ] Test user registration with valid data
- [ ] Test user registration with duplicate email (should fail with proper error)
- [ ] Test user registration with weak password (should fail with proper error)
- [ ] Test user login with valid credentials
- [ ] Test user login with invalid credentials (should fail with proper error)
- [ ] Verify all errors are logged with context (failure_point, error_type, duration_ms)
- [ ] Verify transaction rollback logs on registration failures

**Test Commands:**
```bash
# Registration
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "Test123!@#", "name": "Test User"}'

# Login
curl -X POST "http://localhost:8000/api/v1/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "Test123!@#"}'
```

### 3. Email Verification Endpoint
- [ ] Test email verification with valid domain
- [ ] Test email verification with rate limiting (429 error handling)
- [ ] Test email verification with network errors (503 error handling)
- [ ] Test email verification timeout handling
- [ ] Verify external API calls are logged with duration
- [ ] Verify retry logic works for 401 errors

**Test Command:**
```bash
curl -X POST "http://localhost:8000/api/v3/email/verifier/single/" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"first_name": "John", "last_name": "Doe", "domain": "example.com"}'
```

## ✅ Database Performance

### 4. Query Timeout Protection
- [ ] Test user authentication with slow database (should timeout after 2s)
- [ ] Verify timeout errors are logged with context
- [ ] Verify timeout doesn't crash the application

### 5. Database Indexes
- [ ] Verify indexes are created (run migration)
- [ ] Test user email lookup performance (should be <10ms with index)
- [ ] Test user UUID lookup performance (should be <5ms with index)
- [ ] Test user profile lookup performance (should be <5ms with index)

**Verify Indexes:**
```sql
-- Check if indexes exist
SELECT indexname, tablename 
FROM pg_indexes 
WHERE tablename IN ('users', 'user_profiles', 'user_history', 'user_activities')
ORDER BY tablename, indexname;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename IN ('users', 'user_profiles', 'user_history', 'user_activities');
```

### 6. Connection Pool Monitoring
- [ ] Verify pool statistics are logged periodically
- [ ] Test under high load to verify pool saturation warnings (>80%)
- [ ] Test pool exhaustion alerts (>95%)
- [ ] Verify connection acquisition times are logged

**Check Logs:**
```bash
grep -i "connection pool" backend/logs/app.log
grep -i "pool.*saturation" backend/logs/app.log
grep -i "pool.*exhaustion" backend/logs/app.log
```

## ✅ Logging Enhancements

### 7. Repository Logging
- [ ] Verify database queries are logged with duration, table, operation type
- [ ] Verify database errors are logged with context
- [ ] Test email_finder repository queries
- [ ] Test billing repository queries
- [ ] Test linkedin repository queries
- [ ] Test ai_chat repository queries

**Check Logs:**
```bash
# Check for database query logs
grep "database_query" backend/logs/app.log | head -20

# Check for database error logs
grep "database_error" backend/logs/app.log | head -20
```

### 8. Service Logging
- [ ] Verify activity service logs include duration metrics
- [ ] Verify activity service errors are logged with context
- [ ] Test credit service operations (deduction, retrieval)
- [ ] Verify all service methods log performance metrics

**Check Logs:**
```bash
# Check for service logs
grep "app.services" backend/logs/app.log | head -20
```

### 9. Error Context Logging
- [ ] Test endpoints that return 4xx errors (verify request body is logged)
- [ ] Test endpoints that return 5xx errors (verify full context is logged)
- [ ] Verify request ID is included in all error logs
- [ ] Verify client host, user agent are logged
- [ ] Verify sensitive fields are redacted in logs

**Check Logs:**
```bash
# Check for error context
grep -i "request_id" backend/logs/app.log | head -20
grep -i "client_host" backend/logs/app.log | head -20
grep -i "user_agent" backend/logs/app.log | head -20
```

## ✅ Performance Analysis Tools

### 10. Performance Analysis Script
- [ ] Run performance analysis script on logs
- [ ] Verify slow query patterns are identified
- [ ] Verify endpoint performance metrics are extracted
- [ ] Verify error patterns are identified

**Run Script:**
```bash
cd backend
python scripts/analyze_performance.py --log-file logs/app.log --output reports/performance_report.json
```

## ✅ General Verification

### Code Quality
- [ ] All files pass linting (already verified)
- [ ] No syntax errors
- [ ] All imports are correct
- [ ] No unused imports

### Log Format Verification
- [ ] All logs follow consistent format: `timestamp - logger - level - message | Context: {...} | Performance: {...}`
- [ ] Error logs include: error_type, error_message, context, duration_ms
- [ ] Database query logs include: query_type, table, filters, result_count, duration_ms
- [ ] API error logs include: endpoint, method, status_code, error_type, user_id

### Performance Expectations
- [ ] User email lookup: <10ms (with index)
- [ ] User UUID lookup: <5ms (with index)
- [ ] Avatar upload: <2s for typical files (<1MB)
- [ ] Authentication: <500ms
- [ ] Database queries: <100ms for most operations

## Testing Commands Summary

### Run All Tests
```bash
# Run backend tests
cd backend
pytest tests/ -v

# Run specific test suites
pytest tests/test_auth.py -v
pytest tests/test_user_service.py -v
pytest tests/test_email_service.py -v
```

### Check Log Output
```bash
# Monitor logs in real-time
tail -f backend/logs/app.log | grep -E "(ERROR|WARNING|Slow query|database_error)"

# Search for specific patterns
grep -E "timeout|TimeoutError" backend/logs/app.log
grep -E "pool.*saturation|pool.*exhaustion" backend/logs/app.log
grep -E "duration_ms.*[1-9][0-9]{3,}" backend/logs/app.log  # Queries > 1s
```

### Database Verification
```bash
# Connect to database and verify indexes
psql $DATABASE_URL -c "SELECT indexname, tablename FROM pg_indexes WHERE tablename IN ('users', 'user_profiles');"

# Check query performance
psql $DATABASE_URL -c "EXPLAIN ANALYZE SELECT * FROM users WHERE email = 'test@example.com';"
```

## Success Criteria

✅ All critical endpoints have timeout protection  
✅ All errors are logged with comprehensive context  
✅ Database queries are optimized with indexes  
✅ Connection pool is monitored and alerts on saturation  
✅ Performance analysis tools can extract metrics from logs  
✅ No regressions in existing functionality  
✅ All logs follow consistent format  

