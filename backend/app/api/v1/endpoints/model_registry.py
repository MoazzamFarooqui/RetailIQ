"""Model Registry API endpoints — train, promote, rollback, monitor, accuracy."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_org, require_org_roles
from app.schemas.model_registry import (
    ModelArtifactResponse, TrainRegistryRequest, TrainRegistryResponse,
    RollbackRequest, ForecastAccuracyResponse, AccuracySummary, RegistryOverview,
)
from app.models.user import User
from app.models.organization import Organization
from app.models.model_registry import ModelArtifact, ForecastAccuracy
from app.services.data_service import TenantDataService
from app.services.model_registry_service import ModelRegistryService

router = APIRouter()


@router.get("/overview", response_model=RegistryOverview)
async def registry_overview(
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
):
    """Get the org's model registry overview: active model, versions, health."""
    active = await ModelRegistryService.get_active(db, org.id)
    versions = await ModelRegistryService.list_versions(db, org.id, limit=50)

    degraded = bool(active and ModelRegistryService.check_degradation(active))
    needs_retrain = bool(active is None or ModelRegistryService.should_auto_retrain(active))

    return RegistryOverview(
        active_model=ModelArtifactResponse.model_validate(active) if active else None,
        versions=[ModelArtifactResponse.model_validate(v) for v in versions],
        total_versions=len(versions),
        degraded=degraded,
        needs_retrain=needs_retrain,
    )


@router.post("/train", response_model=TrainRegistryResponse)
async def train_registry(
    request: TrainRegistryRequest,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(require_org_roles(["owner", "admin", "manager", "analyst"])),
):
    """Train all algorithms, register candidates, optionally auto-promote the best."""
    df = await TenantDataService.load_sales_df(db, org.id)
    if df.empty:
        raise HTTPException(status_code=404, detail="No data for this organization. Upload or ingest data first.")

    try:
        best = await ModelRegistryService.train_and_register(
            db, org.id, df,
            created_by=current_user.id,
            sample_size=request.sample_size,
            test_size=request.test_size,
            notes=request.notes,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")

    promoted = False
    if best is not None and request.auto_promote:
        active = await ModelRegistryService.get_active(db, org.id)
        if ModelRegistryService.meets_promotion_bar(best, active):
            await ModelRegistryService.promote(db, best, promoted_by=current_user.id)
            promoted = True

    versions = await ModelRegistryService.list_versions(db, org.id, limit=10)
    message = (
        f"Best candidate: {best.algorithm} (WAPE={best.wape:.2f}%)" if best and best.wape is not None
        else "Training complete"
    )
    if best is not None and promoted:
        message += " — promoted to active."
    elif best is not None and request.auto_promote:
        message += " — not promoted (did not beat active model)."

    return TrainRegistryResponse(
        trained=[ModelArtifactResponse.model_validate(v) for v in versions],
        best=ModelArtifactResponse.model_validate(best) if best else None,
        promoted=promoted,
        message=message,
    )


@router.post("/promote/{artifact_id}", response_model=ModelArtifactResponse)
async def promote_model(
    artifact_id: str,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(require_org_roles(["owner", "admin", "manager"])),
):
    """Manually promote a candidate version to active."""
    result = await db.execute(
        select(ModelArtifact).where(
            ModelArtifact.id == artifact_id,
            ModelArtifact.organization_id == org.id,
        )
    )
    artifact = result.scalar_one_or_none()
    if artifact is None:
        raise HTTPException(status_code=404, detail="Model artifact not found")

    await ModelRegistryService.promote(db, artifact, promoted_by=current_user.id)
    await db.refresh(artifact)
    return artifact


@router.post("/rollback", response_model=ModelArtifactResponse)
async def rollback_model(
    request: RollbackRequest,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(require_org_roles(["owner", "admin", "manager"])),
):
    """Roll the registry back to a previous version."""
    try:
        target = await ModelRegistryService.rollback(db, org.id, request.version, rolled_back_by=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return target


@router.get("/versions", response_model=list[ModelArtifactResponse])
async def list_registry_versions(
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
):
    """List all model versions in the org's registry."""
    versions = await ModelRegistryService.list_versions(db, org.id, limit=100)
    return versions


@router.get("/accuracy", response_model=list[ForecastAccuracyResponse])
async def get_accuracy(
    horizon: int | None = None,
    product_id: str | None = None,
    store_id: str | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
):
    """Get forecast accuracy records for the org, optionally filtered."""
    query = select(ForecastAccuracy).where(ForecastAccuracy.organization_id == org.id)
    if horizon:
        query = query.where(ForecastAccuracy.horizon_days == horizon)
    if product_id:
        query = query.where(ForecastAccuracy.product_id == product_id)
    if store_id:
        query = query.where(ForecastAccuracy.store_id == store_id)
    query = query.order_by(desc(ForecastAccuracy.evaluated_at)).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/accuracy/summary", response_model=list[AccuracySummary])
async def get_accuracy_summary(
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
):
    """Aggregate accuracy per forecast horizon across the org."""
    records = (await db.execute(
        select(ForecastAccuracy).where(ForecastAccuracy.organization_id == org.id)
    )).scalars().all()

    by_horizon: dict[int, list[ForecastAccuracy]] = {}
    for r in records:
        by_horizon.setdefault(r.horizon_days, []).append(r)

    summaries = []
    for horizon, items in sorted(by_horizon.items()):
        import numpy as np
        valid_wape = [i.wape for i in items if i.wape is not None]
        valid_mae = [i.mae for i in items if i.mae is not None]
        valid_rmse = [i.rmse for i in items if i.rmse is not None]
        valid_mape = [i.mape for i in items if i.mape is not None]
        valid_bias = [i.bias for i in items if i.bias is not None]
        points = sum(i.eval_points or 0 for i in items)
        summaries.append(AccuracySummary(
            horizon_days=horizon,
            mae=float(np.mean(valid_mae)) if valid_mae else None,
            rmse=float(np.mean(valid_rmse)) if valid_rmse else None,
            mape=float(np.mean(valid_mape)) if valid_mape else None,
            wape=float(np.mean(valid_wape)) if valid_wape else None,
            bias=float(np.mean(valid_bias)) if valid_bias else None,
            eval_points=points,
            evaluated_at=max(i.evaluated_at for i in items),
        ))
    return summaries


@router.post("/evaluate", status_code=202)
async def trigger_evaluation(
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(require_org_roles(["owner", "admin", "manager", "analyst"])),
):
    """Trigger the forecast-vs-actual evaluation for matured forecasts."""
    result = await ModelRegistryService.evaluate_matured_forecasts(db, org.id)
    return {"status": result.get("status", "ok"), "accuracy_rows": result.get("accuracy_rows", 0)}


@router.post("/flag-degradation/{artifact_id}", response_model=ModelArtifactResponse)
async def flag_degradation(
    artifact_id: str,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(require_org_roles(["owner", "admin", "manager"])),
):
    """Manually flag (or unflag) a model for degradation."""
    result = await db.execute(
        select(ModelArtifact).where(
            ModelArtifact.id == artifact_id,
            ModelArtifact.organization_id == org.id,
        )
    )
    artifact = result.scalar_one_or_none()
    if artifact is None:
        raise HTTPException(status_code=404, detail="Model artifact not found")
    artifact.degradation_flagged = not artifact.degradation_flagged
    await db.commit()
    await db.refresh(artifact)
    return artifact


