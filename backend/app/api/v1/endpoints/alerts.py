"""Smart Alerts API — list, read, resolve, trigger detection."""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_org, require_org_roles
from app.schemas.alert import AlertResponse, AlertCounts
from app.models.user import User
from app.models.organization import Organization
from app.models.alert import Alert
from app.services.alert_service import AlertService
from app.services.data_service import TenantDataService
from app.services.purchase_engine import PurchaseDecisionEngine
from app.services.model_registry_service import ModelRegistryService

router = APIRouter()


@router.get("", response_model=list[AlertResponse])
async def list_alerts(
    limit: int = 50,
    include_resolved: bool = False,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
):
    alerts = await AlertService.list_alerts(db, org.id, limit=limit, include_resolved=include_resolved)
    return alerts


@router.get("/counts", response_model=AlertCounts)
async def alert_counts(
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
):
    alerts = await AlertService.list_alerts(db, org.id, limit=500)
    return AlertCounts(
        total=len(alerts),
        unread=sum(1 for a in alerts if not a.is_read),
        critical=sum(1 for a in alerts if a.severity.value == "critical" and not a.is_resolved),
        high=sum(1 for a in alerts if a.severity.value == "high" and not a.is_resolved),
    )


@router.post("/{alert_id}/read", response_model=AlertResponse)
async def mark_read(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
):
    alert = await AlertService.mark_read(db, org.id, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
):
    alert = await AlertService.resolve(db, org.id, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.post("/detect", status_code=202)
async def trigger_detection(
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(require_org_roles(["owner", "admin", "manager", "analyst"])),
):
    """Manually run all alert detectors for the org."""
    sales_df = await TenantDataService.load_sales_df(db, org.id)

    decisions_df = None
    if not sales_df.empty:
        inv_df = await TenantDataService.load_inventory_df(db, org.id)
        if not inv_df.empty:
            sales_df = sales_df.merge(inv_df, on=["item_id", "store_id"], how="left")
        if "current_stock" not in sales_df.columns or sales_df["current_stock"].isna().all():
            stock = sales_df.groupby(["item_id", "store_id"])["sales"].transform(lambda x: max(x.tail(28).sum() * 1.5, 10))
            sales_df = sales_df.copy()
            sales_df["current_stock"] = stock
        engine = PurchaseDecisionEngine()
        decisions_df = engine.generate_purchase_decisions(sales_df)

    active_model = await ModelRegistryService.get_active(db, org.id)
    counts = await AlertService.run_all_detectors(db, org.id, decisions_df, sales_df, active_model)
    await db.commit()
    return {"status": "ok", "created": counts}
