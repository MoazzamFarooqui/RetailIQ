"""Sales data model — the tenant-scoped daily sales fact table.

Replaces the shared flat CSV. Every row belongs to one organization and
links to its Product and Store; forecast and inventory services read from
here instead of the filesystem.
"""

import uuid
from datetime import datetime, date, timezone
from sqlalchemy import String, Float, Date, DateTime, ForeignKey, Index, BigInteger, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Sale(Base):
    """One day of sales for one product at one store."""
    __tablename__ = "sales"
    __table_args__ = (
        # Unique per org per day per product per store — enables idempotent upserts
        UniqueConstraint("organization_id", "sale_date", "product_id", "store_id", name="uq_sale_org_date_product_store"),
        Index("ix_sales_org_date", "organization_id", "sale_date"),
        Index("ix_sales_org_product", "organization_id", "product_id"),
        Index("ix_sales_org_store", "organization_id", "store_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("products.id"), nullable=False)
    store_id: Mapped[str] = mapped_column(String(36), ForeignKey("stores.id"), nullable=False)
    sale_date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    revenue: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<Sale {self.product_id}@{self.store_id} {self.sale_date}: {self.quantity}>"


