"""Executive Dashboard + Store/Product Intelligence API."""

import pandas as pd

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_org
from app.schemas.intelligence import (
    ExecutiveOverview, StoreIntelligence, ProductIntelligence,
)
from app.models.user import User
from app.models.organization import Organization
from app.services.data_service import TenantDataService
from app.services.intelligence_service import IntelligenceService
from app.services.executive_service import ExecutiveService
from app.services.purchase_engine import PurchaseDecisionEngine
from app.services.alert_service import AlertService
from app.models.model_registry import ForecastAccuracy

router = APIRouter()


async def _load_sales(db, org_id):
    df = await TenantDataService.load_sales_df(db, org_id)
    if df.empty:
        raise HTTPException(status_code=404, detail="No data for this organization")
    return df


@router.get("/executive", response_model=ExecutiveOverview)
async def executive_overview(
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
):
    """Get the executive dashboard payload for the org."""
    df = await _load_sales(db, org.id)

    # Financials from the purchase engine
    inv_df = await TenantDataService.load_inventory_df(db, org.id)
    if not inv_df.empty:
        df = df.merge(inv_df, on=["item_id", "store_id"], how="left")
    if "current_stock" not in df.columns or df["current_stock"].isna().all():
        stock = df.groupby(["item_id", "store_id"])["sales"].transform(lambda x: max(x.tail(28).sum() * 1.5, 10))
        df = df.copy()
        df["current_stock"] = stock
    engine = PurchaseDecisionEngine()
    decisions_df = engine.generate_purchase_decisions(df)
    financials = engine.financial_summary(decisions_df)

    # Accuracy summary
    from sqlalchemy import select
    acc_records = (await db.execute(
        select(ForecastAccuracy).where(ForecastAccuracy.organization_id == org.id)
    )).scalars().all()
    accuracy = [{"wape": a.wape} for a in acc_records if a.wape is not None]

    # Alerts (top 5)
    alerts = await AlertService.list_alerts(db, org.id, limit=10)

    return ExecutiveService.executive_overview(df, financials, accuracy, alerts)


@router.get("/stores", response_model=list[StoreIntelligence])
async def all_stores(
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
):
    """Ranked intelligence for all stores."""
    df = await _load_sales(db, org.id)
    return IntelligenceService.all_stores_intelligence(df)


@router.get("/stores/{store_id}", response_model=StoreIntelligence)
async def store_detail(
    store_id: str,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
):
    """Deep-dive intelligence for one store."""
    df = await _load_sales(db, org.id)
    result = IntelligenceService.store_intelligence(df, store_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/products", response_model=list[ProductIntelligence])
async def all_products(
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
):
    """Ranked intelligence for all products."""
    df = await _load_sales(db, org.id)
    return IntelligenceService.all_products_intelligence(df)


@router.get("/products/{item_id}", response_model=ProductIntelligence)
async def product_detail(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
):
    """Deep-dive intelligence for one product."""
    df = await _load_sales(db, org.id)

    # Forecast accuracy for this product. The registry evaluation job stores
    # the *external* SKU (model_registry_service stores row.item_id), so filter
    # by the same value the sales frame uses.
    from sqlalchemy import select
    acc_records = (await db.execute(
        select(ForecastAccuracy).where(
            ForecastAccuracy.organization_id == org.id,
            ForecastAccuracy.product_id == item_id,
        )
    )).scalars().all()
    acc_df = None
    if acc_records:
        acc_df = pd.DataFrame([{
            "product_id": a.product_id, "wape": a.wape, "mae": a.mae,
            "eval_points": a.eval_points,
        } for a in acc_records])

    result = IntelligenceService.product_intelligence(df, item_id, forecast_accuracy=acc_df)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
