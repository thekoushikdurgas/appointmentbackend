"""Service layer for managing contact export jobs."""

import csv
import io
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.companies import Company
from app.models.exports import ExportStatus, ExportType, UserExport
from app.repositories.companies import CompanyRepository
from app.repositories.contacts import ContactRepository
from app.services.s3_service import S3Service
from app.utils.signed_url import generate_signed_url

settings = get_settings()
logger = get_logger(__name__)


class ExportService:
    """Encapsulate export job orchestration."""

    def __init__(self) -> None:
        """Initialize the export service."""
        self.contact_repo = ContactRepository()
        self.company_repo = CompanyRepository()
        self.s3_service = S3Service()
        logger.debug("Initialized ExportService")

    async def create_export(
        self,
        session: AsyncSession,
        user_id: str,
        export_type: ExportType,
        contact_uuids: Optional[list[str]] = None,
        company_uuids: Optional[list[str]] = None,
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
                status=ExportStatus.pending,
            )
        else:  # companies
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
                status=ExportStatus.pending,
            )
        
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
        
        # Generate CSV in memory
        csv_buffer = io.StringIO()
        
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
        
        # Fetch contacts and write to CSV
        writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
        writer.writeheader()
        
        for contact_uuid in contact_uuids:
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
                
                writer.writerow(row)
                
            except Exception as exc:
                logger.exception(
                    "Failed to process contact for export: contact_uuid=%s error=%s",
                    contact_uuid,
                    str(exc),
                )
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
                logger.debug("CSV uploaded to S3: key=%s", s3_key)
                return s3_key
            except Exception as exc:
                logger.exception("Failed to upload CSV to S3: export_id=%s", export_id)
                # Fallback to local storage
                exports_dir = Path(settings.UPLOAD_DIR) / "exports"
                exports_dir.mkdir(parents=True, exist_ok=True)
                file_path = exports_dir / f"{export_id}.csv"
                with file_path.open("wb") as f:
                    f.write(csv_content)
                logger.debug("CSV saved locally (S3 upload failed): file_path=%s", file_path)
                return str(file_path)
        else:
            # Save locally
            exports_dir = Path(settings.UPLOAD_DIR) / "exports"
            exports_dir.mkdir(parents=True, exist_ok=True)
            file_path = exports_dir / f"{export_id}.csv"
            with file_path.open("wb") as f:
                f.write(csv_content)
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

    async def list_user_exports(
        self,
        session: AsyncSession,
        user_id: str,
    ) -> Sequence[UserExport]:
        """List all exports for a user, ordered by created_at descending."""
        logger.debug("Listing exports for user: user_id=%s", user_id)
        
        stmt = (
            select(UserExport)
            .where(UserExport.user_id == user_id)
            .order_by(UserExport.created_at.desc())
        )
        result = await session.execute(stmt)
        exports = result.scalars().all()
        
        logger.debug("Found %d exports for user: user_id=%s", len(exports), user_id)
        return exports

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

