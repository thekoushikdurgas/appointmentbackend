"""Service for data pipeline operations (ingestion, cleaning, analysis)."""

import asyncio
import os
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

# Add scripts/data to path
_SCRIPTS_DATA_PATH = Path(__file__).parent.parent.parent.parent / "scripts" / "data"
if str(_SCRIPTS_DATA_PATH) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DATA_PATH))

# Thread pool for running synchronous CLI operations
_executor = ThreadPoolExecutor(max_workers=3)


class DataPipelineService:
    """Service for data pipeline operations."""

    def __init__(self):
        """Initialize data pipeline service."""
        self._jobs: Dict[str, Dict] = {}

    def _generate_job_id(self) -> str:
        """Generate a unique job ID."""
        return str(uuid.uuid4())

    async def _run_sync_in_executor(self, func, *args, **kwargs):
        """Run a synchronous function in a thread pool executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, func, *args, **kwargs)

    async def ingest_companies_from_local(
        self, file_path: str, batch_size: int = 1000, max_threads: int = 3
    ) -> Dict:
        """
        Ingest companies from a local CSV file.
        
        Args:
            file_path: Path to the CSV file
            batch_size: Number of rows to process per batch
            max_threads: Maximum number of concurrent threads
            
        Returns:
            Dictionary with job_id, status, message, error_count, etc.
        """
        job_id = self._generate_job_id()
        self._jobs[job_id] = {
            "status": "queued",
            "message": "Job queued",
            "created_at": datetime.now().isoformat(),
        }

        async def _run_ingestion():
            try:
                self._jobs[job_id]["status"] = "running"
                self._jobs[job_id]["message"] = "Starting company ingestion..."

                # Import ingestion function
                from ingestion.local.company import ingest_companies_from_local

                # Get error log info before
                from utils import ingest_utils

                before_path, before_count = ingest_utils.get_error_log_info()

                # Run ingestion
                await self._run_sync_in_executor(
                    ingest_companies_from_local, file_path, batch_size, max_threads
                )

                # Get error log info after
                after_path, after_count = ingest_utils.get_error_log_info()
                error_count = after_count - (before_count or 0)

                self._jobs[job_id]["status"] = "completed"
                self._jobs[job_id]["message"] = f"Successfully ingested companies from {file_path}"
                self._jobs[job_id]["error_count"] = error_count
                self._jobs[job_id]["error_log_path"] = after_path if error_count > 0 else None
                self._jobs[job_id]["completed_at"] = datetime.now().isoformat()

            except Exception as e:
                logger.error(f"Error ingesting companies: {str(e)}", exc_info=True)
                self._jobs[job_id]["status"] = "failed"
                self._jobs[job_id]["message"] = f"Failed to ingest companies: {str(e)}"
                self._jobs[job_id]["error"] = str(e)
                self._jobs[job_id]["completed_at"] = datetime.now().isoformat()

        # Start ingestion in background
        asyncio.create_task(_run_ingestion())

        return {
            "job_id": job_id,
            "status": "queued",
            "message": "Job queued for execution",
        }

    async def ingest_companies_from_s3(
        self, object_key: str, batch_size: int = 1000, max_threads: int = 3
    ) -> Dict:
        """
        Ingest companies from an S3 CSV object.
        
        Args:
            object_key: S3 object key (path to CSV file)
            batch_size: Number of rows to process per batch
            max_threads: Maximum number of concurrent threads
            
        Returns:
            Dictionary with job_id, status, message, error_count, etc.
        """
        job_id = self._generate_job_id()
        self._jobs[job_id] = {
            "status": "queued",
            "message": "Job queued",
            "created_at": datetime.now().isoformat(),
        }

        async def _run_ingestion():
            try:
                self._jobs[job_id]["status"] = "running"
                self._jobs[job_id]["message"] = "Starting company ingestion from S3..."

                from ingestion.s3.company import ingest_companies_from_s3
                from utils import ingest_utils

                before_path, before_count = ingest_utils.get_error_log_info()

                await self._run_sync_in_executor(
                    ingest_companies_from_s3, batch_size, max_threads, object_key
                )

                after_path, after_count = ingest_utils.get_error_log_info()
                error_count = after_count - (before_count or 0)

                self._jobs[job_id]["status"] = "completed"
                self._jobs[job_id]["message"] = f"Successfully ingested companies from S3: {object_key}"
                self._jobs[job_id]["error_count"] = error_count
                self._jobs[job_id]["error_log_path"] = after_path if error_count > 0 else None
                self._jobs[job_id]["completed_at"] = datetime.now().isoformat()

            except Exception as e:
                logger.error(f"Error ingesting companies from S3: {str(e)}", exc_info=True)
                self._jobs[job_id]["status"] = "failed"
                self._jobs[job_id]["message"] = f"Failed to ingest companies from S3: {str(e)}"
                self._jobs[job_id]["error"] = str(e)
                self._jobs[job_id]["completed_at"] = datetime.now().isoformat()

        asyncio.create_task(_run_ingestion())

        return {
            "job_id": job_id,
            "status": "queued",
            "message": "Job queued for execution",
        }

    async def ingest_contacts_from_local(
        self, file_path: str, batch_size: int = 1000, max_threads: int = 3
    ) -> Dict:
        """
        Ingest contacts from a local CSV file.
        
        Args:
            file_path: Path to the CSV file
            batch_size: Number of rows to process per batch
            max_threads: Maximum number of concurrent threads
            
        Returns:
            Dictionary with job_id, status, message, error_count, etc.
        """
        job_id = self._generate_job_id()
        self._jobs[job_id] = {
            "status": "queued",
            "message": "Job queued",
            "created_at": datetime.now().isoformat(),
        }

        async def _run_ingestion():
            try:
                self._jobs[job_id]["status"] = "running"
                self._jobs[job_id]["message"] = "Starting contact ingestion..."

                from ingestion.local.contact import ingest_contacts_from_local
                from utils import ingest_utils

                before_path, before_count = ingest_utils.get_error_log_info()

                await self._run_sync_in_executor(
                    ingest_contacts_from_local, file_path, batch_size, max_threads
                )

                after_path, after_count = ingest_utils.get_error_log_info()
                error_count = after_count - (before_count or 0)

                self._jobs[job_id]["status"] = "completed"
                self._jobs[job_id]["message"] = f"Successfully ingested contacts from {file_path}"
                self._jobs[job_id]["error_count"] = error_count
                self._jobs[job_id]["error_log_path"] = after_path if error_count > 0 else None
                self._jobs[job_id]["completed_at"] = datetime.now().isoformat()

            except Exception as e:
                logger.error(f"Error ingesting contacts: {str(e)}", exc_info=True)
                self._jobs[job_id]["status"] = "failed"
                self._jobs[job_id]["message"] = f"Failed to ingest contacts: {str(e)}"
                self._jobs[job_id]["error"] = str(e)
                self._jobs[job_id]["completed_at"] = datetime.now().isoformat()

        asyncio.create_task(_run_ingestion())

        return {
            "job_id": job_id,
            "status": "queued",
            "message": "Job queued for execution",
        }

    async def ingest_contacts_from_s3(
        self, object_key: str, batch_size: int = 1000, max_threads: int = 3
    ) -> Dict:
        """
        Ingest contacts from an S3 CSV object.
        
        Args:
            object_key: S3 object key (path to CSV file)
            batch_size: Number of rows to process per batch
            max_threads: Maximum number of concurrent threads
            
        Returns:
            Dictionary with job_id, status, message, error_count, etc.
        """
        job_id = self._generate_job_id()
        self._jobs[job_id] = {
            "status": "queued",
            "message": "Job queued",
            "created_at": datetime.now().isoformat(),
        }

        async def _run_ingestion():
            try:
                self._jobs[job_id]["status"] = "running"
                self._jobs[job_id]["message"] = "Starting contact ingestion from S3..."

                from ingestion.s3.contact import ingest_contacts_from_s3
                from utils import ingest_utils

                before_path, before_count = ingest_utils.get_error_log_info()

                await self._run_sync_in_executor(
                    ingest_contacts_from_s3, batch_size, max_threads, object_key
                )

                after_path, after_count = ingest_utils.get_error_log_info()
                error_count = after_count - (before_count or 0)

                self._jobs[job_id]["status"] = "completed"
                self._jobs[job_id]["message"] = f"Successfully ingested contacts from S3: {object_key}"
                self._jobs[job_id]["error_count"] = error_count
                self._jobs[job_id]["error_log_path"] = after_path if error_count > 0 else None
                self._jobs[job_id]["completed_at"] = datetime.now().isoformat()

            except Exception as e:
                logger.error(f"Error ingesting contacts from S3: {str(e)}", exc_info=True)
                self._jobs[job_id]["status"] = "failed"
                self._jobs[job_id]["message"] = f"Failed to ingest contacts from S3: {str(e)}"
                self._jobs[job_id]["error"] = str(e)
                self._jobs[job_id]["completed_at"] = datetime.now().isoformat()

        asyncio.create_task(_run_ingestion())

        return {
            "job_id": job_id,
            "status": "queued",
            "message": "Job queued for execution",
        }

    async def ingest_email_patterns_from_local(
        self, file_path: str, batch_size: int = 1000, max_threads: int = 3
    ) -> Dict:
        """
        Ingest email patterns from a local CSV file.
        
        Args:
            file_path: Path to the CSV file
            batch_size: Number of rows to process per batch
            max_threads: Maximum number of concurrent threads
            
        Returns:
            Dictionary with job_id, status, message, error_count, etc.
        """
        job_id = self._generate_job_id()
        self._jobs[job_id] = {
            "status": "queued",
            "message": "Job queued",
            "created_at": datetime.now().isoformat(),
        }

        async def _run_ingestion():
            try:
                self._jobs[job_id]["status"] = "running"
                self._jobs[job_id]["message"] = "Starting email pattern ingestion..."

                from ingestion.local.email_pattern import ingest_email_patterns_from_local
                from utils import ingest_utils

                before_path, before_count = ingest_utils.get_error_log_info()

                await self._run_sync_in_executor(
                    ingest_email_patterns_from_local, file_path, batch_size, max_threads
                )

                after_path, after_count = ingest_utils.get_error_log_info()
                error_count = after_count - (before_count or 0)

                self._jobs[job_id]["status"] = "completed"
                self._jobs[job_id]["message"] = f"Successfully ingested email patterns from {file_path}"
                self._jobs[job_id]["error_count"] = error_count
                self._jobs[job_id]["error_log_path"] = after_path if error_count > 0 else None
                self._jobs[job_id]["completed_at"] = datetime.now().isoformat()

            except Exception as e:
                logger.error(f"Error ingesting email patterns: {str(e)}", exc_info=True)
                self._jobs[job_id]["status"] = "failed"
                self._jobs[job_id]["message"] = f"Failed to ingest email patterns: {str(e)}"
                self._jobs[job_id]["error"] = str(e)
                self._jobs[job_id]["completed_at"] = datetime.now().isoformat()

        asyncio.create_task(_run_ingestion())

        return {
            "job_id": job_id,
            "status": "queued",
            "message": "Job queued for execution",
        }

    async def clean_database(
        self, batch_size: int = 1000, table_filter: str = "all"
    ) -> Dict:
        """
        Clean the database.
        
        Args:
            batch_size: Number of rows to process per batch
            table_filter: Which tables to clean ("companies", "contacts", or "all")
            
        Returns:
            Dictionary with job_id, status, processed, updated, errors, etc.
        """
        job_id = self._generate_job_id()
        self._jobs[job_id] = {
            "status": "queued",
            "message": "Job queued",
            "created_at": datetime.now().isoformat(),
        }

        async def _run_cleaning():
            try:
                self._jobs[job_id]["status"] = "running"
                self._jobs[job_id]["message"] = "Starting database cleaning..."

                from cleaning.clean_database import (
                    clean_companies,
                    clean_contacts,
                    clean_companies_metadata,
                    clean_contacts_metadata,
                )

                total_processed = 0
                total_updated = 0
                total_errors = 0
                total_invalid_names = 0

                if table_filter in ("all", "companies"):
                    stats = await self._run_sync_in_executor(clean_companies, batch_size)
                    total_processed += stats.get("processed", 0)
                    total_updated += stats.get("updated", 0)
                    total_errors += stats.get("errors", 0)
                    total_invalid_names += stats.get("invalid_names", 0)

                if table_filter in ("all", "companies"):
                    stats = await self._run_sync_in_executor(
                        clean_companies_metadata, batch_size
                    )
                    total_processed += stats.get("processed", 0)
                    total_updated += stats.get("updated", 0)
                    total_errors += stats.get("errors", 0)

                if table_filter in ("all", "contacts"):
                    stats = await self._run_sync_in_executor(clean_contacts, batch_size)
                    total_processed += stats.get("processed", 0)
                    total_updated += stats.get("updated", 0)
                    total_errors += stats.get("errors", 0)

                if table_filter in ("all", "contacts"):
                    stats = await self._run_sync_in_executor(
                        clean_contacts_metadata, batch_size
                    )
                    total_processed += stats.get("processed", 0)
                    total_updated += stats.get("updated", 0)
                    total_errors += stats.get("errors", 0)

                self._jobs[job_id]["status"] = "completed"
                self._jobs[job_id]["message"] = "Database cleaning completed successfully"
                self._jobs[job_id]["processed"] = total_processed
                self._jobs[job_id]["updated"] = total_updated
                self._jobs[job_id]["errors"] = total_errors
                self._jobs[job_id]["invalid_names"] = total_invalid_names
                self._jobs[job_id]["completed_at"] = datetime.now().isoformat()

            except Exception as e:
                logger.error(f"Error cleaning database: {str(e)}", exc_info=True)
                self._jobs[job_id]["status"] = "failed"
                self._jobs[job_id]["message"] = f"Failed to clean database: {str(e)}"
                self._jobs[job_id]["error"] = str(e)
                self._jobs[job_id]["completed_at"] = datetime.now().isoformat()

        asyncio.create_task(_run_cleaning())

        return {
            "job_id": job_id,
            "status": "queued",
            "message": "Job queued for execution",
        }

    async def analyze_company_names(self, batch_size: int = 1000) -> Dict:
        """
        Run company name analysis.
        
        Args:
            batch_size: Number of rows to process per batch
            
        Returns:
            Dictionary with job_id, status, report_path, statistics, etc.
        """
        job_id = self._generate_job_id()
        self._jobs[job_id] = {
            "status": "queued",
            "message": "Job queued",
            "created_at": datetime.now().isoformat(),
        }

        async def _run_analysis():
            try:
                self._jobs[job_id]["status"] = "running"
                self._jobs[job_id]["message"] = "Starting company name analysis..."

                from analysis.analyze_company_names import categorize_company_names, generate_report

                categories = await self._run_sync_in_executor(
                    categorize_company_names, batch_size
                )

                # Generate report
                report_dir = _SCRIPTS_DATA_PATH / "analysis"
                await self._run_sync_in_executor(generate_report, categories, str(report_dir))

                # Find the generated report file
                report_files = sorted(
                    report_dir.glob("company_name_analysis_*.txt"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
                csv_files = sorted(
                    report_dir.glob("company_name_analysis_*.csv"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )

                report_path = str(report_files[0]) if report_files else None
                csv_path = str(csv_files[0]) if csv_files else None

                # Calculate statistics
                total = sum(len(cat) for cat in categories.values())
                statistics = {
                    "total": total,
                    "valid": len(categories.get("valid", [])),
                    "invalid": len(categories.get("invalid", [])),
                    "needs_cleaning": len(categories.get("needs_cleaning", [])),
                    "null_or_empty": len(categories.get("null_or_empty", [])),
                }

                self._jobs[job_id]["status"] = "completed"
                self._jobs[job_id]["message"] = "Company name analysis completed successfully"
                self._jobs[job_id]["report_path"] = report_path
                self._jobs[job_id]["json_report_path"] = csv_path
                self._jobs[job_id]["statistics"] = statistics
                self._jobs[job_id]["timestamp"] = datetime.now().isoformat()
                self._jobs[job_id]["completed_at"] = datetime.now().isoformat()

            except Exception as e:
                logger.error(f"Error analyzing company names: {str(e)}", exc_info=True)
                self._jobs[job_id]["status"] = "failed"
                self._jobs[job_id]["message"] = f"Failed to analyze company names: {str(e)}"
                self._jobs[job_id]["error"] = str(e)
                self._jobs[job_id]["completed_at"] = datetime.now().isoformat()

        asyncio.create_task(_run_analysis())

        return {
            "job_id": job_id,
            "status": "queued",
            "message": "Job queued for execution",
        }

    async def analyze_comprehensive(self, batch_size: int = 1000) -> Dict:
        """
        Run comprehensive data analysis.
        
        Args:
            batch_size: Number of rows to process per batch
            
        Returns:
            Dictionary with job_id, status, report_path, statistics, etc.
        """
        job_id = self._generate_job_id()
        self._jobs[job_id] = {
            "status": "queued",
            "message": "Job queued",
            "created_at": datetime.now().isoformat(),
        }

        async def _run_analysis():
            try:
                self._jobs[job_id]["status"] = "running"
                self._jobs[job_id]["message"] = "Starting comprehensive data analysis..."

                from analysis.comprehensive_data_analysis import (
                    analyze_company_names,
                    analyze_keywords,
                    analyze_titles,
                    generate_comprehensive_report,
                )

                company_stats = await self._run_sync_in_executor(
                    analyze_company_names, batch_size
                )
                keyword_stats = await self._run_sync_in_executor(
                    analyze_keywords, batch_size
                )
                title_stats = await self._run_sync_in_executor(analyze_titles, batch_size)

                # Generate report
                report_dir = _SCRIPTS_DATA_PATH / "analysis"
                await self._run_sync_in_executor(
                    generate_comprehensive_report,
                    company_stats,
                    keyword_stats,
                    title_stats,
                    str(report_dir),
                )

                # Find the generated report files
                report_files = sorted(
                    report_dir.glob("comprehensive_data_analysis_*.txt"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
                json_files = sorted(
                    report_dir.glob("comprehensive_data_analysis_*.json"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )

                report_path = str(report_files[0]) if report_files else None
                json_path = str(json_files[0]) if json_files else None

                # Combine statistics
                statistics = {
                    "company_names": {
                        "total": company_stats.get("total", 0),
                        "valid": company_stats.get("valid", 0),
                        "invalid": company_stats.get("invalid", 0),
                        "needs_cleaning": company_stats.get("needs_cleaning", 0),
                        "null_or_empty": company_stats.get("null_or_empty", 0),
                    },
                    "keywords": {
                        "total_keywords": keyword_stats.get("total_keywords", 0),
                        "valid_keywords": keyword_stats.get("valid_keywords", 0),
                        "invalid_keywords": keyword_stats.get("invalid_keywords", 0),
                        "needs_cleaning": keyword_stats.get("needs_cleaning", 0),
                    },
                    "titles": {
                        "total_contacts": title_stats.get("total_contacts", 0),
                        "valid": title_stats.get("valid", 0),
                        "invalid": title_stats.get("invalid", 0),
                        "needs_cleaning": title_stats.get("needs_cleaning", 0),
                        "null_or_empty": title_stats.get("null_or_empty", 0),
                    },
                }

                self._jobs[job_id]["status"] = "completed"
                self._jobs[job_id]["message"] = "Comprehensive data analysis completed successfully"
                self._jobs[job_id]["report_path"] = report_path
                self._jobs[job_id]["json_report_path"] = json_path
                self._jobs[job_id]["statistics"] = statistics
                self._jobs[job_id]["timestamp"] = datetime.now().isoformat()
                self._jobs[job_id]["completed_at"] = datetime.now().isoformat()

            except Exception as e:
                logger.error(f"Error running comprehensive analysis: {str(e)}", exc_info=True)
                self._jobs[job_id]["status"] = "failed"
                self._jobs[job_id]["message"] = f"Failed to run comprehensive analysis: {str(e)}"
                self._jobs[job_id]["error"] = str(e)
                self._jobs[job_id]["completed_at"] = datetime.now().isoformat()

        asyncio.create_task(_run_analysis())

        return {
            "job_id": job_id,
            "status": "queued",
            "message": "Job queued for execution",
        }

    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """
        Get the status of a job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Dictionary with job status or None if job not found
        """
        return self._jobs.get(job_id)


# Global service instance
data_pipeline_service = DataPipelineService()

