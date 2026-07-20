"""Report generation module for exporting combined analysis outputs.

Supports CSV and PDF exports using fpdf2.
"""

import pandas as pd
import os
from datetime import datetime
from src.utils import ensure_dir


class ReportGenerator:
    """Generates consolidated exportable reports combining forecast, inventory,
    and model insights into CSV and PDF formats."""

    @staticmethod
    def export_forecast_report(forecast_df, item_id, store_id, output_dir='reports/exports', fmt='csv'):
        """Export forecast data as CSV."""
        ensure_dir(output_dir)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base = f'forecast_{item_id}_{store_id}_{timestamp}'

        if fmt == 'csv':
            filepath = os.path.join(output_dir, f'{base}.csv')
            forecast_df.to_csv(filepath, index=False)
        else:
            raise ValueError(f'Unsupported format: {fmt}')

        print(f"Forecast report saved: {filepath}")
        return filepath

    @staticmethod
    def export_inventory_report(inventory_df, output_dir='reports/exports', fmt='csv'):
        """Export inventory recommendations as CSV."""
        ensure_dir(output_dir)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base = f'inventory_report_{timestamp}'

        if fmt == 'csv':
            filepath = os.path.join(output_dir, f'{base}.csv')
            inventory_df.to_csv(filepath, index=False)
        else:
            raise ValueError(f'Unsupported format: {fmt}')

        print(f"Inventory report saved: {filepath}")
        return filepath

    @staticmethod
    def export_model_comparison(comparison_df, output_dir='reports/exports', fmt='csv'):
        """Export model comparison metrics as CSV."""
        ensure_dir(output_dir)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base = f'model_comparison_{timestamp}'

        filepath = os.path.join(output_dir, f'{base}.csv')
        comparison_df.to_csv(filepath, index=False)

        print(f"Model comparison saved: {filepath}")
        return filepath

    @staticmethod
    def export_combined_summary(forecast_df=None, inventory_df=None,
                                 insights_text=None, output_dir='reports/exports'):
        """Generate a combined human-readable summary text file."""
        ensure_dir(output_dir)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = os.path.join(output_dir, f'combined_report_{timestamp}.txt')

        lines = []
        lines.append("=" * 60)
        lines.append("RETAILIQ — COMBINED REPORT")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 60)

        if forecast_df is not None:
            lines.append("\n--- DEMAND FORECAST ---")
            lines.append(f"Period: {forecast_df['date'].min()} to {forecast_df['date'].max()}")
            lines.append(f"Total forecasted demand: {forecast_df['predicted_sales'].sum():.2f}")
            lines.append(f"Average daily: {forecast_df['predicted_sales'].mean():.2f}")

        if inventory_df is not None:
            lines.append("\n--- INVENTORY SUMMARY ---")
            status_counts = inventory_df['status'].value_counts()
            for status, count in status_counts.items():
                lines.append(f"  {status}: {count}")
            lines.append(f"  Items needing reorder: {(inventory_df['recommended_order_qty'] > 0).sum()}")
            lines.append(f"  Total units to order: {inventory_df['recommended_order_qty'].sum():.0f}")

        if insights_text:
            lines.append(f"\n--- MODEL INSIGHTS ---\n{insights_text}")

        lines.append("\n" + "=" * 60)
        lines.append("END OF REPORT")
        lines.append("=" * 60)

        with open(filepath, 'w') as f:
            f.write('\n'.join(lines))

        print(f"Combined report saved: {filepath}")
        return filepath

    @staticmethod
    def export_pdf_report(forecast_df=None, inventory_df=None,
                           insights_text=None, output_dir='reports/exports'):
        """Generate a PDF report using fpdf2."""
        ensure_dir(output_dir)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = os.path.join(output_dir, f'retailiq_report_{timestamp}.pdf')

        try:
            from fpdf import FPDF

            pdf = FPDF()
            pdf.add_page()

            # ── Title ──
            pdf.set_font('Helvetica', 'B', 20)
            pdf.cell(0, 14, 'RetailIQ — Report', new_x="LMARGIN", new_y="NEXT", align='C')
            pdf.set_font('Helvetica', '', 10)
            pdf.cell(0, 8, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                     new_x="LMARGIN", new_y="NEXT", align='C')
            pdf.ln(8)

            # ── Forecast Table ──
            if forecast_df is not None and len(forecast_df) > 0:
                pdf.set_font('Helvetica', 'B', 14)
                pdf.cell(0, 12, 'Demand Forecast', new_x="LMARGIN", new_y="NEXT")
                pdf.ln(2)

                # Table header
                pdf.set_font('Helvetica', 'B', 9)
                pdf.set_fill_color(30, 58, 95)
                pdf.set_text_color(255, 255, 255)
                col_w = pdf.w / 2 - 20
                pdf.cell(col_w, 8, 'Date', border=1, align='C', fill=True)
                pdf.cell(col_w, 8, 'Predicted Sales', border=1, align='C', fill=True)
                pdf.ln()

                # Table rows (max 25 rows to keep it reasonable)
                pdf.set_font('Helvetica', '', 9)
                pdf.set_text_color(0, 0, 0)
                pdf.set_fill_color(245, 245, 245)
                for i, (_, row) in enumerate(forecast_df.head(25).iterrows()):
                    fill = i % 2 == 0
                    pdf.cell(col_w, 7, str(row['date'])[:10], border=1, align='C', fill=fill)
                    pdf.cell(col_w, 7, f"{row['predicted_sales']:.2f}", border=1, align='C', fill=fill)
                    pdf.ln()

                if len(forecast_df) > 25:
                    pdf.set_font('Helvetica', 'I', 8)
                    pdf.cell(0, 6, f'... and {len(forecast_df) - 25} more rows',
                             new_x="LMARGIN", new_y="NEXT", align='C')

                pdf.ln(6)

            # ── Inventory Summary ──
            if inventory_df is not None and len(inventory_df) > 0:
                pdf.set_font('Helvetica', 'B', 14)
                pdf.cell(0, 12, 'Inventory Summary', new_x="LMARGIN", new_y="NEXT")
                pdf.ln(2)

                status_counts = inventory_df['status'].value_counts()
                pdf.set_font('Helvetica', 'B', 9)
                pdf.set_fill_color(30, 58, 95)
                pdf.set_text_color(255, 255, 255)
                col_w2 = pdf.w / 2 - 20
                pdf.cell(col_w2, 8, 'Status', border=1, align='C', fill=True)
                pdf.cell(col_w2, 8, 'Count', border=1, align='C', fill=True)
                pdf.ln()

                pdf.set_font('Helvetica', '', 9)
                pdf.set_text_color(0, 0, 0)
                for i, (status, count) in enumerate(status_counts.items()):
                    fill = i % 2 == 0
                    pdf.cell(col_w2, 7, str(status), border=1, align='C', fill=fill)
                    pdf.cell(col_w2, 7, str(count), border=1, align='C', fill=fill)
                    pdf.ln()

                # Additional stats
                pdf.ln(3)
                pdf.set_font('Helvetica', '', 10)
                reorder_count = (inventory_df['recommended_order_qty'] > 0).sum()
                total_units = inventory_df['recommended_order_qty'].sum()
                pdf.cell(0, 7, f'Items needing reorder: {reorder_count}',
                         new_x="LMARGIN", new_y="NEXT")
                pdf.cell(0, 7, f'Total units to order: {total_units:.0f}',
                         new_x="LMARGIN", new_y="NEXT")
                pdf.ln(6)

            # ── Insights ──
            if insights_text:
                pdf.set_font('Helvetica', 'B', 14)
                pdf.cell(0, 12, 'Insights', new_x="LMARGIN", new_y="NEXT")
                pdf.ln(2)
                pdf.set_font('Helvetica', '', 10)
                pdf.multi_cell(0, 6, insights_text)

            # ── Footer ──
            pdf.ln(10)
            pdf.set_font('Helvetica', 'I', 8)
            pdf.set_text_color(128, 128, 128)
            pdf.cell(0, 5, f'RetailIQ — AI-Powered Retail Intelligence & Inventory Optimization Platform',
                     new_x="LMARGIN", new_y="NEXT", align='C')
            pdf.cell(0, 5, f'Generated by RetailIQ on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                     new_x="LMARGIN", new_y="NEXT", align='C')

            pdf.output(filepath)
            print(f"PDF report saved: {filepath}")

        except ImportError:
            # Fallback to text
            txt = ["PDF export requires fpdf2. Install with: pip install fpdf2"]
            txt.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            if forecast_df is not None:
                txt.append(f"\nForecast period: {forecast_df['date'].min()} to {forecast_df['date'].max()}")
                txt.append(f"Total forecast: {forecast_df['predicted_sales'].sum():.2f}")
            filepath = filepath.replace('.pdf', '.txt')
            with open(filepath, 'w') as f:
                f.write('\n'.join(txt))

        return filepath

    @staticmethod
    def export_combined_pdf(forecast_df=None, inventory_df=None,
                             feature_importance_df=None, model_metrics=None,
                             output_dir='reports/exports'):
        """Generate a combined multi-section PDF report using fpdf2."""
        ensure_dir(output_dir)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = os.path.join(output_dir, f'full_report_{timestamp}.pdf')

        try:
            from fpdf import FPDF

            pdf = FPDF()
            pdf.add_page()

            # ── Title ──
            pdf.set_font('Helvetica', 'B', 20)
            pdf.cell(0, 14, 'RetailIQ — Full Report', new_x="LMARGIN", new_y="NEXT", align='C')
            pdf.set_font('Helvetica', '', 10)
            pdf.cell(0, 8, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                     new_x="LMARGIN", new_y="NEXT", align='C')
            pdf.ln(8)

            # ── Forecast Section ──
            if forecast_df is not None and len(forecast_df) > 0:
                pdf.set_font('Helvetica', 'B', 14)
                pdf.cell(0, 12, 'Demand Forecast', new_x="LMARGIN", new_y="NEXT")
                pdf.ln(2)

                col_w = pdf.w / 2 - 20
                pdf.set_font('Helvetica', 'B', 9)
                pdf.set_fill_color(30, 58, 95)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(col_w, 8, 'Date', border=1, align='C', fill=True)
                pdf.cell(col_w, 8, 'Predicted Sales', border=1, align='C', fill=True)
                pdf.ln()

                pdf.set_font('Helvetica', '', 9)
                pdf.set_text_color(0, 0, 0)
                pdf.set_fill_color(245, 245, 245)
                for i, (_, row) in enumerate(forecast_df.head(25).iterrows()):
                    fill = i % 2 == 0
                    pdf.cell(col_w, 7, str(row['date'])[:10], border=1, align='C', fill=fill)
                    pdf.cell(col_w, 7, f"{row['predicted_sales']:.2f}", border=1, align='C', fill=fill)
                    pdf.ln()
                if len(forecast_df) > 25:
                    pdf.set_font('Helvetica', 'I', 8)
                    pdf.cell(0, 6, f'... and {len(forecast_df) - 25} more rows',
                             new_x="LMARGIN", new_y="NEXT", align='C')
                pdf.ln(6)

            # ── Inventory Section ──
            if inventory_df is not None and len(inventory_df) > 0:
                pdf.add_page()
                pdf.set_font('Helvetica', 'B', 14)
                pdf.cell(0, 12, 'Inventory Recommendations', new_x="LMARGIN", new_y="NEXT")
                pdf.ln(2)

                # Determine available columns for the table
                table_cols = ['item_id', 'store_id', 'status', 'safety_stock',
                              'reorder_point', 'eoq', 'recommended_order_qty']
                available = [c for c in table_cols if c in inventory_df.columns]
                col_count = len(available)
                col_w = (pdf.w - 20) / max(col_count, 1)

                pdf.set_font('Helvetica', 'B', 8)
                pdf.set_fill_color(30, 58, 95)
                pdf.set_text_color(255, 255, 255)
                for col in available:
                    pdf.cell(col_w, 8, col.replace('_', ' ').title(), border=1, align='C', fill=True)
                pdf.ln()

                pdf.set_font('Helvetica', '', 8)
                pdf.set_text_color(0, 0, 0)
                pdf.set_fill_color(245, 245, 245)
                for i, (_, row) in enumerate(inventory_df.head(25).iterrows()):
                    fill = i % 2 == 0
                    for col in available:
                        val = row[col]
                        if isinstance(val, float):
                            val = f"{val:.1f}"
                        pdf.cell(col_w, 6, str(val)[:12], border=1, align='C', fill=fill)
                    pdf.ln()
                if len(inventory_df) > 25:
                    pdf.set_font('Helvetica', 'I', 8)
                    pdf.cell(0, 6, f'... and {len(inventory_df) - 25} more rows',
                             new_x="LMARGIN", new_y="NEXT", align='C')
                pdf.ln(6)

            # ── Feature Importance Section ──
            if feature_importance_df is not None and len(feature_importance_df) > 0:
                pdf.add_page()
                pdf.set_font('Helvetica', 'B', 14)
                pdf.cell(0, 12, 'Feature Importance', new_x="LMARGIN", new_y="NEXT")
                pdf.ln(2)

                fi_cols = list(feature_importance_df.columns[:2])
                col_w = (pdf.w - 20) / 2
                pdf.set_font('Helvetica', 'B', 9)
                pdf.set_fill_color(30, 58, 95)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(col_w, 8, fi_cols[0].replace('_', ' ').title(), border=1, align='C', fill=True)
                pdf.cell(col_w, 8, fi_cols[1].replace('_', ' ').title(), border=1, align='C', fill=True)
                pdf.ln()

                pdf.set_font('Helvetica', '', 9)
                pdf.set_text_color(0, 0, 0)
                pdf.set_fill_color(245, 245, 245)
                for i, (_, row) in enumerate(feature_importance_df.head(20).iterrows()):
                    fill = i % 2 == 0
                    pdf.cell(col_w, 7, str(row[fi_cols[0]])[:20], border=1, align='C', fill=fill)
                    val = row[fi_cols[1]]
                    pdf.cell(col_w, 7, f"{val:.4f}" if isinstance(val, float) else str(val),
                             border=1, align='C', fill=fill)
                    pdf.ln()
                pdf.ln(6)

            # ── Model Metrics Section ──
            if model_metrics is not None:
                pdf.set_font('Helvetica', 'B', 14)
                pdf.cell(0, 12, 'Model Metrics', new_x="LMARGIN", new_y="NEXT")
                pdf.ln(2)
                pdf.set_font('Helvetica', '', 10)
                if isinstance(model_metrics, dict):
                    for key, val in model_metrics.items():
                        pdf.cell(0, 7, f"{key.replace('_', ' ').title()}: {val}",
                                 new_x="LMARGIN", new_y="NEXT")
                elif isinstance(model_metrics, pd.DataFrame):
                    metrics_df = model_metrics.head(10)
                    cols = list(metrics_df.columns)
                    col_w = (pdf.w - 20) / max(len(cols), 1)
                    pdf.set_font('Helvetica', 'B', 8)
                    pdf.set_fill_color(30, 58, 95)
                    pdf.set_text_color(255, 255, 255)
                    for c in cols:
                        pdf.cell(col_w, 8, c.replace('_', ' ').title(), border=1, align='C', fill=True)
                    pdf.ln()
                    pdf.set_font('Helvetica', '', 8)
                    pdf.set_text_color(0, 0, 0)
                    for i, (_, row) in enumerate(metrics_df.iterrows()):
                        fill = i % 2 == 0
                        for c in cols:
                            val = row[c]
                            pdf.cell(col_w, 6, f"{val:.4f}" if isinstance(val, float) else str(val),
                                     border=1, align='C', fill=fill)
                        pdf.ln()

            # ── Footer ──
            pdf.set_text_color(128, 128, 128)
            pdf.set_font('Helvetica', 'I', 8)
            pdf.cell(0, 5, f'RetailIQ — AI-Powered Retail Intelligence & Inventory Optimization Platform',
                     new_x="LMARGIN", new_y="NEXT", align='C')
            pdf.cell(0, 5, f'Generated by RetailIQ on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                     new_x="LMARGIN", new_y="NEXT", align='C')

            pdf.output(filepath)
            print(f"Combined PDF report saved: {filepath}")

        except ImportError:
            filepath = filepath.replace('.pdf', '.txt')
            with open(filepath, 'w') as f:
                f.write("PDF export requires fpdf2. Install with: pip install fpdf2\n")
                if model_metrics is not None:
                    if isinstance(model_metrics, dict):
                        for k, v in model_metrics.items():
                            f.write(f"{k}: {v}\n")

        return filepath
