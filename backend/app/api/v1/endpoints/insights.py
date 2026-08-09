"""AI Business insights endpoints (org-scoped)."""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_org
from app.schemas.insight import InsightItem, SeasonAdvice
from app.models.user import User
from app.models.organization import Organization
from app.models.insight import BusinessInsight
from app.services.insights_engine import InsightsEngine
from app.services.data_service import TenantDataService
from app.services.weather_service import WeatherService
from app.services.holiday_service import HolidayService

router = APIRouter()


@router.post("/generate", response_model=list[InsightItem])
async def generate_insights(
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
):
    """Generate AI-driven business insights from the org's sales data."""
    df = await TenantDataService.load_sales_df(db, org.id)
    if df.empty:
        raise HTTPException(status_code=404, detail="No data for this organization. Upload or ingest data first.")

    # Run insights engine
    engine = InsightsEngine()
    insights = engine.analyze(df)

    # Save to DB (org-scoped)
    saved = []
    for insight in insights:
        record = BusinessInsight(
            organization_id=org.id,
            insight_type=insight["insight_type"],
            insight_text=insight["insight_text"],
            category=insight["category"],
            severity=insight["severity"],
        )
        db.add(record)
        await db.flush()
        await db.refresh(record)
        saved.append(InsightItem.model_validate(record))

    return saved


@router.get("/list", response_model=list[InsightItem])
async def list_insights(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
):
    """Get previously generated insights for the active org."""
    result = await db.execute(
        select(BusinessInsight)
        .where(BusinessInsight.organization_id == org.id)
        .order_by(desc(BusinessInsight.created_at))
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/season-context", response_model=SeasonAdvice)
async def get_season_context():
    """Get current season context with product advice."""
    ws = WeatherService()
    hs = HolidayService()
    now = __import__("datetime").datetime.now()
    season = WeatherService.get_season(now)
    demand_info = WeatherService.get_seasonal_demand_advice(now)
    pre_window = hs.is_in_pre_holiday_window(now)
    upcoming = hs.get_upcoming_holidays(now, limit=3)

    return SeasonAdvice(
        current_season=season,
        season_emoji=WeatherService.get_season_emoji(season),
        season_advice=demand_info.get("advice", ""),
        high_demand_products=demand_info.get("high_demand", []),
        low_demand_products=demand_info.get("low_demand", []),
        pre_holiday_window=pre_window if pre_window else None,
        upcoming_holidays=upcoming.to_dict("records") if len(upcoming) > 0 else [],
    )


