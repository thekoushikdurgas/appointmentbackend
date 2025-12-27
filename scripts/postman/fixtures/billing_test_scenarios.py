"""Comprehensive test scenarios for Billing API endpoints.

This module defines all test scenarios for the Billing API,
covering subscription plans, addons, invoices, and admin operations.
"""

from typing import Dict, List, Any


class BillingTestScenarios:
    """Comprehensive test scenarios for Billing API endpoints."""
    
    @staticmethod
    def get_billing_info_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for billing info endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "billing_info",
                "name": "get_billing_info",
                "description": "Get billing information for current user",
                "method": "GET",
                "endpoint": "/api/v1/billing/",
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["credits", "credits_used", "credits_limit", "subscription_plan", "subscription_status", "usage_percentage"]
                }
            },
            {
                "category": "billing_info_errors",
                "name": "get_billing_info_unauthorized",
                "description": "Get billing info without authentication (should fail)",
                "method": "GET",
                "endpoint": "/api/v1/billing/",
                "requires_auth": False,
                "expected_status": [401],
                "validate_response": {
                    "has_field": "detail"
                }
            }
        ]
    
    @staticmethod
    def get_plans_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for plans endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "plans",
                "name": "get_subscription_plans",
                "description": "Get all available subscription plans (public endpoint)",
                "method": "GET",
                "endpoint": "/api/v1/billing/plans/",
                "requires_auth": False,
                "expected_status": [200],
                "validate_response": {
                    "has_field": "plans",
                    "plans_is_list": True
                }
            }
        ]
    
    @staticmethod
    def get_addons_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for addons endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "addons",
                "name": "get_addon_packages",
                "description": "Get all available addon packages (public endpoint)",
                "method": "GET",
                "endpoint": "/api/v1/billing/addons/",
                "requires_auth": False,
                "expected_status": [200],
                "validate_response": {
                    "has_field": "packages",
                    "packages_is_list": True
                }
            }
        ]
    
    @staticmethod
    def get_subscribe_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for subscribe endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        scenarios = []
        
        # Valid subscription scenarios
        valid_tiers = ["5k", "25k", "100k", "500k", "1M", "5M", "10M"]
        valid_periods = ["monthly", "quarterly", "yearly"]
        
        for tier in valid_tiers[:3]:  # Test a subset for efficiency
            for period in valid_periods:
                scenarios.append({
                    "category": "subscribe",
                    "name": f"subscribe_{tier}_{period}",
                    "description": f"Subscribe to {tier} tier with {period} period",
                    "method": "POST",
                    "endpoint": "/api/v1/billing/subscribe/",
                    "body": {
                        "tier": tier,
                        "period": period
                    },
                    "expected_status": [200],
                    "validate_response": {
                        "has_fields": ["message", "subscription_plan", "subscription_period", "credits"]
                    }
                })
        
        # Error scenarios
        scenarios.extend([
            {
                "category": "subscribe_errors",
                "name": "subscribe_invalid_tier",
                "description": "Subscribe with invalid tier (should fail)",
                "method": "POST",
                "endpoint": "/api/v1/billing/subscribe/",
                "body": {
                    "tier": "invalid_tier",
                    "period": "monthly"
                },
                "expected_status": [400],
                "validate_response": {
                    "has_field": "detail"
                }
            },
            {
                "category": "subscribe_errors",
                "name": "subscribe_invalid_period",
                "description": "Subscribe with invalid period (should fail)",
                "method": "POST",
                "endpoint": "/api/v1/billing/subscribe/",
                "body": {
                    "tier": "5k",
                    "period": "invalid_period"
                },
                "expected_status": [400],
                "validate_response": {
                    "has_field": "detail"
                }
            },
            {
                "category": "subscribe_errors",
                "name": "subscribe_missing_tier",
                "description": "Subscribe with missing tier (should fail)",
                "method": "POST",
                "endpoint": "/api/v1/billing/subscribe/",
                "body": {
                    "period": "monthly"
                },
                "expected_status": [422],
                "validate_response": {
                    "has_field": "detail"
                }
            },
            {
                "category": "subscribe_errors",
                "name": "subscribe_missing_period",
                "description": "Subscribe with missing period (should fail)",
                "method": "POST",
                "endpoint": "/api/v1/billing/subscribe/",
                "body": {
                    "tier": "5k"
                },
                "expected_status": [422],
                "validate_response": {
                    "has_field": "detail"
                }
            },
            {
                "category": "subscribe_errors",
                "name": "subscribe_unauthorized",
                "description": "Subscribe without authentication (should fail)",
                "method": "POST",
                "endpoint": "/api/v1/billing/subscribe/",
                "body": {
                    "tier": "5k",
                    "period": "monthly"
                },
                "requires_auth": False,
                "expected_status": [401],
                "validate_response": {
                    "has_field": "detail"
                }
            }
        ])
        
        return scenarios
    
    @staticmethod
    def get_addon_purchase_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for addon purchase endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        scenarios = []
        
        # Valid addon purchase scenarios
        valid_packages = ["small", "basic", "standard", "plus", "pro", "advanced", "premium"]
        
        for package_id in valid_packages[:3]:  # Test a subset for efficiency
            scenarios.append({
                "category": "addon_purchase",
                "name": f"purchase_addon_{package_id}",
                "description": f"Purchase {package_id} addon package",
                "method": "POST",
                "endpoint": "/api/v1/billing/addon/",
                "body": {
                    "package_id": package_id
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["message", "package", "credits_added", "total_credits"]
                }
            })
        
        # Error scenarios
        scenarios.extend([
            {
                "category": "addon_purchase_errors",
                "name": "purchase_addon_invalid_package",
                "description": "Purchase addon with invalid package_id (should fail)",
                "method": "POST",
                "endpoint": "/api/v1/billing/addon/",
                "body": {
                    "package_id": "invalid_package"
                },
                "expected_status": [400],
                "validate_response": {
                    "has_field": "detail"
                }
            },
            {
                "category": "addon_purchase_errors",
                "name": "purchase_addon_missing_package_id",
                "description": "Purchase addon with missing package_id (should fail)",
                "method": "POST",
                "endpoint": "/api/v1/billing/addon/",
                "body": {},
                "expected_status": [422],
                "validate_response": {
                    "has_field": "detail"
                }
            },
            {
                "category": "addon_purchase_errors",
                "name": "purchase_addon_unauthorized",
                "description": "Purchase addon without authentication (should fail)",
                "method": "POST",
                "endpoint": "/api/v1/billing/addon/",
                "body": {
                    "package_id": "small"
                },
                "requires_auth": False,
                "expected_status": [401],
                "validate_response": {
                    "has_field": "detail"
                }
            }
        ])
        
        return scenarios
    
    @staticmethod
    def get_cancel_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for cancel subscription endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "cancel",
                "name": "cancel_subscription",
                "description": "Cancel current subscription",
                "method": "POST",
                "endpoint": "/api/v1/billing/cancel/",
                "expected_status": [200, 400],  # 400 if already cancelled
                "validate_response": {
                    "has_fields": ["message", "subscription_status"]
                }
            },
            {
                "category": "cancel_errors",
                "name": "cancel_subscription_unauthorized",
                "description": "Cancel subscription without authentication (should fail)",
                "method": "POST",
                "endpoint": "/api/v1/billing/cancel/",
                "requires_auth": False,
                "expected_status": [401],
                "validate_response": {
                    "has_field": "detail"
                }
            }
        ]
    
    @staticmethod
    def get_invoices_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for invoices endpoint.
        
        Returns:
            List of test scenario dictionaries
        """
        return [
            {
                "category": "invoices",
                "name": "get_invoices_default",
                "description": "Get invoices with default pagination",
                "method": "GET",
                "endpoint": "/api/v1/billing/invoices/",
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["invoices", "total"],
                    "invoices_is_list": True
                }
            },
            {
                "category": "invoices",
                "name": "get_invoices_with_pagination",
                "description": "Get invoices with custom pagination",
                "method": "GET",
                "endpoint": "/api/v1/billing/invoices/",
                "query_params": {
                    "limit": 20,
                    "offset": 0
                },
                "expected_status": [200],
                "validate_response": {
                    "has_fields": ["invoices", "total"]
                }
            },
            {
                "category": "invoices_errors",
                "name": "get_invoices_invalid_limit",
                "description": "Get invoices with invalid limit (should fail)",
                "method": "GET",
                "endpoint": "/api/v1/billing/invoices/",
                "query_params": {
                    "limit": 0
                },
                "expected_status": [422],
                "validate_response": {
                    "has_field": "detail"
                }
            },
            {
                "category": "invoices_errors",
                "name": "get_invoices_unauthorized",
                "description": "Get invoices without authentication (should fail)",
                "method": "GET",
                "endpoint": "/api/v1/billing/invoices/",
                "requires_auth": False,
                "expected_status": [401],
                "validate_response": {
                    "has_field": "detail"
                }
            }
        ]
    
    @staticmethod
    def get_admin_scenarios() -> List[Dict[str, Any]]:
        """Get test scenarios for admin endpoints (SuperAdmin only).
        
        Returns:
            List of test scenario dictionaries
        """
        scenarios = []
        
        # Admin plans endpoints
        scenarios.extend([
            {
                "category": "admin_plans",
                "name": "admin_get_plans",
                "description": "Get all subscription plans (admin)",
                "method": "GET",
                "endpoint": "/api/v1/billing/admin/plans/",
                "requires_admin": True,
                "expected_status": [200],
                "validate_response": {
                    "has_field": "plans"
                }
            },
            {
                "category": "admin_plans",
                "name": "admin_get_plans_include_inactive",
                "description": "Get all subscription plans including inactive (admin)",
                "method": "GET",
                "endpoint": "/api/v1/billing/admin/plans/",
                "query_params": {
                    "include_inactive": True
                },
                "requires_admin": True,
                "expected_status": [200]
            },
            {
                "category": "admin_plans",
                "name": "admin_create_plan",
                "description": "Create a new subscription plan (admin)",
                "method": "POST",
                "endpoint": "/api/v1/billing/admin/plans/",
                "body": {
                    "tier": "test-tier",
                    "name": "Test Plan",
                    "category": "STARTER",
                    "periods": [
                        {
                            "period": "monthly",
                            "credits": 5000,
                            "rate_per_credit": 0.002,
                            "price": 10.0
                        }
                    ]
                },
                "requires_admin": True,
                "expected_status": [201],
                "validate_response": {
                    "has_fields": ["message", "tier"]
                }
            },
            {
                "category": "admin_plans",
                "name": "admin_update_plan",
                "description": "Update a subscription plan (admin)",
                "method": "PUT",
                "endpoint": "/api/v1/billing/admin/plans/{tier}/",
                "path_params": {
                    "tier": "5k"
                },
                "body": {
                    "name": "Updated Plan Name"
                },
                "requires_admin": True,
                "expected_status": [200]
            },
            {
                "category": "admin_plans",
                "name": "admin_delete_plan",
                "description": "Delete a subscription plan (admin)",
                "method": "DELETE",
                "endpoint": "/api/v1/billing/admin/plans/{tier}/",
                "path_params": {
                    "tier": "test-tier"
                },
                "requires_admin": True,
                "expected_status": [200]
            },
            {
                "category": "admin_plans",
                "name": "admin_create_plan_period",
                "description": "Create/update a plan period (admin)",
                "method": "POST",
                "endpoint": "/api/v1/billing/admin/plans/{tier}/periods/",
                "path_params": {
                    "tier": "5k"
                },
                "body": {
                    "period": "monthly",
                    "credits": 5000,
                    "rate_per_credit": 0.002,
                    "price": 10.0
                },
                "requires_admin": True,
                "expected_status": [200]
            },
            {
                "category": "admin_plans",
                "name": "admin_delete_plan_period",
                "description": "Delete a plan period (admin)",
                "method": "DELETE",
                "endpoint": "/api/v1/billing/admin/plans/{tier}/periods/{period}/",
                "path_params": {
                    "tier": "5k",
                    "period": "monthly"
                },
                "requires_admin": True,
                "expected_status": [200]
            }
        ])
        
        # Admin addons endpoints
        scenarios.extend([
            {
                "category": "admin_addons",
                "name": "admin_get_addons",
                "description": "Get all addon packages (admin)",
                "method": "GET",
                "endpoint": "/api/v1/billing/admin/addons/",
                "requires_admin": True,
                "expected_status": [200],
                "validate_response": {
                    "has_field": "packages"
                }
            },
            {
                "category": "admin_addons",
                "name": "admin_create_addon",
                "description": "Create a new addon package (admin)",
                "method": "POST",
                "endpoint": "/api/v1/billing/admin/addons/",
                "body": {
                    "id": "test-package",
                    "name": "Test Package",
                    "credits": 5000,
                    "rate_per_credit": 0.002,
                    "price": 10.0
                },
                "requires_admin": True,
                "expected_status": [201]
            },
            {
                "category": "admin_addons",
                "name": "admin_update_addon",
                "description": "Update an addon package (admin)",
                "method": "PUT",
                "endpoint": "/api/v1/billing/admin/addons/{package_id}/",
                "path_params": {
                    "package_id": "small"
                },
                "body": {
                    "name": "Updated Package Name"
                },
                "requires_admin": True,
                "expected_status": [200]
            },
            {
                "category": "admin_addons",
                "name": "admin_delete_addon",
                "description": "Delete an addon package (admin)",
                "method": "DELETE",
                "endpoint": "/api/v1/billing/admin/addons/{package_id}/",
                "path_params": {
                    "package_id": "test-package"
                },
                "requires_admin": True,
                "expected_status": [200]
            }
        ])
        
        return scenarios
    
    @staticmethod
    def get_all_scenarios() -> List[Dict[str, Any]]:
        """Get all test scenarios for Billing API.
        
        Returns:
            List of all test scenario dictionaries
        """
        scenarios = []
        scenarios.extend(BillingTestScenarios.get_billing_info_scenarios())
        scenarios.extend(BillingTestScenarios.get_plans_scenarios())
        scenarios.extend(BillingTestScenarios.get_addons_scenarios())
        scenarios.extend(BillingTestScenarios.get_subscribe_scenarios())
        scenarios.extend(BillingTestScenarios.get_addon_purchase_scenarios())
        scenarios.extend(BillingTestScenarios.get_cancel_scenarios())
        scenarios.extend(BillingTestScenarios.get_invoices_scenarios())
        scenarios.extend(BillingTestScenarios.get_admin_scenarios())
        return scenarios

