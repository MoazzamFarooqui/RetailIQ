"""Pydantic schemas for Executive Dashboard and Store/Product Intelligence."""

from pydantic import BaseModel


# ── Executive ────────────────────────────────────────────────────────────────
class ExecRisk(BaseModel):
    type: str
    severity: str
    amount: float | None
    message: str


class ExecOpportunity(BaseModel):
    type: str
    item_id: str | None
    units: float | None
    message: str


class ExecAction(BaseModel):
    priority: int
    type: str
    title: str
    detail: str
    severity: str


class ExecutiveOverview(BaseModel):
    total_sales: float
    revenue: float | None
    avg_daily_sales: float
    growth_pct: float | None
    products: int
    stores: int
    days_covered: int
    forecast_accuracy_wape: float | None
    inventory_value: float | None
    overstock_capital: float | None
    potential_savings: float | None
    risks: list[ExecRisk] = []
    opportunities: list[ExecOpportunity] = []
    actions: list[ExecAction] = []
    generated_at: str


# ── Store / Product intelligence ─────────────────────────────────────────────
class StoreIntelligence(BaseModel):
    store_id: str
    total_sales: float | None = None
    revenue: float | None = None
    products: int | None = None
    avg_daily_sales: float | None = None
    growth_pct: float | None = None
    sales_velocity: float | None = None
    best_products: list[dict] = []
    day_of_week_spread_pct: float | None = None
    peak_day: str | None = None
    weather_sensitivity: float | None = None
    days_covered: int | None = None
    error: str | None = None


class ProductIntelligence(BaseModel):
    item_id: str
    category: str | None = None
    total_sales: float | None = None
    revenue: float | None = None
    stores: int | None = None
    avg_daily_sales: float | None = None
    growth_pct: float | None = None
    trend_slope: float | None = None
    top_store: str | None = None
    top_store_pct: float | None = None
    day_of_week_spread_pct: float | None = None
    peak_month: int | None = None
    demand_cv: float | None = None
    stockout_risk: str | None = None
    holiday_sensitivity_pct: float | None = None
    forecast_accuracy: dict | None = None
    days_covered: int | None = None
    error: str | None = None

