"""Feature engineering for retail demand forecasting with Pakistan-specific features."""

import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """Creates time, season, holiday, weather, lag, and rolling features."""

    def create_time_features(self, df, date_col="date"):
        """Create time-based features from date column."""
        df = df.copy()
        if date_col in df.columns:
            df["year"] = df[date_col].dt.year
            df["month"] = df[date_col].dt.month
            df["day"] = df[date_col].dt.day
            df["dayofweek"] = df[date_col].dt.dayofweek
            df["dayofyear"] = df[date_col].dt.dayofyear
            df["week"] = df[date_col].dt.isocalendar().week.astype(int)
            df["quarter"] = df[date_col].dt.quarter
            df["is_weekend"] = (df["dayofweek"] >= 5).astype(int)
            df["is_month_start"] = df[date_col].dt.is_month_start.astype(int)
            df["is_month_end"] = df[date_col].dt.is_month_end.astype(int)
        return df

    def create_pakistan_season_features(self, df, date_col="date"):
        """Add Pakistan-specific season features."""
        from app.services.weather_service import WeatherService
        df = df.copy()
        if date_col not in df.columns:
            return df
        df["pakistan_season"] = df[date_col].apply(WeatherService.get_season)
        season_dummies = pd.get_dummies(df["pakistan_season"], prefix="season")
        for s in ["Spring", "Summer", "Monsoon", "Autumn", "Winter"]:
            if f"season_{s}" not in season_dummies.columns:
                season_dummies[f"season_{s}"] = 0
        df = pd.concat([df, season_dummies], axis=1)
        df["month_sin"] = df[date_col].apply(lambda d: np.sin(2 * np.pi * d.month / 12))
        df["month_cos"] = df[date_col].apply(lambda d: np.cos(2 * np.pi * d.month / 12))
        df["dow_sin"] = df[date_col].apply(lambda d: np.sin(2 * np.pi * d.dayofweek / 7))
        df["dow_cos"] = df[date_col].apply(lambda d: np.cos(2 * np.pi * d.dayofweek / 7))
        df["doy_sin"] = df[date_col].apply(lambda d: np.sin(2 * np.pi * d.dayofyear / 365))
        df["doy_cos"] = df[date_col].apply(lambda d: np.cos(2 * np.pi * d.dayofyear / 365))
        return df

    def create_holiday_features(self, df, date_col="date"):
        """Add Pakistan holiday features."""
        from app.services.holiday_service import HolidayService
        df = df.copy()
        if date_col not in df.columns:
            return df
        holiday_svc = HolidayService()
        return holiday_svc.get_holiday_features(df, date_col)

    def create_weather_features(self, df, date_col="date", weather_df=None):
        """Add weather features with seasonal defaults."""
        from app.services.weather_service import WeatherService
        df = df.copy()
        if date_col not in df.columns:
            return df
        df = WeatherService.add_weather_features(df, weather_df)
        if "temp_c" in df.columns:
            df["is_extreme_heat"] = (df["temp_c"] >= 35).astype(int)
            df["is_cold_wave"] = (df["temp_c"] <= 10).astype(int)
            df["is_comfortable_temp"] = ((df["temp_c"] >= 20) & (df["temp_c"] <= 30)).astype(int)
        if "humidity_pct" in df.columns:
            df["is_high_humidity"] = (df["humidity_pct"] >= 70).astype(int)
            df["is_low_humidity"] = (df["humidity_pct"] <= 30).astype(int)
        if "rain_mm" in df.columns:
            df["is_rainy"] = (df["rain_mm"] > 5).astype(int)
            df["is_heavy_rain"] = (df["rain_mm"] > 20).astype(int)
        return df

    def create_season_weather_interactions(self, df):
        """Create interaction features between season and weather."""
        df = df.copy()
        if "pakistan_season" in df.columns and "temp_c" in df.columns:
            df["hot_summer"] = ((df["pakistan_season"] == "Summer") & (df["temp_c"] >= 35)).astype(int)
            df["cold_winter"] = ((df["pakistan_season"] == "Winter") & (df["temp_c"] <= 10)).astype(int)
            if "rain_mm" in df.columns:
                df["rainy_monsoon"] = ((df["pakistan_season"] == "Monsoon") & (df["rain_mm"] > 10)).astype(int)
            if "in_ramadan_window" in df.columns:
                df["hot_ramadan"] = ((df["in_ramadan_window"] == 1) & (df["temp_c"] >= 35)).astype(int)
        return df

    def create_demand_indicators(self, df):
        """Create features that indicate expected demand shifts."""
        df = df.copy()
        if "in_ramadan_window" in df.columns and "in_eid_window" in df.columns:
            df["is_pre_holiday_shopping"] = ((df["in_ramadan_window"] == 1) | (df["in_eid_window"] == 1)).astype(int)
        if "days_to_holiday" in df.columns:
            df["holiday_pressure"] = df["days_to_holiday"].apply(lambda x: max(0, 1 - x / 30) if x <= 30 else 0)
        if "is_weekend" in df.columns and "pakistan_season" in df.columns:
            df["weekend_in_summer"] = ((df["is_weekend"] == 1) & (df["pakistan_season"] == "Summer")).astype(int)
            df["weekend_in_winter"] = ((df["is_weekend"] == 1) & (df["pakistan_season"] == "Winter")).astype(int)
        return df

    def create_lag_features(self, df, target_col="sales", lags=None):
        """Create lag features for time series."""
        if lags is None:
            lags = [1, 7, 14, 28]
        df = df.copy()
        if "item_id" in df.columns and "date" in df.columns:
            df = df.sort_values(["item_id", "store_id", "date"])
        for lag in lags:
            df[f"{target_col}_lag_{lag}"] = df.groupby(["item_id", "store_id"])[target_col].shift(lag)
        return df

    def create_rolling_features(self, df, target_col="sales", windows=None):
        """Create rolling window statistics."""
        if windows is None:
            windows = [7, 14, 28]
        df = df.copy()
        if "item_id" in df.columns and "date" in df.columns:
            df = df.sort_values(["item_id", "store_id", "date"])
        for window in windows:
            df[f"{target_col}_rolling_mean_{window}"] = df.groupby(["item_id", "store_id"])[target_col].transform(
                lambda x: x.rolling(window=window, min_periods=1).mean()
            )
            df[f"{target_col}_rolling_std_{window}"] = df.groupby(["item_id", "store_id"])[target_col].transform(
                lambda x: x.rolling(window=window, min_periods=1).std()
            )
            df[f"{target_col}_rolling_max_{window}"] = df.groupby(["item_id", "store_id"])[target_col].transform(
                lambda x: x.rolling(window=window, min_periods=1).max()
            )
            df[f"{target_col}_rolling_min_{window}"] = df.groupby(["item_id", "store_id"])[target_col].transform(
                lambda x: x.rolling(window=window, min_periods=1).min()
            )
        return df

    def create_price_features(self, df):
        """Create price-related features."""
        df = df.copy()
        if "sell_price" in df.columns:
            df["price_change"] = df.groupby(["item_id", "store_id"])["sell_price"].diff()
            df["price_vs_avg"] = df.groupby("item_id")["sell_price"].transform(lambda x: x - x.mean())
            df["price_momentum"] = df.groupby(["item_id", "store_id"])["sell_price"].transform(lambda x: x - x.shift(7))
        return df

    def create_all_features(self, df):
        """Create all features in one go."""
        logger.info("Creating all features...")
        df = self.create_time_features(df)
        df = self.create_pakistan_season_features(df)
        df = self.create_holiday_features(df)
        df = self.create_weather_features(df)
        df = self.create_season_weather_interactions(df)
        df = self.create_demand_indicators(df)
        df = self.create_price_features(df)
        df = self.create_lag_features(df)
        df = self.create_rolling_features(df)
        logger.info(f"Feature engineering complete: {df.shape}")
        return df


