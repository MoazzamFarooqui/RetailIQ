"""Pydantic schemas for the Data Health Center."""

from pydantic import BaseModel


class HealthCheck(BaseModel):
    check: str
    status: str  # pass | warn | fail
    detail: str


class DataHealthReport(BaseModel):
    score: int
    checks: list[HealthCheck]
    total_rows: int
    assessed_at: str


class Anomaly(BaseModel):
    type: str
    date: str
    sales: float | None = None
    expected: float | None = None
    z_score: float | None = None
    severity: str
    product_id: str | None = None
    store_id: str | None = None
    quantity: float | None = None
    revenue: float | None = None


class AnomalyReport(BaseModel):
    anomalies: list[Anomaly]
    total: int
