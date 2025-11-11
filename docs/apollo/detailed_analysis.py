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
        'organizationNumJobsRange[min]', 'organizationJobPostedAtRange[min]'
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
    'Other': ['uniqueUrlId']
}

# Analyze each URL
analysis = {
    'total_urls': len(urls_data),
    'unique_urls': len(set([u['url'] for u in urls_data])),
    'categories': defaultdict(lambda: {
        'param_count': Counter(),
        'value_examples': defaultdict(set),
        'urls_using': 0
    }),
    'url_details': []
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
                        analysis['categories'][category]['value_examples'][param].update(values[:5])  # Store up to 5 examples
                        analysis['categories'][category]['urls_using'] = max(
                            analysis['categories'][category]['urls_using'],
                            analysis['categories'][category]['param_count'][param]
                        )
            
            analysis['url_details'].append(url_detail)

# Write detailed JSON analysis
with open('url_analysis.json', 'w', encoding='utf-8') as f:
    json.dump(analysis, f, indent=2, ensure_ascii=False)

print("Detailed analysis complete. Results written to url_analysis.json")

