"""Optimized chunked file upload utilities with resumable support.

This module provides utilities for handling large file uploads efficiently
using chunked uploads, resumable uploads, and optimized chunk sizing.

Best practices:
- Use chunked uploads for files >10MB
- Optimize chunk size based on file type and network conditions
- Support resumable uploads for interrupted transfers
- Validate file size and type early
- Use async file I/O for non-blocking operations
"""

from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path
from typing import Callable, Optional

import aiofiles
from fastapi import UploadFile

from app.core.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


def calculate_optimal_chunk_size(
    file_size: Optional[int] = None,
    file_type: Optional[str] = None,
    network_condition: str = "normal",
) -> int:
    """
    Calculate optimal chunk size for file uploads.
    
    Args:
        file_size: Total file size in bytes (None = use default)
        file_type: File type/MIME type (for type-specific optimization)
        network_condition: Network condition ("slow", "normal", "fast")
        
    Returns:
        Optimal chunk size in bytes
        
    Example:
        chunk_size = calculate_optimal_chunk_size(
            file_size=100 * 1024 * 1024,  # 100MB
            file_type="video/mp4",
            network_condition="normal"
        )
    """
    # Base chunk size from settings
    base_chunk_size = settings.MAX_UPLOAD_CHUNK_SIZE
    
    # Adjust based on network condition
    network_multipliers = {
        "slow": 0.5,  # Smaller chunks for slow networks
        "normal": 1.0,
        "fast": 2.0,  # Larger chunks for fast networks
    }
    multiplier = network_multipliers.get(network_condition, 1.0)
    
    # Adjust based on file type
    if file_type:
        # Video files benefit from larger chunks
        if file_type.startswith("video/"):
            multiplier *= 1.5
        # Images can use smaller chunks
        elif file_type.startswith("image/"):
            multiplier *= 0.8
        # Text files can use smaller chunks
        elif file_type.startswith("text/") or file_type.endswith("/csv"):
            multiplier *= 0.5
    
    # Adjust based on file size
    if file_size:
        # Very large files (>1GB) benefit from larger chunks
        if file_size > 1024 * 1024 * 1024:
            multiplier *= 2.0
        # Small files (<1MB) can use smaller chunks
        elif file_size < 1024 * 1024:
            multiplier *= 0.5
    
    optimal_size = int(base_chunk_size * multiplier)
    
    # Clamp to reasonable bounds (64KB to 10MB)
    min_chunk_size = 64 * 1024  # 64KB
    max_chunk_size = 10 * 1024 * 1024  # 10MB
    
    optimal_size = max(min_chunk_size, min(optimal_size, max_chunk_size))
    
    return optimal_size


async def save_upload_file_chunked(
    file: UploadFile,
    destination: Path,
    chunk_size: Optional[int] = None,
    max_size: Optional[int] = None,
    progress_callback: Optional[Callable[[int, Optional[int]], Any]] = None,
) -> dict[str, any]:
    """
    Save uploaded file using chunked async I/O.
    
    Args:
        file: FastAPI UploadFile object
        destination: Destination file path
        chunk_size: Chunk size in bytes (None = auto-calculate)
        max_size: Maximum file size in bytes (None = no limit)
        progress_callback: Optional callback for progress updates (bytes_written, total_bytes)
        
    Returns:
        Dictionary with upload metadata:
        - total_bytes: Total bytes written
        - chunks_written: Number of chunks written
        - file_hash: SHA256 hash of file (if calculated)
        - duration_seconds: Upload duration
        
    Raises:
        ValueError: If file size exceeds max_size
        IOError: If file write fails
        
    Example:
        result = await save_upload_file_chunked(
            file,
            Path("/uploads/data.csv"),
            chunk_size=1024 * 1024,  # 1MB chunks
            max_size=100 * 1024 * 1024  # 100MB limit
        )
    """
    if chunk_size is None:
        # Try to get file size from headers
        content_length = file.headers.get("content-length")
        file_size = int(content_length) if content_length else None
        chunk_size = calculate_optimal_chunk_size(
            file_size=file_size,
            file_type=file.content_type,
        )
    
    start_time = time.time()
    total_bytes = 0
    chunks_written = 0
    file_hash = hashlib.sha256()
    
    # Ensure destination directory exists
    destination.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        async with aiofiles.open(destination, "wb") as async_file:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                
                # Check size limit
                total_bytes += len(chunk)
                if max_size and total_bytes > max_size:
                    await async_file.close()
                    destination.unlink(missing_ok=True)
                    raise ValueError(
                        f"File size {total_bytes} exceeds maximum allowed size {max_size} bytes"
                    )
                
                # Write chunk
                await async_file.write(chunk)
                chunks_written += 1
                
                # Update hash
                file_hash.update(chunk)
                
                # Progress callback
                if progress_callback:
                    try:
                        await progress_callback(total_bytes, None)  # total_bytes, total_size
                    except Exception as exc:
                        pass
        
        duration = time.time() - start_time
        hash_hex = file_hash.hexdigest()
        
        return {
            "total_bytes": total_bytes,
            "chunks_written": chunks_written,
            "file_hash": hash_hex,
            "duration_seconds": duration,
            "destination": str(destination),
        }
    
    except Exception as exc:
        # Clean up partial file on error
        destination.unlink(missing_ok=True)
        raise


class ResumableUpload:
    """
    Manager for resumable file uploads.
    
    Supports resuming interrupted uploads by tracking upload progress
    and allowing clients to resume from the last successful chunk.
    """
    
    def __init__(
        self,
        upload_id: str,
        destination: Path,
        total_size: Optional[int] = None,
        chunk_size: Optional[int] = None,
    ):
        """
        Initialize resumable upload.
        
        Args:
            upload_id: Unique upload identifier
            destination: Destination file path
            total_size: Total expected file size (None = unknown)
            chunk_size: Chunk size in bytes
        """
        self.upload_id = upload_id
        self.destination = destination
        self.total_size = total_size
        self.chunk_size = chunk_size or settings.MAX_UPLOAD_CHUNK_SIZE
        self.progress_file = destination.with_suffix(destination.suffix + ".progress")
        self.bytes_written = 0
    
    async def get_upload_status(self) -> dict[str, any]:
        """
        Get current upload status.
        
        Returns:
            Dictionary with upload status:
            - upload_id: Upload identifier
            - bytes_written: Bytes already written
            - total_size: Total expected size (None if unknown)
            - progress_percent: Upload progress percentage (None if total_size unknown)
            - can_resume: Whether upload can be resumed
        """
        if self.progress_file.exists():
            try:
                async with aiofiles.open(self.progress_file, "r") as f:
                    content = await f.read()
                    self.bytes_written = int(content.strip())
            except Exception as exc:
                self.bytes_written = 0
        elif self.destination.exists():
            # File exists but no progress file - assume complete
            self.bytes_written = self.destination.stat().st_size
        
        progress_percent = None
        if self.total_size and self.total_size > 0:
            progress_percent = (self.bytes_written / self.total_size) * 100
        
        return {
            "upload_id": self.upload_id,
            "bytes_written": self.bytes_written,
            "total_size": self.total_size,
            "progress_percent": progress_percent,
            "can_resume": self.destination.exists() and self.bytes_written < (self.total_size or float("inf")),
        }
    
    async def resume_upload(
        self,
        file: UploadFile,
        start_byte: Optional[int] = None,
    ) -> dict[str, any]:
        """
        Resume an interrupted upload.
        
        Args:
            file: FastAPI UploadFile object
            start_byte: Starting byte position (None = use saved progress)
            
    Returns:
            Upload result dictionary (same as save_upload_file_chunked)
        """
        status = await self.get_upload_status()
        
        if start_byte is None:
            start_byte = status["bytes_written"]
        
        # Seek to start position in file
        if start_byte > 0:
            # For UploadFile, we need to read and discard bytes up to start_byte
            # Note: UploadFile doesn't support seek, so we read and discard
            bytes_to_skip = start_byte
            while bytes_to_skip > 0:
                chunk = await file.read(min(bytes_to_skip, self.chunk_size))
                if not chunk:
                    break
                bytes_to_skip -= len(chunk)
        
        # Continue upload from start_byte
        return await self._continue_upload(file, start_byte)
    
    async def _continue_upload(
        self,
        file: UploadFile,
        start_byte: int,
    ) -> dict[str, any]:
        """Continue upload from a specific byte position."""
        total_bytes = start_byte
        chunks_written = 0
        file_hash = hashlib.sha256()
        start_time = time.time()
        
        # Open file in append mode if resuming, write mode if starting fresh
        mode = "ab" if start_byte > 0 else "wb"
        
        try:
            async with aiofiles.open(self.destination, mode) as async_file:
                # If resuming, read existing file to update hash
                if start_byte > 0 and self.destination.exists():
                    async with aiofiles.open(self.destination, "rb") as existing_file:
                        existing_data = await existing_file.read(start_byte)
                        file_hash.update(existing_data)
                
                while True:
                    chunk = await file.read(self.chunk_size)
                    if not chunk:
                        break
                    
                    await async_file.write(chunk)
                    total_bytes += len(chunk)
                    chunks_written += 1
                    file_hash.update(chunk)
                    
                    # Update progress file
                    async with aiofiles.open(self.progress_file, "w") as progress_file:
                        await progress_file.write(str(total_bytes))
                    
                    # Check size limit
                    if self.total_size and total_bytes > self.total_size:
                        raise ValueError(f"File size exceeds expected size: {total_bytes} > {self.total_size}")
            
            # Upload complete - remove progress file
            self.progress_file.unlink(missing_ok=True)
            
            duration = time.time() - start_time
            hash_hex = file_hash.hexdigest()
            
            return {
                "total_bytes": total_bytes,
                "chunks_written": chunks_written,
                "file_hash": hash_hex,
                "duration_seconds": duration,
                "destination": str(self.destination),
                "resumed": start_byte > 0,
            }
        
        except Exception as exc:
            raise
    
    async def cleanup(self) -> None:
        """Clean up upload files (progress and partial destination)."""
        self.progress_file.unlink(missing_ok=True)
        if self.destination.exists():
            # Only remove if upload is incomplete
            status = await self.get_upload_status()
            if status["bytes_written"] < (self.total_size or float("inf")):
                self.destination.unlink(missing_ok=True)


async def validate_file_upload(
    file: UploadFile,
    allowed_types: Optional[list[str]] = None,
    max_size: Optional[int] = None,
    check_content: bool = True,
) -> dict[str, any]:
    """
    Validate file upload before processing.
    
    Args:
        file: FastAPI UploadFile object
        allowed_types: List of allowed MIME types (None = any)
        max_size: Maximum file size in bytes (None = no limit)
        check_content: Whether to validate file content (magic bytes)
        
    Returns:
        Dictionary with validation results:
        - valid: Whether file is valid
        - errors: List of error messages
        - file_size: Detected file size
        - content_type: Detected content type
        
    Example:
        validation = await validate_file_upload(
            file,
            allowed_types=["text/csv", "application/vnd.ms-excel"],
            max_size=10 * 1024 * 1024  # 10MB
        )
        if not validation["valid"]:
            raise HTTPException(400, detail=validation["errors"])
    """
    errors = []
    
    # Check filename
    if not file.filename:
        errors.append("Filename is required")
    
    # Check content type
    content_type = file.content_type
    if allowed_types and content_type not in allowed_types:
        errors.append(f"File type {content_type} not allowed. Allowed types: {allowed_types}")
    
    # Check file size
    content_length = file.headers.get("content-length")
    file_size = int(content_length) if content_length else None
    
    if file_size and max_size and file_size > max_size:
        errors.append(f"File size {file_size} exceeds maximum allowed size {max_size} bytes")
    
    # Content validation would go here (magic bytes, etc.)
    # For now, we skip it as it requires reading the file
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "file_size": file_size,
        "content_type": content_type,
    }

