"""Test MongoDB connection."""
import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set MongoDB URI
os.environ["MONGODB_URI"] = "mongodb://admin:koushik123456@54.164.46.115:27017"

async def test_connection():
    try:
        from app.clients.mongodb import get_mongodb_database
        print("Testing MongoDB connection...")
        db = await get_mongodb_database()
        print(f"✓ Connected to database: {db.name}")
        
        # Test collection access
        collection = db["marketing_pages"]
        count = await collection.count_documents({})
        print(f"✓ Collection 'marketing_pages' exists with {count} documents")
        
        from app.clients.mongodb import close_mongodb_connection
        await close_mongodb_connection()
        print("✓ Connection closed successfully")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_connection())
    sys.exit(0 if result else 1)

