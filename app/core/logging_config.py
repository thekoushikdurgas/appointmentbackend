"""Centralized logging configuration for the application."""

import json
import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict

from app.core.config import get_settings

settings = get_settings()


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs logs in JSON format."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["error"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else "Exception",
                "message": str(record.exc_info[1]) if record.exc_info[1] else "",
                "stack_trace": self.formatException(record.exc_info),
            }

        # Add extra context if present
        if hasattr(record, "context"):
            log_data["context"] = record.context

        # Add performance metrics if present
        if hasattr(record, "performance"):
            log_data["performance"] = record.performance

        # Add request ID if present
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id

        # Add user ID if present
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id

        # Add any other extra fields
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
                "context",
                "performance",
                "request_id",
                "user_id",
            ]:
                if not key.startswith("_"):
                    log_data[key] = value

        return json.dumps(log_data, default=str)


class TextFormatter(logging.Formatter):
    """Custom formatter that outputs logs in human-readable text format."""

    def __init__(self):
        """Initialize the formatter with a detailed format."""
        super().__init__(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with additional context."""
        formatted = super().format(record)

        # Add exception info if present
        if record.exc_info:
            formatted += "\n" + self.formatException(record.exc_info)

        # Add extra context if present
        if hasattr(record, "context") and record.context:
            formatted += f" | Context: {json.dumps(record.context, default=str)}"

        # Add performance metrics if present
        if hasattr(record, "performance") and record.performance:
            formatted += f" | Performance: {json.dumps(record.performance, default=str)}"

        # Add request ID if present
        if hasattr(record, "request_id"):
            formatted += f" | Request ID: {record.request_id}"

        # Add user ID if present
        if hasattr(record, "user_id"):
            formatted += f" | User ID: {record.user_id}"

        return formatted


def setup_logging() -> None:
    """Configure application-wide logging with file rotation and structured output."""
    # Get log level from settings
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Create logs directory if it doesn't exist
    log_file_path = Path(settings.LOG_FILE_PATH)
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    # Choose formatter based on settings
    if settings.LOG_FORMAT.lower() == "json":
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter()

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=settings.LOG_MAX_BYTES,
        backupCount=settings.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Console handler (optional)
    if settings.LOG_TO_CONSOLE:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # Set specific log levels for noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

    # Log that logging has been configured
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured",
        extra={
            "context": {
                "log_level": settings.LOG_LEVEL,
                "log_file": str(log_file_path),
                "log_format": settings.LOG_FORMAT,
                "log_to_console": settings.LOG_TO_CONSOLE,
            }
        },
    )

