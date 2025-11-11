"""Verify title endpoint responses with detailed output."""
import asyncio
import json
from app.tests.conftest import *
from app.tests.factories import create_contact
from httpx import ASGITransport, AsyncClient
from app.main import app

async def verify_title_responses():
    """Verify title endpoint responses."""
    # Setup test database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestingSessionLocal() as db_session:
        # Clean database
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
        
        # Override get_current_user
        async def _get_test_user():
            return test_user
        app.dependency_overrides[get_current_user] = _get_test_user
        
        # Create test contacts with duplicate titles
        await create_contact(db_session, first_name="John", email="john1@example.com", title="Director")
        await create_contact(db_session, first_name="Jane", email="jane1@example.com", title="Director")
        await create_contact(db_session, first_name="Bob", email="bob@example.com", title="Manager")
        await create_contact(db_session, first_name="Alice", email="alice@example.com", title="Manager")
        await create_contact(db_session, first_name="Charlie", email="charlie@example.com", title="CEO")
        await db_session.commit()
        
        # Create async client
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            print("\n" + "="*80)
            print("TEST 1: GET /api/v1/contacts/title/ (without distinct)")
            print("="*80)
            
            response1 = await client.get("/api/v1/contacts/title/")
            print(f"Status Code: {response1.status_code}")
            result1 = response1.json()
            print(f"Response Type: {type(result1).__name__}")
            print(f"Response Count: {len(result1)}")
            print(f"Response: {json.dumps(result1, indent=2)}")
            
            # Count duplicates
            titles_lower = [str(t).lower() for t in result1 if t]
            unique_count = len(set(titles_lower))
            duplicate_count = len(titles_lower) - unique_count
            print(f"Unique titles (case-insensitive): {unique_count}")
            print(f"Duplicate entries: {duplicate_count}")
            
            print("\n" + "="*80)
            print("TEST 2: GET /api/v1/contacts/title/?distinct=true")
            print("="*80)
            
            response2 = await client.get("/api/v1/contacts/title/", params={"distinct": "true"})
            print(f"Status Code: {response2.status_code}")
            result2 = response2.json()
            print(f"Response Type: {type(result2).__name__}")
            print(f"Response Count: {len(result2)}")
            print(f"Response: {json.dumps(result2, indent=2)}")
            
            # Verify no duplicates
            titles2_lower = [str(t).lower() for t in result2 if t]
            unique_count2 = len(set(titles2_lower))
            print(f"Unique titles (case-insensitive): {unique_count2}")
            print(f"Has duplicates: {len(titles2_lower) != unique_count2}")
            
            print("\n" + "="*80)
            print("VERIFICATION")
            print("="*80)
            
            checks = []
            
            # Check 1: Status codes
            check1 = response1.status_code == 200 and response2.status_code == 200
            checks.append(("Both endpoints return 200", check1))
            print(f"[{'PASS' if check1 else 'FAIL'}] Status codes: {response1.status_code}, {response2.status_code}")
            
            # Check 2: Response format
            check2 = isinstance(result1, list) and isinstance(result2, list)
            checks.append(("Both responses are lists", check2))
            print(f"[{'PASS' if check2 else 'FAIL'}] Response format: List[str]")
            
            # Check 3: Distinct has fewer or equal items
            check3 = len(result2) <= len(result1)
            checks.append(("Distinct returns fewer/equal items", check3))
            print(f"[{'PASS' if check3 else 'FAIL'}] Item count: {len(result2)} <= {len(result1)}")
            
            # Check 4: No duplicates in distinct
            check4 = len(titles2_lower) == unique_count2
            checks.append(("No duplicates in distinct results", check4))
            print(f"[{'PASS' if check4 else 'FAIL'}] No duplicates in distinct: {check4}")
            
            # Check 5: All distinct values in non-distinct
            check5 = all(t.lower() in titles_lower for t in result2 if t)
            checks.append(("All distinct values in non-distinct", check5))
            print(f"[{'PASS' if check5 else 'FAIL'}] All distinct values present in non-distinct")
            
            # Check 6: Expected values
            expected = {"director", "manager", "ceo"}
            actual = {t.lower() for t in result2 if t}
            check6 = expected == actual
            checks.append(("Expected titles match", check6))
            print(f"[{'PASS' if check6 else 'FAIL'}] Expected: {expected}, Actual: {actual}")
            
            print("\n" + "="*80)
            print("SUMMARY")
            print("="*80)
            all_passed = all(c[1] for c in checks)
            for name, passed in checks:
                print(f"[{'PASS' if passed else 'FAIL'}] {name}")
            
            if all_passed:
                print("\n[SUCCESS] All responses are CORRECT!")
            else:
                print("\n[ERROR] Some checks failed - responses need review")
            
            # Cleanup
            app.dependency_overrides.pop(get_current_user, None)
            return all_passed

if __name__ == "__main__":
    result = asyncio.run(verify_title_responses())
    exit(0 if result else 1)

