# Complete Data Inventory - Sales Navigator HTML

## Summary
This document provides a complete inventory of ALL data fields discovered in the Sales Navigator HTML file, organized by category.

---

## CURRENTLY EXTRACTED (11 fields)

✅ **Basic Profile Information**
1. `name` - Full name
2. `title` - Current job title
3. `company` - Company name
4. `location` - Geographic location
5. `profile_url` - Sales Navigator lead URL
6. `image_url` - Profile picture URL
7. `connection_degree` - Connection level (1st, 2nd, 3rd)
8. `about` - Professional summary/bio
9. `time_in_role` - Duration in current position
10. `time_in_company` - Duration at current company
11. `shared_groups` - Basic shared groups indicator

---

## NEWLY DISCOVERED DATA (20+ additional fields)

### Profile-Level Data

#### Identifiers & URLs
12. `lead_id` - Unique lead identifier (ACwAA... format)
13. `lead_urn` - Full URN format (urn:li:fs_salesProfile:...)
14. `search_type` - Search context type (e.g., "NAME_SEARCH")
15. `search_id` - Search session identifier
16. `company_id` - Numeric company identifier
17. `company_url` - Full company profile URL

#### Status Indicators
18. `is_premium_member` - LinkedIn Premium membership status
19. `is_reachable` - InMail reachability status
20. `last_active` - Last activity timestamp/text
21. `is_viewed` - Previously viewed status

#### Network & Connections
22. `mutual_connections_count` - Number of mutual connections
23. `mutual_connections` - Array of mutual connection details
    - `image_url` - Profile image URL
    - `name` - Name (if available)

#### Spotlight Indicators
24. `is_recently_hired` - Recently hired flag
25. `recently_hired_company_logo` - Company logo URL
26. `recent_posts_count` - Number of recent LinkedIn posts
27. `shared_groups_details` - Enhanced shared groups array
    - `group_name` - Group name
    - `group_logo_url` - Group logo URL
    - `group_url` - Group profile URL

#### Tracking & Control
28. `control_id` - Control identifier for tracking
29. `tracking_parameters` - Navigation tracking data

---

### Page-Level Data

#### Search Context
30. `search_filters` - Applied search filters
    - `current_title` - Job title filter value
    - `filter_id` - Filter identifier
    - `selection_type` - INCLUDED/EXCLUDED
31. `search_id` - Recent search ID (5263824340)
32. `session_id` - Session identifier

#### Pagination
33. `current_page` - Current page number
34. `total_pages` - Total pages available
35. `results_per_page` - Results per page (calculated)

#### User & Application Metadata
36. `user_member_urn` - Logged-in user's URN
37. `user_name` - Logged-in user's name (from header)
38. `application_version` - Application version (2.0.5996)
39. `client_page_instance_id` - Page instance ID
40. `request_ip_country` - Request country code (in)
41. `tracking_id` - Tracking identifier array
42. `tree_id` - Tree identifier

#### Extraction Metadata
43. `extraction_timestamp` - When data was extracted
44. `extraction_version` - Script version
45. `source_file` - Source HTML file path

---

## DATA FIELD DETAILS

### Lead Identifiers
- **Lead ID Format**: `ACwAAAByMvQBweFnFh_2u0h3gM1sJHeWTItSn5M`
- **Lead URN Format**: `urn:li:fs_salesProfile:(ACwAA...,NAME_SEARCH,ID)`
- **Extraction Source**: Profile URLs and `data-scroll-into-view` attributes

### Company Information
- **Company ID Format**: Numeric (e.g., 5221148, 11025983)
- **Company URL Format**: `/sales/company/{COMPANY_ID}?_ntb={TRACKING}`
- **Extraction Source**: Company link `href` attributes

### Premium Status
- **Indicator**: `linkedin-premium-gold-icon` SVG element
- **Text**: "X degree connection and LinkedIn premium member"
- **Extraction Source**: Badge element with aria-label

### Activity Status
- **Reachable**: "Reachable" or "Last active X ago"
- **Hidden Class**: `presence-indicator--size-4 hidden` (not reachable)
- **Active Class**: `presence-indicator--is-reachable` (reachable/active)
- **Extraction Source**: `presence-indicator` element `title` attribute

### Viewed Status
- **Indicator**: Eyeball icon (`eyeball-icon`)
- **Text**: "You've already seen [Name]'s profile before"
- **Extraction Source**: Icon presence and aria-label

### Mutual Connections
- **Count Format**: "X mutual connection(s)"
- **Images**: Profile images in `_entityStack` elements
- **Extraction Source**: `search_spotlight_second_degree_connection` button

### Search Filters
- **Query Format**: URL-encoded JSON in query parameter
- **Example**: `(recentSearchParam:(id:5263824340,doLogHistory:true),filters:List((type:CURRENT_TITLE,values:List((id:9,text:Software%20Engineer,selectionType:INCLUDED)))))`
- **Extraction Source**: Search navigation link `href` attribute

### Pagination
- **Format**: "Page X of Y"
- **Extraction Source**: `artdeco-pagination__state--a11y` element text

---

## DATA AVAILABILITY MATRIX

| Field | Always Present | Sometimes Present | Rarely Present |
|-------|---------------|-------------------|----------------|
| name | ✅ | | |
| title | ✅ | | |
| company | ✅ | | |
| location | ✅ | | |
| profile_url | ✅ | | |
| image_url | ✅ | | |
| connection_degree | ✅ | | |
| about | | ✅ | |
| time_in_role | ✅ | | |
| time_in_company | ✅ | | |
| lead_id | ✅ | | |
| company_id | ✅ | | |
| is_premium_member | | ✅ | |
| is_reachable | ✅ | | |
| last_active | | ✅ | |
| is_viewed | | ✅ | |
| mutual_connections_count | | ✅ | |
| shared_groups | | ✅ | |
| is_recently_hired | | ✅ | |
| recent_posts_count | | ✅ | |

---

## DATA EXTRACTION COMPLEXITY

### Low Complexity (Easy to Extract)
- Lead IDs from URLs
- Company IDs from URLs
- Premium status (icon check)
- Viewed status (icon check)
- Pagination info (text parsing)
- Basic metadata (meta tags)

### Medium Complexity (Requires Parsing)
- Lead URN parsing
- Search query parameter decoding
- Mutual connections extraction
- Shared groups details
- Activity status parsing

### High Complexity (May Require Special Handling)
- Full search filter structure
- Dynamic content in hidden dialogs
- Group names from images/logos
- Mutual connection names

---

## DATA QUALITY CONSIDERATIONS

### Reliable Data (High Confidence)
- Name, title, company, location
- Profile and image URLs
- Connection degree
- Lead and company IDs
- Time in role/company

### Moderate Reliability (May Vary)
- About section (may be truncated)
- Premium status (icon may be missing)
- Activity status (format may vary)
- Mutual connections (count reliable, details may be limited)

### Lower Reliability (May Not Always Be Available)
- Shared groups details
- Recent posts content
- Full mutual connection information
- Some spotlight indicators

---

## TOTAL DATA POINTS

- **Currently Extracted**: 11 fields
- **Newly Discovered**: 34+ additional fields
- **Total Available**: 45+ data points per profile
- **Page-Level Data**: 13+ additional fields

---

## RECOMMENDATIONS

1. **Immediate Implementation**: Lead IDs, Company IDs, Premium status, Activity status
2. **Short-term**: Mutual connections, Search context, Pagination
3. **Long-term**: Enhanced spotlight data, Page metadata, Data quality scoring

---

## NOTES

- Some data may require JavaScript execution to be fully available
- HTML structure may change over time
- Not all profiles will have all optional fields
- Some data is in hidden dialogs/popups that may not be in static HTML
- URL parameters are encoded and require proper decoding

