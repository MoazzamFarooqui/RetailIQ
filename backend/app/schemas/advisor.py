"""Pydantic schemas for the AI Business Advisor."""

from datetime import datetime
from pydantic import BaseModel, Field


class AdvisorAskRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=2000)
    history: list[dict] = Field(default_factory=list, description="Prior turns [{role, content}]")


class AdvisorResponse(BaseModel):
    answer: str
    mode: str  # claude | rules
    grounded: bool
    fallback_reason: str | None = None
    snapshot_size: int | None = None
    conversation_id: str | None = None
    created_at: datetime | None = None


class AdvisorHistoryItem(BaseModel):
    id: str
    question: str
    answer: str
    mode: str
    created_at: datetime

    model_config = {"from_attributes": True}

