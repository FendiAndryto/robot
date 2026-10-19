from fastapi import APIRouter, Depends, HTTPException, status
from app.core.config import settings
from app.core.security import verify_password, create_access_token
from app.core.deps import get_current_user
from app.models.auth import LoginRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User login with credentials to receive JWT bearer token"
)
async def login(credentials: LoginRequest):
    is_valid_user = (credentials.username == settings.ADMIN_USERNAME)
    is_valid_pass = verify_password(credentials.password, settings.ADMIN_PASSWORD)
    
    if not (is_valid_user and is_valid_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    token = create_access_token(subject=credentials.username)
    expires_in_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in_seconds
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user profile"
)
async def get_me(current_user: str = Depends(get_current_user)):
    return UserResponse(
        username=current_user,
        is_authenticated=True
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
