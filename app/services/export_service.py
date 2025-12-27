"""Service layer for managing contact export jobs."""

import csv
import io
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Sequence

import aiofiles
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.connectra_client import ConnectraClient
from app.core.config import get_settings
from app.models.exports import ExportStatus, ExportType, UserExport
from app.schemas.filters import ExportFilterParams
from app.services.s3_service import S3Service
from app.services.vql_transformer import VQLTransformer
from app.utils.batch_lookup import batch_fetch_company_metadata_by_uuids
from app.utils.logger import get_logger, log_error
from app.utils.signed_url import generate_signed_url

settings = get_settings()
logger = get_logger(__name__)


class ExportService:
    """Encapsulate export job orchestration."""

    def __init__(
        self,
        s3_service: Optional[S3Service] = None,
    ) -> None:
        """Initialize the export service."""
        self.s3_service = s3_service or S3Service()

    async def create_export(
        self,
        session: AsyncSession,
        user_id: str,
        export_type: ExportType,
        contact_uuids: Optional[list[str]] = None,
        company_uuids: Optional[list[str]] = None,
        linkedin_urls: Optional[list[str]] = None,
    ) -> UserExport:
        """Create a new export record in the database."""
        if export_type == ExportType.contacts:
            export = UserExport(
                user_id=user_id,
                export_type=export_type,
                contact_uuids=contact_uuids or [],
                contact_count=len(contact_uuids) if contact_uuids else 0,
                linkedin_urls=linkedin_urls,
                status=ExportStatus.pending,
            )
        elif export_type == ExportType.companies:
            export = UserExport(
                user_id=user_id,
                export_type=export_type,
                company_uuids=company_uuids or [],
                company_count=len(company_uuids) if company_uuids else 0,
                linkedin_urls=linkedin_urls,
                status=ExportStatus.pending,
            )
        else:  # emails
            export = UserExport(
                user_id=user_id,
                export_type=export_type,
                contact_uuids=[],
                company_uuids=[],
                status=ExportStatus.pending,
            )
        
        # Set expiration to 24 hours from creation
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        export.expires_at = expires_at
        
        session.add(export)
        await session.flush()
        await session.refresh(export)
        await session.commit()
        
        logger.info(
            "Export record created",
            extra={
                "context": {
                    "export_id": export.export_id,
                    "user_id": user_id,
                    "export_type": export_type,
                    "contact_count": len(contact_uuids) if contact_uuids else 0,
                    "company_count": len(company_uuids) if company_uuids else 0,
                },
                "user_id": user_id,
            }
        )
        
        return export

    async def generate_csv(
        self,
        session: AsyncSession,
        export_id: str,
        contact_uuids: list[str],
    ) -> str:
        """
        Fetch contacts with all relations and generate CSV file.
        
        Returns:
            S3 key or local file path to the generated CSV file
        """
        start_time = time.time()
        logger.info(
            "Starting CSV generation for contacts",
            extra={
                "context": {
                    "export_id": export_id,
                    "contact_count": len(contact_uuids),
                }
            }
        )
        
        # Use streaming CSV generation for large exports
        # Create temporary file for streaming write
        exports_dir = Path(settings.UPLOAD_DIR) / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        temp_file_path = exports_dir / f"{export_id}_temp.csv"
        
        # Define CSV fieldnames (all fields from contact, company, and metadata)
        fieldnames = [
            # Contact fields
            "contact_uuid",
            "contact_first_name",
            "contact_last_name",
            "contact_company_id",
            "contact_email",
            "contact_title",
            "contact_departments",
            "contact_mobile_phone",
            "contact_email_status",
            "contact_text_search",
            "contact_seniority",
            "contact_created_at",
            "contact_updated_at",
            # Contact Metadata fields
            "contact_metadata_linkedin_url",
            "contact_metadata_facebook_url",
            "contact_metadata_twitter_url",
            "contact_metadata_website",
            "contact_metadata_work_direct_phone",
            "contact_metadata_home_phone",
            "contact_metadata_city",
            "contact_metadata_state",
            "contact_metadata_country",
            "contact_metadata_other_phone",
            "contact_metadata_stage",
            # Company fields
            "company_uuid",
            "company_name",
            "company_employees_count",
            "company_industries",
            "company_keywords",
            "company_address",
            "company_annual_revenue",
            "company_total_funding",
            "company_technologies",
            "company_text_search",
            "company_created_at",
            "company_updated_at",
            # Company Metadata fields
            "company_metadata_linkedin_url",
            "company_metadata_facebook_url",
            "company_metadata_twitter_url",
            "company_metadata_website",
            "company_metadata_company_name_for_emails",
            "company_metadata_phone_number",
            "company_metadata_latest_funding",
            "company_metadata_latest_funding_amount",
            "company_metadata_last_raised_at",
            "company_metadata_city",
            "company_metadata_state",
            "company_metadata_country",
        ]
        
        # Stream CSV generation to file
        row_count = 0
        async with aiofiles.open(temp_file_path, "w", encoding="utf-8", newline="") as async_file:
            # Write header
            header_line = ",".join(fieldnames) + "\n"
            await async_file.write(header_line)
            
            # Process contacts in batches for better performance
            batch_size = 100
            
            # Use Connectra for exports
            try:
                async with ConnectraClient() as client:
                    transformer = VQLTransformer()
                    # Fetch all contacts via Connectra in batches
                    all_contact_data = await client.batch_search_by_uuids(
                        contact_uuids, entity_type="contact", batch_size=batch_size
                    )
                    
                    # Transform VQL responses to ContactListItem
                    contacts_list = transformer.transform_contact_response({"data": all_contact_data})
                    
                    # Create a mapping for quick lookup
                    contacts_map = {c.uuid: c for c in contacts_list}
                    
                    # Process contacts from Connectra response
                    for contact_uuid in contact_uuids:
                        contact_item = contacts_map.get(contact_uuid)
                        if not contact_item:
                            continue
                        
                        # Convert ContactListItem to CSV row format
                        # Helper functions for formatting
                        def format_array(value):
                            if value is None:
                                return ""
                            if isinstance(value, str):
                                # Already comma-separated string
                                return value
                            if isinstance(value, list):
                                return ",".join(str(v) for v in value if v)
                            return str(value) if value else ""
                        
                        def format_datetime(value):
                            if value is None:
                                return ""
                            if isinstance(value, datetime):
                                return value.isoformat()
                            return str(value) if value else ""
                        
                        def get_value(value, default=""):
                            if value is None:
                                return default
                            if value == "_":  # Default placeholder
                                return ""
                            return str(value)
                        
                        # Extract company data from contact_item
                        company_data = contact_item.model_dump() if hasattr(contact_item, 'model_dump') else {}
                        
                        row = {
                            # Contact fields
                            "contact_uuid": get_value(contact_item.uuid),
                            "contact_first_name": get_value(contact_item.first_name),
                            "contact_last_name": get_value(contact_item.last_name),
                            "contact_company_id": get_value(company_data.get("company_id")),
                            "contact_email": get_value(contact_item.email),
                            "contact_title": get_value(contact_item.title),
                            "contact_departments": format_array(contact_item.departments),
                            "contact_mobile_phone": get_value(contact_item.mobile_phone),
                            "contact_email_status": get_value(contact_item.email_status),
                            "contact_text_search": "",
                            "contact_seniority": get_value(contact_item.seniority),
                            "contact_created_at": format_datetime(contact_item.created_at if hasattr(contact_item, 'created_at') else None),
                            "contact_updated_at": format_datetime(contact_item.updated_at if hasattr(contact_item, 'updated_at') else None),
                            # Contact Metadata fields (from contact_item)
                            "contact_metadata_linkedin_url": get_value(contact_item.person_linkedin_url),
                            "contact_metadata_facebook_url": get_value(company_data.get("facebook_url")),
                            "contact_metadata_twitter_url": get_value(company_data.get("twitter_url")),
                            "contact_metadata_website": get_value(contact_item.website),
                            "contact_metadata_work_direct_phone": get_value(contact_item.work_direct_phone if hasattr(contact_item, 'work_direct_phone') else None),
                            "contact_metadata_home_phone": get_value(contact_item.home_phone if hasattr(contact_item, 'home_phone') else None),
                            "contact_metadata_city": get_value(contact_item.city),
                            "contact_metadata_state": get_value(contact_item.state),
                            "contact_metadata_country": get_value(contact_item.country),
                            "contact_metadata_other_phone": get_value(contact_item.other_phone if hasattr(contact_item, 'other_phone') else None),
                            "contact_metadata_stage": get_value(contact_item.stage if hasattr(contact_item, 'stage') else None),
                            # Company fields (from contact_item)
                            "company_uuid": "",
                            "company_name": get_value(contact_item.company),
                            "company_employees_count": get_value(contact_item.employees),
                            "company_industries": format_array(contact_item.industry),
                            "company_keywords": format_array(contact_item.keywords),
                            "company_address": get_value(contact_item.company_address),
                            "company_annual_revenue": get_value(contact_item.annual_revenue),
                            "company_total_funding": get_value(contact_item.total_funding),
                            "company_technologies": format_array(contact_item.technologies),
                            "company_text_search": "",
                            "company_created_at": "",
                            "company_updated_at": "",
                            # Company Metadata fields
                            "company_metadata_linkedin_url": get_value(contact_item.company_linkedin_url),
                            "company_metadata_facebook_url": get_value(company_data.get("facebook_url")),
                            "company_metadata_twitter_url": get_value(company_data.get("twitter_url")),
                            "company_metadata_website": get_value(contact_item.website),
                            "company_metadata_company_name_for_emails": get_value(contact_item.company_name_for_emails if hasattr(contact_item, 'company_name_for_emails') else None),
                            "company_metadata_phone_number": get_value(contact_item.corporate_phone if hasattr(contact_item, 'corporate_phone') else None),
                            "company_metadata_latest_funding": get_value(contact_item.latest_funding),
                            "company_metadata_latest_funding_amount": get_value(contact_item.latest_funding_amount),
                            "company_metadata_last_raised_at": get_value(contact_item.last_raised_at),
                            "company_metadata_city": get_value(contact_item.company_city),
                            "company_metadata_state": get_value(contact_item.company_state),
                            "company_metadata_country": get_value(contact_item.company_country),
                        }
                        
                        # Write row as CSV line
                        row_values = [str(row.get(field, "")) for field in fieldnames]
                        # Escape CSV values
                        escaped_values = []
                        for value in row_values:
                            if "," in value or '"' in value or "\n" in value:
                                escaped_values.append('"' + value.replace('"', '""') + '"')
                            else:
                                escaped_values.append(value)
                        csv_line = ",".join(escaped_values) + "\n"
                        await async_file.write(csv_line)
                        row_count += 1
            except Exception as exc:
                duration = (time.time() - start_time) * 1000
                log_error(
                    "Connectra export failed",
                    exc,
                    "app.services.export_service",
                    context={
                        "export_id": export_id,
                        "contact_count": len(contact_uuids),
                        "rows_processed": row_count,
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Export service temporarily unavailable"
                ) from exc
        
        # Upload to S3 if configured, otherwise keep local
        if settings.S3_BUCKET_NAME:
            try:
                s3_key = f"{self.s3_service.exports_prefix}{export_id}.csv"
                
                # Stream file to S3 in chunks
                chunk_size = settings.MAX_UPLOAD_CHUNK_SIZE
                async with aiofiles.open(temp_file_path, "rb") as async_file:
                    file_chunks = []
                    while chunk := await async_file.read(chunk_size):
                        file_chunks.append(chunk)
                    csv_content = b"".join(file_chunks)
                
                await self.s3_service.upload_file(
                    file_content=csv_content,
                    s3_key=s3_key,
                    content_type="text/csv",
                )
                
                # Clean up temp file
                temp_file_path.unlink(missing_ok=True)
                duration = (time.time() - start_time) * 1000
                logger.info(
                    "CSV generation completed - uploaded to S3",
                    extra={
                        "context": {
                            "export_id": export_id,
                            "row_count": row_count,
                            "s3_key": s3_key,
                        },
                        "performance": {"duration_ms": duration}
                    }
                )
                return s3_key
            except Exception as s3_exc:
                log_error(
                    "Failed to upload CSV to S3, falling back to local storage",
                    s3_exc,
                    "app.services.export_service",
                    context={"export_id": export_id, "s3_key": s3_key},
                )
                # Fallback to local storage - rename temp file
                file_path = exports_dir / f"{export_id}.csv"
                temp_file_path.rename(file_path)
                duration = (time.time() - start_time) * 1000
                logger.info(
                    "CSV generation completed - saved locally",
                    extra={
                        "context": {
                            "export_id": export_id,
                            "row_count": row_count,
                            "file_path": str(file_path),
                        },
                        "performance": {"duration_ms": duration}
                    }
                )
                return str(file_path)
        else:
            # Save locally - rename temp file to final location
            file_path = exports_dir / f"{export_id}.csv"
            temp_file_path.rename(file_path)
            duration = (time.time() - start_time) * 1000
            logger.info(
                "CSV generation completed - saved locally",
                extra={
                    "context": {
                        "export_id": export_id,
                        "row_count": row_count,
                        "file_path": str(file_path),
                    },
                    "performance": {"duration_ms": duration}
                }
            )
            return str(file_path)

    async def update_export_status(
        self,
        session: AsyncSession,
        export_id: str,
        status: ExportStatus,
        file_path: str,
        contact_count: Optional[int] = None,
        company_count: Optional[int] = None,
    ) -> UserExport:
        """Update export record with file path, status, and generate signed URL."""
        
        # Get export record
        stmt = select(UserExport).where(UserExport.export_id == export_id)
        result = await session.execute(stmt)
        export = result.scalar_one_or_none()
        
        if not export:
            raise ValueError(f"Export not found: {export_id}")
        
        # Update fields
        export.file_path = file_path
        # Extract filename from path (could be S3 key or local path)
        if self.s3_service.is_s3_key(file_path):
            export.file_name = Path(file_path).name
        else:
            export.file_name = Path(file_path).name
        export.status = status
        if contact_count is not None:
            export.contact_count = contact_count
        if company_count is not None:
            export.company_count = company_count
        
        logger.info(
            "Export status updated",
            extra={
                "context": {
                    "export_id": export_id,
                    "status": status,
                    "file_path": file_path,
                    "contact_count": contact_count,
                    "company_count": company_count,
                }
            }
        )
        
        # Set expiration (24 hours from now)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        export.expires_at = expires_at
        
        # Generate signed URL token
        download_token = generate_signed_url(export.export_id, export.user_id, expires_at)
        export.download_token = download_token
        
        # Generate full download URL
        base_url = settings.BASE_URL.rstrip("/")
        export.download_url = f"{base_url}/api/v2/exports/{export_id}/download?token={download_token}"
        
        await session.commit()
        await session.refresh(export)
        return export

    async def get_export(
        self,
        session: AsyncSession,
        export_id: str,
        user_id: str,
    ) -> Optional[UserExport]:
        """Retrieve export record with user validation."""
        
        stmt = select(UserExport).where(
            UserExport.export_id == export_id,
            UserExport.user_id == user_id,
        )
        result = await session.execute(stmt)
        export = result.scalar_one_or_none()
        
        return export

    async def generate_company_csv(
        self,
        session: AsyncSession,
        export_id: str,
        company_uuids: list[str],
    ) -> str:
        """
        Fetch companies with metadata and generate CSV file.
        
        Returns:
            S3 key or local file path to the generated CSV file
        """
        start_time = time.time()
        logger.info(
            "Starting CSV generation for companies",
            extra={
                "context": {
                    "export_id": export_id,
                    "company_count": len(company_uuids),
                }
            }
        )
        
        # Generate CSV in memory
        csv_buffer = io.StringIO()
        
        # Define CSV fieldnames (all fields from company and company metadata)
        fieldnames = [
            # Company fields
            "company_uuid",
            "company_name",
            "company_employees_count",
            "company_industries",
            "company_keywords",
            "company_address",
            "company_annual_revenue",
            "company_total_funding",
            "company_technologies",
            "company_text_search",
            "company_created_at",
            "company_updated_at",
            # Company Metadata fields
            "company_metadata_linkedin_url",
            "company_metadata_facebook_url",
            "company_metadata_twitter_url",
            "company_metadata_website",
            "company_metadata_company_name_for_emails",
            "company_metadata_phone_number",
            "company_metadata_latest_funding",
            "company_metadata_latest_funding_amount",
            "company_metadata_last_raised_at",
            "company_metadata_city",
            "company_metadata_state",
            "company_metadata_country",
        ]
        
        # Use Connectra for company exports
        try:
            async with ConnectraClient() as client:
                transformer = VQLTransformer()
                # Fetch all companies via Connectra in batches
                batch_size = 100
                all_company_data = await client.batch_search_by_uuids(
                    company_uuids, entity_type="company", batch_size=batch_size
                )
                
                # Transform VQL responses to CompanyListItem
                companies_list = transformer.transform_company_response({"data": all_company_data})
                
                # Create a mapping for quick lookup
                companies_map = {c.uuid: c for c in companies_list}
        except Exception as e:
            # If Connectra fails, create empty map (will skip all companies)
            logger.error(f"Failed to fetch companies from Connectra: {e}")
            companies_map = {}
        
        # Helper functions (moved outside loop for reuse)
        def format_array(value):
            if value is None:
                return ""
            if isinstance(value, list):
                return ",".join(str(v) for v in value if v)
            return str(value) if value else ""
        
        def format_datetime(value):
            if value is None:
                return ""
            if isinstance(value, datetime):
                return value.isoformat()
            return str(value) if value else ""
        
        def get_value(value, default=""):
            if value is None:
                return default
            if value == "_":  # Default placeholder in metadata
                return ""
            return str(value)
        
        # Write companies to CSV
        writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
        writer.writeheader()
        
        for company_uuid in company_uuids:
            try:
                company_item = companies_map.get(company_uuid)
                if not company_item:
                    continue
                
                # Extract metadata from company_item
                company_meta = None
                if hasattr(company_item, 'metadata') and company_item.metadata:
                    company_meta = company_item.metadata
                
                industries_list = None
                if company_item.industry:
                    industries_list = [company_item.industry]
                elif hasattr(company_item, 'industries') and company_item.industries:
                    industries_list = company_item.industries
                
                row_data = {
                    # Company fields
                    "company_uuid": get_value(company_item.uuid),
                    "company_name": get_value(company_item.name),
                    "company_employees_count": str(company_item.employees_count) if company_item.employees_count else "",
                    "company_industries": format_array(industries_list),
                    "company_keywords": format_array(company_item.keywords),
                    "company_address": "",
                    "company_annual_revenue": str(company_item.annual_revenue) if company_item.annual_revenue else "",
                    "company_total_funding": str(company_item.total_funding) if company_item.total_funding else "",
                    "company_technologies": format_array(company_item.technologies),
                    "company_text_search": "",
                    "company_created_at": "",
                    "company_updated_at": "",
                    # Company Metadata fields
                    "company_metadata_linkedin_url": get_value(company_item.linkedin_url),
                    "company_metadata_facebook_url": get_value(company_meta.facebook_url if company_meta else None),
                    "company_metadata_twitter_url": get_value(company_meta.twitter_url if company_meta else None),
                    "company_metadata_website": get_value(company_item.website),
                    "company_metadata_company_name_for_emails": get_value(company_meta.company_name_for_emails if company_meta else None),
                    "company_metadata_phone_number": get_value(getattr(company_item, 'phone_number', None) or (company_meta.phone_number if company_meta else None)),
                    "company_metadata_latest_funding": get_value(company_meta.latest_funding if company_meta else None),
                    "company_metadata_latest_funding_amount": str(company_meta.latest_funding_amount) if company_meta and company_meta.latest_funding_amount else "",
                    "company_metadata_last_raised_at": get_value(company_meta.last_raised_at if company_meta else None),
                    "company_metadata_city": get_value(company_item.city),
                    "company_metadata_state": get_value(company_item.state),
                    "company_metadata_country": get_value(company_item.country),
                }
                
                writer.writerow(row_data)
                
            except Exception:
                # Continue with next company even if one fails
                continue
        
        # Get CSV content as bytes
        csv_content = csv_buffer.getvalue().encode("utf-8")
        csv_buffer.close()
        
        # Upload to S3 if configured, otherwise save locally
        row_count = len(company_uuids)
        if settings.S3_BUCKET_NAME:
            try:
                s3_key = f"{self.s3_service.exports_prefix}{export_id}.csv"
                await self.s3_service.upload_file(
                    file_content=csv_content,
                    s3_key=s3_key,
                    content_type="text/csv",
                )
                duration = (time.time() - start_time) * 1000
                logger.info(
                    "Company CSV generation completed - uploaded to S3",
                    extra={
                        "context": {
                            "export_id": export_id,
                            "row_count": row_count,
                            "s3_key": s3_key,
                        },
                        "performance": {"duration_ms": duration}
                    }
                )
                return s3_key
            except Exception as s3_exc:
                log_error(
                    "Failed to upload company CSV to S3, falling back to local storage",
                    s3_exc,
                    "app.services.export_service",
                    context={"export_id": export_id},
                )
                # Fallback to local storage
                exports_dir = Path(settings.UPLOAD_DIR) / "exports"
                exports_dir.mkdir(parents=True, exist_ok=True)
                file_path = exports_dir / f"{export_id}.csv"
                with file_path.open("wb") as f:
                    f.write(csv_content)
                duration = (time.time() - start_time) * 1000
                logger.info(
                    "Company CSV generation completed - saved locally",
                    extra={
                        "context": {
                            "export_id": export_id,
                            "row_count": row_count,
                            "file_path": str(file_path),
                        },
                        "performance": {"duration_ms": duration}
                    }
                )
                return str(file_path)
        else:
            # Save locally
            exports_dir = Path(settings.UPLOAD_DIR) / "exports"
            exports_dir.mkdir(parents=True, exist_ok=True)
            file_path = exports_dir / f"{export_id}.csv"
            with file_path.open("wb") as f:
                f.write(csv_content)
            duration = (time.time() - start_time) * 1000
            logger.info(
                "Company CSV generation completed - saved locally",
                extra={
                    "context": {
                        "export_id": export_id,
                        "row_count": row_count,
                        "file_path": str(file_path),
                    },
                    "performance": {"duration_ms": duration}
                }
            )
            return str(file_path)

    async def generate_email_export_csv(
        self,
        session: AsyncSession,
        export_id: str,
        contacts_data: list[dict],
        fieldnames: list[str] | None = None,
    ) -> str:
        """
        Generate CSV file for email export from processed contact data.
        
        Args:
            session: Database session
            export_id: Export ID
            contacts_data: List of dictionaries with keys: first_name, last_name, domain, email
            
        Returns:
            S3 key or local file path to the generated CSV file
        """
        # Generate CSV in memory
        csv_buffer = io.StringIO()
        
        # Define CSV fieldnames
        # If a specific header order was provided (e.g. original CSV headers),
        # use it. Otherwise, fall back to the minimal legacy header set.
        if fieldnames is None:
            fieldnames = ["first_name", "last_name", "domain", "email"]
        
        # Write CSV
        writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
        writer.writeheader()
        
        rows_written = 0
        rows_failed = 0
        for contact in contacts_data:
            try:
                # contacts_data is expected to already use the final CSV schema:
                # it should contain at least all keys in fieldnames. Missing keys
                # will be written as empty strings.
                row_data = {name: contact.get(name, "") for name in fieldnames}
                writer.writerow(row_data)
                rows_written += 1
            except Exception:
                rows_failed += 1
                # Continue with next contact even if one fails
                continue
        
        # Get CSV content as bytes
        csv_content = csv_buffer.getvalue().encode("utf-8")
        csv_buffer.close()
        
        # Upload to S3 if configured, otherwise save locally
        if settings.S3_BUCKET_NAME:
            try:
                s3_key = f"{self.s3_service.exports_prefix}{export_id}.csv"
                await self.s3_service.upload_file(
                    file_content=csv_content,
                    s3_key=s3_key,
                    content_type="text/csv",
                )
                return s3_key
            except Exception:
                # Fallback to local storage
                exports_dir = Path(settings.UPLOAD_DIR) / "exports"
                exports_dir.mkdir(parents=True, exist_ok=True)
                file_path = exports_dir / f"{export_id}.csv"
                async with aiofiles.open(file_path, "wb") as async_file:
                    await async_file.write(csv_content)
                return str(file_path)
        else:
            # Save locally
            exports_dir = Path(settings.UPLOAD_DIR) / "exports"
            exports_dir.mkdir(parents=True, exist_ok=True)
            file_path = exports_dir / f"{export_id}.csv"
            async with aiofiles.open(file_path, "wb") as async_file:
                await async_file.write(csv_content)
            return str(file_path)

    async def list_user_exports(
        self,
        session: AsyncSession,
        user_id: str,
        filters: Optional[ExportFilterParams] = None,
    ) -> Sequence[UserExport]:
        """List all exports for a user, ordered by created_at descending, with optional filters."""
        
        # Optimized query: Use composite index (user_id, status, created_at DESC)
        # This query pattern matches idx_user_exports_user_status_created index
        stmt = (
            select(UserExport)
            .where(UserExport.user_id == user_id)
        )
        
        # Apply filters if provided
        if filters:
            stmt = self._apply_filters(stmt, filters)
        
        # Order by created_at DESC to match index order
        # The composite index idx_user_exports_user_status_created includes created_at DESC
        stmt = stmt.order_by(UserExport.created_at.desc())
        
        # Add reasonable limit to prevent loading too many records
        # Most users won't need more than 100 recent exports
        if not filters or not hasattr(filters, 'page_size') or filters.page_size is None:
            stmt = stmt.limit(100)
        elif hasattr(filters, 'page_size') and filters.page_size:
            stmt = stmt.limit(min(filters.page_size, 1000))  # Cap at 1000
        
        result = await session.execute(stmt)
        exports = result.scalars().all()
        return exports
    
    def _apply_filters(
        self,
        stmt,
        filters: ExportFilterParams,
    ):
        """Apply filter parameters to the given SQLAlchemy statement."""
        # Status filter
        if filters.status:
            try:
                status_enum = ExportStatus(filters.status.lower())
                stmt = stmt.where(UserExport.status == status_enum)
            except ValueError:
                # Invalid status, ignore filter
                pass
        
        # Export type filter
        if filters.export_type:
            try:
                export_type_enum = ExportType(filters.export_type.lower())
                stmt = stmt.where(UserExport.export_type == export_type_enum)
            except ValueError:
                # Invalid type, ignore filter
                pass
        
        # User ID filter (usually not needed since we filter by user_id in the query)
        if filters.user_id:
            stmt = stmt.where(UserExport.user_id == filters.user_id)
        
        # Date range filters
        if filters.created_at_after:
            stmt = stmt.where(UserExport.created_at >= filters.created_at_after)
        if filters.created_at_before:
            stmt = stmt.where(UserExport.created_at <= filters.created_at_before)
        
        return stmt

    async def delete_all_csv_files(
        self,
        session: AsyncSession,
    ) -> int:
        """
        Delete all CSV files from the exports directory.
        
        Returns:
            Number of files deleted
        """
        exports_dir = Path(settings.UPLOAD_DIR) / "exports"
        
        if not exports_dir.exists():
            return 0
        
        deleted_count = 0
        try:
            # Find all CSV files in exports directory
            csv_files = list(exports_dir.glob("*.csv"))
            
            for csv_file in csv_files:
                try:
                    csv_file.unlink()
                    deleted_count += 1
                except Exception:
                    # Continue with other files
                    pass
            
            # Optionally clean up expired export records
            stmt = select(UserExport).where(
                UserExport.expires_at < datetime.now(timezone.utc)
            )
            result = await session.execute(stmt)
            expired_exports = result.scalars().all()
            
            if expired_exports:
                for export in expired_exports:
                    session.delete(export)
                await session.commit()
            
        except Exception:
            raise
        
        return deleted_count

    async def merge_csv_files(
        self,
        session: AsyncSession,
        main_export_id: str,
        chunk_export_ids: list[str],
    ) -> str:
        """
        Merge multiple CSV files from chunk exports into a single CSV file.
        
        Args:
            session: Database session
            main_export_id: Main export ID to update with merged file
            chunk_export_ids: List of chunk export IDs to merge
            
        Returns:
            S3 key or local file path to the merged CSV file
        """
        # Get all chunk exports
        stmt = select(UserExport).where(UserExport.export_id.in_(chunk_export_ids))
        result = await session.execute(stmt)
        chunk_exports = result.scalars().all()
        
        if not chunk_exports:
            raise ValueError(f"No chunk exports found for IDs: {chunk_export_ids}")
        
        # Verify all chunks are completed
        incomplete_chunks = [
            exp.export_id for exp in chunk_exports
            if exp.status != ExportStatus.completed or not exp.file_path
        ]
        if incomplete_chunks:
            raise ValueError(
                f"Cannot merge: {len(incomplete_chunks)} chunk(s) not completed: {incomplete_chunks}"
            )
        
        # Read all CSV files and merge them
        all_rows = []
        headers = None
        row_count = 0
        
        for chunk_export in chunk_exports:
            file_path = chunk_export.file_path
            if not file_path:
                continue
            
            # Read CSV file (from S3 or local)
            csv_content = None
            if self.s3_service.is_s3_key(file_path):
                # Download from S3
                s3_key = file_path
                if s3_key.startswith("https://"):
                    parts = s3_key.split(".s3.")
                    if len(parts) > 1 and "/" in parts[1]:
                        s3_key = parts[1].split("/", 1)[1]
                csv_content = await self.s3_service.download_file(s3_key)
            else:
                # Read from local file
                local_path = Path(file_path)
                if not local_path.exists():
                    continue
                async with aiofiles.open(local_path, "rb") as f:
                    csv_content = await f.read()
            
            if not csv_content:
                continue
            
            # Parse CSV content
            csv_text = csv_content.decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(csv_text))
            
            # Store headers from first chunk
            if headers is None:
                headers = csv_reader.fieldnames
                if headers:
                    all_rows.append(headers)  # Add header row
            
            # Add data rows
            for row in csv_reader:
                # Ensure row has all headers (fill missing with empty string)
                complete_row = [row.get(header, '') for header in headers] if headers else list(row.values())
                all_rows.append(complete_row)
                row_count += 1
        
        if not all_rows:
            raise ValueError("No data rows found in chunk exports to merge")
        
        # Create merged CSV file
        exports_dir = Path(settings.UPLOAD_DIR) / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        temp_file_path = exports_dir / f"{main_export_id}_merged_temp.csv"
        
        # Write merged CSV
        async with aiofiles.open(temp_file_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            for row in all_rows:
                writer.writerow(row)
        
        # Upload to S3 if configured, otherwise save locally
        if settings.S3_BUCKET_NAME:
            try:
                s3_key = f"{self.s3_service.exports_prefix}{main_export_id}.csv"
                
                # Read merged file and upload
                async with aiofiles.open(temp_file_path, "rb") as async_file:
                    csv_content = await async_file.read()
                
                await self.s3_service.upload_file(
                    file_content=csv_content,
                    s3_key=s3_key,
                    content_type="text/csv",
                )
                
                # Clean up temp file
                temp_file_path.unlink(missing_ok=True)
                return s3_key
            except Exception:
                # Fallback to local storage
                file_path = exports_dir / f"{main_export_id}.csv"
                temp_file_path.rename(file_path)
                return str(file_path)
        else:
            # Save locally - rename temp file to final location
            file_path = exports_dir / f"{main_export_id}.csv"
            temp_file_path.rename(file_path)
            return str(file_path)

    async def generate_bulk_verifier_csv(
        self,
        session: AsyncSession,
        export_id: str,
        csv_rows: list[dict],
        csv_headers: list[str],
    ) -> str:
        """
        Generate CSV file for bulk email verifier with original columns + verification status.
        
        Args:
            session: Database session
            export_id: Export ID
            csv_rows: List of dictionaries with CSV row data including verification_status
            csv_headers: Original CSV headers with verification_status added
            
        Returns:
            S3 key or local file path to the generated CSV file
        """
        # Generate CSV in memory
        csv_buffer = io.StringIO()
        
        # Use provided CSV headers as fieldnames
        fieldnames = csv_headers
        
        # Write CSV
        writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
        writer.writeheader()
        
        rows_written = 0
        rows_failed = 0
        for row in csv_rows:
            try:
                # Ensure all fieldnames are present in row
                row_data = {name: row.get(name, "") for name in fieldnames}
                writer.writerow(row_data)
                rows_written += 1
            except Exception:
                rows_failed += 1
                # Continue with next row even if one fails
                continue
        
        # Get CSV content as bytes
        csv_content = csv_buffer.getvalue().encode("utf-8")
        csv_buffer.close()
        
        # Upload to S3 if configured, otherwise save locally
        if settings.S3_BUCKET_NAME:
            try:
                s3_key = f"{self.s3_service.exports_prefix}{export_id}.csv"
                await self.s3_service.upload_file(
                    file_content=csv_content,
                    s3_key=s3_key,
                    content_type="text/csv",
                )
                return s3_key
            except Exception:
                # Fallback to local storage
                exports_dir = Path(settings.UPLOAD_DIR) / "exports"
                exports_dir.mkdir(parents=True, exist_ok=True)
                file_path = exports_dir / f"{export_id}.csv"
                with file_path.open("wb") as f:
                    f.write(csv_content)
                return str(file_path)
        else:
            # Save locally
            exports_dir = Path(settings.UPLOAD_DIR) / "exports"
            exports_dir.mkdir(parents=True, exist_ok=True)
            file_path = exports_dir / f"{export_id}.csv"
            with file_path.open("wb") as f:
                f.write(csv_content)
            return str(file_path)

    async def generate_linkedin_export_csv(
        self,
        session: AsyncSession,
        export_id: str,
        contact_uuids: list[str],
        company_uuids: list[str],
        unmatched_urls: list[str],
        csv_rows: Optional[list[dict]] = None,
        csv_headers: Optional[list[str]] = None,
    ) -> str:
        """
        Generate combined CSV with contacts, companies, and unmatched URLs.
        
        Creates a CSV file with a record_type column to distinguish between
        contacts, companies, and not_found entries. Includes all contact and
        company fields, with empty values for fields that don't apply.
        
        If csv_rows and csv_headers are provided, preserves original CSV structure
        while enriching with LinkedIn data.
        
        Args:
            session: Database session
            export_id: Export record ID
            contact_uuids: List of contact UUIDs to export
            company_uuids: List of company UUIDs to export
            unmatched_urls: List of LinkedIn URLs that didn't match anything
            csv_rows: Optional pre-processed CSV rows with LinkedIn data (preserves original columns)
            csv_headers: Optional original CSV headers (preserves column order)
            
        Returns:
            S3 key or local file path to the generated CSV file
        """
        # Generate CSV in memory
        csv_buffer = io.StringIO()
        
        # If CSV context is provided, use it; otherwise use standard fieldnames
        if csv_rows is not None and csv_headers is not None:
            # Use original CSV headers as primary fieldnames
            fieldnames = list(csv_headers)
            # Ensure required fields are present
            if "record_type" not in fieldnames:
                fieldnames.insert(0, "record_type")
            if "linkedin_url" not in fieldnames:
                # Insert linkedin_url after record_type or at the beginning
                if "record_type" in fieldnames:
                    idx = fieldnames.index("record_type") + 1
                    fieldnames.insert(idx, "linkedin_url")
                else:
                    fieldnames.insert(0, "linkedin_url")
        else:
            # Define CSV fieldnames - combined structure with record_type and linkedin_url
            fieldnames = [
            "record_type",  # "contact", "company", or "not_found"
            "linkedin_url",  # LinkedIn URL (for not_found rows and reference)
            # Contact fields
            "contact_uuid",
            "contact_first_name",
            "contact_last_name",
            "contact_company_id",
            "contact_email",
            "contact_title",
            "contact_departments",
            "contact_mobile_phone",
            "contact_email_status",
            "contact_text_search",
            "contact_seniority",
            "contact_created_at",
            "contact_updated_at",
            # Contact Metadata fields
            "contact_metadata_linkedin_url",
            "contact_metadata_facebook_url",
            "contact_metadata_twitter_url",
            "contact_metadata_website",
            "contact_metadata_work_direct_phone",
            "contact_metadata_home_phone",
            "contact_metadata_city",
            "contact_metadata_state",
            "contact_metadata_country",
            "contact_metadata_other_phone",
            "contact_metadata_stage",
            # Company fields
            "company_uuid",
            "company_name",
            "company_employees_count",
            "company_industries",
            "company_keywords",
            "company_address",
            "company_annual_revenue",
            "company_total_funding",
            "company_technologies",
            "company_text_search",
            "company_created_at",
            "company_updated_at",
            # Company Metadata fields
            "company_metadata_linkedin_url",
            "company_metadata_facebook_url",
            "company_metadata_twitter_url",
            "company_metadata_website",
            "company_metadata_company_name_for_emails",
            "company_metadata_phone_number",
            "company_metadata_latest_funding",
            "company_metadata_latest_funding_amount",
            "company_metadata_last_raised_at",
            "company_metadata_city",
            "company_metadata_state",
            "company_metadata_country",
        ]
        
        # Helper functions (same as in generate_csv)
        def format_array(value):
            if value is None:
                return ""
            if isinstance(value, list):
                return ",".join(str(v) for v in value if v)
            return str(value) if value else ""
        
        def format_datetime(value):
            if value is None:
                return ""
            if isinstance(value, datetime):
                return value.isoformat()
            return str(value) if value else ""
        
        def get_value(value, default=""):
            if value is None:
                return default
            if value == "_":  # Default placeholder in metadata
                return ""
            return str(value)
        
        # Write CSV
        writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
        writer.writeheader()
        
        # If CSV context is provided, write pre-processed rows
        if csv_rows is not None:
            for row in csv_rows:
                try:
                    # Ensure all fieldnames are present in row
                    row_data = {name: row.get(name, "") for name in fieldnames}
                    writer.writerow(row_data)
                except Exception:
                    continue
        else:
            # Standard processing: Write contact rows using Connectra
            try:
                async with ConnectraClient() as client:
                    transformer = VQLTransformer()
                    batch_size = 100
                    
                    # Fetch contacts via Connectra
                    if contact_uuids:
                        all_contact_data = await client.batch_search_by_uuids(
                            contact_uuids, entity_type="contact", batch_size=batch_size
                        )
                        contacts_list = transformer.transform_contact_response({"data": all_contact_data})
                        contacts_map = {c.uuid: c for c in contacts_list}
                        
                        for contact_uuid in contact_uuids:
                            try:
                                contact_item = contacts_map.get(contact_uuid)
                                if not contact_item:
                                    continue
                                
                                # Get LinkedIn URL from contact_item
                                linkedin_url = get_value(contact_item.person_linkedin_url)
                                
                                departments_list = None
                                if contact_item.departments:
                                    departments_list = [d.strip() for d in contact_item.departments.split(",") if d.strip()]
                                
                                row = {
                                    "record_type": "contact",
                                    "linkedin_url": linkedin_url,
                                    # Contact fields
                                    "contact_uuid": get_value(contact_item.uuid),
                                    "contact_first_name": get_value(contact_item.first_name),
                                    "contact_last_name": get_value(contact_item.last_name),
                                    "contact_company_id": "",
                                    "contact_email": get_value(contact_item.email),
                                    "contact_title": get_value(contact_item.title),
                                    "contact_departments": format_array(departments_list),
                                    "contact_mobile_phone": get_value(contact_item.mobile_phone),
                                    "contact_email_status": get_value(contact_item.email_status),
                                    "contact_text_search": "",
                                    "contact_seniority": get_value(contact_item.seniority),
                                    "contact_created_at": format_datetime(contact_item.created_at),
                                    "contact_updated_at": format_datetime(contact_item.updated_at),
                                    # Contact Metadata fields
                                    "contact_metadata_linkedin_url": linkedin_url,
                                    "contact_metadata_facebook_url": get_value(contact_item.facebook_url),
                                    "contact_metadata_twitter_url": get_value(contact_item.twitter_url),
                                    "contact_metadata_website": get_value(contact_item.website),
                                    "contact_metadata_work_direct_phone": get_value(contact_item.work_direct_phone),
                                    "contact_metadata_home_phone": get_value(contact_item.home_phone),
                                    "contact_metadata_city": get_value(contact_item.city),
                                    "contact_metadata_state": get_value(contact_item.state),
                                    "contact_metadata_country": get_value(contact_item.country),
                                    "contact_metadata_other_phone": get_value(contact_item.other_phone),
                                    "contact_metadata_stage": get_value(contact_item.stage),
                                    # Company fields (from contact_item)
                                    "company_uuid": "",
                                    "company_name": get_value(contact_item.company),
                                    "company_employees_count": str(contact_item.employees) if contact_item.employees else "",
                                    "company_industries": format_array([contact_item.industry] if contact_item.industry else None),
                                    "company_keywords": format_array(contact_item.keywords.split(", ") if contact_item.keywords else None),
                                    "company_address": get_value(contact_item.company_address),
                                    "company_annual_revenue": str(contact_item.annual_revenue) if contact_item.annual_revenue else "",
                                    "company_total_funding": str(contact_item.total_funding) if contact_item.total_funding else "",
                                    "company_technologies": format_array(contact_item.technologies.split(", ") if contact_item.technologies else None),
                                    "company_text_search": "",
                                    "company_created_at": "",
                                    "company_updated_at": "",
                                    # Company Metadata fields
                                    "company_metadata_linkedin_url": get_value(contact_item.company_linkedin_url),
                                    "company_metadata_facebook_url": "",
                                    "company_metadata_twitter_url": "",
                                    "company_metadata_website": get_value(contact_item.website),
                                    "company_metadata_company_name_for_emails": get_value(contact_item.company_name_for_emails),
                                    "company_metadata_phone_number": get_value(contact_item.company_phone),
                                    "company_metadata_latest_funding": get_value(contact_item.latest_funding),
                                    "company_metadata_latest_funding_amount": str(contact_item.latest_funding_amount) if contact_item.latest_funding_amount else "",
                                    "company_metadata_last_raised_at": get_value(contact_item.last_raised_at),
                                    "company_metadata_city": get_value(contact_item.company_city),
                                    "company_metadata_state": get_value(contact_item.company_state),
                                    "company_metadata_country": get_value(contact_item.company_country),
                                }
                                
                                writer.writerow(row)
                                
                            except Exception:
                                continue
                    
                    # Batch fetch all companies and their metadata for company rows using Connectra
                    if company_uuids:
                        all_company_data = await client.batch_search_by_uuids(
                            company_uuids, entity_type="company", batch_size=batch_size
                        )
                        companies_list = transformer.transform_company_response({"data": all_company_data})
                        companies_map = {c.uuid: c for c in companies_list}
                        
                        # Write company rows
                        for company_uuid in company_uuids:
                            try:
                                company_item = companies_map.get(company_uuid)
                                if not company_item:
                                    continue
                                
                                # Extract metadata from company_item
                                company_meta = None
                                if hasattr(company_item, 'metadata') and company_item.metadata:
                                    company_meta = company_item.metadata
                                
                                # Get LinkedIn URL from metadata
                                linkedin_url = get_value(company_item.linkedin_url)
                                
                                industries_list = None
                                if company_item.industry:
                                    industries_list = [company_item.industry]
                                elif hasattr(company_item, 'industries') and company_item.industries:
                                    industries_list = company_item.industries
                                
                                row_data = {
                                    "record_type": "company",
                                    "linkedin_url": linkedin_url,
                                    # Contact fields (empty for companies)
                                    "contact_uuid": "",
                                    "contact_first_name": "",
                                    "contact_last_name": "",
                                    "contact_company_id": "",
                                    "contact_email": "",
                                    "contact_title": "",
                                    "contact_departments": "",
                                    "contact_mobile_phone": "",
                                    "contact_email_status": "",
                                    "contact_text_search": "",
                                    "contact_seniority": "",
                                    "contact_created_at": "",
                                    "contact_updated_at": "",
                                    # Contact Metadata fields (empty for companies)
                                    "contact_metadata_linkedin_url": "",
                                    "contact_metadata_facebook_url": "",
                                    "contact_metadata_twitter_url": "",
                                    "contact_metadata_website": "",
                                    "contact_metadata_work_direct_phone": "",
                                    "contact_metadata_home_phone": "",
                                    "contact_metadata_city": "",
                                    "contact_metadata_state": "",
                                    "contact_metadata_country": "",
                                    "contact_metadata_other_phone": "",
                                    "contact_metadata_stage": "",
                                    # Company fields
                                    "company_uuid": get_value(company_item.uuid),
                                    "company_name": get_value(company_item.name),
                                    "company_employees_count": str(company_item.employees_count) if company_item.employees_count else "",
                                    "company_industries": format_array(industries_list),
                                    "company_keywords": format_array(company_item.keywords),
                                    "company_address": "",
                                    "company_annual_revenue": str(company_item.annual_revenue) if company_item.annual_revenue else "",
                                    "company_total_funding": str(company_item.total_funding) if company_item.total_funding else "",
                                    "company_technologies": format_array(company_item.technologies),
                                    "company_text_search": "",
                                    "company_created_at": "",
                                    "company_updated_at": "",
                                    # Company Metadata fields
                                    "company_metadata_linkedin_url": linkedin_url,
                                    "company_metadata_facebook_url": get_value(company_meta.facebook_url if company_meta else None),
                                    "company_metadata_twitter_url": get_value(company_meta.twitter_url if company_meta else None),
                                    "company_metadata_website": get_value(company_item.website),
                                    "company_metadata_company_name_for_emails": get_value(company_meta.company_name_for_emails if company_meta else None),
                                    "company_metadata_phone_number": get_value(getattr(company_item, 'phone_number', None) or (company_meta.phone_number if company_meta else None)),
                                    "company_metadata_latest_funding": get_value(company_meta.latest_funding if company_meta else None),
                                    "company_metadata_latest_funding_amount": str(company_meta.latest_funding_amount) if company_meta and company_meta.latest_funding_amount else "",
                                    "company_metadata_last_raised_at": get_value(company_meta.last_raised_at if company_meta else None),
                                    "company_metadata_city": get_value(company_item.city),
                                    "company_metadata_state": get_value(company_item.state),
                                    "company_metadata_country": get_value(company_item.country),
                                }
                                
                                writer.writerow(row_data)
                                
                            except Exception:
                                continue
                    
                    # Write not_found rows (only if not using CSV context)
                    for url in unmatched_urls:
                        row_data = {
                            "record_type": "not_found",
                            "linkedin_url": url,
                            # All other fields empty
                        }
                        # Fill all other fields with empty strings
                        for field in fieldnames:
                            if field not in row_data:
                                row_data[field] = ""
                        
                        writer.writerow(row_data)
            except Exception as exc:
                logger.error(f"Connectra LinkedIn export failed: {exc}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Export service temporarily unavailable"
                ) from exc
        
        # Get CSV content as bytes
        csv_content = csv_buffer.getvalue().encode("utf-8")
        csv_buffer.close()
        
        # Upload to S3 if configured, otherwise save locally
        if settings.S3_BUCKET_NAME:
            try:
                s3_key = f"{self.s3_service.exports_prefix}{export_id}.csv"
                await self.s3_service.upload_file(
                    file_content=csv_content,
                    s3_key=s3_key,
                    content_type="text/csv",
                )
                return s3_key
            except Exception:
                # Fallback to local storage
                exports_dir = Path(settings.UPLOAD_DIR) / "exports"
                exports_dir.mkdir(parents=True, exist_ok=True)
                file_path = exports_dir / f"{export_id}.csv"
                with file_path.open("wb") as f:
                    f.write(csv_content)
                return str(file_path)
        else:
            # Save locally
            exports_dir = Path(settings.UPLOAD_DIR) / "exports"
            exports_dir.mkdir(parents=True, exist_ok=True)
            file_path = exports_dir / f"{export_id}.csv"
            with file_path.open("wb") as f:
                f.write(csv_content)
            return str(file_path)

