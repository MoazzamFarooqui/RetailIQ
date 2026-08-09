"""Data ingestion models — import jobs and webhook sources.

v3 moves toward automated data integration: scheduled imports and
API/webhook endpoints that push new sales into RetailIQ continuously.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.core.database import Base


class ImportSourceType(str, enum.Enum):
    CSV = "csv"
    EXCEL = "excel"
    API = "api"
    WEBHOOK = "webhook"
    SCHEDULED = "scheduled"


class ImportJobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ImportJob(Base):
    """A single data import run into an organization."""
    __tablename__ = "import_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    source_type: Mapped[ImportSourceType] = mapped_column(SAEnum(ImportSourceType), default=ImportSourceType.CSV)
    source: Mapped[str] = mapped_column(String(500), nullable=True)
    status: Mapped[ImportJobStatus] = mapped_column(SAEnum(ImportJobStatus), default=ImportJobStatus.PENDING)
    rows_received: Mapped[int] = mapped_column(Integer, default=0)
    rows_imported: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<ImportJob {self.source_type.value} ({self.status.value}) rows={self.rows_imported}>"


class WebhookSource(Base):
    """A registered integration that can push data into an organization."""
    __tablename__ = "webhook_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<WebhookSource {self.name} ({'active' if self.is_active else 'inactive'})>"
