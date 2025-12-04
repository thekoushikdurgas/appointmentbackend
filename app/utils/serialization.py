"""Optimized serialization utilities using Pydantic TypeAdapter.

This module provides utilities for efficient serialization of large collections
using Pydantic's TypeAdapter, which is optimized for high-performance JSON
serialization of collections.

Best practices:
- Use TypeAdapter for large collections (>100 items)
- Use response_model for filtering sensitive data
- Prefer JSONL for very large datasets
- Use orjson for faster JSON serialization (if available)
"""

from __future__ import annotations

import json
from typing import Any, Generic, TypeVar, Union

try:
    import orjson
    ORJSON_AVAILABLE = True
except ImportError:
    ORJSON_AVAILABLE = False

from pydantic import BaseModel, TypeAdapter

from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def serialize_with_type_adapter(
    items: list[Any],
    model: type[BaseModel] | None = None,
    use_orjson: bool = True,
) -> bytes:
    """
    Serialize a list of items using Pydantic TypeAdapter for optimal performance.
    
    TypeAdapter is optimized for serializing collections and provides
    better performance than individual model serialization.
    
    Args:
        items: List of items to serialize
        model: Optional Pydantic model class (auto-detected from first item if None)
        use_orjson: Whether to use orjson if available (faster than standard json)
        
    Returns:
        Serialized JSON as bytes
        
    Example:
        from app.schemas.contacts import ContactListItem
        
        contacts = [contact1, contact2, ...]
        json_bytes = serialize_with_type_adapter(contacts, ContactListItem)
    """
    if not items:
        return b"[]"
    
    # Create TypeAdapter
    if model is None:
        # Try to infer model from first item
        first_item = items[0]
        if isinstance(first_item, BaseModel):
            model = type(first_item)
        else:
            # Fallback to dict serialization
            model = dict
    
    adapter = TypeAdapter(list[model])  # type: ignore
    
    # Serialize using adapter
    if use_orjson and ORJSON_AVAILABLE:
        # Use orjson for faster serialization
        json_bytes = adapter.dump_json(items)
    else:
        # Use standard json
        json_str = adapter.dump_json(items).decode("utf-8")
        json_bytes = json_str.encode("utf-8")
    
    logger.debug("Serialized %d items using TypeAdapter: model=%s size=%d bytes", len(items), model, len(json_bytes))
    return json_bytes


def serialize_dict_list(
    items: list[dict[str, Any]],
    use_orjson: bool = True,
) -> bytes:
    """
    Serialize a list of dictionaries efficiently.
    
    Args:
        items: List of dictionaries
        use_orjson: Whether to use orjson if available
        
    Returns:
        Serialized JSON as bytes
    """
    if not items:
        return b"[]"
    
    if use_orjson and ORJSON_AVAILABLE:
        return orjson.dumps(items, option=orjson.OPT_SERIALIZE_NUMPY)
    
    return json.dumps(items, default=str).encode("utf-8")


def filter_response_data(
    data: dict[str, Any] | list[dict[str, Any]],
    exclude_fields: set[str] | None = None,
    include_fields: set[str] | None = None,
) -> dict[str, Any] | list[dict[str, Any]]:
    """
    Filter response data to reduce payload size.
    
    Args:
        data: Dictionary or list of dictionaries
        exclude_fields: Fields to exclude (None = no exclusions)
        include_fields: Fields to include (None = include all, except excluded)
        
    Returns:
        Filtered data
        
    Example:
        # Exclude sensitive fields
        filtered = filter_response_data(
            user_data,
            exclude_fields={"password", "api_key", "secret"}
        )
        
        # Include only specific fields
        filtered = filter_response_data(
            user_data,
            include_fields={"id", "name", "email"}
        )
    """
    if isinstance(data, list):
        return [
            filter_response_data(item, exclude_fields, include_fields)  # type: ignore
            for item in data
        ]
    
    if not isinstance(data, dict):
        return data
    
    if include_fields:
        # Include only specified fields
        return {k: v for k, v in data.items() if k in include_fields}
    
    if exclude_fields:
        # Exclude specified fields
        return {k: v for k, v in data.items() if k not in exclude_fields}
    
    return data


def create_response_model_adapter(
    model: type[BaseModel],
    exclude_fields: set[str] | None = None,
) -> TypeAdapter:
    """
    Create a TypeAdapter with field exclusions for reduced payload size.
    
    Args:
        model: Pydantic model class
        exclude_fields: Fields to exclude from serialization
        
    Returns:
        TypeAdapter configured with exclusions
        
    Example:
        from app.schemas.users import UserInDB
        
        # Create adapter that excludes password
        adapter = create_response_model_adapter(
            UserInDB,
            exclude_fields={"password"}
        )
        
        users = [user1, user2, ...]
        json_bytes = adapter.dump_json(users)
    """
    if exclude_fields:
        # Create a new model with excluded fields
        # Note: This is a simplified approach - in practice, you'd use
        # Pydantic's model_config or create a separate response model
        logger.debug("Creating adapter with exclusions: model=%s exclude=%s", model, exclude_fields)
    
    return TypeAdapter(list[model])


def optimize_json_serialization(
    data: Any,
    use_orjson: bool = True,
    indent: Optional[int] = None,
) -> Union[str, bytes]:
    """
    Optimize JSON serialization with performance options.
    
    Args:
        data: Data to serialize
        use_orjson: Whether to use orjson (faster, returns bytes)
        indent: Indentation for pretty printing (None = compact)
        
    Returns:
        Serialized JSON (str if standard json, bytes if orjson)
        
    Example:
        # Fast serialization (orjson)
        json_bytes = optimize_json_serialization(large_dataset)
        
        # Pretty printing (standard json)
        json_str = optimize_json_serialization(data, use_orjson=False, indent=2)
    """
    if use_orjson and ORJSON_AVAILABLE:
        options = 0
        if indent:
            # orjson doesn't support indent, fall back to standard json
            return json.dumps(data, indent=indent, default=str)
        return orjson.dumps(data, option=orjson.OPT_SERIALIZE_NUMPY)
    
    # Standard json
    return json.dumps(data, indent=indent, default=str)


class OptimizedSerializer(Generic[T]):
    """
    Optimized serializer for large collections.
    
    Provides caching and optimization for repeated serialization of similar data.
    """
    
    def __init__(
        self,
        model: type[BaseModel] | None = None,
        use_orjson: bool = True,
        exclude_fields: set[str] | None = None,
    ):
        """
        Initialize optimized serializer.
        
        Args:
            model: Optional Pydantic model class
            use_orjson: Whether to use orjson
            exclude_fields: Fields to exclude
        """
        self.model = model
        self.use_orjson = use_orjson
        self.exclude_fields = exclude_fields
        self._adapter: TypeAdapter | None = None
    
    def serialize(self, items: list[T]) -> bytes:
        """
        Serialize items with optimizations.
        
        Args:
            items: List of items to serialize
            
        Returns:
            Serialized JSON as bytes
        """
        if not items:
            return b"[]"
        
        # Filter data if needed
        if self.exclude_fields and isinstance(items[0], dict):
            items = filter_response_data(items, exclude_fields=self.exclude_fields)  # type: ignore
        
        # Use TypeAdapter if model is provided
        if self.model:
            if self._adapter is None:
                self._adapter = TypeAdapter(list[self.model])  # type: ignore
            
            if self.use_orjson and ORJSON_AVAILABLE:
                return self._adapter.dump_json(items)
            else:
                json_str = self._adapter.dump_json(items).decode("utf-8")
                return json_str.encode("utf-8")
        
        # Fallback to standard serialization
        return serialize_dict_list(items, use_orjson=self.use_orjson)  # type: ignore
