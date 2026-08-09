"""Pydantic schemas for inventory optimization endpoints."""

from pydantic import BaseModel, Field


class InventoryRequest(BaseModel):
    service_level: float = Field(default=0.95, ge=0.8, le=0.999)
    lead_time_days: int = Field(default=7, ge=1, le=60)
    excess_threshold_days: int = Field(default=60, ge=30, le=365)
    demand_multiplier: float | None = Field(default=None)
    sample_size: int = Field(default=2000, ge=100, le=50000)


class InventoryRecommendationItem(BaseModel):
    item_id: str
    store_id: str
    current_stock: float
    avg_daily_demand: float
    demand_std: float
    safety_stock: float
    reorder_point: float
    eoq: float
    recommended_order_qty: float
    status: str
    days_of_stock: float
    stockout_in_days: float | None
    stockout_date: str | None
    demand_multiplier_used: float

    model_config = {"from_attributes": True}


class InventoryStatusResponse(BaseModel):
    total_items: int
    items_ok: int
    items_low: int
    items_critical: int
    items_excess: int
    avg_days_of_stock: float
    total_safety_stock: float
    total_recommended_orders: float
    items_need_reorder: int


class StockoutPrediction(BaseModel):
    item_id: str
    store_id: str
    current_stock: float
    avg_daily_demand: float
    days_remaining: float
    predicted_stockout_date: str
    is_critical: bool


class OverstockItem(BaseModel):
    item_id: str
    store_id: str
    current_stock: float
    avg_daily_demand: float
    days_of_stock: float
    excess_units: float
    reason: str


