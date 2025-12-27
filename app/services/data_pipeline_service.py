"""Service for data pipeline operations (ingestion, cleaning, analysis)."""

# Data pipeline operations are no longer available
# The scripts/data directory dependencies have been removed
_DATA_PIPELINE_DISABLED = True

from app.utils.logger import get_logger

logger = get_logger(__name__)


class DataPipelineService:
    """Service for data pipeline operations."""

    def __init__(self):
        """Initialize data pipeline service."""
        pass



# Global service instance
data_pipeline_service = DataPipelineService()

