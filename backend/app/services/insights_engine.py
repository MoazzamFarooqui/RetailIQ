"""AI-generated business insights from sales data with Pakistan weather, season, and holiday awareness."""

import logging
import pandas as pd
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)


class InsightsEngine:
    """Generates natural-language business insights from sales data."""

    def __init__(self, df: pd.DataFrame = None):
        self.df = df
        self.insights = []

    def analyze(self, df: pd.DataFrame = None) -> list:
        """Run all analysis and return a list of insight dicts."""
        if df is not None:
            self.df = df
        if self.df is None:
            raise ValueError("No dataframe provided for analysis")

        self.insights = []
        self._analyze_overall()
        self._analyze_trends()
        self._analyze_products()
        self._analyze_stores()
        self._analyze_seasonality()
        self._analyze_anomalies()
        self._analyze_pakistan_season()
        self._analyze_weather_impact()
        self._analyze_holiday_impact()
        logger.info(f"Generated {len(self.insights)} insights")
        return self.insights

    def _add(self, insight_type: str, text: str, category: str, severity: str = "info"):
        self.insights.append({"insight_type": insight_type, "insight_text": text, "category": category, "severity": severity})

    def _safe_col(self, col: str) -> bool:
        return col in self.df.columns

    def _analyze_overall(self):
        df = self.df
        if not self._safe_col("sales"):
            return
        total = df["sales"].sum()
        avg_daily = df.groupby("date")["sales"].sum().mean() if self._safe_col("date") else 0
        days = df["date"].nunique() if self._safe_col("date") else 0
        items = df["item_id"].nunique() if self._safe_col("item_id") else 1
        stores = df["store_id"].nunique() if self._safe_col("store_id") else 1
        self._add("overall", f"**Overview**: {items:,} products across {stores} stores over {days} days. Total sales: **{total:,.0f}**. Average daily: **{avg_daily:,.0f}**.", "Summary", "info")

        if self._safe_col("sell_price") and self._safe_col("sales"):
            revenue = (df["sales"] * df["sell_price"]).sum()
            self._add("revenue", f"**Revenue**: Estimated total revenue is **${revenue:,.2f}**.", "Revenue", "info")

    def _analyze_trends(self):
        if not (self._safe_col("date") and self._safe_col("sales")):
            return
        df, daily = self.df, self.df.groupby("date")["sales"].sum().reset_index().sort_values("date")
        if len(daily) < 14:
            return
        recent, prior = daily.tail(7)["sales"].mean(), daily.tail(14).head(7)["sales"].mean()
        if prior > 0:
            change = ((recent - prior) / prior) * 100
            self._add("trend", f"{'📈' if change > 0 else '📉'} Sales are {'increasing' if change > 0 else 'decreasing'} by **{abs(change):.1f}%** in the last 7 days.", "Trends", "info")

        df_check = df.copy()
        df_check["_dow"] = df_check["date"].dt.dayofweek
        dow_avg = df_check.groupby("_dow")["sales"].mean()
        if len(dow_avg) > 1:
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            spread = ((dow_avg.max() - dow_avg.min()) / dow_avg.mean()) * 100
            self._add("day_of_week", f"**Day-of-Week**: **{days[dow_avg.idxmax()]}** strongest, **{days[dow_avg.idxmin()]}** weakest. Variation: **{spread:.0f}%**.", "Trends", "info")

    def _analyze_products(self):
        if not (self._safe_col("item_id") and self._safe_col("sales")):
            return
        prod = self.df.groupby("item_id")["sales"].sum().sort_values(ascending=False)
        if len(prod) >= 3:
            top = prod.head(3)
            names = ", ".join([f"**{i}** ({v:,.0f})" for i, v in top.items()])
            self._add("top_products", f"**Top Products**: {names}.", "Products", "info")
            pct = (prod.head(3).sum() / prod.sum()) * 100
            if pct > 50:
                self._add("concentration", f"**High Concentration**: Top 3 account for **{pct:.1f}%** of sales.", "Products", "warning")
        slow = prod[prod < prod.median() * 0.1]
        if len(slow) > 0:
            self._add("slow_movers", f"**Slow Movers**: **{len(slow)}** products sell less than 10% of the median.", "Products", "info")

    def _analyze_stores(self):
        if not (self._safe_col("store_id") and self._safe_col("sales")):
            return
        stores = self.df.groupby("store_id")["sales"].sum().sort_values(ascending=False)
        if len(stores) >= 2:
            ratio = stores.iloc[0] / stores.iloc[-1]
            self._add("store_performance", f"**Store Performance**: **{stores.index[0]}** leads ({stores.iloc[0]:,.0f}). Gap: **{ratio:.1f}x**.", "Stores", "info")
            if ratio > 5:
                self._add("store_disparity", f"**Large Store Disparity**: Top store sells **{ratio:.1f}x** more than lowest.", "Stores", "warning")

    def _analyze_seasonality(self):
        if not (self._safe_col("date") and self._safe_col("sales")):
            return
        df = self.df.copy()
        df["month"] = df["date"].dt.month
        monthly = df.groupby(["year", "month"])["sales"].sum().reset_index() if "year" in df.columns else df.groupby(df["date"].dt.year.rename("year"), "month")["sales"].sum().reset_index()
        if "year" not in monthly.columns:
            monthly["year"] = df["date"].dt.year

        if len(monthly) >= 3:
            max_m = monthly.loc[monthly["sales"].idxmax()]
            min_m = monthly.loc[monthly["sales"].idxmin()]
            months_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            self._add("seasonal_peak", f"**Seasonal Peak**: **{months_names[int(max_m['month'])-1]} {int(max_m['year'])}** highest ({max_m['sales']:,.0f}). Lowest: **{months_names[int(min_m['month'])-1]} {int(min_m['year'])}** ({min_m['sales']:,.0f}).", "Seasonality", "info")

        df["_dow"] = df["date"].dt.dayofweek
        weekend = df[df["_dow"] >= 5]["sales"].mean() if len(df[df["_dow"] >= 5]) > 0 else 0
        weekday = df[df["_dow"] < 5]["sales"].mean() if len(df[df["_dow"] < 5]) > 0 else 1
        if weekday > 0:
            uplift = ((weekend - weekday) / weekday) * 100
            if abs(uplift) > 10:
                self._add("weekend_effect", f"**Weekend Effect**: {'Higher' if uplift > 0 else 'Lower'} by **{abs(uplift):.0f}%**.", "Seasonality", "info")

    def _analyze_anomalies(self):
        if not self._safe_col("sales"):
            return
        sales = self.df["sales"]
        q1, q3 = sales.quantile(0.25), sales.quantile(0.75)
        upper = q3 + 3 * (q3 - q1)
        anomalies = sales[sales > upper]
        if len(anomalies) > 0:
            self._add("anomalies", f"**Anomalies**: **{len(anomalies)}** unusually high sales records ({len(anomalies)/len(sales)*100:.2f}%).", "Data Quality", "warning")

    def _analyze_pakistan_season(self):
        if not (self._safe_col("date") and self._safe_col("sales")):
            return
        from app.services.weather_service import WeatherService
        df = self.df.copy()
        df["season"] = df["date"].apply(WeatherService.get_season)
        season_sales = df.groupby("season")["sales"].agg(["mean", "sum", "std"]).reset_index()
        if len(season_sales) < 2:
            return
        best, worst = season_sales.loc[season_sales["sum"].idxmax()], season_sales.loc[season_sales["sum"].idxmin()]
        emojis = {"Spring": "🌸", "Summer": "☀️", "Monsoon": "🌧️", "Autumn": "🍂", "Winter": "❄️"}
        self._add("season_performance", f"**Pakistan Season**: {emojis.get(best['season'],'')} **{best['season']}** highest ({best['sum']:,.0f}). {emojis.get(worst['season'],'')} **{worst['season']}** lowest ({worst['sum']:,.0f}).", "Seasonality", "info")
        ratio = best["sum"] / worst["sum"]
        if ratio > 1.5:
            self._add("season_variation", f"**High Seasonal Variation**: **{ratio:.1f}x** between peak and low seasons.", "Seasonality", "warning")

    def _analyze_weather_impact(self):
        if not self._safe_col("sales"):
            return
        df = self.df.copy()
        if self._safe_col("temp_c"):
            temp_bins = pd.cut(df["temp_c"], bins=[0, 15, 25, 35, 50], labels=["<15°C", "15-25°C", "25-35°C", ">35°C"])
            temp_sales = df.groupby(temp_bins, observed=True)["sales"].mean().reset_index()
            temp_sales.columns = ["temp_range", "avg_sales"]
            if len(temp_sales) > 1:
                max_t = temp_sales.loc[temp_sales["avg_sales"].idxmax()]
                min_t = temp_sales.loc[temp_sales["avg_sales"].idxmin()]
                self._add("weather_correlation", f"**Weather-Sales**: Highest at **{max_t['temp_range']}** (avg {max_t['avg_sales']:.0f}), lowest at **{min_t['temp_range']}** (avg {min_t['avg_sales']:.0f}).", "Trends", "info")

    def _analyze_holiday_impact(self):
        if not (self._safe_col("date") and self._safe_col("sales")):
            return
        from app.services.holiday_service import HolidayService
        holiday_svc = HolidayService()
        df = holiday_svc.get_holiday_features(self.df.copy())
        if not self._safe_col("is_holiday"):
            return
        holiday_sales = df[df["is_holiday"] == 1]["sales"].mean() if df["is_holiday"].sum() > 0 else 0
        non_holiday = df[df["is_holiday"] == 0]["sales"].mean() if (df["is_holiday"] == 0).sum() > 0 else 1
        if non_holiday > 0:
            uplift = ((holiday_sales - non_holiday) / non_holiday) * 100
            if abs(uplift) > 5:
                self._add("holiday_impact", f"**Holiday Impact**: {'Higher' if uplift > 0 else 'Lower'} by **{abs(uplift):.1f}%** on holidays.", "Seasonality", "info")

    @staticmethod
    def get_current_season_advice(weather_service=None, holiday_service=None) -> dict:
        """Get actionable advice for the current Pakistan season."""
        import sys
        if "app.services.weather_service" in sys.modules.get("app.services.weather_service", ""):
            from app.services.weather_service import WeatherService
        else:
            from app.services.weather_service import WeatherService
        from app.services.holiday_service import HolidayService

        ws = weather_service or WeatherService()
        hs = holiday_service or HolidayService()
        now = datetime.now()
        season = WeatherService.get_season(now)
        demand_info = WeatherService.get_seasonal_demand_advice(now)
        pre_window = hs.is_in_pre_holiday_window(now)
        upcoming = hs.get_upcoming_holidays(now, limit=3)

        return {
            "current_season": season,
            "season_emoji": WeatherService.get_season_emoji(season),
            "season_advice": demand_info.get("advice", ""),
            "high_demand_products": demand_info.get("high_demand", []),
            "low_demand_products": demand_info.get("low_demand", []),
            "pre_holiday_window": pre_window,
            "upcoming_holidays": upcoming.to_dict("records") if len(upcoming) > 0 else [],
        }


