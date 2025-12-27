"""Validate marketing API endpoints."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.repositories.marketing_repository import MarketingRepository


async def validate_data():
    """Validate that all marketing pages exist in MongoDB."""
    print("Validating marketing pages in MongoDB...\n")
    
    repo = MarketingRepository()
    
    expected_pages = [
        "ai-email-writer",
        "email-finder",
        "email-verifier",
        "prospect-finder",
        "chrome-extension",
        "cfo-email-list",
    ]
    
    all_found = True
    
    for page_id in expected_pages:
        page = await repo.get_page_content(page_id, include_drafts=False)
        if page:
            status = page.get("metadata", {}).get("status", "unknown")
            title = page.get("metadata", {}).get("title", "N/A")
            print(f"✓ {page_id}: {title} (status: {status})")
        else:
            print(f"✗ {page_id}: NOT FOUND")
            all_found = False
    
    print("\n" + "=" * 50)
    if all_found:
        print("✓ All marketing pages are present in MongoDB!")
    else:
        print("✗ Some pages are missing. Run the seed script:")
        print("  python scripts/seed_marketing_data.py")
    
    # List all pages
    print("\nAll pages in database:")
    all_pages = await repo.list_all_pages(include_drafts=True)
    for page in all_pages:
        page_id = page.get("page_id", "unknown")
        status = page.get("metadata", {}).get("status", "unknown")
        print(f"  - {page_id} ({status})")
    
    from app.clients.mongodb import close_mongodb_connection
    await close_mongodb_connection()


if __name__ == "__main__":
    asyncio.run(validate_data())

