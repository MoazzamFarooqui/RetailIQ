"""Celery tasks for PDF report generation."""

import logging
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def generate_pdf_report_task(self, forecast_id: str = None, inventory_id: str = None):
    """Generate a combined PDF report asynchronously."""
    logger.info(f"Starting PDF report generation (forecast={forecast_id}, inventory={inventory_id})")
    try:
        from app.services.report_generator import ReportGenerator

        filepath = ReportGenerator.export_pdf_report(
            forecast_df=None,  # Would load from DB in full implementation
            inventory_df=None,
            insights_text="RetailIQ Automated Report",
        )
        return {"status": "success", "filepath": filepath}
    except Exception as e:
        logger.error(f"PDF report task failed: {e}")
        return {"status": "error", "message": str(e)}
