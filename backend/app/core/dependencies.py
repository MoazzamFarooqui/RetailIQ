"""FastAPI dependency injection — auth, tenant scoping, roles, DB session, Redis.

v3 tenancy model:
- JWTs carry `org_id` (the active organization) plus the user's role in it.
- `get_current_user` validates the token and returns the User.
- `get_current_org` resolves the active organization and asserts the user is
  a member of it (isolation enforcement).
- `require_org_roles` performs role checks using the org membership role
  hierarchy (owner > admin > manager > analyst > viewer).
"""

from typing import Annotated, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from redis.asyncio import Redis

from app.core.database import get_db
from app.core.security import decode_token
from app.core.cache import get_redis_client
from app.models.user import User
from app.models.organization import Organization, OrgStatus
from app.models.membership import OrganizationMember, OrganizationRole, ROLE_RANK

security_scheme = HTTPBearer()


def _org_id_from_payload(payload: Optional[dict]) -> Optional[str]:
    """Extract the active organization id from a JWT payload, if present."""
    if not payload:
        return None
    return payload.get("org_id")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency: extract and validate JWT, return the authenticated user."""
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Keep the user's preferred org in sync with the token when the token
    # carries one and the user has none persisted yet.
    if user.organization_id is None and _org_id_from_payload(payload):
        user.organization_id = _org_id_from_payload(payload)

    return user


async def get_current_org(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Organization:
    """Dependency: resolve the user's active organization and verify membership.

    This is the tenancy gate: every org-scoped endpoint depends on it, and
    every tenant query must filter by the returned organization id.
    """
    org_id = current_user.organization_id
    if org_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active organization. Create or join an organization first.",
        )

    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization not found",
        )
    if org.status != OrgStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization is not active",
        )

    # Membership check — the core isolation rule
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user.id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization",
        )

    return org


async def get_membership(
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> OrganizationMember:
    """Dependency: return the current user's membership (with role) in the active org."""
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.user_id == current_user.id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization",
        )
    return membership


def require_org_roles(allowed_roles: list[OrganizationRole] | list[str]):
    """Dependency factory: require the current user's *org role* to be one of allowed_roles.

    Example:
        @router.post("/invite")
        async def invite(current: User = Depends(require_org_roles(["owner", "admin"]))):
            ...
    """
    normalized = [
        r if isinstance(r, OrganizationRole) else OrganizationRole(r)
        for r in allowed_roles
    ]
    min_rank = min(ROLE_RANK[r] for r in normalized)

    async def role_checker(membership: OrganizationMember = Depends(get_membership)) -> OrganizationMember:
        if ROLE_RANK[membership.role] > min_rank:
            allowed = ", ".join(r.value for r in normalized)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{membership.role.value}' not authorized. Requires one of: {allowed}",
            )
        return membership

    return role_checker


# ── Legacy global-role helper (backwards compatibility) ─────────────────────
def require_roles(allowed_roles: list[str]):
    """Legacy role gate on the global User.role column.

    New endpoints should use require_org_roles instead; this remains for the
    pre-tenant auth flow and any user-scoped admin routes.
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' not authorized. Requires one of: {allowed_roles}",
            )
        return current_user
    return role_checker


async def get_redis() -> Redis:
    """Dependency: provide a Redis client instance."""
    client = await get_redis_client()
    return client


# Reusable type aliases for common dependency patterns
DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentOrg = Annotated[Organization, Depends(get_current_org)]
RedisClient = Annotated[Redis, Depends(get_redis)]
