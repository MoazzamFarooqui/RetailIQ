"""Smart Alert Engine — detects events and creates notifications.

Detectors run on the org's data (via Celery daily) and create Alert rows:
  - stockout risk (stock will run out before next arrival)
  - overstock (too much capital tied up)
  - sudden demand changes (spike / drop vs recent baseline)
  - forecast degradation (live accuracy vs eval)
  - upcoming holidays (stock-up window)
  - store performance anomalies (unusual vs peers/history)
"""

import json
import logging
from datetime import datetime, timedelta, timezone

import pandas as pd
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Alert, AlertType, AlertSeverity, NotificationDelivery, NotificationChannel

logger = logging.getLogger(__name__)


class AlertService:
    """Run detectors over org data and persist alerts (deduped)."""

    @staticmethod
    def _dedup_key(org_id: str, alert_type: str, context: dict) -> str:
        stable = {k: str(v) for k, v in sorted(context.items())}
        return f"{org_id}:{alert_type}:{json.dumps(stable, sort_keys=True)}"

    @staticmethod
    async def _create_alert(db: AsyncSession, org_id: str, alert_type: AlertType,
                            severity: AlertSeverity, title: str, message: str,
                            context: dict | None = None) -> Alert | None:
        dedup = AlertService._dedup_key(org_id, alert_type.value, context or {})
        existing = (await db.execute(
            select(Alert).where(Alert.dedup_key == dedup, Alert.is_resolved == False)  # noqa: E712
        )).scalar_one_or_none()
        if existing:
            return None  # already active

        alert = Alert(
            organization_id=org_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            context=json.dumps(context or {}),
            dedup_key=dedup,
        )
        db.add(alert)
        return alert

    # ── Detectors ──────────────────────────────────────────────────────────

    @staticmethod
    async def detect_stockout_risk(db: AsyncSession, org_id: str, decisions_df: pd.DataFrame) -> int:
        """Flag items whose stock runs out within the lead time."""
        created = 0
        now = datetime.now()
        lead = 7
        for _, row in decisions_df.iterrows():
            stockout_days = row.get("stockout_in_days")
            if stockout_days is None or pd.isna(stockout_days) or stockout_days > lead:
                continue
            sev = AlertSeverity.CRITICAL if stockout_days <= 3 else AlertSeverity.HIGH
            ctx = {"item_id": row["item_id"], "store_id": row["store_id"], "days": float(stockout_days),
                   "stock": float(row["current_stock"]), "order_qty": float(row["recommended_order_qty"])}
            alert = await AlertService._create_alert(
                db, org_id, AlertType.STOCKOUT_RISK, sev,
                f"Stockout risk: {row['item_id']} @ {row['store_id']}",
                f"Stock runs out in ~{stockout_days:.0f} days. Order {row['recommended_order_qty']:.0f} units now.",
                ctx,
            )
            if alert:
                created += 1
        return created

    @staticmethod
    async def detect_overstock(db: AsyncSession, org_id: str, decisions_df: pd.DataFrame,
                               excess_days: int = 90) -> int:
        """Flag items carrying more than `excess_days` of stock."""
        created = 0
        for _, row in decisions_df.iterrows():
            days_of_stock = row.get("days_of_stock")
            if days_of_stock is None or pd.isna(days_of_stock) or days_of_stock <= excess_days:
                continue
            ctx = {"item_id": row["item_id"], "store_id": row["store_id"],
                   "days": float(days_of_stock), "capital": float(row.get("overstock_capital", 0))}
            alert = await AlertService._create_alert(
                db, org_id, AlertType.OVERSTOCK, AlertSeverity.MEDIUM,
                f"Overstock: {row['item_id']} @ {row['store_id']}",
                f"{days_of_stock:.0f} days of stock (${row.get('overstock_capital', 0):,.0f} tied up).",
                ctx,
            )
            if alert:
                created += 1
        return created

    @staticmethod
    async def detect_demand_change(db: AsyncSession, org_id: str, sales_df: pd.DataFrame,
                                   spike_pct: float = 40.0, drop_pct: float = 40.0) -> int:
        """Flag products with sudden demand changes (last 7d vs prior 28d baseline)."""
        created = 0
        if "date" not in sales_df.columns:
            return 0
        sales_df = sales_df.copy()
        sales_df["date"] = pd.to_datetime(sales_df["date"])
        last = sales_df["date"].max()
        cutoff_last = last - pd.Timedelta(days=7)
        cutoff_prior = last - pd.Timedelta(days=28)

        for (item, store), g in sales_df.groupby(["item_id", "store_id"]):
            recent = g[g["date"] > cutoff_last]["sales"].sum()
            prior = g[(g["date"] <= cutoff_last) & (g["date"] > cutoff_prior)]["sales"].sum()
            if prior <= 0:
                continue
            change_pct = (recent - prior) / prior * 100
            if change_pct >= spike_pct:
                alert = await AlertService._create_alert(
                    db, org_id, AlertType.DEMAND_SPIKE, AlertSeverity.HIGH,
                    f"Demand spike: {item} @ {store}",
                    f"Sales up {change_pct:.0f}% in the last 7 days. Consider stocking up.",
                    {"item_id": item, "store_id": store, "change_pct": round(change_pct, 1)},
                )
                if alert:
                    created += 1
            elif change_pct <= -drop_pct:
                alert = await AlertService._create_alert(
                    db, org_id, AlertType.DEMAND_DROP, AlertSeverity.MEDIUM,
                    f"Demand drop: {item} @ {store}",
                    f"Sales down {abs(change_pct):.0f}% in the last 7 days.",
                    {"item_id": item, "store_id": store, "change_pct": round(change_pct, 1)},
                )
                if alert:
                    created += 1
        return created

    @staticmethod
    async def detect_forecast_degradation(db: AsyncSession, org_id: str, active_model) -> int:
        """Flag the active model if live accuracy degraded vs evaluation."""
        if active_model is None or active_model.live_wape is None:
            return 0
        from app.services.model_registry_service import ModelRegistryService
        degraded = ModelRegistryService.check_degradation(active_model)
        if not degraded:
            return 0
        alert = await AlertService._create_alert(
            db, org_id, AlertType.FORECAST_DEGRADATION, AlertSeverity.HIGH,
            "Forecast accuracy degraded",
            f"Live WAPE {active_model.live_wape:.1f}% vs {active_model.wape:.1f}% at training. "
            "Consider retraining or rolling back.",
            {"model_version": active_model.version, "live_wape": active_model.live_wape,
             "eval_wape": active_model.wape},
        )
        return 1 if alert else 0

    @staticmethod
    async def detect_upcoming_holiday(db: AsyncSession, org_id: str, days_ahead: int = 7) -> int:
        """Flag upcoming holidays within the stock-up window."""
        from app.services.holiday_service import HolidayService
        hs = HolidayService()
        upcoming = hs.get_upcoming_holidays(datetime.now(), limit=10)
        created = 0
        for _, row in upcoming.iterrows():
            holiday_date = pd.Timestamp(row["date"]).date()
            days_until = (holiday_date - datetime.now().date()).days
            if 0 <= days_until <= days_ahead:
                alert = await AlertService._create_alert(
                    db, org_id, AlertType.UPCOMING_HOLIDAY, AlertSeverity.INFO,
                    f"Upcoming holiday: {row.get('name', 'Holiday')}",
                    f"{row.get('name', 'Holiday')} is in {days_until} days. Stock up early.",
                    {"holiday": row.get("name"), "date": str(row["date"]), "days_until": days_until},
                )
                if alert:
                    created += 1
        return created

    @staticmethod
    async def detect_store_anomaly(db: AsyncSession, org_id: str, sales_df: pd.DataFrame,
                                   z_threshold: float = 2.0) -> int:
        """Flag stores whose last-7d sales deviate from their own history."""
        created = 0
        if "date" not in sales_df.columns or "store_id" not in sales_df.columns:
            return 0
        sales_df = sales_df.copy()
        sales_df["date"] = pd.to_datetime(sales_df["date"])
        last = sales_df["date"].max()

        for store, g in sales_df.groupby("store_id"):
            daily = g.groupby("date")["sales"].sum()
            recent = daily[daily.index > last - pd.Timedelta(days=7)].mean()
            hist = daily[daily.index <= last - pd.Timedelta(days=7)]
            if len(hist) < 14:
                continue
            mean_h, std_h = hist.mean(), hist.std()
            if std_h == 0 or pd.isna(std_h):
                continue
            z = (recent - mean_h) / std_h
            if abs(z) > z_threshold:
                direction = "above" if z > 0 else "below"
                sev = AlertSeverity.HIGH if abs(z) > 3 else AlertSeverity.MEDIUM
                alert = await AlertService._create_alert(
                    db, org_id, AlertType.STORE_PERFORMANCE, sev,
                    f"Store anomaly: {store}",
                    f"{store} is running {abs(z):.1f}σ {direction} its historical average this week.",
                    {"store_id": store, "z_score": round(float(z), 2)},
                )
                if alert:
                    created += 1
        return created

    # ── Orchestration ──────────────────────────────────────────────────────

    @staticmethod
    async def run_all_detectors(db: AsyncSession, org_id: str,
                                decisions_df: pd.DataFrame | None = None,
                                sales_df: pd.DataFrame | None = None,
                                active_model=None) -> dict:
        """Run all detectors and return per-type counts."""
        counts = {}
        if decisions_df is not None and not decisions_df.empty:
            counts["stockout_risk"] = await AlertService.detect_stockout_risk(db, org_id, decisions_df)
            counts["overstock"] = await AlertService.detect_overstock(db, org_id, decisions_df)
        if sales_df is not None and not sales_df.empty:
            counts["demand_change"] = await AlertService.detect_demand_change(db, org_id, sales_df)
            counts["store_anomaly"] = await AlertService.detect_store_anomaly(db, org_id, sales_df)
        counts["forecast_degradation"] = await AlertService.detect_forecast_degradation(db, org_id, active_model)
        counts["upcoming_holiday"] = await AlertService.detect_upcoming_holiday(db, org_id)
        return counts

    @staticmethod
    async def list_alerts(db: AsyncSession, org_id: str, limit: int = 50,
                          include_resolved: bool = False) -> list[Alert]:
        query = select(Alert).where(Alert.organization_id == org_id)
        if not include_resolved:
            query = query.where(Alert.is_resolved == False)  # noqa: E712
        query = query.order_by(Alert.created_at.desc()).limit(limit)
        return (await db.execute(query)).scalars().all()

    @staticmethod
    async def mark_read(db: AsyncSession, org_id: str, alert_id: str) -> Alert | None:
        alert = (await db.execute(
            select(Alert).where(Alert.id == alert_id, Alert.organization_id == org_id)
        )).scalar_one_or_none()
        if alert:
            alert.is_read = True
            await db.commit()
        return alert

    @staticmethod
    async def resolve(db: AsyncSession, org_id: str, alert_id: str) -> Alert | None:
        alert = (await db.execute(
            select(Alert).where(Alert.id == alert_id, Alert.organization_id == org_id)
        )).scalar_one_or_none()
        if alert:
            alert.is_resolved = True
            alert.resolved_at = datetime.now(timezone.utc)
            await db.commit()
        return alert

    @staticmethod
    async def unread_count(db: AsyncSession, org_id: str) -> int:
        return len((await db.execute(
            select(Alert).where(Alert.organization_id == org_id, Alert.is_read == False)  # noqa: E712
        )).scalars().all())
