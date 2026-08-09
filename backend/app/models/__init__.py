"""Model registry — importing every model here registers it with Base.metadata
so Alembic autogenerate and init_db see the full schema.
"""

from app.models.user import User, UserRole
from app.models.organization import Organization, OrgStatus
from app.models.membership import OrganizationMember, OrganizationRole, ROLE_RANK
from app.models.invitation import Invitation, InvitationStatus
from app.models.dataset import Dataset, DatasetStatus
from app.models.product import Product
from app.models.store import Store
from app.models.sale import Sale
from app.models.inventory_level import InventoryLevel
from app.models.ingestion import ImportJob, ImportJobStatus, ImportSourceType, WebhookSource
from app.models.model_registry import ModelArtifact, ModelStatus, ForecastAccuracy
from app.models.alert import Alert, AlertType, AlertSeverity, NotificationDelivery, NotificationChannel
from app.models.advisor_conversation import AdvisorConversation
from app.models.forecast import ForecastHeader, Forecast
from app.models.inventory import InventoryRecommendation
from app.models.model_history import ModelHistory
from app.models.insight import BusinessInsight

__all__ = [
    "User",
    "UserRole",
    "Organization",
    "OrgStatus",
    "OrganizationMember",
    "OrganizationRole",
    "ROLE_RANK",
    "Invitation",
    "InvitationStatus",
    "Dataset",
    "DatasetStatus",
    "Product",
    "Store",
    "Sale",
    "InventoryLevel",
    "ImportJob",
    "ImportJobStatus",
    "ImportSourceType",
    "WebhookSource",
    "ModelArtifact",
    "ModelStatus",
    "ForecastAccuracy",
    "Alert",
    "AlertType",
    "AlertSeverity",
    "NotificationDelivery",
    "NotificationChannel",
    "AdvisorConversation",
    "ForecastHeader",
    "Forecast",
    "InventoryRecommendation",
    "ModelHistory",
    "BusinessInsight",
]
