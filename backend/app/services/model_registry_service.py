"""Model Registry service — training, versioning, promotion, rollback, monitoring.

Owns the lifecycle of ModelArtifact rows and their artifact files:
  train_and_register → evaluate → promote → monitor → rollback
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
from sqlalchemy import select, desc, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ModelArtifact, ModelStatus, ForecastAccuracy, Dataset
from app.models.model_registry import ModelStatus
from app.services.forecasting import DemandForecaster
from app.services.forecast_metrics import full_metrics, evaluate_forecast_df
from app.services.data_service import TenantDataService

logger = logging.getLogger(__name__)

MODEL_ROOT = "models"  # per-org artifacts live at models/{org_id}/registry/{version}.joblib

# Metric threshold: a new candidate must beat the active model by at least this
# relative improvement on the primary metric to be auto-promoted.
MIN_IMPROVEMENT_TO_PROMOTE = 0.02  # 2%
# Degradation: if live WAPE exceeds the evaluation WAPE by this factor, flag it.
DEGRADATION_WAPE_FACTOR = 1.25
DEGRADATION_BIAS_PCT = 15.0  # |bias%| beyond this flags degradation


class ModelRegistryService:
    """Lifecycle operations for the org's model registry."""

    @staticmethod
    def _artifact_path(org_id: str, version: str) -> str:
        return os.path.join(MODEL_ROOT, org_id, "registry", f"{version}.joblib")

    # ── Training & registration ─────────────────────────────────────────────

    @staticmethod
    async def train_and_register(
        db: AsyncSession,
        organization_id: str,
        data_df: pd.DataFrame,
        created_by: Optional[str] = None,
        algorithms: list[str] | None = None,
        sample_size: int = 50000,
        test_size: float = 0.2,
        notes: Optional[str] = None,
    ) -> ModelArtifact:
        """Train all algorithms, register each as a candidate, promote the best.

        Returns the best (promoted) ModelArtifact.
        """
        if data_df.empty:
            raise ValueError("No training data")

        if sample_size < len(data_df):
            data_df = data_df.sample(n=sample_size, random_state=42)

        # Train all models and get comparison
        forecaster = DemandForecaster()
        comparison_df, best_name = forecaster.train_all_models(
            data_df, target_col="sales", test_size=test_size,
            include_prophet="prophet" in (algorithms or []),
            include_baseline="baseline" in (algorithms or []),
        )

        # Split for evaluation (held-out)
        X, y = forecaster.prepare_features(data_df, target_col="sales")
        mask = y.notna()
        X, y = X[mask], y[mask]
        from sklearn.model_selection import train_test_split
        _, X_test, _, y_test = train_test_split(X, y, test_size=test_size, random_state=42)

        # Register each trained model as a candidate version
        registered = []
        for _, row in comparison_df.iterrows():
            algo = row["model"]
            version = f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{algo}"
            artifact = ModelArtifact(
                organization_id=organization_id,
                name=f"{algo} demand model",
                version=version,
                algorithm=algo,
                status=ModelStatus.CANDIDATE,
                is_active=False,
                trained_by=created_by,
                data_rows=len(data_df),
                data_start=str(data_df["date"].min().date()) if "date" in data_df.columns else None,
                data_end=str(data_df["date"].max().date()) if "date" in data_df.columns else None,
                features_used=json.dumps(forecaster.feature_names or []),
                mae=row.get("MAE"),
                rmse=row.get("RMSE"),
                mape=row.get("MAPE"),
                wape=row.get("WAPE") if "WAPE" in row else None,
                bias=row.get("bias") if "bias" in row else None,
                r2=row.get("R2"),
                evaluation_window_days=int(len(y_test)),
                hyperparameters=json.dumps({"test_size": test_size}),
                notes=notes,
            )

            # Save the trained artifact file
            path = ModelRegistryService._artifact_path(organization_id, version)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            best_forecaster = DemandForecaster(model_type=algo)
            try:
                best_forecaster.train_model(data_df, target_col="sales")
                best_forecaster.save_model(path)
                artifact.model_path = path
            except Exception as e:
                logger.error(f"Failed to save artifact for {algo}: {e}")
                artifact.status = ModelStatus.FAILED

            db.add(artifact)
            registered.append(artifact)

        await db.flush()

        # Find the best by WAPE (fallback MAE)
        best_artifact = None
        candidates = [a for a in registered if a.status != ModelStatus.FAILED and a.wape is not None]
        if candidates:
            best_artifact = min(candidates, key=lambda a: a.wape or 1e18)
        elif registered:
            best_artifact = next((a for a in registered if a.algorithm == best_name), registered[0])

        return best_artifact

    # ── Promotion & rollback ────────────────────────────────────────────────

    @staticmethod
    async def promote(db: AsyncSession, artifact: ModelArtifact, promoted_by: Optional[str] = None) -> None:
        """Promote a candidate to active; demote the previous active to archived."""
        # Deactivate current active
        active = (await db.execute(
            select(ModelArtifact).where(
                ModelArtifact.organization_id == artifact.organization_id,
                ModelArtifact.is_active == True,  # noqa: E712
            )
        )).scalars().all()
        for a in active:
            if a.id == artifact.id:
                continue
            a.is_active = False
            a.status = ModelStatus.ARCHIVED

        artifact.is_active = True
        artifact.status = ModelStatus.ACTIVE
        artifact.promoted_at = datetime.now(timezone.utc)
        artifact.promoted_by = promoted_by
        await db.commit()

    @staticmethod
    async def rollback(db: AsyncSession, org_id: str, target_version: str, rolled_back_by: Optional[str] = None) -> ModelArtifact:
        """Roll the registry back to a previous (archived) version."""
        result = await db.execute(
            select(ModelArtifact).where(
                ModelArtifact.organization_id == org_id,
                ModelArtifact.version == target_version,
            )
        )
        target = result.scalar_one_or_none()
        if target is None:
            raise ValueError(f"No artifact with version {target_version}")

        if target.is_active:
            raise ValueError("Version is already active")

        # Mark current active as rolled-back
        active = (await db.execute(
            select(ModelArtifact).where(
                ModelArtifact.organization_id == org_id,
                ModelArtifact.is_active == True,  # noqa: E712
            )
        )).scalars().all()
        for a in active:
            a.is_active = False
            a.status = ModelStatus.ROLLED_BACK

        target.is_active = True
        target.status = ModelStatus.ACTIVE
        target.promoted_at = datetime.now(timezone.utc)
        target.promoted_by = rolled_back_by
        target.notes = (target.notes or "") + " [rolled back to]"
        await db.commit()
        return target

    @staticmethod
    async def get_active(db: AsyncSession, org_id: str) -> Optional[ModelArtifact]:
        result = await db.execute(
            select(ModelArtifact).where(
                ModelArtifact.organization_id == org_id,
                ModelArtifact.is_active == True,  # noqa: E712
            )
            .order_by(desc(ModelArtifact.promoted_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_versions(db: AsyncSession, org_id: str, limit: int = 50) -> list[ModelArtifact]:
        result = await db.execute(
            select(ModelArtifact)
            .where(ModelArtifact.organization_id == org_id)
            .order_by(desc(ModelArtifact.trained_at))
            .limit(limit)
        )
        return result.scalars().all()

    # ── Evaluation vs actuals (post-deployment monitoring) ──────────────────

    @staticmethod
    async def evaluate_matured_forecasts(db: AsyncSession, organization_id: str) -> dict:
        """Compare forecasted sales against actuals for dates that have matured.

        Runs for the active model's forecast headers; writes ForecastAccuracy
        rows per product/store/category/horizon and updates the artifact's
        live metrics. Returns a summary dict.
        """
        from app.models import ForecastHeader, Forecast, Sale, Product, Store

        active = await ModelRegistryService.get_active(db, organization_id)
        if active is None:
            return {"status": "no_active_model"}

        # All forecast headers belonging to this org (not strictly tied to the
        # active model artifact yet — headers store model_type + horizon).
        headers = (await db.execute(
            select(ForecastHeader).where(ForecastHeader.organization_id == organization_id)
        )).scalars().all()

        results = []
        for header in headers:
            horizon = header.horizon_days
            # Matured forecast rows: forecast_date <= today and forecast_date
            # was generated at least 1 day ago (i.e. we have actuals).
            details = (await db.execute(
                select(Forecast).where(Forecast.header_id == header.id)
            )).scalars().all()
            if not details:
                continue

            forecast_rows = pd.DataFrame([{
                "item_id": d.item_id,
                "store_id": d.store_id,
                "date": d.forecast_date,
                "predicted_sales": d.predicted_sales,
            } for d in details])
            forecast_rows["date"] = pd.to_datetime(forecast_rows["date"])
            forecast_rows = forecast_rows[forecast_rows["date"] <= pd.Timestamp.today().normalize()]

            if forecast_rows.empty:
                continue

            # Fetch actuals for those dates from the org's sales table
            dates = forecast_rows["date"].dt.date.unique().tolist()
            sale_rows = (await db.execute(
                select(Sale, Product.sku, Product.category, Store.store_code)
                .join(Product, Product.id == Sale.product_id)
                .join(Store, Store.id == Sale.store_id)
                .where(
                    Sale.organization_id == organization_id,
                    Sale.sale_date.in_(dates),
                )
            )).all()

            actual_df = pd.DataFrame([{
                "item_id": r.sku,
                "store_id": r.store_code,
                "category": r.category,
                "date": pd.Timestamp(r.Sale.sale_date),
                "sales": r.Sale.quantity,
            } for r in sale_rows])
            if actual_df.empty:
                continue

            # Evaluate per product × store
            evaluated = evaluate_forecast_df(
                forecast_rows, actual_df,
                grain=["item_id", "store_id"],
            )
            for _, row in evaluated.iterrows():
                acc = ForecastAccuracy(
                    organization_id=organization_id,
                    model_id=active.id,
                    product_id=row.get("item_id"),
                    store_id=row.get("store_id"),
                    horizon_days=horizon,
                    eval_points=int(row["points"]),
                    mae=row.get("mae"),
                    rmse=row.get("rmse"),
                    mape=row.get("mape"),
                    wape=row.get("wape"),
                    bias=row.get("bias"),
                )
                db.add(acc)
                results.append(acc)

            # Update the active artifact's live metrics (aligned actuals vs forecasts)
            aligned = forecast_rows.merge(
                actual_df[["date", "item_id", "store_id", "sales"]],
                on=["date", "item_id", "store_id"],
                how="inner",
            )
            if not aligned.empty:
                overall = full_metrics(aligned["sales"].values, aligned["predicted_sales"].values)
                active.live_mae = overall["mae"]
                active.live_wape = overall["wape"]
                active.live_bias = overall["bias"]
                active.live_evaluated_at = datetime.now(timezone.utc)

        await db.commit()
        return {"status": "ok", "accuracy_rows": len(results)}

    @staticmethod
    def check_degradation(artifact: ModelArtifact) -> bool:
        """Detect performance degradation on the active model."""
        if artifact.live_wape is None or artifact.wape is None:
            return False
        wape_degraded = artifact.live_wape > artifact.wape * DEGRADATION_WAPE_FACTOR
        bias_abs = abs(artifact.live_bias or 0)
        bias_scale = abs(artifact.live_wape or 1) or 1
        bias_degraded = bias_abs / bias_scale > DEGRADATION_BIAS_PCT / 100
        return wape_degraded or bias_degraded

    # ── Auto-retrain decision ───────────────────────────────────────────────

    @staticmethod
    def should_auto_retrain(artifact: ModelArtifact, since_days: int = 7) -> bool:
        """Decide whether to trigger auto-retraining."""
        if artifact is None:
            return True
        if artifact.degradation_flagged:
            return True
        # Retrain at least every N days
        if artifact.trained_at:
            age_days = (datetime.now(timezone.utc) - artifact.trained_at).days
            if age_days >= since_days:
                return True
        return False

    @staticmethod
    def meets_promotion_bar(candidate: ModelArtifact, active: ModelArtifact | None) -> bool:
        """A candidate may be auto-promoted only if it clearly beats the active."""
        if active is None:
            return True
        cand_wape = candidate.wape if candidate.wape is not None else candidate.mae
        act_wape = active.wape if active.wape is not None else active.mae
        if cand_wape is None or act_wape is None or act_wape == 0:
            return False
        improvement = (act_wape - cand_wape) / act_wape
        return improvement >= MIN_IMPROVEMENT_TO_PROMOTE


