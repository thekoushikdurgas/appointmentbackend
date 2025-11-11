# Logging Conventions

This project configures logging in `app/core/logging.py` using the standard library.

- The root logger level is driven by `settings.LOG_LEVEL`; the default is `INFO`.
- Logs are emitted to both stdout and `logs/app.log` using the format from `settings.LOG_FORMAT`.
- Third-party libraries (`uvicorn`, `sqlalchemy.engine`, `celery`) are tuned to reduce noise.

## Authoring Logs

- Instantiate loggers with `logging.getLogger(__name__)` so that module paths appear in log records.
- Use `logger.debug` for verbose state, `logger.info` for lifecycle events, `logger.warning` for recoverable issues, and `logger.error`/`logger.exception` for failures.
- Redact or omit personally identifiable information; prefer structural context (`job_id`, `query_filters`, counts) over raw payloads.
- When logging errors inside exception handlers, chain context with `exc_info=True` or `logger.exception` to capture stack traces.
- For background tasks, always log the start, completion, and failure state with relevant counters to aid observability.

## Comments & Docstrings

- Favor short docstrings at the module/function level to clarify responsibilities.
- Inline comments should explain non-obvious branches or business rules rather than restating code.


