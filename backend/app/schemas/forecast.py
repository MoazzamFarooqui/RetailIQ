"""Pydantic schemas for forecast endpoints."""

from datetime import datetime, date
from pydantic import BaseModel, Field


class ForecastGenerateRequest(BaseModel):
    item_id: str = Field(..., example="FOODS_3_090")
    store_id: str = Field(..., example="CA_1")
    horizon_days: int = Field(default=30, ge=7, le=365, example=30)
    model_type: str | None = Field(default=None, example="random_forest")
    include_weather: bool = True
    include_holidays: bool = True

    model_config = {"protected_namespaces": ()}


class ForecastRecord(BaseModel):
    id: str
    header_id: str
    item_id: str
    store_id: str
    forecast_date: date
    predicted_sales: float

    model_config = {"from_attributes": True}


class ForecastHeaderResponse(BaseModel):
    id: str
    dataset_id: str | None
    model_type: str
    horizon_days: int
    item_count: int | None
    store_count: int | None
    total_forecast: float | None
    created_by: str | None
    created_at: datetime

    model_config = {"from_attributes": True, "protected_namespaces": ()}


class ForecastDetailResponse(ForecastHeaderResponse):
    details: list[ForecastRecord] = []


class ForecastHistoryResponse(BaseModel):
    headers: list[ForecastHeaderResponse]
    total: int
