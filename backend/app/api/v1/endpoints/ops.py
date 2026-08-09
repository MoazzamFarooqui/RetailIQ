"""Operational endpoints — system health, Celery job management, task status.

Phase 4 hardening: exposes Celery task state so operators can see training
and forecasting progress, retry failed tasks, and monitor system health.
"""

import logging

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_db, engine
from app.core.dependencies import get_current_user, require_org_roles
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/system/health")
async def system_health(db: AsyncSession = Depends(get_db)):
    """Liveness of the platform's components."""
    checks = {"api": "ok"}

    # Database
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    # Redis
    try:
        from app.core.cache import get_redis_client
        redis = await get_redis_client()
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": overall, "checks": checks}


@router.get("/system/info")
async def system_info(current_user: User = Depends(require_org_roles(["owner", "admin"]))):
    """Version and environment info (admin)."""
    from app.core.config import settings
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "python": __import__("sys").version.split()[0],
    }


@router.get("/jobs")
async def list_celery_jobs(
    limit: int = 50,
    current_user: User = Depends(require_org_roles(["owner", "admin", "manager"])),
):
    """List recent Celery task states (all orgs — operator view)."""
    try:
        from celery.result import AsyncResult
        from app.tasks.celery_app import celery_app

        # Celery inspect gives live workers; the result backend stores finished states.
        inspector = celery_app.control.inspect()
        active = inspector.active() or {}
        reserved = inspector.reserved() or {}
        scheduled = inspector.scheduled() or {}

        jobs = []
        for worker, tasks in active.items():
            for t in tasks:
                jobs.append({
                    "task_id": t["id"],
                    "name": t["name"],
                    "state": "active",
                    "worker": worker,
                    "args": str(t.get("args", ""))[:200],
                })
        for worker, tasks in scheduled.items():
            for t in tasks:
                jobs.append({
                    "task_id": t.get("id"),
                    "name": t.get("name"),
                    "state": "scheduled",
                    "worker": worker,
                    "args": str(t.get("args", ""))[:200],
                })
        return {"jobs": jobs[:limit], "total": len(jobs)}
    except Exception as e:
        logger.error(f"Failed to list celery jobs: {e}")
        # Celery broker may be down — return empty gracefully
        return {"jobs": [], "total": 0, "warning": str(e)}


@router.get("/jobs/{task_id}")
async def get_job_status(task_id: str, current_user: User = Depends(require_org_roles(["owner", "admin", "manager"]))):
    """Get the status and result of a Celery task by ID."""
    from celery.result import AsyncResult
    from app.tasks.celery_app import celery_app

    result = AsyncResult(task_id, app=celery_app)
    return {
        "task_id": task_id,
        "state": result.state,
        "status": result.status,
        "ready": result.ready(),
        "successful": result.successful() if result.ready() else None,
        "result": result.result if result.ready() else None,
        "traceback": result.traceback if result.ready() else None,
    }


@router.post("/jobs/{task_id}/retry")
async def retry_job(
    task_id: str,
    current_user: User = Depends(require_org_roles(["owner", "admin", "manager"])),
):
    """Re-enqueue a failed Celery task."""
    from celery.result import AsyncResult
    from app.tasks.celery_app import celery_app

    result = AsyncResult(task_id, app=celery_app)
    if result.successful():
        raise HTTPException(status_code=400, detail="Task already succeeded — nothing to retry")

    # Re-dispatch by looking up the task function and re-running with original args.
    # Celery doesn't persist args for arbitrary re-runs; this re-runs the task
    # function with the same signature when the task name is known.
    task_name = result.task_name if hasattr(result, "task_name") else None
    if not task_name:
        raise HTTPException(status_code=400, detail="Task metadata unavailable — cannot retry")

    try:
        task = celery_app.tasks.get(task_name)
        if task is None:
            raise HTTPException(status_code=404, detail=f"Unknown task {task_name}")
        new_result = task.apply_async(args=result.args or [], kwargs=result.kwargs or {})
        return {"status": "queued", "new_task_id": new_result.id, "task_name": task_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retry failed: {str(e)}")


@router.get("/task-templates")
async def list_task_templates(current_user: User = Depends(require_org_roles(["owner", "admin", "manager"]))):
    """List the Celery tasks the platform can run (for manual dispatch)."""
    from app.tasks.celery_app import celery_app
    templates = []
    for name, task in celery_app.tasks.items():
        if name.startswith("app.tasks."):
            templates.append({"name": name, "description": task.__doc__ or ""})
    return {"tasks": sorted(templates, key=lambda t: t["name"])}

