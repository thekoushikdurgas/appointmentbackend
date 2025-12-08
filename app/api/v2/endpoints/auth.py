"""Authentication API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
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
async def register(
    register_data: UserRegister,
    filters: AuthFilterParams = Depends(resolve_auth_filters),
    session: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    """
    Register a new user account and receive access tokens.
    
    Creates a user profile automatically upon registration.
    """
    try:
        user, access_token, refresh_token = await service.register_user(session, register_data)
        
        response = RegisterResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user={"uuid": user.uuid, "email": user.email},
            message="Registration successful! Please check your email to verify your account."
        )
        return response
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed"
        ) from exc


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
        return response
    except HTTPException:
        raise
    except Exception as exc:
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
            else:
                pass  # Refresh token already blacklisted
        except Exception as exc:
            # Failed to blacklist refresh token - rollback but continue with logout
            pass
            await session.rollback()
    
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
    try:
        access_token, refresh_token = await service.refresh_access_token(
            session,
            refresh_data.refresh_token
        )
        
        response = RefreshTokenResponse(
            access_token=access_token,
            refresh_token=refresh_token
        )
        return response
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token refresh failed"
        ) from exc

