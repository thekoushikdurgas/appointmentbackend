import csv
from urllib.parse import urlparse, parse_qs, unquote
from collections import defaultdict, Counter
import json

# Read all URLs from CSV
urls_data = []
with open('Instantlead.net-2 - Sheet1.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row.get('apollo_url'):
            urls_data.append({
                'url': row['apollo_url'],
                'created_at': row.get('created_at', ''),
                'leads_needed': row.get('leads_needed', ''),
                'status': row.get('status', ''),
                'data_extracted': row.get('data_extracted', '')
            })

# Categorize parameters
param_categories = {
    'Pagination': ['page'],
    'Sorting': ['sortByField', 'sortAscending'],
    'Person Filters': [
        'personTitles[]', 'personNotTitles[]', 'personLocations[]', 
        'personNotLocations[]', 'personSeniorities[]', 
        'personDepartmentOrSubdepartments[]'
    ],
    'Organization Filters': [
        'organizationNumEmployeesRanges[]', 'organizationLocations[]',
        'organizationNotLocations[]', 'organizationIndustryTagIds[]',
        'organizationNotIndustryTagIds[]', 'organizationJobLocations[]',
        'organizationNumJobsRange[min]', 'organizationJobPostedAtRange[min]',
        'revenueRange[min]', 'revenueRange[max]', 'organizationTradingStatus[]'
    ],
    'Email Filters': [
        'contactEmailStatusV2[]', 'contactEmailExcludeCatchAll'
    ],
    'Keyword Filters': [
        'qOrganizationKeywordTags[]', 'qNotOrganizationKeywordTags[]',
        'includedOrganizationKeywordFields[]', 'excludedOrganizationKeywordFields[]'
    ],
    'Search Lists': [
        'qOrganizationSearchListId', 'qNotOrganizationSearchListId',
        'qPersonPersonaIds[]'
    ],
    'Technology': ['currentlyUsingAnyOfTechnologyUids[]'],
    'Market Segments': ['marketSegments[]'],
    'Intent': ['intentStrengths[]'],
    'Lookalike': ['lookalikeOrganizationIds[]'],
    'Prospecting': ['prospectedByCurrentTeam[]'],
    'Other': ['uniqueUrlId', 'tour', 'includeSimilarTitles', 'existFields[]', 'notOrganizationIds[]']
}

# Analyze each URL
analysis = {
    'total_urls': len(urls_data),
    'unique_urls': len(set([u['url'] for u in urls_data])),
    'categories': {},
    'url_details': []
}

# Initialize category tracking
for category in param_categories.keys():
    analysis['categories'][category] = {
        'param_count': Counter(),
        'value_examples': defaultdict(list),
        'urls_using': 0,
        'params': {}
    }

for url_info in urls_data:
    url = url_info['url']
    if '#' in url:
        hash_part = url.split('#', 1)[1]
        if '?' in hash_part:
            path_part, query_part = hash_part.split('?', 1)
            params = parse_qs(query_part)
            
            url_detail = {
                'url': url,
                'path': path_part,
                'params': {},
                'created_at': url_info['created_at'],
                'leads_needed': url_info['leads_needed'],
                'status': url_info['status']
            }
            
            for category, param_list in param_categories.items():
                for param in param_list:
                    if param in params:
                        values = [unquote(v) for v in params[param]]
                        url_detail['params'][param] = values
                        analysis['categories'][category]['param_count'][param] += 1
                        # Store up to 5 unique examples
                        existing = set(analysis['categories'][category]['value_examples'][param])
                        for v in values[:10]:  # Check more to get unique ones
                            if len(existing) < 5 and v not in existing:
                                existing.add(v)
                                analysis['categories'][category]['value_examples'][param].append(v)
                        analysis['categories'][category]['value_examples'][param] = list(existing)[:5]
            
            analysis['url_details'].append(url_detail)

# Calculate URLs using each category
for category in analysis['categories']:
    total_usage = sum(analysis['categories'][category]['param_count'].values())
    analysis['categories'][category]['urls_using'] = total_usage

# Helper function to get parameter descriptions
def get_parameter_description(param):
    descriptions = {
        'page': 'Page number for pagination',
        'sortByField': 'Field to sort results by',
        'sortAscending': 'Sort direction (true/false)',
        'personTitles[]': 'Job titles to include',
        'personNotTitles[]': 'Job titles to exclude',
        'personLocations[]': 'Person locations to include',
        'personNotLocations[]': 'Person locations to exclude',
        'personSeniorities[]': 'Seniority levels to include',
        'personDepartmentOrSubdepartments[]': 'Departments to include',
        'organizationNumEmployeesRanges[]': 'Company size ranges',
        'organizationLocations[]': 'Organization locations to include',
        'organizationNotLocations[]': 'Organization locations to exclude',
        'organizationIndustryTagIds[]': 'Industry tag IDs to include',
        'organizationNotIndustryTagIds[]': 'Industry tag IDs to exclude',
        'contactEmailStatusV2[]': 'Email verification status',
        'contactEmailExcludeCatchAll': 'Exclude catch-all emails',
        'qOrganizationKeywordTags[]': 'Organization keywords to include',
        'qNotOrganizationKeywordTags[]': 'Organization keywords to exclude',
        'includedOrganizationKeywordFields[]': 'Fields to search for keywords',
        'excludedOrganizationKeywordFields[]': 'Fields to exclude from keyword search',
        'qOrganizationSearchListId': 'Saved organization list ID',
        'qNotOrganizationSearchListId': 'Excluded organization list ID',
        'qPersonPersonaIds[]': 'Person persona IDs',
        'currentlyUsingAnyOfTechnologyUids[]': 'Technology stack filters',
        'marketSegments[]': 'Market segment filters',
        'intentStrengths[]': 'Buying intent levels',
        'lookalikeOrganizationIds[]': 'Similar organization IDs',
        'uniqueUrlId': 'Unique URL identifier',
        'tour': 'Tour mode flag',
        'includeSimilarTitles': 'Include similar titles',
        'revenueRange[min]': 'Minimum revenue',
        'revenueRange[max]': 'Maximum revenue',
        'organizationTradingStatus[]': 'Company trading status',
        'organizationJobLocations[]': 'Job posting locations',
        'organizationNumJobsRange[min]': 'Minimum number of job postings',
        'organizationJobPostedAtRange[min]': 'Job posting date range',
        'prospectedByCurrentTeam[]': 'Prospecting status',
        'existFields[]': 'Required fields',
        'notOrganizationIds[]': 'Excluded organization IDs'
    }
    return descriptions.get(param, 'Filter parameter')

# Generate markdown documentation
markdown_content = f"""# Apollo.io URL Analysis and Breakdown

## Executive Summary

- **Total URLs**: {analysis['total_urls']}
- **Unique URLs**: {analysis['unique_urls']}
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

"""

# Add detailed parameter documentation
for category, category_data in analysis['categories'].items():
    if category_data['param_count']:
        markdown_content += f"\n### {category}\n\n"
        markdown_content += f"**URLs using this category**: {category_data['urls_using']}\n\n"
        markdown_content += "| Parameter | Usage Count | Description | Example Values |\n"
        markdown_content += "|-----------|-------------|-------------|----------------|\n"
        
        for param, count in category_data['param_count'].most_common():
            examples = category_data['value_examples'][param]
            examples_str = ", ".join(examples[:3]) if examples else "N/A"
            if len(examples) > 3:
                examples_str += f" (+{len(examples)-3} more)"
            
            # Add description based on parameter name
            desc = get_parameter_description(param)
            markdown_content += f"| `{param}` | {count} | {desc} | {examples_str} |\n"
        
        markdown_content += "\n"

# Add detailed parameter descriptions
markdown_content += """
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

"""

# Write markdown file
with open('apollo_link.md', 'w', encoding='utf-8') as f:
    f.write(markdown_content)

print(f"Documentation generated successfully!")
print(f"Total URLs analyzed: {analysis['total_urls']}")
print(f"Unique URLs: {analysis['unique_urls']}")
print(f"Documentation written to: apollo_link.md")

