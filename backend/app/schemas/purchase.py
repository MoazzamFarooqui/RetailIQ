"""Pydantic schemas for the Purchase Decision Engine and financial intelligence."""

from pydantic import BaseModel, Field


class PurchaseDecisionItem(BaseModel):
    item_id: str
    store_id: str
    avg_daily_demand: float
    demand_std: float
    safety_stock: float
    reorder_point: float
    eoq: float
    recommended_order_qty: float
    order_today: bool
    order_date: str
    arrival_date: str
    stockout_in_days: float | None
    stockout_date: str | None
    status: str
    days_of_stock: float
    unit_price: float
    inventory_value: float
    excess_units: float
    overstock_capital: float
    stockout_revenue_loss: float
    carrying_cost: float
    inventory_turnover: float | None
    days_of_inventory: float
    potential_savings: float


class FinancialSummary(BaseModel):
    total_inventory_value: float
    total_overstock_capital: float
    total_stockout_loss_risk: float
    total_carrying_cost: float
    total_potential_savings: float
    total_recommended_order_value: float
    avg_inventory_turnover: float | None
    avg_days_of_inventory: float
    items_to_reorder: int


class PurchaseDecisionsRequest(BaseModel):
    service_level: float = Field(0.95, ge=0.5, le=0.999)
    lead_time_days: int = Field(7, ge=1, le=365)
    demand_multiplier: float | None = Field(None, ge=0.1, le=10)
    sample_size: int = Field(2000, ge=1, le=50000)
    include_financials: bool = True


class PurchaseDecisionsResponse(BaseModel):
    decisions: list[PurchaseDecisionItem]
    total_count: int
    financials: FinancialSummary | None = None


class WhatIfRequest(BaseModel):
    """A what-if scenario: change one or more knobs and see the impact."""
    demand_growth: float | None = Field(None, ge=-0.5, le=1.0, description="e.g. 0.1 = +10% demand")
    lead_time_days: int | None = Field(None, ge=1, le=365)
    service_level: float | None = Field(None, ge=0.5, le=0.999)
    holding_cost_rate: float | None = Field(None, ge=0.0, le=1.0)
    order_cost: float | None = Field(None, ge=0)
    unit_cost: float | None = Field(None, ge=0)
    demand_multiplier: float | None = Field(None, ge=0.1, le=10)
    sample_size: int = Field(2000, ge=1, le=50000)


class WhatIfResponse(BaseModel):
    """Baseline vs scenario, side by side."""
    baseline_financials: FinancialSummary
    scenario_financials: FinancialSummary
    scenario: dict  # the parameters that changed
    deltas: dict  # e.g. {"total_inventory_value": -5000, "items_to_reorder": -12}
    top_changes: list[dict]  # items with the biggest absolute change
