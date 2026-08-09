"""Regenerate the compact analytics aggregate files from engineered_features.csv.

Produces:
  data/processed/analytics_meta.json     — overview metrics
  data/processed/analytics_daily.csv     — date x store daily totals
  data/processed/analytics_products.csv  — per-product totals

These are what the /api/v1/analytics/* endpoints read (the full engineered
file is hundreds of MB and too slow to load per request).

Usage:  python backend/scripts/regenerate_analytics_aggregates.py
"""

import json
import os

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROCESSED = os.path.join(ROOT, "data", "processed")
SRC = os.path.join(PROCESSED, "engineered_features.csv")

COLS = ["date", "store_id", "item_id", "sales", "cat_id", "state_id"]


def main() -> None:
    print(f"Reading {SRC} ...")
    df = pd.read_csv(SRC, usecols=[c for c in COLS if c in pd.read_csv(SRC, nrows=0).columns])
    df["date"] = pd.to_datetime(df["date"])
    print(f"  {len(df):,} rows | {df['date'].nunique():,} dates")

    # daily store-level
    daily = df.groupby(["date", "store_id"]).agg(
        total_sales=("sales", "sum"),
        item_count=("item_id", "nunique"),
    ).reset_index()
    daily.to_csv(os.path.join(PROCESSED, "analytics_daily.csv"), index=False)
    print(f"  analytics_daily.csv: {len(daily):,} rows")

    # per-product totals
    prods = df.groupby("item_id").agg(
        total_sales=("sales", "sum"),
        days_sold=("date", "nunique"),
        store_count=("store_id", "nunique"),
    ).reset_index()
    prods.to_csv(os.path.join(PROCESSED, "analytics_products.csv"), index=False)
    print(f"  analytics_products.csv: {len(prods):,} rows")

    # meta
    meta = {
        "total_products": int(df["item_id"].nunique()),
        "total_stores": int(df["store_id"].nunique()),
        "total_categories": int(df["cat_id"].nunique()) if "cat_id" in df else 0,
        "total_states": int(df["state_id"].nunique()) if "state_id" in df else 0,
        "total_sales": float(df["sales"].sum()),
        "avg_daily_sales": float(df.groupby("date")["sales"].sum().mean()),
        "date_range": f"{df['date'].min().date()} to {df['date'].max().date()}",
        "n_time_series": int(len(df)),
    }
    with open(os.path.join(PROCESSED, "analytics_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
    print(f"  analytics_meta.json: {json.dumps(meta)}")


if __name__ == "__main__":
    main()


