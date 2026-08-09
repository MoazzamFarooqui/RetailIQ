"""Dataset model — tracks uploaded CSV files and their processing status."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Text, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.core.database import Base


class DatasetStatus(str, enum.Enum):
    PENDING = "pending"
    UPLOADED = "uploaded"
    VALIDATING = "validating"
    CLEANED = "cleaned"
    PROCESSED = "processed"
    ERROR = "error"


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    table_name: Mapped[str] = mapped_column(String(255), nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, nullable=True)
    column_count: Mapped[int] = mapped_column(Integer, nullable=True)
    file_size_kb: Mapped[float] = mapped_column(Float, nullable=True)
    status: Mapped[DatasetStatus] = mapped_column(SAEnum(DatasetStatus), default=DatasetStatus.PENDING)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<Dataset {self.original_filename} ({self.status.value})>"

