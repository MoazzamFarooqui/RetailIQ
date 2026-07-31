"""Celery tasks for long-running forecast generation."""

import logging
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def generate_forecast_task(self, forecast_id: str, params: dict):
    """Generate a demand forecast asynchronously.

    Args:
        forecast_id: UUID of the forecast header record
        params: dict with item_id, store_id, horizon_days, model_type
    """
    logger.info(f"Starting forecast task {forecast_id} with params: {params}")
    try:
        import pandas as pd
        from app.services.forecasting import DemandForecaster

        df = pd.read_csv("data/processed/engineered_features.csv")
        df["date"] = pd.to_datetime(df["date"])

        item_data = df[(df["item_id"] == params["item_id"]) & (df["store_id"] == params["store_id"])].sort_values("date")

        self.update_state(state="PROGRESS", meta={"progress": 0.3, "message": "Loading model..."})
        forecaster = DemandForecaster()
        try:
            forecaster.load_model("models/best_model.joblib")
        except FileNotFoundError:
            forecaster.train_model(item_data)

        self.update_state(state="PROGRESS", meta={"progress": 0.6, "message": "Generating forecast..."})
        forecast_df = forecaster.forecast_future(item_data, periods=params.get("horizon_days", 30))

        self.update_state(state="PROGRESS", meta={"progress": 1.0, "message": "Forecast complete"})
        return {
            "status": "success",
            "forecast_id": forecast_id,
            "total_forecast": float(forecast_df["predicted_sales"].sum()),
            "records": len(forecast_df),
            "model_type": forecaster.model_type,
        }
    except Exception as e:
        logger.error(f"Forecast task failed: {e}")
        return {"status": "error", "forecast_id": forecast_id, "error": str(e)}


@celery_app.task(bind=True)
def bulk_inventory_task(self, dataset_id: str, params: dict):
    """Generate inventory recommendations for all items in a dataset."""
    logger.info(f"Starting bulk inventory task for dataset {dataset_id}")
    try:
        import pandas as pd
        from app.services.inventory_optimizer import InventoryOptimizer

        df = pd.read_csv("data/processed/engineered_features.csv")
        df["date"] = pd.to_datetime(df["date"])

        if "current_stock" not in df.columns:
            stock = df.groupby(["item_id", "store_id"])["sales"].transform(
                lambda x: max(x.tail(28).sum() * 1.5, 10)
            )
            df = df.copy()
            df["current_stock"] = stock

        optimizer = InventoryOptimizer(service_level=params.get("service_level", 0.95))
        demand_mult = params.get("demand_multiplier", 1.0)
        recommendations = optimizer.generate_inventory_recommendations(df, demand_multiplier=demand_mult)

        return {
            "status": "success",
            "dataset_id": dataset_id,
            "total_recommendations": len(recommendations),
        }
    except Exception as e:
        logger.error(f"Bulk inventory task failed: {e}")
        return {"status": "error", "dataset_id": dataset_id, "error": str(e)}
