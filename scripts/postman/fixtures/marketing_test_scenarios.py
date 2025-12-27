"""Comprehensive test scenarios for Marketing API endpoints.

This module defines all test scenarios for the Marketing API,
covering public and admin endpoints for marketing pages.
"""

from typing import Dict, List, Any


class MarketingTestScenarios:
    """Comprehensive test scenarios for Marketing API endpoints."""
    
    @staticmethod
    def get_public_get_page_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for public get marketing page endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "public_get_page",
                "name": "get_published_page_public",
                "description": "Get published marketing page without authentication",
                "method": "GET",
                "endpoint": "/api/v4/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "query_params": {},
                "headers": {},  # No Authorization header
                "expected_status": [200, 404],  # 404 if page doesn't exist
                "validate_response": {
                    "has_fields": ["page_id", "metadata", "hero"],
                    "metadata_has_status": "published"
                }
            },
            {
                "category": "public_get_page",
                "name": "get_published_page_authenticated",
                "description": "Get published marketing page with authentication",
                "method": "GET",
                "endpoint": "/api/v4/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "query_params": {},
                "expected_status": [200, 404],
                "validate_response": {
                    "has_fields": ["page_id", "metadata", "hero"],
                    "metadata_has_status": "published"
                }
            },
            {
                "category": "public_get_page",
                "name": "get_page_not_found",
                "description": "Get non-existent marketing page (should fail)",
                "method": "GET",
                "endpoint": "/api/v4/marketing/{page_id}",
                "path_params": {
                    "page_id": "non-existent-page"
                },
                "query_params": {},
                "expected_status": [404],
            },
            {
                "category": "public_get_page",
                "name": "get_draft_page_public",
                "description": "Get draft page via public endpoint (should fail - only published pages)",
                "method": "GET",
                "endpoint": "/api/v4/marketing/{page_id}",
                "path_params": {
                    "page_id": "draft-page"
                },
                "query_params": {},
                "expected_status": [404],  # Draft pages not accessible via public endpoint
            },
        ]
    
    @staticmethod
    def get_public_list_pages_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for public list marketing pages endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "public_list_pages",
                "name": "list_published_pages",
                "description": "List all published marketing pages",
                "method": "GET",
                "endpoint": "/api/v4/marketing/",
                "query_params": {},
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["pages", "total"],
                    "pages_is_list": True,
                    "total_is_int": True
                }
            },
            {
                "category": "public_list_pages",
                "name": "list_pages_with_include_drafts",
                "description": "List pages with include_drafts parameter (ignored for public endpoint)",
                "method": "GET",
                "endpoint": "/api/v4/marketing/",
                "query_params": {
                    "include_drafts": True
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["pages", "total"]
                }
            },
        ]
    
    @staticmethod
    def get_admin_list_pages_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for admin list marketing pages endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "admin_list_pages",
                "name": "list_all_pages_default",
                "description": "List all marketing pages with default parameters (includes drafts, excludes deleted)",
                "method": "GET",
                "endpoint": "/api/v4/admin/marketing/",
                "query_params": {},
                "expected_status": [200, 401, 403],  # 401/403 if not admin
                "validate_response": {
                    "has_fields": ["pages", "total"]
                }
            },
            {
                "category": "admin_list_pages",
                "name": "list_all_pages_with_drafts",
                "description": "List all pages including drafts",
                "method": "GET",
                "endpoint": "/api/v4/admin/marketing/",
                "query_params": {
                    "include_drafts": True,
                    "include_deleted": False
                },
                "expected_status": [200, 401, 403],
                "validate_response": {
                    "has_fields": ["pages", "total"]
                }
            },
            {
                "category": "admin_list_pages",
                "name": "list_all_pages_with_deleted",
                "description": "List all pages including deleted",
                "method": "GET",
                "endpoint": "/api/v4/admin/marketing/",
                "query_params": {
                    "include_drafts": True,
                    "include_deleted": True
                },
                "expected_status": [200, 401, 403],
                "validate_response": {
                    "has_fields": ["pages", "total"]
                }
            },
            {
                "category": "admin_list_pages",
                "name": "list_pages_unauthorized",
                "description": "List pages without authentication (should fail)",
                "method": "GET",
                "endpoint": "/api/v4/admin/marketing/",
                "query_params": {},
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
            {
                "category": "admin_list_pages",
                "name": "list_pages_forbidden",
                "description": "List pages as non-admin user (should fail)",
                "method": "GET",
                "endpoint": "/api/v4/admin/marketing/",
                "query_params": {},
                "expected_status": [403],  # Free/Pro users cannot access admin endpoints
            },
        ]
    
    @staticmethod
    def get_admin_get_page_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for admin get marketing page endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "admin_get_page",
                "name": "get_any_page_published",
                "description": "Get published page via admin endpoint",
                "method": "GET",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "query_params": {},
                "expected_status": [200, 404, 401, 403],
                "validate_response": {
                    "has_fields": ["page_id", "metadata", "hero"]
                }
            },
            {
                "category": "admin_get_page",
                "name": "get_any_page_draft",
                "description": "Get draft page via admin endpoint",
                "method": "GET",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "draft-page"
                },
                "query_params": {},
                "expected_status": [200, 404, 401, 403],
            },
            {
                "category": "admin_get_page",
                "name": "get_page_not_found",
                "description": "Get non-existent page via admin endpoint (should fail)",
                "method": "GET",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "non-existent-page"
                },
                "query_params": {},
                "expected_status": [404, 401, 403],
            },
            {
                "category": "admin_get_page",
                "name": "get_page_unauthorized",
                "description": "Get page without authentication (should fail)",
                "method": "GET",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "query_params": {},
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
        ]
    
    @staticmethod
    def get_admin_create_page_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for admin create marketing page endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "admin_create_page",
                "name": "create_page_minimal",
                "description": "Create marketing page with minimal required fields",
                "method": "POST",
                "endpoint": "/api/v4/admin/marketing/",
                "body": {
                    "page_id": "test-page-minimal",
                    "hero": {
                        "title": "Test Hero Title",
                        "description": "Test hero description"
                    }
                },
                "expected_status": [201, 400, 401, 403],
                "validate_response": {
                    "has_fields": ["page_id", "hero"]
                }
            },
            {
                "category": "admin_create_page",
                "name": "create_page_complete",
                "description": "Create marketing page with all fields",
                "method": "POST",
                "endpoint": "/api/v4/admin/marketing/",
                "body": {
                    "page_id": "test-page-complete",
                    "metadata": {
                        "title": "Test Page",
                        "description": "Test page description",
                        "keywords": ["test", "page"],
                        "status": "draft",
                        "version": 1
                    },
                    "hero": {
                        "title": "Test Hero Title",
                        "subtitle": "Test Hero Subtitle",
                        "description": "Test hero description",
                        "features": ["Feature 1", "Feature 2"],
                        "cta_text": "Get Started",
                        "cta_href": "/signup"
                    },
                    "sections": {
                        "section1": {
                            "content": "Section content"
                        }
                    },
                    "hero_stats": [
                        {"key": "stat1", "value": "value1"}
                    ],
                    "hero_table": {
                        "column1": "value1"
                    }
                },
                "expected_status": [201, 400, 401, 403],
                "validate_response": {
                    "has_fields": ["page_id", "metadata", "hero", "sections"]
                }
            },
            {
                "category": "admin_create_page",
                "name": "create_page_with_published_status",
                "description": "Create marketing page with published status",
                "method": "POST",
                "endpoint": "/api/v4/admin/marketing/",
                "body": {
                    "page_id": "test-page-published",
                    "metadata": {
                        "title": "Published Page",
                        "description": "Page description",
                        "status": "published"
                    },
                    "hero": {
                        "title": "Hero Title",
                        "description": "Hero description"
                    }
                },
                "expected_status": [201, 400, 401, 403],
            },
            {
                "category": "admin_create_page",
                "name": "create_page_missing_hero",
                "description": "Create page without required hero field (should fail)",
                "method": "POST",
                "endpoint": "/api/v4/admin/marketing/",
                "body": {
                    "page_id": "test-page-invalid"
                    # Missing hero
                },
                "expected_status": [400, 422],
            },
            {
                "category": "admin_create_page",
                "name": "create_page_missing_page_id",
                "description": "Create page without required page_id (should fail)",
                "method": "POST",
                "endpoint": "/api/v4/admin/marketing/",
                "body": {
                    "hero": {
                        "title": "Hero Title",
                        "description": "Hero description"
                    }
                    # Missing page_id
                },
                "expected_status": [400, 422],
            },
            {
                "category": "admin_create_page",
                "name": "create_page_unauthorized",
                "description": "Create page without authentication (should fail)",
                "method": "POST",
                "endpoint": "/api/v4/admin/marketing/",
                "body": {
                    "page_id": "test-page",
                    "hero": {
                        "title": "Hero Title",
                        "description": "Hero description"
                    }
                },
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
        ]
    
    @staticmethod
    def get_admin_update_page_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for admin update marketing page endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "admin_update_page",
                "name": "update_page_metadata",
                "description": "Update marketing page metadata (partial update)",
                "method": "PUT",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "body": {
                    "metadata": {
                        "title": "Updated Title"
                    }
                },
                "expected_status": [200, 404, 400, 401, 403],
                "validate_response": {
                    "has_fields": ["page_id", "metadata"]
                }
            },
            {
                "category": "admin_update_page",
                "name": "update_page_hero",
                "description": "Update marketing page hero section",
                "method": "PUT",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "body": {
                    "hero": {
                        "subtitle": "Updated Subtitle"
                    }
                },
                "expected_status": [200, 404, 400, 401, 403],
            },
            {
                "category": "admin_update_page",
                "name": "update_page_sections",
                "description": "Update marketing page sections",
                "method": "PUT",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "body": {
                    "sections": {
                        "new_section": {
                            "content": "New section content"
                        }
                    }
                },
                "expected_status": [200, 404, 400, 401, 403],
            },
            {
                "category": "admin_update_page",
                "name": "update_page_multiple_fields",
                "description": "Update multiple fields at once",
                "method": "PUT",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "body": {
                    "metadata": {
                        "title": "Updated Title"
                    },
                    "hero": {
                        "subtitle": "Updated Subtitle"
                    },
                    "sections": {
                        "section1": {
                            "content": "Updated content"
                        }
                    }
                },
                "expected_status": [200, 404, 400, 401, 403],
            },
            {
                "category": "admin_update_page",
                "name": "update_page_not_found",
                "description": "Update non-existent page (should fail)",
                "method": "PUT",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "non-existent-page"
                },
                "body": {
                    "metadata": {
                        "title": "Updated Title"
                    }
                },
                "expected_status": [404, 401, 403],
            },
            {
                "category": "admin_update_page",
                "name": "update_page_unauthorized",
                "description": "Update page without authentication (should fail)",
                "method": "PUT",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "body": {
                    "metadata": {
                        "title": "Updated Title"
                    }
                },
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
        ]
    
    @staticmethod
    def get_admin_delete_page_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for admin delete marketing page endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "admin_delete_page",
                "name": "delete_page_soft",
                "description": "Soft delete marketing page (default)",
                "method": "DELETE",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "query_params": {},
                "expected_status": [204, 404, 401, 403],
            },
            {
                "category": "admin_delete_page",
                "name": "delete_page_hard",
                "description": "Hard delete marketing page (permanent)",
                "method": "DELETE",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "query_params": {
                    "hard_delete": True
                },
                "expected_status": [204, 404, 401, 403],
            },
            {
                "category": "admin_delete_page",
                "name": "delete_page_not_found",
                "description": "Delete non-existent page (should fail)",
                "method": "DELETE",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "non-existent-page"
                },
                "query_params": {},
                "expected_status": [404, 401, 403],
            },
            {
                "category": "admin_delete_page",
                "name": "delete_page_unauthorized",
                "description": "Delete page without authentication (should fail)",
                "method": "DELETE",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "query_params": {},
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
        ]
    
    @staticmethod
    def get_admin_publish_page_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for admin publish marketing page endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "admin_publish_page",
                "name": "publish_draft_page",
                "description": "Publish a draft marketing page",
                "method": "POST",
                "endpoint": "/api/v4/admin/marketing/{page_id}/publish",
                "path_params": {
                    "page_id": "draft-page"
                },
                "query_params": {},
                "expected_status": [200, 404, 400, 401, 403],
                "validate_response": {
                    "has_fields": ["page_id", "metadata"],
                    "metadata_has_status": "published"
                }
            },
            {
                "category": "admin_publish_page",
                "name": "publish_page_not_found",
                "description": "Publish non-existent page (should fail)",
                "method": "POST",
                "endpoint": "/api/v4/admin/marketing/{page_id}/publish",
                "path_params": {
                    "page_id": "non-existent-page"
                },
                "query_params": {},
                "expected_status": [404, 401, 403],
            },
            {
                "category": "admin_publish_page",
                "name": "publish_page_unauthorized",
                "description": "Publish page without authentication (should fail)",
                "method": "POST",
                "endpoint": "/api/v4/admin/marketing/{page_id}/publish",
                "path_params": {
                    "page_id": "draft-page"
                },
                "query_params": {},
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
        ]
    
    @staticmethod
    def get_all_scenarios() -> Dict[str, List[Dict[str, Any]]]:
        """Get all test scenarios organized by category.
        
        Returns:
            Dictionary mapping category names to lists of scenarios
        """
        return {
            "public_get_page": MarketingTestScenarios.get_public_get_page_scenarios(),
            "public_list_pages": MarketingTestScenarios.get_public_list_pages_scenarios(),
            "admin_list_pages": MarketingTestScenarios.get_admin_list_pages_scenarios(),
            "admin_get_page": MarketingTestScenarios.get_admin_get_page_scenarios(),
            "admin_create_page": MarketingTestScenarios.get_admin_create_page_scenarios(),
            "admin_update_page": MarketingTestScenarios.get_admin_update_page_scenarios(),
            "admin_delete_page": MarketingTestScenarios.get_admin_delete_page_scenarios(),
            "admin_publish_page": MarketingTestScenarios.get_admin_publish_page_scenarios(),
        }


This module defines all test scenarios for the Marketing API,
covering public and admin endpoints for marketing pages.
"""

from typing import Dict, List, Any


class MarketingTestScenarios:
    """Comprehensive test scenarios for Marketing API endpoints."""
    
    @staticmethod
    def get_public_get_page_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for public get marketing page endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "public_get_page",
                "name": "get_published_page_public",
                "description": "Get published marketing page without authentication",
                "method": "GET",
                "endpoint": "/api/v4/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "query_params": {},
                "headers": {},  # No Authorization header
                "expected_status": [200, 404],  # 404 if page doesn't exist
                "validate_response": {
                    "has_fields": ["page_id", "metadata", "hero"],
                    "metadata_has_status": "published"
                }
            },
            {
                "category": "public_get_page",
                "name": "get_published_page_authenticated",
                "description": "Get published marketing page with authentication",
                "method": "GET",
                "endpoint": "/api/v4/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "query_params": {},
                "expected_status": [200, 404],
                "validate_response": {
                    "has_fields": ["page_id", "metadata", "hero"],
                    "metadata_has_status": "published"
                }
            },
            {
                "category": "public_get_page",
                "name": "get_page_not_found",
                "description": "Get non-existent marketing page (should fail)",
                "method": "GET",
                "endpoint": "/api/v4/marketing/{page_id}",
                "path_params": {
                    "page_id": "non-existent-page"
                },
                "query_params": {},
                "expected_status": [404],
            },
            {
                "category": "public_get_page",
                "name": "get_draft_page_public",
                "description": "Get draft page via public endpoint (should fail - only published pages)",
                "method": "GET",
                "endpoint": "/api/v4/marketing/{page_id}",
                "path_params": {
                    "page_id": "draft-page"
                },
                "query_params": {},
                "expected_status": [404],  # Draft pages not accessible via public endpoint
            },
        ]
    
    @staticmethod
    def get_public_list_pages_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for public list marketing pages endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "public_list_pages",
                "name": "list_published_pages",
                "description": "List all published marketing pages",
                "method": "GET",
                "endpoint": "/api/v4/marketing/",
                "query_params": {},
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["pages", "total"],
                    "pages_is_list": True,
                    "total_is_int": True
                }
            },
            {
                "category": "public_list_pages",
                "name": "list_pages_with_include_drafts",
                "description": "List pages with include_drafts parameter (ignored for public endpoint)",
                "method": "GET",
                "endpoint": "/api/v4/marketing/",
                "query_params": {
                    "include_drafts": True
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["pages", "total"]
                }
            },
        ]
    
    @staticmethod
    def get_admin_list_pages_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for admin list marketing pages endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "admin_list_pages",
                "name": "list_all_pages_default",
                "description": "List all marketing pages with default parameters (includes drafts, excludes deleted)",
                "method": "GET",
                "endpoint": "/api/v4/admin/marketing/",
                "query_params": {},
                "expected_status": [200, 401, 403],  # 401/403 if not admin
                "validate_response": {
                    "has_fields": ["pages", "total"]
                }
            },
            {
                "category": "admin_list_pages",
                "name": "list_all_pages_with_drafts",
                "description": "List all pages including drafts",
                "method": "GET",
                "endpoint": "/api/v4/admin/marketing/",
                "query_params": {
                    "include_drafts": True,
                    "include_deleted": False
                },
                "expected_status": [200, 401, 403],
                "validate_response": {
                    "has_fields": ["pages", "total"]
                }
            },
            {
                "category": "admin_list_pages",
                "name": "list_all_pages_with_deleted",
                "description": "List all pages including deleted",
                "method": "GET",
                "endpoint": "/api/v4/admin/marketing/",
                "query_params": {
                    "include_drafts": True,
                    "include_deleted": True
                },
                "expected_status": [200, 401, 403],
                "validate_response": {
                    "has_fields": ["pages", "total"]
                }
            },
            {
                "category": "admin_list_pages",
                "name": "list_pages_unauthorized",
                "description": "List pages without authentication (should fail)",
                "method": "GET",
                "endpoint": "/api/v4/admin/marketing/",
                "query_params": {},
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
            {
                "category": "admin_list_pages",
                "name": "list_pages_forbidden",
                "description": "List pages as non-admin user (should fail)",
                "method": "GET",
                "endpoint": "/api/v4/admin/marketing/",
                "query_params": {},
                "expected_status": [403],  # Free/Pro users cannot access admin endpoints
            },
        ]
    
    @staticmethod
    def get_admin_get_page_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for admin get marketing page endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "admin_get_page",
                "name": "get_any_page_published",
                "description": "Get published page via admin endpoint",
                "method": "GET",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "query_params": {},
                "expected_status": [200, 404, 401, 403],
                "validate_response": {
                    "has_fields": ["page_id", "metadata", "hero"]
                }
            },
            {
                "category": "admin_get_page",
                "name": "get_any_page_draft",
                "description": "Get draft page via admin endpoint",
                "method": "GET",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "draft-page"
                },
                "query_params": {},
                "expected_status": [200, 404, 401, 403],
            },
            {
                "category": "admin_get_page",
                "name": "get_page_not_found",
                "description": "Get non-existent page via admin endpoint (should fail)",
                "method": "GET",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "non-existent-page"
                },
                "query_params": {},
                "expected_status": [404, 401, 403],
            },
            {
                "category": "admin_get_page",
                "name": "get_page_unauthorized",
                "description": "Get page without authentication (should fail)",
                "method": "GET",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "query_params": {},
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
        ]
    
    @staticmethod
    def get_admin_create_page_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for admin create marketing page endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "admin_create_page",
                "name": "create_page_minimal",
                "description": "Create marketing page with minimal required fields",
                "method": "POST",
                "endpoint": "/api/v4/admin/marketing/",
                "body": {
                    "page_id": "test-page-minimal",
                    "hero": {
                        "title": "Test Hero Title",
                        "description": "Test hero description"
                    }
                },
                "expected_status": [201, 400, 401, 403],
                "validate_response": {
                    "has_fields": ["page_id", "hero"]
                }
            },
            {
                "category": "admin_create_page",
                "name": "create_page_complete",
                "description": "Create marketing page with all fields",
                "method": "POST",
                "endpoint": "/api/v4/admin/marketing/",
                "body": {
                    "page_id": "test-page-complete",
                    "metadata": {
                        "title": "Test Page",
                        "description": "Test page description",
                        "keywords": ["test", "page"],
                        "status": "draft",
                        "version": 1
                    },
                    "hero": {
                        "title": "Test Hero Title",
                        "subtitle": "Test Hero Subtitle",
                        "description": "Test hero description",
                        "features": ["Feature 1", "Feature 2"],
                        "cta_text": "Get Started",
                        "cta_href": "/signup"
                    },
                    "sections": {
                        "section1": {
                            "content": "Section content"
                        }
                    },
                    "hero_stats": [
                        {"key": "stat1", "value": "value1"}
                    ],
                    "hero_table": {
                        "column1": "value1"
                    }
                },
                "expected_status": [201, 400, 401, 403],
                "validate_response": {
                    "has_fields": ["page_id", "metadata", "hero", "sections"]
                }
            },
            {
                "category": "admin_create_page",
                "name": "create_page_with_published_status",
                "description": "Create marketing page with published status",
                "method": "POST",
                "endpoint": "/api/v4/admin/marketing/",
                "body": {
                    "page_id": "test-page-published",
                    "metadata": {
                        "title": "Published Page",
                        "description": "Page description",
                        "status": "published"
                    },
                    "hero": {
                        "title": "Hero Title",
                        "description": "Hero description"
                    }
                },
                "expected_status": [201, 400, 401, 403],
            },
            {
                "category": "admin_create_page",
                "name": "create_page_missing_hero",
                "description": "Create page without required hero field (should fail)",
                "method": "POST",
                "endpoint": "/api/v4/admin/marketing/",
                "body": {
                    "page_id": "test-page-invalid"
                    # Missing hero
                },
                "expected_status": [400, 422],
            },
            {
                "category": "admin_create_page",
                "name": "create_page_missing_page_id",
                "description": "Create page without required page_id (should fail)",
                "method": "POST",
                "endpoint": "/api/v4/admin/marketing/",
                "body": {
                    "hero": {
                        "title": "Hero Title",
                        "description": "Hero description"
                    }
                    # Missing page_id
                },
                "expected_status": [400, 422],
            },
            {
                "category": "admin_create_page",
                "name": "create_page_unauthorized",
                "description": "Create page without authentication (should fail)",
                "method": "POST",
                "endpoint": "/api/v4/admin/marketing/",
                "body": {
                    "page_id": "test-page",
                    "hero": {
                        "title": "Hero Title",
                        "description": "Hero description"
                    }
                },
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
        ]
    
    @staticmethod
    def get_admin_update_page_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for admin update marketing page endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "admin_update_page",
                "name": "update_page_metadata",
                "description": "Update marketing page metadata (partial update)",
                "method": "PUT",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "body": {
                    "metadata": {
                        "title": "Updated Title"
                    }
                },
                "expected_status": [200, 404, 400, 401, 403],
                "validate_response": {
                    "has_fields": ["page_id", "metadata"]
                }
            },
            {
                "category": "admin_update_page",
                "name": "update_page_hero",
                "description": "Update marketing page hero section",
                "method": "PUT",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "body": {
                    "hero": {
                        "subtitle": "Updated Subtitle"
                    }
                },
                "expected_status": [200, 404, 400, 401, 403],
            },
            {
                "category": "admin_update_page",
                "name": "update_page_sections",
                "description": "Update marketing page sections",
                "method": "PUT",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "body": {
                    "sections": {
                        "new_section": {
                            "content": "New section content"
                        }
                    }
                },
                "expected_status": [200, 404, 400, 401, 403],
            },
            {
                "category": "admin_update_page",
                "name": "update_page_multiple_fields",
                "description": "Update multiple fields at once",
                "method": "PUT",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "body": {
                    "metadata": {
                        "title": "Updated Title"
                    },
                    "hero": {
                        "subtitle": "Updated Subtitle"
                    },
                    "sections": {
                        "section1": {
                            "content": "Updated content"
                        }
                    }
                },
                "expected_status": [200, 404, 400, 401, 403],
            },
            {
                "category": "admin_update_page",
                "name": "update_page_not_found",
                "description": "Update non-existent page (should fail)",
                "method": "PUT",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "non-existent-page"
                },
                "body": {
                    "metadata": {
                        "title": "Updated Title"
                    }
                },
                "expected_status": [404, 401, 403],
            },
            {
                "category": "admin_update_page",
                "name": "update_page_unauthorized",
                "description": "Update page without authentication (should fail)",
                "method": "PUT",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "body": {
                    "metadata": {
                        "title": "Updated Title"
                    }
                },
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
        ]
    
    @staticmethod
    def get_admin_delete_page_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for admin delete marketing page endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "admin_delete_page",
                "name": "delete_page_soft",
                "description": "Soft delete marketing page (default)",
                "method": "DELETE",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "query_params": {},
                "expected_status": [204, 404, 401, 403],
            },
            {
                "category": "admin_delete_page",
                "name": "delete_page_hard",
                "description": "Hard delete marketing page (permanent)",
                "method": "DELETE",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "query_params": {
                    "hard_delete": True
                },
                "expected_status": [204, 404, 401, 403],
            },
            {
                "category": "admin_delete_page",
                "name": "delete_page_not_found",
                "description": "Delete non-existent page (should fail)",
                "method": "DELETE",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "non-existent-page"
                },
                "query_params": {},
                "expected_status": [404, 401, 403],
            },
            {
                "category": "admin_delete_page",
                "name": "delete_page_unauthorized",
                "description": "Delete page without authentication (should fail)",
                "method": "DELETE",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "query_params": {},
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
        ]
    
    @staticmethod
    def get_admin_publish_page_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for admin publish marketing page endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "admin_publish_page",
                "name": "publish_draft_page",
                "description": "Publish a draft marketing page",
                "method": "POST",
                "endpoint": "/api/v4/admin/marketing/{page_id}/publish",
                "path_params": {
                    "page_id": "draft-page"
                },
                "query_params": {},
                "expected_status": [200, 404, 400, 401, 403],
                "validate_response": {
                    "has_fields": ["page_id", "metadata"],
                    "metadata_has_status": "published"
                }
            },
            {
                "category": "admin_publish_page",
                "name": "publish_page_not_found",
                "description": "Publish non-existent page (should fail)",
                "method": "POST",
                "endpoint": "/api/v4/admin/marketing/{page_id}/publish",
                "path_params": {
                    "page_id": "non-existent-page"
                },
                "query_params": {},
                "expected_status": [404, 401, 403],
            },
            {
                "category": "admin_publish_page",
                "name": "publish_page_unauthorized",
                "description": "Publish page without authentication (should fail)",
                "method": "POST",
                "endpoint": "/api/v4/admin/marketing/{page_id}/publish",
                "path_params": {
                    "page_id": "draft-page"
                },
                "query_params": {},
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
        ]
    
    @staticmethod
    def get_all_scenarios() -> Dict[str, List[Dict[str, Any]]]:
        """Get all test scenarios organized by category.
        
        Returns:
            Dictionary mapping category names to lists of scenarios
        """
        return {
            "public_get_page": MarketingTestScenarios.get_public_get_page_scenarios(),
            "public_list_pages": MarketingTestScenarios.get_public_list_pages_scenarios(),
            "admin_list_pages": MarketingTestScenarios.get_admin_list_pages_scenarios(),
            "admin_get_page": MarketingTestScenarios.get_admin_get_page_scenarios(),
            "admin_create_page": MarketingTestScenarios.get_admin_create_page_scenarios(),
            "admin_update_page": MarketingTestScenarios.get_admin_update_page_scenarios(),
            "admin_delete_page": MarketingTestScenarios.get_admin_delete_page_scenarios(),
            "admin_publish_page": MarketingTestScenarios.get_admin_publish_page_scenarios(),
        }


This module defines all test scenarios for the Marketing API,
covering public and admin endpoints for marketing pages.
"""

from typing import Dict, List, Any


class MarketingTestScenarios:
    """Comprehensive test scenarios for Marketing API endpoints."""
    
    @staticmethod
    def get_public_get_page_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for public get marketing page endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "public_get_page",
                "name": "get_published_page_public",
                "description": "Get published marketing page without authentication",
                "method": "GET",
                "endpoint": "/api/v4/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "query_params": {},
                "headers": {},  # No Authorization header
                "expected_status": [200, 404],  # 404 if page doesn't exist
                "validate_response": {
                    "has_fields": ["page_id", "metadata", "hero"],
                    "metadata_has_status": "published"
                }
            },
            {
                "category": "public_get_page",
                "name": "get_published_page_authenticated",
                "description": "Get published marketing page with authentication",
                "method": "GET",
                "endpoint": "/api/v4/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "query_params": {},
                "expected_status": [200, 404],
                "validate_response": {
                    "has_fields": ["page_id", "metadata", "hero"],
                    "metadata_has_status": "published"
                }
            },
            {
                "category": "public_get_page",
                "name": "get_page_not_found",
                "description": "Get non-existent marketing page (should fail)",
                "method": "GET",
                "endpoint": "/api/v4/marketing/{page_id}",
                "path_params": {
                    "page_id": "non-existent-page"
                },
                "query_params": {},
                "expected_status": [404],
            },
            {
                "category": "public_get_page",
                "name": "get_draft_page_public",
                "description": "Get draft page via public endpoint (should fail - only published pages)",
                "method": "GET",
                "endpoint": "/api/v4/marketing/{page_id}",
                "path_params": {
                    "page_id": "draft-page"
                },
                "query_params": {},
                "expected_status": [404],  # Draft pages not accessible via public endpoint
            },
        ]
    
    @staticmethod
    def get_public_list_pages_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for public list marketing pages endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "public_list_pages",
                "name": "list_published_pages",
                "description": "List all published marketing pages",
                "method": "GET",
                "endpoint": "/api/v4/marketing/",
                "query_params": {},
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["pages", "total"],
                    "pages_is_list": True,
                    "total_is_int": True
                }
            },
            {
                "category": "public_list_pages",
                "name": "list_pages_with_include_drafts",
                "description": "List pages with include_drafts parameter (ignored for public endpoint)",
                "method": "GET",
                "endpoint": "/api/v4/marketing/",
                "query_params": {
                    "include_drafts": True
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["pages", "total"]
                }
            },
        ]
    
    @staticmethod
    def get_admin_list_pages_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for admin list marketing pages endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "admin_list_pages",
                "name": "list_all_pages_default",
                "description": "List all marketing pages with default parameters (includes drafts, excludes deleted)",
                "method": "GET",
                "endpoint": "/api/v4/admin/marketing/",
                "query_params": {},
                "expected_status": [200, 401, 403],  # 401/403 if not admin
                "validate_response": {
                    "has_fields": ["pages", "total"]
                }
            },
            {
                "category": "admin_list_pages",
                "name": "list_all_pages_with_drafts",
                "description": "List all pages including drafts",
                "method": "GET",
                "endpoint": "/api/v4/admin/marketing/",
                "query_params": {
                    "include_drafts": True,
                    "include_deleted": False
                },
                "expected_status": [200, 401, 403],
                "validate_response": {
                    "has_fields": ["pages", "total"]
                }
            },
            {
                "category": "admin_list_pages",
                "name": "list_all_pages_with_deleted",
                "description": "List all pages including deleted",
                "method": "GET",
                "endpoint": "/api/v4/admin/marketing/",
                "query_params": {
                    "include_drafts": True,
                    "include_deleted": True
                },
                "expected_status": [200, 401, 403],
                "validate_response": {
                    "has_fields": ["pages", "total"]
                }
            },
            {
                "category": "admin_list_pages",
                "name": "list_pages_unauthorized",
                "description": "List pages without authentication (should fail)",
                "method": "GET",
                "endpoint": "/api/v4/admin/marketing/",
                "query_params": {},
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
            {
                "category": "admin_list_pages",
                "name": "list_pages_forbidden",
                "description": "List pages as non-admin user (should fail)",
                "method": "GET",
                "endpoint": "/api/v4/admin/marketing/",
                "query_params": {},
                "expected_status": [403],  # Free/Pro users cannot access admin endpoints
            },
        ]
    
    @staticmethod
    def get_admin_get_page_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for admin get marketing page endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "admin_get_page",
                "name": "get_any_page_published",
                "description": "Get published page via admin endpoint",
                "method": "GET",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "query_params": {},
                "expected_status": [200, 404, 401, 403],
                "validate_response": {
                    "has_fields": ["page_id", "metadata", "hero"]
                }
            },
            {
                "category": "admin_get_page",
                "name": "get_any_page_draft",
                "description": "Get draft page via admin endpoint",
                "method": "GET",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "draft-page"
                },
                "query_params": {},
                "expected_status": [200, 404, 401, 403],
            },
            {
                "category": "admin_get_page",
                "name": "get_page_not_found",
                "description": "Get non-existent page via admin endpoint (should fail)",
                "method": "GET",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "non-existent-page"
                },
                "query_params": {},
                "expected_status": [404, 401, 403],
            },
            {
                "category": "admin_get_page",
                "name": "get_page_unauthorized",
                "description": "Get page without authentication (should fail)",
                "method": "GET",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "query_params": {},
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
        ]
    
    @staticmethod
    def get_admin_create_page_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for admin create marketing page endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "admin_create_page",
                "name": "create_page_minimal",
                "description": "Create marketing page with minimal required fields",
                "method": "POST",
                "endpoint": "/api/v4/admin/marketing/",
                "body": {
                    "page_id": "test-page-minimal",
                    "hero": {
                        "title": "Test Hero Title",
                        "description": "Test hero description"
                    }
                },
                "expected_status": [201, 400, 401, 403],
                "validate_response": {
                    "has_fields": ["page_id", "hero"]
                }
            },
            {
                "category": "admin_create_page",
                "name": "create_page_complete",
                "description": "Create marketing page with all fields",
                "method": "POST",
                "endpoint": "/api/v4/admin/marketing/",
                "body": {
                    "page_id": "test-page-complete",
                    "metadata": {
                        "title": "Test Page",
                        "description": "Test page description",
                        "keywords": ["test", "page"],
                        "status": "draft",
                        "version": 1
                    },
                    "hero": {
                        "title": "Test Hero Title",
                        "subtitle": "Test Hero Subtitle",
                        "description": "Test hero description",
                        "features": ["Feature 1", "Feature 2"],
                        "cta_text": "Get Started",
                        "cta_href": "/signup"
                    },
                    "sections": {
                        "section1": {
                            "content": "Section content"
                        }
                    },
                    "hero_stats": [
                        {"key": "stat1", "value": "value1"}
                    ],
                    "hero_table": {
                        "column1": "value1"
                    }
                },
                "expected_status": [201, 400, 401, 403],
                "validate_response": {
                    "has_fields": ["page_id", "metadata", "hero", "sections"]
                }
            },
            {
                "category": "admin_create_page",
                "name": "create_page_with_published_status",
                "description": "Create marketing page with published status",
                "method": "POST",
                "endpoint": "/api/v4/admin/marketing/",
                "body": {
                    "page_id": "test-page-published",
                    "metadata": {
                        "title": "Published Page",
                        "description": "Page description",
                        "status": "published"
                    },
                    "hero": {
                        "title": "Hero Title",
                        "description": "Hero description"
                    }
                },
                "expected_status": [201, 400, 401, 403],
            },
            {
                "category": "admin_create_page",
                "name": "create_page_missing_hero",
                "description": "Create page without required hero field (should fail)",
                "method": "POST",
                "endpoint": "/api/v4/admin/marketing/",
                "body": {
                    "page_id": "test-page-invalid"
                    # Missing hero
                },
                "expected_status": [400, 422],
            },
            {
                "category": "admin_create_page",
                "name": "create_page_missing_page_id",
                "description": "Create page without required page_id (should fail)",
                "method": "POST",
                "endpoint": "/api/v4/admin/marketing/",
                "body": {
                    "hero": {
                        "title": "Hero Title",
                        "description": "Hero description"
                    }
                    # Missing page_id
                },
                "expected_status": [400, 422],
            },
            {
                "category": "admin_create_page",
                "name": "create_page_unauthorized",
                "description": "Create page without authentication (should fail)",
                "method": "POST",
                "endpoint": "/api/v4/admin/marketing/",
                "body": {
                    "page_id": "test-page",
                    "hero": {
                        "title": "Hero Title",
                        "description": "Hero description"
                    }
                },
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
        ]
    
    @staticmethod
    def get_admin_update_page_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for admin update marketing page endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "admin_update_page",
                "name": "update_page_metadata",
                "description": "Update marketing page metadata (partial update)",
                "method": "PUT",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "body": {
                    "metadata": {
                        "title": "Updated Title"
                    }
                },
                "expected_status": [200, 404, 400, 401, 403],
                "validate_response": {
                    "has_fields": ["page_id", "metadata"]
                }
            },
            {
                "category": "admin_update_page",
                "name": "update_page_hero",
                "description": "Update marketing page hero section",
                "method": "PUT",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "body": {
                    "hero": {
                        "subtitle": "Updated Subtitle"
                    }
                },
                "expected_status": [200, 404, 400, 401, 403],
            },
            {
                "category": "admin_update_page",
                "name": "update_page_sections",
                "description": "Update marketing page sections",
                "method": "PUT",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "body": {
                    "sections": {
                        "new_section": {
                            "content": "New section content"
                        }
                    }
                },
                "expected_status": [200, 404, 400, 401, 403],
            },
            {
                "category": "admin_update_page",
                "name": "update_page_multiple_fields",
                "description": "Update multiple fields at once",
                "method": "PUT",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "body": {
                    "metadata": {
                        "title": "Updated Title"
                    },
                    "hero": {
                        "subtitle": "Updated Subtitle"
                    },
                    "sections": {
                        "section1": {
                            "content": "Updated content"
                        }
                    }
                },
                "expected_status": [200, 404, 400, 401, 403],
            },
            {
                "category": "admin_update_page",
                "name": "update_page_not_found",
                "description": "Update non-existent page (should fail)",
                "method": "PUT",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "non-existent-page"
                },
                "body": {
                    "metadata": {
                        "title": "Updated Title"
                    }
                },
                "expected_status": [404, 401, 403],
            },
            {
                "category": "admin_update_page",
                "name": "update_page_unauthorized",
                "description": "Update page without authentication (should fail)",
                "method": "PUT",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "body": {
                    "metadata": {
                        "title": "Updated Title"
                    }
                },
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
        ]
    
    @staticmethod
    def get_admin_delete_page_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for admin delete marketing page endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "admin_delete_page",
                "name": "delete_page_soft",
                "description": "Soft delete marketing page (default)",
                "method": "DELETE",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "query_params": {},
                "expected_status": [204, 404, 401, 403],
            },
            {
                "category": "admin_delete_page",
                "name": "delete_page_hard",
                "description": "Hard delete marketing page (permanent)",
                "method": "DELETE",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "query_params": {
                    "hard_delete": True
                },
                "expected_status": [204, 404, 401, 403],
            },
            {
                "category": "admin_delete_page",
                "name": "delete_page_not_found",
                "description": "Delete non-existent page (should fail)",
                "method": "DELETE",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "non-existent-page"
                },
                "query_params": {},
                "expected_status": [404, 401, 403],
            },
            {
                "category": "admin_delete_page",
                "name": "delete_page_unauthorized",
                "description": "Delete page without authentication (should fail)",
                "method": "DELETE",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "query_params": {},
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
        ]
    
    @staticmethod
    def get_admin_publish_page_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for admin publish marketing page endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "admin_publish_page",
                "name": "publish_draft_page",
                "description": "Publish a draft marketing page",
                "method": "POST",
                "endpoint": "/api/v4/admin/marketing/{page_id}/publish",
                "path_params": {
                    "page_id": "draft-page"
                },
                "query_params": {},
                "expected_status": [200, 404, 400, 401, 403],
                "validate_response": {
                    "has_fields": ["page_id", "metadata"],
                    "metadata_has_status": "published"
                }
            },
            {
                "category": "admin_publish_page",
                "name": "publish_page_not_found",
                "description": "Publish non-existent page (should fail)",
                "method": "POST",
                "endpoint": "/api/v4/admin/marketing/{page_id}/publish",
                "path_params": {
                    "page_id": "non-existent-page"
                },
                "query_params": {},
                "expected_status": [404, 401, 403],
            },
            {
                "category": "admin_publish_page",
                "name": "publish_page_unauthorized",
                "description": "Publish page without authentication (should fail)",
                "method": "POST",
                "endpoint": "/api/v4/admin/marketing/{page_id}/publish",
                "path_params": {
                    "page_id": "draft-page"
                },
                "query_params": {},
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
        ]
    
    @staticmethod
    def get_all_scenarios() -> Dict[str, List[Dict[str, Any]]]:
        """Get all test scenarios organized by category.
        
        Returns:
            Dictionary mapping category names to lists of scenarios
        """
        return {
            "public_get_page": MarketingTestScenarios.get_public_get_page_scenarios(),
            "public_list_pages": MarketingTestScenarios.get_public_list_pages_scenarios(),
            "admin_list_pages": MarketingTestScenarios.get_admin_list_pages_scenarios(),
            "admin_get_page": MarketingTestScenarios.get_admin_get_page_scenarios(),
            "admin_create_page": MarketingTestScenarios.get_admin_create_page_scenarios(),
            "admin_update_page": MarketingTestScenarios.get_admin_update_page_scenarios(),
            "admin_delete_page": MarketingTestScenarios.get_admin_delete_page_scenarios(),
            "admin_publish_page": MarketingTestScenarios.get_admin_publish_page_scenarios(),
        }


This module defines all test scenarios for the Marketing API,
covering public and admin endpoints for marketing pages.
"""

from typing import Dict, List, Any


class MarketingTestScenarios:
    """Comprehensive test scenarios for Marketing API endpoints."""
    
    @staticmethod
    def get_public_get_page_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for public get marketing page endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "public_get_page",
                "name": "get_published_page_public",
                "description": "Get published marketing page without authentication",
                "method": "GET",
                "endpoint": "/api/v4/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "query_params": {},
                "headers": {},  # No Authorization header
                "expected_status": [200, 404],  # 404 if page doesn't exist
                "validate_response": {
                    "has_fields": ["page_id", "metadata", "hero"],
                    "metadata_has_status": "published"
                }
            },
            {
                "category": "public_get_page",
                "name": "get_published_page_authenticated",
                "description": "Get published marketing page with authentication",
                "method": "GET",
                "endpoint": "/api/v4/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "query_params": {},
                "expected_status": [200, 404],
                "validate_response": {
                    "has_fields": ["page_id", "metadata", "hero"],
                    "metadata_has_status": "published"
                }
            },
            {
                "category": "public_get_page",
                "name": "get_page_not_found",
                "description": "Get non-existent marketing page (should fail)",
                "method": "GET",
                "endpoint": "/api/v4/marketing/{page_id}",
                "path_params": {
                    "page_id": "non-existent-page"
                },
                "query_params": {},
                "expected_status": [404],
            },
            {
                "category": "public_get_page",
                "name": "get_draft_page_public",
                "description": "Get draft page via public endpoint (should fail - only published pages)",
                "method": "GET",
                "endpoint": "/api/v4/marketing/{page_id}",
                "path_params": {
                    "page_id": "draft-page"
                },
                "query_params": {},
                "expected_status": [404],  # Draft pages not accessible via public endpoint
            },
        ]
    
    @staticmethod
    def get_public_list_pages_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for public list marketing pages endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "public_list_pages",
                "name": "list_published_pages",
                "description": "List all published marketing pages",
                "method": "GET",
                "endpoint": "/api/v4/marketing/",
                "query_params": {},
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["pages", "total"],
                    "pages_is_list": True,
                    "total_is_int": True
                }
            },
            {
                "category": "public_list_pages",
                "name": "list_pages_with_include_drafts",
                "description": "List pages with include_drafts parameter (ignored for public endpoint)",
                "method": "GET",
                "endpoint": "/api/v4/marketing/",
                "query_params": {
                    "include_drafts": True
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["pages", "total"]
                }
            },
        ]
    
    @staticmethod
    def get_admin_list_pages_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for admin list marketing pages endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "admin_list_pages",
                "name": "list_all_pages_default",
                "description": "List all marketing pages with default parameters (includes drafts, excludes deleted)",
                "method": "GET",
                "endpoint": "/api/v4/admin/marketing/",
                "query_params": {},
                "expected_status": [200, 401, 403],  # 401/403 if not admin
                "validate_response": {
                    "has_fields": ["pages", "total"]
                }
            },
            {
                "category": "admin_list_pages",
                "name": "list_all_pages_with_drafts",
                "description": "List all pages including drafts",
                "method": "GET",
                "endpoint": "/api/v4/admin/marketing/",
                "query_params": {
                    "include_drafts": True,
                    "include_deleted": False
                },
                "expected_status": [200, 401, 403],
                "validate_response": {
                    "has_fields": ["pages", "total"]
                }
            },
            {
                "category": "admin_list_pages",
                "name": "list_all_pages_with_deleted",
                "description": "List all pages including deleted",
                "method": "GET",
                "endpoint": "/api/v4/admin/marketing/",
                "query_params": {
                    "include_drafts": True,
                    "include_deleted": True
                },
                "expected_status": [200, 401, 403],
                "validate_response": {
                    "has_fields": ["pages", "total"]
                }
            },
            {
                "category": "admin_list_pages",
                "name": "list_pages_unauthorized",
                "description": "List pages without authentication (should fail)",
                "method": "GET",
                "endpoint": "/api/v4/admin/marketing/",
                "query_params": {},
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
            {
                "category": "admin_list_pages",
                "name": "list_pages_forbidden",
                "description": "List pages as non-admin user (should fail)",
                "method": "GET",
                "endpoint": "/api/v4/admin/marketing/",
                "query_params": {},
                "expected_status": [403],  # Free/Pro users cannot access admin endpoints
            },
        ]
    
    @staticmethod
    def get_admin_get_page_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for admin get marketing page endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "admin_get_page",
                "name": "get_any_page_published",
                "description": "Get published page via admin endpoint",
                "method": "GET",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "query_params": {},
                "expected_status": [200, 404, 401, 403],
                "validate_response": {
                    "has_fields": ["page_id", "metadata", "hero"]
                }
            },
            {
                "category": "admin_get_page",
                "name": "get_any_page_draft",
                "description": "Get draft page via admin endpoint",
                "method": "GET",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "draft-page"
                },
                "query_params": {},
                "expected_status": [200, 404, 401, 403],
            },
            {
                "category": "admin_get_page",
                "name": "get_page_not_found",
                "description": "Get non-existent page via admin endpoint (should fail)",
                "method": "GET",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "non-existent-page"
                },
                "query_params": {},
                "expected_status": [404, 401, 403],
            },
            {
                "category": "admin_get_page",
                "name": "get_page_unauthorized",
                "description": "Get page without authentication (should fail)",
                "method": "GET",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "query_params": {},
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
        ]
    
    @staticmethod
    def get_admin_create_page_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for admin create marketing page endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "admin_create_page",
                "name": "create_page_minimal",
                "description": "Create marketing page with minimal required fields",
                "method": "POST",
                "endpoint": "/api/v4/admin/marketing/",
                "body": {
                    "page_id": "test-page-minimal",
                    "hero": {
                        "title": "Test Hero Title",
                        "description": "Test hero description"
                    }
                },
                "expected_status": [201, 400, 401, 403],
                "validate_response": {
                    "has_fields": ["page_id", "hero"]
                }
            },
            {
                "category": "admin_create_page",
                "name": "create_page_complete",
                "description": "Create marketing page with all fields",
                "method": "POST",
                "endpoint": "/api/v4/admin/marketing/",
                "body": {
                    "page_id": "test-page-complete",
                    "metadata": {
                        "title": "Test Page",
                        "description": "Test page description",
                        "keywords": ["test", "page"],
                        "status": "draft",
                        "version": 1
                    },
                    "hero": {
                        "title": "Test Hero Title",
                        "subtitle": "Test Hero Subtitle",
                        "description": "Test hero description",
                        "features": ["Feature 1", "Feature 2"],
                        "cta_text": "Get Started",
                        "cta_href": "/signup"
                    },
                    "sections": {
                        "section1": {
                            "content": "Section content"
                        }
                    },
                    "hero_stats": [
                        {"key": "stat1", "value": "value1"}
                    ],
                    "hero_table": {
                        "column1": "value1"
                    }
                },
                "expected_status": [201, 400, 401, 403],
                "validate_response": {
                    "has_fields": ["page_id", "metadata", "hero", "sections"]
                }
            },
            {
                "category": "admin_create_page",
                "name": "create_page_with_published_status",
                "description": "Create marketing page with published status",
                "method": "POST",
                "endpoint": "/api/v4/admin/marketing/",
                "body": {
                    "page_id": "test-page-published",
                    "metadata": {
                        "title": "Published Page",
                        "description": "Page description",
                        "status": "published"
                    },
                    "hero": {
                        "title": "Hero Title",
                        "description": "Hero description"
                    }
                },
                "expected_status": [201, 400, 401, 403],
            },
            {
                "category": "admin_create_page",
                "name": "create_page_missing_hero",
                "description": "Create page without required hero field (should fail)",
                "method": "POST",
                "endpoint": "/api/v4/admin/marketing/",
                "body": {
                    "page_id": "test-page-invalid"
                    # Missing hero
                },
                "expected_status": [400, 422],
            },
            {
                "category": "admin_create_page",
                "name": "create_page_missing_page_id",
                "description": "Create page without required page_id (should fail)",
                "method": "POST",
                "endpoint": "/api/v4/admin/marketing/",
                "body": {
                    "hero": {
                        "title": "Hero Title",
                        "description": "Hero description"
                    }
                    # Missing page_id
                },
                "expected_status": [400, 422],
            },
            {
                "category": "admin_create_page",
                "name": "create_page_unauthorized",
                "description": "Create page without authentication (should fail)",
                "method": "POST",
                "endpoint": "/api/v4/admin/marketing/",
                "body": {
                    "page_id": "test-page",
                    "hero": {
                        "title": "Hero Title",
                        "description": "Hero description"
                    }
                },
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
        ]
    
    @staticmethod
    def get_admin_update_page_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for admin update marketing page endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "admin_update_page",
                "name": "update_page_metadata",
                "description": "Update marketing page metadata (partial update)",
                "method": "PUT",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "body": {
                    "metadata": {
                        "title": "Updated Title"
                    }
                },
                "expected_status": [200, 404, 400, 401, 403],
                "validate_response": {
                    "has_fields": ["page_id", "metadata"]
                }
            },
            {
                "category": "admin_update_page",
                "name": "update_page_hero",
                "description": "Update marketing page hero section",
                "method": "PUT",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "body": {
                    "hero": {
                        "subtitle": "Updated Subtitle"
                    }
                },
                "expected_status": [200, 404, 400, 401, 403],
            },
            {
                "category": "admin_update_page",
                "name": "update_page_sections",
                "description": "Update marketing page sections",
                "method": "PUT",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "body": {
                    "sections": {
                        "new_section": {
                            "content": "New section content"
                        }
                    }
                },
                "expected_status": [200, 404, 400, 401, 403],
            },
            {
                "category": "admin_update_page",
                "name": "update_page_multiple_fields",
                "description": "Update multiple fields at once",
                "method": "PUT",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "body": {
                    "metadata": {
                        "title": "Updated Title"
                    },
                    "hero": {
                        "subtitle": "Updated Subtitle"
                    },
                    "sections": {
                        "section1": {
                            "content": "Updated content"
                        }
                    }
                },
                "expected_status": [200, 404, 400, 401, 403],
            },
            {
                "category": "admin_update_page",
                "name": "update_page_not_found",
                "description": "Update non-existent page (should fail)",
                "method": "PUT",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "non-existent-page"
                },
                "body": {
                    "metadata": {
                        "title": "Updated Title"
                    }
                },
                "expected_status": [404, 401, 403],
            },
            {
                "category": "admin_update_page",
                "name": "update_page_unauthorized",
                "description": "Update page without authentication (should fail)",
                "method": "PUT",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "body": {
                    "metadata": {
                        "title": "Updated Title"
                    }
                },
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
        ]
    
    @staticmethod
    def get_admin_delete_page_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for admin delete marketing page endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "admin_delete_page",
                "name": "delete_page_soft",
                "description": "Soft delete marketing page (default)",
                "method": "DELETE",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "query_params": {},
                "expected_status": [204, 404, 401, 403],
            },
            {
                "category": "admin_delete_page",
                "name": "delete_page_hard",
                "description": "Hard delete marketing page (permanent)",
                "method": "DELETE",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "query_params": {
                    "hard_delete": True
                },
                "expected_status": [204, 404, 401, 403],
            },
            {
                "category": "admin_delete_page",
                "name": "delete_page_not_found",
                "description": "Delete non-existent page (should fail)",
                "method": "DELETE",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "non-existent-page"
                },
                "query_params": {},
                "expected_status": [404, 401, 403],
            },
            {
                "category": "admin_delete_page",
                "name": "delete_page_unauthorized",
                "description": "Delete page without authentication (should fail)",
                "method": "DELETE",
                "endpoint": "/api/v4/admin/marketing/{page_id}",
                "path_params": {
                    "page_id": "example-page"
                },
                "query_params": {},
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
        ]
    
    @staticmethod
    def get_admin_publish_page_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for admin publish marketing page endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "admin_publish_page",
                "name": "publish_draft_page",
                "description": "Publish a draft marketing page",
                "method": "POST",
                "endpoint": "/api/v4/admin/marketing/{page_id}/publish",
                "path_params": {
                    "page_id": "draft-page"
                },
                "query_params": {},
                "expected_status": [200, 404, 400, 401, 403],
                "validate_response": {
                    "has_fields": ["page_id", "metadata"],
                    "metadata_has_status": "published"
                }
            },
            {
                "category": "admin_publish_page",
                "name": "publish_page_not_found",
                "description": "Publish non-existent page (should fail)",
                "method": "POST",
                "endpoint": "/api/v4/admin/marketing/{page_id}/publish",
                "path_params": {
                    "page_id": "non-existent-page"
                },
                "query_params": {},
                "expected_status": [404, 401, 403],
            },
            {
                "category": "admin_publish_page",
                "name": "publish_page_unauthorized",
                "description": "Publish page without authentication (should fail)",
                "method": "POST",
                "endpoint": "/api/v4/admin/marketing/{page_id}/publish",
                "path_params": {
                    "page_id": "draft-page"
                },
                "query_params": {},
                "headers": {},  # No Authorization header
                "expected_status": [401],
            },
        ]
    
    @staticmethod
    def get_all_scenarios() -> Dict[str, List[Dict[str, Any]]]:
        """Get all test scenarios organized by category.
        
        Returns:
            Dictionary mapping category names to lists of scenarios
        """
        return {
            "public_get_page": MarketingTestScenarios.get_public_get_page_scenarios(),
            "public_list_pages": MarketingTestScenarios.get_public_list_pages_scenarios(),
            "admin_list_pages": MarketingTestScenarios.get_admin_list_pages_scenarios(),
            "admin_get_page": MarketingTestScenarios.get_admin_get_page_scenarios(),
            "admin_create_page": MarketingTestScenarios.get_admin_create_page_scenarios(),
            "admin_update_page": MarketingTestScenarios.get_admin_update_page_scenarios(),
            "admin_delete_page": MarketingTestScenarios.get_admin_delete_page_scenarios(),
            "admin_publish_page": MarketingTestScenarios.get_admin_publish_page_scenarios(),
        }

