"""Forecast models — header metadata and individual forecast records."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Date, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ForecastHeader(Base):
    """Metadata for a forecast run."""
    __tablename__ = "forecast_headers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    dataset_id: Mapped[str] = mapped_column(String(36), ForeignKey("datasets.id"), nullable=True)
    model_type: Mapped[str] = mapped_column(String(100), nullable=False)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    item_count: Mapped[int] = mapped_column(Integer, nullable=True)
    store_count: Mapped[int] = mapped_column(Integer, nullable=True)
    total_forecast: Mapped[float] = mapped_column(Float, nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationship
    details = relationship("Forecast", back_populates="header", lazy="selectin")

    def __repr__(self) -> str:
        return f"<ForecastHeader {self.model_type} {self.horizon_days}d>"


class Forecast(Base):
    """Individual forecast record for an item-store-date combination."""
    __tablename__ = "forecasts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    header_id: Mapped[str] = mapped_column(String(36), ForeignKey("forecast_headers.id"), nullable=False)
    dataset_id: Mapped[str] = mapped_column(String(36), ForeignKey("datasets.id"), nullable=True)
    item_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    store_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    forecast_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    predicted_sales: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    header = relationship("ForecastHeader", back_populates="details")

    def __repr__(self) -> str:
        return f"<Forecast {self.item_id}@{self.store_id} {self.forecast_date}: {self.predicted_sales:.2f}>"


