"""Pydantic schemas for model training endpoints."""

from datetime import datetime
from pydantic import BaseModel, Field


class TrainRequest(BaseModel):
    sample_size: int = Field(default=50000, ge=1000, le=500000)
    test_size: float = Field(default=0.2, ge=0.1, le=0.4)
    include_prophet: bool = False
    include_baseline: bool = True
    run_async: bool = True


class ModelMetrics(BaseModel):
    model_type: str
    mae: float | None
    rmse: float | None
    mape: float | None
    r2: float | None
    training_time_sec: float | None
    is_best: bool = False

    model_config = {"from_attributes": True, "protected_namespaces": ()}


class ModelHistoryRecord(BaseModel):
    id: str
    model_type: str
    model_version: str | None
    mae: float | None
    rmse: float | None
    mape: float | None
    r2: float | None
    training_time_sec: float | None
    feature_count: int | None
    is_best: bool
    trained_at: datetime

    model_config = {"from_attributes": True, "protected_namespaces": ()}


class ModelComparisonResponse(BaseModel):
    models: list[ModelMetrics]
    best_model: str | None


class FeatureImportance(BaseModel):
    feature: str
    importance: float


class TrainResponse(BaseModel):
    task_id: str | None = None
    message: str
    is_async: bool = True


