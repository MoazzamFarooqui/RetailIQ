"""User management endpoints — profile, list, update (admin)."""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.core.security import hash_password
from app.schemas.auth import UserResponse, UserUpdateRequest
from app.models.user import User, UserRole

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get the authenticated user's profile."""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    request: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the authenticated user's profile."""
    if request.email is not None:
        current_user.email = request.email
    if request.username is not None:
        current_user.username = request.username
    if request.password is not None:
        current_user.hashed_password = hash_password(request.password)
    await db.flush()
    await db.refresh(current_user)
    return current_user


@router.get("/", response_model=list[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["admin"])),
):
    """List all users (admin only)."""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return result.scalars().all()


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    request: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["admin"])),
):
    """Update any user's details (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if request.email is not None:
        user.email = request.email
    if request.username is not None:
        user.username = request.username
    if request.role is not None:
        user.role = UserRole(request.role)
    if request.is_active is not None:
        user.is_active = request.is_active
    if request.password is not None:
        user.hashed_password = hash_password(request.password)

    await db.flush()
    await db.refresh(user)
    return user


