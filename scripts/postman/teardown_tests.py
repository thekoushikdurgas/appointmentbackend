#!/usr/bin/env python3
"""Teardown script for test environment."""

import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from tests.config import TestConfig
from tests.auth import AuthHandler
from fixtures.test_data import TestDataFixtures


def cleanup_test_environment(base_url: str = None):
    """Clean up after tests.
    
    Args:
        base_url: API base URL (optional)
    
    Returns:
        Dictionary with cleanup results
    """
    print("Cleaning up test environment...")
    
    # Initialize configuration
    config = TestConfig(base_url=base_url)
    
    # Initialize authentication handler
    auth_handler = AuthHandler(config)
    
    # Authenticate to perform cleanup
    if not auth_handler.authenticate():
        print("⚠ Authentication failed - skipping cleanup")
        return {"success": False, "error": "Authentication failed"}
    
    # Initialize fixtures
    fixtures = TestDataFixtures(config, auth_handler)
    
    # Step 1: Clean up fixture entities
    print("Step 1: Cleaning up fixture entities...")
    try:
        fixtures.cleanup_test_data()
        print("✓ Fixture entities cleaned up")
    except Exception as e:
        print(f"⚠ Error cleaning up fixtures: {e}")
    
    # Step 2: Clear cached tokens
    print("Step 2: Clearing cached tokens...")
    auth_handler.access_token = None
    auth_handler.refresh_token = None
    auth_handler._authenticated = False
    print("✓ Tokens cleared")
    
    # Step 3: Remove seed files (optional)
    seed_file = config.output_dir / "test_seeds.json"
    if seed_file.exists():
        try:
            seed_file.unlink()
            print(f"✓ Removed seed file: {seed_file}")
        except Exception as e:
            print(f"⚠ Could not remove seed file: {e}")
    
    print("\n✓ Test environment cleanup complete!")
    return {"success": True}


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Cleanup test environment")
    parser.add_argument("--base-url", type=str, help="API base URL")
    
    args = parser.parse_args()
    
    result = cleanup_test_environment(base_url=args.base_url)
    
    if not result["success"]:
        sys.exit(1)

