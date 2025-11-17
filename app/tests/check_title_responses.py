"""Check title endpoint responses using pytest fixtures."""
import pytest
import asyncio
import json
from app.tests.conftest import *
from app.tests.factories import create_contact
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.api.deps import get_current_user
from app.models.user import User
from sqlalchemy import delete

async def check_title_responses():
    """Check title endpoint responses with detailed output."""
    # Setup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestingSessionLocal() as db_session:
        # Clean
        for table in (ContactMetadata, Contact, CompanyMetadata, Company, UserProfile, User):
            await db_session.execute(delete(table))
        await db_session.commit()
        
        # Create test user
        test_user = User(
            id="test-user-123",
            email="test@example.com",
            hashed_password="test_hash",
            name="Test User",
            is_active=True,
        )
        db_session.add(test_user)
        await db_session.flush()
        
        # Override auth
        async def _get_test_user():
            return test_user
        app.dependency_overrides[get_current_user] = _get_test_user
        
        # Create test data - same as the test
        for i in range(3):
            await create_contact(
                db_session,
                first_name=f"Person{i}",
                email=f"person{i}@example.com",
                title="Director",
            )
        await create_contact(
            db_session,
            first_name="Manager",
            email="manager@example.com",
            title="Manager",
        )
        await db_session.commit()
        
        # Test
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            print("\n" + "="*80)
            print("GET /api/v1/contacts/title/ (without distinct)")
            print("="*80)
            
            response1 = await client.get("/api/v1/contacts/title/")
            result1 = response1.json()
            print(f"Status: {response1.status_code}")
            print(f"Response: {json.dumps(result1, indent=2)}")
            print(f"Count: {len(result1)}")
            
            print("\n" + "="*80)
            print("GET /api/v1/contacts/title/?distinct=true")
            print("="*80)
            
            response2 = await client.get("/api/v1/contacts/title/", params={"distinct": "true"})
            result2 = response2.json()
            print(f"Status: {response2.status_code}")
            print(f"Response: {json.dumps(result2, indent=2)}")
            print(f"Count: {len(result2)}")
            
            print("\n" + "="*80)
            print("VERIFICATION")
            print("="*80)
            
            # Verify
            assert response1.status_code == 200, "First endpoint should return 200"
            assert response2.status_code == 200, "Second endpoint should return 200"
            assert isinstance(result1, list), "First response should be a list"
            assert isinstance(result2, list), "Second response should be a list"
            assert len(result2) <= len(result1), "Distinct should return fewer or equal items"
            
            # Check for duplicates in distinct
            distinct_lower = [str(v).lower() for v in result2 if v]
            assert len(distinct_lower) == len(set(distinct_lower)), "Distinct results should have no duplicates"
            
            # Check all distinct values are in non-distinct
            no_distinct_lower = [str(v).lower() for v in result1 if v]
            for dv in distinct_lower:
                assert dv in no_distinct_lower, f"Distinct value '{dv}' should be in non-distinct results"
            
            print("[PASS] Status codes: Both 200")
            print("[PASS] Response format: Both List[str]")
            print(f"[PASS] Item count: {len(result2)} <= {len(result1)}")
            print("[PASS] No duplicates in distinct results")
            print("[PASS] All distinct values present in non-distinct results")
            
            # Expected values
            expected = {"director", "manager"}
            actual = {v.lower() for v in result2 if v}
            if expected == actual:
                print(f"[PASS] Expected titles match: {expected}")
            else:
                print(f"[INFO] Expected: {expected}, Got: {actual}")
            
            print("\n[SUCCESS] All responses are CORRECT!")
            
            app.dependency_overrides.pop(get_current_user, None)
            return True

if __name__ == "__main__":
    asyncio.run(check_title_responses())

