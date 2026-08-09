"""Celery tasks for model training (org-scoped)."""

import asyncio
import logging

from app.tasks.celery_app import celery_app
from app.core.database import async_session_factory
from app.services.data_service import TenantDataService
from app.services.forecasting import DemandForecaster
from app.models.model_history import ModelHistory

logger = logging.getLogger(__name__)


def _run_sync(awaitable):
    """Run an async coroutine in the Celery worker's event loop."""
    return asyncio.run(awaitable)


@celery_app.task(bind=True)
def train_all_models_task(self, organization_id: str = None, dataset_id: str = None, params: dict = None):
    """Train all forecasting models asynchronously on an org's data, select and save the best."""
    if params is None:
        params = {}
    logger.info(f"Starting model training task (org={organization_id})")
    try:
        import os
        from sqlalchemy import select

        async def _train():
            async with async_session_factory() as db:
                df = await TenantDataService.load_sales_df(db, organization_id)
                if df.empty:
                    return {"status": "error", "message": "No training data found for this organization"}

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

                # Save best model to the org's directory
                best_forecaster = DemandForecaster(model_type=best_model)
                best_forecaster.train_model(df, target_col="sales")
                org_model_dir = os.path.join("models", organization_id)
                os.makedirs(org_model_dir, exist_ok=True)
                model_path = os.path.join(org_model_dir, "best_model.joblib")
                best_forecaster.save_model(model_path)

                # Persist metrics
                for _, row in comparison_df.iterrows():
                    is_best = row["model"] == best_model
                    db.add(ModelHistory(
                        organization_id=organization_id,
                        model_type=row["model"],
                        mae=row.get("MAE"), rmse=row.get("RMSE"),
                        mape=row.get("MAPE"), r2=row.get("R2"),
                        training_time_sec=row.get("training_time_sec"),
                        is_best=is_best,
                        model_path=model_path if is_best else None,
                        feature_count=len(best_forecaster.feature_names) if is_best and best_forecaster.feature_names else 0,
                    ))
                await db.commit()

                return {
                    "status": "success",
                    "best_model": best_model,
                    "comparison": comparison_df.to_dict("records"),
                    "models_trained": len(comparison_df),
                    "organization_id": organization_id,
                }

        return _run_sync(_train())
    except Exception as e:
        logger.error(f"Training task failed: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True)
def generate_daily_insights(self):
    """Scheduled task: generate daily business insights for all active orgs."""
    logger.info("Starting daily insights generation")
    try:
        from app.services.insights_engine import InsightsEngine

        async def _run():
            async with async_session_factory() as db:
                from sqlalchemy import select
                from app.models import Organization, OrgStatus

                orgs = (await db.execute(
                    select(Organization).where(Organization.status == OrgStatus.ACTIVE)
                )).scalars().all()

                total = 0
                for org in orgs:
                    df = await TenantDataService.load_sales_df(db, org.id)
                    if df.empty:
                        continue
                    engine = InsightsEngine()
                    insights = engine.analyze(df)
                    # Persist insights org-scoped
                    from app.models.insight import BusinessInsight
                    for ins in insights[:50]:
                        db.add(BusinessInsight(
                            organization_id=org.id,
                            insight_type=ins["insight_type"],
                            insight_text=ins["insight_text"],
                            category=ins.get("category"),
                            severity=ins.get("severity", "info"),
                        ))
                    total += len(insights)
                await db.commit()
                return {"status": "success", "insights_count": total, "organizations": len(orgs)}

        return _run_sync(_run())
    except Exception as e:
        logger.error(f"Daily insights task failed: {e}")
        return {"status": "error", "message": str(e)}

