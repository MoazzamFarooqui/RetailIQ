"""Smart Alert model — proactive notifications for events that need attention."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, Enum as SAEnum, Boolean, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.core.database import Base


class AlertSeverity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertType(str, enum.Enum):
    STOCKOUT_RISK = "stockout_risk"
    OVERSTOCK = "overstock"
    DEMAND_SPIKE = "demand_spike"
    DEMAND_DROP = "demand_drop"
    FORECAST_DEGRADATION = "forecast_degradation"
    UPCOMING_HOLIDAY = "upcoming_holiday"
    STORE_PERFORMANCE = "store_performance"
    DATA_ANOMALY = "data_anomaly"
    LOW_STOCK = "low_stock"
    INVENTORY_VALUE = "inventory_value"


class Alert(Base):
    """A detected event requiring attention, with delivery status."""
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    alert_type: Mapped[AlertType] = mapped_column(SAEnum(AlertType), nullable=False, index=True)
    severity: Mapped[AlertSeverity] = mapped_column(SAEnum(AlertSeverity), default=AlertSeverity.INFO)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Context for the UI (JSON): product_id, store_id, value, threshold, etc.
    context: Mapped[str] = mapped_column(Text, nullable=True)

    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Dedup key so the daily detector doesn't create the same alert twice
    dedup_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<Alert {self.alert_type.value} [{self.severity.value}] {self.title}>"


class NotificationChannel(str, enum.Enum):
    IN_APP = "in_app"
    EMAIL = "email"


class NotificationDelivery(Base):
    """Delivery record — which channel an alert was sent to, and whether it succeeded."""
    __tablename__ = "notification_deliveries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_id: Mapped[str] = mapped_column(String(36), ForeignKey("alerts.id"), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    channel: Mapped[NotificationChannel] = mapped_column(SAEnum(NotificationChannel), nullable=False)
    recipient: Mapped[str] = mapped_column(String(255), nullable=True)  # user id or email
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | sent | failed
    error: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<NotificationDelivery {self.channel.value} → {self.recipient}: {self.status}>"

