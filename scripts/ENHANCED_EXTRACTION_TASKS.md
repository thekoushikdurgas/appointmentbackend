# Enhanced Sales Navigator Data Extraction - Task Breakdown

## Overview
This document breaks down all tasks needed to extract comprehensive data from the Sales Navigator HTML file, organized into smaller, manageable tasks.

---

## NEWLY DISCOVERED DATA FIELDS

### 1. **Premium Membership Status**
- **Location**: `artdeco-entity-lockup__badge` with `linkedin-premium-gold-icon`
- **Data**: Boolean indicating if person has LinkedIn Premium
- **Example**: "3rd degree connection and LinkedIn premium member"
- **Extraction Method**: Check for `linkedin-premium-gold-icon` in badge element

### 2. **Last Active Status**
- **Location**: `presence-indicator` with `title` attribute
- **Data**: Timestamp of last activity
- **Example**: "Last active 2 minutes ago", "Reachable"
- **Extraction Method**: Parse `title` attribute of presence indicator

### 3. **Viewed Status**
- **Location**: Eyeball icon with aria-label
- **Data**: Boolean indicating if profile was previously viewed
- **Example**: "You've already seen [Name]'s profile before"
- **Extraction Method**: Check for eyeball icon and aria-label text

### 4. **Search Query Parameters (Detailed)**
- **Location**: URL query parameters in search links
- **Data**: 
  - `recentSearchId`: 5263824340
  - `sessionId`: MZSayEwCQkaWxjmJ3Sz4Wg%3D%3D
  - `query`: Encoded filter parameters
  - Filter details: `CURRENT_TITLE`, `id:9`, `text:Software Engineer`, `selectionType:INCLUDED`
- **Extraction Method**: Parse URL query string

### 5. **Page-Level Metadata**
- **Location**: Meta tags and page structure
- **Data**:
  - User Member URN: `urn:li:member:301118112`
  - Application Version: `2.0.5996`
  - Client Page Instance ID: `3fd1fa6a-dc94-413b-9df7-ae3a1dcb503d`
  - Tracking ID: Array of numbers
  - Request IP Country: `in` (India)
  - Tree ID: `AAZEG7qFXTcSYbM745ibpg==`

### 6. **Lead URN (Full Format)**
- **Location**: `data-scroll-into-view` attribute
- **Data**: Complete URN format
- **Example**: `urn:li:fs_salesProfile:(ACwAAAByMvQBweFnFh_2u0h3gM1sJHeWTItSn5M,NAME_SEARCH,z0xx)`
- **Extraction Method**: Parse attribute value

### 7. **Company Logo URLs** (in spotlight indicators)
- **Location**: Shared groups and recently hired spotlights
- **Data**: Company logo image URLs
- **Example**: `https://media.licdn.com/dms/image/v2/C510BAQHsmjPgkZGRMw/company-logo_100_100/...`

### 8. **Mutual Connection Profile Images**
- **Location**: Second degree connection spotlight
- **Data**: Array of profile image URLs for mutual connections
- **Extraction Method**: Extract from `_entityStack` elements

---

## TASK BREAKDOWN

### PHASE 1: Core Data Extraction Enhancement

#### Task 1.1: Extract Lead Identifiers
- **Priority**: High
- **Complexity**: Low
- **Description**: Extract unique lead identifiers from URLs and URNs
- **Fields to Add**:
  - `lead_id`: Extract from profile URL (ACwAA... format)
  - `lead_urn`: Extract from `data-scroll-into-view` attribute
  - `search_type`: Extract from URN (e.g., "NAME_SEARCH")
  - `search_id`: Extract from URN (e.g., "z0xx")
- **Implementation**:
  - Parse profile URL to extract lead ID
  - Parse `data-scroll-into-view` attribute for URN
  - Split URN into components

#### Task 1.2: Extract Company Information
- **Priority**: High
- **Complexity**: Low
- **Description**: Extract company IDs and full company URLs
- **Fields to Add**:
  - `company_id`: Numeric ID from company URL
  - `company_url`: Full company profile URL
- **Implementation**:
  - Parse company link `href` attribute
  - Extract numeric ID from `/sales/company/{ID}` pattern
  - Convert to full URL

#### Task 1.3: Extract Premium Status
- **Priority**: Medium
- **Complexity**: Low
- **Description**: Detect if person has LinkedIn Premium
- **Fields to Add**:
  - `is_premium_member`: Boolean
- **Implementation**:
  - Check badge element for `linkedin-premium-gold-icon`
  - Parse aria-label text for "premium member"

#### Task 1.4: Extract Activity Status
- **Priority**: Medium
- **Complexity**: Low
- **Description**: Extract last active time and reachability
- **Fields to Add**:
  - `is_reachable`: Boolean (InMail reachable)
  - `last_active`: String (e.g., "Last active 2 minutes ago" or "Reachable")
- **Implementation**:
  - Check `presence-indicator` element
  - Parse `title` attribute
  - Check for "Reachable" vs "Last active X ago" patterns

#### Task 1.5: Extract Viewed Status
- **Priority**: Low
- **Complexity**: Low
- **Description**: Check if profile was previously viewed
- **Fields to Add**:
  - `is_viewed`: Boolean
- **Implementation**:
  - Check for eyeball icon (`eyeball-icon`)
  - Parse aria-label for "already seen" text

---

### PHASE 2: Spotlight & Network Data Extraction

#### Task 2.1: Extract Shared Groups Details
- **Priority**: Medium
- **Complexity**: Medium
- **Description**: Extract detailed shared groups information
- **Fields to Add**:
  - `shared_groups`: Enhanced array with group details
    - `group_name`: Name of group
    - `group_logo_url`: Group logo image URL
    - `group_url`: Group profile URL (if available)
- **Implementation**:
  - Find shared groups button
  - Extract group logo images from `_entityStack`
  - Parse group names from text or alt attributes
  - Note: Full details may be in hidden dialog/popup

#### Task 2.2: Extract Recently Hired Information
- **Priority**: Medium
- **Complexity**: Low
- **Description**: Extract recently hired spotlight data
- **Fields to Add**:
  - `is_recently_hired`: Boolean
  - `recently_hired_company_logo`: Company logo URL (if available)
- **Implementation**:
  - Check for `search_spotlight_recently_hired` button
  - Extract company logo from `_entityStack` if present

#### Task 2.3: Extract Recent Posts Information
- **Priority**: Low
- **Complexity**: Medium
- **Description**: Extract recent posts count
- **Fields to Add**:
  - `recent_posts_count`: Integer (number of recent posts)
- **Implementation**:
  - Check for `search_spotlight_recent_posts` button
  - Parse text for number (e.g., "2 recent posts")
  - Note: Full post details may be in hidden dialog

#### Task 2.4: Extract Mutual Connections Details
- **Priority**: High
- **Complexity**: Medium
- **Description**: Extract mutual connections count and profile images
- **Fields to Add**:
  - `mutual_connections_count`: Integer
  - `mutual_connections`: Array of objects
    - `name`: Connection name (if available)
    - `image_url`: Profile image URL
- **Implementation**:
  - Find `search_spotlight_second_degree_connection` button
  - Parse text for count (e.g., "1 mutual connection")
  - Extract profile images from `_entityStack`
  - Note: Names may not be available in HTML

---

### PHASE 3: Search Context & Metadata Extraction

#### Task 3.1: Extract Search Query Details
- **Priority**: Medium
- **Complexity**: Medium
- **Description**: Extract applied search filters and parameters
- **Fields to Add** (at page level, not per profile):
  - `search_filters`: Object with filter details
    - `current_title`: Filter value (e.g., "Software Engineer")
    - `filter_id`: Filter ID (e.g., 9)
    - `selection_type`: "INCLUDED" or "EXCLUDED"
  - `search_id`: Recent search ID
  - `session_id`: Session identifier
- **Implementation**:
  - Parse search URL from navigation links
  - Decode URL-encoded query parameters
  - Parse filter structure from query string

#### Task 3.2: Extract Pagination Information
- **Priority**: Low
- **Complexity**: Low
- **Description**: Extract pagination details
- **Fields to Add** (at page level):
  - `current_page`: Integer
  - `total_pages`: Integer
  - `results_per_page`: Integer (may need calculation)
- **Implementation**:
  - Parse pagination text ("Page 1 of 100")
  - Extract from `artdeco-pagination__state--a11y` element

#### Task 3.3: Extract Page-Level Metadata
- **Priority**: Low
- **Complexity**: Low
- **Description**: Extract user and application metadata
- **Fields to Add** (at page level):
  - `user_member_urn`: User's LinkedIn member URN
  - `application_version`: Application version
  - `client_page_instance_id`: Page instance ID
  - `request_ip_country`: Country code
  - `tracking_id`: Tracking identifier array
- **Implementation**:
  - Parse meta tags
  - Extract from `__init` meta tag JSON
  - Extract from `applicationInstance` meta tag

---

### PHASE 4: Data Quality & Enhancement

#### Task 4.1: Improve About Section Extraction
- **Priority**: High
- **Complexity**: Low
- **Description**: Always get full text from title attribute when truncated
- **Implementation**:
  - Check for `data-truncated` attribute
  - Always prefer `title` attribute over visible text when truncated
  - Clean HTML entities properly

#### Task 4.2: Handle HTML Entity Decoding
- **Priority**: Medium
- **Complexity**: Low
- **Description**: Properly decode all HTML entities
- **Implementation**:
  - Use BeautifulSoup's built-in decoding
  - Handle special cases: `&nbsp;`, `&amp;`, `&#39;`, etc.
  - Clean up extra whitespace after decoding

#### Task 4.3: Validate and Normalize URLs
- **Priority**: Medium
- **Complexity**: Low
- **Description**: Ensure all URLs are properly formatted
- **Implementation**:
  - Convert relative URLs to absolute
  - Validate URL format
  - Handle URL encoding/decoding properly

#### Task 4.4: Extract Control IDs for Tracking
- **Priority**: Low
- **Complexity**: Low
- **Description**: Extract control IDs for potential future use
- **Fields to Add**:
  - `control_id`: Control identifier (encoded string)
- **Implementation**:
  - Extract from `data-control-id` attributes
  - Note: These are binary/encoded, may not be useful

---

### PHASE 5: Output Structure Enhancement

#### Task 5.1: Create Hierarchical JSON Structure
- **Priority**: Medium
- **Complexity**: Medium
- **Description**: Organize output with page-level and profile-level data
- **Structure**:
```json
{
  "page_metadata": {
    "search_filters": {...},
    "pagination": {...},
    "user_info": {...},
    "application_info": {...}
  },
  "profiles": [
    {
      // All profile data
    }
  ]
}
```

#### Task 5.2: Add Data Quality Indicators
- **Priority**: Low
- **Complexity**: Low
- **Description**: Add flags indicating data completeness
- **Fields to Add**:
  - `data_quality_score`: Integer (0-100)
  - `missing_fields`: Array of missing field names
- **Implementation**:
  - Calculate based on available vs expected fields
  - List fields that are null/missing

#### Task 5.3: Add Extraction Timestamps
- **Priority**: Low
- **Complexity**: Low
- **Description**: Add metadata about extraction process
- **Fields to Add** (at root level):
  - `extraction_timestamp`: ISO timestamp
  - `extraction_version`: Script version
  - `source_file`: Source HTML file path

---

## IMPLEMENTATION PRIORITY

### High Priority (Implement First)
1. Task 1.1: Extract Lead Identifiers
2. Task 1.2: Extract Company Information
3. Task 2.4: Extract Mutual Connections Details
4. Task 4.1: Improve About Section Extraction

### Medium Priority (Implement Second)
5. Task 1.3: Extract Premium Status
6. Task 1.4: Extract Activity Status
7. Task 2.1: Extract Shared Groups Details
8. Task 2.2: Extract Recently Hired Information
9. Task 3.1: Extract Search Query Details
10. Task 5.1: Create Hierarchical JSON Structure

### Low Priority (Nice to Have)
11. Task 1.5: Extract Viewed Status
12. Task 2.3: Extract Recent Posts Information
13. Task 3.2: Extract Pagination Information
14. Task 3.3: Extract Page-Level Metadata
15. Task 4.2: Handle HTML Entity Decoding
16. Task 4.3: Validate and Normalize URLs
17. Task 4.4: Extract Control IDs
18. Task 5.2: Add Data Quality Indicators
19. Task 5.3: Add Extraction Timestamps

---

## ESTIMATED EFFORT

- **High Priority Tasks**: 4-6 hours
- **Medium Priority Tasks**: 6-8 hours
- **Low Priority Tasks**: 4-6 hours
- **Total Estimated Time**: 14-20 hours

---

## TESTING REQUIREMENTS

### Unit Tests Needed
1. Test lead ID extraction from various URL formats
2. Test URN parsing with different formats
3. Test company ID extraction
4. Test premium status detection
5. Test activity status parsing
6. Test mutual connections extraction
7. Test truncated about section handling
8. Test HTML entity decoding

### Integration Tests Needed
1. Test full profile extraction with all new fields
2. Test page-level metadata extraction
3. Test JSON structure validation
4. Test edge cases (missing fields, malformed HTML)

---

## NOTES

1. **Dynamic Content**: Some data (like full group details, post content) may be in hidden dialogs that require JavaScript to load. These may not be extractable from static HTML.

2. **Data Availability**: Not all profiles will have all fields. The script should handle missing data gracefully.

3. **URL Encoding**: Search query parameters are URL-encoded and may need special parsing.

4. **Performance**: Adding more fields will increase processing time. Consider batching or optimization for large files.

5. **Maintenance**: LinkedIn may change HTML structure. The script should be flexible and handle variations.

---

## NEXT STEPS

1. Review and prioritize tasks based on business needs
2. Create detailed implementation plan for high-priority tasks
3. Set up testing framework
4. Implement tasks in priority order
5. Test with multiple HTML files if available
6. Document any limitations or edge cases discovered

