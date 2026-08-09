"""Organization (tenant) models — the root of RetailIQ multi-tenancy.

Every business using the platform is an Organization. All data models carry
an organization_id column; all data access flows through the active
organization, so tenants are fully isolated from one another.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, Enum as SAEnum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.core.database import Base


class OrgStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class Organization(Base):
    """A tenant: one business using the RetailIQ platform."""
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[OrgStatus] = mapped_column(SAEnum(OrgStatus), default=OrgStatus.ACTIVE, nullable=False)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False)

    # Defaults for inventory optimization (can be overridden per org later)
    default_service_level: Mapped[float] = mapped_column(default=0.95, nullable=False)
    default_lead_time_days: Mapped[int] = mapped_column(default=7, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    members = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Organization {self.name} ({self.slug})>"

