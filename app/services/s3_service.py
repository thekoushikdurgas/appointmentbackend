"""Service layer for AWS S3 operations."""

import csv
import io
from typing import List, Optional

import aioboto3
from botocore.exceptions import ClientError

from app.core.config import get_settings
from app.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


class S3Service:
    """Service for async S3 operations."""

    def __init__(self) -> None:
        """Initialize S3 service with settings."""
        self.bucket_name = settings.S3_BUCKET_NAME
        self.region = settings.AWS_REGION
        self.avatars_prefix = settings.S3_AVATARS_PREFIX
        self.exports_prefix = settings.S3_EXPORTS_PREFIX
        self.use_presigned_urls = settings.S3_USE_PRESIGNED_URLS
        self.presigned_expiration = settings.S3_PRESIGNED_URL_EXPIRATION

        # Validate S3 configuration
        # S3_BUCKET_NAME must be configured for S3 operations to work
        # AWS credentials must be configured for S3 operations to work

    def _get_session(self) -> aioboto3.Session:
        """Create and return an aioboto3 session."""
        return aioboto3.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=self.region,
        )

    async def upload_file(
        self,
        file_content: bytes,
        s3_key: str,
        content_type: Optional[str] = None,
    ) -> str:
        """
        Upload a file to S3.

        Args:
            file_content: The file content as bytes
            s3_key: The S3 key (path) where the file should be stored
            content_type: Optional content type (MIME type) for the file

        Returns:
            The S3 key where the file was uploaded

        Raises:
            ValueError: If S3 is not configured
            Exception: If upload fails
        """
        if not self.bucket_name:
            raise ValueError("S3_BUCKET_NAME is not configured")

        # Uploading file to S3 with bucket, key, and size

        session = self._get_session()
        try:
            async with session.client("s3") as s3_client:
                upload_kwargs = {
                    "Bucket": self.bucket_name,
                    "Key": s3_key,
                    "Body": file_content,
                }
                if content_type:
                    upload_kwargs["ContentType"] = content_type

                await s3_client.put_object(**upload_kwargs)
                # File uploaded successfully
                return s3_key
        except ClientError as exc:
            # Upload failed - re-raising with descriptive error
            raise Exception(f"Failed to upload file to S3: {str(exc)}") from exc
        except Exception as exc:
            # Unexpected error during upload - re-raising with descriptive error
            raise Exception(f"Unexpected error uploading file to S3: {str(exc)}") from exc

    async def download_file(self, s3_key: str) -> bytes:
        """
        Download a file from S3.

        Args:
            s3_key: The S3 key (path) of the file to download

        Returns:
            The file content as bytes

        Raises:
            ValueError: If S3 is not configured
            FileNotFoundError: If file doesn't exist
            Exception: If download fails
        """
        if not self.bucket_name:
            raise ValueError("S3_BUCKET_NAME is not configured")

        # Downloading file from S3
        session = self._get_session()
        try:
            async with session.client("s3") as s3_client:
                response = await s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
                file_content = await response["Body"].read()
                # File downloaded successfully
                return file_content
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchKey":
                # File not found in S3
                raise FileNotFoundError(f"File not found in S3: {s3_key}") from exc
            # Download failed - re-raising with descriptive error
            raise Exception(f"Failed to download file from S3: {str(exc)}") from exc
        except Exception as exc:
            # Unexpected error during download - re-raising with descriptive error
            raise Exception(f"Unexpected error downloading file from S3: {str(exc)}") from exc

    async def delete_file(self, s3_key: str) -> bool:
        """
        Delete a file from S3.

        Args:
            s3_key: The S3 key (path) of the file to delete

        Returns:
            True if deleted successfully, False if file doesn't exist

        Raises:
            ValueError: If S3 is not configured
            Exception: If deletion fails
        """
        if not self.bucket_name:
            raise ValueError("S3_BUCKET_NAME is not configured")

        # Deleting file from S3
        session = self._get_session()
        try:
            async with session.client("s3") as s3_client:
                await s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
                # File deleted successfully
                return True
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchKey":
                # File not found (may already be deleted)
                return False
            # Delete failed - re-raising with descriptive error
            raise Exception(f"Failed to delete file from S3: {str(exc)}") from exc
        except Exception as exc:
            # Unexpected error during deletion - re-raising with descriptive error
            raise Exception(f"Unexpected error deleting file from S3: {str(exc)}") from exc

    async def generate_presigned_url(
        self,
        s3_key: str,
        expiration: Optional[int] = None,
    ) -> str:
        """
        Generate a presigned URL for temporary access to an S3 object.

        Args:
            s3_key: The S3 key (path) of the file
            expiration: Expiration time in seconds (defaults to S3_PRESIGNED_URL_EXPIRATION)

        Returns:
            A presigned URL string

        Raises:
            ValueError: If S3 is not configured
            Exception: If URL generation fails
        """
        if not self.bucket_name:
            raise ValueError("S3_BUCKET_NAME is not configured")

        expiration = expiration or self.presigned_expiration
        # Generating presigned URL for temporary access
        session = self._get_session()
        try:
            async with session.client("s3") as s3_client:
                url = await s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.bucket_name, "Key": s3_key},
                    ExpiresIn=expiration,
                )
                # Presigned URL generated successfully
                return url
        except ClientError as exc:
            # Presigned URL generation failed - re-raising with descriptive error
            raise Exception(f"Failed to generate presigned URL: {str(exc)}") from exc
        except Exception as exc:
            # Unexpected error during presigned URL generation - re-raising with descriptive error
            raise Exception(f"Unexpected error generating presigned URL: {str(exc)}") from exc

    def get_public_url(self, s3_key: str) -> str:
        """
        Generate a public URL for an S3 object (assumes bucket is public).

        Args:
            s3_key: The S3 key (path) of the file

        Returns:
            A public URL string
        """
        return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"

    def is_s3_key(self, path: str) -> bool:
        """
        Check if a path is an S3 key (starts with a known prefix or is a full S3 URL).

        Args:
            path: The path to check

        Returns:
            True if it appears to be an S3 key/URL
        """
        if not path:
            return False
        # Check if it's a full S3 URL
        if path.startswith("https://") and ".s3." in path:
            return True
        # Check if it starts with our known prefixes
        if path.startswith(self.avatars_prefix) or path.startswith(self.exports_prefix):
            return True
        # Check if it doesn't start with / (local path indicator)
        if not path.startswith("/") and not path.startswith("./"):
            return True
        return False

    async def list_csv_files(self, prefix: str = "", bucket_name: Optional[str] = None) -> List[dict]:
        """
        List all CSV files in the S3 bucket.

        Args:
            prefix: Optional prefix to filter files
            bucket_name: Optional bucket name (defaults to self.bucket_name or S3_V3_BUCKET_NAME)

        Returns:
            List of dictionaries with file information (key, size, last_modified, etc.)

        Raises:
            ValueError: If S3 is not configured
            Exception: If listing fails
        """
        bucket = bucket_name or self.bucket_name or settings.S3_V3_BUCKET_NAME
        if not bucket:
            raise ValueError("S3 bucket name is not configured")

        # Listing CSV files in S3 bucket
        session = self._get_session()
        files = []
        try:
            async with session.client("s3") as s3_client:
                # First verify bucket exists
                try:
                    await s3_client.head_bucket(Bucket=bucket)
                    # Bucket exists and is accessible
                except ClientError as e:
                    error_code = e.response.get("Error", {}).get("Code", "")
                    if error_code == "404":
                        raise ValueError(f"Bucket '{bucket}' does not exist") from e
                    elif error_code == "403":
                        raise ValueError(f"Access denied to bucket '{bucket}' - check permissions") from e
                    else:
                        raise ValueError(f"Error accessing bucket '{bucket}': {error_code}") from e
                
                # List objects
                paginator = s3_client.get_paginator("list_objects_v2")
                total_objects = 0
                async for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                    contents = page.get("Contents", [])
                    total_objects += len(contents)
                    for obj in contents:
                        key = obj.get("Key", "")
                        if key.lower().endswith(".csv"):
                            files.append({
                                "key": key,
                                "filename": key.split("/")[-1],
                                "size": obj.get("Size"),
                                "last_modified": obj.get("LastModified"),
                                "content_type": obj.get("ContentType"),
                            })
                
                # No CSV files found (prefix specified or bucket empty)
                return files
        except ClientError as exc:
            # Listing failed - re-raising with descriptive error
            raise Exception(f"Failed to list CSV files in S3: {str(exc)}") from exc
        except Exception as exc:
            # Unexpected error during listing - re-raising with descriptive error
            raise Exception(f"Unexpected error listing CSV files in S3: {str(exc)}") from exc

    async def get_csv_file_info(self, s3_key: str, bucket_name: Optional[str] = None) -> dict:
        """
        Get metadata/information about a CSV file in S3.

        Args:
            s3_key: The S3 object key (full path)
            bucket_name: Optional bucket name (defaults to self.bucket_name or S3_V3_BUCKET_NAME)

        Returns:
            Dictionary with file information

        Raises:
            ValueError: If S3 is not configured
            FileNotFoundError: If file doesn't exist
            Exception: If operation fails
        """
        bucket = bucket_name or self.bucket_name or settings.S3_V3_BUCKET_NAME
        if not bucket:
            raise ValueError("S3 bucket name is not configured")

        # Getting CSV file metadata from S3
        session = self._get_session()
        try:
            async with session.client("s3") as s3_client:
                response = await s3_client.head_object(Bucket=bucket, Key=s3_key)
                return {
                    "key": s3_key,
                    "filename": s3_key.split("/")[-1],
                    "size": response.get("ContentLength"),
                    "last_modified": response.get("LastModified"),
                    "content_type": response.get("ContentType"),
                }
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            is_not_found = error_code in ("404", "NoSuchKey")
            if is_not_found:
                # CSV file not found in S3
                raise FileNotFoundError(f"CSV file not found in S3: {s3_key}") from exc
            # Getting file info failed - re-raising with descriptive error
            raise Exception(f"Failed to get CSV file info from S3: {str(exc)}") from exc
        except Exception as exc:
            # Unexpected error getting file info - re-raising with descriptive error
            raise Exception(f"Unexpected error getting CSV file info from S3: {str(exc)}") from exc

    async def read_csv_paginated(
        self,
        s3_key: str,
        limit: int = 100,
        offset: int = 0,
        bucket_name: Optional[str] = None,
    ) -> tuple[List[dict], Optional[int]]:
        """
        Read paginated CSV data from S3.

        Args:
            s3_key: The S3 object key (full path)
            limit: Maximum number of rows to return
            offset: Number of rows to skip
            bucket_name: Optional bucket name (defaults to self.bucket_name or S3_V3_BUCKET_NAME)

        Returns:
            Tuple of (list of row dictionaries, total row count if available)

        Raises:
            ValueError: If S3 is not configured
            FileNotFoundError: If file doesn't exist
            Exception: If reading fails
        """
        bucket = bucket_name or self.bucket_name or settings.S3_V3_BUCKET_NAME
        if not bucket:
            raise ValueError("S3 bucket name is not configured")

        # Reading paginated CSV data from S3
        session = self._get_session()
        rows = []
        try:
            async with session.client("s3") as s3_client:
                response = await s3_client.get_object(Bucket=bucket, Key=s3_key)
                body = response["Body"]
                
                # Read and decode the CSV file
                content = await body.read()
                content_str = content.decode("utf-8")
                
                # Parse CSV
                csv_reader = csv.DictReader(io.StringIO(content_str))
                
                # Skip offset rows
                for _ in range(offset):
                    try:
                        next(csv_reader)
                    except StopIteration:
                        break
                
                # Read limit rows
                for _ in range(limit):
                    try:
                        row = next(csv_reader)
                        rows.append(row)
                    except StopIteration:
                        break
                
                # Try to get total count by reading the entire file (if small enough)
                # For large files, we'll return None for total_rows
                total_rows = None
                if len(content) < 10 * 1024 * 1024:  # Only count if file is < 10MB
                    csv_reader = csv.DictReader(io.StringIO(content_str))
                    total_rows = sum(1 for _ in csv_reader)
                
                # Returning paginated rows
                return rows, total_rows
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            is_not_found = error_code in ("404", "NoSuchKey")
            if is_not_found:
                # CSV file not found in S3
                raise FileNotFoundError(f"CSV file not found in S3: {s3_key}") from exc
            # Reading CSV failed - re-raising with descriptive error
            raise Exception(f"Failed to read CSV from S3: {str(exc)}") from exc
        except Exception as exc:
            # Unexpected error reading CSV - re-raising with descriptive error
            raise Exception(f"Unexpected error reading CSV from S3: {str(exc)}") from exc

    async def download_csv_file(self, s3_key: str, bucket_name: Optional[str] = None) -> bytes:
        """
        Download a CSV file from S3.

        Args:
            s3_key: The S3 object key (full path)
            bucket_name: Optional bucket name (defaults to self.bucket_name or S3_V3_BUCKET_NAME)

        Returns:
            The file content as bytes

        Raises:
            ValueError: If S3 is not configured
            FileNotFoundError: If file doesn't exist
            Exception: If download fails
        """
        bucket = bucket_name or self.bucket_name or settings.S3_V3_BUCKET_NAME
        if not bucket:
            raise ValueError("S3 bucket name is not configured")

        # Downloading CSV file from S3
        session = self._get_session()
        try:
            async with session.client("s3") as s3_client:
                # Getting object from S3
                response = await s3_client.get_object(Bucket=bucket, Key=s3_key)
                file_content = await response["Body"].read()
                # CSV file downloaded successfully
                return file_content
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            is_not_found = error_code in ("404", "NoSuchKey")
            if is_not_found:
                # CSV file not found - attempting to list bucket contents for debugging
                try:
                    # Listing files in bucket to help diagnose the issue
                    async with session.client("s3") as s3_client_debug:
                        paginator = s3_client_debug.get_paginator("list_objects_v2")
                        all_files = []
                        async for page in paginator.paginate(Bucket=bucket, MaxKeys=50):
                            contents = page.get("Contents", [])
                            for obj in contents:
                                all_files.append(obj.get("Key", ""))
                        
                        if all_files:
                            # Check if file exists with different case or path
                            target_lower = s3_key.lower()
                            similar_files = [f for f in all_files if target_lower in f.lower() or any(part in f.lower() for part in s3_key.split("/") if part)]
                except Exception:
                    # Could not list files for debugging (non-critical)
                    pass
                raise FileNotFoundError(f"CSV file not found in S3 bucket '{bucket}': {s3_key}") from exc
            # Download failed - re-raising with descriptive error
            raise Exception(f"Failed to download CSV file from S3: {str(exc)}") from exc
        except Exception as exc:
            # Unexpected error during download - re-raising with descriptive error
            raise Exception(f"Unexpected error downloading CSV file from S3: {str(exc)}") from exc

    async def initiate_multipart_upload(
        self,
        file_key: str,
        content_type: str = "application/octet-stream",
        bucket_name: Optional[str] = None,
    ) -> dict:
        """
        Initiate S3 multipart upload and return upload_id.

        Args:
            file_key: The S3 key (path) where the file should be stored
            content_type: Content type (MIME type) for the file
            bucket_name: Optional bucket name (defaults to self.bucket_name)

        Returns:
            Dictionary with upload_id and file_key

        Raises:
            ValueError: If S3 is not configured
            Exception: If initiation fails
        """
        bucket = bucket_name or self.bucket_name
        if not bucket:
            raise ValueError("S3_BUCKET_NAME is not configured")

        session = self._get_session()
        try:
            async with session.client("s3") as s3_client:
                response = await s3_client.create_multipart_upload(
                    Bucket=bucket,
                    Key=file_key,
                    ContentType=content_type,
                    ServerSideEncryption="AES256",
                )
                return {
                    "upload_id": response["UploadId"],
                    "file_key": response["Key"],
                }
        except ClientError as exc:
            raise Exception(f"Failed to initiate multipart upload: {str(exc)}") from exc
        except Exception as exc:
            raise Exception(f"Unexpected error initiating multipart upload: {str(exc)}") from exc

    async def generate_presigned_upload_url(
        self,
        file_key: str,
        upload_id: str,
        part_number: int,
        expiration: int = 3600,
        bucket_name: Optional[str] = None,
    ) -> str:
        """
        Generate presigned URL for uploading a single part.

        Args:
            file_key: The S3 key (path) of the file
            upload_id: The multipart upload ID from initiate_multipart_upload
            part_number: Part number (1-indexed)
            expiration: Expiration time in seconds (defaults to 3600)
            bucket_name: Optional bucket name (defaults to self.bucket_name)

        Returns:
            A presigned URL string for uploading the part

        Raises:
            ValueError: If S3 is not configured
            Exception: If URL generation fails
        """
        bucket = bucket_name or self.bucket_name
        if not bucket:
            raise ValueError("S3_BUCKET_NAME is not configured")

        session = self._get_session()
        try:
            async with session.client("s3") as s3_client:
                url = await s3_client.generate_presigned_url(
                    "upload_part",
                    Params={
                        "Bucket": bucket,
                        "Key": file_key,
                        "UploadId": upload_id,
                        "PartNumber": part_number,
                    },
                    ExpiresIn=expiration,
                )
                return url
        except ClientError as exc:
            raise Exception(f"Failed to generate presigned upload URL: {str(exc)}") from exc
        except Exception as exc:
            raise Exception(f"Unexpected error generating presigned upload URL: {str(exc)}") from exc

    async def complete_multipart_upload(
        self,
        file_key: str,
        upload_id: str,
        parts: List[dict],
        bucket_name: Optional[str] = None,
    ) -> dict:
        """
        Complete multipart upload with all parts.

        Args:
            file_key: The S3 key (path) of the file
            upload_id: The multipart upload ID
            parts: List of dicts with PartNumber and ETag: [{"PartNumber": 1, "ETag": "etag1"}, ...]
            bucket_name: Optional bucket name (defaults to self.bucket_name)

        Returns:
            Dictionary with location, key, and etag

        Raises:
            ValueError: If S3 is not configured
            Exception: If completion fails
        """
        bucket = bucket_name or self.bucket_name
        if not bucket:
            raise ValueError("S3_BUCKET_NAME is not configured")

        session = self._get_session()
        try:
            async with session.client("s3") as s3_client:
                response = await s3_client.complete_multipart_upload(
                    Bucket=bucket,
                    Key=file_key,
                    UploadId=upload_id,
                    MultipartUpload={"Parts": parts},
                )
                return {
                    "location": response.get("Location"),
                    "key": response.get("Key"),
                    "etag": response.get("ETag"),
                }
        except ClientError as exc:
            raise Exception(f"Failed to complete multipart upload: {str(exc)}") from exc
        except Exception as exc:
            raise Exception(f"Unexpected error completing multipart upload: {str(exc)}") from exc

    async def abort_multipart_upload(
        self,
        file_key: str,
        upload_id: str,
        bucket_name: Optional[str] = None,
    ) -> None:
        """
        Abort incomplete multipart upload.

        Args:
            file_key: The S3 key (path) of the file
            upload_id: The multipart upload ID
            bucket_name: Optional bucket name (defaults to self.bucket_name)

        Raises:
            ValueError: If S3 is not configured
            Exception: If abort fails
        """
        bucket = bucket_name or self.bucket_name
        if not bucket:
            raise ValueError("S3_BUCKET_NAME is not configured")

        session = self._get_session()
        try:
            async with session.client("s3") as s3_client:
                await s3_client.abort_multipart_upload(
                    Bucket=bucket,
                    Key=file_key,
                    UploadId=upload_id,
                )
        except ClientError as exc:
            # Don't raise if upload doesn't exist (already aborted or completed)
            error_code = exc.response.get("Error", {}).get("Code", "")
            if error_code not in ("NoSuchUpload", "404"):
                raise Exception(f"Failed to abort multipart upload: {str(exc)}") from exc
        except Exception as exc:
            raise Exception(f"Unexpected error aborting multipart upload: {str(exc)}") from exc

    async def list_multipart_parts(
        self,
        file_key: str,
        upload_id: str,
        bucket_name: Optional[str] = None,
    ) -> List[dict]:
        """
        List uploaded parts for a multipart upload (for resume functionality).

        Args:
            file_key: The S3 key (path) of the file
            upload_id: The multipart upload ID
            bucket_name: Optional bucket name (defaults to self.bucket_name)

        Returns:
            List of dictionaries with part information (PartNumber, ETag, Size, etc.)

        Raises:
            ValueError: If S3 is not configured
            Exception: If listing fails
        """
        bucket = bucket_name or self.bucket_name
        if not bucket:
            raise ValueError("S3_BUCKET_NAME is not configured")

        session = self._get_session()
        parts = []
        try:
            async with session.client("s3") as s3_client:
                paginator = s3_client.get_paginator("list_parts")
                async for page in paginator.paginate(
                    Bucket=bucket,
                    Key=file_key,
                    UploadId=upload_id,
                ):
                    parts.extend(page.get("Parts", []))
                return parts
        except ClientError as exc:
            raise Exception(f"Failed to list multipart parts: {str(exc)}") from exc
        except Exception as exc:
            raise Exception(f"Unexpected error listing multipart parts: {str(exc)}") from exc

