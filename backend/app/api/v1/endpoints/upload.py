"""CSV upload endpoints — upload, validate, preview, history."""

import os
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import pandas as pd

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.config import settings
from app.schemas.upload import UploadResponse, DatasetInfo
from app.models.user import User
from app.models.dataset import Dataset, DatasetStatus
from app.services.upload_service import DataValidator

router = APIRouter()


@router.post("/", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a CSV file. Validates, stores, and returns processing status."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    # Save file to disk
    upload_dir = os.path.join(settings.DATA_DIR, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    file_id = str(uuid.uuid4())
    safe_filename = f"{file_id}_{file.filename}"
    filepath = os.path.join(upload_dir, safe_filename)

    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    # Validate
    validation = DataValidator.validate_csv(filepath)

    # Create dataset record
    dataset = Dataset(
        filename=safe_filename,
        original_filename=file.filename,
        row_count=validation["row_count"],
        column_count=validation["column_count"],
        file_size_kb=round(len(content) / 1024, 2),
        status=DatasetStatus.VALIDATING if validation["valid"] else DatasetStatus.ERROR,
        error_message="; ".join(validation["errors"]) if validation["errors"] else None,
        uploaded_by=current_user.id,
    )

    db.add(dataset)
    await db.flush()
    await db.refresh(dataset)

    return UploadResponse(
        id=dataset.id,
        filename=file.filename,
        row_count=validation["row_count"],
        column_count=validation["column_count"],
        file_size_kb=dataset.file_size_kb,
        status=dataset.status.value,
        warnings=validation.get("warnings", []),
        errors=validation.get("errors", []),
    )


@router.get("/history", response_model=list[DatasetInfo])
async def upload_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get upload history for the current user."""
    result = await db.execute(
        select(Dataset).where(Dataset.uploaded_by == current_user.id).order_by(Dataset.created_at.desc()).limit(50)
    )
    return result.scalars().all()


@router.post("/{dataset_id}/clean")
async def clean_dataset(
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Auto-clean a previously uploaded dataset."""
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    filepath = os.path.join(settings.DATA_DIR, "uploads", dataset.filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found on disk")

    df = pd.read_csv(filepath)
    validation_result = DataValidator.validate_csv(filepath)
    df_clean = DataValidator.auto_clean(df, validation_result)

    # Save cleaned version
    clean_path = os.path.join(settings.DATA_DIR, "processed", f"cleaned_{dataset.filename}")
    os.makedirs(os.path.dirname(clean_path), exist_ok=True)
    df_clean.to_csv(clean_path, index=False)

    dataset.status = DatasetStatus.CLEANED
    dataset.row_count = len(df_clean)
    await db.flush()

    return {"status": "cleaned", "row_count": len(df_clean), "path": clean_path}


