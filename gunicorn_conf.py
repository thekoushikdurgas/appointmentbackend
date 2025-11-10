"""Gunicorn configuration for running the Appointment360 FastAPI backend."""

from __future__ import annotations

import multiprocessing
import os
from typing import Any

from app.core.config import get_settings


settings = get_settings()


def _env_int(name: str, default: int) -> int:
    """Return an integer environment variable value with a sensible default."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError:
        return default


def _env_str(name: str, default: str) -> str:
    """Return a string environment variable value with a fallback."""
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default
    return raw_value


def _default_worker_count() -> int:
    """Return the default worker count based on CPU availability."""
    cpu_count = multiprocessing.cpu_count() or 1
    return (cpu_count * 2) + 1


bind: str | list[str] = _env_str("GUNICORN_BIND", "0.0.0.0:8000")
worker_class: str = _env_str(
    "GUNICORN_WORKER_CLASS", "uvicorn.workers.UvicornWorker"
)
workers: int = _env_int("GUNICORN_WORKERS", _default_worker_count())
threads: int = _env_int("GUNICORN_THREADS", 1)
timeout: int = _env_int("GUNICORN_TIMEOUT", 30)
graceful_timeout: int = _env_int("GUNICORN_GRACEFUL_TIMEOUT", 30)
keepalive: int = _env_int("GUNICORN_KEEPALIVE", 5)
max_requests: int = _env_int("GUNICORN_MAX_REQUESTS", 0)
max_requests_jitter: int = _env_int("GUNICORN_MAX_REQUESTS_JITTER", 0)

accesslog: str = _env_str("GUNICORN_ACCESSLOG", "-")
errorlog: str = _env_str("GUNICORN_ERRORLOG", "-")
loglevel: str = _env_str("GUNICORN_LOGLEVEL", settings.LOG_LEVEL.lower())
capture_output: bool = True

forwarded_allow_ips: str = _env_str("FORWARDED_ALLOW_IPS", "*")
proxy_allow_ips: str = forwarded_allow_ips
proxy_protocol: bool = os.getenv("PROXY_PROTOCOL", "0") in {"1", "true", "True"}

proc_name: str = _env_str(
    "GUNICORN_PROC_NAME", settings.PROJECT_NAME.replace(" ", "-")
)

# Enable hot reload for local development, but keep it off in production.
reload: bool = settings.DEBUG

# Provide a richer access log format that includes response time.
access_log_format: str = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s '
    '"%(f)s" "%(a)s" %(L)s'
)

# Configure the Uvicorn worker to trust proxy headers supplied by Nginx.
def post_fork(server: Any, worker: Any) -> None:
    """Hook executed in each worker after fork to log startup context."""
    server.log.info(
        "Worker spawned pid=%s bind=%s workers=%s threads=%s",
        worker.pid,
        bind,
        workers,
        threads,
    )

