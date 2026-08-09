"""Pydantic schemas for authentication endpoints."""

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    username: str = Field(..., example="analyst1")
    password: str = Field(..., example="securepassword123")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    role: str
    is_active: bool
    organization_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginResponse(TokenResponse):
    """Token pair plus the user profile and active organization."""
    user: UserResponse
    organization: dict | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


class UserUpdateRequest(BaseModel):
    email: EmailStr | None = None
    username: str | None = Field(None, min_length=3, max_length=100)
    is_active: bool | None = None
    password: str | None = Field(None, min_length=8)
