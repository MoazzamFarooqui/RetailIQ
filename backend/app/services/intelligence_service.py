"""Store & Product Intelligence service — deep drill-down analytics.

Computes the metrics the Store Intelligence and Product Intelligence pages
need: revenue, growth, sales velocity, demand trends, forecast accuracy,
stockout risk, seasonality, weather/holiday sensitivity.
"""

import logging
import math
from datetime import timedelta

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _finite(value):
    """Return None for non-finite floats so JSON serialization never fails.

    pandas operations (std of a single point, 0/0 divisions) can produce
    NaN/Inf; the API schema allows None for every numeric field.
    """
    if value is None:
        return None
    try:
        return value if math.isfinite(float(value)) else None
    except (TypeError, ValueError):
        return value


class IntelligenceService:
    """Analytics over a tenant's sales dataframe."""

    # ── Store intelligence ─────────────────────────────────────────────────

    @staticmethod
    def store_intelligence(df: pd.DataFrame, store_id: str,
                           weather_df: pd.DataFrame | None = None,
                           holiday_df: pd.DataFrame | None = None) -> dict:
        """Deep-dive metrics for a single store."""
        store_df = df[df["store_id"] == store_id].copy()
        if store_df.empty:
            return {"store_id": store_id, "error": "No data"}

        daily = store_df.groupby("date")["sales"].sum()
        total_sales = float(store_df["sales"].sum())
        revenue = float((store_df["sales"] * store_df["sell_price"].fillna(0)).sum()) if "sell_price" in store_df.columns else None
        products = int(store_df["item_id"].nunique())
        days = len(daily)
        avg_daily = total_sales / days if days else 0

        # Growth: last 28d vs prior 28d
        last_28 = daily.tail(28).sum()
        prior_28 = daily.iloc[-56:-28].sum()
        growth_pct = ((last_28 - prior_28) / prior_28 * 100) if prior_28 > 0 else None

        # Sales velocity: units per product per day
        velocity = _finite(float(store_df.groupby("item_id")["sales"].mean().mean())) if products else 0

        # Best/worst products
        prod_stats = store_df.groupby("item_id").agg(
            units=("sales", "sum"),
            days=("date", "nunique"),
        )
        best_products = prod_stats.sort_values("units", ascending=False).head(5).reset_index()
        best_products = [{"item_id": r["item_id"], "units": float(r["units"]),
                          "avg_daily": float(r["units"] / r["days"]) if r["days"] else 0}
                         for _, r in best_products.iterrows()]

        # Seasonality strength: day-of-week spread
        dow = daily.groupby(daily.index.dayofweek).mean()
        dow_spread = float((dow.max() - dow.min()) / dow.mean() * 100) if dow.mean() > 0 else 0
        days_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        peak_day = days_names[int(dow.idxmax())] if len(dow) > 0 else None

        # Weather sensitivity: correlation between daily sales and temp
        weather_sensitivity = None
        if weather_df is not None and "temp_c" in weather_df.columns and not weather_df.empty:
            merged = daily.reset_index().merge(
                weather_df[["date", "temp_c"]], on="date", how="inner"
            )
            if len(merged) >= 10 and merged["temp_c"].std() > 0:
                corr = np.corrcoef(merged["sales"], merged["temp_c"])[0, 1]
                weather_sensitivity = round(float(corr), 2)

        return {
            "store_id": store_id,
            "total_sales": _finite(round(total_sales, 2)),
            "revenue": _finite(round(revenue, 2)) if revenue is not None else None,
            "products": products,
            "avg_daily_sales": _finite(round(avg_daily, 2)),
            "growth_pct": _finite(round(growth_pct, 1)) if growth_pct is not None else None,
            "sales_velocity": _finite(round(velocity, 2)) if velocity is not None else None,
            "best_products": best_products,
            "day_of_week_spread_pct": _finite(round(dow_spread, 1)),
            "peak_day": peak_day,
            "weather_sensitivity": _finite(weather_sensitivity),
            "days_covered": days,
        }

    @staticmethod
    def all_stores_intelligence(df: pd.DataFrame) -> list[dict]:
        """Ranked store intelligence for all stores."""
        stores = []
        for store_id in df["store_id"].unique():
            stores.append(IntelligenceService.store_intelligence(df, store_id))
        return sorted(stores, key=lambda s: s.get("total_sales", 0), reverse=True)

    # ── Product intelligence ───────────────────────────────────────────────

    @staticmethod
    def product_intelligence(df: pd.DataFrame, item_id: str,
                             weather_df: pd.DataFrame | None = None,
                             holiday_df: pd.DataFrame | None = None,
                             forecast_accuracy: pd.DataFrame | None = None) -> dict:
        """Deep-dive metrics for a single product."""
        prod_df = df[df["item_id"] == item_id].copy()
        if prod_df.empty:
            return {"item_id": item_id, "error": "No data"}

        daily = prod_df.groupby("date")["sales"].sum()
        total_sales = float(prod_df["sales"].sum())
        revenue = float((prod_df["sales"] * prod_df["sell_price"].fillna(0)).sum()) if "sell_price" in prod_df.columns else None
        stores = int(prod_df["store_id"].nunique())
        days = len(daily)
        avg_daily = total_sales / days if days else 0

        # Growth
        last_28 = daily.tail(28).sum()
        prior_28 = daily.iloc[-56:-28].sum()
        growth_pct = ((last_28 - prior_28) / prior_28 * 100) if prior_28 > 0 else None

        # Category & store concentration
        category = None
        if "category" in prod_df.columns and prod_df["category"].notna().any():
            category = prod_df["category"].dropna().iloc[0]
        store_share = prod_df.groupby("store_id")["sales"].sum().sort_values(ascending=False)
        top_store = str(store_share.index[0]) if len(store_share) else None
        top_store_pct = float(store_share.iloc[0] / total_sales * 100) if total_sales > 0 and len(store_share) else None

        # Demand trend: linear regression slope over daily sales
        trend_slope = None
        if len(daily) >= 2:
            x = np.arange(len(daily))
            try:
                trend_slope = float(np.polyfit(x, daily.values, 1)[0])
            except Exception:
                pass

        # Seasonality
        dow = daily.groupby(daily.index.dayofweek).mean()
        dow_spread = float((dow.max() - dow.min()) / dow.mean() * 100) if dow.mean() > 0 else 0
        month_avg = daily.groupby(daily.index.month).mean()
        peak_month = int(month_avg.idxmax()) if len(month_avg) else None

        # Stockout risk proxy: sales variance / stability.
        # A single-day series yields std() = NaN (0/0); treat as stable.
        cv = float(daily.std() / daily.mean()) if daily.mean() > 0 and len(daily) > 1 else 0
        stockout_risk = "high" if cv > 1.5 else ("medium" if cv > 0.8 else "low")

        # Holiday sensitivity: sales on holiday dates vs baseline
        holiday_sensitivity = None
        if holiday_df is not None and "date" in holiday_df.columns:
            merged = daily.reset_index().rename(columns={"index": "date"})
            holiday_dates = set(pd.to_datetime(holiday_df["date"]).dt.date)
            is_holiday = merged["date"].dt.date.isin(holiday_dates)
            if is_holiday.sum() >= 2:
                hol_avg = merged[is_holiday]["sales"].mean()
                base_avg = merged[~is_holiday]["sales"].mean()
                if base_avg > 0:
                    holiday_sensitivity = round(float((hol_avg - base_avg) / base_avg * 100), 1)

        # Forecast accuracy for this product (if provided)
        accuracy = None
        if forecast_accuracy is not None and not forecast_accuracy.empty:
            acc = forecast_accuracy[forecast_accuracy["product_id"] == item_id]
            if not acc.empty:
                accuracy = {
                    "wape": _finite(acc["wape"].mean()) if acc["wape"].notna().any() else None,
                    "mae": _finite(acc["mae"].mean()) if acc["mae"].notna().any() else None,
                    "points": int(acc["eval_points"].sum()),
                }

        return {
            "item_id": item_id,
            "category": category,
            "total_sales": _finite(round(total_sales, 2)),
            "revenue": _finite(round(revenue, 2)) if revenue is not None else None,
            "stores": stores,
            "avg_daily_sales": _finite(round(avg_daily, 2)),
            "growth_pct": _finite(round(growth_pct, 1)) if growth_pct is not None else None,
            "trend_slope": _finite(round(trend_slope, 3)) if trend_slope is not None else None,
            "top_store": top_store,
            "top_store_pct": _finite(round(top_store_pct, 1)) if top_store_pct is not None else None,
            "day_of_week_spread_pct": _finite(round(dow_spread, 1)),
            "peak_month": peak_month,
            "demand_cv": _finite(round(cv, 2)),
            "stockout_risk": stockout_risk,
            "holiday_sensitivity_pct": _finite(holiday_sensitivity),
            "forecast_accuracy": accuracy,
            "days_covered": days,
        }

    @staticmethod
    def all_products_intelligence(df: pd.DataFrame) -> list[dict]:
        """Ranked product intelligence for all products."""
        products = []
        for item_id in df["item_id"].unique():
            products.append(IntelligenceService.product_intelligence(df, item_id))
        return sorted(products, key=lambda p: p.get("total_sales", 0), reverse=True)
