"""Performance tests for user operations to track improvements and prevent regressions."""

import time
from uuid import uuid4

import pytest
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user import UserRepository
from app.schemas.user import UserRegister
from app.services.user_service import UserService


@pytest.mark.asyncio
@pytest.mark.performance
class TestUserOperationsPerformance:
    """Performance benchmarks for user operations."""

    @pytest.mark.asyncio
    async def test_user_lookup_performance(self, db_session: AsyncSession):
        """Ensure user lookup by UUID is <50ms."""
        repo = UserRepository()
        
        # Create a test user first
        from app.core.security import get_password_hash
        from app.models.user import User
        
        test_uuid = str(uuid4())
        test_user = User(
            uuid=test_uuid,
            email=f"test_{test_uuid[:8]}@example.com",
            hashed_password=get_password_hash("testpassword123"),
            name="Test User",
        )
        db_session.add(test_user)
        await db_session.commit()
        await db_session.refresh(test_user)
        
        # Measure lookup time
        start = time.time()
        user = await repo.get_by_uuid(db_session, test_uuid)
        duration_ms = (time.time() - start) * 1000
        
        assert user is not None, "User should be found"
        assert duration_ms < 50, f"User lookup took {duration_ms:.2f}ms (should be <50ms)"
        
        # Cleanup
        await db_session.delete(test_user)
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_user_email_lookup_performance(self, db_session: AsyncSession):
        """Ensure user lookup by email is <50ms."""
        repo = UserRepository()
        
        # Create a test user first
        from app.core.security import get_password_hash
        from app.models.user import User
        
        test_email = f"test_{uuid4().hex[:8]}@example.com"
        test_user = User(
            uuid=str(uuid4()),
            email=test_email,
            hashed_password=get_password_hash("testpassword123"),
            name="Test User",
        )
        db_session.add(test_user)
        await db_session.commit()
        await db_session.refresh(test_user)
        
        # Measure lookup time
        start = time.time()
        user = await repo.get_by_email(db_session, test_email)
        duration_ms = (time.time() - start) * 1000
        
        assert user is not None, "User should be found"
        assert duration_ms < 50, f"User email lookup took {duration_ms:.2f}ms (should be <50ms)"
        
        # Cleanup
        await db_session.delete(test_user)
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_cached_user_lookup_performance(self, db_session: AsyncSession):
        """Ensure cached user lookup is <5ms."""
        repo = UserRepository()
        
        # Create a test user first
        from app.core.security import get_password_hash
        from app.models.user import User
        
        test_uuid = str(uuid4())
        test_user = User(
            uuid=test_uuid,
            email=f"test_{test_uuid[:8]}@example.com",
            hashed_password=get_password_hash("testpassword123"),
            name="Test User",
        )
        db_session.add(test_user)
        await db_session.commit()
        await db_session.refresh(test_user)
        
        # First lookup (populates cache)
        await repo.get_by_uuid_cached(db_session, test_uuid)
        
        # Second lookup (should hit cache)
        start = time.time()
        user = await repo.get_by_uuid_cached(db_session, test_uuid)
        duration_ms = (time.time() - start) * 1000
        
        assert user is not None, "User should be found"
        assert duration_ms < 5, f"Cached user lookup took {duration_ms:.2f}ms (should be <5ms)"
        
        # Cleanup
        await db_session.delete(test_user)
        await db_session.commit()

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires S3 configuration and test file")
    async def test_avatar_upload_performance(self, db_session: AsyncSession):
        """Ensure avatar upload is <3s."""
        service = UserService()
        
        # Create a test user first
        from app.core.security import get_password_hash
        from app.models.user import User
        
        test_uuid = str(uuid4())
        test_user = User(
            uuid=test_uuid,
            email=f"test_{test_uuid[:8]}@example.com",
            hashed_password=get_password_hash("testpassword123"),
            name="Test User",
        )
        db_session.add(test_user)
        await db_session.commit()
        await db_session.refresh(test_user)
        
        # Create a test file (this would need actual file handling)
        # For now, this test is skipped as it requires S3 setup
        # test_file = UploadFile(filename="test.jpg", file=io.BytesIO(b"fake image data"))
        
        # start = time.time()
        # await service.upload_avatar(db_session, test_uuid, test_file)
        # duration_ms = (time.time() - start) * 1000
        # 
        # assert duration_ms < 3000, f"Avatar upload took {duration_ms:.2f}ms (should be <3s)"
        
        # Cleanup
        await db_session.delete(test_user)
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_registration_performance(self, db_session: AsyncSession):
        """Ensure registration is <1.5s."""
        service = UserService()
        
        test_email = f"test_{uuid4().hex[:8]}@example.com"
        register_data = UserRegister(
            email=test_email,
            password="testpassword123",
            name="Test User",
        )
        
        start = time.time()
        user, access_token, refresh_token = await service.register_user(db_session, register_data)
        duration_ms = (time.time() - start) * 1000
        
        assert user is not None, "User should be created"
        assert access_token is not None, "Access token should be generated"
        assert refresh_token is not None, "Refresh token should be generated"
        assert duration_ms < 1500, f"Registration took {duration_ms:.2f}ms (should be <1.5s)"
        
        # Cleanup
        await db_session.delete(user)
        await db_session.commit()

