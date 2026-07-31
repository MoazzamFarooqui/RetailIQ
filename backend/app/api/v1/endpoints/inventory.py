"""Inventory optimization endpoints."""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd
import numpy as np

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.inventory import (
    InventoryRequest, InventoryRecommendationItem, InventoryStatusResponse,
    StockoutPrediction, OverstockItem,
)
from app.models.user import User
from app.services.inventory_optimizer import InventoryOptimizer
from app.services.weather_service import WeatherService

router = APIRouter()


@router.post("/recommendations")
async def generate_recommendations(
    request: InventoryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate inventory optimization recommendations."""
    # Load data
    try:
        data_path = "data/processed/engineered_features.csv"
        df = pd.read_csv(data_path)
        df["date"] = pd.to_datetime(df["date"])
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Processed data not found. Upload and process data first.")

    # Get demand multiplier
    demand_mult = request.demand_multiplier or InventoryOptimizer.get_current_demand_multiplier()["multiplier"]

    # Sample if needed
    combos = df[["item_id", "store_id"]].drop_duplicates()
    if len(combos) > request.sample_size:
        sampled = combos.sample(n=request.sample_size, random_state=42)
        df = df.merge(sampled, on=["item_id", "store_id"])

    # Estimate current stock if not present
    if "current_stock" not in df.columns:
        stock = df.groupby(["item_id", "store_id"])["sales"].transform(lambda x: max(x.tail(28).sum() * 1.5, 10))
        df = df.copy()
        df["current_stock"] = stock

    # Run optimizer
    optimizer = InventoryOptimizer(service_level=request.service_level)
    recommendations = optimizer.generate_inventory_recommendations(
        df, demand_multiplier=demand_mult
    )

    if len(recommendations) == 0:
        raise HTTPException(status_code=500, detail="No recommendations generated")

    # Calculate metrics
    metrics = optimizer.calculate_inventory_metrics(recommendations)
    items_need_reorder = int((recommendations["recommended_order_qty"] > 0).sum())

    # Stockout predictions
    stockout_predictions = []
    for _, row in recommendations.iterrows():
        stockout = optimizer.predict_stockout_date(row["current_stock"], row["avg_daily_demand"])
        if stockout and stockout["days_remaining"] < 90:
            stockout_predictions.append({
                "item_id": row["item_id"], "store_id": row["store_id"],
                "current_stock": float(row["current_stock"]),
                "avg_daily_demand": float(row["avg_daily_demand"]),
                "days_remaining": stockout["days_remaining"],
                "predicted_stockout_date": stockout["predicted_date"],
                "is_critical": stockout["is_critical"],
            })

    # Overstock
    overstock_items = []
    for _, row in recommendations.iterrows():
        overstock = optimizer.detect_overstock(row["current_stock"], row["avg_daily_demand"], request.excess_threshold_days)
        if overstock["is_overstock"]:
            overstock_items.append({
                "item_id": row["item_id"], "store_id": row["store_id"],
                "current_stock": float(row["current_stock"]),
                "avg_daily_demand": float(row["avg_daily_demand"]),
                "days_of_stock": overstock["days_of_stock"],
                "excess_units": overstock["excess_units"],
                "reason": overstock["reason"],
            })

    # Build response items
    items = []
    for _, row in recommendations.head(100).iterrows():
        items.append(InventoryRecommendationItem(
            item_id=row["item_id"], store_id=row["store_id"],
            current_stock=float(row["current_stock"]),
            avg_daily_demand=float(row["avg_daily_demand"]),
            demand_std=float(row["demand_std"]),
            safety_stock=float(row["safety_stock"]),
            reorder_point=float(row["reorder_point"]),
            eoq=float(row["eoq"]),
            recommended_order_qty=float(row["recommended_order_qty"]),
            status=row["status"], days_of_stock=float(row["days_of_stock"]),
            stockout_in_days=float(row.get("stockout_in_days", 999)),
            stockout_date=str(row.get("stockout_date", "N/A")),
            demand_multiplier_used=float(row["demand_multiplier_used"]),
        ))

    return {
        "recommendations": items,
        "total_count": len(recommendations),
        "metrics": {
            "total_items": metrics["total_items"],
            "items_ok": metrics["items_ok"],
            "items_low": metrics["items_low"],
            "items_critical": metrics["items_critical"],
            "items_excess": metrics["items_excess"],
            "avg_days_of_stock": round(metrics["avg_days_of_stock"], 1),
            "total_safety_stock": round(metrics["total_safety_stock"], 0),
            "total_recommended_orders": round(metrics["total_recommended_orders"], 0),
            "items_need_reorder": items_need_reorder,
        },
        "stockout_predictions": stockout_predictions[:50],
        "overstock_items": overstock_items[:50],
    }


@router.get("/demand-multiplier")
async def get_demand_multiplier():
    """Get the current demand multiplier based on season, weather, and holidays."""
    multiplier = InventoryOptimizer.get_current_demand_multiplier()
    return multiplier


@router.get("/seasonal-advice")
async def get_seasonal_advice():
    """Get seasonal product advice and holiday stock recommendations."""
    advice = InventoryOptimizer.get_holiday_stock_advice()
    return {"advice": advice}
