"""SQLite database layer for storing datasets, forecasts, inventory, and model history."""

import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).resolve().parent.parent / 'data' / 'retailiq.db'


class Database:
    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()

        c.execute('''
            CREATE TABLE IF NOT EXISTS uploaded_datasets (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                filename    TEXT NOT NULL,
                table_name  TEXT NOT NULL,
                row_count   INTEGER,
                column_count INTEGER,
                file_size_kb REAL,
                status      TEXT DEFAULT 'pending',
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS cleaned_datasets (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id   INTEGER NOT NULL,
                table_name  TEXT NOT NULL,
                row_count   INTEGER,
                cleaned_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_id) REFERENCES uploaded_datasets(id)
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS forecasts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_id  INTEGER,
                model_type  TEXT,
                horizon_days INTEGER,
                item_id     TEXT,
                store_id    TEXT,
                forecast_date DATE,
                predicted_sales REAL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dataset_id) REFERENCES uploaded_datasets(id)
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS forecast_headers (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_id  INTEGER,
                model_type  TEXT,
                horizon_days INTEGER,
                item_count  INTEGER,
                store_count INTEGER,
                total_forecast REAL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dataset_id) REFERENCES uploaded_datasets(id)
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS inventory_recommendations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_id  INTEGER,
                item_id     TEXT,
                store_id    TEXT,
                current_stock    REAL DEFAULT 0,
                avg_daily_demand REAL,
                demand_std       REAL,
                safety_stock     REAL,
                reorder_point    REAL,
                eoq              REAL,
                recommended_order REAL,
                stockout_in_days REAL,
                stockout_date    TEXT,
                status           TEXT,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dataset_id) REFERENCES uploaded_datasets(id)
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS model_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_id  INTEGER,
                model_type  TEXT NOT NULL,
                mae         REAL,
                rmse        REAL,
                mape        REAL,
                r2          REAL,
                training_time_sec REAL,
                feature_count INTEGER,
                is_best     INTEGER DEFAULT 0,
                trained_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dataset_id) REFERENCES uploaded_datasets(id)
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS business_insights (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_id  INTEGER,
                insight_type TEXT,
                insight_text TEXT,
                category    TEXT,
                severity    TEXT DEFAULT 'info',
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dataset_id) REFERENCES uploaded_datasets(id)
            )
        ''')

        conn.commit()
        conn.close()

    # ── Uploads ─────────────────────────────────────────────────────────────

    def save_uploaded_dataset(self, filename: str, df: pd.DataFrame) -> tuple:
        """Save uploaded dataframe to a table and log metadata.
        Returns (dataset_id, table_name).
        """
        ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        table_name = f'upload_{ts}'
        conn = sqlite3.connect(str(self.db_path))
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        size_kb = df.memory_usage(deep=True).sum() / 1024
        c = conn.cursor()
        c.execute('''
            INSERT INTO uploaded_datasets (filename, table_name, row_count, column_count, file_size_kb, status)
            VALUES (?, ?, ?, ?, ?, 'uploaded')
        ''', (filename, table_name, len(df), len(df.columns), round(size_kb, 2)))
        dataset_id = c.lastrowid
        conn.commit()
        conn.close()
        return dataset_id, table_name

    def update_upload_status(self, dataset_id: int, status: str):
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute('UPDATE uploaded_datasets SET status = ? WHERE id = ?', (status, dataset_id))
        conn.commit()
        conn.close()

    def get_uploaded_datasets(self) -> pd.DataFrame:
        conn = sqlite3.connect(str(self.db_path))
        df = pd.read_sql('SELECT * FROM uploaded_datasets ORDER BY uploaded_at DESC', conn)
        conn.close()
        return df

    def get_uploaded_table(self, dataset_id: int) -> pd.DataFrame:
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute('SELECT table_name FROM uploaded_datasets WHERE id = ?', (dataset_id,))
        row = c.fetchone()
        conn.close()
        if not row:
            raise FileNotFoundError(f'No dataset with id={dataset_id}')
        conn = sqlite3.connect(str(self.db_path))
        df = pd.read_sql(f'SELECT * FROM "{row[0]}"', conn)
        conn.close()
        return df

    # ── Cleaned datasets ────────────────────────────────────────────────────

    def save_cleaned_dataset(self, source_id: int, df: pd.DataFrame) -> str:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        table_name = f'cleaned_{ts}'
        conn = sqlite3.connect(str(self.db_path))
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        c = conn.cursor()
        c.execute('''
            INSERT INTO cleaned_datasets (source_id, table_name, row_count)
            VALUES (?, ?, ?)
        ''', (source_id, table_name, len(df)))
        conn.commit()
        conn.close()
        return table_name

    def get_latest_cleaned_table(self) -> pd.DataFrame:
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute('SELECT table_name FROM cleaned_datasets ORDER BY cleaned_at DESC LIMIT 1')
        row = c.fetchone()
        if not row:
            conn.close()
            return None
        df = pd.read_sql(f'SELECT * FROM "{row[0]}"', conn)
        conn.close()
        return df

    # ── Forecasts ───────────────────────────────────────────────────────────

    def save_forecast(self, dataset_id: int, model_type: str, horizon_days: int,
                      forecast_df: pd.DataFrame):
        """Save individual forecast records."""
        conn = sqlite3.connect(str(self.db_path))
        forecast_df.to_sql('_forecast_batch', conn, if_exists='replace', index=False)
        c = conn.cursor()
        # Move from temp table with metadata
        c.execute('''
            INSERT INTO forecasts (dataset_id, model_type, horizon_days, item_id, store_id, forecast_date, predicted_sales)
            SELECT ?, ?, ?, item_id, store_id, date, predicted_sales FROM _forecast_batch
        ''', (dataset_id, model_type, horizon_days))
        conn.commit()
        c.execute('DROP TABLE IF EXISTS _forecast_batch')
        conn.commit()
        conn.close()

    def save_forecast_header(self, dataset_id: int, model_type: str,
                              horizon_days: int, item_count: int,
                              store_count: int, total_forecast: float):
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute('''
            INSERT INTO forecast_headers (dataset_id, model_type, horizon_days, item_count, store_count, total_forecast)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (dataset_id, model_type, horizon_days, item_count, store_count, total_forecast))
        conn.commit()
        conn.close()

    def get_forecast_history(self) -> pd.DataFrame:
        conn = sqlite3.connect(str(self.db_path))
        df = pd.read_sql('SELECT * FROM forecast_headers ORDER BY created_at DESC', conn)
        conn.close()
        return df

    # ── Inventory ───────────────────────────────────────────────────────────

    def save_inventory_recommendations(self, dataset_id: int, recs_df: pd.DataFrame):
        conn = sqlite3.connect(str(self.db_path))
        recs_df.to_sql('_inv_batch', conn, if_exists='replace', index=False)
        c = conn.cursor()
        c.execute('''
            INSERT INTO inventory_recommendations
                (dataset_id, item_id, store_id, current_stock, avg_daily_demand,
                 demand_std, safety_stock, reorder_point, eoq, recommended_order,
                 stockout_in_days, stockout_date, status)
            SELECT ?, item_id, store_id, current_stock, avg_daily_demand,
                   demand_std, safety_stock, reorder_point, eoq, recommended_order_qty,
                   stockout_in_days, stockout_date, status FROM _inv_batch
        ''', (dataset_id,))
        conn.commit()
        c.execute('DROP TABLE IF EXISTS _inv_batch')
        conn.commit()
        conn.close()

    def get_inventory_history(self) -> pd.DataFrame:
        conn = sqlite3.connect(str(self.db_path))
        df = pd.read_sql('''
            SELECT DISTINCT ir.*, fh.horizon_days, fh.model_type
            FROM inventory_recommendations ir
            LEFT JOIN forecast_headers fh ON ir.dataset_id = fh.dataset_id
            ORDER BY ir.created_at DESC
        ''', conn)
        conn.close()
        return df

    # ── Model History ───────────────────────────────────────────────────────

    def save_model_metrics(self, dataset_id: int, model_type: str,
                           metrics: dict, feature_count: int = None):
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        # Mark previous best=0 for this model type
        c.execute('UPDATE model_history SET is_best = 0 WHERE model_type = ?', (model_type,))
        c.execute('''
            INSERT INTO model_history
                (dataset_id, model_type, mae, rmse, mape, r2,
                 training_time_sec, feature_count, is_best)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            dataset_id, model_type,
            metrics.get('MAE'), metrics.get('RMSE'), metrics.get('MAPE'),
            metrics.get('R2'), metrics.get('training_time_sec'),
            feature_count,
            1 if metrics.get('is_best', False) else 0
        ))
        conn.commit()
        conn.close()

    def get_model_history(self, limit: int = 20) -> pd.DataFrame:
        conn = sqlite3.connect(str(self.db_path))
        df = pd.read_sql('''
            SELECT * FROM model_history
            ORDER BY trained_at DESC LIMIT ?
        ''', conn, params=(limit,))
        conn.close()
        return df

    def get_best_model(self):
        conn = sqlite3.connect(str(self.db_path))
        df = pd.read_sql(
            'SELECT * FROM model_history WHERE is_best = 1 ORDER BY trained_at DESC LIMIT 1',
            conn
        )
        conn.close()
        return df.iloc[0] if len(df) > 0 else None

    # ── Insights ────────────────────────────────────────────────────────────

    def save_insight(self, dataset_id: int, insight_type: str,
                     insight_text: str, category: str, severity: str = 'info'):
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute('''
            INSERT INTO business_insights (dataset_id, insight_type, insight_text, category, severity)
            VALUES (?, ?, ?, ?, ?)
        ''', (dataset_id, insight_type, insight_text, category, severity))
        conn.commit()
        conn.close()

    def get_insights(self, limit: int = 50) -> pd.DataFrame:
        conn = sqlite3.connect(str(self.db_path))
        df = pd.read_sql('''
            SELECT * FROM business_insights ORDER BY created_at DESC LIMIT ?
        ''', conn, params=(limit,))
        conn.close()
        return df
