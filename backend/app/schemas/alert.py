"""Pydantic schemas for Smart Alerts."""

from datetime import datetime
from pydantic import BaseModel


class AlertResponse(BaseModel):
    id: str
    organization_id: str
    alert_type: str
    severity: str
    title: str
    message: str
    context: str | None
    is_read: bool
    is_resolved: bool
    resolved_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertCounts(BaseModel):
    total: int
    unread: int
    critical: int
    high: int
