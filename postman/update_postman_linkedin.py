"""Script to add LinkedIn endpoints to Postman collection."""

import json

# Read the Postman collection
with open('postman/Appointment360 API.postman_collection.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Create LinkedIn item with two requests
linkedin_item = {
    "name": "LinkedIn",
    "item": [
        {
            "name": "Search by LinkedIn URL",
            "request": {
                "method": "GET",
                "header": [
                    {
                        "key": "Authorization",
                        "value": "Bearer {{accessToken}}",
                        "type": "text"
                    },
                    {
                        "key": "Accept",
                        "value": "application/json",
                        "type": "text"
                    }
                ],
                "url": {
                    "raw": "{{baseUrl}}/api/v2/linkedin/?url=https://www.linkedin.com/in/example",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "v2", "linkedin", ""],
                    "query": [
                        {
                            "key": "url",
                            "value": "https://www.linkedin.com/in/example",
                            "description": "LinkedIn URL to search for (person or company)"
                        }
                    ]
                },
                "description": "Search for contacts and companies by LinkedIn URL. Searches both person LinkedIn URLs (ContactMetadata.linkedin_url) and company LinkedIn URLs (CompanyMetadata.linkedin_url)."
            },
            "response": []
        },
        {
            "name": "Create or Update by LinkedIn URL",
            "request": {
                "method": "POST",
                "header": [
                    {
                        "key": "Authorization",
                        "value": "Bearer {{accessToken}}",
                        "type": "text"
                    },
                    {
                        "key": "Content-Type",
                        "value": "application/json",
                        "type": "text"
                    }
                ],
                "body": {
                    "mode": "raw",
                    "raw": json.dumps({
                        "url": "https://www.linkedin.com/in/example",
                        "contact_data": {
                            "first_name": "John",
                            "last_name": "Doe",
                            "email": "john.doe@example.com",
                            "title": "Software Engineer"
                        },
                        "contact_metadata": {
                            "city": "San Francisco",
                            "state": "CA",
                            "country": "US"
                        }
                    }, indent=2),
                    "options": {
                        "raw": {
                            "language": "json"
                        }
                    }
                },
                "url": {
                    "raw": "{{baseUrl}}/api/v2/linkedin/",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "v2", "linkedin", ""]
                },
                "description": "Create or update contacts and companies based on LinkedIn URL. If a record with the LinkedIn URL already exists, it will be updated. Otherwise, new records will be created."
            },
            "response": []
        }
    ]
}

# Add LinkedIn item to the collection
data['item'].append(linkedin_item)

# Write back to file
with open('postman/Appointment360 API.postman_collection.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("LinkedIn endpoints added successfully to Postman collection!")

