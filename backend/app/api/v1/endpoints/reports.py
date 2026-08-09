"""Reporting API — professional report generation and export."""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_org, require_org_roles
from app.models.user import User
from app.models.organization import Organization
from app.models.membership import OrganizationMember
from app.services.reporting_service import ReportingService

router = APIRouter()


@router.get("/{report_type}")
async def get_report(
    report_type: str,
    include_advisor: bool = False,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
):
    """Get a report payload as JSON (executive | inventory | forecast | ai_insights)."""
    if report_type not in ReportingService.REPORT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unknown report type. Use one of {ReportingService.REPORT_TYPES}")
    try:
        report = await ReportingService.build_report(db, org, report_type, advisor_key=include_advisor)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return report


@router.get("/{report_type}/export")
async def export_report(
    report_type: str,
    format: str = "pdf",
    include_advisor: bool = False,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
):
    """Export a report as CSV or PDF."""
    if report_type not in ReportingService.REPORT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unknown report type. Use one of {ReportingService.REPORT_TYPES}")
    if format not in ("csv", "pdf"):
        raise HTTPException(status_code=400, detail="format must be 'csv' or 'pdf'")

    try:
        report = await ReportingService.build_report(db, org, report_type, advisor_key=include_advisor)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if format == "csv":
        content = ReportingService.to_csv(report)
        media = "text/csv"
        ext = "csv"
    else:
        content = ReportingService.to_pdf(report)
        media = "application/pdf"
        ext = "pdf"

    filename = f"retailiq_{report_type}_{org.slug}.{ext}"
    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


