from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., description="Administrator username", min_length=1)
    password: str = Field(..., description="Administrator password", min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    username: str
    is_authenticated: bool = True
