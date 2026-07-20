"""SHAP-based model explainability — handles multiple output shapes robustly."""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

try:
    import shap
    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False
    shap = None


# ── Helper: normalize SHAP values to (n_samples, n_features) ────────────────

def _normalize_shap_values(shap_values, X):
    """Convert any valid SHAP output to a 2D array (n_samples, n_features).

    SHAP can return:
      - 2D (n_samples, n_features)        ← standard regression case
      - list of 2D arrays (multi-output)   ← take class-1 values
      - 3D (n_samples, n_features, n_outputs)  ← squeeze output dim
      - Explanation object
    """
    if isinstance(shap_values, shap.Explanation):
        shap_values = shap_values.values

    if isinstance(shap_values, (list, tuple)):
        # Multi-output / multi-class: take the first (or only meaningful) output
        # For binary classifiers, index 1 = positive class
        if len(shap_values) > 1:
            shap_values = shap_values[1] if shap_values[1].shape[-1] == X.shape[1] else shap_values[0]
        else:
            shap_values = shap_values[0]

    # Handle wrapped arrays (pandas Series/DataFrame, matrix wrappers)
    if hasattr(shap_values, 'toarray'):
        shap_values = shap_values.toarray()

    # Now it should be a numpy array — ensure 2D
    shap_values = np.asarray(shap_values)

    if shap_values.ndim == 1:
        # (n_features,) → (1, n_features)
        shap_values = shap_values.reshape(1, -1)
    elif shap_values.ndim == 3:
        # (n_samples, n_features, n_outputs) → squeeze last dim or take mean
        if shap_values.shape[2] == 1:
            shap_values = shap_values[:, :, 0]
        else:
            # Multi-dimensional output: average across output dim
            shap_values = shap_values.mean(axis=2)
    elif shap_values.ndim > 3:
        raise ValueError(f"Unexpected SHAP values shape: {shap_values.shape}")

    return shap_values


def _normalize_expected_value(expected_value):
    """Convert SHAP expected_value to a Python float.

    Can be: float, 0-d array, 1-d array, or a list (multi-output).
    """
    if isinstance(expected_value, (list, tuple)):
        # Multi-output: take the first or the one for the positive class
        ev = expected_value[1] if len(expected_value) > 1 else expected_value[0]
        return _normalize_expected_value(ev)

    if isinstance(expected_value, np.ndarray):
        if expected_value.ndim == 0:
            return float(expected_value)
        elif expected_value.ndim == 1:
            return float(expected_value[0])
        elif expected_value.ndim == 2:
            return float(expected_value[0, 0])
        else:
            return float(expected_value.ravel()[0])

    return float(expected_value)


def _squeeze_scalar(val):
    """Convert any numeric value to a Python float, handling arrays."""
    if isinstance(val, (list, tuple)):
        val = np.asarray(val)
    if isinstance(val, np.ndarray):
        if val.ndim == 0:
            return float(val)
        # Multi-element array — take first element or mean
        return float(val.ravel()[0])
    return float(val)


# ── Helper: build shap Explanation safely ───────────────────────────────────

def _build_explanation_for_waterfall(shap_values_row, expected_value, data_row, feature_names):
    """Build a shap.Explanation object handling shape mismatches."""
    shap_values_row = np.asarray(shap_values_row).ravel()
    data_row = np.asarray(data_row).ravel()

    # If lengths don't match, trim or pad
    n_features = len(feature_names)
    if len(shap_values_row) > n_features:
        shap_values_row = shap_values_row[:n_features]
    elif len(shap_values_row) < n_features:
        shap_values_row = np.pad(shap_values_row, (0, n_features - len(shap_values_row)))

    if len(data_row) > n_features:
        data_row = data_row[:n_features]
    elif len(data_row) < n_features:
        data_row = np.pad(data_row, (0, n_features - len(data_row)))

    return shap.Explanation(
        values=shap_values_row,
        base_values=expected_value,
        data=data_row,
        feature_names=feature_names,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ModelExplainer class
# ═══════════════════════════════════════════════════════════════════════════════

class ModelExplainer:
    def __init__(self, model, feature_names):
        self.model = model
        self.feature_names = feature_names
        self.explainer = None
        self.shap_values = None  # Will always be stored as (n_samples, n_features)
        self._raw_expected_value = None

    def create_explainer(self, X_sample, explainer_type='tree'):
        """Create SHAP explainer"""
        if explainer_type == 'tree':
            self.explainer = shap.TreeExplainer(self.model)
        elif explainer_type == 'kernel':
            self.explainer = shap.KernelExplainer(self.model.predict, X_sample)
        else:
            raise ValueError(f"Unknown explainer type: {explainer_type}")
        return self.explainer

    def calculate_shap_values(self, X):
        """Calculate SHAP values for given data.

        Normalizes the output to always be (n_samples, n_features) internally.
        """
        if self.explainer is None:
            self.create_explainer(X[:100])

        raw = self.explainer.shap_values(X)

        # Store expected_value before normalization
        self._raw_expected_value = getattr(self.explainer, 'expected_value', 0)

        # Normalize to 2D
        self.shap_values = _normalize_shap_values(raw, X)

        return self.shap_values

    # ── Plotting ──────────────────────────────────────────────────────────

    def plot_summary(self, X, max_display=20, save_path=None):
        """Create SHAP summary plot"""
        if self.shap_values is None:
            self.calculate_shap_values(X)

        # shap_values may have been normalized to 2D; ensure X matches
        X_use = X.iloc[:self.shap_values.shape[0]] if len(X) > self.shap_values.shape[0] else X
        shap.summary_plot(self.shap_values, X_use, feature_names=self.feature_names,
                         max_display=max_display, show=False)
        if save_path:
            plt.savefig(save_path, bbox_inches='tight', dpi=300)
            plt.close()

    def plot_feature_importance(self, X, max_display=20, save_path=None):
        """Plot feature importance using SHAP values"""
        if self.shap_values is None:
            self.calculate_shap_values(X)

        X_use = X.iloc[:self.shap_values.shape[0]] if len(X) > self.shap_values.shape[0] else X
        shap.summary_plot(self.shap_values, X_use, feature_names=self.feature_names,
                         plot_type='bar', max_display=max_display, show=False)
        if save_path:
            plt.savefig(save_path, bbox_inches='tight', dpi=300)
            plt.close()

    # ── Explain prediction ──────────────────────────────────────────────

    def explain_prediction(self, X_instance, instance_index=0):
        """Explain a single prediction.

        Handles all SHAP output shapes (2D, 3D, list-of-arrays, etc.)
        """
        if self.shap_values is None:
            self.calculate_shap_values(X_instance)

        n_samples = self.shap_values.shape[0]

        # Clamp instance_index
        idx = min(instance_index, n_samples - 1)

        # Prediction — handle arrays vs scalars
        try:
            pred_raw = self.model.predict(X_instance)
            if isinstance(pred_raw, np.ndarray) and pred_raw.ndim > 1:
                pred_raw = pred_raw.ravel()
            pred = _squeeze_scalar(pred_raw[idx] if hasattr(pred_raw, '__getitem__') else pred_raw)
        except Exception:
            pred = 0.0

        # Base value
        ev = _normalize_expected_value(self._raw_expected_value)

        # Feature contributions
        shap_vals = {}
        for i, feature in enumerate(self.feature_names):
            if idx < self.shap_values.shape[0] and i < self.shap_values.shape[1]:
                raw_sv = self.shap_values[idx, i]
            else:
                raw_sv = 0.0
            sv = _squeeze_scalar(raw_sv)

            # Feature value
            try:
                raw_val = X_instance.iloc[idx, i] if hasattr(X_instance, 'iloc') else X_instance[idx, i]
            except Exception:
                raw_val = 0.0
            val = _squeeze_scalar(raw_val)

            shap_vals[feature] = {'value': val, 'shap_value': sv}

        # Sort by absolute SHAP value
        shap_vals = dict(
            sorted(shap_vals.items(), key=lambda x: abs(x[1]['shap_value']), reverse=True)
        )

        return {
            'prediction': pred,
            'base_value': ev,
            'shap_values': shap_vals,
        }

    # ── Waterfall plot ──────────────────────────────────────────────────

    def plot_waterfall(self, X_instance, instance_index=0, save_path=None):
        """Create waterfall plot for a single prediction.

        Handles shape mismatches between SHAP values and the data.
        """
        if self.shap_values is None:
            self.calculate_shap_values(X_instance)

        n_samples = self.shap_values.shape[0]
        idx = min(instance_index, n_samples - 1)

        # Get the row of SHAP values
        sv_row = self.shap_values[idx]

        # Get the data row
        try:
            data_row = X_instance.iloc[idx].values if hasattr(X_instance, 'iloc') else X_instance[idx]
        except Exception:
            data_row = np.zeros(len(self.feature_names))

        ev = _normalize_expected_value(self._raw_expected_value)

        # Build Explanation safely
        explanation = _build_explanation_for_waterfall(
            sv_row, ev, data_row, self.feature_names
        )

        plt.close('all')
        shap.waterfall_plot(explanation, show=False)

        if save_path:
            plt.savefig(save_path, bbox_inches='tight', dpi=300)
            plt.close()

    # ── Force plot ──────────────────────────────────────────────────────

    def plot_force(self, X_instance, instance_index=0, save_path=None):
        """Create force plot for single prediction"""
        if self.shap_values is None:
            self.calculate_shap_values(X_instance)

        n_samples = self.shap_values.shape[0]
        idx = min(instance_index, n_samples - 1)

        ev = _normalize_expected_value(self._raw_expected_value)

        plt.close('all')
        shap.force_plot(
            ev,
            self.shap_values[idx],
            X_instance.iloc[idx] if hasattr(X_instance, 'iloc') else X_instance[idx],
            feature_names=self.feature_names,
            matplotlib=True,
            show=False,
        )

        if save_path:
            plt.savefig(save_path, bbox_inches='tight', dpi=300)
            plt.close()

    # ── Feature importance ─────────────────────────────────────────────

    def get_top_features(self, X, top_n=10):
        """Get top N most important features by mean absolute SHAP value."""
        if self.shap_values is None:
            self.calculate_shap_values(X)

        mean_abs_shap = np.abs(self.shap_values).mean(axis=0)
        # Handle shape mismatch — if longer than feature_names, trim
        if len(mean_abs_shap) > len(self.feature_names):
            mean_abs_shap = mean_abs_shap[:len(self.feature_names)]

        feature_importance = pd.DataFrame({
            'feature': self.feature_names[:len(mean_abs_shap)],
            'importance': mean_abs_shap,
        }).sort_values('importance', ascending=False).head(top_n)

        return feature_importance

    def analyze_feature_interactions(self, X, feature1, feature2):
        """Analyze interaction between two features"""
        if self.shap_values is None:
            self.calculate_shap_values(X)

        try:
            f1_idx = self.feature_names.index(feature1)
        except ValueError:
            raise ValueError(f"Feature '{feature1}' not found in feature names")
        try:
            f2_idx = self.feature_names.index(feature2)
        except ValueError:
            raise ValueError(f"Feature '{feature2}' not found in feature names")

        shap.dependence_plot(
            f1_idx,
            self.shap_values,
            X,
            feature_names=self.feature_names,
            interaction_index=f2_idx,
        )
