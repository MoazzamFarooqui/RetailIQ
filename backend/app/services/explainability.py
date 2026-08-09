"""SHAP-based model explainability — handles multiple output shapes robustly."""

import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)

try:
    import shap
    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False
    shap = None


def _normalize_shap_values(shap_values, X):
    """Convert any valid SHAP output to 2D (n_samples, n_features)."""
    if isinstance(shap_values, shap.Explanation):
        shap_values = shap_values.values
    if isinstance(shap_values, (list, tuple)):
        shap_values = shap_values[1] if len(shap_values) > 1 and shap_values[1].shape[-1] == X.shape[1] else shap_values[0]
    if hasattr(shap_values, "toarray"):
        shap_values = shap_values.toarray()
    shap_values = np.asarray(shap_values)
    if shap_values.ndim == 1:
        shap_values = shap_values.reshape(1, -1)
    elif shap_values.ndim == 3:
        shap_values = shap_values[:, :, 0] if shap_values.shape[2] == 1 else shap_values.mean(axis=2)
    elif shap_values.ndim > 3:
        raise ValueError(f"Unexpected SHAP values shape: {shap_values.shape}")
    return shap_values


def _normalize_expected_value(expected_value):
    """Convert SHAP expected_value to a Python float."""
    if isinstance(expected_value, (list, tuple)):
        ev = expected_value[1] if len(expected_value) > 1 else expected_value[0]
        return _normalize_expected_value(ev)
    if isinstance(expected_value, np.ndarray):
        return float(expected_value.ravel()[0])
    return float(expected_value)


class ModelExplainer:
    """SHAP-based model explainer for tree-based demand forecasting models."""

    def __init__(self, model, feature_names):
        self.model = model
        self.feature_names = feature_names
        self.explainer = None
        self.shap_values = None
        self._raw_expected_value = None
        logger.debug("ModelExplainer initialized")

    def create_explainer(self, X_sample, explainer_type="tree"):
        if explainer_type == "tree":
            self.explainer = shap.TreeExplainer(self.model)
        elif explainer_type == "kernel":
            self.explainer = shap.KernelExplainer(self.model.predict, X_sample)
        else:
            raise ValueError(f"Unknown explainer type: {explainer_type}")
        return self.explainer

    def calculate_shap_values(self, X):
        if self.explainer is None:
            self.create_explainer(X[:100])
        raw = self.explainer.shap_values(X)
        self._raw_expected_value = getattr(self.explainer, "expected_value", 0)
        self.shap_values = _normalize_shap_values(raw, X)
        return self.shap_values

    def get_top_features(self, X, top_n=10):
        """Get top N most important features by mean absolute SHAP value."""
        if self.shap_values is None:
            self.calculate_shap_values(X)
        mean_abs_shap = np.abs(self.shap_values).mean(axis=0)
        if len(mean_abs_shap) > len(self.feature_names):
            mean_abs_shap = mean_abs_shap[:len(self.feature_names)]
        return pd.DataFrame({
            "feature": self.feature_names[:len(mean_abs_shap)],
            "importance": mean_abs_shap,
        }).sort_values("importance", ascending=False).head(top_n)

    def explain_prediction(self, X_instance, instance_index=0):
        """Explain a single prediction."""
        if self.shap_values is None:
            self.calculate_shap_values(X_instance)
        n_samples = self.shap_values.shape[0]
        idx = min(instance_index, n_samples - 1)
        try:
            pred_raw = self.model.predict(X_instance)
            pred = float(pred_raw.ravel()[idx] if hasattr(pred_raw, "ravel") else pred_raw)
        except Exception:
            pred = 0.0
        ev = _normalize_expected_value(self._raw_expected_value)
        shap_vals = {}
        for i, feature in enumerate(self.feature_names):
            if idx < self.shap_values.shape[0] and i < self.shap_values.shape[1]:
                sv = float(self.shap_values[idx, i])
            else:
                sv = 0.0
            try:
                val = float(X_instance.iloc[idx, i]) if hasattr(X_instance, "iloc") else float(X_instance[idx, i])
            except Exception:
                val = 0.0
            shap_vals[feature] = {"value": val, "shap_value": sv}
        shap_vals = dict(sorted(shap_vals.items(), key=lambda x: abs(x[1]["shap_value"]), reverse=True))
        return {"prediction": pred, "base_value": ev, "shap_values": shap_vals}


