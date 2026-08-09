"""Inventory stock level model — real stock levels, not heuristics.

The v3 purchase decision engine needs *actual* on-hand stock per product and
store. Rows are upserted on ingestion; a history trail is kept via
inventory_movements (Phase 2 financials can consume it).
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Float, Date, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class InventoryLevel(Base):
    """Current on-hand stock for a product at a store, as of a snapshot date."""
    __tablename__ = "inventory_levels"
    __table_args__ = (
        UniqueConstraint("organization_id", "product_id", "store_id", name="uq_inventory_org_product_store"),
        Index("ix_inventory_org_store", "organization_id", "store_id"),
        Index("ix_inventory_org_product", "organization_id", "product_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("products.id"), nullable=False)
    store_id: Mapped[str] = mapped_column(String(36), ForeignKey("stores.id"), nullable=False)
    quantity_on_hand: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    snapshot_date: Mapped[datetime] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<InventoryLevel {self.product_id}@{self.store_id}: {self.quantity_on_hand}>"
