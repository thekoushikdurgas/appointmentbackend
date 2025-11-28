"""Optimized serialization utilities for large collections.

This module provides utilities for efficiently serializing large collections
using Pydantic TypeAdapter, which is faster than standard JSON serialization
for large datasets.

Usage:
    from app.utils.serialization import serialize_collection
    
    # Serialize large collection efficiently
    json_bytes = serialize_collection(items, ItemSchema)
"""

from __future__ import annotations

from typing import TypeVar, Type, Any

from pydantic import TypeAdapter, BaseModel

from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


def serialize_collection(
    items: list[Any],
    schema: Type[T],
    use_type_adapter: bool = True,
) -> bytes:
    """
    Serialize a collection of items to JSON bytes using optimized Pydantic TypeAdapter.
    
    This is significantly faster than standard json.dumps() for large collections,
    especially when items are Pydantic models.
    
    Args:
        items: List of items to serialize
        schema: Pydantic model class or type for the items
        use_type_adapter: If True, use TypeAdapter for better performance
        
    Returns:
        JSON bytes representation of the collection
        
    Example:
        from app.schemas.contacts import ContactListItem
        
        items = [contact1, contact2, ...]
        json_bytes = serialize_collection(items, ContactListItem)
    """
    if not items:
        return b"[]"
    
    if use_type_adapter:
        try:
            # Use TypeAdapter for high-performance serialization
            adapter = TypeAdapter(list[schema])
            json_bytes = adapter.dump_json(items)
            logger.debug("Serialized %d items using TypeAdapter", len(items))
            return json_bytes
        except Exception as exc:
            logger.warning("TypeAdapter serialization failed, falling back to standard: %s", exc)
            # Fallback to standard serialization
            import json
            return json.dumps([item.model_dump() if hasattr(item, "model_dump") else item for item in items]).encode("utf-8")
    else:
        # Standard serialization
        import json
        return json.dumps([item.model_dump() if hasattr(item, "model_dump") else item for item in items]).encode("utf-8")


def serialize_model(model: BaseModel, use_type_adapter: bool = True) -> bytes:
    """
    Serialize a single Pydantic model to JSON bytes.
    
    Args:
        model: Pydantic model instance
        use_type_adapter: If True, use TypeAdapter for better performance
        
    Returns:
        JSON bytes representation of the model
    """
    if use_type_adapter:
        try:
            adapter = TypeAdapter(type(model))
            json_bytes = adapter.dump_json(model)
            logger.debug("Serialized model using TypeAdapter: %s", type(model).__name__)
            return json_bytes
        except Exception as exc:
            logger.warning("TypeAdapter serialization failed, falling back to standard: %s", exc)
            import json
            return json.dumps(model.model_dump()).encode("utf-8")
    else:
        import json
        return json.dumps(model.model_dump()).encode("utf-8")

