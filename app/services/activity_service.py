"""Service layer for user activity tracking."""

from typing import Optional
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.user import ActivityActionType, ActivityServiceType, ActivityStatus
from app.repositories.user import UserActivityRepository

logger = get_logger(__name__)


class ActivityService:
    """Business logic for user activity tracking."""

    def __init__(self, activity_repo: Optional[UserActivityRepository] = None) -> None:
        """Initialize the service with repository dependencies."""
        self.logger = get_logger(__name__)
        self.activity_repo = activity_repo or UserActivityRepository()

    def _extract_request_info(self, request: Optional[Request] = None) -> tuple[Optional[str], Optional[str]]:
        """
        Extract IP address and user agent from FastAPI request.
        
        Args:
            request: Optional FastAPI Request object
            
        Returns:
            Tuple of (ip_address, user_agent)
        """
        if not request:
            return None, None
        
        # Extract IP address
        # Check for forwarded headers first (for proxies/load balancers)
        ip_address = None
        if request.headers.get("x-forwarded-for"):
            # X-Forwarded-For can contain multiple IPs, take the first one
            ip_address = request.headers.get("x-forwarded-for").split(",")[0].strip()
        elif request.headers.get("x-real-ip"):
            ip_address = request.headers.get("x-real-ip")
        else:
            # Fallback to client host
            ip_address = request.client.host if request.client else None
        
        # Extract user agent
        user_agent = request.headers.get("user-agent")
        
        return ip_address, user_agent

    async def log_search_activity(
        self,
        session: AsyncSession,
        user_id: str,
        service_type: ActivityServiceType,
        request_params: dict,
        result_count: int,
        result_summary: Optional[dict] = None,
        status: ActivityStatus = ActivityStatus.SUCCESS,
        error_message: Optional[str] = None,
        request: Optional[Request] = None,
    ) -> None:
        """
        Log a search activity.
        
        Args:
            session: Database session
            user_id: User ID
            service_type: Service type (linkedin or email)
            request_params: Request parameters as dict
            result_count: Number of results returned
            result_summary: Optional summary of results
            status: Activity status (default: SUCCESS)
            error_message: Optional error message if failed
            request: Optional FastAPI Request object for extracting IP/user agent
        """
        try:
            ip_address, user_agent = self._extract_request_info(request)
            
            await self.activity_repo.create_activity(
                session=session,
                user_id=user_id,
                service_type=service_type,
                action_type=ActivityActionType.SEARCH,
                status=status,
                request_params=request_params,
                result_count=result_count,
                result_summary=result_summary,
                error_message=error_message,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            self.logger.debug(
                "Logged search activity: user_id=%s service_type=%s result_count=%d",
                user_id,
                service_type.value,
                result_count,
            )
        except Exception as exc:
            # Don't fail the main request if activity logging fails
            self.logger.exception("Failed to log search activity: %s", exc)

    async def log_export_activity(
        self,
        session: AsyncSession,
        user_id: str,
        service_type: ActivityServiceType,
        request_params: dict,
        export_id: str,
        result_count: int = 0,
        status: ActivityStatus = ActivityStatus.SUCCESS,
        error_message: Optional[str] = None,
        request: Optional[Request] = None,
    ) -> Optional[int]:
        """
        Log an export activity and return the activity ID for later updates.
        
        Args:
            session: Database session
            user_id: User ID
            service_type: Service type (linkedin or email)
            request_params: Request parameters as dict
            export_id: Export ID
            result_count: Number of results (default: 0, will be updated when export completes)
            status: Activity status (default: SUCCESS)
            error_message: Optional error message if failed
            request: Optional FastAPI Request object for extracting IP/user agent
            
        Returns:
            Activity ID if successful, None if logging failed
        """
        try:
            ip_address, user_agent = self._extract_request_info(request)
            
            result_summary = {
                "export_id": export_id,
                "status": status.value,
            }
            
            activity = await self.activity_repo.create_activity(
                session=session,
                user_id=user_id,
                service_type=service_type,
                action_type=ActivityActionType.EXPORT,
                status=status,
                request_params=request_params,
                result_count=result_count,
                result_summary=result_summary,
                error_message=error_message,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            self.logger.debug(
                "Logged export activity: user_id=%s service_type=%s export_id=%s activity_id=%d",
                user_id,
                service_type.value,
                export_id,
                activity.id,
            )
            return activity.id
        except Exception as exc:
            # Don't fail the main request if activity logging fails
            self.logger.exception("Failed to log export activity: %s", exc)
            return None

    async def update_export_activity(
        self,
        session: AsyncSession,
        activity_id: int,
        result_count: int,
        result_summary: Optional[dict] = None,
        status: Optional[ActivityStatus] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Update an export activity when the export completes.
        
        Args:
            session: Database session
            activity_id: Activity ID to update
            result_count: Final result count
            result_summary: Updated result summary
            status: Updated status (if changed)
            error_message: Error message if failed
        """
        try:
            # Get the activity
            from sqlalchemy import select
            from app.models.user import UserActivity
            
            stmt = select(UserActivity).where(UserActivity.id == activity_id)
            result = await session.execute(stmt)
            activity = result.scalar_one_or_none()
            
            if not activity:
                self.logger.warning("Activity not found for update: activity_id=%d", activity_id)
                return
            
            # Update fields
            update_kwargs = {}
            if result_count is not None:
                update_kwargs["result_count"] = result_count
            if result_summary is not None:
                update_kwargs["result_summary"] = result_summary
            if status is not None:
                update_kwargs["status"] = status
            if error_message is not None:
                update_kwargs["error_message"] = error_message
            
            if update_kwargs:
                await self.activity_repo.update_activity(session, activity, **update_kwargs)
                self.logger.debug(
                    "Updated export activity: activity_id=%d result_count=%d status=%s",
                    activity_id,
                    result_count,
                    status.value if status else "unchanged",
                )
        except Exception as exc:
            # Don't fail the main request if activity update fails
            self.logger.exception("Failed to update export activity: %s", exc)

