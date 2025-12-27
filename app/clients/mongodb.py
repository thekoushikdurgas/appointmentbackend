"""MongoDB client for async database operations."""

import os
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Global MongoDB client instance
_mongodb_client: Optional[AsyncIOMotorClient] = None
_mongodb_database: Optional[AsyncIOMotorDatabase] = None


async def get_mongodb_database() -> AsyncIOMotorDatabase:
    """Get MongoDB database instance, creating connection if needed."""
    global _mongodb_client, _mongodb_database
    
    if _mongodb_database is not None:
        return _mongodb_database
    
    # Get MongoDB URI from settings
    mongodb_uri = settings.MONGODB_URI
    
    # Create client if it doesn't exist
    if _mongodb_client is None:
        _mongodb_client = AsyncIOMotorClient(
            mongodb_uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=5000,
        )
    
    # Get or create database
    db_name = settings.MONGODB_DB_NAME
    _mongodb_database = _mongodb_client[db_name]
    
    # Test connection
    try:
        await _mongodb_client.admin.command('ping')
    except Exception as e:
        raise ConnectionError(f"Failed to connect to MongoDB: {e}") from e
    
    return _mongodb_database


async def close_mongodb_connection() -> None:
    """Close MongoDB connection."""
    global _mongodb_client, _mongodb_database
    
    if _mongodb_client is not None:
        _mongodb_client.close()
        _mongodb_client = None
        _mongodb_database = None

