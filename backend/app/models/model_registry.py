"""Model Registry — versioned, org-scoped model artifacts with full metadata.

Replaces the flat 'best_model.joblib' with a first-class registry so each
organization can see which model is active, when it was trained, on what
data, with what features, how it performed, and which previous versions can
be rolled back to.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Text, DateTime, ForeignKey, Boolean, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.core.database import Base


class ModelStatus(str, enum.Enum):
    ACTIVE = "active"        # currently serving predictions
    CANDIDATE = "candidate"  # trained, not yet promoted
    ARCHIVED = "archived"    # superseded, kept for rollback
    FAILED = "failed"        # training/evaluation failed
    ROLLED_BACK = "rolled_back"  # was active, rolled back to a previous version


class ModelArtifact(Base):
    """A trained model version in the org's registry."""
    __tablename__ = "model_registry"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    algorithm: Mapped[str] = mapped_column(String(100), nullable=False)  # xgboost | lightgbm | random_forest | prophet | baseline

    # Status
    status: Mapped[ModelStatus] = mapped_column(SAEnum(ModelStatus), default=ModelStatus.CANDIDATE, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Training metadata
    trained_by: Mapped[str] = mapped_column(String(36), nullable=True)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Dataset snapshot (what it was trained on)
    dataset_id: Mapped[str] = mapped_column(String(36), ForeignKey("datasets.id"), nullable=True)
    data_rows: Mapped[int] = mapped_column(Integer, nullable=True)
    data_start: Mapped[str] = mapped_column(String(20), nullable=True)
    data_end: Mapped[str] = mapped_column(String(20), nullable=True)
    features_used: Mapped[Text] = mapped_column(Text, nullable=True)  # JSON list of feature names
    data_snapshot: Mapped[Text] = mapped_column(Text, nullable=True)  # JSON summary of dataset

    # Performance on the held-out evaluation set
    mae: Mapped[float] = mapped_column(Float, nullable=True)
    rmse: Mapped[float] = mapped_column(Float, nullable=True)
    mape: Mapped[float] = mapped_column(Float, nullable=True)
    wape: Mapped[float] = mapped_column(Float, nullable=True)
    bias: Mapped[float] = mapped_column(Float, nullable=True)
    r2: Mapped[float] = mapped_column(Float, nullable=True)
    evaluation_window_days: Mapped[int] = mapped_column(Integer, nullable=True)

    # Post-deployment performance (forecast vs actual on live data)
    live_mae: Mapped[float] = mapped_column(Float, nullable=True)
    live_wape: Mapped[float] = mapped_column(Float, nullable=True)
    live_bias: Mapped[float] = mapped_column(Float, nullable=True)
    live_evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    degradation_flagged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Artifact storage
    model_path: Mapped[str] = mapped_column(String(500), nullable=True)
    hyperparameters: Mapped[Text] = mapped_column(Text, nullable=True)  # JSON

    # Promotion/rollback notes
    promoted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    promoted_by: Mapped[str] = mapped_column(String(36), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<ModelArtifact {self.name} v{self.version} ({self.algorithm}, {self.status.value})>"


class ForecastAccuracy(Base):
    """Forecast-vs-actual accuracy tracking per product/store/horizon.

    Filled by the daily evaluation job as forecasted dates mature.
    """
    __tablename__ = "forecast_accuracy"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    model_id: Mapped[str] = mapped_column(String(36), ForeignKey("model_registry.id"), nullable=True)

    # Grain
    product_id: Mapped[str] = mapped_column(String(100), nullable=True)
    store_id: Mapped[str] = mapped_column(String(100), nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=True)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)  # 7 | 30 | 90

    # Period evaluated (forecasted dates that have now matured)
    eval_start: Mapped[str] = mapped_column(String(20), nullable=True)
    eval_end: Mapped[str] = mapped_column(String(20), nullable=True)
    eval_points: Mapped[int] = mapped_column(Integer, default=0)

    # Metrics
    mae: Mapped[float] = mapped_column(Float, nullable=True)
    rmse: Mapped[float] = mapped_column(Float, nullable=True)
    mape: Mapped[float] = mapped_column(Float, nullable=True)
    wape: Mapped[float] = mapped_column(Float, nullable=True)
    bias: Mapped[float] = mapped_column(Float, nullable=True)  # negative = underforecasting

    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<ForecastAccuracy {self.product_id}@{self.store_id} h{self.horizon_days} WAPE={self.wape:.2f}>"
