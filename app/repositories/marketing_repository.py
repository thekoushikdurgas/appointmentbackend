"""Marketing repository for MongoDB operations."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorCollection

from app.clients.mongodb import get_mongodb_database
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MarketingRepository:
    """Repository for marketing page operations in MongoDB."""
    
    COLLECTION_NAME = "marketing_pages"
    
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
        """Get marketing page by page_id."""
        collection = await self._get_collection()
        
        query = {"page_id": page_id}
        if not include_deleted:
            query["metadata.status"] = {"$ne": "deleted"}
        
        page = await collection.find_one(query)
        if page:
            # Convert ObjectId to string for JSON serialization
            page["_id"] = str(page["_id"])
        return page
    
    async def list_all(
        self, 
        include_drafts: bool = False,
        include_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        """List all marketing pages."""
        collection = await self._get_collection()
        
        query: Dict[str, Any] = {}
        if not include_deleted:
            query["metadata.status"] = {"$ne": "deleted"}
        
        if not include_drafts:
            query["metadata.status"] = "published"
        
        cursor = collection.find(query).sort("metadata.last_updated", -1)
        pages = await cursor.to_list(length=None)
        
        # Convert ObjectIds to strings
        for page in pages:
            page["_id"] = str(page["_id"])
        
        return pages
    
    async def create_page_content(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new marketing page."""
        collection = await self._get_collection()
        
        # Ensure metadata has required fields
        if "metadata" not in data:
            data["metadata"] = {}
        
        data["metadata"]["last_updated"] = datetime.utcnow()
        if "status" not in data["metadata"]:
            data["metadata"]["status"] = "draft"
        if "version" not in data["metadata"]:
            data["metadata"]["version"] = 1
        
        # Check if page_id already exists
        existing = await self.get_by_page_id(data["page_id"], include_deleted=True)
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
        """Update existing marketing page."""
        collection = await self._get_collection()
        
        # Remove _id if present (can't update MongoDB _id)
        update_data = {k: v for k, v in data.items() if k != "_id"}
        
        # Update last_updated timestamp
        if "metadata" in update_data:
            update_data["metadata"]["last_updated"] = datetime.utcnow()
            # Increment version if updating
            existing = await self.get_by_page_id(page_id, include_deleted=True)
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
    
    async def delete_page(
        self, 
        page_id: str, 
        hard_delete: bool = False
    ) -> bool:
        """Delete marketing page (soft delete by default)."""
        collection = await self._get_collection()
        
        if hard_delete:
            result = await collection.delete_one({"page_id": page_id})
            return result.deleted_count > 0
        else:
            # Soft delete - update status
            result = await collection.update_one(
                {"page_id": page_id},
                {
                    "$set": {
                        "metadata.status": "deleted",
                        "metadata.last_updated": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
    
    async def publish_page(self, page_id: str) -> Optional[Dict[str, Any]]:
        """Publish a draft page."""
        collection = await self._get_collection()
        
        result = await collection.find_one_and_update(
            {"page_id": page_id},
            {
                "$set": {
                    "metadata.status": "published",
                    "metadata.last_updated": datetime.utcnow()
                }
            },
            return_document=True
        )
        
        if result:
            result["_id"] = str(result["_id"])
        return result
    
    async def count_pages(
        self, 
        include_drafts: bool = False,
        include_deleted: bool = False
    ) -> int:
        """Count marketing pages."""
        collection = await self._get_collection()
        
        query: Dict[str, Any] = {}
        if not include_deleted:
            query["metadata.status"] = {"$ne": "deleted"}
        
        if not include_drafts:
            query["metadata.status"] = "published"
        
        return await collection.count_documents(query)

