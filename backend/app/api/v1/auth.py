from fastapi import APIRouter, Depends, HTTPException, status
from app.core.config import settings
from app.core.security import verify_password, create_access_token
from app.core.deps import get_current_user
from app.models.auth import (
    LoginRequest,
    RegisterRequest,
    ChangePasswordRequest,
    TokenResponse,
    UserResponse
)
from app.services.user_service import user_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account"
)
async def register(req: RegisterRequest):
    try:
        # Public self-registration is strictly restricted to 'trader' role
        new_user = user_service.register(
            username=req.username,
            plain_password=req.password,
            role="trader"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    token = create_access_token(subject=new_user["username"])
    expires_in_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in_seconds,
        username=new_user["username"],
        role=new_user.get("role", "trader")
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User login with credentials to receive JWT bearer token"
)
async def login(credentials: LoginRequest):
    username = credentials.username.strip()
    user = user_service.authenticate(username, credentials.password)

    # Fallback to direct settings admin verification for backwards compatibility
    if not user and username == settings.ADMIN_USERNAME:
        if verify_password(credentials.password, settings.ADMIN_PASSWORD):
            user = {"username": username, "role": "admin"}

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    token = create_access_token(subject=user["username"])
    expires_in_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in_seconds,
        username=user["username"],
        role=user.get("role", "trader")
    )


@router.post(
    "/change-password",
    status_code=status.HTTP_200_OK,
    summary="Change password for current logged-in user"
)
async def change_password(
    req: ChangePasswordRequest,
    current_user: str = Depends(get_current_user)
):
    try:
        success = user_service.change_password(
            username=current_user,
            old_password=req.old_password,
            new_password=req.new_password
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password verification failed"
        )

    return {
        "status": "ok",
        "message": "Password changed successfully"
    }


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user profile"
)
async def get_me(current_user: str = Depends(get_current_user)):
    user_record = user_service.get_user(current_user)
    role = user_record.get("role", "admin" if current_user == settings.ADMIN_USERNAME else "trader") if user_record else "admin"

    return UserResponse(
        username=current_user,
        is_authenticated=True,
        role=role
    )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Client session logout acknowledgment"
)
async def logout():
    return {
        "status": "ok",
        "message": "Logged out successfully"
    }
