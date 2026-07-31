"""Model training and management endpoints."""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import pandas as pd
import os

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.schemas.model import (
    TrainRequest, ModelMetrics, ModelHistoryRecord, ModelComparisonResponse,
    FeatureImportance, TrainResponse,
)
from app.models.user import User
from app.models.model_history import ModelHistory
from app.services.forecasting import DemandForecaster

router = APIRouter()


@router.post("/train", response_model=TrainResponse)
async def train_models(
    request: TrainRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "analyst"])),
):
    """Train all forecasting models and select the best one."""
    # Load data
    data_paths = [
        "data/processed/engineered_features.csv",
        "data/processed/uploaded_data.csv",
        "data/processed/final_dataset.csv",
    ]
    df = None
    for p in data_paths:
        if os.path.exists(p):
            df = pd.read_csv(p)
            df["date"] = pd.to_datetime(df["date"])
            break

    if df is None:
        raise HTTPException(status_code=404, detail="No training data found. Upload data first.")

    # Feature engineering if needed
    if request.sample_size < len(df):
        df = df.sample(n=request.sample_size, random_state=42)

    if "sales" not in df.columns:
        raise HTTPException(status_code=400, detail="Training data must contain a 'sales' column")

    # Train all models
    try:
        forecaster = DemandForecaster()
        comparison_df, best_model = forecaster.train_all_models(
            df, target_col="sales", test_size=request.test_size,
            include_prophet=request.include_prophet,
            include_baseline=request.include_baseline,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")

    # Save best model
    best_forecaster = DemandForecaster(model_type=best_model)
    best_forecaster.train_model(df, target_col="sales")
    model_path = "models/best_model.joblib"
    os.makedirs("models", exist_ok=True)
    best_forecaster.save_model(model_path)

    # Save metrics to DB
    models_saved = []
    for _, row in comparison_df.iterrows():
        is_best = row["model"] == best_model
        metrics = ModelHistory(
            model_type=row["model"],
            mae=row.get("MAE"), rmse=row.get("RMSE"),
            mape=row.get("MAPE"), r2=row.get("R2"),
            training_time_sec=row.get("training_time_sec"),
            is_best=is_best,
            model_path=model_path if is_best else None,
            created_by=current_user.id,
            feature_count=len(best_forecaster.feature_names) if is_best and best_forecaster.feature_names else 0,
        )
        db.add(metrics)
        models_saved.append(ModelMetrics(
            model_type=row["model"],
            mae=row.get("MAE"), rmse=row.get("RMSE"),
            mape=row.get("MAPE"), r2=row.get("R2"),
            training_time_sec=row.get("training_time_sec"),
            is_best=is_best,
        ))

    await db.flush()

    return TrainResponse(
        message=f"Training complete. Best model: {best_model}. Models trained: {len(comparison_df)}",
        is_async=False,
        comparison=[m.model_dump() for m in models_saved],
        best_model=best_model,
    )


@router.get("/history", response_model=list[ModelHistoryRecord])
async def get_model_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get model training history."""
    result = await db.execute(
        select(ModelHistory).order_by(desc(ModelHistory.trained_at)).limit(50)
    )
    return result.scalars().all()


@router.get("/best")
async def get_best_model(db: AsyncSession = Depends(get_db)):
    """Get the best performing model."""
    result = await db.execute(
        select(ModelHistory).where(ModelHistory.is_best == True).order_by(desc(ModelHistory.trained_at)).limit(1)
    )
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="No trained model found")
    return ModelMetrics(
        model_type=model.model_type, mae=model.mae, rmse=model.rmse,
        mape=model.mape, r2=model.r2,
        training_time_sec=model.training_time_sec, is_best=True,
    )


@router.get("/features", response_model=list[FeatureImportance])
async def get_feature_importance(current_user: User = Depends(get_current_user)):
    """Get feature importance from the current best model."""
    model_path = "models/best_model.joblib"
    if not os.path.exists(model_path):
        raise HTTPException(status_code=404, detail="No trained model found")

    try:
        forecaster = DemandForecaster()
        forecaster.load_model(model_path)
        importance = forecaster.get_feature_importance(top_n=20)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get feature importance: {str(e)}")

    if importance is None:
        raise HTTPException(status_code=400, detail="Current model does not support feature importance")

    return [
        FeatureImportance(feature=row["feature"], importance=float(row["importance"]))
        for _, row in importance.iterrows()
    ]
