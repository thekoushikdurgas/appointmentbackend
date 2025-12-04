"""Authentication API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.logging import get_logger, log_function_call
from app.db.session import get_db
from app.models.user import User
from app.repositories.token_blacklist import TokenBlacklistRepository
from app.schemas.common import MessageResponse
from app.schemas.filters import AuthFilterParams
from app.schemas.user import (
    LogoutRequest,
    LogoutResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    RegisterResponse,
    SessionResponse,
    TokenResponse,
    UserLogin,
    UserRegister,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = get_logger(__name__)
service = UserService()
blacklist_repo = TokenBlacklistRepository()


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


@router.post("/register/", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
async def register(
    register_data: UserRegister,
    filters: AuthFilterParams = Depends(resolve_auth_filters),
    session: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    """
    Register a new user account and receive access tokens.
    
    Creates a user profile automatically upon registration.
    """
    logger.info("Registration request: email=%s", register_data.email)
    
    try:
        user, access_token, refresh_token = await service.register_user(session, register_data)
        
        response = RegisterResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user={"uuid": user.uuid, "email": user.email},
            message="Registration successful! Please check your email to verify your account."
        )
        logger.info("Registration successful: user_uuid=%s email=%s", user.uuid, user.email)
        return response
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Registration failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed"
        ) from exc


@router.post("/login/", response_model=TokenResponse)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
async def login(
    login_data: UserLogin,
    filters: AuthFilterParams = Depends(resolve_auth_filters),
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate a user and receive access tokens.
    
    Updates the user's last_sign_in_at timestamp upon successful login.
    """
    logger.info("Login request: email=%s", login_data.email)
    
    try:
        user, access_token, refresh_token = await service.authenticate_user(session, login_data)
        
        # Refresh user to ensure all attributes are loaded and object is attached to session
        await session.refresh(user)
        
        # Extract user attributes immediately to avoid lazy loading issues
        user_uuid = user.uuid
        user_email = user.email
        
        response = TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user={"uuid": user_uuid, "email": user_email}
        )
        logger.info("Login successful: user_uuid=%s email=%s", user_uuid, user_email)
        return response
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Login failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Login failed"
        ) from exc


@router.post("/logout/", response_model=LogoutResponse)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
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
    logger.info("Logout request: user_uuid=%s", current_user.uuid)
    
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
                await session.commit()
                logger.info("Refresh token blacklisted: user_uuid=%s", current_user.uuid)
            else:
                logger.debug("Refresh token already blacklisted: user_uuid=%s", current_user.uuid)
        except Exception as exc:
            # Log error but don't fail logout - blacklisting is best effort
            logger.warning("Failed to blacklist refresh token: user_uuid=%s error=%s", current_user.uuid, exc)
            # Rollback the blacklist operation but continue with logout
            await session.rollback()
    
    response = LogoutResponse(message="Logout successful")
    logger.info("Logout successful: user_uuid=%s", current_user.uuid)
    return response


@router.get("/session/", response_model=SessionResponse)
@log_function_call(logger=logger, log_result=True)
async def get_session(
    filters: AuthFilterParams = Depends(resolve_auth_filters),
    current_user: User = Depends(get_current_user),
) -> SessionResponse:
    """
    Get the current authenticated user's session information.
    
    Useful for checking token validity.
    """
    logger.debug("Session request: user_uuid=%s", current_user.uuid)
    
    response = SessionResponse(
        user={
            "uuid": current_user.uuid,
            "email": current_user.email,
            "last_sign_in_at": current_user.last_sign_in_at
        }
    )
    logger.debug("Session response: user_uuid=%s", current_user.uuid)
    return response


@router.post("/refresh/", response_model=RefreshTokenResponse)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    filters: AuthFilterParams = Depends(resolve_auth_filters),
    session: AsyncSession = Depends(get_db),
) -> RefreshTokenResponse:
    """
    Refresh an expired access token using a refresh token.
    
    Returns new access and refresh tokens (token rotation).
    """
    logger.info("Token refresh request")
    
    try:
        access_token, refresh_token = await service.refresh_access_token(
            session,
            refresh_data.refresh_token
        )
        
        response = RefreshTokenResponse(
            access_token=access_token,
            refresh_token=refresh_token
        )
        logger.info("Token refresh successful")
        return response
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Token refresh failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token refresh failed"
        ) from exc

