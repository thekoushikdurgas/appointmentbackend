"""Seed script to populate MongoDB with dashboard page access control."""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.clients.mongodb import get_mongodb_database, close_mongodb_connection
from app.repositories.dashboard_repository import DashboardRepository


async def seed_finder_page(repo: DashboardRepository):
    """Seed Email Finder page."""
    data = {
        "page_id": "finder",
        "metadata": {
            "title": "Email Finder",
            "description": "Find professional email addresses in seconds",
            "route": "/finder",
            "last_updated": datetime.utcnow(),
            "version": 1,
        },
        "access_control": {
            "allowed_roles": ["FreeUser", "ProUser", "Admin", "SuperAdmin"],
            "restriction_type": "none",
            "redirect_path": "/billing",
            "redirect_message": "Upgrade to access Email Finder",
        },
        "sections": {
            "single_search": {
                "access_control": {
                    "allowed_roles": ["FreeUser", "ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "none",
                },
                "components": {
                    "search_form": {
                        "access_control": {
                            "allowed_roles": ["FreeUser", "ProUser", "Admin", "SuperAdmin"],
                        },
                    },
                    "advanced_options": {
                        "access_control": {
                            "allowed_roles": ["ProUser", "Admin", "SuperAdmin"],
                            "restriction_type": "hidden",
                            "redirect_path": "/billing",
                            "redirect_message": "Upgrade to Pro for advanced search options",
                        },
                    },
                },
            },
            "bulk_upload": {
                "access_control": {
                    "allowed_roles": ["ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "full",
                    "redirect_path": "/billing",
                    "redirect_message": "Upgrade to Pro to use bulk email finder",
                },
            },
            "history": {
                "access_control": {
                    "allowed_roles": ["FreeUser", "ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "none",
                },
            },
        },
    }
    
    existing = await repo.get_by_page_id(data["page_id"])
    if existing:
        await repo.update_page_content(data["page_id"], data)
        print("✓ Updated Finder page")
    else:
        await repo.create_page_content(data)
        print("✓ Seeded Finder page")


async def seed_verifier_page(repo: DashboardRepository):
    """Seed Email Verifier page."""
    data = {
        "page_id": "verifier",
        "metadata": {
            "title": "Email Verifier",
            "description": "Verify email addresses and check deliverability",
            "route": "/verifier",
            "last_updated": datetime.utcnow(),
            "version": 1,
        },
        "access_control": {
            "allowed_roles": ["FreeUser", "ProUser", "Admin", "SuperAdmin"],
            "restriction_type": "none",
            "redirect_path": "/billing",
        },
        "sections": {
            "bulk_tab": {
                "access_control": {
                    "allowed_roles": ["ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "full",
                    "redirect_path": "/billing",
                    "redirect_message": "Upgrade to Pro for bulk verification",
                },
            },
            "email_tab": {
                "access_control": {
                    "allowed_roles": ["FreeUser", "ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "none",
                },
            },
            "management_tab": {
                "access_control": {
                    "allowed_roles": ["ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "full",
                    "redirect_path": "/billing",
                    "redirect_message": "Upgrade to Pro for verification management",
                },
            },
            "history_tab": {
                "access_control": {
                    "allowed_roles": ["FreeUser", "ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "none",
                },
            },
        },
    }
    
    existing = await repo.get_by_page_id(data["page_id"])
    if existing:
        await repo.update_page_content(data["page_id"], data)
        print("✓ Updated Verifier page")
    else:
        await repo.create_page_content(data)
        print("✓ Seeded Verifier page")


async def seed_ai_chat_page(repo: DashboardRepository):
    """Seed AI Chat page."""
    data = {
        "page_id": "ai-chat",
        "metadata": {
            "title": "AI Chat",
            "description": "Chat with AI to get insights about your contacts",
            "route": "/ai-chat",
            "last_updated": datetime.utcnow(),
            "version": 1,
        },
        "access_control": {
            "allowed_roles": ["ProUser", "Admin", "SuperAdmin"],
            "restriction_type": "full",
            "redirect_path": "/billing",
            "redirect_message": "Upgrade to Pro to access AI Chat",
        },
        "sections": {
            "chat_sidebar": {
                "access_control": {
                    "allowed_roles": ["ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "none",
                },
            },
            "chat_messages": {
                "access_control": {
                    "allowed_roles": ["ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "none",
                },
            },
            "chat_input": {
                "access_control": {
                    "allowed_roles": ["ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "none",
                },
            },
            "model_selector": {
                "access_control": {
                    "allowed_roles": ["ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "none",
                },
            },
        },
    }
    
    existing = await repo.get_by_page_id(data["page_id"])
    if existing:
        await repo.update_page_content(data["page_id"], data)
        print("✓ Updated AI Chat page")
    else:
        await repo.create_page_content(data)
        print("✓ Seeded AI Chat page")


async def seed_linkedin_page(repo: DashboardRepository):
    """Seed LinkedIn page."""
    data = {
        "page_id": "linkedin",
        "metadata": {
            "title": "LinkedIn Search",
            "description": "Search and enrich LinkedIn profiles",
            "route": "/linkedin",
            "last_updated": datetime.utcnow(),
            "version": 1,
        },
        "access_control": {
            "allowed_roles": ["FreeUser", "ProUser", "Admin", "SuperAdmin"],
            "restriction_type": "none",
            "redirect_path": "/billing",
        },
        "sections": {
            "search_tab": {
                "access_control": {
                    "allowed_roles": ["FreeUser", "ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "none",
                },
            },
            "paste_tab": {
                "access_control": {
                    "allowed_roles": ["FreeUser", "ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "none",
                },
            },
            "upload_tab": {
                "access_control": {
                    "allowed_roles": ["ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "full",
                    "redirect_path": "/billing",
                    "redirect_message": "Upgrade to Pro for bulk LinkedIn upload",
                },
            },
            "advanced_filters": {
                "access_control": {
                    "allowed_roles": ["ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "hidden",
                    "redirect_path": "/billing",
                    "redirect_message": "Upgrade to Pro for advanced LinkedIn filters",
                },
            },
        },
    }
    
    existing = await repo.get_by_page_id(data["page_id"])
    if existing:
        await repo.update_page_content(data["page_id"], data)
        print("✓ Updated LinkedIn page")
    else:
        await repo.create_page_content(data)
        print("✓ Seeded LinkedIn page")


async def seed_export_page(repo: DashboardRepository):
    """Seed Export page."""
    data = {
        "page_id": "export",
        "metadata": {
            "title": "Exports",
            "description": "Manage your data exports",
            "route": "/export",
            "last_updated": datetime.utcnow(),
            "version": 1,
        },
        "access_control": {
            "allowed_roles": ["ProUser", "Admin", "SuperAdmin"],
            "restriction_type": "full",
            "redirect_path": "/billing",
            "redirect_message": "Upgrade to Pro to access exports",
        },
        "sections": {
            "export_list": {
                "access_control": {
                    "allowed_roles": ["ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "none",
                },
            },
            "export_filters": {
                "access_control": {
                    "allowed_roles": ["ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "none",
                },
            },
        },
    }
    
    existing = await repo.get_by_page_id(data["page_id"])
    if existing:
        await repo.update_page_content(data["page_id"], data)
        print("✓ Updated Export page")
    else:
        await repo.create_page_content(data)
        print("✓ Seeded Export page")


async def seed_contacts_page(repo: DashboardRepository):
    """Seed Contacts page."""
    data = {
        "page_id": "contacts",
        "metadata": {
            "title": "Contacts",
            "description": "Manage your contact database",
            "route": "/contacts",
            "last_updated": datetime.utcnow(),
            "version": 1,
        },
        "access_control": {
            "allowed_roles": ["FreeUser", "ProUser", "Admin", "SuperAdmin"],
            "restriction_type": "none",
            "redirect_path": "/billing",
        },
        "sections": {
            "contacts_table": {
                "access_control": {
                    "allowed_roles": ["FreeUser", "ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "none",
                },
            },
            "advanced_filters": {
                "access_control": {
                    "allowed_roles": ["ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "hidden",
                    "redirect_path": "/billing",
                    "redirect_message": "Upgrade to Pro for advanced contact filters",
                },
            },
            "bulk_import": {
                "access_control": {
                    "allowed_roles": ["ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "full",
                    "redirect_path": "/billing",
                    "redirect_message": "Upgrade to Pro for bulk contact import",
                },
            },
            "export": {
                "access_control": {
                    "allowed_roles": ["ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "full",
                    "redirect_path": "/billing",
                    "redirect_message": "Upgrade to Pro to export contacts",
                },
            },
        },
    }
    
    existing = await repo.get_by_page_id(data["page_id"])
    if existing:
        await repo.update_page_content(data["page_id"], data)
        print("✓ Updated Contacts page")
    else:
        await repo.create_page_content(data)
        print("✓ Seeded Contacts page")


async def seed_companies_page(repo: DashboardRepository):
    """Seed Companies page."""
    data = {
        "page_id": "companies",
        "metadata": {
            "title": "Companies",
            "description": "Manage your company database",
            "route": "/companies",
            "last_updated": datetime.utcnow(),
            "version": 1,
        },
        "access_control": {
            "allowed_roles": ["FreeUser", "ProUser", "Admin", "SuperAdmin"],
            "restriction_type": "none",
            "redirect_path": "/billing",
        },
        "sections": {
            "companies_table": {
                "access_control": {
                    "allowed_roles": ["FreeUser", "ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "none",
                },
            },
            "advanced_filters": {
                "access_control": {
                    "allowed_roles": ["ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "hidden",
                    "redirect_path": "/billing",
                    "redirect_message": "Upgrade to Pro for advanced company filters",
                },
            },
            "bulk_import": {
                "access_control": {
                    "allowed_roles": ["ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "full",
                    "redirect_path": "/billing",
                    "redirect_message": "Upgrade to Pro for bulk company import",
                },
            },
            "export": {
                "access_control": {
                    "allowed_roles": ["ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "full",
                    "redirect_path": "/billing",
                    "redirect_message": "Upgrade to Pro to export companies",
                },
            },
        },
    }
    
    existing = await repo.get_by_page_id(data["page_id"])
    if existing:
        await repo.update_page_content(data["page_id"], data)
        print("✓ Updated Companies page")
    else:
        await repo.create_page_content(data)
        print("✓ Seeded Companies page")


async def seed_dashboard_page(repo: DashboardRepository):
    """Seed Dashboard page."""
    data = {
        "page_id": "dashboard",
        "metadata": {
            "title": "Dashboard",
            "description": "Overview of your account activity",
            "route": "/dashboard",
            "last_updated": datetime.utcnow(),
            "version": 1,
        },
        "access_control": {
            "allowed_roles": ["FreeUser", "ProUser", "Admin", "SuperAdmin"],
            "restriction_type": "none",
            "redirect_path": "/billing",
        },
        "sections": {
            "performance_chart": {
                "access_control": {
                    "allowed_roles": ["ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "hidden",
                    "redirect_path": "/billing",
                    "redirect_message": "Upgrade to Pro to view performance charts",
                },
            },
            "activity_feed": {
                "access_control": {
                    "allowed_roles": ["FreeUser", "ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "none",
                },
            },
            "admin_stats": {
                "access_control": {
                    "allowed_roles": ["Admin", "SuperAdmin"],
                    "restriction_type": "hidden",
                },
            },
        },
    }
    
    existing = await repo.get_by_page_id(data["page_id"])
    if existing:
        await repo.update_page_content(data["page_id"], data)
        print("✓ Updated Dashboard page")
    else:
        await repo.create_page_content(data)
        print("✓ Seeded Dashboard page")


async def seed_activities_page(repo: DashboardRepository):
    """Seed Activities page."""
    data = {
        "page_id": "activities",
        "metadata": {
            "title": "Activities",
            "description": "View your account activity history",
            "route": "/activities",
            "last_updated": datetime.utcnow(),
            "version": 1,
        },
        "access_control": {
            "allowed_roles": ["FreeUser", "ProUser", "Admin", "SuperAdmin"],
            "restriction_type": "none",
            "redirect_path": "/billing",
        },
        "sections": {
            "activity_table": {
                "access_control": {
                    "allowed_roles": ["FreeUser", "ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "none",
                },
            },
            "activity_filters": {
                "access_control": {
                    "allowed_roles": ["FreeUser", "ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "none",
                },
            },
        },
    }
    
    existing = await repo.get_by_page_id(data["page_id"])
    if existing:
        await repo.update_page_content(data["page_id"], data)
        print("✓ Updated Activities page")
    else:
        await repo.create_page_content(data)
        print("✓ Seeded Activities page")


async def seed_billing_page(repo: DashboardRepository):
    """Seed Billing page."""
    data = {
        "page_id": "billing",
        "metadata": {
            "title": "Billing",
            "description": "Manage your subscription and billing",
            "route": "/billing",
            "last_updated": datetime.utcnow(),
            "version": 1,
        },
        "access_control": {
            "allowed_roles": ["FreeUser", "ProUser", "Admin", "SuperAdmin"],
            "restriction_type": "none",
            "redirect_path": "/billing",
        },
        "sections": {
            "view_subscription": {
                "access_control": {
                    "allowed_roles": ["FreeUser", "ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "none",
                },
            },
            "manage_subscription": {
                "access_control": {
                    "allowed_roles": ["ProUser", "Admin", "SuperAdmin"],
                    "restriction_type": "none",
                },
            },
            "team_management": {
                "access_control": {
                    "allowed_roles": ["Admin", "SuperAdmin"],
                    "restriction_type": "hidden",
                },
            },
        },
    }
    
    existing = await repo.get_by_page_id(data["page_id"])
    if existing:
        await repo.update_page_content(data["page_id"], data)
        print("✓ Updated Billing page")
    else:
        await repo.create_page_content(data)
        print("✓ Seeded Billing page")


async def main():
    """Main seed function."""
    import sys
    print("Starting dashboard pages seed...", flush=True)
    sys.stdout.flush()
    
    try:
        repo = DashboardRepository()
        print("Repository initialized", flush=True)
        
        # Seed all dashboard pages
        print("\nSeeding dashboard pages...", flush=True)
        await seed_finder_page(repo)
        await seed_verifier_page(repo)
        await seed_ai_chat_page(repo)
        await seed_linkedin_page(repo)
        await seed_export_page(repo)
        await seed_contacts_page(repo)
        await seed_companies_page(repo)
        await seed_dashboard_page(repo)
        await seed_activities_page(repo)
        await seed_billing_page(repo)
        
        print("\n✓ All dashboard pages seeded successfully!", flush=True)
        
    except Exception as e:
        import traceback
        print(f"\n✗ Error seeding data: {e}", flush=True)
        traceback.print_exc()
        raise
    finally:
        await close_mongodb_connection()
        print("MongoDB connection closed", flush=True)


if __name__ == "__main__":
    asyncio.run(main())

