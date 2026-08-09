"""AI Business Advisor API — data-grounded Q&A."""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_org
from app.schemas.advisor import (
    AdvisorAskRequest, AdvisorResponse, AdvisorHistoryItem,
)
from app.models.user import User
from app.models.organization import Organization
from app.models.advisor_conversation import AdvisorConversation
from app.services.advisor_service import AdvisorService

router = APIRouter()


@router.post("/ask", response_model=AdvisorResponse)
async def ask_advisor(
    request: AdvisorAskRequest,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
):
    """Ask the AI Business Advisor a question grounded in the org's data."""
    result = await AdvisorService.answer(
        db, org, current_user.id, request.question, request.history,
    )

    conversation = AdvisorConversation(
        organization_id=org.id,
        user_id=current_user.id,
        question=request.question,
        answer=result["answer"],
        mode=result.get("mode", "rules"),
        grounded=result.get("grounded", True),
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    return AdvisorResponse(
        answer=result["answer"],
        mode=result.get("mode", "rules"),
        grounded=result.get("grounded", True),
        fallback_reason=result.get("fallback_reason"),
        snapshot_size=result.get("snapshot_size"),
        conversation_id=conversation.id,
        created_at=conversation.created_at,
    )


@router.get("/history", response_model=list[AdvisorHistoryItem])
async def advisor_history(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
):
    """Get the user's recent advisor conversations in this org."""
    result = await db.execute(
        select(AdvisorConversation)
        .where(
            AdvisorConversation.organization_id == org.id,
            AdvisorConversation.user_id == current_user.id,
        )
        .order_by(desc(AdvisorConversation.created_at))
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/snapshot")
async def advisor_snapshot(
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
):
    """Inspect the data snapshot the advisor uses as grounding (dev/debug)."""
    snapshot = await AdvisorService.build_snapshot(db, org)
    return snapshot

