"""User invitation model — invites new members into an organization."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Enum as SAEnum, Boolean
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.core.database import Base


class InvitationStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REVOKED = "revoked"
    EXPIRED = "expired"


class Invitation(Base):
    """An invitation for a user to join an organization."""
    __tablename__ = "invitations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), default="viewer", nullable=False)
    token: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    invited_by: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[InvitationStatus] = mapped_column(SAEnum(InvitationStatus), default=InvitationStatus.PENDING, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<Invitation {self.email} → {self.organization_id} ({self.status.value})>"

