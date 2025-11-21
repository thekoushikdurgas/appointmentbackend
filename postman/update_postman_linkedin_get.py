"""Script to update LinkedIn GET request in Postman collection to use body instead of query parameter."""

import json

# Read the Postman collection
with open('postman/Appointment360 API.postman_collection.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Find LinkedIn item
linkedin_item = None
for item in data.get('item', []):
    if item.get('name') == 'LinkedIn':
        linkedin_item = item
        break

if not linkedin_item:
    print("LinkedIn item not found in collection!")
    exit(1)

# Find "Search by LinkedIn URL" request
search_request = None
for req in linkedin_item.get('item', []):
    if req.get('name') == 'Search by LinkedIn URL':
        search_request = req
        break

if not search_request:
    print("Search by LinkedIn URL request not found!")
    exit(1)

# Update the request
request_obj = search_request.get('request', {})
url_obj = request_obj.get('url', {})

# Remove query parameter
url_obj['raw'] = '{{baseUrl}}/api/v2/linkedin/'
url_obj['query'] = []

# Add JSON body
request_obj['body'] = {
    'mode': 'raw',
    'raw': json.dumps({
        'url': 'https://www.linkedin.com/in/example'
    }, indent=2),
    'options': {
        'raw': {
            'language': 'json'
        }
    }
}

# Add Content-Type header if not present
headers = request_obj.get('header', [])
content_type_exists = any(h.get('key', '').lower() == 'content-type' for h in headers)
if not content_type_exists:
    headers.append({
        'key': 'Content-Type',
        'value': 'application/json',
        'type': 'text'
    })

# Update description
search_request['request']['description'] = 'Search for contacts and companies by LinkedIn URL. Searches both person LinkedIn URLs (ContactMetadata.linkedin_url) and company LinkedIn URLs (CompanyMetadata.linkedin_url).'

# Write back to file
with open('postman/Appointment360 API.postman_collection.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("LinkedIn GET request updated successfully in Postman collection!")
print("Changed from query parameter to JSON body format.")

