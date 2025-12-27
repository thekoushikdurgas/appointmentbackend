"""Dashboard repository for MongoDB operations."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorCollection

from app.clients.mongodb import get_mongodb_database
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DashboardRepository:
    """Repository for dashboard page operations in MongoDB."""
    
    COLLECTION_NAME = "dashboard_pages"
    
    def __init__(self):
        """Initialize repository."""
        self._collection: Optional[AsyncIOMotorCollection] = None
    
    async def _get_collection(self) -> AsyncIOMotorCollection:
        """Get MongoDB collection, creating connection if needed."""
        if self._collection is None:
            db = await get_mongodb_database()
            self._collection = db[self.COLLECTION_NAME]
            # Create index on page_id for fast lookups
            await self._collection.create_index("page_id", unique=True)
        return self._collection
    
    async def get_by_page_id(
        self, 
        page_id: str, 
        include_deleted: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get dashboard page by page_id."""
        collection = await self._get_collection()
        
        query = {"page_id": page_id}
        # Note: dashboard pages don't have soft delete, but keeping parameter for consistency
        
        page = await collection.find_one(query)
        if page:
            # Convert ObjectId to string for JSON serialization
            page["_id"] = str(page["_id"])
        return page
    
    async def list_all(self) -> List[Dict[str, Any]]:
        """List all dashboard pages."""
        collection = await self._get_collection()
        
        cursor = collection.find({}).sort("metadata.route", 1)
        pages = await cursor.to_list(length=None)
        
        # Convert ObjectIds to strings
        for page in pages:
            page["_id"] = str(page["_id"])
        
        return pages
    
    async def create_page_content(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new dashboard page."""
        collection = await self._get_collection()
        
        # Ensure metadata has required fields
        if "metadata" not in data:
            data["metadata"] = {}
        
        data["metadata"]["last_updated"] = datetime.utcnow()
        if "version" not in data["metadata"]:
            data["metadata"]["version"] = 1
        
        # Ensure access_control has defaults
        if "access_control" not in data:
            data["access_control"] = {
                "allowed_roles": ["FreeUser", "ProUser", "Admin", "SuperAdmin"],
                "restriction_type": "none",
            }
        
        # Check if page_id already exists
        existing = await self.get_by_page_id(data["page_id"])
        if existing:
            raise ValueError(f"Page with page_id '{data['page_id']}' already exists")
        
        result = await collection.insert_one(data)
        data["_id"] = str(result.inserted_id)
        return data
    
    async def update_page_content(
        self, 
        page_id: str, 
        data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update existing dashboard page."""
        collection = await self._get_collection()
        
        # Remove _id if present (can't update MongoDB _id)
        update_data = {k: v for k, v in data.items() if k != "_id"}
        
        # Update last_updated timestamp
        if "metadata" in update_data:
            update_data["metadata"]["last_updated"] = datetime.utcnow()
            # Increment version if updating
            existing = await self.get_by_page_id(page_id)
            if existing and "metadata" in existing:
                current_version = existing["metadata"].get("version", 1)
                update_data["metadata"]["version"] = current_version + 1
        else:
            # Update metadata.last_updated even if metadata not in update
            update_data["metadata"] = update_data.get("metadata", {})
            update_data["metadata"]["last_updated"] = datetime.utcnow()
        
        result = await collection.find_one_and_update(
            {"page_id": page_id},
            {"$set": update_data},
            return_document=True
        )
        
        if result:
            result["_id"] = str(result["_id"])
        return result
    
    async def delete_page(self, page_id: str) -> bool:
        """Delete dashboard page (hard delete)."""
        collection = await self._get_collection()
        
        result = await collection.delete_one({"page_id": page_id})
        return result.deleted_count > 0
    
    async def count_pages(self) -> int:
        """Count dashboard pages."""
        collection = await self._get_collection()
        return await collection.count_documents({})

