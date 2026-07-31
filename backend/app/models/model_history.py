"""Model training history model."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ModelHistory(Base):
    """Tracks each model training run and its performance metrics."""
    __tablename__ = "model_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id: Mapped[str] = mapped_column(String(36), ForeignKey("datasets.id"), nullable=True)
    model_type: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=True)

    # Metrics
    mae: Mapped[float] = mapped_column(Float, nullable=True)
    rmse: Mapped[float] = mapped_column(Float, nullable=True)
    mape: Mapped[float] = mapped_column(Float, nullable=True)
    r2: Mapped[float] = mapped_column(Float, nullable=True)
    training_time_sec: Mapped[float] = mapped_column(Float, nullable=True)
    feature_count: Mapped[int] = mapped_column(Integer, nullable=True)

    # Hyperparameters (stored as JSON string)
    hyperparameters: Mapped[str] = mapped_column(Text, nullable=True)

    is_best: Mapped[bool] = mapped_column(Boolean, default=False)
    model_path: Mapped[str] = mapped_column(String(500), nullable=True)

    created_by: Mapped[str] = mapped_column(String(36), nullable=True)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<ModelHistory {self.model_type} (MAE={self.mae:.2f})>"
