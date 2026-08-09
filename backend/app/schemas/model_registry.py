"""Pydantic schemas for the Model Registry."""

from datetime import datetime
from pydantic import BaseModel, Field


class ModelArtifactResponse(BaseModel):
    id: str
    name: str
    version: str
    algorithm: str
    status: str
    is_active: bool
    trained_at: datetime
    data_rows: int | None
    data_start: str | None
    data_end: str | None
    features_used: str | None
    mae: float | None
    rmse: float | None
    mape: float | None
    wape: float | None
    bias: float | None
    r2: float | None
    evaluation_window_days: int | None
    live_mae: float | None
    live_wape: float | None
    live_bias: float | None
    live_evaluated_at: datetime | None
    degradation_flagged: bool
    model_path: str | None
    hyperparameters: str | None
    promoted_at: datetime | None
    notes: str | None

    model_config = {"from_attributes": True}


class TrainRegistryRequest(BaseModel):
    sample_size: int = Field(50000, ge=100, le=2_000_000)
    test_size: float = Field(0.2, gt=0.05, lt=0.5)
    include_prophet: bool = False
    include_baseline: bool = True
    auto_promote: bool = True
    notes: str | None = None


class TrainRegistryResponse(BaseModel):
    trained: list[ModelArtifactResponse]
    best: ModelArtifactResponse
    promoted: bool
    message: str


class RollbackRequest(BaseModel):
    version: str


class ForecastAccuracyResponse(BaseModel):
    id: str
    product_id: str | None
    store_id: str | None
    horizon_days: int
    eval_points: int
    mae: float | None
    rmse: float | None
    mape: float | None
    wape: float | None
    bias: float | None
    evaluated_at: datetime

    model_config = {"from_attributes": True}


class AccuracySummary(BaseModel):
    """Aggregated accuracy across products/stores for a horizon."""
    horizon_days: int
    mae: float | None
    rmse: float | None
    mape: float | None
    wape: float | None
    bias: float | None
    eval_points: int
    evaluated_at: datetime | None


class RegistryOverview(BaseModel):
    active_model: ModelArtifactResponse | None
    versions: list[ModelArtifactResponse]
    total_versions: int
    degraded: bool
    needs_retrain: bool


