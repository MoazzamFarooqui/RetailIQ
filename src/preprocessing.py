import pandas as pd
import numpy as np
import joblib
import os
from sklearn.preprocessing import LabelEncoder, StandardScaler

class DataPreprocessor:
    def __init__(self):
        self.label_encoders = {}
        self.scaler = None

    def clean_calendar(self, df):
        """Clean calendar data"""
        df = df.copy()

        # Replace 'NA' strings with NaN
        df = df.replace('NA', np.nan)

        # Ensure date is datetime
        if not pd.api.types.is_datetime64_any_dtype(df['date']):
            df['date'] = pd.to_datetime(df['date'])

        # Add 'd' column if missing (maps d_1..d_N to calendar rows)
        # M5 calendar: d_1 is the first day in the calendar
        if 'd' not in df.columns:
            df['d'] = [f'd_{i+1}' for i in range(len(df))]

        # Fill missing event information
        event_columns = ['event_name_1', 'event_type_1', 'event_name_2', 'event_type_2']
        for col in event_columns:
            if col in df.columns:
                df[col] = df[col].fillna('None')

        return df

    def clean_sales(self, df):
        """Clean sales data"""
        df = df.copy()

        # Check for missing values
        missing_counts = df.isnull().sum()
        if missing_counts.any():
            print(f"Missing values found:\n{missing_counts[missing_counts > 0]}")

        # Remove duplicates
        initial_rows = len(df)
        df = df.drop_duplicates()
        if len(df) < initial_rows:
            print(f"Removed {initial_rows - len(df)} duplicate rows")

        return df

    def clean_prices(self, df):
        """Clean price data"""
        df = df.copy()

        # Check for negative prices
        if (df['sell_price'] < 0).any():
            print(f"Warning: Found {(df['sell_price'] < 0).sum()} negative prices")
            df = df[df['sell_price'] >= 0]

        # Remove duplicates
        df = df.drop_duplicates(subset=['store_id', 'item_id', 'wm_yr_wk'])

        return df

    def melt_sales_data(self, sales_df):
        """Transform sales data from wide to long format"""
        # Identify the id columns (non-date columns)
        # The actual data has item_id, dept_id, cat_id, store_id, state_id (no bare 'id' column)
        id_cols = [col for col in ['id', 'item_id', 'dept_id', 'cat_id', 'store_id', 'state_id']
                   if col in sales_df.columns]

        # Get day columns (d_1, d_2, etc.)
        day_cols = [col for col in sales_df.columns if col.startswith('d_')]

        # Melt the dataframe
        sales_long = pd.melt(
            sales_df,
            id_vars=id_cols,
            value_vars=day_cols,
            var_name='d',
            value_name='sales'
        )

        return sales_long

    def merge_datasets(self, sales_df, calendar_df, prices_df):
        """Merge all datasets into one"""
        # Ensure sales is in long format
        if 'd_1' in sales_df.columns:
            sales_df = self.melt_sales_data(sales_df)

        # Merge sales with calendar
        df = sales_df.merge(calendar_df, on='d', how='left')

        # Merge with prices
        df = df.merge(prices_df, on=['store_id', 'item_id', 'wm_yr_wk'], how='left')

        return df

    def fit_scaler(self, df, columns):
        """Fit a StandardScaler on selected numeric columns"""
        self.scaler = StandardScaler()
        self.scaler.fit(df[columns])
        return self.scaler

    def transform_scaler(self, df, columns):
        """Transform columns using fitted scaler"""
        if self.scaler is None:
            raise ValueError("Scaler not fitted. Call fit_scaler() first.")
        df = df.copy()
        df[columns] = self.scaler.transform(df[columns])
        return df

    def save_encoders(self, filepath):
        """Save label encoders and scaler to disk"""
        save_data = {
            'label_encoders': self.label_encoders,
            'scaler': self.scaler
        }
        joblib.dump(save_data, filepath)
        print(f"Encoders saved to {filepath}")

    def load_encoders(self, filepath):
        """Load label encoders and scaler from disk"""
        save_data = joblib.load(filepath)
        self.label_encoders = save_data.get('label_encoders', {})
        self.scaler = save_data.get('scaler')
        print(f"Encoders loaded from {filepath}")

    def encode_categorical(self, df, columns):
        """Encode categorical columns"""
        df = df.copy()

        for col in columns:
            if col in df.columns:
                if col not in self.label_encoders:
                    self.label_encoders[col] = LabelEncoder()
                    df[f'{col}_encoded'] = self.label_encoders[col].fit_transform(df[col].astype(str))
                else:
                    df[f'{col}_encoded'] = self.label_encoders[col].transform(df[col].astype(str))

        return df

    def handle_missing_values(self, df, strategy='median'):
        """Handle missing values in the dataset"""
        df = df.copy()

        numeric_cols = df.select_dtypes(include=[np.number]).columns

        if strategy == 'median':
            for col in numeric_cols:
                if df[col].isnull().any():
                    df[col] = df[col].fillna(df[col].median())
        elif strategy == 'mean':
            for col in numeric_cols:
                if df[col].isnull().any():
                    df[col] = df[col].fillna(df[col].mean())
        elif strategy == 'zero':
            df[numeric_cols] = df[numeric_cols].fillna(0)

        return df
