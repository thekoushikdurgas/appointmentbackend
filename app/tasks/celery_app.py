"""Celery application instance shared across background task modules."""

from celery import Celery

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

celery_app = Celery(
    "appointment360",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_max_tasks_per_child=1000,
    task_track_started=True,
)

# Auto-discover tasks
celery_app.autodiscover_tasks(["app.tasks"])
logger.debug("Configured Celery app for project tasks")

