"""Authentication endpoints — register, login, refresh tokens, password change."""

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.schemas.auth import (
    RegisterRequest, LoginRequest, TokenResponse, RefreshRequest, UserResponse,
    LoginResponse, ChangePasswordRequest,
)
from app.models.user import User
from app.models.membership import OrganizationMember

router = APIRouter()


async def _load_user_profile(db: AsyncSession, user: User) -> dict:
    """Load the user's active organization into the login response."""
    organization = None
    if user.organization_id:
        from app.models.organization import Organization
        result = await db.execute(select(Organization).where(Organization.id == user.organization_id))
        org = result.scalar_one_or_none()
        if org:
            organization = {
                "id": org.id,
                "name": org.name,
                "slug": org.slug,
                "status": org.status.value,
            }
    return organization


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user (no organization yet)."""
    # Check if email exists
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Check if username exists
    result = await db.execute(select(User).where(User.username == request.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already taken")

    user = User(
        email=request.email,
        username=request.username,
        hashed_password=hash_password(request.password),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate user and return JWT tokens + profile + active org."""
    result = await db.execute(select(User).where(User.username == request.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive")

    # If the user has no active org but is a member of at least one, prefer
    # the most recent membership — makes first login "just work".
    if user.organization_id is None:
        result = await db.execute(
            select(OrganizationMember)
            .where(OrganizationMember.user_id == user.id)
            .order_by(OrganizationMember.created_at.desc())
            .limit(1)
        )
        latest = result.scalar_one_or_none()
        if latest:
            user.organization_id = latest.organization_id
            await db.commit()

    org_id = user.organization_id
    role = user.role.value

    # Effective org role (v3): prefer the membership role when an org is active
    if org_id:
        result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == user.id,
            )
        )
        membership = result.scalar_one_or_none()
        if membership:
            role = membership.role.value

    access_token = create_access_token(data={"sub": user.id, "org_id": org_id, "role": role})
    refresh_token = create_refresh_token(data={"sub": user.id, "org_id": org_id, "role": role})

    organization = await _load_user_profile(db, user)
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
        organization=organization,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: RefreshRequest):
    """Refresh an expired access token using a refresh token."""
    payload = decode_token(request.refresh_token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user_id = payload.get("sub")
    org_id = payload.get("org_id")
    role = payload.get("role", "analyst")

    new_access = create_access_token(data={"sub": user_id, "org_id": org_id, "role": role})
    new_refresh = create_refresh_token(data={"sub": user_id, "org_id": org_id, "role": role})

    return TokenResponse(access_token=new_access, refresh_token=new_refresh)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    request: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change the authenticated user's password."""
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    current_user.hashed_password = hash_password(request.new_password)
    await db.commit()
