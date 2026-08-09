"""Pydantic schemas for organizations, memberships, and invitations."""

from datetime import datetime
from pydantic import BaseModel, Field, EmailStr


# ── Organization ─────────────────────────────────────────────────────────────
class OrganizationCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: str | None = None


class OrganizationUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    description: str | None = None
    default_service_level: float | None = Field(None, ge=0.5, le=0.999)
    default_lead_time_days: int | None = Field(None, ge=1, le=365)


class OrganizationResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None
    status: str
    owner_id: str
    default_service_level: float
    default_lead_time_days: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Membership ───────────────────────────────────────────────────────────────
class MembershipResponse(BaseModel):
    id: str
    organization_id: str
    user_id: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MemberInfo(BaseModel):
    """A member with user details, for the org members list."""
    user_id: str
    email: str
    username: str
    role: str
    is_active: bool
    joined_at: datetime


class MembershipUpdateRequest(BaseModel):
    role: str = Field(..., pattern="^(owner|admin|manager|analyst|viewer)$")


# ── Invitations ──────────────────────────────────────────────────────────────
class InvitationCreateRequest(BaseModel):
    email: EmailStr
    role: str = Field("viewer", pattern="^(admin|manager|analyst|viewer)$")


class InvitationResponse(BaseModel):
    id: str
    organization_id: str
    email: str
    role: str
    status: str
    expires_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class InviteAcceptRequest(BaseModel):
    """Accept an invitation. For existing users: email + token.
    For new users (not yet registered): email + token + chosen password."""
    email: EmailStr
    token: str
    password: str | None = Field(None, min_length=8)


class InviteAcceptResponse(BaseModel):
    organization_id: str
    organization_name: str
    role: str
    user_id: str


