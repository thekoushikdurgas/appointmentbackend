"""Service layer for managing contact export jobs."""

import csv
import io
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Sequence

import aiofiles
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from typing import Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.companies import Company
from app.models.exports import ExportStatus, ExportType, UserExport
from app.repositories.companies import CompanyRepository
from app.repositories.contacts import ContactRepository
from app.schemas.filters import ExportFilterParams
from app.services.s3_service import S3Service
from app.utils.signed_url import generate_signed_url

settings = get_settings()
logger = get_logger(__name__)


class ExportService:
    """Encapsulate export job orchestration."""

    def __init__(
        self,
        contact_repository: Optional[ContactRepository] = None,
        company_repository: Optional[CompanyRepository] = None,
        s3_service: Optional[S3Service] = None,
    ) -> None:
        """Initialize the export service with repository dependencies."""
        self.contact_repo = contact_repository or ContactRepository()
        self.company_repo = company_repository or CompanyRepository()
        self.s3_service = s3_service or S3Service()
        logger.debug("Initialized ExportService")

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
            logger.info(
                "Creating contact export: user_id=%s contact_count=%d",
                user_id,
                len(contact_uuids) if contact_uuids else 0,
            )
            export = UserExport(
                user_id=user_id,
                export_type=export_type,
                contact_uuids=contact_uuids or [],
                contact_count=len(contact_uuids) if contact_uuids else 0,
                linkedin_urls=linkedin_urls,
                status=ExportStatus.pending,
            )
        elif export_type == ExportType.companies:
            logger.info(
                "Creating company export: user_id=%s company_count=%d",
                user_id,
                len(company_uuids) if company_uuids else 0,
            )
            export = UserExport(
                user_id=user_id,
                export_type=export_type,
                company_uuids=company_uuids or [],
                company_count=len(company_uuids) if company_uuids else 0,
                linkedin_urls=linkedin_urls,
                status=ExportStatus.pending,
            )
        else:  # emails
            logger.info(
                "Creating email export: user_id=%s",
                user_id,
            )
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
        
        logger.debug("Created export: export_id=%s export_type=%s", export.export_id, export_type)
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
        logger.info("Generating CSV: export_id=%s contact_count=%d", export_id, len(contact_uuids))
        
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
            for i in range(0, len(contact_uuids), batch_size):
                batch_uuids = contact_uuids[i:i + batch_size]
                
                for contact_uuid in batch_uuids:
                    try:
                        result = await self.contact_repo.get_contact_with_relations(
                            session, contact_uuid
                        )
                        
                        if not result:
                            logger.warning("Contact not found: contact_uuid=%s", contact_uuid)
                            continue
                        
                        contact, company, contact_meta, company_meta = result
                        
                        # Helper function to format array fields
                        def format_array(value):
                            if value is None:
                                return ""
                            if isinstance(value, list):
                                return ",".join(str(v) for v in value if v)
                            return str(value) if value else ""
                        
                        # Helper function to format datetime
                        def format_datetime(value):
                            if value is None:
                                return ""
                            if isinstance(value, datetime):
                                return value.isoformat()
                            return str(value) if value else ""
                        
                        # Helper function to get value or empty string
                        def get_value(value, default=""):
                            if value is None:
                                return default
                            if value == "_":  # Default placeholder in metadata
                                return ""
                            return str(value)
                        
                        row = {
                            # Contact fields
                            "contact_uuid": contact.uuid or "",
                            "contact_first_name": contact.first_name or "",
                            "contact_last_name": contact.last_name or "",
                            "contact_company_id": contact.company_id or "",
                            "contact_email": contact.email or "",
                            "contact_title": contact.title or "",
                            "contact_departments": format_array(contact.departments),
                            "contact_mobile_phone": contact.mobile_phone or "",
                            "contact_email_status": contact.email_status or "",
                            "contact_text_search": contact.text_search or "",
                            "contact_seniority": contact.seniority or "",
                            "contact_created_at": format_datetime(contact.created_at),
                            "contact_updated_at": format_datetime(contact.updated_at),
                            # Contact Metadata fields
                            "contact_metadata_linkedin_url": get_value(contact_meta.linkedin_url if contact_meta else None),
                            "contact_metadata_facebook_url": get_value(contact_meta.facebook_url if contact_meta else None),
                            "contact_metadata_twitter_url": get_value(contact_meta.twitter_url if contact_meta else None),
                            "contact_metadata_website": get_value(contact_meta.website if contact_meta else None),
                            "contact_metadata_work_direct_phone": get_value(contact_meta.work_direct_phone if contact_meta else None),
                            "contact_metadata_home_phone": get_value(contact_meta.home_phone if contact_meta else None),
                            "contact_metadata_city": get_value(contact_meta.city if contact_meta else None),
                            "contact_metadata_state": get_value(contact_meta.state if contact_meta else None),
                            "contact_metadata_country": get_value(contact_meta.country if contact_meta else None),
                            "contact_metadata_other_phone": get_value(contact_meta.other_phone if contact_meta else None),
                            "contact_metadata_stage": get_value(contact_meta.stage if contact_meta else None),
                            # Company fields
                            "company_uuid": company.uuid if company else "",
                            "company_name": company.name if company else "",
                            "company_employees_count": str(company.employees_count) if company and company.employees_count else "",
                            "company_industries": format_array(company.industries if company else None),
                            "company_keywords": format_array(company.keywords if company else None),
                            "company_address": company.address if company else "",
                            "company_annual_revenue": str(company.annual_revenue) if company and company.annual_revenue else "",
                            "company_total_funding": str(company.total_funding) if company and company.total_funding else "",
                            "company_technologies": format_array(company.technologies if company else None),
                            "company_text_search": company.text_search if company else "",
                            "company_created_at": format_datetime(company.created_at if company else None),
                            "company_updated_at": format_datetime(company.updated_at if company else None),
                            # Company Metadata fields
                            "company_metadata_linkedin_url": company_meta.linkedin_url if company_meta else "",
                            "company_metadata_facebook_url": company_meta.facebook_url if company_meta else "",
                            "company_metadata_twitter_url": company_meta.twitter_url if company_meta else "",
                            "company_metadata_website": company_meta.website if company_meta else "",
                            "company_metadata_company_name_for_emails": company_meta.company_name_for_emails if company_meta else "",
                            "company_metadata_phone_number": company_meta.phone_number if company_meta else "",
                            "company_metadata_latest_funding": company_meta.latest_funding if company_meta else "",
                            "company_metadata_latest_funding_amount": str(company_meta.latest_funding_amount) if company_meta and company_meta.latest_funding_amount else "",
                            "company_metadata_last_raised_at": company_meta.last_raised_at if company_meta else "",
                            "company_metadata_city": company_meta.city if company_meta else "",
                            "company_metadata_state": company_meta.state if company_meta else "",
                            "company_metadata_country": company_meta.country if company_meta else "",
                        }
                        
                        # Write row as CSV line
                        row_values = [str(row.get(field, "")) for field in fieldnames]
                        # Escape CSV values (simple escaping for commas and quotes)
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
                        logger.exception(
                            "Failed to process contact for export: contact_uuid=%s error=%s",
                            contact_uuid,
                            str(exc),
                        )
                        # Continue with next contact even if one fails
                        continue
        
        logger.info("CSV generation completed: export_id=%s rows=%d", export_id, row_count)
        
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
                logger.debug("CSV uploaded to S3: key=%s size=%d", s3_key, len(csv_content))
                
                # Clean up temp file
                temp_file_path.unlink(missing_ok=True)
                return s3_key
            except Exception as exc:
                logger.exception("Failed to upload CSV to S3: export_id=%s", export_id)
                # Fallback to local storage - rename temp file
                file_path = exports_dir / f"{export_id}.csv"
                temp_file_path.rename(file_path)
                logger.debug("CSV saved locally (S3 upload failed): file_path=%s", file_path)
                return str(file_path)
        else:
            # Save locally - rename temp file to final location
            file_path = exports_dir / f"{export_id}.csv"
            temp_file_path.rename(file_path)
            logger.debug("CSV saved locally: file_path=%s", file_path)
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
        logger.info(
            "Updating export status: export_id=%s status=%s file_path=%s",
            export_id,
            status,
            file_path,
        )
        
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
        
        logger.debug("Updated export: export_id=%s status=%s", export_id, status)
        return export

    async def get_export(
        self,
        session: AsyncSession,
        export_id: str,
        user_id: str,
    ) -> Optional[UserExport]:
        """Retrieve export record with user validation."""
        logger.debug("Getting export: export_id=%s user_id=%s", export_id, user_id)
        
        stmt = select(UserExport).where(
            UserExport.export_id == export_id,
            UserExport.user_id == user_id,
        )
        result = await session.execute(stmt)
        export = result.scalar_one_or_none()
        
        if export:
            logger.debug("Found export: export_id=%s", export_id)
        else:
            logger.warning("Export not found or access denied: export_id=%s user_id=%s", export_id, user_id)
        
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
        logger.info("Generating company CSV: export_id=%s company_count=%d", export_id, len(company_uuids))
        
        # Generate CSV in memory
        import io
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
        
        # Fetch companies and write to CSV
        writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
        writer.writeheader()
        
        for company_uuid in company_uuids:
                try:
                    # Get company with metadata using base_query
                    stmt, company_meta_alias = self.company_repo.base_query()
                    stmt = stmt.where(Company.uuid == company_uuid)
                    result = await session.execute(stmt)
                    row = result.first()
                    
                    if not row:
                        logger.warning("Company not found: company_uuid=%s", company_uuid)
                        continue
                    
                    company, company_meta = row
                    
                    # Helper function to format array fields
                    def format_array(value):
                        if value is None:
                            return ""
                        if isinstance(value, list):
                            return ",".join(str(v) for v in value if v)
                        return str(value) if value else ""
                    
                    # Helper function to format datetime
                    def format_datetime(value):
                        if value is None:
                            return ""
                        if isinstance(value, datetime):
                            return value.isoformat()
                        return str(value) if value else ""
                    
                    # Helper function to get value or empty string
                    def get_value(value, default=""):
                        if value is None:
                            return default
                        if value == "_":  # Default placeholder in metadata
                            return ""
                        return str(value)
                    
                    row_data = {
                        # Company fields
                        "company_uuid": company.uuid or "",
                        "company_name": company.name or "",
                        "company_employees_count": str(company.employees_count) if company.employees_count else "",
                        "company_industries": format_array(company.industries),
                        "company_keywords": format_array(company.keywords),
                        "company_address": company.address or "",
                        "company_annual_revenue": str(company.annual_revenue) if company.annual_revenue else "",
                        "company_total_funding": str(company.total_funding) if company.total_funding else "",
                        "company_technologies": format_array(company.technologies),
                        "company_text_search": company.text_search or "",
                        "company_created_at": format_datetime(company.created_at),
                        "company_updated_at": format_datetime(company.updated_at),
                        # Company Metadata fields
                        "company_metadata_linkedin_url": get_value(company_meta.linkedin_url if company_meta else None),
                        "company_metadata_facebook_url": get_value(company_meta.facebook_url if company_meta else None),
                        "company_metadata_twitter_url": get_value(company_meta.twitter_url if company_meta else None),
                        "company_metadata_website": get_value(company_meta.website if company_meta else None),
                        "company_metadata_company_name_for_emails": get_value(company_meta.company_name_for_emails if company_meta else None),
                        "company_metadata_phone_number": get_value(company_meta.phone_number if company_meta else None),
                        "company_metadata_latest_funding": get_value(company_meta.latest_funding if company_meta else None),
                        "company_metadata_latest_funding_amount": str(company_meta.latest_funding_amount) if company_meta and company_meta.latest_funding_amount else "",
                        "company_metadata_last_raised_at": get_value(company_meta.last_raised_at if company_meta else None),
                        "company_metadata_city": get_value(company_meta.city if company_meta else None),
                        "company_metadata_state": get_value(company_meta.state if company_meta else None),
                        "company_metadata_country": get_value(company_meta.country if company_meta else None),
                    }
                    
                    writer.writerow(row_data)
                    
                except Exception as exc:
                    logger.exception(
                        "Failed to process company for export: company_uuid=%s error=%s",
                        company_uuid,
                        str(exc),
                    )
                    # Continue with next company even if one fails
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
                logger.debug("Company CSV uploaded to S3: key=%s", s3_key)
                return s3_key
            except Exception as exc:
                logger.exception("Failed to upload company CSV to S3: export_id=%s", export_id)
                # Fallback to local storage
                exports_dir = Path(settings.UPLOAD_DIR) / "exports"
                exports_dir.mkdir(parents=True, exist_ok=True)
                file_path = exports_dir / f"{export_id}.csv"
                with file_path.open("wb") as f:
                    f.write(csv_content)
                logger.debug("Company CSV saved locally (S3 upload failed): file_path=%s", file_path)
                return str(file_path)
        else:
            # Save locally
            exports_dir = Path(settings.UPLOAD_DIR) / "exports"
            exports_dir.mkdir(parents=True, exist_ok=True)
            file_path = exports_dir / f"{export_id}.csv"
            with file_path.open("wb") as f:
                f.write(csv_content)
                logger.debug("Company CSV saved locally: file_path=%s", file_path)
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
        logger.info(
            "Generating email export CSV: export_id=%s contact_count=%d",
            export_id,
            len(contacts_data),
        )
        
        # Generate CSV in memory
        import io
        csv_buffer = io.StringIO()
        
        # Define CSV fieldnames
        # If a specific header order was provided (e.g. original CSV headers),
        # use it. Otherwise, fall back to the minimal legacy header set.
        if fieldnames is None:
            fieldnames = ["first_name", "last_name", "domain", "email"]
        logger.debug(
            "CSV fieldnames defined: export_id=%s fieldnames=%s",
            export_id,
            fieldnames,
        )
        
        # Write CSV
        writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
        writer.writeheader()
        logger.debug(
            "CSV header written: export_id=%s",
            export_id,
        )
        
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
            except Exception as exc:
                rows_failed += 1
                logger.exception(
                    "Failed to write contact row: export_id=%s contact=%s error=%s",
                    export_id,
                    contact,
                    str(exc),
                )
                # Continue with next contact even if one fails
                continue
        
        logger.debug(
            "CSV rows written: export_id=%s rows_written=%d rows_failed=%d",
            export_id,
            rows_written,
            rows_failed,
        )
        
        # Get CSV content as bytes
        csv_content = csv_buffer.getvalue().encode("utf-8")
        csv_buffer.close()
        logger.debug(
            "CSV content generated: export_id=%s size=%d bytes",
            export_id,
            len(csv_content),
        )
        
        # Upload to S3 if configured, otherwise save locally
        if settings.S3_BUCKET_NAME:
            logger.info(
                "Uploading CSV to S3: export_id=%s bucket=%s",
                export_id,
                settings.S3_BUCKET_NAME,
            )
            try:
                s3_key = f"{self.s3_service.exports_prefix}{export_id}.csv"
                await self.s3_service.upload_file(
                    file_content=csv_content,
                    s3_key=s3_key,
                    content_type="text/csv",
                )
                logger.info(
                    "Email export CSV uploaded to S3: export_id=%s key=%s size=%d bytes",
                    export_id,
                    s3_key,
                    len(csv_content),
                )
                return s3_key
            except Exception as exc:
                logger.exception(
                    "Failed to upload email export CSV to S3: export_id=%s error=%s",
                    export_id,
                    exc,
                )
                # Fallback to local storage
                logger.warning(
                    "Falling back to local storage: export_id=%s",
                    export_id,
                )
                exports_dir = Path(settings.UPLOAD_DIR) / "exports"
                exports_dir.mkdir(parents=True, exist_ok=True)
                file_path = exports_dir / f"{export_id}.csv"
                async with aiofiles.open(file_path, "wb") as async_file:
                    await async_file.write(csv_content)
                logger.info(
                    "Email export CSV saved locally (S3 upload failed): export_id=%s file_path=%s size=%d bytes",
                    export_id,
                    file_path,
                    len(csv_content),
                )
                return str(file_path)
        else:
            # Save locally
            logger.info(
                "Saving CSV locally: export_id=%s",
                export_id,
            )
            exports_dir = Path(settings.UPLOAD_DIR) / "exports"
            exports_dir.mkdir(parents=True, exist_ok=True)
            file_path = exports_dir / f"{export_id}.csv"
            async with aiofiles.open(file_path, "wb") as async_file:
                await async_file.write(csv_content)
            logger.info(
                "Email export CSV saved locally: export_id=%s file_path=%s size=%d bytes",
                export_id,
                file_path,
                len(csv_content),
            )
            return str(file_path)

    async def list_user_exports(
        self,
        session: AsyncSession,
        user_id: str,
        filters: Optional[ExportFilterParams] = None,
    ) -> Sequence[UserExport]:
        """List all exports for a user, ordered by created_at descending, with optional filters."""
        logger.debug(
            "Listing exports for user: user_id=%s filters=%s",
            user_id,
            filters.model_dump(exclude_none=True) if filters else None,
        )
        
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
        
        logger.debug("Found %d exports for user: user_id=%s", len(exports), user_id)
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
                logger.warning("Invalid export status filter: %s", filters.status)
        
        # Export type filter
        if filters.export_type:
            try:
                export_type_enum = ExportType(filters.export_type.lower())
                stmt = stmt.where(UserExport.export_type == export_type_enum)
            except ValueError:
                # Invalid type, ignore filter
                logger.warning("Invalid export type filter: %s", filters.export_type)
        
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
        logger.info("Deleting all CSV files from exports directory")
        
        exports_dir = Path(settings.UPLOAD_DIR) / "exports"
        
        if not exports_dir.exists():
            logger.warning("Exports directory does not exist: %s", exports_dir)
            return 0
        
        deleted_count = 0
        try:
            # Find all CSV files in exports directory
            csv_files = list(exports_dir.glob("*.csv"))
            
            for csv_file in csv_files:
                try:
                    csv_file.unlink()
                    deleted_count += 1
                    logger.debug("Deleted CSV file: %s", csv_file)
                except Exception as exc:
                    logger.exception("Failed to delete CSV file: %s error=%s", csv_file, str(exc))
                    # Continue with other files
            
            logger.info("Deleted %d CSV files", deleted_count)
            
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
                logger.info("Cleaned up %d expired export records", len(expired_exports))
            
        except Exception as exc:
            logger.exception("Error deleting CSV files: %s", str(exc))
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
        logger.info(
            "Merging CSV files: main_export_id=%s chunk_count=%d",
            main_export_id,
            len(chunk_export_ids),
        )
        
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
                logger.warning("Chunk export has no file path: export_id=%s", chunk_export.export_id)
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
                    logger.warning("Chunk export file not found: file_path=%s", file_path)
                    continue
                async with aiofiles.open(local_path, "rb") as f:
                    csv_content = await f.read()
            
            if not csv_content:
                logger.warning("No content read from chunk export: export_id=%s", chunk_export.export_id)
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
            
            logger.debug(
                "Read chunk CSV: export_id=%s rows=%d",
                chunk_export.export_id,
                row_count,
            )
        
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
        
        logger.info(
            "Merged CSV created: main_export_id=%s total_rows=%d",
            main_export_id,
            row_count,
        )
        
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
                logger.debug("Merged CSV uploaded to S3: key=%s size=%d", s3_key, len(csv_content))
                
                # Clean up temp file
                temp_file_path.unlink(missing_ok=True)
                return s3_key
            except Exception as exc:
                logger.exception("Failed to upload merged CSV to S3: main_export_id=%s", main_export_id)
                # Fallback to local storage
                file_path = exports_dir / f"{main_export_id}.csv"
                temp_file_path.rename(file_path)
                logger.debug("Merged CSV saved locally (S3 upload failed): file_path=%s", file_path)
                return str(file_path)
        else:
            # Save locally - rename temp file to final location
            file_path = exports_dir / f"{main_export_id}.csv"
            temp_file_path.rename(file_path)
            logger.debug("Merged CSV saved locally: file_path=%s", file_path)
            return str(file_path)

    async def generate_linkedin_export_csv(
        self,
        session: AsyncSession,
        export_id: str,
        contact_uuids: list[str],
        company_uuids: list[str],
        unmatched_urls: list[str],
    ) -> str:
        """
        Generate combined CSV with contacts, companies, and unmatched URLs.
        
        Creates a CSV file with a record_type column to distinguish between
        contacts, companies, and not_found entries. Includes all contact and
        company fields, with empty values for fields that don't apply.
        
        Args:
            session: Database session
            export_id: Export record ID
            contact_uuids: List of contact UUIDs to export
            company_uuids: List of company UUIDs to export
            unmatched_urls: List of LinkedIn URLs that didn't match anything
            
        Returns:
            S3 key or local file path to the generated CSV file
        """
        logger.info(
            "Generating LinkedIn export CSV: export_id=%s contacts=%d companies=%d unmatched=%d",
            export_id,
            len(contact_uuids),
            len(company_uuids),
            len(unmatched_urls),
        )
        
        # Generate CSV in memory
        csv_buffer = io.StringIO()
        
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
        
        # Write contact rows
        for contact_uuid in contact_uuids:
            try:
                result = await self.contact_repo.get_contact_with_relations(
                    session, contact_uuid
                )
                
                if not result:
                    logger.warning("Contact not found: contact_uuid=%s", contact_uuid)
                    continue
                
                contact, company, contact_meta, company_meta = result
                
                # Get LinkedIn URL from metadata
                linkedin_url = get_value(contact_meta.linkedin_url if contact_meta else None)
                
                row = {
                    "record_type": "contact",
                    "linkedin_url": linkedin_url,
                    # Contact fields
                    "contact_uuid": contact.uuid or "",
                    "contact_first_name": contact.first_name or "",
                    "contact_last_name": contact.last_name or "",
                    "contact_company_id": contact.company_id or "",
                    "contact_email": contact.email or "",
                    "contact_title": contact.title or "",
                    "contact_departments": format_array(contact.departments),
                    "contact_mobile_phone": contact.mobile_phone or "",
                    "contact_email_status": contact.email_status or "",
                    "contact_text_search": contact.text_search or "",
                    "contact_seniority": contact.seniority or "",
                    "contact_created_at": format_datetime(contact.created_at),
                    "contact_updated_at": format_datetime(contact.updated_at),
                    # Contact Metadata fields
                    "contact_metadata_linkedin_url": linkedin_url,
                    "contact_metadata_facebook_url": get_value(contact_meta.facebook_url if contact_meta else None),
                    "contact_metadata_twitter_url": get_value(contact_meta.twitter_url if contact_meta else None),
                    "contact_metadata_website": get_value(contact_meta.website if contact_meta else None),
                    "contact_metadata_work_direct_phone": get_value(contact_meta.work_direct_phone if contact_meta else None),
                    "contact_metadata_home_phone": get_value(contact_meta.home_phone if contact_meta else None),
                    "contact_metadata_city": get_value(contact_meta.city if contact_meta else None),
                    "contact_metadata_state": get_value(contact_meta.state if contact_meta else None),
                    "contact_metadata_country": get_value(contact_meta.country if contact_meta else None),
                    "contact_metadata_other_phone": get_value(contact_meta.other_phone if contact_meta else None),
                    "contact_metadata_stage": get_value(contact_meta.stage if contact_meta else None),
                    # Company fields (from related company)
                    "company_uuid": company.uuid if company else "",
                    "company_name": company.name if company else "",
                    "company_employees_count": str(company.employees_count) if company and company.employees_count else "",
                    "company_industries": format_array(company.industries if company else None),
                    "company_keywords": format_array(company.keywords if company else None),
                    "company_address": company.address if company else "",
                    "company_annual_revenue": str(company.annual_revenue) if company and company.annual_revenue else "",
                    "company_total_funding": str(company.total_funding) if company and company.total_funding else "",
                    "company_technologies": format_array(company.technologies if company else None),
                    "company_text_search": company.text_search if company else "",
                    "company_created_at": format_datetime(company.created_at if company else None),
                    "company_updated_at": format_datetime(company.updated_at if company else None),
                    # Company Metadata fields
                    "company_metadata_linkedin_url": get_value(company_meta.linkedin_url if company_meta else None),
                    "company_metadata_facebook_url": get_value(company_meta.facebook_url if company_meta else None),
                    "company_metadata_twitter_url": get_value(company_meta.twitter_url if company_meta else None),
                    "company_metadata_website": get_value(company_meta.website if company_meta else None),
                    "company_metadata_company_name_for_emails": get_value(company_meta.company_name_for_emails if company_meta else None),
                    "company_metadata_phone_number": get_value(company_meta.phone_number if company_meta else None),
                    "company_metadata_latest_funding": get_value(company_meta.latest_funding if company_meta else None),
                    "company_metadata_latest_funding_amount": str(company_meta.latest_funding_amount) if company_meta and company_meta.latest_funding_amount else "",
                    "company_metadata_last_raised_at": get_value(company_meta.last_raised_at if company_meta else None),
                    "company_metadata_city": get_value(company_meta.city if company_meta else None),
                    "company_metadata_state": get_value(company_meta.state if company_meta else None),
                    "company_metadata_country": get_value(company_meta.country if company_meta else None),
                }
                
                writer.writerow(row)
                
            except Exception as exc:
                logger.exception(
                    "Failed to process contact for export: contact_uuid=%s error=%s",
                    contact_uuid,
                    str(exc),
                )
                continue
        
        # Write company rows
        for company_uuid in company_uuids:
            try:
                # Get company with metadata using base_query
                stmt, company_meta_alias = self.company_repo.base_query()
                stmt = stmt.where(Company.uuid == company_uuid)
                result = await session.execute(stmt)
                row = result.first()
                
                if not row:
                    logger.warning("Company not found: company_uuid=%s", company_uuid)
                    continue
                
                company, company_meta = row
                
                # Get LinkedIn URL from metadata
                linkedin_url = get_value(company_meta.linkedin_url if company_meta else None)
                
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
                    "company_uuid": company.uuid or "",
                    "company_name": company.name or "",
                    "company_employees_count": str(company.employees_count) if company.employees_count else "",
                    "company_industries": format_array(company.industries),
                    "company_keywords": format_array(company.keywords),
                    "company_address": company.address or "",
                    "company_annual_revenue": str(company.annual_revenue) if company.annual_revenue else "",
                    "company_total_funding": str(company.total_funding) if company.total_funding else "",
                    "company_technologies": format_array(company.technologies),
                    "company_text_search": company.text_search or "",
                    "company_created_at": format_datetime(company.created_at),
                    "company_updated_at": format_datetime(company.updated_at),
                    # Company Metadata fields
                    "company_metadata_linkedin_url": linkedin_url,
                    "company_metadata_facebook_url": get_value(company_meta.facebook_url if company_meta else None),
                    "company_metadata_twitter_url": get_value(company_meta.twitter_url if company_meta else None),
                    "company_metadata_website": get_value(company_meta.website if company_meta else None),
                    "company_metadata_company_name_for_emails": get_value(company_meta.company_name_for_emails if company_meta else None),
                    "company_metadata_phone_number": get_value(company_meta.phone_number if company_meta else None),
                    "company_metadata_latest_funding": get_value(company_meta.latest_funding if company_meta else None),
                    "company_metadata_latest_funding_amount": str(company_meta.latest_funding_amount) if company_meta and company_meta.latest_funding_amount else "",
                    "company_metadata_last_raised_at": get_value(company_meta.last_raised_at if company_meta else None),
                    "company_metadata_city": get_value(company_meta.city if company_meta else None),
                    "company_metadata_state": get_value(company_meta.state if company_meta else None),
                    "company_metadata_country": get_value(company_meta.country if company_meta else None),
                }
                
                writer.writerow(row_data)
                
            except Exception as exc:
                logger.exception(
                    "Failed to process company for export: company_uuid=%s error=%s",
                    company_uuid,
                    str(exc),
                )
                continue
        
        # Write not_found rows
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
                logger.debug("LinkedIn export CSV uploaded to S3: key=%s", s3_key)
                return s3_key
            except Exception as exc:
                logger.exception("Failed to upload LinkedIn export CSV to S3: export_id=%s", export_id)
                # Fallback to local storage
                exports_dir = Path(settings.UPLOAD_DIR) / "exports"
                exports_dir.mkdir(parents=True, exist_ok=True)
                file_path = exports_dir / f"{export_id}.csv"
                with file_path.open("wb") as f:
                    f.write(csv_content)
                logger.debug("LinkedIn export CSV saved locally (S3 upload failed): file_path=%s", file_path)
                return str(file_path)
        else:
            # Save locally
            exports_dir = Path(settings.UPLOAD_DIR) / "exports"
            exports_dir.mkdir(parents=True, exist_ok=True)
            file_path = exports_dir / f"{export_id}.csv"
            with file_path.open("wb") as f:
                f.write(csv_content)
            logger.debug("LinkedIn export CSV saved locally: file_path=%s", file_path)
            return str(file_path)

