"""Data Health Center API — quality assessment and anomaly detection."""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_org
from app.schemas.data_health import DataHealthReport, AnomalyReport, Anomaly
from app.models.user import User
from app.models.organization import Organization
from app.services.data_service import TenantDataService
from app.services.data_health_service import DataHealthService

router = APIRouter()


@router.get("/report", response_model=DataHealthReport)
async def health_report(
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
):
    """Get the org's data quality score and per-check breakdown."""
    df = await TenantDataService.load_sales_df(db, org.id)
    if df.empty:
        raise HTTPException(status_code=404, detail="No data for this organization")
    return DataHealthService.assess(df)


@router.get("/anomalies", response_model=AnomalyReport)
async def anomalies(
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
):
    """Detect sales anomalies (spikes, drops, gaps) and suspicious transactions."""
    df = await TenantDataService.load_sales_df(db, org.id)
    if df.empty:
        raise HTTPException(status_code=404, detail="No data for this organization")

    sales_anomalies = DataHealthService.detect_anomalies(df)
    txn_anomalies = await DataHealthService.detect_transaction_anomalies(db, org.id)

    all_anomalies = sales_anomalies + txn_anomalies
    return AnomalyReport(anomalies=[Anomaly(**a) for a in all_anomalies], total=len(all_anomalies))

