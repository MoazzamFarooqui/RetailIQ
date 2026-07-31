"""Celery tasks for model training."""

import logging
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def train_all_models_task(self, dataset_id: str = None, params: dict = None):
    """Train all forecasting models asynchronously, select and save the best."""
    if params is None:
        params = {}
    logger.info(f"Starting model training task (dataset={dataset_id})")
    try:
        import pandas as pd
        import os
        from app.services.forecasting import DemandForecaster

        # Load data
        data_paths = [
            "data/processed/engineered_features.csv",
            "data/processed/uploaded_data.csv",
        ]
        df = None
        for p in data_paths:
            if os.path.exists(p):
                df = pd.read_csv(p)
                df["date"] = pd.to_datetime(df["date"])
                break

        if df is None:
            return {"status": "error", "message": "No training data found"}

        sample_size = params.get("sample_size", 50000)
        if sample_size < len(df):
            df = df.sample(n=sample_size, random_state=42)

        self.update_state(state="PROGRESS", meta={"progress": 0.2, "message": "Training models..."})

        forecaster = DemandForecaster()
        comparison_df, best_model = forecaster.train_all_models(
            df, target_col="sales",
            test_size=params.get("test_size", 0.2),
            include_prophet=params.get("include_prophet", False),
            include_baseline=params.get("include_baseline", True),
        )

        self.update_state(state="PROGRESS", meta={"progress": 0.7, "message": f"Best model: {best_model}. Saving..."})

        # Save best model
        best_forecaster = DemandForecaster(model_type=best_model)
        best_forecaster.train_model(df, target_col="sales")
        os.makedirs("models", exist_ok=True)
        best_forecaster.save_model("models/best_model.joblib")

        return {
            "status": "success",
            "best_model": best_model,
            "comparison": comparison_df.to_dict("records"),
            "models_trained": len(comparison_df),
        }
    except Exception as e:
        logger.error(f"Training task failed: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True)
def generate_daily_insights(self):
    """Scheduled task: generate daily business insights."""
    logger.info("Starting daily insights generation")
    try:
        import pandas as pd
        from app.services.insights_engine import InsightsEngine

        df = pd.read_csv("data/processed/engineered_features.csv")
        df["date"] = pd.to_datetime(df["date"])

        engine = InsightsEngine()
        insights = engine.analyze(df)
        return {"status": "success", "insights_count": len(insights)}
    except Exception as e:
        logger.error(f"Daily insights task failed: {e}")
        return {"status": "error", "message": str(e)}
