"""AI-generated business insights from sales data — with Pakistan weather, season, and holiday awareness."""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class InsightsEngine:
    """Generates natural-language business insights from sales data.

    Includes Pakistan-specific analysis: seasonal demand, Ramadan/Eid patterns,
    monsoon effects, weather correlation, and holiday uplift detection.
    """

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
        self._analyze_forecast_readiness()
        self._analyze_pakistan_season()
        self._analyze_weather_impact()
        self._analyze_holiday_impact()
        return self.insights

    def _add(self, insight_type: str, text: str, category: str, severity: str = 'info'):
        self.insights.append({
            'insight_type': insight_type,
            'insight_text': text,
            'category': category,
            'severity': severity
        })

    # ── Overall summary ────────────────────────────────────────────────────

    def _analyze_overall(self):
        df = self.df
        total = df['sales'].sum() if 'sales' in df else 0
        avg_daily = df.groupby('date')['sales'].sum().mean() if 'date' in df and 'sales' in df else 0
        days = df['date'].nunique() if 'date' in df else 0
        items = df['item_id'].nunique() if 'item_id' in df else 1
        stores = df['store_id'].nunique() if 'store_id' in df else 1

        self._add(
            'overall',
            f"**Overview**: The dataset contains **{items:,} products** across **{stores} stores** "
            f"over **{days} days**. Total sales: **{total:,.0f}** units. "
            f"Average daily sales: **{avg_daily:,.0f}** units.",
            'Summary', 'info'
        )

        if 'sell_price' in df.columns and 'sales' in df.columns:
            revenue = (df['sales'] * df['sell_price']).sum()
            self._add(
                'revenue',
                f"**Revenue**: Estimated total revenue is **${revenue:,.2f}** "
                f"based on sales × unit price.",
                'Revenue', 'info'
            )

    # ── Trend analysis ─────────────────────────────────────────────────────

    def _analyze_trends(self):
        df = self.df.copy()
        if 'date' not in df.columns or 'sales' not in df.columns:
            return
        daily = df.groupby('date')['sales'].sum().reset_index()
        daily = daily.sort_values('date')

        if len(daily) < 14:
            return

        # Recent vs prior period comparison
        recent = daily.tail(7)['sales'].mean()
        prior = daily.tail(14).head(7)['sales'].mean()
        if prior > 0:
            change = ((recent - prior) / prior) * 100
            direction = '**increasing**' if change > 0 else '**decreasing**'
            self._add(
                'trend',
                f"{'📈' if change > 0 else '📉'} Sales are {'increasing' if change > 0 else 'decreasing'} "
                f"by **{abs(change):.1f}%** in the last 7 days compared to the prior week. "
                f"(Recent avg: {recent:.0f}, Prior avg: {prior:.0f})",
                'Trends', 'info'
            )

        # Day-of-week pattern
        if len(df) > 7:
            df['_dow'] = df['date'].dt.dayofweek
            dow_avg = df.groupby('_dow')['sales'].mean()
            best_day = dow_avg.idxmax()
            best_day_name = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][best_day]
            worst_day = dow_avg.idxmin()
            worst_day_name = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][worst_day]
            spread = ((dow_avg.max() - dow_avg.min()) / dow_avg.mean()) * 100
            self._add(
                'day_of_week',
                f"**Day-of-Week Pattern**: **{best_day_name}** is the strongest sales day "
                f"(avg {dow_avg.max():.0f}), while **{worst_day_name}** is the weakest "
                f"(avg {dow_avg.min():.0f}). Intra-week variation is **{spread:.0f}%**.",
                'Trends', 'info'
            )

    # ── Product performance ────────────────────────────────────────────────

    def _analyze_products(self):
        if 'item_id' not in self.df.columns or 'sales' not in self.df.columns:
            return
        df = self.df
        prod = df.groupby('item_id')['sales'].sum().sort_values(ascending=False)

        if len(prod) >= 3:
            top = prod.head(3)
            top_names = ', '.join([f'**{i}** ({v:,.0f})' for i, v in top.items()])
            self._add(
                'top_products',
                f"**Top Products**: {top_names}.",
                'Products', 'info'
            )

            # Concentration
            top3_pct = (prod.head(3).sum() / prod.sum()) * 100
            if top3_pct > 50:
                self._add(
                    'concentration',
                    f"**High Concentration**: Top 3 products account for **{top3_pct:.1f}%** of all sales. "
                    f"Consider diversifying inventory to reduce risk.",
                    'Products', 'warning'
                )

        # Low performers
        slow = prod[prod < prod.median() * 0.1]
        if len(slow) > 0:
            self._add(
                'slow_movers',
                f"**Slow Movers**: **{len(slow)}** products sell less than 10% of the median. "
                f"Review these for potential discontinuation or markdown strategy.",
                'Products', 'info'
            )

    # ── Store analysis ─────────────────────────────────────────────────────

    def _analyze_stores(self):
        if 'store_id' not in self.df.columns or 'sales' not in self.df.columns:
            return
        df = self.df
        stores = df.groupby('store_id')['sales'].sum().sort_values(ascending=False)

        if len(stores) >= 2:
            top_store = stores.index[0]
            bottom_store = stores.index[-1]
            ratio = stores.iloc[0] / stores.iloc[-1]
            self._add(
                'store_performance',
                f"**Store Performance**: **{top_store}** leads with **{stores.iloc[0]:,.0f}** total sales. "
                f"The gap between best and worst is **{ratio:.1f}x** ({bottom_store}: {stores.iloc[-1]:,.0f}).",
                'Stores', 'info'
            )

            if ratio > 5:
                self._add(
                    'store_disparity',
                    f"**Large Store Disparity**: The top store sells **{ratio:.1f}x** more than the lowest. "
                    f"Investigate underperforming locations for stock issues or local demand factors.",
                    'Stores', 'warning'
                )

    # ── Seasonality ─────────────────────────────────────────────────────────

    def _analyze_seasonality(self):
        if 'date' not in self.df.columns or 'sales' not in self.df.columns:
            return
        df = self.df
        df = df.copy()
        df['month'] = df['date'].dt.month
        df['year'] = df['date'].dt.year

        monthly = df.groupby(['year', 'month'])['sales'].sum().reset_index()

        if len(monthly) >= 3:
            max_month = monthly.loc[monthly['sales'].idxmax()]
            min_month = monthly.loc[monthly['sales'].idxmin()]
            months_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                            'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            self._add(
                'seasonal_peak',
                f"**Seasonal Peak**: **{months_names[int(max_month['month'])-1]} {int(max_month['year'])}** "
                f"had the highest sales ({max_month['sales']:,.0f}). "
                f"Lowest was **{months_names[int(min_month['month'])-1]} {int(min_month['year'])}** "
                f"({min_month['sales']:,.0f}).",
                'Seasonality', 'info'
            )

        # Weekend effect
        if 'date' in df.columns:
            df['_dow'] = df['date'].dt.dayofweek
            weekend = df[df['_dow'] >= 5]['sales'].mean() if len(df[df['_dow'] >= 5]) > 0 else 0
            weekday = df[df['_dow'] < 5]['sales'].mean() if len(df[df['_dow'] < 5]) > 0 else 1
            if weekday > 0:
                weekend_uplift = ((weekend - weekday) / weekday) * 100
                if abs(weekend_uplift) > 10:
                    direction = 'higher' if weekend_uplift > 0 else 'lower'
                    self._add(
                        'weekend_effect',
                        f"**Weekend Effect**: Weekend sales are **{direction}** by "
                        f"**{abs(weekend_uplift):.0f}%** compared to weekdays.",
                        'Seasonality', 'info'
                    )

    # ── Anomaly detection ──────────────────────────────────────────────────

    def _analyze_anomalies(self):
        if 'sales' not in self.df.columns:
            return
        sales = self.df['sales']
        q1, q3 = sales.quantile(0.25), sales.quantile(0.75)
        iqr = q3 - q1
        upper = q3 + 3 * iqr
        anomalies = sales[sales > upper]
        if len(anomalies) > 0:
            pct = (len(anomalies) / len(sales)) * 100
            self._add(
                'anomalies',
                f"**Anomalies**: Found **{len(anomalies)}** unusually high sales records "
                f"({pct:.2f}% of data) — values exceeding {upper:.0f}. "
                f"Investigate for promotions, data errors, or special events.",
                'Data Quality', 'warning'
            )

    # ── Forecast readiness ─────────────────────────────────────────────────

    def _analyze_forecast_readiness(self):
        df = self.df
        checks = []
        if 'date' in df.columns:
            days = df['date'].nunique()
            if days >= 28:
                checks.append(f"**{days} days** of history (28+ required)")
            else:
                checks.append(f"Only **{days} days** (28+ recommended for meaningful forecasts)")

        if 'item_id' in df.columns:
            items = df['item_id'].nunique()
            checks.append(f"**{items} products** tracked")

        if 'store_id' in df.columns:
            stores = df['store_id'].nunique()
            checks.append(f"**{stores} stores**")

        if 'sell_price' in df.columns:
            has_price = df['sell_price'].notna().sum() > 0
            checks.append(f"{'Price data available' if has_price else 'Price data missing'}")
        else:
            checks.append("No price data — revenue analysis limited")

        self._add(
            'readiness',
            "**Forecast Readiness**:\n" + "\n".join(f"  {c}" for c in checks),
            'Summary', 'info'
        )

    # ── Pakistan Season Analysis ──────────────────────────────────────────

    def _analyze_pakistan_season(self):
        """Analyze sales patterns by Pakistan season (Summer, Monsoon, Winter, etc.)."""
        if 'date' not in self.df.columns or 'sales' not in self.df.columns:
            return

        df = self.df.copy()
        from src.weather_service import WeatherService

        df['season'] = df['date'].apply(WeatherService.get_season)
        season_sales = df.groupby('season')['sales'].agg(['mean', 'sum', 'std']).reset_index()

        if len(season_sales) < 2:
            return

        # Best-performing season
        best = season_sales.loc[season_sales['sum'].idxmax()]
        worst = season_sales.loc[season_sales['sum'].idxmin()]
        season_emojis = {'Spring': '🌸', 'Summer': '☀️', 'Monsoon': '🌧️', 'Autumn': '🍂', 'Winter': '❄️'}
        best_emoji = season_emojis.get(best['season'], '')
        worst_emoji = season_emojis.get(worst['season'], '')

        self._add(
            'season_performance',
            f"**Pakistan Season Analysis**: {best_emoji} **{best['season']}** is the highest-selling season "
            f"(total: {best['sum']:,.0f}, avg daily: {best['mean']:,.0f}). "
            f"{worst_emoji} **{worst['season']}** is the lowest ({worst['sum']:,.0f}). "
            f"Plan inventory accordingly ahead of peak seasons.",
            'Seasonality', 'info'
        )

        # Inter-season variation
        max_sum = season_sales['sum'].max()
        min_sum = season_sales['sum'].min()
        if min_sum > 0 and max_sum / min_sum > 1.5:
            self._add(
                'season_variation',
                f"**High Seasonal Variation**: Sales differ by **{max_sum/min_sum:.1f}x** between "
                f"peak and low seasons. Consider seasonal staffing and inventory adjustments.",
                'Seasonality', 'warning'
            )

        # Monsoon-specific
        if 'Monsoon' in season_sales['season'].values:
            monsoon_data = season_sales[season_sales['season'] == 'Monsoon'].iloc[0]
            self._add(
                'monsoon_impact',
                f"**Monsoon Impact**: Average daily sales during monsoon: **{monsoon_data['mean']:,.0f}**. "
                f"Stock umbrellas, raincoats, and indoor snacks. Expect reduced foot traffic but "
                f"increased demand for delivery and hot beverages.",
                'Seasonality', 'info'
            )

        # Ramadan / seasonal month overlap
        if 'month' in df.columns or 'date' in df.columns:
            df['month'] = df['date'].dt.month
            # March-April often has Ramadan overlap
            spring_months = df[df['month'].isin([3, 4])]
            if len(spring_months) > 0:
                spring_avg = spring_months.groupby('date')['sales'].sum().mean()
                overall_avg = df.groupby('date')['sales'].sum().mean()
                if overall_avg > 0:
                    spring_ratio = spring_avg / overall_avg
                    if abs(spring_ratio - 1) > 0.1:
                        direction = 'higher' if spring_ratio > 1 else 'lower'
                        self._add(
                            'ramadan_season_effect',
                            f"**Ramadan Season Effect (Mar-Apr)**: Sales in Ramadan period are "
                            f"**{direction}** by **{abs(spring_ratio - 1) * 100:.0f}%** vs yearly average. "
                            f"{'Prepare extra stock of dates, juices, and beverages.' if spring_ratio > 1 else 'Expect muted demand during fasting hours.'}",
                            'Seasonality', 'info'
                        )

    # ── Weather Impact Analysis ─────────────────────────────────────────────

    def _analyze_weather_impact(self):
        """Analyze how weather conditions correlate with sales."""
        if 'sales' not in self.df.columns:
            return

        df = self.df.copy()

        # Check if we have temperature data
        has_temp = 'temp_c' in df.columns or 'temperature_c' in df.columns
        has_humidity = 'humidity_pct' in df.columns

        if has_temp:
            temp_col = 'temp_c' if 'temp_c' in df.columns else 'temperature_c'
            # Bin temperatures and calculate avg sales per bin
            temp_bins = pd.cut(df[temp_col], bins=[0, 15, 25, 35, 50], labels=['<15°C', '15-25°C', '25-35°C', '>35°C'])
            temp_sales = df.groupby(temp_bins, observed=True)['sales'].mean().reset_index()
            temp_sales.columns = ['temp_range', 'avg_sales']

            if len(temp_sales) > 1:
                max_temp = temp_sales.loc[temp_sales['avg_sales'].idxmax()]
                min_temp = temp_sales.loc[temp_sales['avg_sales'].idxmin()]
                self._add(
                    'weather_correlation',
                    f"**Weather-Sales Correlation**: Highest sales occur at **{max_temp['temp_range']}** "
                    f"(avg {max_temp['avg_sales']:.0f}), lowest at **{min_temp['temp_range']}** "
                    f"(avg {min_temp['avg_sales']:.0f}). Use this to plan weather-based promotions.",
                    'Trends', 'info'
                )

        if has_humidity:
            humid_bins = pd.cut(df['humidity_pct'], bins=[0, 40, 60, 80, 100],
                                 labels=['Dry (<40%)', 'Moderate (40-60%)', 'Humid (60-80%)', 'Very Humid (>80%)'])
            humid_sales = df.groupby(humid_bins, observed=True)['sales'].mean().reset_index()

            if len(humid_sales) > 1:
                max_h = humid_sales.loc[humid_sales['avg_sales'].idxmax()]
                self._add(
                    'humidity_impact',
                    f"**Humidity Impact**: Sales peak during **{max_h['temp_range'] if 'temp_range' in max_h else max_h['humidity_pct']}** humidity levels. "
                    f"High humidity drives demand for beverages, while low humidity boosts outdoor-related products.",
                    'Trends', 'info'
                )

    # ── Holiday Impact Analysis ─────────────────────────────────────────────

    def _analyze_holiday_impact(self):
        """Analyze how Pakistan holidays impact sales patterns."""
        if 'date' not in self.df.columns or 'sales' not in self.df.columns:
            return

        from src.holiday_service import HolidayService
        holiday_svc = HolidayService()

        df = self.df.copy()
        df = holiday_svc.get_holiday_features(df)

        if 'is_holiday' not in df.columns:
            return

        holiday_sales = df[df['is_holiday'] == 1]['sales'].mean() if df['is_holiday'].sum() > 0 else 0
        non_holiday_sales = df[df['is_holiday'] == 0]['sales'].mean() if (df['is_holiday'] == 0).sum() > 0 else 1

        if non_holiday_sales > 0:
            holiday_uplift = ((holiday_sales - non_holiday_sales) / non_holiday_sales) * 100
            if abs(holiday_uplift) > 5:
                direction = 'higher' if holiday_uplift > 0 else 'lower'
                self._add(
                    'holiday_impact',
                    f"**Pakistan Holiday Impact**: Sales on holidays are **{direction}** "
                    f"by **{abs(holiday_uplift):.1f}%** compared to regular days "
                    f"(holiday avg: {holiday_sales:.0f}, regular: {non_holiday_sales:.0f}). "
                    f"{'Prepare extra inventory ahead of upcoming holidays.' if holiday_uplift > 0 else 'Holiday closures may reduce sales volume.'}",
                    'Seasonality', 'info'
                )

        # Pre-Ramadan shopping window
        if 'in_ramadan_window' in df.columns:
            ramadan_window_sales = df[df['in_ramadan_window'] == 1]['sales'].mean() if df['in_ramadan_window'].sum() > 0 else 0
            if ramadan_window_sales > 0 and non_holiday_sales > 0:
                ramadan_uplift = ((ramadan_window_sales - non_holiday_sales) / non_holiday_sales) * 100
                if ramadan_uplift > 5:
                    self._add(
                        'ramadan_window',
                        f"**Pre-Ramadan Shopping Surge**: Sales rise **{ramadan_uplift:.0f}%** in the "
                        f"2 weeks before Ramadan. Stock up on dates, juices, frozen foods, and "
                        f"cooking oil ahead of Ramadan.",
                        'Seasonality', 'info'
                    )

        # Pre-Eid shopping window
        if 'in_eid_window' in df.columns:
            eid_window_sales = df[df['in_eid_window'] == 1]['sales'].mean() if df['in_eid_window'].sum() > 0 else 0
            if eid_window_sales > 0 and non_holiday_sales > 0:
                eid_uplift = ((eid_window_sales - non_holiday_sales) / non_holiday_sales) * 100
                if eid_uplift > 5:
                    self._add(
                        'eid_window',
                        f"**Pre-Eid Shopping Surge**: Sales rise **{eid_uplift:.0f}%** in the week "
                        f"before Eid. Stock up on soft drinks, snacks, sweets, and gift items.",
                        'Seasonality', 'info'
                    )

        # Days-to-holiday effect
        if 'days_to_holiday' in df.columns:
            # Sales in the 3-day window before holidays
            pre_holiday = df[(df['days_to_holiday'] > 0) & (df['days_to_holiday'] <= 3)]['sales'].mean()
            if pre_holiday > 0 and non_holiday_sales > 0:
                pre_uplift = ((pre_holiday - non_holiday_sales) / non_holiday_sales) * 100
                if pre_uplift > 10:
                    self._add(
                        'pre_holiday_surge',
                        f"**Last-Minute Holiday Shopping**: Sales jump **{pre_uplift:.0f}%** in the "
                        f"3 days before Pakistan holidays. Ensure shelves are fully stocked.",
                        'Seasonality', 'info'
                    )

    # ── Current season awareness ───────────────────────────────────────────

    @staticmethod
    def get_current_season_advice() -> dict:
        """Get actionable advice for the current Pakistan season."""
        from src.weather_service import WeatherService
        from src.holiday_service import HolidayService

        now = datetime.now()
        season = WeatherService.get_season(now)
        season_emoji = WeatherService.get_season_emoji(season)
        demand_info = WeatherService.get_seasonal_demand_advice(now)

        holiday_svc = HolidayService()
        pre_window = holiday_svc.is_in_pre_holiday_window(now)
        upcoming = holiday_svc.get_upcoming_holidays(now, limit=3)

        advice = {
            'current_season': season,
            'season_emoji': season_emoji,
            'season_advice': demand_info.get('advice', ''),
            'high_demand_products': demand_info.get('high_demand', []),
            'low_demand_products': demand_info.get('low_demand', []),
            'pre_holiday_window': pre_window,
            'upcoming_holidays': upcoming.to_dict('records') if len(upcoming) > 0 else [],
        }

        return advice
