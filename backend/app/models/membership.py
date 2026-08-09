"""Organization membership model — user ↔ organization with role.

Also defines the OrganizationRole hierarchy used across the platform for
role-based access control.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.core.database import Base


class OrganizationRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    ANALYST = "analyst"
    VIEWER = "viewer"


# Role hierarchy: index = seniority. Lower numbers are more privileged.
ROLE_RANK = {
    OrganizationRole.OWNER: 0,
    OrganizationRole.ADMIN: 1,
    OrganizationRole.MANAGER: 2,
    OrganizationRole.ANALYST: 3,
    OrganizationRole.VIEWER: 4,
}


class OrganizationMember(Base):
    """A user's membership in an organization with a role."""
    __tablename__ = "organization_members"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", name="uq_member_org_user"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    role: Mapped[OrganizationRole] = mapped_column(SAEnum(OrganizationRole), default=OrganizationRole.VIEWER, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    organization = relationship("Organization", back_populates="members")
    user = relationship("User", back_populates="memberships")

    def __repr__(self) -> str:
        return f"<OrganizationMember {self.user_id}@{self.organization_id} ({self.role.value})>"


