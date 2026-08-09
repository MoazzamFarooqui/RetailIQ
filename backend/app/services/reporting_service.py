"""Professional reporting service — executive, inventory, forecast, AI insight reports.

Generates org-scoped reports (CSV + PDF) with automatically-written executive
summaries, plus a report catalog so businesses can share with management.
"""

import io
import json
import logging
from datetime import datetime, timezone

import pandas as pd

from app.services.executive_service import ExecutiveService
from app.services.purchase_engine import PurchaseDecisionEngine
from app.services.data_service import TenantDataService
from app.services.advisor_service import AdvisorService

logger = logging.getLogger(__name__)


class ReportingService:
    """Build report payloads and file exports from org data."""

    REPORT_TYPES = ["executive", "inventory", "forecast", "ai_insights"]

    # ── Auto-summary generation ────────────────────────────────────────────

    @staticmethod
    def _auto_summary(executive: dict, financials: dict | None) -> str:
        """Write a management-readable summary from the executive metrics."""
        parts = []
        growth = executive.get("growth_pct")
        if growth is not None:
            direction = "grew" if growth >= 0 else "declined"
            parts.append(f"Sales {direction} {abs(growth):.1f}% month-over-month "
                         f"({executive.get('total_sales', 0):,.0f} units total).")
        else:
            parts.append(f"Total sales {executive.get('total_sales', 0):,.0f} units.")

        if executive.get("revenue") is not None:
            parts.append(f"Estimated revenue {executive['revenue']:,.0f}.")

        if financials:
            parts.append(f"Inventory value {financials.get('total_inventory_value', 0):,.0f} "
                         f"with {financials.get('total_overstock_capital', 0):,.0f} tied up in overstock "
                         f"and {financials.get('total_stockout_loss_risk', 0):,.0f} at stockout risk.")

        acc = executive.get("forecast_accuracy_wape")
        if acc is not None:
            parts.append(f"Forecast accuracy (WAPE) {acc:.1f}%.")

        risks = executive.get("risks", [])
        if risks:
            parts.append("Key risks: " + "; ".join(r["message"] for r in risks[:3]) + ".")

        actions = executive.get("actions", [])
        if actions:
            parts.append("Priority actions: " + "; ".join(a["title"] for a in actions[:4]) + ".")

        return " ".join(parts) if parts else "No data available."

    # ── Report payloads ────────────────────────────────────────────────────

    @staticmethod
    async def build_report(db, org, report_type: str, advisor_key: bool = False) -> dict:
        """Build a full report payload for the given type."""
        if report_type not in ReportingService.REPORT_TYPES:
            raise ValueError(f"Unknown report type: {report_type}")

        sales_df = await TenantDataService.load_sales_df(db, org.id)
        if sales_df.empty:
            raise ValueError("No data for this organization")

        inv_df = await TenantDataService.load_inventory_df(db, org.id)
        if not inv_df.empty:
            sales_df = sales_df.merge(inv_df, on=["item_id", "store_id"], how="left")
        if "current_stock" not in sales_df.columns or sales_df["current_stock"].isna().all():
            stock = sales_df.groupby(["item_id", "store_id"])["sales"].transform(lambda x: max(x.tail(28).sum() * 1.5, 10))
            sales_df = sales_df.copy()
            sales_df["current_stock"] = stock
        else:
            sales_df["current_stock"] = sales_df["current_stock"].fillna(0)

        engine = PurchaseDecisionEngine()
        decisions = engine.generate_purchase_decisions(sales_df)
        financials = engine.financial_summary(decisions)

        # Executive metrics + accuracy
        from app.models.model_registry import ForecastAccuracy
        from sqlalchemy import select
        acc_records = (await db.execute(
            select(ForecastAccuracy).where(ForecastAccuracy.organization_id == org.id)
        )).scalars().all()
        accuracy = [{"wape": a.wape} for a in acc_records if a.wape is not None]

        from app.services.alert_service import AlertService
        alerts = await AlertService.list_alerts(db, org.id, limit=10)
        executive = ExecutiveService.executive_overview(sales_df, financials, accuracy, alerts)

        summary = ReportingService._auto_summary(executive, financials)

        report = {
            "organization": org.name,
            "report_type": report_type,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": summary,
            "executive": executive,
            "financials": financials,
        }

        if report_type in ("inventory", "executive"):
            report["decisions"] = decisions.head(200).to_dict("records")

        if report_type == "forecast":
            report["decisions"] = None
            report["active_model"] = None
            from app.services.model_registry_service import ModelRegistryService
            active = await ModelRegistryService.get_active(db, org.id)
            if active:
                report["active_model"] = {
                    "algorithm": active.algorithm, "version": active.version,
                    "wape": active.wape, "live_wape": active.live_wape,
                    "trained_at": active.trained_at.isoformat() if active.trained_at else None,
                    "data_rows": active.data_rows, "features": active.features_used,
                }
            report["accuracy"] = [{"horizon_days": a.horizon_days, "wape": a.wape, "mae": a.mae}
                                  for a in acc_records[:50]]

        if report_type == "ai_insights" and advisor_key:
            # Ask the advisor for a narrative
            result = await AdvisorService.answer(
                db, org, "report",
                "Summarize the current state of this business, key risks, and recommended actions.",
            )
            report["advisor_answer"] = result["answer"]
            report["advisor_mode"] = result.get("mode")

        return report

    # ── File exports ───────────────────────────────────────────────────────

    @staticmethod
    def to_csv(report: dict) -> bytes:
        """Serialize a report's tabular sections to CSV bytes."""
        buf = io.StringIO()
        buf.write(f"# RetailIQ Report — {report['report_type']} — {report['organization']}\n")
        buf.write(f"# Generated: {report['generated_at']}\n")
        buf.write(f"# Summary: {report['summary']}\n\n")

        decisions = report.get("decisions")
        if decisions:
            df = pd.DataFrame(decisions)
            # Drop noisy columns, keep the essentials
            keep = [c for c in ["item_id", "store_id", "status", "avg_daily_demand", "safety_stock",
                                 "reorder_point", "recommended_order_qty", "order_today",
                                 "stockout_in_days", "inventory_value", "overstock_capital",
                                 "stockout_revenue_loss", "potential_savings"] if c in df.columns]
            df[keep].to_csv(buf, index=False)
        return buf.getvalue().encode("utf-8")

    @staticmethod
    def _pdf_safe(text: str) -> str:
        """Strip characters outside Latin-1 (Helvetica can't render em dashes etc.)."""
        return "".join(c if ord(c) < 256 else "-" for c in text)

    @staticmethod
    def to_pdf(report: dict) -> bytes:
        """Serialize a report to a professional PDF (fpdf2).

        Returns real `bytes`: fpdf2's `output()` yields a `bytearray`, and
        FastAPI's `Response` treats any non-`str` content as text (calling
        `.encode()`), which crashes with `AttributeError: 'bytearray' object
        has no attribute 'encode'`. Converting to bytes makes the response
        binary and the download work.
        """
        from fpdf import FPDF

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 18)
        pdf.cell(0, 12, ReportingService._pdf_safe(f"RetailIQ — {report['report_type'].replace('_', ' ').title()} Report"),
                 new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 8, f"{report['organization']} | Generated {report['generated_at'][:19]}",
                 new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(4)

        # Summary
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, "Executive Summary", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, ReportingService._pdf_safe(report["summary"]))
        pdf.ln(3)

        # Executive metrics
        exec_ = report.get("executive", {})
        metrics = [
            ("Total Sales", f"{exec_.get('total_sales', 0):,.0f}"),
            ("Revenue", f"${exec_.get('revenue', 0):,.0f}"),
            ("Growth MoM", f"{exec_.get('growth_pct', 0)}%"),
            ("Products", str(exec_.get("products", 0))),
            ("Stores", str(exec_.get("stores", 0))),
            ("Forecast WAPE", f"{exec_.get('forecast_accuracy_wape', 'N/A')}%"),
        ]
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 8, "Key Metrics", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        for label, value in metrics:
            pdf.cell(pdf.w / 2 - 10, 7, f"{label}:", border=1)
            pdf.cell(pdf.w / 2 - 10, 7, value, border=1, new_x="LMARGIN", new_y="NEXT")

        # Actions
        actions = exec_.get("actions", [])
        if actions:
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 10, "Priority Actions", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            for a in actions[:8]:
                pdf.multi_cell(0, 6, ReportingService._pdf_safe(f"[{a['severity']}] {a['title']} — {a['detail']}"))

        # Decisions table
        decisions = report.get("decisions")
        if decisions:
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 10, "Inventory Decisions", new_x="LMARGIN", new_y="NEXT")
            df = pd.DataFrame(decisions[:60])
            cols = [c for c in ["item_id", "store_id", "status", "recommended_order_qty",
                                 "stockout_in_days", "inventory_value"] if c in df.columns]
            col_w = (pdf.w - 20) / max(len(cols), 1)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_fill_color(30, 58, 95)
            pdf.set_text_color(255, 255, 255)
            for c in cols:
                pdf.cell(col_w, 7, c, border=1, align="C", fill=True)
            pdf.ln()
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(0, 0, 0)
            for i, (_, row) in enumerate(df.iterrows()):
                for c in cols:
                    val = row[c]
                    text = f"{val:,.0f}" if isinstance(val, (int, float)) and c not in ("item_id", "store_id", "status") else str(val)
                    pdf.cell(col_w, 6, ReportingService._pdf_safe(text[:20]), border=1, align="C", fill=(i % 2 == 0))
                pdf.ln()

        # Advisor narrative
        if report.get("advisor_answer"):
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 10, "AI Business Advisor", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            pdf.multi_cell(0, 6, ReportingService._pdf_safe(report["advisor_answer"]))

        return bytes(pdf.output())

