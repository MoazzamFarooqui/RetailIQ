"""Data Health Center — evaluates data quality and detects anomalies.

Scores the org's data on missing values, duplicates, date coverage, invalid
values, and suspicious transactions; flags anomalies (spikes, drops, gaps,
abnormal prices) that could corrupt forecasting if left in.
"""

import logging
from datetime import date, timedelta

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class DataHealthService:
    """Run data-quality checks and anomaly detection over an org's data."""

    @staticmethod
    def assess(df: pd.DataFrame) -> dict:
        """Full data health assessment of a sales dataframe.

        Returns a 0-100 score plus per-check results.
        """
        checks = []
        total_rows = len(df)

        # 1. Missing values
        missing = df.isna().sum().sum()
        missing_pct = (missing / (total_rows * len(df.columns)) * 100) if total_rows else 0
        checks.append({
            "check": "missing_values",
            "status": "pass" if missing_pct < 1 else ("warn" if missing_pct < 5 else "fail"),
            "detail": f"{missing} missing cells ({missing_pct:.2f}%)",
        })

        # 2. Duplicates
        subset = [c for c in ["date", "item_id", "store_id"] if c in df.columns]
        dupes = df.duplicated(subset=subset).sum() if subset else 0
        checks.append({
            "check": "duplicates",
            "status": "pass" if dupes == 0 else ("warn" if dupes < total_rows * 0.01 else "fail"),
            "detail": f"{dupes} duplicate (date, item, store) rows",
        })

        # 3. Date coverage (gaps in the daily series)
        date_gaps = 0
        if "date" in df.columns:
            daily = df.groupby("date")["sales"].sum()
            full_range = pd.date_range(daily.index.min(), daily.index.max(), freq="D")
            missing_days = set(full_range.date) - set(daily.index.date)
            date_gaps = len(missing_days)
            checks.append({
                "check": "date_coverage",
                "status": "pass" if date_gaps == 0 else ("warn" if date_gaps < 14 else "fail"),
                "detail": f"{date_gaps} missing days in the date range "
                          f"({daily.index.min().date()} → {daily.index.max().date()})",
            })

        # 4. Negative / invalid sales
        if "sales" in df.columns:
            neg = (df["sales"] < 0).sum()
            checks.append({
                "check": "negative_sales",
                "status": "pass" if neg == 0 else "warn",
                "detail": f"{neg} negative sales rows (may be returns)",
            })

        # 5. Abnormal prices (0 or extreme)
        price_issues = 0
        if "sell_price" in df.columns:
            prices = df["sell_price"].dropna()
            if len(prices):
                median = prices.median()
                high = (prices > median * 10).sum()
                zero = (prices == 0).sum()
                price_issues = int(high + zero)
                checks.append({
                    "check": "price_anomalies",
                    "status": "pass" if price_issues == 0 else "warn",
                    "detail": f"{zero} zero prices, {high} prices > 10x median",
                })

        # Score: start 100, deduct per failing check
        score = 100
        for c in checks:
            if c["status"] == "fail":
                score -= 20
            elif c["status"] == "warn":
                score -= 8
        score = max(0, min(100, score))

        return {
            "score": score,
            "checks": checks,
            "total_rows": total_rows,
            "assessed_at": date.today().isoformat(),
        }

    # ── Anomaly detection ──────────────────────────────────────────────────

    @staticmethod
    def detect_anomalies(df: pd.DataFrame, z_threshold: float = 3.0) -> list[dict]:
        """Detect unusual sales events: spikes, drops, and gaps.

        Returns a list of anomaly dicts the alert engine can consume.
        """
        anomalies = []
        if "date" not in df.columns or "sales" not in df.columns:
            return anomalies

        daily = df.groupby("date")["sales"].sum().sort_index()
        if len(daily) < 14:
            return anomalies

        mean = daily.mean()
        std = daily.std()
        if std == 0 or pd.isna(std):
            return anomalies

        # Per-day z-score anomalies
        for day, value in daily.items():
            z = (value - mean) / std
            if abs(z) >= z_threshold:
                anomalies.append({
                    "type": "sales_spike" if z > 0 else "sales_drop",
                    "date": str(day.date()),
                    "sales": float(value),
                    "expected": float(mean),
                    "z_score": round(float(z), 2),
                    "severity": "high" if abs(z) >= 4 else "medium",
                })

        # Date gaps
        full_range = pd.date_range(daily.index.min(), daily.index.max(), freq="D")
        missing_days = set(full_range.date) - set(daily.index.date)
        for d in sorted(missing_days):
            anomalies.append({
                "type": "missing_period",
                "date": str(d),
                "sales": 0,
                "expected": float(mean),
                "z_score": None,
                "severity": "low",
            })

        return anomalies[:50]

    @staticmethod
    async def detect_transaction_anomalies(db, org_id: str) -> list[dict]:
        """Detect suspicious transactions: negative sales, zero/abnormal prices."""
        from app.models import Sale
        from sqlalchemy import select

        rows = (await db.execute(
            select(Sale).where(Sale.organization_id == org_id)
        )).scalars().all()

        issues = []
        for r in rows:
            if r.quantity < 0:
                issues.append({
                    "type": "negative_quantity",
                    "date": str(r.sale_date),
                    "product_id": r.product_id,
                    "store_id": r.store_id,
                    "quantity": r.quantity,
                    "severity": "medium",
                })
            if r.revenue < 0:
                issues.append({
                    "type": "negative_revenue",
                    "date": str(r.sale_date),
                    "product_id": r.product_id,
                    "store_id": r.store_id,
                    "revenue": r.revenue,
                    "severity": "medium",
                })
        return issues[:100]

