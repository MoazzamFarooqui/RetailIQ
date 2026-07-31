"""Pydantic schemas for authentication endpoints."""

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: str = Field(..., example="user@example.com")
    username: str = Field(..., min_length=3, max_length=100, example="analyst1")
    password: str = Field(..., min_length=8, example="securepassword123")


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
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    email: str | None = None
    username: str | None = None
    role: str | None = None
    is_active: bool | None = None
    password: str | None = None
