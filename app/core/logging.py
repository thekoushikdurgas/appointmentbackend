"""Centralized logging configuration and convenience utilities."""

from __future__ import annotations

import asyncio
import logging
import sys
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

_DEFAULT_MAX_ARG_LENGTH = 200


def setup_logging() -> None:
    """Configure project-wide logging handlers and default formatting."""
    from .config import get_settings

    settings = get_settings()
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format=settings.LOG_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / "app.log"),
        ],
    )

    # Tune noisy libraries
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a namespaced logger, defaulting to the application root."""
    return logging.getLogger(name or "app")


def _safe_repr(obj: Any, *, max_length: int = _DEFAULT_MAX_ARG_LENGTH) -> str:
    """Return a shortened representation of an object suitable for logging."""
    try:
        rendered = repr(obj)
    except Exception:  # pragma: no cover - defensive
        rendered = object.__repr__(obj)
    if len(rendered) > max_length:
        return f"{rendered[: max_length - 3]}..."
    return rendered


def log_function_call(
    *,
    logger: logging.Logger | None = None,
    entry_level: int = logging.DEBUG,
    exit_level: int = logging.DEBUG,
    log_arguments: bool = False,
    log_result: bool = False,
    max_repr_length: int = _DEFAULT_MAX_ARG_LENGTH,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator that logs entry, exit, and optional arguments/results for a callable.

    Args:
        logger: Explicit logger instance. Defaults to a logger derived from the wrapped
            function's module.
        entry_level: Logging level used when recording function entry.
        exit_level: Logging level used when recording function exit.
        log_arguments: When true, positional and keyword arguments are logged using
            ``repr`` (truncated to ``max_repr_length``).
        log_result: When true, the return value is logged using ``repr`` (truncated to
            ``max_repr_length``).
        max_repr_length: Maximum length (in characters) for argument/result rendering.

    Returns:
        Callable decorator that wraps the target function with logging statements.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        target_logger = logger or get_logger(func.__module__)
        qual_name = f"{func.__module__}.{func.__qualname__}"

        async def _async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            if log_arguments:
                target_logger.log(
                    entry_level,
                    "Entering %s args=%s kwargs=%s",
                    qual_name,
                    _safe_repr(args, max_length=max_repr_length),
                    _safe_repr(kwargs, max_length=max_repr_length),
                )
            else:
                target_logger.log(entry_level, "Entering %s", qual_name)

            try:
                result = await func(*args, **kwargs)  # type: ignore[misc]
            except Exception:
                target_logger.exception("Error in %s", qual_name)
                raise

            if log_result:
                target_logger.log(
                    exit_level,
                    "Exiting %s result=%s",
                    qual_name,
                    _safe_repr(result, max_length=max_repr_length),
                )
            else:
                target_logger.log(exit_level, "Exiting %s", qual_name)
            return result

        def _sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            if log_arguments:
                target_logger.log(
                    entry_level,
                    "Entering %s args=%s kwargs=%s",
                    qual_name,
                    _safe_repr(args, max_length=max_repr_length),
                    _safe_repr(kwargs, max_length=max_repr_length),
                )
            else:
                target_logger.log(entry_level, "Entering %s", qual_name)

            try:
                result = func(*args, **kwargs)
            except Exception:
                target_logger.exception("Error in %s", qual_name)
                raise

            if log_result:
                target_logger.log(
                    exit_level,
                    "Exiting %s result=%s",
                    qual_name,
                    _safe_repr(result, max_length=max_repr_length),
                )
            else:
                target_logger.log(exit_level, "Exiting %s", qual_name)
            return result

        wrapped: Callable[P, R]
        if asyncio.iscoroutinefunction(func):
            wrapped = wraps(func)(_async_wrapper)  # type: ignore[assignment]
        else:
            wrapped = wraps(func)(_sync_wrapper)
        return wrapped

    return decorator

