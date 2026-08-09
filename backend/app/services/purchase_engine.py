"""Purchase Decision Engine — tells a retailer exactly what to reorder, when, and the money behind it.

Extends the classic InventoryOptimizer with:
  - Order quantity (reorder point − stock + lead-time demand)
  - Order date (when to place the order so it arrives before stockout)
  - Financial intelligence: inventory value, overstock capital, stockout
    revenue loss, carrying cost, turnover, days of inventory, savings
  - What-if simulation: recompute safety stock/orders/risk/value under
    changed demand growth, lead time, service level, or holding cost.
"""

import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from app.services.inventory_optimizer import InventoryOptimizer

logger = logging.getLogger(__name__)


class PurchaseDecisionEngine(InventoryOptimizer):
    """Inventory recommendations + financial intelligence + what-if simulation."""

    def __init__(self, service_level=0.95, lead_time_days=7, order_cost=100.0,
                 holding_cost_rate=0.25, unit_cost=10.0, demand_growth=0.0):
        super().__init__(service_level=service_level)
        self.lead_time_days = lead_time_days
        self.order_cost = order_cost
        self.holding_cost_rate = holding_cost_rate
        self.unit_cost = unit_cost
        self.demand_growth = demand_growth  # fraction, e.g. 0.05 = +5%/yr

    # ── Per-item purchase decision ──────────────────────────────────────────

    def purchase_decision_for_item(self, current_stock, historical_sales,
                                   demand_multiplier=1.0, unit_price=None,
                                   annual_units=None, holding_cost_rate=None):
        """Full purchase decision + financials for one item-store.

        Returns everything the retailer needs to act:
          - demand stats, safety stock, reorder point, EOQ
          - recommended order qty, order date, expected stockout date
          - financial: inventory value, overstock capital, stockout revenue
            loss, carrying cost, days of inventory, turnover
        """
        opt = self.optimize_inventory_for_item(
            historical_sales, lead_time_days=self.lead_time_days,
            demand_multiplier=demand_multiplier * (1 + self.demand_growth),
        )

        avg_demand = opt["avg_demand"]
        safety_stock = opt["safety_stock"]
        reorder_point = opt["reorder_point"]
        eoq = opt["eoq"]

        # Order quantity: cover reorder point + lead-time demand, minus what's on hand
        lead_time_demand = avg_demand * self.lead_time_days
        recommended_order_qty = max(0.0, (reorder_point + lead_time_demand) - current_stock)

        # Order timing: place the order today if stock will hit reorder point
        # before the lead time elapses; otherwise schedule it.
        days_to_reorder = (current_stock - reorder_point) / avg_demand if avg_demand > 0 else 999
        days_until_stockout = current_stock / avg_demand if avg_demand > 0 else 999
        order_today = days_to_reorder <= self.lead_time_days
        order_date = datetime.now() if order_today else datetime.now() + timedelta(days=int(days_to_reorder))
        arrival_date = order_date + timedelta(days=self.lead_time_days)
        stockout_date = datetime.now() + timedelta(days=days_until_stockout) if days_until_stockout < 365 else None

        # Status
        status = "OK"
        if current_stock < safety_stock:
            status = "CRITICAL"
        elif current_stock < reorder_point:
            status = "LOW"
        elif current_stock > reorder_point + eoq:
            status = "EXCESS"

        # ── Financial intelligence ──────────────────────────────────────────
        price = unit_price or self.unit_cost
        inventory_value = current_stock * price
        excess_units = 0.0
        if days_until_stockout > 90:  # >90 days of stock = excess
            excess_units = max(0.0, current_stock - (avg_demand * 90))
        overstock_capital = excess_units * price

        # Stockout revenue loss: if stock runs out before next arrival, we lose
        # sales for the gap days.
        if stockout_date and arrival_date and stockout_date < arrival_date and avg_demand > 0:
            gap_days = max(0, (arrival_date - stockout_date).days)
            stockout_loss_units = gap_days * avg_demand
            stockout_revenue_loss = stockout_loss_units * price
        else:
            stockout_revenue_loss = 0.0

        # Carrying cost & turnover
        annual_demand = avg_demand * 365
        hcr = holding_cost_rate if holding_cost_rate is not None else self.holding_cost_rate
        carrying_cost = inventory_value * hcr
        turnover = annual_demand / current_stock if current_stock > 0 else float("inf")
        days_of_inventory = current_stock / avg_demand if avg_demand > 0 else 999

        # Potential savings: reduce overstock carrying cost + avoid stockout loss
        potential_savings = overstock_capital * hcr + stockout_revenue_loss

        return {
            # Decision
            "avg_daily_demand": avg_demand,
            "demand_std": opt["demand_std"],
            "safety_stock": safety_stock,
            "reorder_point": reorder_point,
            "eoq": eoq,
            "recommended_order_qty": recommended_order_qty,
            "order_today": order_today,
            "order_date": order_date.strftime("%Y-%m-%d") if order_today or days_to_reorder < 365 else "N/A",
            "arrival_date": arrival_date.strftime("%Y-%m-%d"),
            "stockout_in_days": round(days_until_stockout, 1) if days_until_stockout < 365 else None,
            "stockout_date": stockout_date.strftime("%Y-%m-%d") if stockout_date else None,
            "status": status,
            "days_of_stock": round(days_until_stockout, 1) if days_until_stockout < 365 else 999,
            # Financial
            "unit_price": price,
            "inventory_value": round(inventory_value, 2),
            "excess_units": round(excess_units, 1),
            "overstock_capital": round(overstock_capital, 2),
            "stockout_revenue_loss": round(stockout_revenue_loss, 2),
            "carrying_cost": round(carrying_cost, 2),
            "inventory_turnover": round(turnover, 2) if turnover != float("inf") else None,
            "days_of_inventory": round(days_of_inventory, 1),
            "potential_savings": round(potential_savings, 2),
        }

    # ── Batch decisions ─────────────────────────────────────────────────────

    def generate_purchase_decisions(self, df, demand_multiplier=1.0):
        """Generate purchase decisions for all item-store combos in a sales df.

        df must contain: item_id, store_id, sales, and optionally current_stock
        and sell_price.
        """
        decisions = []
        groups = df.groupby(["item_id", "store_id"])
        for (item_id, store_id), group in groups:
            historical = group["sales"].values
            current_stock = group["current_stock"].iloc[-1] if "current_stock" in group.columns and pd.notna(group["current_stock"].iloc[-1]) else 0
            unit_price = group["sell_price"].iloc[-1] if "sell_price" in group.columns and pd.notna(group["sell_price"].iloc[-1]) else self.unit_cost

            decision = self.purchase_decision_for_item(
                current_stock, historical,
                demand_multiplier=demand_multiplier,
                unit_price=unit_price,
            )
            decision["item_id"] = item_id
            decision["store_id"] = store_id
            decisions.append(decision)

        return pd.DataFrame(decisions)

    def financial_summary(self, decisions_df):
        """Aggregate financial KPIs across all purchase decisions."""
        if decisions_df.empty:
            return {
                "total_inventory_value": 0.0,
                "total_overstock_capital": 0.0,
                "total_stockout_loss_risk": 0.0,
                "total_carrying_cost": 0.0,
                "total_potential_savings": 0.0,
                "total_recommended_order_value": 0.0,
                "avg_inventory_turnover": 0.0,
                "avg_days_of_inventory": 0.0,
                "items_to_reorder": 0,
            }

        total_order_qty = float(decisions_df["recommended_order_qty"].sum())
        avg_price = float(decisions_df["unit_price"].mean()) if "unit_price" in decisions_df else self.unit_cost

        return {
            "total_inventory_value": round(float(decisions_df["inventory_value"].sum()), 2),
            "total_overstock_capital": round(float(decisions_df["overstock_capital"].sum()), 2),
            "total_stockout_loss_risk": round(float(decisions_df["stockout_revenue_loss"].sum()), 2),
            "total_carrying_cost": round(float(decisions_df["carrying_cost"].sum()), 2),
            "total_potential_savings": round(float(decisions_df["potential_savings"].sum()), 2),
            "total_recommended_order_value": round(total_order_qty * avg_price, 2),
            "avg_inventory_turnover": round(float(decisions_df["inventory_turnover"].mean()), 2)
            if decisions_df["inventory_turnover"].notna().any() else None,
            "avg_days_of_inventory": round(float(decisions_df["days_of_inventory"].mean()), 1),
            "items_to_reorder": int((decisions_df["recommended_order_qty"] > 0).sum()),
        }

    # ── What-if simulation ──────────────────────────────────────────────────

    def simulate(self, df, demand_growth=None, lead_time_days=None, service_level=None,
                 holding_cost_rate=None, order_cost=None, unit_cost=None,
                 demand_multiplier=1.0):
        """Recompute all purchase decisions under changed parameters.

        Returns (decisions_df, financial_summary) so the UI can compare the
        baseline against the scenario side by side.
        """
        engine = PurchaseDecisionEngine(
            service_level=service_level if service_level is not None else self.service_level,
            lead_time_days=lead_time_days if lead_time_days is not None else self.lead_time_days,
            order_cost=order_cost if order_cost is not None else self.order_cost,
            holding_cost_rate=holding_cost_rate if holding_cost_rate is not None else self.holding_cost_rate,
            unit_cost=unit_cost if unit_cost is not None else self.unit_cost,
            demand_growth=demand_growth if demand_growth is not None else self.demand_growth,
        )
        decisions = engine.generate_purchase_decisions(df, demand_multiplier=demand_multiplier)
        summary = engine.financial_summary(decisions)
        return decisions, summary

