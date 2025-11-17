"""Service layer for AWS S3 operations."""

import io
from datetime import timedelta
from typing import Optional

import aioboto3
from botocore.exceptions import ClientError

from app.core.config import get_settings
from app.core.logging import get_logger

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
        if not self.bucket_name:
            logger.warning("S3_BUCKET_NAME not configured. S3 operations will fail.")
        if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
            logger.warning("AWS credentials not configured. S3 operations will fail.")

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

        logger.debug("Uploading file to S3: bucket=%s key=%s size=%d", self.bucket_name, s3_key, len(file_content))

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
                logger.debug("File uploaded successfully: key=%s", s3_key)
                return s3_key
        except ClientError as exc:
            logger.exception("Failed to upload file to S3: key=%s error=%s", s3_key, str(exc))
            raise Exception(f"Failed to upload file to S3: {str(exc)}") from exc
        except Exception as exc:
            logger.exception("Unexpected error uploading file to S3: key=%s", s3_key)
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

        logger.debug("Downloading file from S3: bucket=%s key=%s", self.bucket_name, s3_key)

        session = self._get_session()
        try:
            async with session.client("s3") as s3_client:
                response = await s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
                file_content = await response["Body"].read()
                logger.debug("File downloaded successfully: key=%s size=%d", s3_key, len(file_content))
                return file_content
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchKey":
                logger.warning("File not found in S3: key=%s", s3_key)
                raise FileNotFoundError(f"File not found in S3: {s3_key}") from exc
            logger.exception("Failed to download file from S3: key=%s error=%s", s3_key, str(exc))
            raise Exception(f"Failed to download file from S3: {str(exc)}") from exc
        except Exception as exc:
            logger.exception("Unexpected error downloading file from S3: key=%s", s3_key)
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

        logger.debug("Deleting file from S3: bucket=%s key=%s", self.bucket_name, s3_key)

        session = self._get_session()
        try:
            async with session.client("s3") as s3_client:
                await s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
                logger.debug("File deleted successfully: key=%s", s3_key)
                return True
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchKey":
                logger.warning("File not found in S3 (already deleted?): key=%s", s3_key)
                return False
            logger.exception("Failed to delete file from S3: key=%s error=%s", s3_key, str(exc))
            raise Exception(f"Failed to delete file from S3: {str(exc)}") from exc
        except Exception as exc:
            logger.exception("Unexpected error deleting file from S3: key=%s", s3_key)
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
        logger.debug(
            "Generating presigned URL: bucket=%s key=%s expiration=%d",
            self.bucket_name,
            s3_key,
            expiration,
        )

        session = self._get_session()
        try:
            async with session.client("s3") as s3_client:
                url = await s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.bucket_name, "Key": s3_key},
                    ExpiresIn=expiration,
                )
                logger.debug("Presigned URL generated: key=%s", s3_key)
                return url
        except ClientError as exc:
            logger.exception("Failed to generate presigned URL: key=%s error=%s", s3_key, str(exc))
            raise Exception(f"Failed to generate presigned URL: {str(exc)}") from exc
        except Exception as exc:
            logger.exception("Unexpected error generating presigned URL: key=%s", s3_key)
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

