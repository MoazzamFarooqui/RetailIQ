"""Forecast generation and history endpoints."""

import uuid
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import pandas as pd

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.forecast import (
    ForecastGenerateRequest, ForecastHeaderResponse, ForecastDetailResponse,
    ForecastHistoryResponse, ForecastRecord,
)
from app.models.user import User
from app.models.forecast import ForecastHeader, Forecast
from app.models.dataset import Dataset
from app.services.forecasting import DemandForecaster

router = APIRouter()


@router.post("/generate")
async def generate_forecast(
    request: ForecastGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a demand forecast for a specific product/store combination."""
    # Load data
    try:
        data_path = "data/processed/engineered_features.csv"
        df = pd.read_csv(data_path)
        df["date"] = pd.to_datetime(df["date"])
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Processed data not found. Upload and process data first.")

    # Filter for the requested item + store
    item_store_data = df[(df["item_id"] == request.item_id) & (df["store_id"] == request.store_id)].sort_values("date")
    if len(item_store_data) == 0:
        raise HTTPException(status_code=404, detail=f"No data found for {request.item_id} at {request.store_id}")

    # Train or load model
    model_path = "models/best_model.joblib"
    try:
        forecaster = DemandForecaster()
        forecaster.load_model(model_path)
    except (FileNotFoundError, Exception):
        # Train on the fly
        forecaster = DemandForecaster()
        forecaster.train_model(item_store_data)

    # Generate forecast
    forecast_df = forecaster.forecast_future(item_store_data, periods=request.horizon_days)

    if len(forecast_df) == 0:
        raise HTTPException(status_code=500, detail="Forecast generation returned no data")

    # Save forecast header
    header = ForecastHeader(
        model_type=forecaster.model_type,
        horizon_days=request.horizon_days,
        item_count=1,
        store_count=1,
        total_forecast=float(forecast_df["predicted_sales"].sum()),
        created_by=current_user.id,
    )
    db.add(header)
    await db.flush()

    # Build response
    records = []
    for _, row in forecast_df.iterrows():
        records.append({
            "id": str(uuid.uuid4()),
            "header_id": header.id,
            "item_id": request.item_id,
            "store_id": request.store_id,
            "forecast_date": row["date"].strftime("%Y-%m-%d") if hasattr(row["date"], "strftime") else str(row["date"])[:10],
            "predicted_sales": float(row["predicted_sales"]),
        })

    return {
        "header": ForecastHeaderResponse(
            id=header.id, dataset_id=None, model_type=header.model_type,
            horizon_days=header.horizon_days, item_count=1, store_count=1,
            total_forecast=header.total_forecast, created_by=current_user.id,
            created_at=header.created_at,
        ),
        "forecast": records,
        "summary": {
            "total_forecast": float(forecast_df["predicted_sales"].sum()),
            "avg_daily": float(forecast_df["predicted_sales"].mean()),
            "peak_day": forecast_df.loc[forecast_df["predicted_sales"].idxmax(), "date"].strftime("%Y-%m-%d") if len(forecast_df) > 0 else None,
            "peak_value": float(forecast_df["predicted_sales"].max()) if len(forecast_df) > 0 else 0,
        },
    }


@router.get("/history", response_model=ForecastHistoryResponse)
async def forecast_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get forecast generation history."""
    result = await db.execute(
        select(ForecastHeader).order_by(ForecastHeader.created_at.desc()).limit(50)
    )
    headers = result.scalars().all()
    return ForecastHistoryResponse(
        headers=[ForecastHeaderResponse.model_validate(h) for h in headers],
        total=len(headers),
    )


@router.get("/{forecast_id}", response_model=ForecastDetailResponse)
async def get_forecast(
    forecast_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full forecast details including all predictions."""
    result = await db.execute(select(ForecastHeader).where(ForecastHeader.id == forecast_id))
    header = result.scalar_one_or_none()
    if not header:
        raise HTTPException(status_code=404, detail="Forecast not found")

    return ForecastDetailResponse(
        id=header.id, dataset_id=header.dataset_id,
        model_type=header.model_type, horizon_days=header.horizon_days,
        item_count=header.item_count, store_count=header.store_count,
        total_forecast=header.total_forecast, created_by=header.created_by,
        created_at=header.created_at,
        details=[ForecastRecord.model_validate(d) for d in header.details],
    )
