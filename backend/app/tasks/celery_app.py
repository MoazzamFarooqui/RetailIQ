"""Celery application configuration."""

from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "retailiq",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.forecast_tasks", "app.tasks.training_tasks", "app.tasks.report_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Karachi",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    worker_max_tasks_per_child=10,
    beat_schedule={
        "generate-daily-insights": {
            "task": "app.tasks.training_tasks.generate_daily_insights",
            "schedule": 86400.0,  # daily
        },
    },
)


@celery_app.task(bind=True)
def debug_task(self):
    """Debug task to verify Celery is working."""
    print(f"Request: {self.request!r}")
    return {"status": "ok", "message": "Celery is running"}
