"""Tenant-scoped data service — reads and writes sales data in MySQL.

Replaces the shared flat-CSV pipeline. All functions take an explicit
organization_id and filter every query by it, so tenant isolation is
enforced at the data layer, not just in the API layer.
"""

import logging
import uuid
from datetime import date, datetime, timedelta

import pandas as pd
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Product, Store, Sale, InventoryLevel, ImportJob, ImportJobStatus, Dataset

logger = logging.getLogger(__name__)

# Columns that may appear in uploaded data (standardized after cleaning)
STANDARD_DATE_COLS = {"date", "day", "transaction_date", "sale_date", "order_date", "timestamp", "datetime"}
STANDARD_SALES_COLS = {"sales", "quantity", "demand", "qty", "units_sold", "volume", "sales_quantity", "units"}
STANDARD_ITEM_COLS = {"item_id", "product_id", "sku", "product", "item", "article"}
STANDARD_STORE_COLS = {"store_id", "store", "location", "warehouse", "branch"}
STANDARD_PRICE_COLS = {"sell_price", "price", "unit_price", "revenue_per_unit"}


class TenantDataService:
    """Read/write tenant-scoped sales, product, store, and inventory data."""

    # ── Loading org data back into a DataFrame (for ML services) ───────────

    @staticmethod
    async def load_sales_df(
        db: AsyncSession,
        organization_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
        include_price: bool = True,
    ) -> pd.DataFrame:
        """Load an organization's sales as a DataFrame in the classic format.

        Returns columns: item_id, store_id, date, sales, sell_price, category.
        item_id/store_id are the *external* codes (sku/store_code) so the rest
        of the pipeline (forecasting, inventory, analytics) keeps working
        unchanged against org-scoped data.
        """
        query = (
            select(Sale, Product.sku, Product.category, Store.store_code)
            .join(Product, Product.id == Sale.product_id)
            .join(Store, Store.id == Sale.store_id)
            .where(Sale.organization_id == organization_id)
        )
        if start_date:
            query = query.where(Sale.sale_date >= start_date)
        if end_date:
            query = query.where(Sale.sale_date <= end_date)

        rows = (await db.execute(query)).all()
        if not rows:
            return pd.DataFrame(columns=["item_id", "store_id", "date", "sales", "sell_price", "category"])

        df = pd.DataFrame([{
            "item_id": row.sku,
            "store_id": row.store_code,
            "date": row.Sale.sale_date,
            "sales": row.Sale.quantity,
            "sell_price": row.Sale.revenue / row.Sale.quantity if row.Sale.quantity else None,
            "category": row.category,
        } for row in rows])
        df["date"] = pd.to_datetime(df["date"])
        return df

    @staticmethod
    async def load_inventory_df(db: AsyncSession, organization_id: str) -> pd.DataFrame:
        """Load current on-hand stock as a DataFrame (item_id, store_id, current_stock)."""
        query = (
            select(InventoryLevel, Product.sku, Store.store_code)
            .join(Product, Product.id == InventoryLevel.product_id)
            .join(Store, Store.id == InventoryLevel.store_id)
            .where(InventoryLevel.organization_id == organization_id)
        )
        rows = (await db.execute(query)).all()
        if not rows:
            return pd.DataFrame(columns=["item_id", "store_id", "current_stock"])
        return pd.DataFrame([{
            "item_id": row.sku,
            "store_id": row.store_code,
            "current_stock": row.InventoryLevel.quantity_on_hand,
        } for row in rows])

    # ── Ingestion ────────────────────────────────────────────────────────────

    @staticmethod
    async def _get_or_create_product(db, org_id: str, sku: str, name: str | None,
                                     category: str | None, unit_price: float | None,
                                     unit_cost: float | None) -> tuple[Product, bool]:
        """Return (product, created_flag)."""
        result = await db.execute(select(Product).where(
            Product.organization_id == org_id, Product.sku == sku,
        ))
        product = result.scalar_one_or_none()
        if product:
            # Refresh pricing/category if a more recent upload has them
            if category and not product.category:
                product.category = category
            if unit_price and not product.unit_price:
                product.unit_price = unit_price
            if unit_cost and not product.unit_cost:
                product.unit_cost = unit_cost
            return product, False

        product = Product(
            organization_id=org_id,
            sku=sku,
            name=name or sku,
            category=category,
            unit_price=unit_price,
            unit_cost=unit_cost,
        )
        db.add(product)
        await db.flush()
        return product, True

    @staticmethod
    async def _get_or_create_store(db, org_id: str, store_code: str) -> tuple[Store, bool]:
        """Return (store, created_flag)."""
        result = await db.execute(select(Store).where(
            Store.organization_id == org_id, Store.store_code == store_code,
        ))
        store = result.scalar_one_or_none()
        if store:
            return store, False

        store = Store(
            organization_id=org_id,
            store_code=store_code,
            name=store_code,
        )
        db.add(store)
        await db.flush()
        return store, True

    @staticmethod
    async def ingest_dataframe(
        db: AsyncSession,
        organization_id: str,
        df: pd.DataFrame,
        source_type: str = "csv",
        source: str | None = None,
        created_by: str | None = None,
    ) -> dict:
        """Upsert cleaned sales rows into the org's MySQL tables.

        df is expected to have (at least) item_id, store_id, date, sales,
        and optionally sell_price, category, current_stock.
        """
        job = ImportJob(
            organization_id=organization_id,
            source_type=source_type,
            source=source,
            status=ImportJobStatus.RUNNING,
            rows_received=len(df),
            created_by=created_by,
        )
        db.add(job)
        await db.flush()

        if df.empty:
            job.status = ImportJobStatus.SUCCEEDED
            job.rows_imported = 0
            await db.commit()
            return {"job_id": job.id, "rows_imported": 0, "products": 0, "stores": 0, "sales": 0}

        df = df.copy()
        # Normalize column names (case-insensitive matching)
        col_map = {c: c for c in df.columns}
        for col in list(df.columns):
            lower = col.lower()
            if lower in STANDARD_DATE_COLS:
                col_map[col] = "date"
            elif lower in STANDARD_SALES_COLS:
                col_map[col] = "sales"
            elif lower in STANDARD_ITEM_COLS:
                col_map[col] = "item_id"
            elif lower in STANDARD_STORE_COLS:
                col_map[col] = "store_id"
            elif lower in STANDARD_PRICE_COLS:
                col_map[col] = "sell_price"
        df = df.rename(columns=col_map)

        # Defaults for single-item / single-store uploads
        if "item_id" not in df.columns:
            df["item_id"] = "PRODUCT_001"
        if "store_id" not in df.columns:
            df["store_id"] = "STORE_001"

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["sales"] = pd.to_numeric(df["sales"], errors="coerce").fillna(0).clip(lower=0)
        if "sell_price" in df.columns:
            df["sell_price"] = pd.to_numeric(df["sell_price"], errors="coerce").fillna(0)
        df["category"] = df.get("category")
        df = df.dropna(subset=["date"])

        # Dedupe within the batch
        subset = [c for c in ["date", "item_id", "store_id"] if c in df.columns]
        df = df.drop_duplicates(subset=subset)

        products_created = 0
        stores_created = 0
        sales_upserted = 0

        # Cache resolved ids so each sku/store_code is looked up only once
        product_ids: dict[str, str] = {}
        store_ids: dict[str, str] = {}

        # Upsert sales in batches
        batch = []
        for _, row in df.iterrows():
            sku = str(row["item_id"])
            store_code = str(row["store_id"])
            sale_date = row["date"].date()
            quantity = float(row["sales"])
            if quantity <= 0 and "sell_price" not in df.columns:
                # Skip pure zero rows only if we have nothing else to record
                if quantity == 0:
                    continue

            if sku not in product_ids:
                product, created = await TenantDataService._get_or_create_product(
                    db, organization_id, sku,
                    name=str(row.get("name", sku)) if "name" in df.columns else sku,
                    category=str(row.get("category")) if "category" in df.columns and pd.notna(row.get("category")) else None,
                    unit_price=float(row["sell_price"]) if "sell_price" in df.columns and pd.notna(row.get("sell_price")) else None,
                    unit_cost=None,
                )
                product_ids[sku] = product.id
                if created:
                    products_created += 1

            if store_code not in store_ids:
                store, created = await TenantDataService._get_or_create_store(db, organization_id, store_code)
                store_ids[store_code] = store.id
                if created:
                    stores_created += 1

            revenue = quantity * float(row["sell_price"]) if "sell_price" in df.columns and pd.notna(row.get("sell_price")) else 0.0

            batch.append({
                "organization_id": organization_id,
                "product_id": product_ids[sku],
                "store_id": store_ids[store_code],
                "sale_date": sale_date,
                "quantity": quantity,
                "revenue": revenue,
            })
            sales_upserted += 1

            if len(batch) >= 500:
                await TenantDataService._upsert_sales(db, organization_id, batch)
                batch = []

        if batch:
            await TenantDataService._upsert_sales(db, organization_id, batch)

        # Inventory levels if provided
        if "current_stock" in df.columns:
            inv_batch = []
            for _, row in df.iterrows():
                if pd.notna(row.get("current_stock")):
                    product_id = product_ids.get(str(row["item_id"]))
                    store_id = store_ids.get(str(row["store_id"]))
                    if product_id and store_id:
                        inv_batch.append({
                            "organization_id": organization_id,
                            "product_id": product_id,
                            "store_id": store_id,
                            "quantity_on_hand": float(row["current_stock"]),
                            "snapshot_date": date.today(),
                        })
            if inv_batch:
                await TenantDataService._upsert_inventory(db, organization_id, inv_batch)

        job.status = ImportJobStatus.SUCCEEDED
        job.rows_imported = sales_upserted
        job.error_message = None
        await db.commit()

        logger.info(f"Org {organization_id}: ingested {sales_upserted} sales rows "
                    f"({products_created} products, {stores_created} stores)")
        return {
            "job_id": job.id,
            "rows_imported": sales_upserted,
            "products": products_created,
            "stores": stores_created,
        }

    @staticmethod
    async def _upsert_sales(db: AsyncSession, org_id: str, rows: list[dict]) -> None:
        """Idempotent upsert of sale rows keyed on (org, date, product, store)."""
        from sqlalchemy.dialects.mysql import insert as mysql_insert

        for r in rows:
            existing = await db.execute(select(Sale.id).where(
                Sale.organization_id == org_id,
                Sale.sale_date == r["sale_date"],
                Sale.product_id == r["product_id"],
                Sale.store_id == r["store_id"],
            ))
            sale_id = existing.scalar_one_or_none()
            if sale_id:
                await db.execute(
                    update(Sale)
                    .where(Sale.id == sale_id)
                    .values(quantity=r["quantity"], revenue=r["revenue"])
                )
            else:
                db.add(Sale(**r))
        await db.flush()

    @staticmethod
    async def _upsert_inventory(db: AsyncSession, org_id: str, rows: list[dict]) -> None:
        for r in rows:
            existing = await db.execute(select(InventoryLevel.id).where(
                InventoryLevel.organization_id == org_id,
                InventoryLevel.product_id == r["product_id"],
                InventoryLevel.store_id == r["store_id"],
            ))
            level_id = existing.scalar_one_or_none()
            if level_id:
                await db.execute(
                    update(InventoryLevel)
                    .where(InventoryLevel.id == level_id)
                    .values(quantity_on_hand=r["quantity_on_hand"], snapshot_date=r["snapshot_date"])
                )
            else:
                db.add(InventoryLevel(**r))
        await db.flush()

    @staticmethod
    async def ingest_rows_json(
        db: AsyncSession,
        organization_id: str,
        rows: list[dict],
        created_by: str | None = None,
    ) -> dict:
        """Ingest a list of row dicts from the API/webhook endpoint."""
        df = pd.DataFrame(rows)
        return await TenantDataService.ingest_dataframe(
            db, organization_id, df, source_type="api", created_by=created_by,
        )

    # ── Health / stats ───────────────────────────────────────────────────────

    @staticmethod
    async def org_data_summary(db: AsyncSession, organization_id: str) -> dict:
        """Quick summary of what data an org has loaded."""
        products = (await db.execute(
            select(Product).where(Product.organization_id == organization_id)
        )).scalars().all()
        stores = (await db.execute(
            select(Store).where(Store.organization_id == organization_id)
        )).scalars().all()

        min_date = None
        max_date = None
        total_rows = 0
        result = await db.execute(
            select(Sale.sale_date)
            .where(Sale.organization_id == organization_id)
            .order_by(Sale.sale_date)
            .limit(1)
        )
        first = result.scalar_one_or_none()
        if first:
            min_date = first
            result = await db.execute(
                select(Sale.sale_date)
                .where(Sale.organization_id == organization_id)
                .order_by(Sale.sale_date.desc())
                .limit(1)
            )
            max_date = result.scalar_one_or_none()
            total_rows = (await db.execute(
                select(Sale.id).where(Sale.organization_id == organization_id)
            )).all()
            total_rows = len(total_rows)

        return {
            "products": len(products),
            "stores": len(stores),
            "sales_rows": total_rows,
            "date_start": str(min_date) if min_date else None,
            "date_end": str(max_date) if max_date else None,
            "days_covered": (max_date - min_date).days if min_date and max_date else 0,
        }
