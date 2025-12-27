#!/usr/bin/env python3
"""Setup script for test environment."""

import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from tests.config import TestConfig
from tests.auth import AuthHandler
from fixtures.test_data import TestDataFixtures
from fixtures.seed_test_entities import TestEntitySeeder


def setup_test_environment(base_url: str = None, email: str = None, password: str = None):
    """One-time setup for test environment.
    
    Args:
        base_url: API base URL (optional)
        email: Test user email (optional)
        password: Test user password (optional)
    
    Returns:
        Dictionary with setup results
    """
    print("Setting up test environment...")
    
    # Initialize configuration
    config = TestConfig(
        base_url=base_url,
        email=email,
        password=password,
        auto_create_test_user=True
    )
    
    # Initialize authentication handler
    auth_handler = AuthHandler(config)
    
    # Step 1: Create test user and authenticate
    print("Step 1: Creating test user and authenticating...")
    if not auth_handler.authenticate():
        print("ERROR: Authentication failed")
        return {"success": False, "error": "Authentication failed"}
    
    print("✓ Test user authenticated")
    
    # Step 2: Authenticate admin if credentials available
    if config.has_admin_credentials():
        print("Step 2: Authenticating admin user...")
        if auth_handler.authenticate_admin():
            print("✓ Admin user authenticated")
        else:
            print("⚠ Admin authentication failed (admin endpoints will be skipped)")
    
    # Step 3: Create fixture entities
    print("Step 3: Creating fixture entities...")
    fixtures = TestDataFixtures(config, auth_handler)
    
    # Create test chat
    chat_id = fixtures.get_test_chat_id()
    if chat_id:
        print(f"✓ Created test chat: {chat_id}")
    else:
        print("⚠ Could not create test chat")
    
    # Step 4: Seed test entities
    print("Step 4: Seeding test entities...")
    seeder = TestEntitySeeder(config, auth_handler)
    seeds = seeder.seed_all()
    
    if seeds:
        print(f"✓ Seeded {len(seeds)} test entities")
        for entity_type, entity_id in seeds.items():
            print(f"  - {entity_type}: {entity_id}")
    else:
        print("⚠ No test entities seeded (some tests may be skipped)")
    
    # Step 5: Save seeds to file
    seeder.save_seeds()
    print(f"✓ Seeds saved to: {seeder.seed_file}")
    
    print("\n✓ Test environment setup complete!")
    return {
        "success": True,
        "seeds": seeds,
        "chat_id": chat_id,
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup test environment")
    parser.add_argument("--base-url", type=str, help="API base URL")
    parser.add_argument("--email", type=str, help="Test user email")
    parser.add_argument("--password", type=str, help="Test user password")
    
    args = parser.parse_args()
    
    result = setup_test_environment(
        base_url=args.base_url,
        email=args.email,
        password=args.password
    )
    
    if not result["success"]:
        sys.exit(1)

