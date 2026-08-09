"""multi tenant foundation

Revision ID: 0001_multi_tenant_foundation
Revises:
Create Date: 2026-08-03

Introduces the RetailIQ v3 tenancy layer:
- organizations, organization_members, invitations tables
- products, stores, sales (tenant-scoped fact table)
- organization_id columns on users and all existing data tables
- users.organization_id (preferred/active org)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "0001_multi_tenant_foundation"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── New tables ─────────────────────────────────────────────────────────
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.Enum("active", "suspended", "deleted", name="orgstatus"), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("default_service_level", sa.Float(), nullable=False),
        sa.Column("default_lead_time_days", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "organization_members",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.Enum("owner", "admin", "manager", "analyst", "viewer", name="organizationrole"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_member_org_user"),
    )
    op.create_index("ix_organization_members_organization_id", "organization_members", ["organization_id"])
    op.create_index("ix_organization_members_user_id", "organization_members", ["user_id"])

    op.create_table(
        "invitations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("token", sa.String(length=100), nullable=False),
        sa.Column("invited_by", sa.String(length=36), nullable=False),
        sa.Column("status", sa.Enum("pending", "accepted", "revoked", "expired", name="invitationstatus"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index("ix_invitations_organization_id", "invitations", ["organization_id"])
    op.create_index("ix_invitations_email", "invitations", ["email"])

    op.create_table(
        "products",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("sku", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("unit_cost", sa.Float(), nullable=True),
        sa.Column("unit_price", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_products_organization_id", "products", ["organization_id"])
    op.create_index("ix_products_sku", "products", ["sku"])
    op.create_index("ix_products_category", "products", ["category"])

    op.create_table(
        "stores",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("store_code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("region", sa.String(length=100), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("opening_date", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stores_organization_id", "stores", ["organization_id"])
    op.create_index("ix_stores_store_code", "stores", ["store_code"])

    op.create_table(
        "sales",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("product_id", sa.String(length=36), nullable=False),
        sa.Column("store_id", sa.String(length=36), nullable=False),
        sa.Column("sale_date", sa.Date(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("revenue", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "sale_date", "product_id", "store_id", name="uq_sale_org_date_product_store"),
    )
    op.create_index("ix_sales_org_date", "sales", ["organization_id", "sale_date"])
    op.create_index("ix_sales_org_product", "sales", ["organization_id", "product_id"])
    op.create_index("ix_sales_org_store", "sales", ["organization_id", "store_id"])
    op.create_index("ix_sales_organization_id", "sales", ["organization_id"])

    op.create_table(
        "inventory_levels",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("product_id", sa.String(length=36), nullable=False),
        sa.Column("store_id", sa.String(length=36), nullable=False),
        sa.Column("quantity_on_hand", sa.Float(), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "product_id", "store_id", name="uq_inventory_org_product_store"),
    )
    op.create_index("ix_inventory_levels_organization_id", "inventory_levels", ["organization_id"])
    op.create_index("ix_inventory_org_store", "inventory_levels", ["organization_id", "store_id"])
    op.create_index("ix_inventory_org_product", "inventory_levels", ["organization_id", "product_id"])

    op.create_table(
        "import_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("source_type", sa.Enum("csv", "excel", "api", "webhook", "scheduled", name="importsourcetype"), nullable=False),
        sa.Column("source", sa.String(length=500), nullable=True),
        sa.Column("status", sa.Enum("pending", "running", "succeeded", "failed", name="importjobstatus"), nullable=False),
        sa.Column("rows_received", sa.Integer(), nullable=False),
        sa.Column("rows_imported", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_import_jobs_organization_id", "import_jobs", ["organization_id"])

    op.create_table(
        "webhook_sources",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("api_key", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("api_key"),
    )
    op.create_index("ix_webhook_sources_organization_id", "webhook_sources", ["organization_id"])

    op.create_table(
        "model_registry",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("algorithm", sa.String(length=100), nullable=False),
        sa.Column("status", sa.Enum("active", "candidate", "archived", "failed", "rolled_back", name="modelstatus"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("trained_by", sa.String(length=36), nullable=True),
        sa.Column("trained_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dataset_id", sa.String(length=36), nullable=True),
        sa.Column("data_rows", sa.Integer(), nullable=True),
        sa.Column("data_start", sa.String(length=20), nullable=True),
        sa.Column("data_end", sa.String(length=20), nullable=True),
        sa.Column("features_used", sa.Text(), nullable=True),
        sa.Column("data_snapshot", sa.Text(), nullable=True),
        sa.Column("mae", sa.Float(), nullable=True),
        sa.Column("rmse", sa.Float(), nullable=True),
        sa.Column("mape", sa.Float(), nullable=True),
        sa.Column("wape", sa.Float(), nullable=True),
        sa.Column("bias", sa.Float(), nullable=True),
        sa.Column("r2", sa.Float(), nullable=True),
        sa.Column("evaluation_window_days", sa.Integer(), nullable=True),
        sa.Column("live_mae", sa.Float(), nullable=True),
        sa.Column("live_wape", sa.Float(), nullable=True),
        sa.Column("live_bias", sa.Float(), nullable=True),
        sa.Column("live_evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("degradation_flagged", sa.Boolean(), nullable=False),
        sa.Column("model_path", sa.String(length=500), nullable=True),
        sa.Column("hyperparameters", sa.Text(), nullable=True),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("promoted_by", sa.String(length=36), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_model_registry_organization_id", "model_registry", ["organization_id"])

    op.create_table(
        "forecast_accuracy",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("model_id", sa.String(length=36), nullable=True),
        sa.Column("product_id", sa.String(length=100), nullable=True),
        sa.Column("store_id", sa.String(length=100), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("eval_start", sa.String(length=20), nullable=True),
        sa.Column("eval_end", sa.String(length=20), nullable=True),
        sa.Column("eval_points", sa.Integer(), nullable=False),
        sa.Column("mae", sa.Float(), nullable=True),
        sa.Column("rmse", sa.Float(), nullable=True),
        sa.Column("mape", sa.Float(), nullable=True),
        sa.Column("wape", sa.Float(), nullable=True),
        sa.Column("bias", sa.Float(), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["model_id"], ["model_registry.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_forecast_accuracy_organization_id", "forecast_accuracy", ["organization_id"])

    op.create_table(
        "alerts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("alert_type", sa.Enum("stockout_risk", "overstock", "demand_spike", "demand_drop", "forecast_degradation", "upcoming_holiday", "store_performance", "data_anomaly", "low_stock", "inventory_value", name="alerttype"), nullable=False),
        sa.Column("severity", sa.Enum("critical", "high", "medium", "low", "info", name="alertseverity"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("is_resolved", sa.Boolean(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dedup_key", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alerts_organization_id", "alerts", ["organization_id"])
    op.create_index("ix_alerts_alert_type", "alerts", ["alert_type"])
    op.create_index("ix_alerts_dedup_key", "alerts", ["dedup_key"])

    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("alert_id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("channel", sa.Enum("in_app", "email", name="notificationchannel"), nullable=False),
        sa.Column("recipient", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notification_deliveries_alert_id", "notification_deliveries", ["alert_id"])
    op.create_index("ix_notification_deliveries_organization_id", "notification_deliveries", ["organization_id"])

    op.create_table(
        "advisor_conversations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("grounded", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_advisor_conversations_organization_id", "advisor_conversations", ["organization_id"])
    op.create_index("ix_advisor_conversations_user_id", "advisor_conversations", ["user_id"])

    # ── Existing tables: add organization_id ───────────────────────────────
    op.add_column("users", sa.Column("organization_id", sa.String(length=36), nullable=True))
    op.create_index("ix_users_organization_id", "users", ["organization_id"])

    op.add_column("datasets", sa.Column("organization_id", sa.String(length=36), nullable=False, server_default=""))
    op.create_index("ix_datasets_organization_id", "datasets", ["organization_id"])

    op.add_column("forecast_headers", sa.Column("organization_id", sa.String(length=36), nullable=False, server_default=""))
    op.create_index("ix_forecast_headers_organization_id", "forecast_headers", ["organization_id"])

    op.add_column("forecasts", sa.Column("organization_id", sa.String(length=36), nullable=False, server_default=""))
    op.create_index("ix_forecasts_organization_id", "forecasts", ["organization_id"])

    op.add_column("inventory_recommendations", sa.Column("organization_id", sa.String(length=36), nullable=False, server_default=""))
    op.create_index("ix_inventory_recommendations_organization_id", "inventory_recommendations", ["organization_id"])

    op.add_column("model_history", sa.Column("organization_id", sa.String(length=36), nullable=False, server_default=""))
    op.create_index("ix_model_history_organization_id", "model_history", ["organization_id"])

    op.add_column("business_insights", sa.Column("organization_id", sa.String(length=36), nullable=False, server_default=""))
    op.create_index("ix_business_insights_organization_id", "business_insights", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_business_insights_organization_id", table_name="business_insights")
    op.drop_column("business_insights", "organization_id")

    op.drop_index("ix_model_history_organization_id", table_name="model_history")
    op.drop_column("model_history", "organization_id")

    op.drop_index("ix_inventory_recommendations_organization_id", table_name="inventory_recommendations")
    op.drop_column("inventory_recommendations", "organization_id")

    op.drop_index("ix_forecasts_organization_id", table_name="forecasts")
    op.drop_column("forecasts", "organization_id")

    op.drop_index("ix_forecast_headers_organization_id", table_name="forecast_headers")
    op.drop_column("forecast_headers", "organization_id")

    op.drop_index("ix_datasets_organization_id", table_name="datasets")
    op.drop_column("datasets", "organization_id")

    op.drop_index("ix_users_organization_id", table_name="users")
    op.drop_column("users", "organization_id")

    op.drop_table("advisor_conversations")
    op.drop_table("notification_deliveries")
    op.drop_table("alerts")
    op.drop_table("forecast_accuracy")
    op.drop_table("model_registry")
    op.drop_table("webhook_sources")
    op.drop_table("import_jobs")
    op.drop_table("inventory_levels")
    op.drop_table("sales")
    op.drop_table("stores")
    op.drop_table("products")
    op.drop_table("invitations")
    op.drop_table("organization_members")
    op.drop_table("organizations")


