"""Optimized streaming response utilities for large datasets.

This module provides utilities for streaming large datasets efficiently
in JSON, CSV, and JSONL formats with optimized chunk sizes and memory management.

Best practices:
- Use streaming for datasets >10k rows
- Optimize chunk size based on data type and network conditions
- Use JSONL for very large datasets (one object per line)
- Use CSV for tabular data exports
- Use JSON for structured nested data (smaller datasets)
"""

from __future__ import annotations

import asyncio
import csv
import io
import json
from collections.abc import AsyncIterator, Iterator
from typing import Any, Optional

from app.core.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


def optimize_chunk_size(
    data_type: str = "json",
    avg_item_size: Optional[int] = None,
    target_chunk_size: int = 1024 * 1024,  # 1MB default
) -> int:
    """
    Calculate optimal chunk size based on data type and item size.
    
    Args:
        data_type: Data format ("json", "csv", "jsonl")
        avg_item_size: Average size of a single item in bytes (estimated)
        target_chunk_size: Target chunk size in bytes (default: 1MB)
        
    Returns:
        Optimal number of items per chunk
    """
    if avg_item_size is None:
        # Default estimates based on data type
        if data_type == "csv":
            avg_item_size = 200  # ~200 bytes per CSV row
        elif data_type == "jsonl":
            avg_item_size = 500  # ~500 bytes per JSONL line
        else:  # json
            avg_item_size = 1000  # ~1KB per JSON object
    
    if avg_item_size <= 0:
        avg_item_size = 1000
    
    items_per_chunk = max(1, target_chunk_size // avg_item_size)
    
    # Cap at reasonable limits
    if data_type == "csv":
        items_per_chunk = min(items_per_chunk, 10000)  # Max 10k CSV rows per chunk
    elif data_type == "jsonl":
        items_per_chunk = min(items_per_chunk, 5000)  # Max 5k JSONL lines per chunk
    else:  # json
        items_per_chunk = min(items_per_chunk, 1000)  # Max 1k JSON objects per chunk
    
    return items_per_chunk


def stream_jsonl(
    items: Iterator[dict[str, Any]] | AsyncIterator[dict[str, Any]],
    chunk_size: Optional[int] = None,
) -> Iterator[bytes]:
    """
    Stream items as JSONL (newline-delimited JSON) format.
    
    JSONL is ideal for very large datasets as it's:
    - Memory efficient (one object per line)
    - Easy to parse incrementally
    - Supports streaming without loading all data
    
    Args:
        items: Iterator or AsyncIterator of dictionaries
        chunk_size: Number of items to buffer before yielding (None = auto-optimize)
        
    Yields:
        Bytes chunks of JSONL data
        
    Example:
        async def get_contacts():
            async for contact in db.stream_contacts():
                yield contact
        
        for chunk in stream_jsonl(get_contacts()):
            yield chunk
    """
    if chunk_size is None:
        chunk_size = optimize_chunk_size("jsonl")
    
    buffer = io.BytesIO()
    count = 0
    
    async def _async_stream():
        nonlocal buffer, count
        async for item in items:  # type: ignore
            json_line = json.dumps(item, default=str, ensure_ascii=False) + "\n"
            buffer.write(json_line.encode("utf-8"))
            count += 1
            
            if count >= chunk_size:
                chunk = buffer.getvalue()
                buffer = io.BytesIO()
                count = 0
                yield chunk
        
        # Yield remaining data
        if count > 0:
            yield buffer.getvalue()
    
    def _sync_stream():
        nonlocal buffer, count
        for item in items:  # type: ignore
            json_line = json.dumps(item, default=str, ensure_ascii=False) + "\n"
            buffer.write(json_line.encode("utf-8"))
            count += 1
            
            if count >= chunk_size:
                chunk = buffer.getvalue()
                buffer = io.BytesIO()
                count = 0
                yield chunk
        
        # Yield remaining data
        if count > 0:
            yield buffer.getvalue()
    
    # Detect if items is async or sync
    if hasattr(items, "__aiter__"):
        # Async iterator - need to handle differently
        # For now, return sync wrapper that will be used with async generator
        
        async def async_gen():
            async for chunk in _async_stream():
                yield chunk
        
        # Return a sync iterator that wraps async
        # Note: This is a simplified version - in practice, you'd use asyncio.run or similar
        return _sync_stream()  # Fallback to sync for now
    
    return _sync_stream()


async def stream_jsonl_async(
    items: AsyncIterator[dict[str, Any]],
    chunk_size: Optional[int] = None,
) -> AsyncIterator[bytes]:
    """
    Stream items as JSONL format (async version).
    
    Args:
        items: AsyncIterator of dictionaries
        chunk_size: Number of items to buffer before yielding
        
    Yields:
        Bytes chunks of JSONL data
    """
    if chunk_size is None:
        chunk_size = optimize_chunk_size("jsonl")
    
    buffer = io.BytesIO()
    count = 0
    
    async for item in items:
        json_line = json.dumps(item, default=str, ensure_ascii=False) + "\n"
        buffer.write(json_line.encode("utf-8"))
        count += 1
        
        if count >= chunk_size:
            chunk = buffer.getvalue()
            buffer = io.BytesIO()
            count = 0
            yield chunk
    
    # Yield remaining data
    if count > 0:
        yield buffer.getvalue()


def stream_csv(
    items: Iterator[dict[str, Any]],
    headers: Optional[list[str]] = None,
    chunk_size: Optional[int] = None,
) -> Iterator[bytes]:
    """
    Stream items as CSV format.
    
    CSV is ideal for tabular data exports and spreadsheet compatibility.
    
    Args:
        items: Iterator of dictionaries
        headers: Optional list of column headers (auto-detected from first item if None)
        chunk_size: Number of rows to buffer before yielding (None = auto-optimize)
        
    Yields:
        Bytes chunks of CSV data
        
    Example:
        async def get_contacts():
            async for contact in db.stream_contacts():
                yield {"id": contact.id, "name": contact.name, "email": contact.email}
        
        for chunk in stream_csv(get_contacts(), headers=["id", "name", "email"]):
            yield chunk
    """
    if chunk_size is None:
        chunk_size = optimize_chunk_size("csv")
    
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=headers, extrasaction="ignore")
    headers_written = False
    count = 0
    
    for item in items:
        # Write headers on first item
        if not headers_written:
            if headers is None:
                # Auto-detect headers from first item
                headers = list(item.keys())
                writer.fieldnames = headers
            writer.writeheader()
            headers_written = True
        
        writer.writerow(item)
        count += 1
        
        if count >= chunk_size:
            chunk = buffer.getvalue().encode("utf-8")
            buffer = io.StringIO()
            writer = csv.DictWriter(buffer, fieldnames=headers, extrasaction="ignore")
            count = 0
            yield chunk
    
    # Yield remaining data
    if count > 0:
        yield buffer.getvalue().encode("utf-8")


def stream_json_array(
    items: Iterator[dict[str, Any]],
    chunk_size: Optional[int] = None,
) -> Iterator[bytes]:
    """
    Stream items as JSON array format.
    
    Note: JSON arrays require closing bracket, so this streams partial arrays.
    For very large datasets, prefer JSONL format.
    
    Args:
        items: Iterator of dictionaries
        chunk_size: Number of items per chunk (None = auto-optimize)
        
    Yields:
        Bytes chunks of JSON array data
        
    Example:
        # First chunk: '[{"id": 1}, {"id": 2}, '
        # Middle chunks: '{"id": 3}, {"id": 4}, '
        # Last chunk: '{"id": 5}]'
    """
    if chunk_size is None:
        chunk_size = optimize_chunk_size("json")
    
    buffer = io.BytesIO()
    count = 0
    first_chunk = True
    
    for item in items:
        if first_chunk:
            buffer.write(b"[")
            first_chunk = False
        else:
            buffer.write(b", ")
        
        json_str = json.dumps(item, default=str, ensure_ascii=False)
        buffer.write(json_str.encode("utf-8"))
        count += 1
        
        if count >= chunk_size:
            chunk = buffer.getvalue()
            buffer = io.BytesIO()
            count = 0
            yield chunk
    
    # Yield remaining data with closing bracket
    if count > 0:
        remaining = buffer.getvalue()
        remaining += b"]"
        yield remaining
    elif first_chunk:
        # Empty array
        yield b"[]"


async def stream_json_array_async(
    items: AsyncIterator[dict[str, Any]],
    chunk_size: Optional[int] = None,
) -> AsyncIterator[bytes]:
    """
    Stream items as JSON array format (async version).
    
    Args:
        items: AsyncIterator of dictionaries
        chunk_size: Number of items per chunk
        
    Yields:
        Bytes chunks of JSON array data
    """
    if chunk_size is None:
        chunk_size = optimize_chunk_size("json")
    
    buffer = io.BytesIO()
    count = 0
    first_chunk = True
    
    async for item in items:
        if first_chunk:
            buffer.write(b"[")
            first_chunk = False
        else:
            buffer.write(b", ")
        
        json_str = json.dumps(item, default=str, ensure_ascii=False)
        buffer.write(json_str.encode("utf-8"))
        count += 1
        
        if count >= chunk_size:
            chunk = buffer.getvalue()
            buffer = io.BytesIO()
            count = 0
            yield chunk
    
    # Yield remaining data with closing bracket
    if count > 0:
        remaining = buffer.getvalue()
        remaining += b"]"
        yield remaining
    elif first_chunk:
        # Empty array
        yield b"[]"


def create_streaming_response_generator(
    items: Iterator[dict[str, Any]] | AsyncIterator[dict[str, Any]],
    format: str = "jsonl",
    headers: Optional[list[str]] = None,
    chunk_size: Optional[int] = None,
) -> Iterator[bytes] | AsyncIterator[bytes]:
    """
    Create a streaming response generator based on format.
    
    Args:
        items: Iterator or AsyncIterator of dictionaries
        format: Output format ("jsonl", "csv", "json")
        headers: Column headers for CSV (optional)
        chunk_size: Chunk size override (None = auto-optimize)
        
    Returns:
        Iterator or AsyncIterator of bytes chunks
        
    Example:
        generator = create_streaming_response_generator(
            get_contacts(),
            format="jsonl",
            chunk_size=1000
        )
    """
    format_lower = format.lower()
    
    if format_lower == "jsonl":
        if hasattr(items, "__aiter__"):
            return stream_jsonl_async(items, chunk_size)  # type: ignore
        return stream_jsonl(items, chunk_size)  # type: ignore
    elif format_lower == "csv":
        if hasattr(items, "__aiter__"):
            # CSV streaming from async iterator - convert to sync for now
            # In practice, you'd use a different approach
            raise ValueError("CSV streaming from async iterator not yet supported")
        return stream_csv(items, headers, chunk_size)  # type: ignore
    elif format_lower == "json":
        if hasattr(items, "__aiter__"):
            return stream_json_array_async(items, chunk_size)  # type: ignore
        return stream_json_array(items, chunk_size)  # type: ignore
    else:
        raise ValueError(f"Unsupported format: {format}. Use 'jsonl', 'csv', or 'json'")


def get_content_type_for_format(format: str) -> str:
    """
    Get appropriate Content-Type header for format.
    
    Args:
        format: Format name ("jsonl", "csv", "json")
        
    Returns:
        Content-Type string
    """
    format_lower = format.lower()
    content_types = {
        "jsonl": "application/x-ndjson",
        "csv": "text/csv",
        "json": "application/json",
    }
    return content_types.get(format_lower, "application/octet-stream")

