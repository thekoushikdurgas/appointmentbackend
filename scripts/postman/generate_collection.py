"""Generate Postman Collection v2.1.0 JSON from CSV endpoint data with complete parameters."""

import csv
import json
import sys
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add backend to path for imports
# Script is at: backend/scripts/postman/generate_collection.py
# Need to add: backend/ (parent.parent.parent) so we can import from app
backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Try to import filter classes for dynamic parameter extraction
try:
    from app.schemas.filters import (
        AIChatFilterParams,
        AuthFilterParams,
        CompanyContactFilterParams,
        CompanyFilterParams,
        ContactFilterParams,
        ExportFilterParams,
        RootFilterParams,
        UserFilterParams,
        AttributeListParams,
    )
    FILTERS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import filter classes: {e}")
    print("Will use fallback parameter generation")
    FILTERS_AVAILABLE = False

# Try to import request schemas
try:
    from app.schemas.user import (
        UserRegister, UserLogin, RefreshTokenRequest, LogoutRequest, ProfileUpdate,
        UpdateUserRoleRequest, UpdateUserCreditsRequest
    )
    from app.schemas.contacts import ContactCreate
    from app.schemas.companies import CompanyCreate
    from app.schemas.ai_chat import AIChatMessageRequest
    from app.schemas.email import (
        EmailVerifierRequest,
        BulkEmailVerifierRequest,
        SingleEmailVerifierRequest,
        EmailExportRequest,
        SingleEmailRequest,
    )
    from app.schemas.linkedin import LinkedInSearchRequest
    from app.schemas.usage import TrackUsageRequest
    from app.schemas.billing import SubscribeRequest, AddonPurchaseRequest
    # Gemini schemas are defined in the endpoint file, not in schemas
    from app.schemas.sales_navigator import SalesNavigatorScrapeRequest
    from app.schemas.exports import ContactExportRequest, CompanyExportRequest, ChunkedExportRequest
    from app.schemas.marketing import MarketingPageCreate, MarketingPageUpdate
    # Try to import VQL structures
    try:
        from app.core.vql.structures import VQLQuery
        VQL_AVAILABLE = True
    except ImportError:
        VQL_AVAILABLE = False
    SCHEMAS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import request schemas: {e}")
    print("Will use fallback request body generation")
    SCHEMAS_AVAILABLE = False
    VQL_AVAILABLE = False

# Read CSV data (lazy loading - only when needed)
# Try to find CSV file in current directory or csv/ subdirectory
csv_paths = [
    Path(__file__).parent / "api endpoints documentation(in) (1).csv",
    Path(__file__).parent / "csv" / "api endpoints documentation(in) (1).csv",
]

endpoints = []
csv_path = None
for path in csv_paths:
    if path.exists():
        csv_path = path
        break

if csv_path:
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:  # utf-8-sig handles BOM
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('endpoint'):  # Skip empty rows
                    endpoints.append(row)
        print(f"Loaded {len(endpoints)} endpoints from {csv_path.name}")
    except Exception as e:
        print(f"Warning: Could not load CSV file: {e}")
        endpoints = []
else:
    # CSV file not found - this is OK if the module is just being imported
    # Only print warning if this is the main script (not an import)
    if __name__ == "__main__":
        print(f"Warning: CSV file not found. Tried: {[str(p) for p in csv_paths]}")
        endpoints = []

# Helper functions
def replace_path_params(endpoint):
    """Replace path parameters with Postman variables."""
    replacements = {
        '{contact_uuid}': '{{contact_uuid}}',
        '{company_uuid}': '{{company_uuid}}',
        '{chat_id}': '{{chat_id}}',
        '{job_id}': '{{job_id}}',
        '{user_id}': '{{user_id}}',
        '{uuid}': '{{contact_uuid}}',
        '{tier}': '{{tier}}',
        '{period}': '{{period}}',
        '{package_id}': '{{package_id}}',
        '{pattern_uuid}': '{{pattern_uuid}}',
        '{export_id}': '{{export_id}}',
        '{file_id:path}': '{{file_id}}',
        '{file_type}': '{{file_type}}',
        '{slug}': '{{slug}}',
    }
    result = endpoint
    for old, new in replacements.items():
        result = result.replace(old, new)
    return result

def extract_filter_params_from_model(filter_class) -> List[Dict[str, Any]]:
    """Extract all parameters from a Pydantic filter model."""
    if not FILTERS_AVAILABLE:
        return []
    
    params = []
    try:
        model_fields = filter_class.model_fields
        for field_name, field_info in model_fields.items():
            # Get field type
            field_type = field_info.annotation
            type_str = str(field_type)
            
            # Determine default value
            default = field_info.default
            if default is None or (isinstance(default, type) and default == type(None)):
                default_value = ""
            elif isinstance(default, bool):
                default_value = str(default).lower()
            elif isinstance(default, (int, float)):
                default_value = str(default)
            elif isinstance(default, list):
                default_value = ""
            else:
                default_value = str(default) if default is not None else ""
            
            # Get description
            description = field_info.description or f"Filter by {field_name}"
            
            # Handle validation aliases
            param_key = field_name
            if hasattr(field_info, 'validation_alias'):
                alias = field_info.validation_alias
                if isinstance(alias, list) and len(alias) > 0:
                    # Use the first alias if available, but keep original name as primary
                    pass
            
            # Build parameter dict
            param = {
                "key": param_key,
                "value": default_value,
                "description": description,
                "disabled": default is None or default == ""
            }
            
            # Add type hints in description
            if "Optional" in type_str or "None" in type_str:
                param["description"] += " (optional)"
            if "list" in type_str.lower() or "List" in type_str:
                param["description"] += " - Can be comma-separated or JSON array"
            if "int" in type_str.lower():
                param["description"] += " - Integer value"
            if "bool" in type_str.lower() or "Bool" in type_str:
                param["description"] += " - Boolean (true/false)"
            if "datetime" in type_str.lower():
                param["description"] += " - ISO timestamp format"
            
            params.append(param)
    except Exception as e:
        print(f"Error extracting params from {filter_class.__name__}: {e}")
    
    return params

def get_filter_class_for_endpoint(endpoint: str, method: str) -> Optional[Any]:
    """Determine which filter class to use based on endpoint path."""
    if not FILTERS_AVAILABLE:
        return None
    
    # VQL POST endpoints don't use filter classes (they use VQLQuery in request body)
    if method == 'POST' and ('/query' in endpoint or '/count' in endpoint) and ('/contacts/' in endpoint or '/companies/' in endpoint):
        return None
    
    # Contacts endpoints
    if '/contacts/' in endpoint and method == 'GET':
        if '/company/' in endpoint and '/contacts/' in endpoint:
            return CompanyContactFilterParams
        else:
            return ContactFilterParams
    
    # Companies endpoints
    if '/companies/' in endpoint and method == 'GET':
        return CompanyFilterParams
    
    # AI Chat endpoints
    if '/ai-chats/' in endpoint:
        return AIChatFilterParams
    
    # Auth endpoints
    if '/auth/' in endpoint:
        return AuthFilterParams
    
    # User endpoints
    if '/users/' in endpoint:
        return UserFilterParams
    
    # Export endpoints
    if '/export' in endpoint or '/exports/' in endpoint:
        return ExportFilterParams
    
    # Root/health endpoints
    if endpoint in ['/health', '/health/db', '/api/v1/', '/api/v1/health/']:
        return RootFilterParams
    
    return None

def get_query_params(endpoint, method):
    """Get query parameters based on endpoint type with complete filter parameters."""
    params = []
    
    # VQL POST endpoints use request body, not query parameters
    if method == 'POST' and ('/query' in endpoint or '/count' in endpoint) and ('/contacts/' in endpoint or '/companies/' in endpoint):
        return params  # VQL endpoints don't use query params
    
    # Get filter class for this endpoint
    filter_class = get_filter_class_for_endpoint(endpoint, method)
    if filter_class:
        filter_params = extract_filter_params_from_model(filter_class)
        params.extend(filter_params)
    
    # Add common pagination params (if not already in filter params)
    existing_keys = {p["key"] for p in params}
    
    # List endpoints (GET endpoints ending with /)
    if method == 'GET' and endpoint.endswith('/') and 'count' not in endpoint and 'stream' not in endpoint and 'uuids' not in endpoint:
        # Skip single resource endpoints (with UUIDs in path)
        if '{' not in endpoint or endpoint.count('{') == 1 and endpoint.endswith('{uuid}/'):
            if 'limit' not in existing_keys:
                params.append({"key": "limit", "value": "10", "description": "Number of items per page"})
            if 'offset' not in existing_keys:
                params.append({"key": "offset", "value": "0", "description": "Offset for pagination"})
    
    # S3 files endpoint (with file_id)
    if '/s3/files/' in endpoint and '{file_id' in endpoint:
        if 'limit' not in existing_keys:
            params.append({"key": "limit", "value": "", "description": "Maximum number of rows to return (min: 1, max: 1000). If not provided, returns full CSV file for download. If provided, returns paginated JSON data.", "disabled": True})
        if 'offset' not in existing_keys:
            params.append({"key": "offset", "value": "", "description": "Number of rows to skip (min: 0). Only used in pagination mode (when limit is provided).", "disabled": True})
    
    # Activities endpoint
    if '/activities/' in endpoint and method == 'GET':
        if 'service_type' not in existing_keys:
            params.append({"key": "service_type", "value": "", "description": "Filter by service type: linkedin or email", "disabled": True})
        if 'action_type' not in existing_keys:
            params.append({"key": "action_type", "value": "", "description": "Filter by action type: search or export", "disabled": True})
        if 'status' not in existing_keys:
            params.append({"key": "status", "value": "", "description": "Filter by status: success, failed, or partial", "disabled": True})
        if 'start_date' not in existing_keys:
            params.append({"key": "start_date", "value": "", "description": "Filter by start date (ISO format)", "disabled": True})
        if 'end_date' not in existing_keys:
            params.append({"key": "end_date", "value": "", "description": "Filter by end date (ISO format)", "disabled": True})
    
    # S3 files list endpoint
    if '/s3/files' in endpoint and method == 'GET' and '{file_id' not in endpoint and endpoint.endswith('/s3/files'):
        if 'prefix' not in existing_keys:
            params.append({"key": "prefix", "value": "", "description": "Optional prefix to filter files by path (e.g., 'data/' to list files in data directory)", "disabled": True})
    
    # Marketing endpoints with query parameters
    if endpoint == '/api/v4/marketing/' and method == 'GET':
        if 'include_drafts' not in existing_keys:
            params.append({"key": "include_drafts", "value": "", "description": "Include draft pages (public endpoint ignores this parameter and always excludes drafts)", "disabled": True})
    
    if endpoint == '/api/v4/admin/marketing/' and method == 'GET':
        if 'include_drafts' not in existing_keys:
            params.append({"key": "include_drafts", "value": "true", "description": "Include draft pages (default: true)", "disabled": False})
        if 'include_deleted' not in existing_keys:
            params.append({"key": "include_deleted", "value": "false", "description": "Include deleted pages (default: false)", "disabled": False})
    
    if '/api/v4/admin/marketing/' in endpoint and '{page_id' in endpoint and method == 'DELETE':
        if 'hard_delete' not in existing_keys:
            params.append({"key": "hard_delete", "value": "false", "description": "Permanently delete instead of soft delete (default: false)", "disabled": False})
    
    # User endpoints with query parameters
    if endpoint == '/api/v1/users/' and method == 'GET':
        if 'limit' not in existing_keys:
            params.append({"key": "limit", "value": "100", "description": "Maximum number of users to return (min: 1, max: 1000)", "disabled": False})
        if 'offset' not in existing_keys:
            params.append({"key": "offset", "value": "0", "description": "Number of users to skip (for pagination, min: 0)", "disabled": False})
    
    if endpoint == '/api/v1/users/history/' and method == 'GET':
        if 'user_id' not in existing_keys:
            params.append({"key": "user_id", "value": "", "description": "Filter by user ID (UUID format, optional)", "disabled": True})
        if 'event_type' not in existing_keys:
            params.append({"key": "event_type", "value": "", "description": "Filter by event type: registration or login (optional)", "disabled": True})
        if 'limit' not in existing_keys:
            params.append({"key": "limit", "value": "100", "description": "Maximum number of records to return (min: 1, max: 1000)", "disabled": False})
        if 'offset' not in existing_keys:
            params.append({"key": "offset", "value": "0", "description": "Number of records to skip (for pagination, min: 0)", "disabled": False})
    
    if endpoint == '/api/v1/users/sales-navigator/list' and method == 'GET':
        if 'limit' not in existing_keys:
            params.append({"key": "limit", "value": "100", "description": "Maximum number of records to return (min: 1, max: 1000)", "disabled": False})
        if 'offset' not in existing_keys:
            params.append({"key": "offset", "value": "0", "description": "Number of records to skip (for pagination, min: 0)", "disabled": False})
    
    if endpoint == '/api/v1/users/promote-to-super-admin/' and method == 'POST':
        if 'user_id' not in existing_keys:
            params.append({"key": "user_id", "value": "{{user_id}}", "description": "User ID to promote to super admin (UUID format, required)", "disabled": False})
    
    # Email finder endpoint (GET with query params)
    if endpoint == '/api/v3/email/finder/' and method == 'GET':
        if 'first_name' not in existing_keys:
            params.append({"key": "first_name", "value": "John", "description": "Contact first name (required, case-insensitive partial match)", "disabled": False})
        if 'last_name' not in existing_keys:
            params.append({"key": "last_name", "value": "Doe", "description": "Contact last name (required, case-insensitive partial match)", "disabled": False})
        if 'domain' not in existing_keys:
            params.append({"key": "domain", "value": "example.com", "description": "Company domain or website URL (optional, can use website parameter instead)", "disabled": True})
        if 'website' not in existing_keys:
            params.append({"key": "website", "value": "", "description": "Company website URL (optional, alias for domain parameter)", "disabled": True})
    
    # Email bulk download endpoint (GET with path and query params)
    if '/email/bulk/download' in endpoint and method == 'GET':
        if 'provider' not in existing_keys:
            params.append({"key": "provider", "value": "truelist", "description": "Email verification provider: truelist or truelist (required)", "disabled": False})
    
    return params

def get_headers(endpoint: str, method: str, api_version: str) -> List[Dict[str, Any]]:
    """Get headers for endpoint based on method and API version."""
    headers = []
    
    # Content-Type header
    if method in ['POST', 'PUT', 'PATCH']:
        # Check if it's a file upload endpoint
        if '/import/' in endpoint or '/avatar/' in endpoint or '/import' in endpoint:
            headers.append({
                "key": "Content-Type",
                "value": "multipart/form-data",
                "disabled": False
            })
        else:
            headers.append({
                "key": "Content-Type",
                "value": "application/json",
                "disabled": False
            })
    else:
        headers.append({
            "key": "Content-Type",
            "value": "application/json",
            "disabled": True
        })
    
    # Accept header for GET requests
    if method == 'GET':
        headers.append({
            "key": "Accept",
            "value": "application/json",
            "disabled": False
        })
    
    # Authorization headers are handled by get_auth_config()
    # Note: VQL POST endpoints use Bearer token, not X-Write-Key
    # Only non-VQL v1 write operations would use X-Write-Key, but those are removed (moved to Connectra)
    # So we don't add X-Write-Key header here anymore
    
    return headers

def get_auth_config(endpoint, api_version, requires_auth, requires_admin):
    """Get authentication configuration for endpoint."""
    # Global endpoints don't need auth
    if api_version == 'global':
        return None
    
    # Auth endpoints themselves don't need auth (login, register, refresh)
    if '/auth/login' in endpoint or '/auth/register' in endpoint or '/auth/refresh' in endpoint:
        return None
    
    # v1 endpoints - VQL POST endpoints use Bearer token, not X-Write-Key
    if api_version == 'v1':
        # VQL query endpoints (POST /query, POST /count) use Bearer token
        if ('/query' in endpoint or '/count' in endpoint) and ('/contacts/' in endpoint or '/companies/' in endpoint):
            return {
                "type": "bearer",
                "bearer": [
                    {"key": "token", "value": "{{access_token}}", "type": "string"}
                ]
            }
        # Other v1 endpoints that require auth also use Bearer token now
        if requires_auth:
            return {
                "type": "bearer",
                "bearer": [
                    {"key": "token", "value": "{{access_token}}", "type": "string"}
                ]
            }
        return None
    
    # v2, v3, v4 endpoints ALWAYS use Bearer token (except public auth endpoints)
    if api_version in ['v2', 'v3', 'v4']:
        # Only login, register, and refresh are public
        if '/auth/login' in endpoint or '/auth/register' in endpoint or '/auth/refresh' in endpoint:
            return None
        # All other v2/v3/v4 endpoints need Bearer token
        return {
            "type": "bearer",
            "bearer": [
                {"key": "token", "value": "{{access_token}}", "type": "string"}
            ]
        }
    
    return None

def _clean_for_json(obj: Any) -> Any:
    """Clean object to ensure it's JSON serializable."""
    try:
        from pydantic_core import PydanticUndefined
    except ImportError:
        try:
            from pydantic import PydanticUndefined
        except (ImportError, AttributeError):
            PydanticUndefined = None
    
    if PydanticUndefined is not None and obj is PydanticUndefined:
        return None
    elif isinstance(obj, dict):
        return {k: _clean_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_clean_for_json(item) for item in obj]
    elif isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    else:
        # Try to convert to string for non-serializable types
        try:
            json.dumps(obj)
            return obj
        except (TypeError, ValueError):
            return str(obj)

def extract_schema_fields(schema_class) -> Dict[str, Any]:
    """Extract fields from a Pydantic schema class to build request body."""
    if not SCHEMAS_AVAILABLE:
        return {}
    
    try:
        example_data = {}
        model_fields = schema_class.model_fields
        
        for field_name, field_info in model_fields.items():
            field_type = field_info.annotation
            default = field_info.default
            
            # Generate example value based on type
            # Check for PydanticUndefined
            try:
                from pydantic_core import PydanticUndefined
                is_undefined = default is PydanticUndefined
            except ImportError:
                try:
                    from pydantic import PydanticUndefined
                    is_undefined = default is PydanticUndefined
                except (ImportError, AttributeError):
                    is_undefined = False
            
            if default is not None and not is_undefined and not (isinstance(default, type) and default == type(None)):
                example_data[field_name] = default
            else:
                type_str = str(field_type)
                if "str" in type_str.lower() or "String" in type_str:
                    if "email" in field_name.lower():
                        example_data[field_name] = "user@example.com"
                    elif "password" in field_name.lower():
                        example_data[field_name] = "securepassword123"
                    elif "url" in field_name.lower() or "link" in field_name.lower():
                        example_data[field_name] = "https://example.com"
                    elif "uuid" in field_name.lower() or "id" in field_name.lower():
                        example_data[field_name] = "{{" + field_name.replace("_uuid", "_uuid").replace("_id", "_id") + "}}"
                    else:
                        example_data[field_name] = f"Example {field_name.replace('_', ' ').title()}"
                elif "int" in type_str.lower():
                    example_data[field_name] = 0
                elif "float" in type_str.lower():
                    example_data[field_name] = 0.0
                elif "bool" in type_str.lower() or "Bool" in type_str:
                    example_data[field_name] = False
                elif "list" in type_str.lower() or "List" in type_str:
                    example_data[field_name] = []
                elif "dict" in type_str.lower() or "Dict" in type_str:
                    example_data[field_name] = {}
                else:
                    example_data[field_name] = None
        
        return example_data
    except Exception as e:
        print(f"Error extracting schema fields from {schema_class.__name__}: {e}")
        return {}

def get_request_body(endpoint, method, api_version, category, description=""):
    """Get example request body for POST/PUT/PATCH endpoints."""
    if method not in ['POST', 'PUT', 'PATCH']:
        return None
    
    # VQL query endpoints - generate VQL structure
    if method == 'POST' and ('/query' in endpoint or '/count' in endpoint) and ('/contacts/' in endpoint or '/companies/' in endpoint):
        # Generate example VQL query structure
        vql_body = {
            "filters": {
                "and": [
                    {
                        "field": "name" if "/companies/" in endpoint else "first_name",
                        "operator": "eq",
                        "value": "Example" if "/companies/" in endpoint else "John"
                    }
                ]
            },
            "select_columns": ["uuid", "name"] if "/companies/" in endpoint else ["uuid", "first_name", "last_name"],
            "limit": 10,
            "offset": 0,
            "sort_by": "name" if "/companies/" in endpoint else "first_name",
            "sort_direction": "asc"
        }
        
        # Add populate config for contacts query (to populate company)
        if "/contacts/" in endpoint:
            vql_body["company_config"] = {
                "populate": True,
                "select_columns": ["uuid", "name"]
            }
        
        return {
            "mode": "raw",
            "raw": json.dumps(vql_body, indent=2),
            "options": {"raw": {"language": "json"}}
        }
    
    # Try to use schema-based generation first
    if SCHEMAS_AVAILABLE:
        schema_map = {
            '/api/v1/auth/register/': UserRegister,
            '/api/v1/auth/login/': UserLogin,
            '/api/v1/auth/refresh/': RefreshTokenRequest,
            '/api/v1/auth/logout/': LogoutRequest,
            # Note: VQL endpoints handled above, not using ContactCreate/CompanyCreate
            '/api/v2/ai-chats/': None,  # Will use template
            '/api/v3/email/verifier/': EmailVerifierRequest,
            '/api/v3/email/bulk/verifier/': BulkEmailVerifierRequest,
            '/api/v3/email/single/verifier/': SingleEmailVerifierRequest,
            '/api/v3/email/export': EmailExportRequest,
            '/api/v3/email/single/': SingleEmailRequest,
            '/api/v3/linkedin/': LinkedInSearchRequest,
            '/api/v1/usage/track/': TrackUsageRequest,
            '/api/v1/users/profile/': ProfileUpdate,
            '/api/v1/users/{user_id}/role/': UpdateUserRoleRequest,
            '/api/v1/users/{user_id}/credits/': UpdateUserCreditsRequest,
            '/api/v1/billing/subscribe/': SubscribeRequest,
            '/api/v1/billing/addon/': AddonPurchaseRequest,
            '/api/v3/sales-navigator/scrape': SalesNavigatorScrapeRequest,
            '/api/v3/exports/contacts/export': ContactExportRequest,
            '/api/v3/exports/companies/export': CompanyExportRequest,
            '/api/v3/exports/contacts/export/chunked': ChunkedExportRequest,
            '/api/v4/admin/marketing/': MarketingPageCreate,
        }
        
        # Check for exact match
        if endpoint in schema_map:
            schema_class = schema_map[endpoint]
            if schema_class:
                example_data = extract_schema_fields(schema_class)
                if example_data:
                    # Clean data before JSON serialization
                    cleaned_data = _clean_for_json(example_data)
                    return {
                        "mode": "raw",
                        "raw": json.dumps(cleaned_data, indent=2),
                        "options": {"raw": {"language": "json"}}
                    }
        
        # Check for pattern matches
        for pattern, schema_class in schema_map.items():
            if endpoint.startswith(pattern) and schema_class:
                example_data = extract_schema_fields(schema_class)
                if example_data:
                    # Clean data before JSON serialization
                    cleaned_data = _clean_for_json(example_data)
                    return {
                        "mode": "raw",
                        "raw": json.dumps(cleaned_data, indent=2),
                        "options": {"raw": {"language": "json"}}
                    }
    
    # Fallback to hardcoded templates
    body_templates = {
        # Auth
        '/api/v1/auth/register': {
            "mode": "raw",
            "raw": json.dumps({
                "name": "{{$randomFullName}}",
                "email": "{{$randomEmail}}",
                "password": "securepassword123",
                "geolocation": {
                    "ip": "{{$randomIP}}",
                    "continent": "North America",
                    "continent_code": "NA",
                    "country": "United States",
                    "country_code": "US",
                    "region": "CA",
                    "region_name": "California",
                    "city": "{{$randomCity}}",
                    "district": "",
                    "zip": "{{$randomZipCode}}",
                    "lat": 37.7749,
                    "lon": -122.4194,
                    "timezone": "America/Los_Angeles",
                    "offset": -28800,
                    "currency": "USD",
                    "isp": "Example ISP",
                    "org": "Example Org",
                    "asname": "",
                    "reverse": "",
                    "device": "{{$randomUserAgent}}",
                    "proxy": False,
                    "hosting": False
                }
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        '/api/v1/auth/register/': {
            "mode": "raw",
            "raw": json.dumps({
                "name": "{{$randomFullName}}",
                "email": "{{$randomEmail}}",
                "password": "securepassword123",
                "geolocation": {
                    "ip": "{{$randomIP}}",
                    "continent": "North America",
                    "continent_code": "NA",
                    "country": "United States",
                    "country_code": "US",
                    "region": "CA",
                    "region_name": "California",
                    "city": "{{$randomCity}}",
                    "district": "",
                    "zip": "{{$randomZipCode}}",
                    "lat": 37.7749,
                    "lon": -122.4194,
                    "timezone": "America/Los_Angeles",
                    "offset": -28800,
                    "currency": "USD",
                    "isp": "Example ISP",
                    "org": "Example Org",
                    "asname": "",
                    "reverse": "",
                    "device": "{{$randomUserAgent}}",
                    "proxy": False,
                    "hosting": False
                }
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        '/api/v1/auth/login/': {
            "mode": "raw",
            "raw": json.dumps({
                "email": "{{user_email}}",
                "password": "{{user_password}}",
                "geolocation": {
                    "ip": "{{$randomIP}}",
                    "continent": "North America",
                    "continent_code": "NA",
                    "country": "United States",
                    "country_code": "US",
                    "region": "CA",
                    "region_name": "California",
                    "city": "{{$randomCity}}",
                    "district": "",
                    "zip": "{{$randomZipCode}}",
                    "lat": 37.7749,
                    "lon": -122.4194,
                    "timezone": "America/Los_Angeles",
                    "offset": -28800,
                    "currency": "USD",
                    "isp": "Example ISP",
                    "org": "Example Org",
                    "asname": "",
                    "reverse": "",
                    "device": "{{$randomUserAgent}}",
                    "proxy": False,
                    "hosting": False
                }
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        '/api/v1/auth/refresh/': {
            "mode": "raw",
            "raw": json.dumps({
                "refresh_token": "{{refresh_token}}"
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        '/api/v1/auth/logout/': {
            "mode": "raw",
            "raw": json.dumps({
                "refresh_token": "{{refresh_token}}"
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        # User Profile
        '/api/v1/users/profile/': {
            "mode": "raw",
            "raw": json.dumps({
                "name": "{{$randomFullName}}",
                "job_title": "{{$randomJobTitle}}",
                "bio": "{{$randomLoremParagraph}}",
                "timezone": "America/New_York",
                "avatar_url": "https://picsum.photos/seed/123/40/40",
                "notifications": {
                    "weeklyReports": True,
                    "newLeadAlerts": True
                }
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        # Super Admin
        '/api/v1/users/{user_id}/role/': {
            "mode": "raw",
            "raw": json.dumps({
                "role": "ProUser"
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        '/api/v1/users/{user_id}/credits/': {
            "mode": "raw",
            "raw": json.dumps({
                "credits": 1000
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        # Usage
        '/api/v1/usage/track/': {
            "mode": "raw",
            "raw": json.dumps({
                "feature": "EMAIL_FINDER",
                "amount": 1
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        '/api/v2/usage/reset': {
            "mode": "raw",
            "raw": json.dumps({
                "feature": "EMAIL_FINDER"
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        # Note: VQL endpoints (/api/v3/contacts/query, /api/v3/companies/query) handled above
        # Bulk
        '/api/v1/bulk/insert/': {
            "mode": "raw",
            "raw": json.dumps({
                "contacts": [
                    {
                        "first_name": "John",
                        "last_name": "Doe",
                        "email": "john@example.com"
                    }
                ],
                "companies": [
                    {
                        "name": "Example Corp",
                        "employees_count": 50
                    }
                ]
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        # AI Chats
        '/api/v2/ai-chats/': {
            "mode": "raw",
            "raw": json.dumps({
                "title": "New Conversation",
                "model": "gemini-pro"
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        '/api/v2/ai-chats/{chat_id}/': {
            "mode": "raw",
            "raw": json.dumps({
                "title": "Updated Conversation Title"
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        '/api/v2/ai-chats/{chat_id}/message': {
            "mode": "raw",
            "raw": json.dumps({
                "message": "Hello, how can you help me?"
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        '/api/v2/ai-chats/{chat_id}/message/stream': {
            "mode": "raw",
            "raw": json.dumps({
                "message": "Hello, how can you help me?"
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        # Apollo
        '/api/v2/apollo/analyze': {
            "mode": "raw",
            "raw": json.dumps({
                "url": "https://app.apollo.io/#/people?finderViewId=..."
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        '/api/v2/apollo/contacts': {
            "mode": "raw",
            "raw": json.dumps({
                "url": "https://app.apollo.io/#/people?finderViewId=...",
                "limit": 100,
                "offset": 0
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        # Email
        # Note: /api/v3/email/finder/ is GET with query params, not POST with body
        '/api/v3/email/export': {
            "mode": "raw",
            "raw": json.dumps({
                "contacts": [
                    {
                        "first_name": "John",
                        "last_name": "Doe",
                        "domain": "example.com",
                        "email": "john.doe@example.com"
                    }
                ],
                "mapping": {
                    "first_name": "first_name",
                    "last_name": "last_name",
                    "domain": "domain",
                    "website": None,
                    "email": "email"
                }
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        '/api/v3/email/single/': {
            "mode": "raw",
            "raw": json.dumps({
                "first_name": "John",
                "last_name": "Doe",
                "domain": "example.com",
                "provider": "truelist"
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        '/api/v3/email/bulk/verifier/': {
            "mode": "raw",
            "raw": json.dumps({
                "provider": "truelist",
                "emails": [
                    "john.doe@example.com",
                    "jane.smith@example.com"
                ]
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        '/api/v3/email/single/verifier/': {
            "mode": "raw",
            "raw": json.dumps({
                "email": "john.doe@example.com",
                "provider": "truelist"
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        '/api/v3/email/verifier/': {
            "mode": "raw",
            "raw": json.dumps({
                "first_name": "John",
                "last_name": "Doe",
                "domain": "example.com",
                "provider": "truelist",
                "email_count": 1000,
                "max_retries": 10
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        '/api/v3/email/verifier/single/': {
            "mode": "raw",
            "raw": json.dumps({
                "first_name": "John",
                "last_name": "Doe",
                "domain": "example.com",
                "provider": "truelist",
                "email_count": 1000,
                "max_retries": 10
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        '/api/v3/email/verifier/single/': {
            "mode": "raw",
            "raw": json.dumps({
                "first_name": "John",
                "last_name": "Doe",
                "domain": "example.com"
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        # Email Patterns
        '/api/v2/email-patterns/': {
            "mode": "raw",
            "raw": json.dumps({
                "company_uuid": "{{company_uuid}}",
                "pattern": "first.last@company.com",
                "confidence": 0.95
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        # LinkedIn endpoints - differentiate by description
        '/api/v3/linkedin/export': {
            "mode": "raw",
            "raw": json.dumps({
                "urls": ["https://www.linkedin.com/in/johndoe/"],
                "mapping": None,
                "raw_headers": None,
                "rows": None,
                "linkedin_url_column": None,
                "contact_field_mappings": None,
                "company_field_mappings": None
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        # Usage
        '/api/v1/usage/track/': {
            "mode": "raw",
            "raw": json.dumps({
                "feature": "email_finder",
                "count": 1
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        # Users
        '/api/v1/users/profile/': {
            "mode": "raw",
            "raw": json.dumps({
                "name": "Updated Name",
                "notification_preferences": {
                    "email_enabled": True
                }
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        '/api/v1/users/profile/avatar/': {
            "mode": "formdata",
            "formdata": [
                {
                    "key": "file",
                    "type": "file",
                    "src": [],
                    "description": "Avatar image file"
                }
            ]
        },
        '/api/v1/users/promote-to-admin/': {
            "mode": "raw",
            "raw": json.dumps({}, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        '/api/v1/users/promote-to-super-admin/': {
            "mode": "raw",
            "raw": json.dumps({
                "user_id": "{{user_id}}"
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        # Billing
        '/api/v1/billing/subscribe/': {
            "mode": "raw",
            "raw": json.dumps({
                "tier": "pro",
                "period": "monthly"
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        '/api/v1/billing/addon/': {
            "mode": "raw",
            "raw": json.dumps({
                "package_id": "{{package_id}}"
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        '/api/v1/billing/cancel/': {
            "mode": "raw",
            "raw": json.dumps({}, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        # Data Pipeline
        '/api/v3/data-pipeline/ingest/contacts/local': {
            "mode": "raw",
            "raw": json.dumps({
                "file_path": "path/to/contacts.csv",
                "batch_size": 1000
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        # Analysis
        '/api/v3/analysis/contact/batch/': {
            "mode": "raw",
            "raw": json.dumps({
                "uuids": ["{{contact_uuid}}"]
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        # Sales Navigator
        '/api/v3/sales-navigator/scrape': {
            "mode": "raw",
            "raw": json.dumps({
                "html": "<html><head><title>Sales Navigator</title></head><body><div class=\"search-results\"><div class=\"profile-card\"><div class=\"profile-name\">John Doe</div><div class=\"profile-title\">Software Engineer</div><div class=\"profile-company\">Tech Corp</div><div class=\"profile-location\">San Francisco, CA</div></div></div></body></html>",
                "save": False
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        # Note: contacts/import endpoints were removed - no longer available
        # Exports
        '/api/v3/exports/contacts/export': {
            "mode": "raw",
            "raw": json.dumps({
                "contact_uuids": ["{{contact_uuid}}"]
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        '/api/v3/exports/companies/export': {
            "mode": "raw",
            "raw": json.dumps({
                "company_uuids": ["{{company_uuid}}"]
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        '/api/v3/exports/contacts/export/chunked': {
            "mode": "raw",
            "raw": json.dumps({
                "filters": {
                    "and": [
                        {
                            "field": "first_name",
                            "operator": "eq",
                            "value": "John"
                        }
                    ]
                },
                "select_columns": ["uuid", "first_name", "last_name"],
                "limit": 1000,
                "offset": 0
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        # Gemini
        '/api/v2/gemini/email/analyze': {
            "mode": "raw",
            "raw": json.dumps({
                "email": "test@example.com"
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        '/api/v2/gemini/company/summary': {
            "mode": "raw",
            "raw": json.dumps({
                "company_name": "Example Company Inc.",
                "industry": "Technology"
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        # Cleanup
        '/api/v3/cleanup/contact/batch/': {
            "mode": "raw",
            "raw": json.dumps({
                "uuids": ["{{contact_uuid}}"]
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        '/api/v3/cleanup/company/batch/': {
            "mode": "raw",
            "raw": json.dumps({
                "uuids": ["{{company_uuid}}"]
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        # Validation
        '/api/v3/validation/contact/batch/': {
            "mode": "raw",
            "raw": json.dumps({
                "uuids": ["{{contact_uuid}}"]
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        '/api/v3/validation/company/batch/': {
            "mode": "raw",
            "raw": json.dumps({
                "uuids": ["{{company_uuid}}"]
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        # Note: v3 email_pattern endpoints were removed - use v2 email-patterns endpoints instead
        # Email Patterns Import
        '/api/v2/email-patterns/import': {
            "mode": "formdata",
            "formdata": [
                {
                    "key": "file",
                    "type": "file",
                    "src": [],
                    "description": "CSV file with email patterns"
                }
            ]
        },
        '/api/v2/email-patterns/bulk': {
            "mode": "raw",
            "raw": json.dumps({
                "patterns": [
                    {
                        "company_uuid": "{{company_uuid}}",
                        "pattern": "first.last@company.com",
                        "confidence": 0.95
                    }
                ]
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        # Users
        '/api/v1/users/{user_id}/role/': {
            "mode": "raw",
            "raw": json.dumps({
                "role": "admin"
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        '/api/v1/users/{user_id}/credits/': {
            "mode": "raw",
            "raw": json.dumps({
                "credits": 1000
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        # Billing Admin
        '/api/v1/billing/admin/plans/': {
            "mode": "raw",
            "raw": json.dumps({
                "tier": "enterprise",
                "name": "Enterprise Plan",
                "description": "Enterprise tier with all features"
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        '/api/v1/billing/admin/plans/{tier}/': {
            "mode": "raw",
            "raw": json.dumps({
                "name": "Updated Plan Name",
                "description": "Updated plan description"
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        '/api/v1/billing/admin/plans/{tier}/periods/': {
            "mode": "raw",
            "raw": json.dumps({
                "period": "monthly",
                "price": 99.99,
                "currency": "USD"
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        '/api/v1/billing/admin/addons/{package_id}/': {
            "mode": "raw",
            "raw": json.dumps({
                "name": "Updated Addon Name",
                "credits": 2000,
                "price": 49.99
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        },
        '/api/v1/billing/admin/addons/': {
            "mode": "raw",
            "raw": json.dumps({
                "name": "Email Credits",
                "credits": 1000,
                "price": 29.99
            }, indent=2),
            "options": {"raw": {"language": "json"}}
        }
    }
    
    # Special handling for LinkedIn endpoints with same path but different bodies
    if endpoint == '/api/v3/linkedin/':
        if 'Search' in description or 'search' in description.lower():
            return {
                "mode": "raw",
                "raw": json.dumps({
                    "url": "https://www.linkedin.com/in/johndoe/"
                }, indent=2),
                "options": {"raw": {"language": "json"}}
            }
        elif 'Create or update' in description or 'upsert' in description.lower() or 'create' in description.lower():
            return {
                "mode": "raw",
                "raw": json.dumps({
                    "url": "https://www.linkedin.com/in/johndoe/",
                    "contact_data": None,
                    "company_data": None,
                    "contact_metadata": None,
                    "company_metadata": None
                }, indent=2),
                "options": {"raw": {"language": "json"}}
            }
    
    # Check for exact match
    if endpoint in body_templates:
        return body_templates[endpoint]
    
    # Check for pattern matches
    for pattern, body in body_templates.items():
        if endpoint.startswith(pattern):
            return body
    
    # Default JSON body for POST/PUT
    return {
        "mode": "raw",
        "raw": json.dumps({}, indent=2),
        "options": {"raw": {"language": "json"}}
    }

def get_test_scripts(endpoint, method, api_version, category):
    """Get test scripts for endpoint."""
    scripts = []
    
    # Common tests
    scripts.append("pm.test('Status code is successful', function () {")
    scripts.append("    pm.expect(pm.response.code).to.be.oneOf([200, 201, 202, 204]);")
    scripts.append("});")
    scripts.append("")
    scripts.append("pm.test('Response time is acceptable', function () {")
    scripts.append("    pm.expect(pm.response.responseTime).to.be.below(10000);")
    scripts.append("});")
    
    # Auth endpoints - save tokens
    if 'auth' in endpoint and method == 'POST':
        if 'login' in endpoint or 'register' in endpoint:
            scripts.append("")
            scripts.append("if (pm.response.code === 200 || pm.response.code === 201) {")
            scripts.append("    try {")
            scripts.append("        const jsonData = pm.response.json();")
            scripts.append("        if (jsonData.access_token) {")
            scripts.append("            pm.environment.set('access_token', jsonData.access_token);")
            scripts.append("            console.log('Access token saved');")
            scripts.append("        }")
            scripts.append("        if (jsonData.refresh_token) {")
            scripts.append("            pm.environment.set('refresh_token', jsonData.refresh_token);")
            scripts.append("            console.log('Refresh token saved');")
            scripts.append("        }")
            scripts.append("    } catch (e) {")
            scripts.append("        console.error('Failed to parse response:', e);")
            scripts.append("    }")
            scripts.append("}")
        elif 'refresh' in endpoint:
            scripts.append("")
            scripts.append("if (pm.response.code === 200) {")
            scripts.append("    try {")
            scripts.append("        const jsonData = pm.response.json();")
            scripts.append("        if (jsonData.access_token) {")
            scripts.append("            pm.environment.set('access_token', jsonData.access_token);")
            scripts.append("        }")
            scripts.append("        if (jsonData.refresh_token) {")
            scripts.append("            pm.environment.set('refresh_token', jsonData.refresh_token);")
            scripts.append("        }")
            scripts.append("    } catch (e) {")
            scripts.append("        console.error('Failed to parse response:', e);")
            scripts.append("    }")
            scripts.append("}")
    
    # List endpoints - validate pagination
    if method == 'GET' and endpoint.endswith('/') and 'count' not in endpoint and 'stream' not in endpoint:
        scripts.append("")
        scripts.append("pm.test('Response has correct structure', function () {")
        scripts.append("    const jsonData = pm.response.json();")
        scripts.append("    pm.expect(jsonData).to.be.an('object');")
        scripts.append("});")
    
    # UUID endpoints - save UUIDs from responses
    if method in ['POST', 'GET']:
        scripts.append("")
        scripts.append("// Save UUIDs from response if available")
        scripts.append("if (pm.response.code === 200 || pm.response.code === 201) {")
        scripts.append("    try {")
        scripts.append("        const jsonData = pm.response.json();")
        scripts.append("        const endpoint = pm.request.url.toString();")
        scripts.append("        ")
        scripts.append("        // Save contact UUID")
        scripts.append("        if (jsonData.uuid && (endpoint.includes('contact') || jsonData.first_name || jsonData.last_name)) {")
        scripts.append("            pm.environment.set('contact_uuid', jsonData.uuid);")
        scripts.append("        }")
        scripts.append("        // Save company UUID")
        scripts.append("        if (jsonData.uuid && (endpoint.includes('company') || jsonData.name)) {")
        scripts.append("            pm.environment.set('company_uuid', jsonData.uuid);")
        scripts.append("        }")
        scripts.append("        // Save chat ID")
        scripts.append("        if ((jsonData.uuid || jsonData.id) && endpoint.includes('chat')) {")
        scripts.append("            pm.environment.set('chat_id', jsonData.uuid || jsonData.id);")
        scripts.append("        }")
        scripts.append("        // Save job/export ID")
        scripts.append("        if ((jsonData.uuid || jsonData.id || jsonData.job_id) && (endpoint.includes('job') || endpoint.includes('export'))) {")
        scripts.append("            pm.environment.set('job_id', jsonData.uuid || jsonData.id || jsonData.job_id);")
        scripts.append("            pm.environment.set('export_id', jsonData.uuid || jsonData.id || jsonData.job_id);")
        scripts.append("        }")
        scripts.append("    } catch (e) {")
        scripts.append("        // Response might not be JSON or might not have UUID")
        scripts.append("    }")
        scripts.append("}")
    
    return "\n".join(scripts)

def get_pre_request_script(endpoint, api_version):
    """Get pre-request script."""
    scripts = []
    scripts.append("// Set request timestamp")
    scripts.append("pm.environment.set('timestamp', new Date().toISOString());")
    scripts.append("")
    scripts.append("// Log request details")
    scripts.append("console.log(`Request to: ${pm.request.url.toString()}`);")
    
    # v1 auth/users/billing/usage endpoints also use Bearer token
    # v2, v3, v4 endpoints use Bearer token
    if api_version in ['v1', 'v2', 'v3', 'v4']:
        # Skip token check for public auth endpoints (login, register, refresh)
        if not ('/auth/login' in endpoint or '/auth/register' in endpoint or '/auth/refresh' in endpoint):
            scripts.append("")
            scripts.append("// Check if token exists")
            scripts.append("const token = pm.environment.get('access_token');")
            scripts.append("if (!token || token === '') {")
            scripts.append("    console.warn('No access token set. Please login first.');")
            scripts.append("}")
    
    return "\n".join(scripts)

# Only process endpoints if this script is run directly (not imported)
if __name__ == "__main__" and endpoints:
    # Organize endpoints by category
    categories = defaultdict(list)
    for ep in endpoints:
        category = ep.get('category', 'Other')
        categories[category].append(ep)

    print(f"Organized into {len(categories)} categories")

    # Create collection structure
    collection = {
    "info": {
        "_postman_id": str(uuid.uuid4()),
        "name": "Contact360 API - Complete Collection",
        "description": "Comprehensive API collection for Contact360 backend with 162 endpoints across 4 API versions (v1-v4). Includes authentication, filtering, exports, AI features, and data pipeline operations.\n\n**Base URL**: {{base_url}}\n**Authentication**: \n- v1 endpoints: Bearer token (JWT) for auth/users/billing/usage endpoints\n- v2/v3/v4 endpoints: Bearer token (JWT)\n- Public endpoints (login, register, refresh): No authentication required\n\n## API Structure\n- **V1**: Auth, Users, Billing, Usage, Health, Root\n- **V2**: AI Chats, Gemini\n- **V3**: Companies, Contacts, Email, Exports, LinkedIn, Activities, S3, Sales Navigator\n- **V4**: Marketing, Dashboard Pages (and admin endpoints)\n\n## Features\n- Complete CRUD operations for contacts and companies\n- Advanced filtering and search\n- Email finder and verification\n- AI chat with Gemini\n- LinkedIn profile lookup\n- Data pipeline operations\n- Export functionality",
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
    },
    "item": [],
    "variable": [
        {"key": "base_url", "value": "http://34.229.94.175", "type": "string"},
        {"key": "api_v1_prefix", "value": "/api/v1", "type": "string"},
        {"key": "api_v2_prefix", "value": "/api/v2", "type": "string"},
        {"key": "api_v3_prefix", "value": "/api/v3", "type": "string"},
        {"key": "api_v4_prefix", "value": "/api/v4", "type": "string"},
        {"key": "access_token", "value": "", "type": "string"},
        {"key": "refresh_token", "value": "", "type": "string"},
        {"key": "write_key", "value": "", "type": "string"},
        {"key": "contact_uuid", "value": "00000000-0000-0000-0000-000000000000", "type": "string"},
        {"key": "company_uuid", "value": "00000000-0000-0000-0000-000000000000", "type": "string"},
        {"key": "chat_id", "value": "", "type": "string"},
        {"key": "job_id", "value": "", "type": "string"},
        {"key": "export_id", "value": "", "type": "string"},
        {"key": "user_id", "value": "", "type": "string"},
        {"key": "pattern_uuid", "value": "", "type": "string"},
        {"key": "tier", "value": "pro", "type": "string"},
        {"key": "period", "value": "monthly", "type": "string"},
        {"key": "package_id", "value": "", "type": "string"},
        {"key": "file_id", "value": "", "type": "string"},
        {"key": "file_type", "value": "json", "type": "string"},
        {"key": "slug", "value": "", "type": "string"}
    ],
    "event": [
        {
            "listen": "prerequest",
            "script": {
                "type": "text/javascript",
                "exec": [
                    "// Set request timestamp",
                    "pm.environment.set('timestamp', new Date().toISOString());",
                    "",
                    "// Log request details",
                    "console.log(`Request to: ${pm.request.url.toString()}`);"
                ]
            }
        },
        {
            "listen": "test",
            "script": {
                "type": "text/javascript",
                "exec": [
                    "// Global test script - runs after each request"
                ]
            }
        }
    ]
}

    # Create folders (categories)
    for category_name, category_endpoints in sorted(categories.items()):
        folder = {
            "name": category_name,
            "item": [],
            "description": f"Endpoints in the {category_name} category"
        }
        
        # Add folder-level auth if needed
        if category_name not in ['Global', 'Root']:
            # Determine auth type from first endpoint
            first_ep = category_endpoints[0]
            api_version = first_ep.get('api_version', 'v1')
            endpoint_path = first_ep.get('endpoint', '')
            
            # v1 endpoints - auth/users/billing/usage use Bearer token
            # v2, v3, v4 endpoints use Bearer token (except Auth category)
            if api_version == 'v1':
                # v1 Auth folder doesn't need token at folder level (login/register are public)
                # But Users, Billing, Usage folders should have Bearer token
                if category_name not in ['Auth', 'Root', 'Health']:
                    folder["auth"] = {
                        "type": "bearer",
                        "bearer": [
                            {"key": "token", "value": "{{access_token}}", "type": "string"}
                        ]
                    }
            elif api_version in ['v2', 'v3', 'v4']:
                # Auth folder doesn't need token at folder level (login/register are public)
                if category_name != 'Auth':
                    folder["auth"] = {
                        "type": "bearer",
                        "bearer": [
                            {"key": "token", "value": "{{access_token}}", "type": "string"}
                        ]
                    }
        
        # Add requests to folder
        for ep in category_endpoints:
            method = ep.get('method', 'GET')
            endpoint = ep.get('endpoint', '')
            description = ep.get('description', '')
            api_version = ep.get('api_version', 'global')
            requires_auth = ep.get('requires_auth', 'FALSE') == 'TRUE'
            requires_admin = ep.get('requires_admin', 'FALSE') == 'TRUE'
            status_code = ep.get('status_code', '')
            error_message = ep.get('error_message', '')
            
            # Build URL
            url_path = replace_path_params(endpoint)
            if url_path.startswith('/'):
                full_url = f"{{{{base_url}}}}{url_path}"
            else:
                full_url = f"{{{{base_url}}}}/{url_path}"
            
            # Parse URL components
            url_parts = endpoint.split('/')
            path_parts = [p for p in url_parts if p and not p.startswith('api')]
            
            request_obj = {
                "name": f"{method} {endpoint}",
                "request": {
                    "method": method,
                    "header": get_headers(endpoint, method, api_version),
                    "url": {
                        "raw": full_url,
                        "host": ["{{base_url}}"],
                        "path": [p for p in endpoint.split('/') if p]
                    },
                    "description": description + (
                        f"\n\n**Note**: {error_message}" if error_message else ""
                    ) + (
                        "\n\n**Requires Admin Access**" if requires_admin else ""
                    ) + (
                        "\n\n**Status**: " + status_code if status_code else ""
                    ),
                    "auth": get_auth_config(endpoint, api_version, requires_auth, requires_admin)
                },
                "response": []
            }
            
            # Add query parameters
            query_params = get_query_params(endpoint, method)
            if query_params:
                request_obj["request"]["url"]["query"] = query_params
            
            # Add request body
            if method in ['POST', 'PUT', 'PATCH']:
                body = get_request_body(endpoint, method, api_version, category_name, description)
                if body:
                    request_obj["request"]["body"] = body
            
            # Add test scripts
            test_script = get_test_scripts(endpoint, method, api_version, category_name)
            if test_script:
                request_obj["request"]["event"] = [
                    {
                        "listen": "test",
                        "script": {
                            "type": "text/javascript",
                            "exec": test_script.split('\n')
                        }
                    }
                ]
            
            # Add pre-request script
            pre_request = get_pre_request_script(endpoint, api_version)
            if pre_request:
                if 'event' not in request_obj["request"]:
                    request_obj["request"]["event"] = []
                request_obj["request"]["event"].insert(0, {
                    "listen": "prerequest",
                    "script": {
                        "type": "text/javascript",
                        "exec": pre_request.split('\n')
                    }
                })
            
            # Special handling for WebSocket
            if method == 'WEBSOCKET':
                request_obj["request"]["description"] += "\n\n**Note**: This is a WebSocket endpoint. Postman cannot test WebSocket connections directly. Use a WebSocket client tool instead."
            
            folder["item"].append(request_obj)
        
        collection["item"].append(folder)

    # Write collection to file
    json_dir = Path(__file__).parent / "json"
    json_dir.mkdir(parents=True, exist_ok=True)
    output_path = json_dir / "Contact360 API.postman_collection.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(collection, f, indent=2, ensure_ascii=False)

    print(f"Generated Postman collection with {len(endpoints)} endpoints in {len(categories)} categories")
    print(f"Output: {output_path}")
    if FILTERS_AVAILABLE:
        print("✓ Filter parameter extraction enabled")
    else:
        print("⚠ Filter parameter extraction disabled (using fallback)")
    if SCHEMAS_AVAILABLE:
        print("✓ Request body schema extraction enabled")
    else:
        print("⚠ Request body schema extraction disabled (using fallback)")

