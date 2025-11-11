# Apollo.io URL Analysis and Breakdown

## Executive Summary

- **Total URLs**: 129
- **Unique URLs**: 127
- **Base Path**: All URLs use `#/people` (People Search)
- **Analysis Date**: Generated from Instantlead.net-2 - Sheet1.csv

## URL Structure

All Apollo.io URLs follow this structure:

```
https://app.apollo.io/#/people?[query_parameters]
```

### Components:
- **Base URL**: `https://app.apollo.io`
- **Hash Route**: `#/people` (indicates People Search page)
- **Query Parameters**: Filter and search criteria (URL encoded)

## Parameter Categories


### Pagination

**URLs using this category**: 128

| Parameter | Usage Count | Description | Example Values |
|-----------|-------------|-------------|----------------|
| `page` | 128 | Page number for pagination | 1, 2, 4 (+1 more) |


### Sorting

**URLs using this category**: 252

| Parameter | Usage Count | Description | Example Values |
|-----------|-------------|-------------|----------------|
| `sortByField` | 126 | Field to sort results by | recommendations_score, sanitized_organization_name_unanalyzed, person_name.raw (+2 more) |
| `sortAscending` | 126 | Sort direction (true/false) | false, true |


### Person Filters

**URLs using this category**: 301

| Parameter | Usage Count | Description | Example Values |
|-----------|-------------|-------------|----------------|
| `personLocations[]` | 110 | Person locations to include | Alabama, US, Arizona, california (+2 more) |
| `personTitles[]` | 99 | Job titles to include | founder, owner, ceo (+2 more) |
| `personSeniorities[]` | 46 | Seniority levels to include | senior, manager, head (+2 more) |
| `personNotTitles[]` | 24 | Job titles to exclude | "team lead", coordinator, specialist (+2 more) |
| `personDepartmentOrSubdepartments[]` | 13 | Departments to include | executive, master_marketing, founder (+2 more) |
| `personNotLocations[]` | 9 | Person locations to exclude | China,  China, India, Iran, Jordan, Syria, Lebanon, Snohomish, Washington (+2 more) |


### Organization Filters

**URLs using this category**: 225

| Parameter | Usage Count | Description | Example Values |
|-----------|-------------|-------------|----------------|
| `organizationNumEmployeesRanges[]` | 106 | Company size ranges | 51,100, 11,20, 1,10 (+2 more) |
| `organizationIndustryTagIds[]` | 45 | Industry tag IDs to include | 5567cd467369644d39040000, 5567cd4773696439dd350000, 5567cdd67369643e64020000 (+2 more) |
| `organizationLocations[]` | 36 | Organization locations to include | Tennessee, US, Alabama, US, South Carolina, US (+2 more) |
| `organizationNotIndustryTagIds[]` | 16 | Industry tag IDs to exclude | 5567cd4c73696453e1300000, 5567cd527369643981050000, 5567cdd97369645430680000 (+2 more) |
| `organizationNotLocations[]` | 4 | Organization locations to exclude | China |
| `organizationJobLocations[]` | 4 | Job posting locations | China, Nigeria, United States (+2 more) |
| `organizationNumJobsRange[min]` | 4 | Minimum number of job postings | 1 |
| `organizationJobPostedAtRange[min]` | 4 | Job posting date range | 60_days_ago |
| `revenueRange[min]` | 3 | Minimum revenue | 5000000, 1000000, 100000000 |
| `revenueRange[max]` | 2 | Maximum revenue | 10000000000, 250000000 |
| `organizationTradingStatus[]` | 1 | Company trading status | private |


### Email Filters

**URLs using this category**: 85

| Parameter | Usage Count | Description | Example Values |
|-----------|-------------|-------------|----------------|
| `contactEmailStatusV2[]` | 73 | Email verification status | user_managed, likely_to_engage, unverified (+2 more) |
| `contactEmailExcludeCatchAll` | 12 | Exclude catch-all emails | true |


### Keyword Filters

**URLs using this category**: 171

| Parameter | Usage Count | Description | Example Values |
|-----------|-------------|-------------|----------------|
| `includedOrganizationKeywordFields[]` | 73 | Fields to search for keywords | social_media_description, name, tags |
| `qOrganizationKeywordTags[]` | 51 | Organization keywords to include | marketing services, creative, Agency (+2 more) |
| `excludedOrganizationKeywordFields[]` | 25 | Fields to exclude from keyword search | social_media_description, name, seo_description (+1 more) |
| `qNotOrganizationKeywordTags[]` | 22 | Organization keywords to exclude | Agriculture, Airlines/Aviation, Apparel & Fashion (+2 more) |


### Search Lists

**URLs using this category**: 21

| Parameter | Usage Count | Description | Example Values |
|-----------|-------------|-------------|----------------|
| `qPersonPersonaIds[]` | 8 | Person persona IDs | 674f26ee61657e02ce11cb2b, 68f9248998c6f70015ec6cab, 6819492a816af400113835f4 (+2 more) |
| `qNotOrganizationSearchListId` | 7 | Excluded organization list ID | 68fb8d52886f9d00154d8792, 68fb3e7b403e00001528532d, 68fbfc4f9dc0c30021c14f55 (+2 more) |
| `qOrganizationSearchListId` | 6 | Saved organization list ID | 68fb5723dd0022000db39f18, 68fe40fa88a297001de275aa, 68f7b60b02adc0001919f471 (+2 more) |


### Technology

**URLs using this category**: 4

| Parameter | Usage Count | Description | Example Values |
|-----------|-------------|-------------|----------------|
| `currentlyUsingAnyOfTechnologyUids[]` | 4 | Technology stack filters | shopify_plus, shopify_product_reviews, shopify_unlimited (+2 more) |


### Market Segments

**URLs using this category**: 14

| Parameter | Usage Count | Description | Example Values |
|-----------|-------------|-------------|----------------|
| `marketSegments[]` | 14 | Market segment filters | e-commerce, b2c, b2b2c (+2 more) |


### Intent

**URLs using this category**: 1

| Parameter | Usage Count | Description | Example Values |
|-----------|-------------|-------------|----------------|
| `intentStrengths[]` | 1 | Buying intent levels | mid, none, high (+1 more) |


### Lookalike

**URLs using this category**: 3

| Parameter | Usage Count | Description | Example Values |
|-----------|-------------|-------------|----------------|
| `lookalikeOrganizationIds[]` | 3 | Similar organization IDs | 5569a9fb7369642525957100, 54a129f869702d9b8b8dea01, 55e86501f3e5bb616400044b (+2 more) |


### Prospecting

**URLs using this category**: 7

| Parameter | Usage Count | Description | Example Values |
|-----------|-------------|-------------|----------------|
| `prospectedByCurrentTeam[]` | 7 | Prospecting status | no |


### Other

**URLs using this category**: 25

| Parameter | Usage Count | Description | Example Values |
|-----------|-------------|-------------|----------------|
| `uniqueUrlId` | 17 | Unique URL identifier | R0stG397ho, wxAKT7af2i, poDy1zcYZv (+2 more) |
| `includeSimilarTitles` | 3 | Include similar titles | false |
| `tour` | 2 | Tour mode flag | true |
| `existFields[]` | 2 | Required fields | person_title_normalized, organization_total_funding_long |
| `notOrganizationIds[]` | 1 | Excluded organization IDs | 57c4ace7a6da9867ee5599e7, 54a11ec569702d8ed45e8b01 |


## Detailed Parameter Descriptions

### Pagination Parameters

#### `page`
- **Type**: Integer
- **Purpose**: Specifies which page of results to display
- **Usage**: Found in 128 URLs (99.2%)
- **Example Values**: `1`, `2`, `4`, `81`
- **Notes**: Most searches start at page 1

### Sorting Parameters

#### `sortByField`
- **Type**: String
- **Purpose**: Field to sort results by
- **Usage**: Found in 126 URLs (97.7%)
- **Common Values**:
  - `[none]` - No sorting
  - `recommendations_score` - Sort by Apollo's recommendation score
  - `sanitized_organization_name_unanalyzed` - Sort alphabetically by company name
  - `person_name.raw` - Sort by person name
  - `organization_linkedin_industry_tag_ids` - Sort by industry tags

#### `sortAscending`
- **Type**: Boolean
- **Purpose**: Sort direction (true = ascending, false = descending)
- **Usage**: Found in 126 URLs (97.7%)
- **Values**: `true`, `false`
- **Default**: Usually `false` (descending)

### Person Filters

#### `personTitles[]`
- **Type**: Array of strings
- **Purpose**: Filter by job titles (inclusive)
- **Usage**: Found in 99 URLs (76.7%)
- **Example Values**: `CEO`, `Founder`, `Marketing Director`, `VP of Sales`
- **Notes**: Can include multiple titles. Supports variations and abbreviations.

#### `personNotTitles[]`
- **Type**: Array of strings
- **Purpose**: Exclude specific job titles
- **Usage**: Found in 24 URLs (18.6%)
- **Example Values**: `assistant`, `intern`, `coordinator`, `engineer`
- **Notes**: Used to filter out unwanted titles

#### `personLocations[]`
- **Type**: Array of strings
- **Purpose**: Filter by person location (inclusive)
- **Usage**: Found in 110 URLs (85.3%)
- **Example Values**: `United States`, `Canada`, `California`, `New York, US`
- **Notes**: Supports countries, states, cities, and regions

#### `personNotLocations[]`
- **Type**: Array of strings
- **Purpose**: Exclude specific locations
- **Usage**: Found in 9 URLs (7.0%)
- **Example Values**: `India`, `China`, `Africa`
- **Notes**: Used to exclude specific geographic regions

#### `personSeniorities[]`
- **Type**: Array of strings
- **Purpose**: Filter by seniority level
- **Usage**: Found in 46 URLs (35.7%)
- **Common Values**: `c_suite`, `owner`, `founder`, `partner`, `vp`, `head`, `director`, `manager`, `senior`, `entry`
- **Notes**: Hierarchical levels from executive to entry-level

#### `personDepartmentOrSubdepartments[]`
- **Type**: Array of strings
- **Purpose**: Filter by department or subdepartment
- **Usage**: Found in 13 URLs (10.1%)
- **Example Values**: `master_marketing`, `revenue_operations`, `inside_sales`, `sales_operations`
- **Notes**: Uses internal Apollo department codes

### Organization Filters

#### `organizationNumEmployeesRanges[]`
- **Type**: Array of strings (range format)
- **Purpose**: Filter by company size
- **Usage**: Found in 106 URLs (82.2%)
- **Format**: `min,max` or single value like `10001`
- **Example Values**: `1,10`, `11,20`, `21,50`, `51,100`, `101,200`, `201,500`, `501,1000`, `10001`
- **Notes**: Most common filter, used to target specific company sizes

#### `organizationLocations[]`
- **Type**: Array of strings
- **Purpose**: Filter by organization location
- **Usage**: Found in 36 URLs (27.9%)
- **Example Values**: `United States`, `Germany`, `Palo Alto, California`
- **Notes**: Can specify countries, states, or cities

#### `organizationNotLocations[]`
- **Type**: Array of strings
- **Purpose**: Exclude specific organization locations
- **Usage**: Found in 4 URLs (3.1%)
- **Example Values**: `China`
- **Notes**: Used to exclude specific regions

#### `organizationIndustryTagIds[]`
- **Type**: Array of hex strings
- **Purpose**: Filter by industry using Apollo's internal tag IDs
- **Usage**: Found in 45 URLs (34.9%)
- **Format**: Hexadecimal IDs like `5567cd4773696439dd350000`
- **Notes**: Apollo uses internal IDs for industries. Multiple IDs can be combined.

#### `organizationNotIndustryTagIds[]`
- **Type**: Array of hex strings
- **Purpose**: Exclude specific industries
- **Usage**: Found in 16 URLs (12.4%)
- **Notes**: Used to filter out unwanted industries

#### `revenueRange[min]` and `revenueRange[max]`
- **Type**: Integer
- **Purpose**: Filter by company revenue range
- **Usage**: Found in 1 URL (0.8%)
- **Example**: `min=5000000`, `max=250000000`
- **Notes**: Revenue in dollars

#### `organizationTradingStatus[]`
- **Type**: Array of strings
- **Purpose**: Filter by company trading status
- **Usage**: Found in 1 URL (0.8%)
- **Values**: `private`, `public`
- **Notes**: Distinguishes between private and public companies

### Email Filters

#### `contactEmailStatusV2[]`
- **Type**: Array of strings
- **Purpose**: Filter by email verification status
- **Usage**: Found in 73 URLs (56.6%)
- **Values**: 
  - `verified` - Email is verified
  - `likely_to_engage` - Email likely to engage
  - `unverified` - Email not verified
  - `user_managed` - User-managed email
- **Notes**: Critical for email deliverability

#### `contactEmailExcludeCatchAll`
- **Type**: Boolean
- **Purpose**: Exclude catch-all email addresses
- **Usage**: Found in 12 URLs (9.3%)
- **Values**: `true`
- **Notes**: Catch-all emails have lower deliverability

### Keyword Filters

#### `qOrganizationKeywordTags[]`
- **Type**: Array of strings
- **Purpose**: Include organizations with specific keywords
- **Usage**: Found in 51 URLs (39.5%)
- **Example Values**: `saas`, `marketing`, `software development`, `construction`
- **Notes**: Searches in tags, name, and social media description

#### `qNotOrganizationKeywordTags[]`
- **Type**: Array of strings
- **Purpose**: Exclude organizations with specific keywords
- **Usage**: Found in 22 URLs (17.1%)
- **Example Values**: `Agriculture`, `Retail`, `Restaurants`, `marketing services`
- **Notes**: Used to filter out unwanted industries or business types

#### `includedOrganizationKeywordFields[]`
- **Type**: Array of strings
- **Purpose**: Specify which fields to search for keywords
- **Usage**: Found in 73 URLs (56.6%)
- **Values**: `tags`, `name`, `social_media_description`
- **Notes**: Controls where keyword searches are performed

#### `excludedOrganizationKeywordFields[]`
- **Type**: Array of strings
- **Purpose**: Exclude specific fields from keyword search
- **Usage**: Found in 25 URLs (19.4%)
- **Values**: `tags`, `name`, `social_media_description`, `seo_description`
- **Notes**: Used to narrow search scope

### Search Lists

#### `qOrganizationSearchListId`
- **Type**: String (hex ID)
- **Purpose**: Use a saved organization search list
- **Usage**: Found in 6 URLs (4.7%)
- **Format**: Hex ID like `68f53d30a36cc6001d7a53dc`
- **Notes**: References a pre-saved list of organizations

#### `qNotOrganizationSearchListId`
- **Type**: String (hex ID)
- **Purpose**: Exclude organizations from a saved list
- **Usage**: Found in 7 URLs (5.4%)
- **Notes**: Used to exclude specific organizations

#### `qPersonPersonaIds[]`
- **Type**: Array of hex IDs
- **Purpose**: Filter by saved person personas
- **Usage**: Found in 8 URLs (6.2%)
- **Format**: Hex IDs like `674f26ee61657e02ce11cb2b`
- **Notes**: References pre-defined person profiles

### Technology Filters

#### `currentlyUsingAnyOfTechnologyUids[]`
- **Type**: Array of strings
- **Purpose**: Filter by technology stack
- **Usage**: Found in 4 URLs (3.1%)
- **Example Values**: `shopify`, `magento`, `woo_commerce`, `hubspot`, `zoominfo`
- **Notes**: Identifies companies using specific technologies

### Market Segments

#### `marketSegments[]`
- **Type**: Array of strings
- **Purpose**: Filter by market segment
- **Usage**: Found in 14 URLs (10.9%)
- **Values**: `b2b`, `b2c`, `b2b2c`, `d2c`, `e-commerce`, `fintech`, `saas`, `services`, `retail`
- **Notes**: Categorizes business models

### Intent Filters

#### `intentStrengths[]`
- **Type**: Array of strings
- **Purpose**: Filter by buying intent signals
- **Usage**: Found in 1 URL (0.8%)
- **Values**: `low`, `mid`, `high`, `none`
- **Notes**: Based on Apollo's intent detection

### Lookalike Matching

#### `lookalikeOrganizationIds[]`
- **Type**: Array of hex IDs
- **Purpose**: Find organizations similar to specified ones
- **Usage**: Found in 1 URL (0.8%)
- **Format**: Hex IDs like `54a129f869702d9b8b8dea01`
- **Notes**: Uses machine learning to find similar companies

### Other Parameters

#### `uniqueUrlId`
- **Type**: String
- **Purpose**: Unique identifier for saved searches
- **Usage**: Found in 17 URLs (13.2%)
- **Format**: Alphanumeric like `CntHsqwQ9m`, `Fp8Vr5PLXI`
- **Notes**: Used to reference saved search configurations

#### `tour`
- **Type**: Boolean
- **Purpose**: Enable tour mode
- **Usage**: Found in 1 URL (0.8%)
- **Values**: `true`
- **Notes**: Used for onboarding/tutorials

#### `includeSimilarTitles`
- **Type**: Boolean
- **Purpose**: Include similar job titles in search
- **Usage**: Found in 2 URLs (1.6%)
- **Values**: `true`, `false`
- **Notes**: Expands title matching

#### `existFields[]`
- **Type**: Array of strings
- **Purpose**: Require specific fields to exist
- **Usage**: Found in 1 URL (0.8%)
- **Example**: `organization_total_funding_long`
- **Notes**: Ensures data completeness

#### `notOrganizationIds[]`
- **Type**: Array of hex IDs
- **Purpose**: Exclude specific organizations by ID
- **Usage**: Found in 1 URL (0.8%)
- **Notes**: Direct organization exclusion

## Common Filter Combinations

### High-Value Executive Search
```
personTitles[]=CEO
personTitles[]=Founder
personSeniorities[]=c_suite
contactEmailStatusV2[]=verified
organizationNumEmployeesRanges[]=11,50
```

### Marketing Professionals
```
personTitles[]=Marketing Director
personTitles[]=CMO
personDepartmentOrSubdepartments[]=master_marketing
personLocations[]=United States
```

### Technology Companies
```
qOrganizationKeywordTags[]=saas
qOrganizationKeywordTags[]=software
organizationIndustryTagIds[]=[tech industry IDs]
marketSegments[]=b2b
```

### Verified Email Focus
```
contactEmailStatusV2[]=verified
contactEmailExcludeCatchAll=true
personLocations[]=United States
```

## Statistics and Insights

### Most Used Parameters
1. **page** - 128 URLs (99.2%) - Almost all searches use pagination
2. **sortByField** - 126 URLs (97.7%) - Most searches specify sorting
3. **sortAscending** - 126 URLs (97.7%) - Sort direction is commonly specified
4. **personLocations[]** - 110 URLs (85.3%) - Geographic targeting is very common
5. **organizationNumEmployeesRanges[]** - 106 URLs (82.2%) - Company size is a key filter

### Parameter Categories Usage
- **Person Filters**: Most common category, used in 99+ URLs
- **Organization Filters**: Second most common, used in 106+ URLs
- **Email Filters**: Used in 73 URLs (56.6%) - Important for deliverability
- **Keyword Filters**: Used in 51-73 URLs - Flexible search capability
- **Sorting**: Used in 126 URLs (97.7%) - Almost universal

### Search Patterns
- **Geographic Targeting**: 85% of searches include location filters
- **Company Size Targeting**: 82% specify employee ranges
- **Title-Based Search**: 77% filter by job titles
- **Email Quality**: 57% filter by email verification status
- **Industry Targeting**: 35% use industry tag filters

## URL Examples

### Example 1: Marketing Directors in US Tech Companies
```
https://app.apollo.io/#/people?personTitles[]=marketing&sortAscending=false&sortByField=[none]&uniqueUrlId=CntHsqwQ9m&personSeniorities[]=director&organizationNumEmployeesRanges[]=10001&personDepartmentOrSubdepartments[]=master_marketing&page=1
```

### Example 2: Verified CEOs in SaaS Companies
```
https://app.apollo.io/#/people?page=1&contactEmailStatusV2[]=verified&contactEmailExcludeCatchAll=true&personTitles[]=ceo&personTitles[]=founder&personLocations[]=United States&organizationNumEmployeesRanges[]=1,10&qOrganizationKeywordTags[]=saas solutions&sortByField=recommendations_score&sortAscending=false
```

### Example 3: Complex Multi-Filter Search
```
https://app.apollo.io/#/people?contactEmailStatusV2[]=verified&personLocations[]=california&organizationNumEmployeesRanges[]=2,5&qOrganizationKeywordTags[]=Marketing&qNotOrganizationKeywordTags[]=Agriculture&includedOrganizationKeywordFields[]=tags&sortByField=[none]&sortAscending=false&page=1
```

## Notes

- All URLs use hash-based routing (`#/people`)
- Parameters are URL-encoded (spaces become `%20`, etc.)
- Array parameters use `[]` notation (e.g., `personTitles[]`)
- Multiple values for the same parameter are repeated in the URL
- Apollo uses internal IDs for industries and organizations
- The `uniqueUrlId` parameter references saved searches
- Most searches combine multiple filter types for precision

## Data Source

This analysis is based on 129 URLs from `Instantlead.net-2 - Sheet1.csv`, containing Apollo.io search URLs used for lead generation campaigns.

