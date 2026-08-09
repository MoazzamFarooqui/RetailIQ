"""Pydantic schemas for insights endpoints."""

from datetime import datetime
from pydantic import BaseModel


class InsightItem(BaseModel):
    id: str
    insight_type: str
    insight_text: str
    category: str | None
    severity: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SeasonAdvice(BaseModel):
    current_season: str
    season_emoji: str
    season_advice: str
    high_demand_products: list[str]
    low_demand_products: list[str]
    pre_holiday_window: dict | None = None
    upcoming_holidays: list[dict] = []


class WeatherContext(BaseModel):
    temperature_c: float
    feels_like_c: float
    humidity_pct: float
    weather_condition: str
    season: str
    season_emoji: str
    holiday_name: str | None
    pre_holiday_window: dict | None = None
    demand_multiplier: float


