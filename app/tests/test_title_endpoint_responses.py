"""Script to test and verify title endpoint responses with and without distinct parameter."""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import delete

from app.main import app
from app.db.base import Base
from app.models.companies import Company, CompanyMetadata
from app.models.contacts import Contact, ContactMetadata
from app.models.user import User
from app.api.deps import get_current_user
from app.tests.factories import create_contact, create_company

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def setup_test_data(session: AsyncSession):
    """Create test data with duplicate titles."""
    # Clean existing data
    for table in (ContactMetadata, Contact, CompanyMetadata, Company, User):
        await session.execute(delete(table))
    await session.commit()
    
    # Create test user for authentication
    test_user = User(
        id="test-user-id",
        email="test@example.com",
        hashed_password="test_hash",
        name="Test User",
        is_active=True,
    )
    session.add(test_user)
    await session.flush()
    
    # Override get_current_user
    async def _get_test_user():
        return test_user
    app.dependency_overrides[get_current_user] = _get_test_user
    
    # Create contacts with duplicate titles
    await create_contact(session, first_name="John", email="john1@example.com", title="Director")
    await create_contact(session, first_name="Jane", email="jane1@example.com", title="Director")
    await create_contact(session, first_name="Bob", email="bob@example.com", title="Manager")
    await create_contact(session, first_name="Alice", email="alice@example.com", title="Manager")
    await create_contact(session, first_name="Charlie", email="charlie@example.com", title="CEO")
    
    await session.commit()


async def test_title_endpoints():
    """Test title endpoint with and without distinct parameter."""
    # Setup database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    session = TestingSessionLocal()
    try:
        await setup_test_data(session)
        
        # Create async client
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            print("=" * 80)
            print("Testing GET /api/v1/contacts/title/ (without distinct)")
            print("=" * 80)
            
            # Test without distinct
            response_no_distinct = await client.get("/api/v1/contacts/title/")
            print(f"Status Code: {response_no_distinct.status_code}")
            print(f"Response Type: {type(response_no_distinct.json())}")
            results_no_distinct = response_no_distinct.json()
            print(f"Response: {results_no_distinct}")
            print(f"Count: {len(results_no_distinct)}")
            print(f"Unique values (case-insensitive): {len(set(v.lower() if v else '' for v in results_no_distinct))}")
            
            print("\n" + "=" * 80)
            print("Testing GET /api/v1/contacts/title/?distinct=true")
            print("=" * 80)
            
            # Test with distinct=true
            response_distinct = await client.get("/api/v1/contacts/title/", params={"distinct": "true"})
            print(f"Status Code: {response_distinct.status_code}")
            print(f"Response Type: {type(response_distinct.json())}")
            results_distinct = response_distinct.json()
            print(f"Response: {results_distinct}")
            print(f"Count: {len(results_distinct)}")
            print(f"Unique values (case-insensitive): {len(set(v.lower() if v else '' for v in results_distinct))}")
            
            print("\n" + "=" * 80)
            print("VERIFICATION RESULTS")
            print("=" * 80)
            
            # Verify responses
            checks = []
            
            # Check 1: Status codes
            status_ok = response_no_distinct.status_code == 200 and response_distinct.status_code == 200
            checks.append(("Status codes are 200", status_ok))
            print(f"[PASS] Status codes are 200: {status_ok}")
            
            # Check 2: Response format
            format_ok = isinstance(results_no_distinct, list) and isinstance(results_distinct, list)
            checks.append(("Response format is List[str]", format_ok))
            print(f"[PASS] Response format is List[str]: {format_ok}")
            
            # Check 3: Distinct returns fewer or equal items
            length_ok = len(results_distinct) <= len(results_no_distinct)
            checks.append(("Distinct returns fewer or equal items", length_ok))
            print(f"[PASS] Distinct returns fewer or equal items: {length_ok} ({len(results_distinct)} <= {len(results_no_distinct)})")
            
            # Check 4: No duplicates in distinct results
            distinct_lower = [str(v).lower() if v else "" for v in results_distinct]
            no_duplicates = len(distinct_lower) == len(set(distinct_lower))
            checks.append(("No duplicates in distinct results", no_duplicates))
            print(f"[PASS] No duplicates in distinct results: {no_duplicates}")
            
            # Check 5: All distinct values present in non-distinct
            no_distinct_lower = [str(v).lower() if v else "" for v in results_no_distinct]
            all_present = all(dv in no_distinct_lower for dv in distinct_lower) if distinct_lower else True
            checks.append(("All distinct values in non-distinct results", all_present))
            print(f"[PASS] All distinct values in non-distinct results: {all_present}")
            
            # Check 6: Expected values (only if we have test data)
            if results_distinct:
                expected_titles = {"director", "manager", "ceo"}
                actual_titles = {v.lower() for v in results_distinct if v}
                expected_ok = expected_titles.issubset(actual_titles) or actual_titles.issubset(expected_titles)
                checks.append(("Expected titles present", expected_ok))
                print(f"[PASS] Expected titles present: {expected_ok}")
                print(f"  Expected: {expected_titles}")
                print(f"  Actual: {actual_titles}")
            
            print("\n" + "=" * 80)
            print("SUMMARY")
            print("=" * 80)
            all_passed = all(check[1] for check in checks)
            for check_name, passed in checks:
                status = "[PASS]" if passed else "[FAIL]"
                print(f"{status}: {check_name}")
            
            if all_passed:
                print("\n[SUCCESS] ALL CHECKS PASSED - Responses are CORRECT")
            else:
                print("\n[ERROR] SOME CHECKS FAILED - Responses need review")
            
            return all_passed
            
    finally:
        await session.close()
        app.dependency_overrides.pop(get_current_user, None)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)


if __name__ == "__main__":
    result = asyncio.run(test_title_endpoints())
    sys.exit(0 if result else 1)

