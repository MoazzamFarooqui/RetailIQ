"""Pydantic schemas for file upload endpoints."""

from datetime import datetime
from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    id: str
    filename: str
    row_count: int
    column_count: int
    file_size_kb: float
    status: str
    warnings: list[str] = []
    errors: list[str] = []


class DatasetInfo(BaseModel):
    id: str
    original_filename: str
    row_count: int | None
    column_count: int | None
    file_size_kb: float | None
    status: str
    uploaded_by: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ValidationResult(BaseModel):
    valid: bool
    row_count: int
    column_count: int
    columns: list[str]
    date_range: dict | None = None
    sales_stats: dict | None = None
    warnings: list[str] = []
    errors: list[str] = []
