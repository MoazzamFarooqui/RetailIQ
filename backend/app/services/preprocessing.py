"""Data preprocessing service — calendar cleaning and sales data melting."""

import logging
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)


class DataPreprocessor:
    """Preprocesses raw retail sales data from CSV format."""

    @staticmethod
    def clean_calendar(calendar_df: pd.DataFrame) -> pd.DataFrame:
        """Clean calendar data: parse dates, handle holidays, add features."""
        df = calendar_df.copy()
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
        if "d" in df.columns:
            df["d"] = df["d"].str.strip()
        if "wm_yr_wk" in df.columns:
            df["wm_yr_wk"] = pd.to_numeric(df["wm_yr_wk"], errors="coerce")

        # Holiday features
        for col in ["event_name_1", "event_name_2", "event_type_1", "event_type_2"]:
            if col in df.columns:
                df[col] = df[col].fillna("None")

        return df

    @staticmethod
    def melt_sales_data(sales_df: pd.DataFrame) -> pd.DataFrame:
        """Melt wide-format sales data (d_1...d_N) into long format with a date column."""
        if "d_1" not in sales_df.columns:
            logger.info("Data appears to be in long format already")
            return sales_df

        id_cols = [c for c in sales_df.columns if not c.startswith("d_")]
        value_vars = [c for c in sales_df.columns if c.startswith("d_")]

        df_long = sales_df.melt(
            id_vars=id_cols,
            value_vars=value_vars,
            var_name="d",
            value_name="sales",
        )
        logger.info(f"Melted: {sales_df.shape} -> {df_long.shape}")
        return df_long

    @staticmethod
    def merge_and_clean_sales(
        sales_long: pd.DataFrame,
        calendar: pd.DataFrame,
        prices: pd.DataFrame = None,
    ) -> pd.DataFrame:
        """Merge sales with calendar and prices, then clean."""
        df = sales_long.merge(
            calendar[["d", "date", "wm_yr_wk", "event_name_1", "event_name_2", "event_type_1", "event_type_2"]],
            on="d", how="left",
        )
        if prices is not None and "wm_yr_wk" in prices.columns:
            df = df.merge(
                prices[["item_id", "store_id", "wm_yr_wk", "sell_price"]],
                on=["item_id", "store_id", "wm_yr_wk"], how="left",
            )
        df["date"] = pd.to_datetime(df["date"])
        df["sales"] = pd.to_numeric(df["sales"], errors="coerce").fillna(0)
        return df
