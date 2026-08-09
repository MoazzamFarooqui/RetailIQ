"""Organization (tenant) management endpoints.

Covers: create/update org, list members, invite members, accept/revoke
invitations, change membership roles, transfer ownership, and the
organization switcher (set active org).
"""

import uuid
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func

from app.core.database import get_db
from app.core.dependencies import (
    get_current_user, get_current_org, get_membership, require_org_roles,
)
from app.core.security import create_access_token, hash_password
from app.schemas.organization import (
    OrganizationCreateRequest, OrganizationUpdateRequest, OrganizationResponse,
    MembershipResponse, MemberInfo, MembershipUpdateRequest,
    InvitationCreateRequest, InvitationResponse, InviteAcceptRequest,
    InviteAcceptResponse,
)
from app.models.user import User
from app.models.organization import Organization, OrgStatus
from app.models.membership import OrganizationMember, OrganizationRole, ROLE_RANK
from app.models.invitation import Invitation, InvitationStatus

router = APIRouter()


def _slugify(name: str) -> str:
    """Create a URL-friendly slug from an organization name."""
    slug = "".join(c if c.isalnum() else "-" for c in name.lower()).strip("-")
    return slug[:80] or "org"


# ── Organization CRUD ────────────────────────────────────────────────────────

@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    request: OrganizationCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new organization; the creator becomes its owner."""
    base_slug = _slugify(request.name)
    slug = base_slug
    counter = 1
    # Ensure the slug is unique
    while True:
        result = await db.execute(select(Organization).where(Organization.slug == slug))
        if result.scalar_one_or_none() is None:
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    org = Organization(
        name=request.name,
        slug=slug,
        description=request.description,
        owner_id=current_user.id,
        status=OrgStatus.ACTIVE,
    )
    db.add(org)
    await db.flush()

    # Creator is the owner, and the new org becomes their active org
    db.add(OrganizationMember(
        organization_id=org.id,
        user_id=current_user.id,
        role=OrganizationRole.OWNER,
    ))
    current_user.organization_id = org.id
    await db.commit()
    await db.refresh(org)
    return org


@router.get("/me", response_model=OrganizationResponse)
async def get_my_org(org: Organization = Depends(get_current_org)):
    """Get the current user's active organization."""
    return org


@router.patch("/me", response_model=OrganizationResponse)
async def update_my_org(
    request: OrganizationUpdateRequest,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    membership: OrganizationMember = Depends(require_org_roles(["owner", "admin"])),
):
    """Update the active organization's profile or defaults."""
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(org, field, value)
    await db.commit()
    await db.refresh(org)
    return org


@router.post("/switch/{org_id}", response_model=OrganizationResponse)
async def switch_organization(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set the user's active organization (org switcher in the UI)."""
    # Must be a member of the target org
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user.id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=403, detail="You are not a member of this organization")

    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if org is None or org.status != OrgStatus.ACTIVE:
        raise HTTPException(status_code=404, detail="Organization not found or inactive")

    current_user.organization_id = org.id
    await db.commit()
    return org


@router.get("/members", response_model=list[MemberInfo])
async def list_members(
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
):
    """List all members of the active organization with their roles."""
    result = await db.execute(
        select(OrganizationMember, User)
        .join(User, User.id == OrganizationMember.user_id)
        .where(OrganizationMember.organization_id == org.id)
        .order_by(OrganizationMember.created_at)
    )
    rows = result.all()
    return [
        MemberInfo(
            user_id=user.id,
            email=user.email,
            username=user.username,
            role=member.role.value,
            is_active=user.is_active,
            joined_at=member.created_at,
        )
        for member, user in rows
    ]


@router.patch("/members/{user_id}", response_model=MemberInfo)
async def update_member_role(
    user_id: str,
    request: MembershipUpdateRequest,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    membership: OrganizationMember = Depends(require_org_roles(["owner", "admin"])),
):
    """Change a member's role. Owners cannot be demoted by non-owners."""
    new_role = OrganizationRole(request.role)

    result = await db.execute(
        select(OrganizationMember, User)
        .join(User, User.id == OrganizationMember.user_id)
        .where(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.user_id == user_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Member not found in this organization")
    target_membership, target_user = row

    # Prevent demoting the owner unless the caller is the owner
    if target_membership.role == OrganizationRole.OWNER and membership.role != OrganizationRole.OWNER:
        raise HTTPException(status_code=403, detail="Only the owner can change the owner's role")

    target_membership.role = new_role
    await db.commit()
    return MemberInfo(
        user_id=target_user.id,
        email=target_user.email,
        username=target_user.username,
        role=new_role.value,
        is_active=target_user.is_active,
        joined_at=target_membership.created_at,
    )


@router.delete("/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    membership: OrganizationMember = Depends(require_org_roles(["owner", "admin"])),
):
    """Remove a member from the organization. Owners cannot be removed."""
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.user_id == user_id,
        )
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="Member not found")
    if target.role == OrganizationRole.OWNER:
        raise HTTPException(status_code=403, detail="The owner cannot be removed. Transfer ownership first.")

    # If the removed user's active org was this one, clear it
    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()
    if target_user and target_user.organization_id == org.id:
        target_user.organization_id = None

    await db.delete(target)
    await db.commit()


@router.post("/transfer-ownership/{user_id}", response_model=OrganizationResponse)
async def transfer_ownership(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    membership: OrganizationMember = Depends(require_org_roles(["owner"])),
):
    """Transfer organization ownership to another member."""
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.user_id == user_id,
        )
    )
    new_owner = result.scalar_one_or_none()
    if new_owner is None:
        raise HTTPException(status_code=404, detail="Target user is not a member of this organization")

    # Old owner becomes admin
    membership.role = OrganizationRole.ADMIN
    new_owner.role = OrganizationRole.OWNER
    org.owner_id = user_id
    await db.commit()
    await db.refresh(org)
    return org


# ── Invitations ──────────────────────────────────────────────────────────────

@router.post("/invitations", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
async def create_invitation(
    request: InvitationCreateRequest,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    membership: OrganizationMember = Depends(require_org_roles(["owner", "admin"])),
    current_user: User = Depends(get_current_user),
):
    """Invite a user (by email) to join the active organization."""
    email = request.email.lower()

    # Already a member?
    result = await db.execute(
        select(User).where(User.email == email)
    )
    existing = result.scalar_one_or_none()
    if existing:
        result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org.id,
                OrganizationMember.user_id == existing.id,
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="This user is already a member")

    # Existing pending invitation?
    result = await db.execute(
        select(Invitation).where(
            Invitation.organization_id == org.id,
            Invitation.email == email,
            Invitation.status == InvitationStatus.PENDING,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="An invitation for this email is already pending")

    invitation = Invitation(
        organization_id=org.id,
        email=email,
        role=request.role,
        token=secrets.token_urlsafe(32),
        invited_by=current_user.id,
        status=InvitationStatus.PENDING,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)

    # TODO(phase 3): send invitation email via SMTP. For now the token is
    # returned for development; in production, email delivery is required.
    return invitation


@router.get("/invitations", response_model=list[InvitationResponse])
async def list_invitations(
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    membership: OrganizationMember = Depends(require_org_roles(["owner", "admin"])),
):
    """List invitations for the active organization."""
    result = await db.execute(
        select(Invitation)
        .where(Invitation.organization_id == org.id)
        .order_by(Invitation.created_at.desc())
    )
    return result.scalars().all()


@router.post("/invitations/{invitation_id}/revoke", response_model=InvitationResponse)
async def revoke_invitation(
    invitation_id: str,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    membership: OrganizationMember = Depends(require_org_roles(["owner", "admin"])),
):
    """Revoke a pending invitation."""
    result = await db.execute(
        select(Invitation).where(
            Invitation.id == invitation_id,
            Invitation.organization_id == org.id,
        )
    )
    invitation = result.scalar_one_or_none()
    if invitation is None:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(status_code=400, detail="Only pending invitations can be revoked")

    invitation.status = InvitationStatus.REVOKED
    await db.commit()
    await db.refresh(invitation)
    return invitation


# ── Accepting invitations (public, no auth required) ─────────────────────────

@router.post("/invitations/accept", response_model=InviteAcceptResponse)
async def accept_invitation(
    request: InviteAcceptRequest,
    db: AsyncSession = Depends(get_db),
):
    """Accept an invitation by email + token.

    - If the user already exists, they join the org with the invited role.
    - If not, they are registered first (password required).
    """
    email = request.email.lower()
    result = await db.execute(select(Invitation).where(Invitation.token == request.token))
    invitation = result.scalar_one_or_none()
    if invitation is None:
        raise HTTPException(status_code=404, detail="Invalid invitation token")

    if invitation.email.lower() != email:
        raise HTTPException(status_code=400, detail="Email does not match this invitation")

    if invitation.status == InvitationStatus.ACCEPTED:
        raise HTTPException(status_code=400, detail="Invitation already accepted")
    if invitation.status == InvitationStatus.REVOKED:
        raise HTTPException(status_code=400, detail="Invitation has been revoked")
    expires_at = invitation.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)  # DB may store naive UTC
    if expires_at < datetime.now(timezone.utc):
        invitation.status = InvitationStatus.EXPIRED
        await db.commit()
        raise HTTPException(status_code=400, detail="Invitation has expired")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        if not request.password:
            raise HTTPException(status_code=400, detail="A password is required to register for this invitation")
        # New user — register with a generated username from the email prefix
        username = email.split("@")[0][:100]
        result = await db.execute(select(User).where(User.username == username))
        if result.scalar_one_or_none():
            username = f"{username}_{uuid.uuid4().hex[:6]}"
        user = User(
            email=email,
            username=username,
            hashed_password=hash_password(request.password),
        )
        db.add(user)
        await db.flush()

    # Already a member?
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == invitation.organization_id,
            OrganizationMember.user_id == user.id,
        )
    )
    if result.scalar_one_or_none():
        invitation.status = InvitationStatus.ACCEPTED
        invitation.accepted_at = datetime.now(timezone.utc)
        await db.commit()
        raise HTTPException(status_code=400, detail="You are already a member of this organization")

    db.add(OrganizationMember(
        organization_id=invitation.organization_id,
        user_id=user.id,
        role=invitation.role,
    ))
    invitation.status = InvitationStatus.ACCEPTED
    invitation.accepted_at = datetime.now(timezone.utc)

    # Make this the user's active org
    if user.organization_id is None:
        user.organization_id = invitation.organization_id

    await db.commit()

    result = await db.execute(select(Organization).where(Organization.id == invitation.organization_id))
    org = result.scalar_one()
    return InviteAcceptResponse(
        organization_id=org.id,
        organization_name=org.name,
        role=invitation.role,
        user_id=user.id,
    )
