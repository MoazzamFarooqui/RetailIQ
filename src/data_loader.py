import pandas as pd
import os
from pathlib import Path

class DataLoader:
    def __init__(self, data_dir='data/raw'):
        self.data_dir = Path(data_dir)

    def load_calendar(self):
        """Load calendar data with date information and events"""
        calendar_path = self.data_dir / 'calendar.csv'
        if not calendar_path.exists():
            raise FileNotFoundError(f"Calendar file not found at {calendar_path}")

        df = pd.read_csv(calendar_path)
        df['date'] = pd.to_datetime(df['date'])
        return df

    def load_sales(self):
        """Load sales training data"""
        sales_path = self.data_dir / 'sales_train_evaluation.csv'
        if not sales_path.exists():
            sales_path = self.data_dir / 'sales_train_validation.csv'

        if not sales_path.exists():
            raise FileNotFoundError(f"Sales file not found at {self.data_dir}")

        df = pd.read_csv(sales_path)
        return df

    def load_prices(self):
        """Load sell prices data"""
        prices_path = self.data_dir / 'sell_prices.csv'
        if not prices_path.exists():
            raise FileNotFoundError(f"Prices file not found at {prices_path}")

        df = pd.read_csv(prices_path)
        return df

    def load_all_data(self):
        """Load all datasets and return as a dictionary"""
        return {
            'calendar': self.load_calendar(),
            'sales': self.load_sales(),
            'prices': self.load_prices()
        }

    def get_data_info(self):
        """Get information about loaded datasets"""
        data = self.load_all_data()
        info = {}

        for name, df in data.items():
            info[name] = {
                'shape': df.shape,
                'columns': list(df.columns),
                'memory_usage': f"{df.memory_usage(deep=True).sum() / 1024**2:.2f} MB"
            }

        return info
