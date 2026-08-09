"""Regenerate data/processed/engineered_features.csv from the raw M5 files.

Subsamples the full dataset to a handful of stores (full date range per store),
so the analytics endpoints get a proper multi-date time series.

By default this writes the base long-format frame (item/store/date/sales plus
calendar + price columns) — enough for the analytics dashboard and for
DemandForecaster.prepare_features to auto-select numeric columns. Pass
--with-features to also run the full FeatureEngineer pipeline (memory-heavy on
6M+ rows; do that on a machine with plenty of RAM).

Usage:  python backend/scripts/regenerate_engineered_data.py [--stores CA_1,TX_2,WI_3] [--with-features]
"""

import argparse
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "data", "processed", "engineered_features.csv")

SALES_FILE = os.path.join(RAW, "sales_train_evaluation.csv")
CALENDAR_FILE = os.path.join(RAW, "calendar.csv")
PRICES_FILE = os.path.join(RAW, "sell_prices.csv")


def build(store_ids: list[str]) -> pd.DataFrame:
    # 1. Sales: read only the rows for our stores (wide format d_1..d_1969).
    #    IMPORTANT: reset_index() so positional alignment with the chunked
    #    d_ reads matches exactly (skiprows-filtered chunks get a fresh
    #    sequential index; without reset the concat below would misalign
    #    on original row labels and pad NaNs).
    sales = pd.read_csv(SALES_FILE, usecols=["item_id", "dept_id", "cat_id", "store_id", "state_id"])
    store_set = set(store_ids)
    sales = sales[sales["store_id"].isin(store_set)].reset_index(drop=True)
    idx = sales.index
    # read the d_ columns for just those rows, chunked to bound memory.
    # skiprows receives the 0-based physical CSV row; row 0 is the header and
    # data rows 1..N correspond to DataFrame index 0..N-1 (chunk_idx).
    d_cols = pd.read_csv(SALES_FILE, nrows=0).columns.tolist()
    d_cols = [c for c in d_cols if c.startswith("d_")]
    chunks = []
    for start in range(0, len(idx), 500_000):
        chunk_idx = idx[start : start + 500_000]
        wanted = set(chunk_idx)
        chunk = pd.read_csv(
            SALES_FILE,
            usecols=d_cols,
            skiprows=lambda r: r != 0 and (r - 1) not in wanted,
        ).reset_index(drop=True)
        chunk.index = range(start, start + len(chunk))
        chunks.append(chunk)
    d_df = pd.concat(chunks)
    sales = pd.concat([sales, d_df], axis=1)

    # 2. Melt wide -> long
    id_cols = [c for c in sales.columns if not c.startswith("d_")]
    value_vars = [c for c in sales.columns if c.startswith("d_")]
    df = sales.melt(id_vars=id_cols, value_vars=value_vars, var_name="d", value_name="sales")

    # 3. Calendar + prices. M5 calendar rows map 1:1 to d_1..d_N by position.
    calendar = pd.read_csv(CALENDAR_FILE)
    calendar = calendar.reset_index(names="d")
    calendar["d"] = "d_" + (calendar["d"] + 1).astype(str)
    df = df.merge(
        calendar[["d", "date", "wm_yr_wk", "weekday", "wday", "month", "year",
                  "event_name_1", "event_type_1", "event_name_2", "event_type_2",
                  "snap_CA", "snap_TX", "snap_WI"]],
        on="d", how="left",
    )
    prices = pd.read_csv(PRICES_FILE)
    prices = prices[prices["store_id"].isin(store_set)]
    df = df.merge(prices[["item_id", "store_id", "wm_yr_wk", "sell_price"]],
                  on=["item_id", "store_id", "wm_yr_wk"], how="left")

    df["date"] = pd.to_datetime(df["date"])
    df["sales"] = pd.to_numeric(df["sales"], errors="coerce").fillna(0)
    df = df[df["sales"] > 0]  # drop zero rows (never purchased)
    return df


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """Feature columns the rest of the app expects (mirror of backend FeatureEngineer)."""
    from app.services.feature_engineering import FeatureEngineer
    fe = FeatureEngineer()
    df = fe.create_all_features(df)
    return df


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stores", default="CA_1,TX_2,WI_3",
                        help="comma-separated store ids to keep")
    parser.add_argument("--with-features", action="store_true",
                        help="run full FeatureEngineer pipeline (memory-heavy)")
    args = parser.parse_args()
    store_ids = [s.strip() for s in args.stores.split(",") if s.strip()]

    print(f"Building long-format sales for stores: {store_ids}")
    df = build(store_ids)
    print(f"Long-format rows: {len(df):,} | dates: {df['date'].min().date()} -> {df['date'].max().date()}")

    if args.with_features:
        # add backend/ to path so app.services.* import works
        backend_dir = os.path.join(ROOT, "backend")
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
        print("Adding features...")
        df = add_features(df)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"Wrote {OUT} ({len(df):,} rows)")


if __name__ == "__main__":
    main()


