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

# Enhanced Celery configuration for better performance
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Worker configuration
    worker_max_tasks_per_child=1000,
    worker_prefetch_multiplier=4,  # Prefetch tasks for better throughput
    worker_max_memory_per_child=200000,  # 200MB per child process
    # Task execution
    task_track_started=True,
    task_acks_late=True,  # Acknowledge tasks after completion for reliability
    task_reject_on_worker_lost=True,  # Reject tasks if worker dies
    # Concurrency
    worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,
    # Result backend
    result_expires=3600,  # Results expire after 1 hour
    result_backend_transport_options={
        "master_name": "mymaster",
        "visibility_timeout": 3600,
    },
    # Task routing and prioritization
    task_routes={
        "app.tasks.import_tasks.*": {"queue": "imports", "priority": 5},
        "app.tasks.export_tasks.*": {"queue": "exports", "priority": 4},
        "app.tasks.*": {"queue": "default", "priority": 3},
    },
    task_default_queue="default",
    task_default_exchange="tasks",
    task_default_exchange_type="direct",
    task_default_routing_key="default",
    # Task time limits
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    task_soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,
    # Optimization settings
    task_compression="gzip",  # Compress large task messages
    result_compression="gzip",  # Compress large result messages
    # Broker connection
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    # Task result caching
    result_cache_max=10000,  # Cache up to 10k results
)

# Configure task result expiration
celery_app.conf.task_result_expires = 3600  # 1 hour

# Auto-discover tasks
celery_app.autodiscover_tasks(["app.tasks"])
logger.info(
    "Configured Celery app: concurrency=%d queues=%s",
    settings.CELERY_WORKER_CONCURRENCY,
    ["default", "imports", "exports"],
)

