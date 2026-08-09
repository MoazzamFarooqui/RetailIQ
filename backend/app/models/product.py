"""Product model — org-scoped product catalog for RetailIQ v3.

Replaces the item_id strings inside flat CSVs with a real, tenant-scoped
relational catalog that Store/Product Intelligence, forecasting, and the
inventory purchase engine can query.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Product(Base):
    """A sellable product belonging to one organization."""
    __tablename__ = "products"
    __table_args__ = ({"mysql_charset": "utf8mb4"},)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    unit_cost: Mapped[float] = mapped_column(Float, nullable=True)
    unit_price: Mapped[float] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<Product {self.sku} ({self.name})>"

