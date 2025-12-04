"""Data pipeline endpoints for v3 API."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.logging import get_logger, log_function_call
from app.db.session import get_db
from app.models.user import User
from app.schemas.v3.data_pipeline import (
    AnalysisRequest,
    AnalysisResponse as DataPipelineAnalysisResponse,
    CleaningRequest,
    CleaningResponse,
    IngestionRequest,
    IngestionResponse,
)
from app.services.data_pipeline_service import data_pipeline_service

router = APIRouter(prefix="/data-pipeline", tags=["Data Pipeline"])
logger = get_logger(__name__)


@router.post("/ingest/companies/local", response_model=IngestionResponse, status_code=status.HTTP_202_ACCEPTED)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
async def ingest_companies_from_local(
    request: IngestionRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> IngestionResponse:
    """
    Trigger company ingestion from a local CSV file.
    
    Args:
        request: Ingestion request with file_path, batch_size, max_threads
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        Ingestion response with job_id and status
    """
    logger.info(
        "POST /v3/data-pipeline/ingest/companies/local request received: file_path=%s user_id=%s",
        request.file_path,
        current_user.uuid,
    )

    if not request.file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="file_path is required for local ingestion",
        )

    try:
        result = await data_pipeline_service.ingest_companies_from_local(
            file_path=request.file_path,
            batch_size=request.batch_size,
            max_threads=request.max_threads,
        )

        return IngestionResponse(
            job_id=result["job_id"],
            status=result["status"],
            message=result["message"],
            error_count=0,
        )
    except Exception as e:
        logger.error(
            "Error triggering company ingestion: file_path=%s error=%s",
            request.file_path,
            str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger company ingestion: {str(e)}",
        ) from e


@router.post("/ingest/companies/s3", response_model=IngestionResponse, status_code=status.HTTP_202_ACCEPTED)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
async def ingest_companies_from_s3(
    request: IngestionRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> IngestionResponse:
    """
    Trigger company ingestion from an S3 CSV object.
    
    Args:
        request: Ingestion request with object_key, batch_size, max_threads
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        Ingestion response with job_id and status
    """
    logger.info(
        "POST /v3/data-pipeline/ingest/companies/s3 request received: object_key=%s user_id=%s",
        request.object_key,
        current_user.uuid,
    )

    if not request.object_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="object_key is required for S3 ingestion",
        )

    try:
        result = await data_pipeline_service.ingest_companies_from_s3(
            object_key=request.object_key,
            batch_size=request.batch_size,
            max_threads=request.max_threads,
        )

        return IngestionResponse(
            job_id=result["job_id"],
            status=result["status"],
            message=result["message"],
            error_count=0,
        )
    except Exception as e:
        logger.error(
            "Error triggering company ingestion from S3: object_key=%s error=%s",
            request.object_key,
            str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger company ingestion from S3: {str(e)}",
        ) from e


@router.post("/ingest/contacts/local", response_model=IngestionResponse, status_code=status.HTTP_202_ACCEPTED)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
async def ingest_contacts_from_local(
    request: IngestionRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> IngestionResponse:
    """
    Trigger contact ingestion from a local CSV file.
    
    Args:
        request: Ingestion request with file_path, batch_size, max_threads
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        Ingestion response with job_id and status
    """
    logger.info(
        "POST /v3/data-pipeline/ingest/contacts/local request received: file_path=%s user_id=%s",
        request.file_path,
        current_user.uuid,
    )

    if not request.file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="file_path is required for local ingestion",
        )

    try:
        result = await data_pipeline_service.ingest_contacts_from_local(
            file_path=request.file_path,
            batch_size=request.batch_size,
            max_threads=request.max_threads,
        )

        return IngestionResponse(
            job_id=result["job_id"],
            status=result["status"],
            message=result["message"],
            error_count=0,
        )
    except Exception as e:
        logger.error(
            "Error triggering contact ingestion: file_path=%s error=%s",
            request.file_path,
            str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger contact ingestion: {str(e)}",
        ) from e


@router.post("/ingest/contacts/s3", response_model=IngestionResponse, status_code=status.HTTP_202_ACCEPTED)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
async def ingest_contacts_from_s3(
    request: IngestionRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> IngestionResponse:
    """
    Trigger contact ingestion from an S3 CSV object.
    
    Args:
        request: Ingestion request with object_key, batch_size, max_threads
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        Ingestion response with job_id and status
    """
    logger.info(
        "POST /v3/data-pipeline/ingest/contacts/s3 request received: object_key=%s user_id=%s",
        request.object_key,
        current_user.uuid,
    )

    if not request.object_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="object_key is required for S3 ingestion",
        )

    try:
        result = await data_pipeline_service.ingest_contacts_from_s3(
            object_key=request.object_key,
            batch_size=request.batch_size,
            max_threads=request.max_threads,
        )

        return IngestionResponse(
            job_id=result["job_id"],
            status=result["status"],
            message=result["message"],
            error_count=0,
        )
    except Exception as e:
        logger.error(
            "Error triggering contact ingestion from S3: object_key=%s error=%s",
            request.object_key,
            str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger contact ingestion from S3: {str(e)}",
        ) from e


@router.post(
    "/ingest/email-patterns/local",
    response_model=IngestionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
async def ingest_email_patterns_from_local(
    request: IngestionRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> IngestionResponse:
    """
    Trigger email pattern ingestion from a local CSV file.
    
    Args:
        request: Ingestion request with file_path, batch_size, max_threads
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        Ingestion response with job_id and status
    """
    logger.info(
        "POST /v3/data-pipeline/ingest/email-patterns/local request received: file_path=%s user_id=%s",
        request.file_path,
        current_user.uuid,
    )

    if not request.file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="file_path is required for local ingestion",
        )

    try:
        result = await data_pipeline_service.ingest_email_patterns_from_local(
            file_path=request.file_path,
            batch_size=request.batch_size,
            max_threads=request.max_threads,
        )

        return IngestionResponse(
            job_id=result["job_id"],
            status=result["status"],
            message=result["message"],
            error_count=0,
        )
    except Exception as e:
        logger.error(
            "Error triggering email pattern ingestion: file_path=%s error=%s",
            request.file_path,
            str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger email pattern ingestion: {str(e)}",
        ) from e


@router.post("/clean/database", response_model=CleaningResponse, status_code=status.HTTP_202_ACCEPTED)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
async def clean_database(
    request: CleaningRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CleaningResponse:
    """
    Trigger full database cleaning.
    
    Args:
        request: Cleaning request with batch_size and table_filter
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        Cleaning response with job_id and status
    """
    logger.info(
        "POST /v3/data-pipeline/clean/database request received: table_filter=%s user_id=%s",
        request.table_filter,
        current_user.uuid,
    )

    try:
        result = await data_pipeline_service.clean_database(
            batch_size=request.batch_size,
            table_filter=request.table_filter or "all",
        )

        return CleaningResponse(
            job_id=result["job_id"],
            status=result["status"],
            processed=0,
            updated=0,
            errors=0,
            invalid_names=0,
            message=result["message"],
        )
    except Exception as e:
        logger.error(
            "Error triggering database cleaning: error=%s",
            str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger database cleaning: {str(e)}",
        ) from e


@router.post("/clean/companies", response_model=CleaningResponse, status_code=status.HTTP_202_ACCEPTED)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
async def clean_companies(
    request: CleaningRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CleaningResponse:
    """
    Clean companies table only.
    
    Args:
        request: Cleaning request with batch_size
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        Cleaning response with job_id and status
    """
    logger.info(
        "POST /v3/data-pipeline/clean/companies request received: user_id=%s",
        current_user.uuid,
    )

    try:
        result = await data_pipeline_service.clean_database(
            batch_size=request.batch_size,
            table_filter="companies",
        )

        return CleaningResponse(
            job_id=result["job_id"],
            status=result["status"],
            processed=0,
            updated=0,
            errors=0,
            invalid_names=0,
            message=result["message"],
        )
    except Exception as e:
        logger.error(
            "Error triggering companies cleaning: error=%s",
            str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger companies cleaning: {str(e)}",
        ) from e


@router.post("/clean/contacts", response_model=CleaningResponse, status_code=status.HTTP_202_ACCEPTED)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
async def clean_contacts(
    request: CleaningRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CleaningResponse:
    """
    Clean contacts table only.
    
    Args:
        request: Cleaning request with batch_size
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        Cleaning response with job_id and status
    """
    logger.info(
        "POST /v3/data-pipeline/clean/contacts request received: user_id=%s",
        current_user.uuid,
    )

    try:
        result = await data_pipeline_service.clean_database(
            batch_size=request.batch_size,
            table_filter="contacts",
        )

        return CleaningResponse(
            job_id=result["job_id"],
            status=result["status"],
            processed=0,
            updated=0,
            errors=0,
            invalid_names=0,
            message=result["message"],
        )
    except Exception as e:
        logger.error(
            "Error triggering contacts cleaning: error=%s",
            str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger contacts cleaning: {str(e)}",
        ) from e


@router.post(
    "/analyze/company-names",
    response_model=DataPipelineAnalysisResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
async def analyze_company_names(
    request: AnalysisRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DataPipelineAnalysisResponse:
    """
    Run company name analysis.
    
    Args:
        request: Analysis request with batch_size
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        Analysis response with job_id and status
    """
    logger.info(
        "POST /v3/data-pipeline/analyze/company-names request received: user_id=%s",
        current_user.uuid,
    )

    try:
        result = await data_pipeline_service.analyze_company_names(
            batch_size=request.batch_size,
        )

        return DataPipelineAnalysisResponse(
            job_id=result["job_id"],
            status=result["status"],
            report_path=None,
            json_report_path=None,
            statistics=None,
            timestamp=datetime.now().isoformat(),
            message=result["message"],
        )
    except Exception as e:
        logger.error(
            "Error triggering company name analysis: error=%s",
            str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger company name analysis: {str(e)}",
        ) from e


@router.post(
    "/analyze/comprehensive",
    response_model=DataPipelineAnalysisResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
async def analyze_comprehensive(
    request: AnalysisRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DataPipelineAnalysisResponse:
    """
    Run comprehensive data analysis.
    
    Args:
        request: Analysis request with batch_size
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        Analysis response with job_id and status
    """
    logger.info(
        "POST /v3/data-pipeline/analyze/comprehensive request received: user_id=%s",
        current_user.uuid,
    )

    try:
        result = await data_pipeline_service.analyze_comprehensive(
            batch_size=request.batch_size,
        )

        return DataPipelineAnalysisResponse(
            job_id=result["job_id"],
            status=result["status"],
            report_path=None,
            json_report_path=None,
            statistics=None,
            timestamp=datetime.now().isoformat(),
            message=result["message"],
        )
    except Exception as e:
        logger.error(
            "Error triggering comprehensive analysis: error=%s",
            str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger comprehensive analysis: {str(e)}",
        ) from e


@router.get("/job/{job_id}", response_model=dict)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
async def get_job_status(
    job_id: str = Path(..., description="Job identifier"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get the status of a data pipeline job.
    
    Args:
        job_id: Job identifier
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        Dictionary with job status and details
    """
    logger.info(
        "GET /v3/data-pipeline/job/%s request received: user_id=%s",
        job_id,
        current_user.uuid,
    )

    job_status = data_pipeline_service.get_job_status(job_id)

    if job_status is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found",
        )

    return job_status

