"""Report generation service — CSV and PDF exports."""

import logging
import os
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates exportable reports combining forecast, inventory, and model insights."""

    @staticmethod
    def export_forecast_report(forecast_df, item_id, store_id, output_dir="reports/exports"):
        """Export forecast data as CSV."""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(output_dir, f"forecast_{item_id}_{store_id}_{timestamp}.csv")
        forecast_df.to_csv(filepath, index=False)
        logger.info(f"Forecast report saved: {filepath}")
        return filepath

    @staticmethod
    def export_inventory_report(inventory_df, output_dir="reports/exports"):
        """Export inventory recommendations as CSV."""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(output_dir, f"inventory_report_{timestamp}.csv")
        inventory_df.to_csv(filepath, index=False)
        logger.info(f"Inventory report saved: {filepath}")
        return filepath

    @staticmethod
    def export_pdf_report(forecast_df=None, inventory_df=None, insights_text=None, output_dir="reports/exports"):
        """Generate a PDF report using fpdf2."""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(output_dir, f"retailiq_report_{timestamp}.pdf")

        try:
            from fpdf import FPDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 20)
            pdf.cell(0, 14, "RetailIQ — Report", new_x="LMARGIN", new_y="NEXT", align="C")
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 8, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", new_x="LMARGIN", new_y="NEXT", align="C")
            pdf.ln(8)

            if forecast_df is not None and len(forecast_df) > 0:
                pdf.set_font("Helvetica", "B", 14)
                pdf.cell(0, 12, "Demand Forecast", new_x="LMARGIN", new_y="NEXT")
                pdf.ln(2)
                col_w = pdf.w / 2 - 20
                pdf.set_font("Helvetica", "B", 9)
                pdf.set_fill_color(30, 58, 95)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(col_w, 8, "Date", border=1, align="C", fill=True)
                pdf.cell(col_w, 8, "Predicted Sales", border=1, align="C", fill=True)
                pdf.ln()
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(0, 0, 0)
                pdf.set_fill_color(245, 245, 245)
                for i, (_, row) in enumerate(forecast_df.head(25).iterrows()):
                    pdf.cell(col_w, 7, str(row["date"])[:10], border=1, align="C", fill=(i % 2 == 0))
                    pdf.cell(col_w, 7, f"{row['predicted_sales']:.2f}", border=1, align="C", fill=(i % 2 == 0))
                    pdf.ln()
                if len(forecast_df) > 25:
                    pdf.set_font("Helvetica", "I", 8)
                    pdf.cell(0, 6, f"... and {len(forecast_df) - 25} more rows", new_x="LMARGIN", new_y="NEXT", align="C")

            if inventory_df is not None and len(inventory_df) > 0:
                pdf.add_page()
                pdf.set_font("Helvetica", "B", 14)
                pdf.cell(0, 12, "Inventory Recommendations", new_x="LMARGIN", new_y="NEXT")
                pdf.ln(2)
                available = [c for c in ["item_id", "store_id", "status", "safety_stock", "reorder_point", "eoq", "recommended_order_qty"] if c in inventory_df.columns]
                col_w = (pdf.w - 20) / max(len(available), 1)
                pdf.set_font("Helvetica", "B", 8)
                pdf.set_fill_color(30, 58, 95)
                pdf.set_text_color(255, 255, 255)
                for col in available:
                    pdf.cell(col_w, 8, col.replace("_", " ").title(), border=1, align="C", fill=True)
                pdf.ln()
                pdf.set_font("Helvetica", "", 8)
                pdf.set_text_color(0, 0, 0)
                for i, (_, row) in enumerate(inventory_df.head(25).iterrows()):
                    for col in available:
                        val = row[col]
                        pdf.cell(col_w, 6, f"{val:.1f}" if isinstance(val, float) else str(val)[:12], border=1, align="C", fill=(i % 2 == 0))
                    pdf.ln()

            if insights_text:
                pdf.set_font("Helvetica", "B", 14)
                pdf.cell(0, 12, "Insights", new_x="LMARGIN", new_y="NEXT")
                pdf.ln(2)
                pdf.set_font("Helvetica", "", 10)
                pdf.multi_cell(0, 6, insights_text)

            pdf.set_text_color(128, 128, 128)
            pdf.set_font("Helvetica", "I", 8)
            pdf.cell(0, 5, "RetailIQ — AI-Powered Retail Intelligence Platform", new_x="LMARGIN", new_y="NEXT", align="C")
            pdf.output(filepath)
            logger.info(f"PDF report saved: {filepath}")
        except ImportError:
            filepath = filepath.replace(".pdf", ".txt")
            with open(filepath, "w") as f:
                f.write("PDF export requires fpdf2.\n")
                if forecast_df is not None:
                    f.write(f"\nForecast period: {forecast_df['date'].min()} to {forecast_df['date'].max()}\n")
                    f.write(f"Total forecast: {forecast_df['predicted_sales'].sum():.2f}\n")

        return filepath


