"""Forecast accuracy metrics — the numbers behind the Model Registry.

Provides the full set of evaluation metrics the platform tracks:
MAE, RMSE, MAPE, WAPE, bias — computed per product/store/category/horizon.
"""

import numpy as np
import pandas as pd


def _safe_arrays(y_true, y_pred):
    """Return aligned float arrays, dropping rows where actual is missing."""
    y_true = np.asarray(y_true, dtype=float).ravel()
    y_pred = np.asarray(y_pred, dtype=float).ravel()
    mask = ~(np.isnan(y_true) | np.isnan(y_pred))
    return y_true[mask], y_pred[mask]


def mae(y_true, y_pred) -> float:
    y_true, y_pred = _safe_arrays(y_true, y_pred)
    if len(y_true) == 0:
        return float("nan")
    return float(np.mean(np.abs(y_true - y_pred)))


def rmse(y_true, y_pred) -> float:
    y_true, y_pred = _safe_arrays(y_true, y_pred)
    if len(y_true) == 0:
        return float("nan")
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def mape(y_true, y_pred) -> float:
    """Mean Absolute Percentage Error (%) — undefined where actual = 0."""
    y_true, y_pred = _safe_arrays(y_true, y_pred)
    if len(y_true) == 0:
        return float("nan")
    mask = y_true != 0
    if mask.sum() == 0:
        return float("nan")
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def wape(y_true, y_pred) -> float:
    """Weighted Absolute Percentage Error (%) — scale-free, robust to zeros."""
    y_true, y_pred = _safe_arrays(y_true, y_pred)
    denom = np.sum(np.abs(y_true))
    if denom == 0:
        return float("nan")
    return float(np.sum(np.abs(y_true - y_pred)) / denom * 100)


def bias(y_true, y_pred) -> float:
    """Bias: mean signed error. Negative = underforecasting, positive = overforecasting.

    Returns both the raw signed error and the percentage-of-mean version.
    """
    y_true, y_pred = _safe_arrays(y_true, y_pred)
    if len(y_true) == 0:
        return float("nan")
    signed = float(np.mean(y_pred - y_true))
    pct = (signed / np.mean(y_true) * 100) if np.mean(y_true) != 0 else float("nan")
    return signed


def bias_percent(y_true, y_pred) -> float:
    y_true, y_pred = _safe_arrays(y_true, y_pred)
    if len(y_true) == 0:
        return float("nan")
    mean_actual = float(np.mean(y_true))
    if mean_actual == 0:
        return float("nan")
    return float((np.mean(y_pred - y_true)) / mean_actual * 100)


def full_metrics(y_true, y_pred) -> dict:
    """Return the full metric set as a dict."""
    return {
        "mae": mae(y_true, y_pred),
        "rmse": rmse(y_true, y_pred),
        "mape": mape(y_true, y_pred),
        "wape": wape(y_true, y_pred),
        "bias": bias(y_true, y_pred),
        "bias_percent": bias_percent(y_true, y_pred),
    }


def evaluate_forecast_df(forecast_df: pd.DataFrame, actual_df: pd.DataFrame,
                         date_col: str = "date", actual_col: str = "sales",
                         pred_col: str = "predicted_sales",
                         grain: list[str] | None = None) -> pd.DataFrame:
    """Evaluate a forecast DataFrame against actuals.

    Parameters
    ----------
    forecast_df : pd.DataFrame — rows of (date, [grain cols...], predicted_sales)
    actual_df   : pd.DataFrame — rows of (date, [grain cols...], sales)
    grain       : optional list of columns to group by (e.g. ['item_id', 'store_id'])
                  When None, evaluates the overall totals.

    Returns a DataFrame with one row per grain combination (or a single row
    when grain is None) containing the full metric set.
    """
    if forecast_df.empty or actual_df.empty:
        return pd.DataFrame()

    merged = forecast_df.merge(
        actual_df[[date_col] + (grain or []) + [actual_col]].drop_duplicates(
            subset=[date_col] + (grain or [])
        ),
        on=[date_col] + (grain or []),
        how="inner",
    )
    if merged.empty:
        return pd.DataFrame()

    if grain:
        groups = merged.groupby(grain, dropna=False)
    else:
        # Single group over everything
        merged = merged.copy()
        merged["_all"] = "_all"
        groups = merged.groupby("_all", dropna=False)

    rows = []
    for keys, group in groups:
        m = full_metrics(group[actual_col].values, group[pred_col].values)
        row = {"points": len(group)}
        if grain:
            row.update(dict(zip(grain, keys)))
        row.update(m)
        rows.append(row)

    return pd.DataFrame(rows)


