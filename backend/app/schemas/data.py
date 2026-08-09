"""Pydantic schemas for the data ingestion endpoints."""

from pydantic import BaseModel, Field


class IngestResponse(BaseModel):
    job_id: str
    rows_imported: int
    products: int
    stores: int
    warnings: list[str] = []


class BulkIngestRequest(BaseModel):
    """A list of raw sales rows, e.g.:
    [{"item_id": "SKU1", "store_id": "STORE1", "date": "2026-07-01", "sales": 12, "sell_price": 4.5}, ...]
    """
    rows: list[dict] = Field(..., min_length=1, max_length=50000)


class OrgDataSummary(BaseModel):
    products: int
    stores: int
    sales_rows: int
    date_start: str | None
    date_end: str | None
    days_covered: int


