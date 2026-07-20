import pandas as pd
import numpy as np
import os
from pathlib import Path
import joblib

def ensure_dir(directory):
    """Create directory if it doesn't exist"""
    Path(directory).mkdir(parents=True, exist_ok=True)

def save_dataframe(df, filepath, index=False):
    """Save dataframe to CSV"""
    ensure_dir(os.path.dirname(filepath))
    df.to_csv(filepath, index=index)
    print(f"Saved dataframe to {filepath}")

def load_dataframe(filepath):
    """Load dataframe from CSV"""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    return pd.read_csv(filepath)

def save_model(model, filepath):
    """Save model using joblib"""
    ensure_dir(os.path.dirname(filepath))
    joblib.dump(model, filepath)
    print(f"Saved model to {filepath}")

def load_model(filepath):
    """Load model using joblib"""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Model file not found: {filepath}")
    return joblib.load(filepath)

def calculate_mape(y_true, y_pred):
    """Calculate Mean Absolute Percentage Error"""
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    mask = y_true != 0
    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100

def calculate_wmape(y_true, y_pred):
    """Calculate Weighted Mean Absolute Percentage Error"""
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    return np.sum(np.abs(y_true - y_pred)) / np.sum(np.abs(y_true)) * 100

def create_date_features(df, date_col='date'):
    """Create common date features"""
    df = df.copy()
    df['year'] = df[date_col].dt.year
    df['month'] = df[date_col].dt.month
    df['day'] = df[date_col].dt.day
    df['dayofweek'] = df[date_col].dt.dayofweek
    df['is_weekend'] = (df['dayofweek'] >= 5).astype(int)
    df['quarter'] = df[date_col].dt.quarter
    return df

def reduce_memory_usage(df):
    """Reduce memory usage of dataframe"""
    start_mem = df.memory_usage().sum() / 1024**2
    print(f'Memory usage before optimization: {start_mem:.2f} MB')

    for col in df.columns:
        col_type = df[col].dtype

        if col_type != object and not pd.api.types.is_datetime64_any_dtype(df[col]):
            try:
                c_min = df[col].min()
                c_max = df[col].max()

                if str(col_type)[:3] == 'int':
                    if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max:
                        df[col] = df[col].astype(np.int8)
                    elif c_min > np.iinfo(np.int16).min and c_max < np.iinfo(np.int16).max:
                        df[col] = df[col].astype(np.int16)
                    elif c_min > np.iinfo(np.int32).min and c_max < np.iinfo(np.int32).max:
                        df[col] = df[col].astype(np.int32)
                else:
                    if c_min > np.finfo(np.float16).min and c_max < np.finfo(np.float16).max:
                        df[col] = df[col].astype(np.float16)
                    elif c_min > np.finfo(np.float32).min and c_max < np.finfo(np.float32).max:
                        df[col] = df[col].astype(np.float32)
            except TypeError:
                pass  # skip columns that can't be compared (e.g. datetime)

    end_mem = df.memory_usage().sum() / 1024**2
    print(f'Memory usage after optimization: {end_mem:.2f} MB')
    print(f'Decreased by {100 * (start_mem - end_mem) / start_mem:.1f}%')

    return df

def get_date_range_info(df, date_col='date'):
    """Get information about date range in dataframe"""
    min_date = df[date_col].min()
    max_date = df[date_col].max()
    n_days = (max_date - min_date).days + 1

    return {
        'min_date': min_date,
        'max_date': max_date,
        'n_days': n_days,
        'date_range': f'{min_date} to {max_date}'
    }

def split_train_test_by_date(df, date_col='date', test_days=28):
    """Split dataframe into train and test sets by date"""
    max_date = df[date_col].max()
    split_date = max_date - pd.Timedelta(days=test_days)

    train = df[df[date_col] <= split_date].copy()
    test = df[df[date_col] > split_date].copy()

    print(f"Train set: {len(train)} rows, dates from {train[date_col].min()} to {train[date_col].max()}")
    print(f"Test set: {len(test)} rows, dates from {test[date_col].min()} to {test[date_col].max()}")

    return train, test

def load_css():
    """Load the shared custom CSS for consistent theming across all pages."""
    import streamlit as st
    css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'custom.css')
    if os.path.exists(css_path):
        with open(css_path) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)


def render_sidebar():
    """Render the premium dark sidebar with navigation links."""
    import streamlit as st
    from datetime import datetime
    with st.sidebar:
        st.markdown(f'''
        <div class="sidebar-brand">
            <div class="sidebar-brand-monogram">R</div>
            <div class="sidebar-brand-text">
                <div class="sidebar-brand-name">RetailIQ</div>
                <div class="sidebar-brand-tagline">Intelligence Platform</div>
            </div>
        </div>
        ''', unsafe_allow_html=True)

        st.markdown(f'''
        <div class="sidebar-profile">
            <div class="sidebar-profile-avatar">AD</div>
            <div class="sidebar-profile-info">
                <div class="sidebar-profile-name">Admin User</div>
                <div class="sidebar-profile-role">Retail Analyst</div>
            </div>
            <div class="sidebar-status-dot"></div>
        </div>
        ''', unsafe_allow_html=True)

        st.markdown('<div class="sidebar-nav-section">Core Analytics</div>', unsafe_allow_html=True)
        st.page_link("app.py", label="Dashboard")
        st.page_link("pages/Analytics.py", label="Analytics")
        st.page_link("pages/Forecast.py", label="Forecast")

        st.markdown('<div class="sidebar-nav-section">Operations</div>', unsafe_allow_html=True)
        st.page_link("pages/Inventory.py", label="Inventory")
        st.page_link("pages/Model_Insights.py", label="Model Insights")
        st.page_link("pages/AI_Insights.py", label="AI Insights")

        st.markdown('<div class="sidebar-nav-divider"></div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-spacer"></div>', unsafe_allow_html=True)
        st.markdown(f'''
        <div class="sidebar-system-bar">
            <div class="sidebar-system-info">
                <div class="sidebar-system-dot"></div>
                <span>All systems operational</span>
            </div>
            <div class="sidebar-system-version">v2.0 · {datetime.now().strftime("%Y")}</div>
        </div>
        ''', unsafe_allow_html=True)


def format_large_number(num):
    """Format large numbers with K, M, B suffixes"""
    if num >= 1_000_000_000:
        return f'{num/1_000_000_000:.2f}B'
    elif num >= 1_000_000:
        return f'{num/1_000_000:.2f}M'
    elif num >= 1_000:
        return f'{num/1_000:.2f}K'
    else:
        return f'{num:.0f}'

def get_data_summary(df):
    """Get summary statistics of dataframe"""
    summary = {
        'n_rows': len(df),
        'n_cols': len(df.columns),
        'memory_mb': df.memory_usage(deep=True).sum() / 1024**2,
        'n_duplicates': df.duplicated().sum(),
        'missing_values': df.isnull().sum().sum(),
        'numeric_cols': len(df.select_dtypes(include=[np.number]).columns),
        'categorical_cols': len(df.select_dtypes(include=['object']).columns)
    }

    return summary
