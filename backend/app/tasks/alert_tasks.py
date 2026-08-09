"""Celery tasks for the Smart Alert Engine — daily detection for all orgs."""

import asyncio
import logging

from app.tasks.celery_app import celery_app
from app.core.database import async_session_factory
from app.services.alert_service import AlertService
from app.services.data_service import TenantDataService
from app.services.purchase_engine import PurchaseDecisionEngine
from app.services.model_registry_service import ModelRegistryService

logger = logging.getLogger(__name__)


def _run_sync(awaitable):
    return asyncio.run(awaitable)


@celery_app.task(bind=True)
def run_alert_detection_task(self):
    """Daily: run all alert detectors for every active org."""
    logger.info("Starting alert detection task")
    try:
        async def _run():
            from sqlalchemy import select
            from app.models import Organization, OrgStatus

            async with async_session_factory() as db:
                orgs = (await db.execute(
                    select(Organization).where(Organization.status == OrgStatus.ACTIVE)
                )).scalars().all()

                totals = {}
                for org in orgs:
                    try:
                        sales_df = await TenantDataService.load_sales_df(db, org.id)
                        if sales_df.empty:
                            continue

                        inv_df = await TenantDataService.load_inventory_df(db, org.id)
                        if not inv_df.empty:
                            sales_df = sales_df.merge(inv_df, on=["item_id", "store_id"], how="left")
                        if "current_stock" not in sales_df.columns or sales_df["current_stock"].isna().all():
                            stock = sales_df.groupby(["item_id", "store_id"])["sales"].transform(lambda x: max(x.tail(28).sum() * 1.5, 10))
                            sales_df = sales_df.copy()
                            sales_df["current_stock"] = stock

                        engine = PurchaseDecisionEngine()
                        decisions_df = engine.generate_purchase_decisions(sales_df)
                        active_model = await ModelRegistryService.get_active(db, org.id)

                        counts = await AlertService.run_all_detectors(db, org.id, decisions_df, sales_df, active_model)
                        for k, v in counts.items():
                            totals[k] = totals.get(k, 0) + v
                    except Exception as e:
                        logger.error(f"Alert detection failed for org {org.id}: {e}")

                await db.commit()
                return {"status": "ok", "created": totals, "organizations": len(orgs)}

        return _run_sync(_run())
    except Exception as e:
        logger.error(f"Alert detection task failed: {e}")
        return {"status": "error", "message": str(e)}

