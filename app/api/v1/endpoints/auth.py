"""Authentication API endpoints."""

import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.repositories.token_blacklist import TokenBlacklistRepository
from app.schemas.billing import BillingInfoResponse
from app.schemas.filters import AuthFilterParams
from app.schemas.user import (
    LogoutRequest,
    LogoutResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    RegisterResponse,
    SessionResponse,
    TokenResponse,
    UserInfoResponse,
    UserLogin,
    UserRegister,
)
from app.services.billing_service import BillingService
from app.services.user_service import UserService
from app.utils.logger import get_logger, log_error, log_api_error

router = APIRouter(prefix="/auth", tags=["Authentication"])
service = UserService()
billing_service = BillingService()
blacklist_repo = TokenBlacklistRepository()
logger = get_logger(__name__)


async def resolve_auth_filters(request: Request) -> AuthFilterParams:
    """Build auth filter parameters from query string and request body."""
    query_params = request.query_params
    data = dict(query_params)
    try:
        return AuthFilterParams.model_validate(data)
    except ValidationError as exc:
        first_error = exc.errors()[0] if exc.errors() else {}
        message = first_error.get("msg", "Invalid query parameters")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc


async def _register_handler(
    register_data: UserRegister,
    filters: AuthFilterParams,
    session: AsyncSession,
) -> RegisterResponse:
    """Internal handler for register endpoint."""
    start_time = time.time()
    logger.info(
        "User registration attempt",
        extra={
            "context": {
                "email": register_data.email,
                "name": register_data.name,
                "has_geolocation": register_data.geolocation is not None,
            }
        }
    )
    
    try:
        user, access_token, refresh_token = await service.register_user(session, register_data)
        # Logging is handled in the service layer with appropriate levels
        
        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            "User registration completed successfully",
            extra={
                "context": {
                    "user_uuid": user.uuid,
                    "email": user.email,
                },
                "performance": {"duration_ms": duration_ms}
            }
        )
        
        response = RegisterResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user={"uuid": user.uuid, "email": user.email},
            message="Registration successful! Please check your email to verify your account."
        )
        return response
    except HTTPException as exc:
        duration_ms = (time.time() - start_time) * 1000
        # Enhanced error logging with specific error context
        error_context = {
            "email": register_data.email,
            "status_code": exc.status_code,
            "detail": str(exc.detail),
            "error_type": "HTTPException",
        }
        
        # Add specific error context based on status code
        if exc.status_code == status.HTTP_400_BAD_REQUEST:
            # Parse detail to identify specific failure point
            if isinstance(exc.detail, dict):
                if "email" in exc.detail:
                    error_context["failure_point"] = "email_validation"
                    error_context["email_error"] = exc.detail["email"]
                elif "password" in exc.detail:
                    error_context["failure_point"] = "password_validation"
                    error_context["password_error"] = exc.detail["password"]
                else:
                    error_context["failure_point"] = "validation"
            else:
                error_context["failure_point"] = "validation"
        elif exc.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            error_context["failure_point"] = "request_validation"
        elif exc.status_code == status.HTTP_409_CONFLICT:
            error_context["failure_point"] = "duplicate_email"
        elif exc.status_code >= 500:
            error_context["failure_point"] = "server_error"
        
        logger.warning(
            "User registration failed",
            extra={
                "context": error_context,
                "performance": {"duration_ms": duration_ms}
            }
        )
        raise
    except Exception as exc:
        duration_ms = (time.time() - start_time) * 1000
        # Enhanced error logging with transaction context
        log_error(
            "User registration error: unexpected exception",
            exc,
            "app.api.v1.endpoints.auth",
            context={
                "email": register_data.email,
                "name": register_data.name,
                "duration_ms": duration_ms,
                "failure_point": "unknown",
                "error_type": type(exc).__name__,
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed due to an internal error. Please try again later."
        ) from exc


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    register_data: UserRegister,
    filters: AuthFilterParams = Depends(resolve_auth_filters),
    session: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    """
    Register a new user account and receive access tokens.
    
    Creates a user profile automatically upon registration.
    """
    return await _register_handler(register_data, filters, session)


@router.post("/register/", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_with_slash(
    register_data: UserRegister,
    filters: AuthFilterParams = Depends(resolve_auth_filters),
    session: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    """
    Register a new user account and receive access tokens (with trailing slash).
    
    Creates a user profile automatically upon registration.
    """
    return await _register_handler(register_data, filters, session)


@router.post("/login/", response_model=TokenResponse)
async def login(
    login_data: UserLogin,
    filters: AuthFilterParams = Depends(resolve_auth_filters),
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate a user and receive access tokens.
    
    Updates the user's last_sign_in_at timestamp upon successful login.
    """
    start_time = time.time()
    logger.debug(
        "User login attempt",
        extra={
            "context": {
                "email": login_data.email,
            }
        }
    )
    
    try:
        user, access_token, refresh_token = await service.authenticate_user(session, login_data)
        
        # Refresh user to ensure all attributes are loaded and object is attached to session
        await session.refresh(user)
        
        # Extract user attributes immediately to avoid lazy loading issues
        user_uuid = user.uuid
        user_email = user.email
        duration_ms = (time.time() - start_time) * 1000
        
        # Only log as INFO if slow, otherwise DEBUG
        if duration_ms > 1000:
            logger.info(
                "User login successful (slow)",
                extra={
                    "context": {
                        "user_uuid": user_uuid,
                        "email": user_email,
                    },
                    "performance": {"duration_ms": duration_ms}
                }
            )
        else:
            logger.debug(
                "User login successful",
                extra={
                    "context": {
                        "user_uuid": user_uuid,
                        "email": user_email,
                    },
                    "performance": {"duration_ms": duration_ms}
                }
            )
        
        response = TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user={"uuid": user_uuid, "email": user_email}
        )
        return response
    except HTTPException as exc:
        duration_ms = (time.time() - start_time) * 1000
        logger.warning(
            "User login failed",
            extra={
                "context": {
                    "email": login_data.email,
                    "status_code": exc.status_code,
                    "detail": str(exc.detail),
                },
                "performance": {"duration_ms": duration_ms}
            }
        )
        raise
    except Exception as exc:
        duration_ms = (time.time() - start_time) * 1000
        log_error(
            "User login error",
            exc,
            "app.api.v1.endpoints.auth",
            context={
                "email": login_data.email,
                "duration_ms": duration_ms,
            }
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Login failed"
        ) from exc


@router.post("/logout/", response_model=LogoutResponse)
async def logout(
    logout_data: LogoutRequest,
    filters: AuthFilterParams = Depends(resolve_auth_filters),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> LogoutResponse:
    """
    Logout the current user and invalidate refresh token.
    
    If a refresh_token is provided, it will be blacklisted to prevent reuse.
    Logout succeeds even if refresh token is not provided.
    """
    start_time = time.time()
    logger.debug(
        "User logout attempt",
        extra={
            "context": {
                "user_uuid": current_user.uuid,
                "email": current_user.email,
                "has_refresh_token": bool(logout_data.refresh_token),
            }
        }
    )
    
    # Blacklist refresh token if provided
    if logout_data.refresh_token:
        try:
            # Check if token is already blacklisted (idempotent operation)
            is_blacklisted = await blacklist_repo.is_token_blacklisted(session, logout_data.refresh_token)
            if not is_blacklisted:
                await blacklist_repo.create_blacklist_entry(
                    session,
                    logout_data.refresh_token,
                    current_user.uuid,
                )
                # Flush to persist changes without committing (transaction managed by get_db())
                await session.flush()
                logger.debug(
                    "Refresh token blacklisted",
                    extra={
                        "context": {
                            "user_uuid": current_user.uuid,
                        }
                    }
                )
            else:
                logger.debug(
                    "Refresh token already blacklisted",
                    extra={
                        "context": {
                            "user_uuid": current_user.uuid,
                        }
                    }
                )
        except Exception as exc:
            # Failed to blacklist refresh token - rollback but continue with logout
            log_error(
                "Failed to blacklist refresh token during logout",
                exc,
                "app.api.v1.endpoints.auth",
                context={
                    "user_uuid": current_user.uuid,
                }
            )
            await session.rollback()
    
    duration_ms = (time.time() - start_time) * 1000
    # Only log as INFO if slow, otherwise DEBUG
    if duration_ms > 1000:
        logger.info(
            "User logout successful (slow)",
            extra={
                "context": {
                    "user_uuid": current_user.uuid,
                    "email": current_user.email,
                },
                "performance": {"duration_ms": duration_ms}
            }
        )
    else:
        logger.debug(
            "User logout successful",
            extra={
                "context": {
                    "user_uuid": current_user.uuid,
                    "email": current_user.email,
                },
                "performance": {"duration_ms": duration_ms}
            }
        )
    
    response = LogoutResponse(message="Logout successful")
    return response


@router.get("/session/", response_model=SessionResponse)
async def get_session(
    filters: AuthFilterParams = Depends(resolve_auth_filters),
    current_user: User = Depends(get_current_user),
) -> SessionResponse:
    """
    Get the current authenticated user's session information.
    
    Useful for checking token validity.
    """
    response = SessionResponse(
        user={
            "uuid": current_user.uuid,
            "email": current_user.email,
            "last_sign_in_at": current_user.last_sign_in_at
        }
    )
    return response


# Resolve forward references for UserInfoResponse before using it in route decorator
# Import billing schema and rebuild model to resolve forward reference
try:
    from app.schemas.billing import BillingInfoResponse
    UserInfoResponse.model_rebuild()
except ImportError:
    # Billing schema not available - will be resolved when endpoint is called
    pass


@router.get("/user-info/", response_model=UserInfoResponse)
async def get_user_info(
    filters: AuthFilterParams = Depends(resolve_auth_filters),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserInfoResponse:
    """
    Get combined user information in a single request.
    
    Returns session, profile, and billing data to reduce API calls.
    """
    try:
        # Get session data
        session_data = SessionResponse(
            user={
                "uuid": current_user.uuid,
                "email": current_user.email,
                "last_sign_in_at": current_user.last_sign_in_at
            }
        )
        
        # Get profile data
        profile_data = await service.get_user_profile(session, current_user.uuid)
        
        # Get billing data
        billing_data_dict = await billing_service.get_billing_info(session, current_user.uuid)
        billing_data = BillingInfoResponse(**billing_data_dict)
        
        return UserInfoResponse(
            session=session_data,
            profile=profile_data,
            billing=billing_data
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user information"
        ) from exc


@router.post("/refresh/", response_model=RefreshTokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    filters: AuthFilterParams = Depends(resolve_auth_filters),
    session: AsyncSession = Depends(get_db),
) -> RefreshTokenResponse:
    """
    Refresh an expired access token using a refresh token.
    
    Returns new access and refresh tokens (token rotation).
    """
    start_time = time.time()
    logger.debug(
        "Token refresh attempt",
        extra={
            "context": {
                "has_refresh_token": bool(refresh_data.refresh_token),
            }
        }
    )
    
    try:
        access_token, refresh_token = await service.refresh_access_token(
            session,
            refresh_data.refresh_token
        )
        duration_ms = (time.time() - start_time) * 1000
        
        # Only log as INFO if slow, otherwise DEBUG
        if duration_ms > 1000:
            logger.info(
                "Token refresh successful (slow)",
                extra={
                    "performance": {"duration_ms": duration_ms}
                }
            )
        else:
            logger.debug(
                "Token refresh successful",
                extra={
                    "performance": {"duration_ms": duration_ms}
                }
            )
        
        response = RefreshTokenResponse(
            access_token=access_token,
            refresh_token=refresh_token
        )
        return response
    except HTTPException as exc:
        duration_ms = (time.time() - start_time) * 1000
        if exc.status_code == 400:
            log_api_error(
                endpoint="/api/v1/auth/refresh/",
                method="POST",
                status_code=400,
                error_type="TokenInvalidError" if "invalid" in str(exc.detail).lower() else "TokenExpiredError",
                error_message=str(exc.detail),
                context={"token_type": "refresh"}
            )
        raise
    except Exception as exc:
        duration_ms = (time.time() - start_time) * 1000
        log_error(
            "Token refresh error",
            exc,
            "app.api.v1.endpoints.auth",
            context={
                "duration_ms": duration_ms,
            }
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token refresh failed"
        ) from exc

