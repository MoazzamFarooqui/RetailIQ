"""Feature engineering for retail demand forecasting — with Pakistan season, weather, and holiday features."""

import pandas as pd
import numpy as np


class FeatureEngineer:
    def __init__(self):
        pass

    # ── Time features ──────────────────────────────────────────────────────

    def create_time_features(self, df, date_col='date'):
        """Create time-based features from date column."""
        df = df.copy()
        if date_col in df.columns:
            df['year'] = df[date_col].dt.year
            df['month'] = df[date_col].dt.month
            df['day'] = df[date_col].dt.day
            df['dayofweek'] = df[date_col].dt.dayofweek
            df['dayofyear'] = df[date_col].dt.dayofyear
            df['week'] = df[date_col].dt.isocalendar().week.astype(int)
            df['quarter'] = df[date_col].dt.quarter
            df['is_weekend'] = (df['dayofweek'] >= 5).astype(int)
            df['is_month_start'] = df[date_col].dt.is_month_start.astype(int)
            df['is_month_end'] = df[date_col].dt.is_month_end.astype(int)
        return df

    # ── Pakistan season features ──────────────────────────────────────────

    def create_pakistan_season_features(self, df, date_col='date'):
        """Add Pakistan-specific season features (Summer, Monsoon, Winter, etc.).

        Also adds cyclical month encoding for models to learn seasonal patterns.
        """
        from src.weather_service import WeatherService

        df = df.copy()
        if date_col not in df.columns:
            return df

        # Pakistan season label
        df['pakistan_season'] = df[date_col].apply(WeatherService.get_season)

        # One-hot encode seasons
        season_dummies = pd.get_dummies(df['pakistan_season'], prefix='season')
        for s in ['Spring', 'Summer', 'Monsoon', 'Autumn', 'Winter']:
            col = f'season_{s}'
            if col not in season_dummies.columns:
                season_dummies[col] = 0
        df = pd.concat([df, season_dummies], axis=1)

        # Cyclical month encoding (sine/cosine so model learns "December & January are similar")
        df['month_sin'] = df[date_col].apply(lambda d: np.sin(2 * np.pi * d.month / 12))
        df['month_cos'] = df[date_col].apply(lambda d: np.cos(2 * np.pi * d.month / 12))

        # Cyclical day-of-week encoding
        df['dow_sin'] = df[date_col].apply(lambda d: np.sin(2 * np.pi * d.dayofweek / 7))
        df['dow_cos'] = df[date_col].apply(lambda d: np.cos(2 * np.pi * d.dayofweek / 7))

        # Day-of-year cyclical encoding (so model knows seasonal position)
        df['doy_sin'] = df[date_col].apply(lambda d: np.sin(2 * np.pi * d.dayofyear / 365))
        df['doy_cos'] = df[date_col].apply(lambda d: np.cos(2 * np.pi * d.dayofyear / 365))

        # Month-quarter mapping
        month_to_quarter = {1: 1, 2: 1, 3: 1, 4: 2, 5: 2, 6: 2,
                            7: 3, 8: 3, 9: 3, 10: 4, 11: 4, 12: 4}
        df['quarter'] = df[date_col].dt.month.map(month_to_quarter)

        return df

    # ── Pakistan holiday features ──────────────────────────────────────────

    def create_holiday_features(self, df, date_col='date'):
        """Add Pakistan holiday features: flags, days to/from holidays, pre-holiday windows."""
        from src.holiday_service import HolidayService

        df = df.copy()
        if date_col not in df.columns:
            return df

        holiday_svc = HolidayService()
        df = holiday_svc.get_holiday_features(df, date_col)

        return df

    # ── Weather features ──────────────────────────────────────────────────

    def create_weather_features(self, df, date_col='date', weather_df=None):
        """Add weather features with seasonal defaults for Pakistan."""
        from src.weather_service import WeatherService

        df = df.copy()
        if date_col not in df.columns:
            return df

        df = WeatherService.add_weather_features(df, weather_df)

        # Temperature-derived features
        if 'temp_c' in df.columns:
            # Extreme heat flag
            df['is_extreme_heat'] = (df['temp_c'] >= 35).astype(int)
            # Cold wave flag
            df['is_cold_wave'] = (df['temp_c'] <= 10).astype(int)
            # Comfortable temp flag
            df['is_comfortable_temp'] = ((df['temp_c'] >= 20) & (df['temp_c'] <= 30)).astype(int)

        # Humidity-derived features
        if 'humidity_pct' in df.columns:
            df['is_high_humidity'] = (df['humidity_pct'] >= 70).astype(int)
            df['is_low_humidity'] = (df['humidity_pct'] <= 30).astype(int)

        # Rain features
        if 'rain_mm' in df.columns:
            df['is_rainy'] = (df['rain_mm'] > 5).astype(int)
            df['is_heavy_rain'] = (df['rain_mm'] > 20).astype(int)

        return df

    # ── Weather × Season interaction features ──────────────────────────────

    def create_season_weather_interactions(self, df):
        """Create interaction features between season and weather.

        These help the model learn patterns like:
        - "Hot summer day → cold drink sales spike"
        - "Cold winter day → soup/tea sales spike"
        """
        df = df.copy()

        if 'pakistan_season' in df.columns and 'temp_c' in df.columns:
            # Hot summer day
            df['hot_summer'] = (
                (df['pakistan_season'] == 'Summer') & (df['temp_c'] >= 35)
            ).astype(int)
            # Cold winter day
            df['cold_winter'] = (
                (df['pakistan_season'] == 'Winter') & (df['temp_c'] <= 10)
            ).astype(int)
            # Rainy monsoon
            if 'rain_mm' in df.columns:
                df['rainy_monsoon'] = (
                    (df['pakistan_season'] == 'Monsoon') & (df['rain_mm'] > 10)
                ).astype(int)
            # Hot weather in Ramadan
            if 'in_ramadan_window' in df.columns:
                df['hot_ramadan'] = (
                    (df['in_ramadan_window'] == 1) & (df['temp_c'] >= 35)
                ).astype(int)

        return df

    # ── Demand indicator features ─────────────────────────────────────────

    def create_demand_indicators(self, df):
        """Create features that indicate expected demand shifts.

        These are based on Pakistan seasonality + holiday patterns.
        """
        df = df.copy()

        # Pre-holiday demand boost indicator (combines all pre-windows)
        if 'in_ramadan_window' in df.columns and 'in_eid_window' in df.columns:
            df['is_pre_holiday_shopping'] = (
                (df['in_ramadan_window'] == 1) | (df['in_eid_window'] == 1)
            ).astype(int)

        # Days until event inverted (closer = higher demand pressure)
        if 'days_to_holiday' in df.columns:
            df['holiday_pressure'] = df['days_to_holiday'].apply(
                lambda x: max(0, 1 - x / 30) if x <= 30 else 0
            )

        # Weekend × season interaction
        if 'is_weekend' in df.columns and 'pakistan_season' in df.columns:
            df['weekend_in_summer'] = (
                (df['is_weekend'] == 1) & (df['pakistan_season'] == 'Summer')
            ).astype(int)
            df['weekend_in_winter'] = (
                (df['is_weekend'] == 1) & (df['pakistan_season'] == 'Winter')
            ).astype(int)

        return df

    # ── Existing features ─────────────────────────────────────────────────

    def create_lag_features(self, df, target_col='sales', lags=[1, 7, 14, 28]):
        """Create lag features for time series."""
        df = df.copy()
        if 'item_id' in df.columns and 'date' in df.columns:
            df = df.sort_values(['item_id', 'store_id', 'date'])
        for lag in lags:
            df[f'{target_col}_lag_{lag}'] = df.groupby(['item_id', 'store_id'])[target_col].shift(lag)
        return df

    def create_rolling_features(self, df, target_col='sales', windows=[7, 14, 28]):
        """Create rolling window statistics."""
        df = df.copy()
        if 'item_id' in df.columns and 'date' in df.columns:
            df = df.sort_values(['item_id', 'store_id', 'date'])
        for window in windows:
            df[f'{target_col}_rolling_mean_{window}'] = df.groupby(['item_id', 'store_id'])[target_col].transform(
                lambda x: x.rolling(window=window, min_periods=1).mean()
            )
            df[f'{target_col}_rolling_std_{window}'] = df.groupby(['item_id', 'store_id'])[target_col].transform(
                lambda x: x.rolling(window=window, min_periods=1).std()
            )
            df[f'{target_col}_rolling_max_{window}'] = df.groupby(['item_id', 'store_id'])[target_col].transform(
                lambda x: x.rolling(window=window, min_periods=1).max()
            )
            df[f'{target_col}_rolling_min_{window}'] = df.groupby(['item_id', 'store_id'])[target_col].transform(
                lambda x: x.rolling(window=window, min_periods=1).min()
            )
        return df

    def create_price_features(self, df):
        """Create price-related features."""
        df = df.copy()
        if 'sell_price' in df.columns:
            df['price_change'] = df.groupby(['item_id', 'store_id'])['sell_price'].diff()
            df['price_vs_avg'] = df.groupby('item_id')['sell_price'].transform(
                lambda x: x - x.mean()
            )
            df['price_momentum'] = df.groupby(['item_id', 'store_id'])['sell_price'].transform(
                lambda x: x - x.shift(7)
            )
        return df

    def create_event_features(self, df):
        """Create features from event information."""
        df = df.copy()
        if 'event_name_1' in df.columns:
            df['has_event'] = (
                (df['event_name_1'] != 'None') | (df.get('event_name_2', 'None') != 'None')
            ).astype(int)
            if 'event_type_1' in df.columns:
                df['is_sporting_event'] = (df['event_type_1'] == 'Sporting').astype(int)
                df['is_cultural_event'] = (df['event_type_1'] == 'Cultural').astype(int)
                df['is_national_event'] = (df['event_type_1'] == 'National').astype(int)
                df['is_religious_event'] = (df['event_type_1'] == 'Religious').astype(int)
        return df

    def create_snap_features(self, df):
        """Create SNAP benefit features."""
        df = df.copy()
        snap_cols = ['snap_CA', 'snap_TX', 'snap_WI']
        for col in snap_cols:
            if col in df.columns:
                df[col] = df[col].astype(int)
        if all(col in df.columns for col in snap_cols):
            df['snap_count'] = df[snap_cols].sum(axis=1)
        return df

    def create_aggregated_features(self, df):
        """Create aggregated features by different dimensions."""
        df = df.copy()
        if 'sales' in df.columns:
            if 'store_id' in df.columns:
                df['store_sales_avg'] = df.groupby('store_id')['sales'].transform('mean')
                df['store_sales_std'] = df.groupby('store_id')['sales'].transform('std')
            if 'cat_id' in df.columns:
                df['cat_sales_avg'] = df.groupby('cat_id')['sales'].transform('mean')
            if 'dept_id' in df.columns:
                df['dept_sales_avg'] = df.groupby('dept_id')['sales'].transform('mean')
        return df

    # ── Master pipeline ───────────────────────────────────────────────────

    def create_all_features(self, df):
        """Create all features in one go, including Pakistan-specific ones."""
        print("Creating time features...")
        df = self.create_time_features(df)

        print("Creating Pakistan season features...")
        df = self.create_pakistan_season_features(df)

        print("Creating Pakistan holiday features...")
        df = self.create_holiday_features(df)

        print("Creating weather features...")
        df = self.create_weather_features(df)

        print("Creating season×weather interactions...")
        df = self.create_season_weather_interactions(df)

        print("Creating demand indicators...")
        df = self.create_demand_indicators(df)

        print("Creating event features...")
        df = self.create_event_features(df)

        print("Creating SNAP features...")
        df = self.create_snap_features(df)

        print("Creating price features...")
        df = self.create_price_features(df)

        print("Creating lag features...")
        df = self.create_lag_features(df)

        print("Creating rolling features...")
        df = self.create_rolling_features(df)

        print("Creating aggregated features...")
        df = self.create_aggregated_features(df)

        return df
