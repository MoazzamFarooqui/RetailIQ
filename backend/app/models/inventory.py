"""Inventory recommendation model."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class InventoryRecommendation(Base):
    """Inventory optimization result for an item-store combination."""
    __tablename__ = "inventory_recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    dataset_id: Mapped[str] = mapped_column(String(36), ForeignKey("datasets.id"), nullable=True)
    forecast_id: Mapped[str] = mapped_column(String(36), ForeignKey("forecast_headers.id"), nullable=True)
    item_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    store_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    current_stock: Mapped[float] = mapped_column(Float, default=0)
    avg_daily_demand: Mapped[float] = mapped_column(Float, nullable=True)
    demand_std: Mapped[float] = mapped_column(Float, nullable=True)
    safety_stock: Mapped[float] = mapped_column(Float, nullable=True)
    reorder_point: Mapped[float] = mapped_column(Float, nullable=True)
    eoq: Mapped[float] = mapped_column(Float, nullable=True)
    recommended_order_qty: Mapped[float] = mapped_column(Float, nullable=True)
    stockout_in_days: Mapped[float] = mapped_column(Float, nullable=True)
    stockout_date: Mapped[str] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=True)
    days_of_stock: Mapped[float] = mapped_column(Float, nullable=True)
    demand_multiplier_used: Mapped[float] = mapped_column(Float, default=1.0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<InventoryRecommendation {self.item_id}@{self.store_id}: {self.status}>"

