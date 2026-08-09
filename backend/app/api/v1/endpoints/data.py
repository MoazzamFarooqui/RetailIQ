"""Data ingestion endpoints — upload, bulk JSON, and webhook push.

v3's move toward automated data integration: uploads still work, and now
machines can push sales rows continuously via the API or a per-org webhook
endpoint, keeping forecasts and inventory recommendations fresh.
"""

import os
import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import pandas as pd

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_org, require_org_roles
from app.core.config import settings
from app.schemas.data import IngestResponse, OrgDataSummary, BulkIngestRequest
from app.models.user import User
from app.models.organization import Organization
from app.models.membership import OrganizationMember
from app.models.ingestion import WebhookSource
from app.models.dataset import Dataset, DatasetStatus
from app.services.data_service import TenantDataService
from app.services.upload_service import DataValidator

router = APIRouter()


@router.post("/upload", response_model=IngestResponse)
async def upload_and_ingest(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
):
    """Upload a CSV/Excel file, validate it, and ingest into the org's MySQL tables."""
    is_excel = file.filename.lower().endswith((".xlsx", ".xls"))
    if not (file.filename.endswith(".csv") or is_excel):
        raise HTTPException(status_code=400, detail="Only CSV or Excel files are supported")

    upload_dir = os.path.join(settings.DATA_DIR, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    file_id = str(uuid.uuid4())
    safe_filename = f"{file_id}_{os.path.basename(file.filename)}"
    filepath = os.path.join(upload_dir, safe_filename)

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit")
    with open(filepath, "wb") as f:
        f.write(content)

    # Validate + clean
    try:
        if is_excel:
            df = pd.read_excel(filepath)
            validation = DataValidator.validate_dataframe(df)
        else:
            df = pd.read_csv(filepath)
            validation = DataValidator.validate_dataframe(df)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot read file: {str(e)}")

    if not validation["valid"]:
        # Record the failed dataset
        dataset = Dataset(
            organization_id=org.id,
            filename=safe_filename,
            original_filename=file.filename,
            row_count=validation["row_count"],
            column_count=validation["column_count"],
            file_size_kb=round(len(content) / 1024, 2),
            status=DatasetStatus.ERROR,
            error_message="; ".join(validation["errors"]),
            uploaded_by=current_user.id,
        )
        db.add(dataset)
        await db.commit()
        raise HTTPException(status_code=400, detail="; ".join(validation["errors"]))

    df_clean = DataValidator.auto_clean(df, validation)

    # Ingest into MySQL (idempotent upsert)
    result = await TenantDataService.ingest_dataframe(
        db, org.id, df_clean, source_type="csv",
        source=file.filename, created_by=current_user.id,
    )

    # Record the dataset
    dataset = Dataset(
        organization_id=org.id,
        filename=safe_filename,
        original_filename=file.filename,
        row_count=len(df_clean),
        column_count=len(df_clean.columns),
        file_size_kb=round(len(content) / 1024, 2),
        status=DatasetStatus.PROCESSED,
        uploaded_by=current_user.id,
    )
    db.add(dataset)
    await db.commit()

    return IngestResponse(
        job_id=result["job_id"],
        rows_imported=result["rows_imported"],
        products=result["products"],
        stores=result["stores"],
        warnings=validation.get("warnings", []),
    )


@router.post("/bulk", response_model=IngestResponse)
async def bulk_ingest(
    request: BulkIngestRequest,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
):
    """Ingest sales rows directly as JSON (API integration)."""
    if not request.rows:
        raise HTTPException(status_code=400, detail="No rows provided")

    result = await TenantDataService.ingest_rows_json(
        db, org.id, request.rows, created_by=current_user.id,
    )
    return IngestResponse(
        job_id=result["job_id"],
        rows_imported=result["rows_imported"],
        products=result["products"],
        stores=result["stores"],
    )


@router.post("/webhook/{webhook_id}", response_model=IngestResponse)
async def webhook_ingest(
    webhook_id: str,
    request: BulkIngestRequest,
    db: AsyncSession = Depends(get_db),
    x_api_key: Annotated[str | None, Header(alias="X-Api-Key")] = None,
):
    """Machine-to-machine ingestion via a registered webhook (API key auth)."""
    result = await db.execute(select(WebhookSource).where(WebhookSource.id == webhook_id))
    source = result.scalar_one_or_none()
    if source is None or not source.is_active:
        raise HTTPException(status_code=404, detail="Webhook not found")

    if not x_api_key or x_api_key != source.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if not request.rows:
        raise HTTPException(status_code=400, detail="No rows provided")

    ingest = await TenantDataService.ingest_rows_json(db, source.organization_id, request.rows)
    return IngestResponse(
        job_id=ingest["job_id"],
        rows_imported=ingest["rows_imported"],
        products=ingest["products"],
        stores=ingest["stores"],
    )


@router.get("/summary", response_model=OrgDataSummary)
async def org_data_summary(
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
):
    """Get a summary of what data the org has loaded."""
    summary = await TenantDataService.org_data_summary(db, org.id)
    return OrgDataSummary(**summary)


# ── Webhook source management ─────────────────────────────────────────────────

@router.post("/webhooks", status_code=status.HTTP_201_CREATED)
async def create_webhook_source(
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    membership: OrganizationMember = Depends(require_org_roles(["owner", "admin"])),
):
    """Register a webhook source and return its API key (shown once)."""
    import secrets
    from app.models.ingestion import WebhookSource

    source = WebhookSource(
        organization_id=org.id,
        name="API Integration",
        api_key=secrets.token_urlsafe(32),
        is_active=True,
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return {"id": source.id, "name": source.name, "api_key": source.api_key, "endpoint": f"/api/v1/data/webhook/{source.id}"}


@router.get("/webhooks")
async def list_webhook_sources(
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    membership: OrganizationMember = Depends(require_org_roles(["owner", "admin"])),
):
    """List the org's webhook sources (without full API keys)."""
    from app.models.ingestion import WebhookSource

    result = await db.execute(
        select(WebhookSource).where(WebhookSource.organization_id == org.id)
    )
    sources = result.scalars().all()
    return [
        {"id": s.id, "name": s.name, "is_active": s.is_active,
         "created_at": s.created_at.isoformat(), "endpoint": f"/api/v1/data/webhook/{s.id}"}
        for s in sources
    ]


@router.delete("/webhooks/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_webhook_source(
    webhook_id: str,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    membership: OrganizationMember = Depends(require_org_roles(["owner", "admin"])),
):
    """Deactivate a webhook source."""
    from app.models.ingestion import WebhookSource

    result = await db.execute(
        select(WebhookSource).where(WebhookSource.id == webhook_id, WebhookSource.organization_id == org.id)
    )
    source = result.scalar_one_or_none()
    if source is None:
        raise HTTPException(status_code=404, detail="Webhook not found")
    source.is_active = False
    await db.commit()

