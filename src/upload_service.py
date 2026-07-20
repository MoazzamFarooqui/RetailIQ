"""Data upload, validation, and auto-cleaning module."""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import re


class DataValidator:
    """Validates uploaded CSV files for the retail forecasting pipeline."""

    REQUIRED_COLUMNS = {
        'minimal': {'date', 'sales'},
        'recommended': {'date', 'sales', 'item_id', 'store_id'},
        'full': {'date', 'sales', 'item_id', 'store_id', 'cat_id', 'dept_id', 'state_id', 'sell_price'}
    }

    @staticmethod
    def validate_csv(filepath) -> dict:
        """Validate a CSV file and return a report dict."""
        result = {
            'valid': False,
            'filename': Path(filepath).name,
            'errors': [],
            'warnings': [],
            'row_count': 0,
            'column_count': 0,
            'columns': [],
            'dtypes': {},
            'missing_pct': {},
            'date_range': None,
            'sales_stats': None,
            'has_price': False,
        }

        try:
            df = pd.read_csv(filepath, nrows=0)
            result['columns'] = list(df.columns)
            result['column_count'] = len(df.columns)
        except Exception as e:
            result['errors'].append(f"Cannot read CSV header: {e}")
            return result

        try:
            df = pd.read_csv(filepath)
            result['row_count'] = len(df)
        except Exception as e:
            result['errors'].append(f"Cannot parse CSV: {e}")
            return result

        if len(df) == 0:
            result['errors'].append("CSV file is empty")
            return result

        cols_lower = set(c.lower().strip() for c in df.columns)
        # Check for both date and sales column variants
        date_keywords = {'date', 'day', 'timestamp', 'ds'}
        sales_keywords = {'sales', 'sales_amount', 'quantity', 'demand', 'units', 'qty'}
        has_date = bool(cols_lower.intersection(date_keywords))
        has_sales = bool(cols_lower.intersection(sales_keywords))
        if not (has_date and has_sales):
            result['errors'].append(
                "Missing required columns: need both a 'date' column and a 'sales' (or quantity/demand) column. "
                f"Found: {list(df.columns)}"
            )
            return result

        # Rename common variations
        rename_map = {}
        for c in df.columns:
            cl = c.lower().strip()
            if cl in ('date', 'day', 'timestamp', 'ds'):
                rename_map[c] = 'date'
            elif cl in ('sales', 'sales_amount', 'quantity', 'demand', 'units', 'qty'):
                rename_map[c] = 'sales'
            elif cl in ('item', 'item_id', 'product', 'product_id', 'sku'):
                rename_map[c] = 'item_id'
            elif cl in ('store', 'store_id', 'location', 'warehouse'):
                rename_map[c] = 'store_id'
            elif cl in ('price', 'sell_price', 'unit_price', 'price_per_unit'):
                rename_map[c] = 'sell_price'
            elif cl in ('category', 'cat_id', 'product_category'):
                rename_map[c] = 'cat_id'
            elif cl in ('department', 'dept_id'):
                rename_map[c] = 'dept_id'
            elif cl in ('state', 'state_id', 'region'):
                rename_map[c] = 'state_id'

        df = df.rename(columns=rename_map)
        result['rename_map'] = rename_map

        # Parse date
        try:
            df['date'] = pd.to_datetime(df['date'])
            result['date_range'] = {
                'min': df['date'].min(),
                'max': df['date'].max(),
                'days': (df['date'].max() - df['date'].min()).days + 1
            }
        except Exception as e:
            result['errors'].append(f"Cannot parse date column: {e}")

        # Parse sales
        try:
            df['sales'] = pd.to_numeric(df['sales'], errors='coerce')
            sales_clean = df['sales'].dropna()
            result['sales_stats'] = {
                'min': float(sales_clean.min()),
                'max': float(sales_clean.max()),
                'mean': float(sales_clean.mean()),
                'median': float(sales_clean.median()),
                'sum': float(sales_clean.sum()),
                'negative_count': int((sales_clean < 0).sum()),
                'zero_count': int((sales_clean == 0).sum())
            }
        except Exception:
            result['errors'].append("Cannot parse sales column as numeric")

        # Check missing values
        missing = df.isnull().sum()
        result['missing_pct'] = (missing[missing > 0] / len(df) * 100).round(2).to_dict()

        result['has_price'] = 'sell_price' in df.columns
        result['has_item'] = 'item_id' in df.columns
        result['has_store'] = 'store_id' in df.columns

        # Warnings
        if result.get('sales_stats', {}).get('negative_count', 0) > 0:
            result['warnings'].append(
                f"Found {result['sales_stats']['negative_count']} negative sales values"
            )
        if result.get('sales_stats', {}).get('zero_count', 0) > len(df) * 0.5:
            result['warnings'].append("More than 50% of sales are zero")
        if result.get('missing_pct', {}):
            for col, pct in result['missing_pct'].items():
                if pct > 20:
                    result['warnings'].append(f"Column '{col}' is {pct:.1f}% missing")

        result['valid'] = len(result['errors']) == 0
        return result

    @staticmethod
    def auto_clean(df: pd.DataFrame, validation_report: dict = None) -> pd.DataFrame:
        """Automatically clean a dataframe based on validation results."""
        df = df.copy()

        # Apply renames from validation
        if validation_report and 'rename_map' in validation_report:
            df = df.rename(columns=validation_report['rename_map'])

        # Ensure date is datetime
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')

        # Sales as numeric
        if 'sales' in df.columns:
            df['sales'] = pd.to_numeric(df['sales'], errors='coerce')

            # Cap negative sales to 0
            df['sales'] = df['sales'].clip(lower=0)

            # Fill NaN sales with median
            if df['sales'].isnull().any():
                df['sales'] = df['sales'].fillna(df['sales'].median())

        # Price cleaning
        if 'sell_price' in df.columns:
            df['sell_price'] = pd.to_numeric(df['sell_price'], errors='coerce')
            df['sell_price'] = df['sell_price'].clip(lower=0)
            if df['sell_price'].isnull().any():
                df['sell_price'] = df['sell_price'].fillna(df['sell_price'].median())

        # Fill missing categoricals
        for col in ['item_id', 'store_id', 'cat_id', 'dept_id', 'state_id']:
            if col in df.columns:
                df[col] = df[col].fillna('Unknown')
                df[col] = df[col].astype(str)

        # Add default ids if missing
        if 'item_id' not in df.columns:
            df['item_id'] = 'ITEM_001'
        if 'store_id' not in df.columns:
            df['store_id'] = 'STORE_001'
        if 'cat_id' not in df.columns:
            df['cat_id'] = 'General'
        if 'dept_id' not in df.columns:
            df['dept_id'] = 'Dept_001'
        if 'state_id' not in df.columns:
            df['state_id'] = 'Unknown'

        # Remove duplicates (exact row duplicates)
        before = len(df)
        df = df.drop_duplicates()
        # Sort by date
        if 'date' in df.columns:
            df = df.sort_values('date').reset_index(drop=True)

        return df
