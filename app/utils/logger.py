"""Logger utility functions and decorators for structured logging."""

import functools
import logging
import time
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.
    
    Args:
        name: Logger name, typically __name__ of the calling module
        
    Returns:
        Logger instance configured with application settings
    """
    return logging.getLogger(name)


def log_function_call(
    logger_name: Optional[str] = None,
    log_args: bool = False,
    log_result: bool = False,
    log_duration: bool = True,
) -> Callable:
    """Decorator to log function entry, exit, and duration.
    
    Args:
        logger_name: Optional logger name (defaults to function's module)
        log_args: Whether to log function arguments
        log_result: Whether to log function return value
        log_duration: Whether to log execution duration
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        log = logging.getLogger(logger_name or func.__module__)
        
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            func_name = f"{func.__module__}.{func.__name__}"
            
            # Log entry
            extra_context: Dict[str, Any] = {"function": func_name}
            if log_args:
                extra_context["args"] = str(args)
                extra_context["kwargs"] = str(kwargs)
            
            log.debug(
                f"Function {func_name} called",
                extra={"context": extra_context}
            )
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Log exit
                exit_context = {"function": func_name}
                if log_duration:
                    exit_context["duration_ms"] = duration * 1000
                if log_result:
                    exit_context["result"] = str(result)
                
                log.debug(
                    f"Function {func_name} completed",
                    extra={
                        "context": exit_context,
                        "performance": {"duration_ms": duration * 1000}
                    }
                )
                
                return result
            except Exception as exc:
                duration = time.time() - start_time
                log.error(
                    f"Function {func_name} failed",
                    exc_info=True,
                    extra={
                        "context": {
                            "function": func_name,
                            "error_type": type(exc).__name__,
                            "error_message": str(exc),
                        },
                        "performance": {"duration_ms": duration * 1000}
                    }
                )
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            func_name = f"{func.__module__}.{func.__name__}"
            
            # Log entry
            extra_context: Dict[str, Any] = {"function": func_name}
            if log_args:
                extra_context["args"] = str(args)
                extra_context["kwargs"] = str(kwargs)
            
            log.debug(
                f"Function {func_name} called",
                extra={"context": extra_context}
            )
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Log exit
                exit_context = {"function": func_name}
                if log_duration:
                    exit_context["duration_ms"] = duration * 1000
                if log_result:
                    exit_context["result"] = str(result)
                
                log.debug(
                    f"Function {func_name} completed",
                    extra={
                        "context": exit_context,
                        "performance": {"duration_ms": duration * 1000}
                    }
                )
                
                return result
            except Exception as exc:
                duration = time.time() - start_time
                log.error(
                    f"Function {func_name} failed",
                    exc_info=True,
                    extra={
                        "context": {
                            "function": func_name,
                            "error_type": type(exc).__name__,
                            "error_message": str(exc),
                        },
                        "performance": {"duration_ms": duration * 1000}
                    }
                )
                raise
        
        # Return appropriate wrapper based on whether function is async
        if functools.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def log_database_operation(
    operation: str,
    table: Optional[str] = None,
    duration_ms: Optional[float] = None,
    **kwargs: Any
) -> None:
    """Log a database operation with context.
    
    Args:
        operation: Operation type (SELECT, INSERT, UPDATE, DELETE, etc.)
        table: Table name
        duration_ms: Operation duration in milliseconds
        **kwargs: Additional context to include in log
    """
    log = logging.getLogger("app.db")
    context: Dict[str, Any] = {
        "operation": operation,
    }
    if table:
        context["table"] = table
    if kwargs:
        context.update(kwargs)
    
    extra: Dict[str, Any] = {"context": context}
    if duration_ms is not None:
        extra["performance"] = {"duration_ms": duration_ms}
        if duration_ms > 1000:
            log.warning(f"Slow database operation: {operation}", extra=extra)
        else:
            log.debug(f"Database operation: {operation}", extra=extra)
    else:
        log.debug(f"Database operation: {operation}", extra=extra)


def log_api_request(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    user_id: Optional[str] = None,
    request_id: Optional[str] = None,
    **kwargs: Any
) -> None:
    """Log an API request with context.
    
    Args:
        method: HTTP method
        path: Request path
        status_code: Response status code
        duration_ms: Request duration in milliseconds
        user_id: Optional user ID
        request_id: Optional request ID
        **kwargs: Additional context
    """
    log = logging.getLogger("app.api")
    context: Dict[str, Any] = {
        "method": method,
        "path": path,
        "status_code": status_code,
    }
    if user_id:
        context["user_id"] = user_id
    if request_id:
        context["request_id"] = request_id
    if kwargs:
        context.update(kwargs)
    
    # Optimize logging: Only log slow or failed requests as INFO/WARNING/ERROR
    # Fast successful requests (200-299, <1s) are logged as DEBUG to reduce noise
    if status_code >= 500:
        level = logging.ERROR
    elif status_code >= 400:
        level = logging.WARNING
    elif duration_ms > 1000.0:  # Slow successful requests
        level = logging.INFO
    else:
        # Fast successful requests - log as DEBUG to reduce noise
        level = logging.DEBUG
    
    extra: Dict[str, Any] = {
        "context": context,
        "performance": {"duration_ms": duration_ms},
    }
    if user_id:
        extra["user_id"] = user_id
    if request_id:
        extra["request_id"] = request_id
    
    log.log(
        level,
        f"{method} {path} - {status_code}",
        extra=extra
    )


def log_error(
    message: str,
    error: Exception,
    logger_name: str = "app",
    context: Optional[Dict[str, Any]] = None,
    **kwargs: Any
) -> None:
    """Log an error with full context and stack trace.
    
    Args:
        message: Error message
        error: Exception object
        logger_name: Logger name
        context: Additional context dictionary
        **kwargs: Additional context fields
    """
    log = logging.getLogger(logger_name)
    error_context: Dict[str, Any] = {
        "error_type": type(error).__name__,
        "error_message": str(error),
    }
    if context:
        error_context.update(context)
    if kwargs:
        error_context.update(kwargs)
    
    log.error(
        message,
        exc_info=error,
        extra={"context": error_context}
    )


def log_validation_error(
    field: str,
    error_type: str,
    message: str,
    input_value: Any = None,
    logger_name: str = "app.validation",
    **kwargs: Any
) -> None:
    """Log a validation error with field-level details.
    
    Args:
        field: Field name that failed validation
        error_type: Type of validation error (e.g., 'string_too_short', 'value_error')
        message: Validation error message
        input_value: The input value that failed (will be truncated if too long)
        logger_name: Logger name
        **kwargs: Additional context fields
    """
    log = logging.getLogger(logger_name)
    context: Dict[str, Any] = {
        "field": field,
        "error_type": error_type,
        "message": message,
    }
    
    # Truncate long input values for logging
    if input_value is not None:
        input_str = str(input_value)
        if len(input_str) > 200:
            context["input"] = input_str[:200] + "... (truncated)"
        else:
            context["input"] = input_str
    
    if kwargs:
        context.update(kwargs)
    
    log.warning(
        f"Validation error on field '{field}': {message}",
        extra={"context": context}
    )


def log_database_query(
    query_type: str,
    table: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
    result_count: Optional[int] = None,
    duration_ms: Optional[float] = None,
    logger_name: str = "app.db.query",
    **kwargs: Any
) -> None:
    """Log a database query with parameters and results.
    
    Args:
        query_type: Type of query (SELECT, COUNT, etc.)
        table: Table name being queried
        filters: Query filters/parameters (will be sanitized)
        result_count: Number of results returned
        duration_ms: Query execution duration in milliseconds
        logger_name: Logger name
        **kwargs: Additional context fields
    """
    log = logging.getLogger(logger_name)
    context: Dict[str, Any] = {
        "query_type": query_type,
    }
    
    if table:
        context["table"] = table
    
    if filters:
        # Sanitize filters - remove sensitive data and truncate long values
        sanitized_filters = {}
        for key, value in filters.items():
            if isinstance(value, str) and len(value) > 100:
                sanitized_filters[key] = value[:100] + "... (truncated)"
            elif key.lower() in ("password", "token", "secret", "key"):
                sanitized_filters[key] = "***REDACTED***"
            else:
                sanitized_filters[key] = value
        context["filters"] = sanitized_filters
    
    if result_count is not None:
        context["result_count"] = result_count
    
    if kwargs:
        context.update(kwargs)
    
    extra: Dict[str, Any] = {"context": context}
    if duration_ms is not None:
        extra["performance"] = {"duration_ms": duration_ms}
        if duration_ms > 1000:
            log.warning(f"Slow query: {query_type}", extra=extra)
        else:
            log.debug(f"Query executed: {query_type}", extra=extra)
    else:
        log.debug(f"Query executed: {query_type}", extra=extra)


def log_performance_issue(
    endpoint: str,
    method: str,
    duration_ms: float,
    threshold_ms: float = 1000.0,
    status_code: Optional[int] = None,
    logger_name: str = "app.performance",
    **kwargs: Any
) -> None:
    """Log performance issues for slow endpoints.
    
    Args:
        endpoint: API endpoint path
        method: HTTP method
        duration_ms: Request duration in milliseconds
        threshold_ms: Threshold for considering it slow (default: 1000ms)
        status_code: HTTP status code
        logger_name: Logger name
        **kwargs: Additional context
    """
    log = logging.getLogger(logger_name)
    context: Dict[str, Any] = {
        "endpoint": endpoint,
        "method": method,
        "duration_ms": duration_ms,
        "threshold_ms": threshold_ms,
    }
    
    if status_code:
        context["status_code"] = status_code
    
    if kwargs:
        context.update(kwargs)
    
    extra: Dict[str, Any] = {
        "context": context,
        "performance": {"duration_ms": duration_ms}
    }
    
    if duration_ms > threshold_ms:
        log.warning(
            f"Slow endpoint: {method} {endpoint} took {duration_ms:.2f}ms",
            extra=extra
        )
    else:
        log.debug(
            f"Endpoint: {method} {endpoint} took {duration_ms:.2f}ms",
            extra=extra
        )


def log_external_api_call(
    service_name: str,
    method: str,
    url: str,
    status_code: Optional[int] = None,
    duration_ms: Optional[float] = None,
    request_data: Optional[Dict[str, Any]] = None,
    response_data: Optional[Dict[str, Any]] = None,
    error: Optional[Exception] = None,
    logger_name: str = "app.external_api",
    **kwargs: Any
) -> None:
    """Log an external API call with request/response details.
    
    Args:
        service_name: Name of the external service (e.g., 'Connectra', 'S3')
        method: HTTP method
        url: Request URL (sensitive parts will be redacted)
        status_code: Response status code
        duration_ms: Request duration in milliseconds
        request_data: Request payload (will be sanitized)
        response_data: Response payload (will be sanitized and truncated)
        error: Exception if the call failed
        logger_name: Logger name
        **kwargs: Additional context fields
    """
    log = logging.getLogger(logger_name)
    context: Dict[str, Any] = {
        "service": service_name,
        "method": method,
        "url": url,  # URL redaction could be added if needed
    }
    
    if status_code is not None:
        context["status_code"] = status_code
    
    if request_data:
        # Sanitize request data
        sanitized_request = {}
        for key, value in request_data.items():
            if key.lower() in ("password", "token", "secret", "key", "api_key", "apikey"):
                sanitized_request[key] = "***REDACTED***"
            elif isinstance(value, str) and len(value) > 200:
                sanitized_request[key] = value[:200] + "... (truncated)"
            else:
                sanitized_request[key] = value
        context["request"] = sanitized_request
    
    if response_data:
        # Truncate large response data
        sanitized_response = {}
        for key, value in response_data.items():
            if isinstance(value, (dict, list)):
                # For complex structures, just log the keys or count
                if isinstance(value, dict):
                    sanitized_response[key] = f"<dict with {len(value)} keys>"
                else:
                    sanitized_response[key] = f"<list with {len(value)} items>"
            elif isinstance(value, str) and len(value) > 500:
                sanitized_response[key] = value[:500] + "... (truncated)"
            else:
                sanitized_response[key] = value
        context["response"] = sanitized_response
    
    if error:
        context["error_type"] = type(error).__name__
        context["error_message"] = str(error)
    
    if kwargs:
        context.update(kwargs)
    
    extra: Dict[str, Any] = {"context": context}
    if duration_ms is not None:
        extra["performance"] = {"duration_ms": duration_ms}
    
    if error:
        log.error(
            f"External API call failed: {service_name} {method} {url}",
            exc_info=error,
            extra=extra
        )
    elif status_code and status_code >= 400:
        log.warning(
            f"External API call returned error: {service_name} {method} {url} - {status_code}",
            extra=extra
        )
    else:
        log.info(
            f"External API call: {service_name} {method} {url}",
            extra=extra
        )


def log_background_task(
    task_name: str,
    status: str = "started",
    duration_ms: Optional[float] = None,
    result: Optional[Any] = None,
    error: Optional[Exception] = None,
    logger_name: str = "app.background",
    **kwargs: Any
) -> None:
    """Log a background task execution.
    
    Args:
        task_name: Name of the background task
        status: Task status ('started', 'completed', 'failed')
        duration_ms: Task duration in milliseconds
        result: Task result (will be truncated if too long)
        error: Exception if the task failed
        logger_name: Logger name
        **kwargs: Additional context fields
    """
    log = logging.getLogger(logger_name)
    context: Dict[str, Any] = {
        "task": task_name,
        "status": status,
    }
    
    if result is not None:
        result_str = str(result)
        if len(result_str) > 500:
            context["result"] = result_str[:500] + "... (truncated)"
        else:
            context["result"] = result_str
    
    if error:
        context["error_type"] = type(error).__name__
        context["error_message"] = str(error)
    
    if kwargs:
        context.update(kwargs)
    
    extra: Dict[str, Any] = {"context": context}
    if duration_ms is not None:
        extra["performance"] = {"duration_ms": duration_ms}
    
    if status == "failed" or error:
        log.error(
            f"Background task failed: {task_name}",
            exc_info=error,
            extra=extra
        )
    elif status == "completed":
        log.info(
            f"Background task completed: {task_name}",
            extra=extra
        )
    else:
        log.info(
            f"Background task {status}: {task_name}",
            extra=extra
        )


def log_api_error(
    endpoint: str,
    method: str,
    status_code: int,
    error_type: str,
    error_message: str,
    user_id: Optional[str] = None,
    request_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    logger_name: str = "app.errors",
    **kwargs: Any
) -> None:
    """Log API errors with comprehensive context.
    
    Args:
        endpoint: API endpoint path
        method: HTTP method
        status_code: HTTP status code
        error_type: Type of error (ValidationError, NotFoundError, etc.)
        error_message: Error message
        user_id: User ID if available
        request_id: Request ID for tracing
        context: Additional context
        logger_name: Logger name
        **kwargs: Additional fields
    """
    log = logging.getLogger(logger_name)
    error_context: Dict[str, Any] = {
        "endpoint": endpoint,
        "method": method,
        "status_code": status_code,
        "error_type": error_type,
        "error_message": error_message,
    }
    
    if user_id:
        error_context["user_id"] = user_id
    if context:
        error_context.update(context)
    if kwargs:
        error_context.update(kwargs)
    
    extra: Dict[str, Any] = {"context": error_context}
    if request_id:
        extra["request_id"] = request_id
    
    # Log at appropriate level based on status code
    if status_code >= 500:
        log.error(f"Server error on {method} {endpoint}: {error_message}", extra=extra)
    elif status_code >= 400:
        log.warning(f"Client error on {method} {endpoint}: {error_message}", extra=extra)
    else:
        log.info(f"Error on {method} {endpoint}: {error_message}", extra=extra)


def log_database_error(
    operation: str,
    table: Optional[str] = None,
    error: Optional[Exception] = None,
    query: Optional[str] = None,
    duration_ms: Optional[float] = None,
    logger_name: str = "app.db.errors",
    **kwargs: Any
) -> None:
    """Log database errors with query details.
    
    Args:
        operation: Database operation (SELECT, INSERT, etc.)
        table: Table name
        error: Exception that occurred
        query: SQL query (sanitized)
        duration_ms: Query duration if available
        logger_name: Logger name
        **kwargs: Additional context
    """
    log = logging.getLogger(logger_name)
    error_context: Dict[str, Any] = {
        "operation": operation,
    }
    
    if table:
        error_context["table"] = table
    if error:
        error_context["error_type"] = type(error).__name__
        error_context["error_message"] = str(error)
    if query:
        # Sanitize query - remove sensitive data
        sanitized_query = query
        for sensitive in ["password", "token", "secret", "api_key"]:
            sanitized_query = sanitized_query.replace(sensitive, "***REDACTED***")
        error_context["query"] = sanitized_query[:500]  # Truncate long queries
    if duration_ms:
        error_context["duration_ms"] = duration_ms
    if kwargs:
        error_context.update(kwargs)
    
    log.error(
        f"Database error during {operation}",
        exc_info=error is not None,
        extra={"context": error_context}
    )


def log_validation_context(
    endpoint: str,
    method: str,
    failed_fields: list[str],
    error_details: list[Dict[str, Any]],
    user_id: Optional[str] = None,
    logger_name: str = "app.validation.detail",
    **kwargs: Any
) -> None:
    """Log detailed validation error context.
    
    Args:
        endpoint: API endpoint path
        method: HTTP method
        failed_fields: List of field names that failed validation
        error_details: List of detailed error information
        user_id: User ID if available
        logger_name: Logger name
        **kwargs: Additional context
    """
    log = logging.getLogger(logger_name)
    context: Dict[str, Any] = {
        "endpoint": endpoint,
        "method": method,
        "failed_fields": failed_fields,
        "error_count": len(failed_fields),
        "error_details": error_details,
    }
    
    if user_id:
        context["user_id"] = user_id
    if kwargs:
        context.update(kwargs)
    
    log.warning(
        f"Validation failed on {method} {endpoint}: {len(failed_fields)} field(s) failed",
        extra={"context": context}
    )


def get_validation_suggestion(error_type: str, field_path: str) -> Optional[str]:
    """Provide helpful suggestions for common validation errors.
    
    Args:
        error_type: Type of validation error
        field_path: Path to the field that failed validation
        
    Returns:
        Helpful suggestion message or None
    """
    suggestions = {
        "missing": f"Required field '{field_path}' is missing. Please provide this field.",
        "string_too_short": f"Field '{field_path}' is too short. Check minimum length requirement.",
        "string_too_long": f"Field '{field_path}' exceeds maximum length. Please shorten it.",
        "value_error": f"Field '{field_path}' has invalid format. Check the expected format.",
        "string_type": f"Field '{field_path}' must be a string, not a number.",
        "int_parsing": f"Field '{field_path}' must be a valid integer.",
        "greater_than_equal": f"Field '{field_path}' must meet minimum value requirement.",
        "too_short": f"Field '{field_path}' list/array is too short. Provide at least the minimum required items.",
        "enum": f"Field '{field_path}' has invalid value. Check allowed values.",
        "bool_parsing": f"Field '{field_path}' must be a boolean (true/false).",
    }
    return suggestions.get(error_type)


def log_slow_query_alert(
    query_type: str,
    table: str,
    duration_ms: float,
    threshold_ms: float,
    filters: Optional[Dict[str, Any]] = None,
    logger_name: str = "app.performance.queries",
    **kwargs: Any
) -> None:
    """Log alerts for queries exceeding performance thresholds.
    
    Args:
        query_type: Type of query (SELECT, INSERT, etc.)
        table: Table name
        duration_ms: Query duration in milliseconds
        threshold_ms: Performance threshold in milliseconds
        filters: Query filters/parameters
        logger_name: Logger name
        **kwargs: Additional context
    """
    log = logging.getLogger(logger_name)
    
    context = {
        "query_type": query_type,
        "table": table,
        "duration_ms": duration_ms,
        "threshold_ms": threshold_ms,
        "slowness_factor": round(duration_ms / threshold_ms, 2),
    }
    
    if filters:
        context["filters"] = filters
    if kwargs:
        context.update(kwargs)
    
    log.warning(
        f"SLOW QUERY ALERT: {query_type} on {table} took {duration_ms:.2f}ms (threshold: {threshold_ms}ms)",
        extra={"context": context, "performance": {"duration_ms": duration_ms}}
    )