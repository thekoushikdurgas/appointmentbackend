"""Application-specific exception hierarchy with structured logging."""

from fastapi import HTTPException, status

from app.core.logging import get_logger

logger = get_logger(__name__)


class AppException(HTTPException):
    """Base exception with application-specific error codes."""

    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: str = "APP_ERROR",
    ) -> None:
        logger.debug(
            "Initializing AppException status_code=%s error_code=%s detail=%s",
            status_code,
            error_code,
            detail,
        )
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code


class NotFoundException(AppException):
    """Exception raised when a resource cannot be located."""

    def __init__(self, detail: str = "Resource not found") -> None:
        logger.info("Raising NotFoundException detail=%s", detail)
        super().__init__(status.HTTP_404_NOT_FOUND, detail, "NOT_FOUND")


class UnauthorizedException(AppException):
    """Exception raised for failed authentication attempts."""

    def __init__(self, detail: str = "Unauthorized") -> None:
        logger.warning("Raising UnauthorizedException detail=%s", detail)
        super().__init__(status.HTTP_401_UNAUTHORIZED, detail, "UNAUTHORIZED")


class ForbiddenException(AppException):
    """Exception raised when a user lacks permission to access a resource."""

    def __init__(self, detail: str = "Forbidden") -> None:
        logger.warning("Raising ForbiddenException detail=%s", detail)
        super().__init__(status.HTTP_403_FORBIDDEN, detail, "FORBIDDEN")


class ValidationException(AppException):
    """Exception raised for data validation errors."""

    def __init__(self, detail: str = "Validation error") -> None:
        logger.info("Raising ValidationException detail=%s", detail)
        super().__init__(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail,
            "VALIDATION_ERROR",
        )

