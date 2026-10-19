from typing import Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., description="Username", min_length=1)
    password: str = Field(..., description="Password", min_length=1)


class RegisterRequest(BaseModel):
    username: str = Field(..., description="Desired username", min_length=3, max_length=50)
    password: str = Field(..., description="Account password", min_length=4)
    role: Optional[str] = Field("trader", description="User role (admin or trader)")


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., description="Current password")
    new_password: str = Field(..., description="New password", min_length=4)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    username: Optional[str] = None
    role: Optional[str] = "trader"


class UserResponse(BaseModel):
    username: str
    is_authenticated: bool = True
    role: Optional[str] = "trader"

