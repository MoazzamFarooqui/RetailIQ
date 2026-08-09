"""Executive Dashboard service — what business owners actually need to see.

Revenue, growth, inventory value, forecast accuracy, financial risks, major
opportunities, and a prioritized action list — with the WHY behind each
action, so the dashboard never just shows charts.
"""

import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class ExecutiveService:
    """Aggregate executive metrics + prioritized actions for an org."""

    @staticmethod
    def executive_overview(df: pd.DataFrame, financials: dict | None = None,
                           accuracy: list | None = None,
                           alerts: list | None = None) -> dict:
        """Compute the executive dashboard payload."""
        if df.empty:
            return {"error": "No data"}

        daily = df.groupby("date")["sales"].sum()
        total_sales = float(df["sales"].sum())
        revenue = float((df["sales"] * df["sell_price"].fillna(0)).sum()) if "sell_price" in df.columns else None
        days = len(daily)
        avg_daily = total_sales / days if days else 0

        # Growth: last 28d vs prior 28d
        last_28 = daily.tail(28).sum()
        prior_28 = daily.iloc[-56:-28].sum()
        growth_pct = ((last_28 - prior_28) / prior_28 * 100) if prior_28 > 0 else None

        # Products & stores
        products = int(df["item_id"].nunique())
        stores = int(df["store_id"].nunique())

        # Forecast accuracy (mean WAPE across horizons if provided)
        forecast_accuracy = None
        if accuracy:
            valid = [a for a in accuracy if a.get("wape") is not None]
            if valid:
                forecast_accuracy = round(float(np.mean([a["wape"] for a in valid])), 1)

        # Financial risks from the purchase engine financials
        risks = []
        if financials:
            if financials.get("total_overstock_capital", 0) > 1000:
                risks.append({
                    "type": "overstock_capital",
                    "severity": "high" if financials["total_overstock_capital"] > 10000 else "medium",
                    "amount": financials["total_overstock_capital"],
                    "message": f"${financials['total_overstock_capital']:,.0f} tied up in overstock",
                })
            if financials.get("total_stockout_loss_risk", 0) > 500:
                risks.append({
                    "type": "stockout_loss",
                    "severity": "high",
                    "amount": financials["total_stockout_loss_risk"],
                    "message": f"${financials['total_stockout_loss_risk']:,.0f} at risk from stockouts",
                })
            if financials.get("total_carrying_cost", 0) > 1000:
                risks.append({
                    "type": "carrying_cost",
                    "severity": "low",
                    "amount": financials["total_carrying_cost"],
                    "message": f"${financials['total_carrying_cost']:,.0f} annual carrying cost",
                })

        # Opportunities: top growing products / stores
        opportunities = []
        prod_growth = df.groupby("item_id")["sales"].agg(lambda s: s.tail(28).sum() - s.iloc[-56:-28].sum())
        prod_growth = prod_growth.sort_values(ascending=False).head(3)
        for item, growth_units in prod_growth.items():
            if growth_units > 0:
                opportunities.append({
                    "type": "product_growth",
                    "item_id": item,
                    "units": float(growth_units),
                    "message": f"{item} growing (+{growth_units:.0f} units vs prior month)",
                })

        # ── Prioritized actions ────────────────────────────────────────────
        actions = []
        if alerts:
            for alert in alerts[:5]:
                actions.append({
                    "priority": 1 if alert.severity.value in ("critical", "high") else 2,
                    "type": alert.alert_type.value,
                    "title": alert.title,
                    "detail": alert.message,
                    "severity": alert.severity.value,
                })
        if financials and financials.get("items_to_reorder", 0) > 0:
            actions.append({
                "priority": 2,
                "type": "reorder",
                "title": f"{financials['items_to_reorder']} items need reordering",
                "detail": f"Estimated order value ${financials.get('total_recommended_order_value', 0):,.0f}",
                "severity": "medium",
            })
        if growth_pct is not None and growth_pct < -10:
            actions.append({
                "priority": 1,
                "type": "revenue_decline",
                "title": f"Revenue down {abs(growth_pct):.0f}% month-over-month",
                "detail": "Investigate demand shifts, stockouts, or pricing before it compounds.",
                "severity": "high",
            })
        actions.sort(key=lambda a: a["priority"])

        return {
            "total_sales": round(total_sales, 2),
            "revenue": round(revenue, 2) if revenue is not None else None,
            "avg_daily_sales": round(avg_daily, 2),
            "growth_pct": round(growth_pct, 1) if growth_pct is not None else None,
            "products": products,
            "stores": stores,
            "days_covered": days,
            "forecast_accuracy_wape": forecast_accuracy,
            "inventory_value": round(financials.get("total_inventory_value", 0), 2) if financials else None,
            "overstock_capital": round(financials.get("total_overstock_capital", 0), 2) if financials else None,
            "potential_savings": round(financials.get("total_potential_savings", 0), 2) if financials else None,
            "risks": risks,
            "opportunities": opportunities,
            "actions": actions,
            "generated_at": datetime.now().isoformat(),
        }

