#!/usr/bin/env python3
"""Generate and update Connectra API Postman Collection.

This script merges the functionality of:
- update_connectra_auth.py: Updates authentication to use X-API-Key
- add_connectra_write_endpoints.py: Adds write endpoints (CRUD operations)
- add_new_endpoints.py: Adds Marketing/Dashboard Pages (for Contact360, not Connectra - kept for reference)

For Connectra API, this script:
1. Updates all endpoints to use X-API-Key authentication
2. Adds write endpoints (create, update, delete, upsert, bulk) for contacts and companies
3. Ensures proper collection variables and test scripts
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional


class ConnectraCollectionGenerator:
    """Generate and update Connectra API Postman collection."""
    
    def __init__(self, collection_path: Optional[Path] = None):
        """Initialize the generator.
        
        Args:
            collection_path: Path to Connectra collection JSON file. If None, uses default location.
        """
        if collection_path is None:
            script_dir = Path(__file__).parent if '__file__' in globals() else Path.cwd() / "backend" / "scripts" / "postman"
            collection_path = script_dir / "json" / "Connectra API.postman_collection.json"
        
        self.collection_path = collection_path
        self.collection = None
    
    def load_collection(self) -> bool:
        """Load the Connectra collection from file.
        
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            with open(self.collection_path, 'r', encoding='utf-8') as f:
                self.collection = json.load(f)
            return True
        except FileNotFoundError:
            print(f"Error: Collection file not found: {self.collection_path}")
            return False
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in collection file: {e}")
            return False
    
    def save_collection(self) -> bool:
        """Save the updated collection to file.
        
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            with open(self.collection_path, 'w', encoding='utf-8') as f:
                json.dump(self.collection, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving collection: {e}")
            return False
    
    def add_api_key_variable(self):
        """Add API Key variable to collection if it doesn't exist."""
        api_key_var = {
            "key": "apiKey",
            "value": "",
            "type": "string",
            "description": "Connectra API Key (X-API-Key header)"
        }
        
        if 'variable' not in self.collection:
            self.collection['variable'] = []
        
        # Check if variable already exists
        var_exists = False
        for var in self.collection['variable']:
            if var.get('key') == 'apiKey':
                var_exists = True
                break
        
        if not var_exists:
            self.collection['variable'].append(api_key_var)
            print("Added apiKey collection variable")
    
    def update_auth_in_item(self, item: Dict[str, Any]) -> bool:
        """Recursively update authentication in item and all sub-items.
        
        Args:
            item: Postman collection item (folder or request)
        
        Returns:
            True if any updates were made, False otherwise
        """
        updated = False
        
        # Update request headers if this is a request item
        if 'request' in item:
            request = item['request']
            
            # Update headers - replace Bearer token with X-API-Key
            if 'header' in request:
                headers = request['header']
                new_headers = []
                has_api_key = False
                
                for header in headers:
                    if header.get('key') == 'Authorization' and 'Bearer' in str(header.get('value', '')):
                        # Replace Bearer token with X-API-Key
                        new_headers.append({
                            "key": "X-API-Key",
                            "value": "{{apiKey}}",
                            "disabled": False,
                            "description": "Connectra API Key"
                        })
                        has_api_key = True
                        updated = True
                    elif header.get('key') == 'X-API-Key':
                        # Already correct, keep it
                        new_headers.append(header)
                        has_api_key = True
                    else:
                        # Keep other headers
                        new_headers.append(header)
                
                request['header'] = new_headers
            
            # Ensure X-API-Key header exists for all authenticated endpoints (except health check)
            if 'url' in request:
                url_path = str(request['url'].get('path', []))
                if 'health' not in url_path.lower() and 'favicon' not in url_path.lower() and 'admin' not in url_path.lower():
                    # Check if X-API-Key header exists
                    has_api_key = False
                    if 'header' in request:
                        for header in request['header']:
                            if header.get('key') == 'X-API-Key':
                                has_api_key = True
                                break
                    
                    if not has_api_key:
                        # Add X-API-Key header
                        if 'header' not in request:
                            request['header'] = []
                        request['header'].append({
                            "key": "X-API-Key",
                            "value": "{{apiKey}}",
                            "disabled": False,
                            "description": "Connectra API Key"
                        })
                        updated = True
            
            # Remove Bearer auth from request auth config
            if 'auth' in request:
                if request['auth'].get('type') == 'bearer':
                    # Remove bearer auth - we use X-API-Key header instead
                    del request['auth']
                    updated = True
        
        # Recursively update sub-items
        if 'item' in item:
            for sub_item in item['item']:
                if self.update_auth_in_item(sub_item):
                    updated = True
        
        return updated
    
    def update_authentication(self) -> Dict[str, int]:
        """Update all endpoints to use X-API-Key authentication.
        
        Returns:
            Dictionary with update statistics
        """
        stats = {
            'folders_updated': 0,
            'endpoints_updated': 0
        }
        
        # Count initial Bearer tokens
        def count_bearer_tokens(item, count=0):
            if 'request' in item:
                if 'header' in item['request']:
                    for header in item['request']['header']:
                        if header.get('key') == 'Authorization' and 'Bearer' in str(header.get('value', '')):
                            count += 1
                            break
                if 'auth' in item['request'] and item['request']['auth'].get('type') == 'bearer':
                    count += 1
            if 'item' in item:
                for sub_item in item['item']:
                    count = count_bearer_tokens(sub_item, count)
            return count
        
        initial_count = 0
        for item in self.collection.get('item', []):
            initial_count = count_bearer_tokens(item, initial_count)
        
        # Update all items
        for item in self.collection.get('item', []):
            if self.update_auth_in_item(item):
                stats['folders_updated'] += 1
        
        # Count final Bearer tokens
        final_count = 0
        for item in self.collection.get('item', []):
            final_count = count_bearer_tokens(item, final_count)
        
        stats['endpoints_updated'] = initial_count - final_count
        
        return stats
    
    def get_company_write_endpoints(self) -> List[Dict[str, Any]]:
        """Get company write endpoints definitions.
        
        Returns:
            List of endpoint dictionaries
        """
        return [
            {
                "name": "Create Company",
                "request": {
                    "method": "POST",
                    "header": [
                        {
                            "key": "Content-Type",
                            "value": "application/json",
                            "disabled": False
                        },
                        {
                            "key": "X-API-Key",
                            "value": "{{apiKey}}",
                            "disabled": False,
                            "description": "Connectra API Key"
                        }
                    ],
                    "body": {
                        "mode": "raw",
                        "raw": json.dumps({
                            "name": "Acme Software Corp",
                            "normalized_domain": "acme.com",
                            "employees_count": 120,
                            "industries": ["Software", "Technology"],
                            "keywords": ["AI", "Machine Learning"],
                            "address": "123 Tech Street",
                            "annual_revenue": 5000000,
                            "total_funding": 10000000,
                            "technologies": ["Python", "Go", "React"],
                            "city": "New York",
                            "state": "NY",
                            "country": "USA",
                            "linkedin_url": "https://linkedin.com/company/acme",
                            "website": "https://acme.com"
                        }, indent=2),
                        "options": {
                            "raw": {
                                "language": "json"
                            }
                        }
                    },
                    "url": {
                        "raw": "{{baseUrl}}/companies/create",
                        "host": ["{{baseUrl}}"],
                        "path": ["companies", "create"]
                    },
                    "description": "Create a new company record with automatic Elasticsearch indexing.\n\n**Validation Rules**:\n- `name`: Required\n- `normalized_domain`: Optional, must be valid domain format\n- `employees_count`, `annual_revenue`, `total_funding`: Must be non-negative integers\n- `linkedin_url`, `website`: Must be valid URL format\n\n**Response**: 201 Created with company data"
                },
                "response": []
            },
            {
                "name": "Update Company",
                "request": {
                    "method": "PUT",
                    "header": [
                        {
                            "key": "Content-Type",
                            "value": "application/json",
                            "disabled": False
                        },
                        {
                            "key": "X-API-Key",
                            "value": "{{apiKey}}",
                            "disabled": False,
                            "description": "Connectra API Key"
                        }
                    ],
                    "body": {
                        "mode": "raw",
                        "raw": json.dumps({
                            "name": "Updated Company Name",
                            "employees_count": 150,
                            "industries": ["Software", "AI"]
                        }, indent=2),
                        "options": {
                            "raw": {
                                "language": "json"
                            }
                        }
                    },
                    "url": {
                        "raw": "{{baseUrl}}/companies/:uuid",
                        "host": ["{{baseUrl}}"],
                        "path": ["companies", ":uuid"],
                        "variable": [
                            {
                                "key": "uuid",
                                "value": "c0a8012e-1111-2222-3333-444455556666",
                                "description": "Company UUID"
                            }
                        ]
                    },
                    "description": "Update an existing company record by UUID with automatic Elasticsearch reindexing.\n\n**Request Body**: All fields optional, provide only fields to update\n\n**Response**: 200 OK with updated company data\n\n**Error**: 404 Not Found if company doesn't exist"
                },
                "response": []
            },
            {
                "name": "Delete Company",
                "request": {
                    "method": "DELETE",
                    "header": [
                        {
                            "key": "X-API-Key",
                            "value": "{{apiKey}}",
                            "disabled": False,
                            "description": "Connectra API Key"
                        }
                    ],
                    "url": {
                        "raw": "{{baseUrl}}/companies/:uuid",
                        "host": ["{{baseUrl}}"],
                        "path": ["companies", ":uuid"],
                        "variable": [
                            {
                                "key": "uuid",
                                "value": "c0a8012e-1111-2222-3333-444455556666",
                                "description": "Company UUID"
                            }
                        ]
                    },
                    "description": "Soft delete a company record by UUID (sets `deleted_at` timestamp).\n\n**Response**: 200 OK\n\n**Error**: 404 Not Found if company doesn't exist\n\n**Note**: Deleted companies are removed from Elasticsearch index but retained in PostgreSQL with `deleted_at` timestamp for audit purposes."
                },
                "response": []
            },
            {
                "name": "Upsert Company",
                "request": {
                    "method": "POST",
                    "header": [
                        {
                            "key": "Content-Type",
                            "value": "application/json",
                            "disabled": False
                        },
                        {
                            "key": "X-API-Key",
                            "value": "{{apiKey}}",
                            "disabled": False,
                            "description": "Connectra API Key"
                        }
                    ],
                    "body": {
                        "mode": "raw",
                        "raw": json.dumps({
                            "uuid": "c0a8012e-1111-2222-3333-444455556666",
                            "name": "Acme Software Corp",
                            "normalized_domain": "acme.com",
                            "employees_count": 120,
                            "industries": ["Software", "Technology"]
                        }, indent=2),
                        "options": {
                            "raw": {
                                "language": "json"
                            }
                        }
                    },
                    "url": {
                        "raw": "{{baseUrl}}/companies/upsert",
                        "host": ["{{baseUrl}}"],
                        "path": ["companies", "upsert"]
                    },
                    "description": "Create a new company or update an existing one (identified by UUID or normalized_domain).\n\n**Upsert Logic**:\n1. If company with matching UUID exists → update\n2. If company with matching normalized_domain exists → update\n3. Otherwise → create new company\n\n**Response**: 200 OK with company data"
                },
                "response": []
            },
            {
                "name": "Bulk Upsert Companies",
                "request": {
                    "method": "POST",
                    "header": [
                        {
                            "key": "Content-Type",
                            "value": "application/json",
                            "disabled": False
                        },
                        {
                            "key": "X-API-Key",
                            "value": "{{apiKey}}",
                            "disabled": False,
                            "description": "Connectra API Key"
                        }
                    ],
                    "body": {
                        "mode": "raw",
                        "raw": json.dumps({
                            "companies": [
                                {
                                    "uuid": "c0a8012e-1111-2222-3333-444455556666",
                                    "name": "Company 1",
                                    "employees_count": 100,
                                    "industries": ["Software"]
                                },
                                {
                                    "uuid": "c0a8012e-2222-3333-4444-555566667777",
                                    "name": "Company 2",
                                    "employees_count": 200,
                                    "industries": ["Technology"]
                                }
                            ]
                        }, indent=2),
                        "options": {
                            "raw": {
                                "language": "json"
                            }
                        }
                    },
                    "url": {
                        "raw": "{{baseUrl}}/companies/bulk",
                        "host": ["{{baseUrl}}"],
                        "path": ["companies", "bulk"]
                    },
                    "description": "Efficiently create or update multiple companies in a single request.\n\n**Validation**:\n- `companies`: Required array with minimum 1 item\n- Each company must have `name` field\n- UUIDs generated automatically if not provided\n\n**Response**: 200 OK with count of processed companies\n\n**Performance**:\n- Uses PostgreSQL `ON CONFLICT` for atomic upsert\n- Batch Elasticsearch indexing for efficiency\n- Can handle 1000+ records per request"
                },
                "response": []
            }
        ]
    
    def get_contact_write_endpoints(self) -> List[Dict[str, Any]]:
        """Get contact write endpoints definitions.
        
        Returns:
            List of endpoint dictionaries
        """
        return [
            {
                "name": "Create Contact",
                "request": {
                    "method": "POST",
                    "header": [
                        {
                            "key": "Content-Type",
                            "value": "application/json",
                            "disabled": False
                        },
                        {
                            "key": "X-API-Key",
                            "value": "{{apiKey}}",
                            "disabled": False,
                            "description": "Connectra API Key"
                        }
                    ],
                    "body": {
                        "mode": "raw",
                        "raw": json.dumps({
                            "first_name": "John",
                            "last_name": "Smith",
                            "email": "john.smith@example.com",
                            "company_id": "c0a8012e-1111-2222-3333-444455556666",
                            "title": "Senior Software Engineer",
                            "departments": ["Engineering"],
                            "mobile_phone": "4706037761",
                            "email_status": "verified",
                            "seniority": "Senior",
                            "city": "San Francisco",
                            "state": "CA",
                            "country": "USA",
                            "linkedin_url": "https://linkedin.com/in/john-smith",
                            "facebook_url": "https://facebook.com/johnsmith",
                            "twitter_url": "https://twitter.com/johnsmith",
                            "website": "https://johnsmith.dev"
                        }, indent=2),
                        "options": {
                            "raw": {
                                "language": "json"
                            }
                        }
                    },
                    "url": {
                        "raw": "{{baseUrl}}/contacts/create",
                        "host": ["{{baseUrl}}"],
                        "path": ["contacts", "create"]
                    },
                    "description": "Create a new contact record with automatic Elasticsearch indexing.\n\n**Validation Rules**:\n- `first_name`: Required\n- `last_name`: Required\n- `email`: Required, must be valid email format\n- `company_id`: Optional, must be valid UUID format\n- `linkedin_url`, `facebook_url`, `twitter_url`, `website`: Must be valid URL format\n- `uuid`: Optional (generated if not provided)\n\n**Response**: 201 Created with contact data"
                },
                "response": []
            },
            {
                "name": "Update Contact",
                "request": {
                    "method": "PUT",
                    "header": [
                        {
                            "key": "Content-Type",
                            "value": "application/json",
                            "disabled": False
                        },
                        {
                            "key": "X-API-Key",
                            "value": "{{apiKey}}",
                            "disabled": False,
                            "description": "Connectra API Key"
                        }
                    ],
                    "body": {
                        "mode": "raw",
                        "raw": json.dumps({
                            "title": "Staff Software Engineer",
                            "seniority": "Principal",
                            "departments": ["Engineering", "Architecture"],
                            "city": "New York",
                            "state": "NY"
                        }, indent=2),
                        "options": {
                            "raw": {
                                "language": "json"
                            }
                        }
                    },
                    "url": {
                        "raw": "{{baseUrl}}/contacts/:uuid",
                        "host": ["{{baseUrl}}"],
                        "path": ["contacts", ":uuid"],
                        "variable": [
                            {
                                "key": "uuid",
                                "value": "d1e2f3a4-5678-90ab-cdef-1234567890ab",
                                "description": "Contact UUID"
                            }
                        ]
                    },
                    "description": "Update an existing contact record by UUID with automatic Elasticsearch reindexing.\n\n**Request Body**: All fields optional, provide only fields to update\n\n**Response**: 200 OK with updated contact data\n\n**Error**: 404 Not Found if contact doesn't exist"
                },
                "response": []
            },
            {
                "name": "Delete Contact",
                "request": {
                    "method": "DELETE",
                    "header": [
                        {
                            "key": "X-API-Key",
                            "value": "{{apiKey}}",
                            "disabled": False,
                            "description": "Connectra API Key"
                        }
                    ],
                    "url": {
                        "raw": "{{baseUrl}}/contacts/:uuid",
                        "host": ["{{baseUrl}}"],
                        "path": ["contacts", ":uuid"],
                        "variable": [
                            {
                                "key": "uuid",
                                "value": "d1e2f3a4-5678-90ab-cdef-1234567890ab",
                                "description": "Contact UUID"
                            }
                        ]
                    },
                    "description": "Soft delete a contact record by UUID (sets `deleted_at` timestamp).\n\n**Response**: 200 OK\n\n**Error**: 404 Not Found if contact doesn't exist\n\n**Note**: Deleted contacts are removed from Elasticsearch index but retained in PostgreSQL with `deleted_at` timestamp for audit purposes."
                },
                "response": []
            },
            {
                "name": "Upsert Contact",
                "request": {
                    "method": "POST",
                    "header": [
                        {
                            "key": "Content-Type",
                            "value": "application/json",
                            "disabled": False
                        },
                        {
                            "key": "X-API-Key",
                            "value": "{{apiKey}}",
                            "disabled": False,
                            "description": "Connectra API Key"
                        }
                    ],
                    "body": {
                        "mode": "raw",
                        "raw": json.dumps({
                            "uuid": "d1e2f3a4-5678-90ab-cdef-1234567890ab",
                            "first_name": "John",
                            "last_name": "Smith",
                            "email": "john.smith@example.com",
                            "company_id": "c0a8012e-1111-2222-3333-444455556666",
                            "title": "Senior Software Engineer",
                            "departments": ["Engineering"],
                            "seniority": "Senior"
                        }, indent=2),
                        "options": {
                            "raw": {
                                "language": "json"
                            }
                        }
                    },
                    "url": {
                        "raw": "{{baseUrl}}/contacts/upsert",
                        "host": ["{{baseUrl}}"],
                        "path": ["contacts", "upsert"]
                    },
                    "description": "Create a new contact or update an existing one (identified by UUID or email).\n\n**Upsert Logic**:\n1. If contact with matching UUID exists → update\n2. If contact with matching email exists → update\n3. Otherwise → create new contact\n\n**Response**: 200 OK with contact data"
                },
                "response": []
            },
            {
                "name": "Bulk Upsert Contacts",
                "request": {
                    "method": "POST",
                    "header": [
                        {
                            "key": "Content-Type",
                            "value": "application/json",
                            "disabled": False
                        },
                        {
                            "key": "X-API-Key",
                            "value": "{{apiKey}}",
                            "disabled": False,
                            "description": "Connectra API Key"
                        }
                    ],
                    "body": {
                        "mode": "raw",
                        "raw": json.dumps({
                            "contacts": [
                                {
                                    "uuid": "d1e2f3a4-5678-90ab-cdef-1234567890ab",
                                    "first_name": "John",
                                    "last_name": "Smith",
                                    "email": "john.smith@example.com",
                                    "company_id": "c0a8012e-1111-2222-3333-444455556666",
                                    "title": "Senior Software Engineer",
                                    "departments": ["Engineering"],
                                    "seniority": "Senior"
                                },
                                {
                                    "uuid": "e2f3g4h5-6789-01bc-def0-234567890bcd",
                                    "first_name": "Jane",
                                    "last_name": "Doe",
                                    "email": "jane.doe@example.com",
                                    "company_id": "c0a8012e-2222-3333-4444-555566667777",
                                    "title": "Engineering Manager",
                                    "departments": ["Engineering"],
                                    "seniority": "Lead"
                                }
                            ]
                        }, indent=2),
                        "options": {
                            "raw": {
                                "language": "json"
                            }
                        }
                    },
                    "url": {
                        "raw": "{{baseUrl}}/contacts/bulk",
                        "host": ["{{baseUrl}}"],
                        "path": ["contacts", "bulk"]
                    },
                    "description": "Efficiently create or update multiple contacts in a single request.\n\n**Validation**:\n- `contacts`: Required array with minimum 1 item\n- Each contact must have `first_name`, `last_name`, and `email` fields\n- UUIDs generated automatically if not provided\n\n**Response**: 200 OK with count of processed contacts\n\n**Performance**:\n- Uses PostgreSQL `ON CONFLICT` for atomic upsert\n- Batch Elasticsearch indexing for efficiency\n- Can handle 1000+ records per request"
                },
                "response": []
            }
        ]
    
    def add_test_scripts(self, endpoint: Dict[str, Any]):
        """Add test scripts to endpoint.
        
        Args:
            endpoint: Endpoint dictionary
        """
        if 'event' not in endpoint:
            endpoint['event'] = []
        
        # Test script
        test_script = [
            "pm.test('Status code is successful', function () {",
            "    pm.expect(pm.response.code).to.be.oneOf([200, 201, 202, 204]);",
            "});",
            "",
            "pm.test('Response time is acceptable', function () {",
            "    pm.expect(pm.response.responseTime).to.be.below(10000);",
            "});",
            "",
            "pm.test('Response has correct structure', function () {",
            "    if (pm.response.code === 200 || pm.response.code === 201) {",
            "        const jsonData = pm.response.json();",
            "        pm.expect(jsonData).to.be.an('object');",
            "        if (jsonData.success !== undefined) {",
            "            pm.expect(jsonData.success).to.be.a('boolean');",
            "        }",
            "    }",
            "});",
            "",
            "// Save UUIDs from response if available",
            "if (pm.response.code === 200 || pm.response.code === 201) {",
            "    try {",
            "        const jsonData = pm.response.json();",
            "        const endpoint = pm.request.url.toString();",
            "        ",
            "        // Save contact UUID",
            "        if (jsonData.data && jsonData.data.uuid && (endpoint.includes('contact') || jsonData.data.first_name || jsonData.data.last_name)) {",
            "            pm.collectionVariables.set('contact_uuid', jsonData.data.uuid);",
            "        }",
            "        // Save company UUID",
            "        if (jsonData.data && jsonData.data.uuid && (endpoint.includes('company') || jsonData.data.name)) {",
            "            pm.collectionVariables.set('company_uuid', jsonData.data.uuid);",
            "        }",
            "    } catch (e) {",
            "        // Response might not be JSON or might not have UUID",
            "    }",
            "}"
        ]
        
        endpoint['event'].append({
            "listen": "test",
            "script": {
                "type": "text/javascript",
                "exec": test_script
            }
        })
        
        # Pre-request script
        pre_request_script = [
            "// Set request timestamp",
            "pm.environment.set('timestamp', new Date().toISOString());",
            "",
            "// Log request details",
            "console.log(`Request to: ${pm.request.url.toString()}`);",
            "",
            "// Check if API key exists",
            "const apiKey = pm.collectionVariables.get('apiKey');",
            "if (!apiKey || apiKey === '') {",
            "    console.warn('No API key set. Please set the apiKey collection variable.');",
            "}"
        ]
        
        endpoint['event'].insert(0, {
            "listen": "prerequest",
            "script": {
                "type": "text/javascript",
                "exec": pre_request_script
            }
        })
    
    def add_write_endpoints(self) -> Dict[str, int]:
        """Add write endpoints to Companies and Contacts folders.
        
        Returns:
            Dictionary with statistics about added endpoints
        """
        stats = {
            'company_endpoints_added': 0,
            'contact_endpoints_added': 0
        }
        
        # Find Companies and Contacts folders
        companies_index = None
        contacts_index = None
        
        for i, item in enumerate(self.collection.get('item', [])):
            if item.get('name') == 'Companies':
                companies_index = i
            elif item.get('name') == 'Contacts':
                contacts_index = i
        
        if companies_index is None:
            print("Warning: Could not find Companies folder")
        else:
            company_endpoints = self.get_company_write_endpoints()
            for endpoint in company_endpoints:
                self.add_test_scripts(endpoint)
            
            print(f"Adding {len(company_endpoints)} endpoints to Companies folder (index {companies_index})")
            print(f"Companies folder currently has {len(self.collection['item'][companies_index]['item'])} items")
            self.collection['item'][companies_index]['item'].extend(company_endpoints)
            print(f"Companies folder now has {len(self.collection['item'][companies_index]['item'])} items")
            stats['company_endpoints_added'] = len(company_endpoints)
        
        if contacts_index is None:
            print("Warning: Could not find Contacts folder")
        else:
            contact_endpoints = self.get_contact_write_endpoints()
            for endpoint in contact_endpoints:
                self.add_test_scripts(endpoint)
            
            print(f"Adding {len(contact_endpoints)} endpoints to Contacts folder (index {contacts_index})")
            print(f"Contacts folder currently has {len(self.collection['item'][contacts_index]['item'])} items")
            self.collection['item'][contacts_index]['item'].extend(contact_endpoints)
            print(f"Contacts folder now has {len(self.collection['item'][contacts_index]['item'])} items")
            stats['contact_endpoints_added'] = len(contact_endpoints)
        
        return stats
    
    def generate(self, update_auth: bool = True, add_write_endpoints: bool = True) -> bool:
        """Generate and update the Connectra collection.
        
        Args:
            update_auth: Whether to update authentication to X-API-Key
            add_write_endpoints: Whether to add write endpoints
        
        Returns:
            True if successful, False otherwise
        """
        if not self.load_collection():
            return False
        
        # Add API key variable
        self.add_api_key_variable()
        
        # Update authentication
        if update_auth:
            print("\nUpdating authentication to X-API-Key...")
            auth_stats = self.update_authentication()
            print(f"Updated {auth_stats['folders_updated']} top-level folders")
            print(f"Updated {auth_stats['endpoints_updated']} endpoints from Bearer token to X-API-Key")
        
        # Add write endpoints
        if add_write_endpoints:
            print("\nAdding write endpoints...")
            write_stats = self.add_write_endpoints()
            print(f"Added {write_stats['company_endpoints_added']} company write endpoints")
            print(f"Added {write_stats['contact_endpoints_added']} contact write endpoints")
            print(f"Total: {write_stats['company_endpoints_added'] + write_stats['contact_endpoints_added']} new endpoints")
        
        # Save collection
        if self.save_collection():
            print(f"\nSuccessfully updated Connectra collection: {self.collection_path}")
            return True
        else:
            return False


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate and update Connectra API Postman Collection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update authentication and add write endpoints (default)
  python generate_connectra_collection.py
  
  # Only update authentication
  python generate_connectra_collection.py --no-write-endpoints
  
  # Only add write endpoints
  python generate_connectra_collection.py --no-update-auth
  
  # Custom collection path
  python generate_connectra_collection.py --collection-path ./custom/collection.json
        """
    )
    
    parser.add_argument(
        "--collection-path",
        type=str,
        default=None,
        help="Path to Connectra collection JSON file (default: json/Connectra API.postman_collection.json)"
    )
    parser.add_argument(
        "--no-update-auth",
        action="store_true",
        help="Skip updating authentication to X-API-Key"
    )
    parser.add_argument(
        "--no-write-endpoints",
        action="store_true",
        help="Skip adding write endpoints"
    )
    
    args = parser.parse_args()
    
    collection_path = Path(args.collection_path) if args.collection_path else None
    generator = ConnectraCollectionGenerator(collection_path)
    
    success = generator.generate(
        update_auth=not args.no_update_auth,
        add_write_endpoints=not args.no_write_endpoints
    )
    
    if success:
        print("\n✓ Connectra collection generation completed successfully!")
        return 0
    else:
        print("\n✗ Connectra collection generation failed!")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

