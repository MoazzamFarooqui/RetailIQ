"""Celery tasks for the Model Registry — scheduled monitoring & auto-retrain."""

import asyncio
import logging

from app.tasks.celery_app import celery_app
from app.core.database import async_session_factory
from app.services.model_registry_service import ModelRegistryService
from app.services.data_service import TenantDataService

logger = logging.getLogger(__name__)


def _run_sync(awaitable):
    return asyncio.run(awaitable)


@celery_app.task(bind=True)
def evaluate_forecasts_task(self):
    """Daily: evaluate matured forecasts against actuals for all active orgs.

    Updates ForecastAccuracy rows and the active model's live metrics, then
    flags degradation.
    """
    logger.info("Starting forecast evaluation task")
    try:
        async def _run():
            from sqlalchemy import select
            from app.models import Organization, OrgStatus

            async with async_session_factory() as db:
                orgs = (await db.execute(
                    select(Organization).where(Organization.status == OrgStatus.ACTIVE)
                )).scalars().all()

                total_rows = 0
                for org in orgs:
                    try:
                        result = await ModelRegistryService.evaluate_matured_forecasts(db, org.id)
                        total_rows += result.get("accuracy_rows", 0)
                    except Exception as e:
                        logger.error(f"Evaluation failed for org {org.id}: {e}")
                return {"status": "ok", "accuracy_rows": total_rows, "organizations": len(orgs)}

        return _run_sync(_run())
    except Exception as e:
        logger.error(f"Forecast evaluation task failed: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True)
def auto_retrain_task(self):
    """Daily: retrain degraded or stale models, auto-promote if clearly better."""
    logger.info("Starting auto-retrain task")
    try:
        async def _run():
            from sqlalchemy import select
            from app.models import Organization, OrgStatus

            async with async_session_factory() as db:
                orgs = (await db.execute(
                    select(Organization).where(Organization.status == OrgStatus.ACTIVE)
                )).scalars().all()

                retrained = 0
                promoted = 0
                for org in orgs:
                    active = await ModelRegistryService.get_active(db, org.id)
                    if not ModelRegistryService.should_auto_retrain(active):
                        continue

                    df = await TenantDataService.load_sales_df(db, org.id)
                    if df.empty:
                        continue
                    try:
                        best = await ModelRegistryService.train_and_register(
                            db, org.id, df, created_by=None, sample_size=50000,
                        )
                        retrained += 1
                        if best and ModelRegistryService.meets_promotion_bar(best, active):
                            await ModelRegistryService.promote(db, best)
                            promoted += 1
                    except Exception as e:
                        logger.error(f"Auto-retrain failed for org {org.id}: {e}")
                return {"status": "ok", "retrained": retrained, "promoted": promoted, "organizations": len(orgs)}

        return _run_sync(_run())
    except Exception as e:
        logger.error(f"Auto-retrain task failed: {e}")
        return {"status": "error", "message": str(e)}
