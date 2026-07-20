import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.forecasting import DemandForecaster
from src.explainability import ModelExplainer
from src.utils import load_dataframe, load_css
from src.report_generator import ReportGenerator

st.set_page_config(page_title="Model Insights — RetailIQ", layout="wide")

load_css()

st.markdown("""
<div class="page-header">
    <h1>🧠 Model Insights & Explainability</h1>
    <p>Understand how your forecasting model works — feature importance, SHAP analysis, and model comparison.</p>
</div>
""", unsafe_allow_html=True)

model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models', 'best_model.joblib')

if not os.path.exists(model_path):
    st.error("❌ Model not found — please train a model first using the **Train Model** tab on the Dashboard.")
    st.info("Go to **Dashboard → Train Model** to train the forecasting model.")
    st.stop()

# Load model and data
@st.cache_resource
def load_model():
    forecaster = DemandForecaster()
    forecaster.load_model(model_path)
    return forecaster

@st.cache_data
def load_insights_data():
    data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'processed', 'engineered_features.csv')
    try:
        df = load_dataframe(data_path)
        df['date'] = pd.to_datetime(df['date'])
        return df
    except Exception:
        return None

with st.spinner("Loading model..."):
    forecaster = load_model()
    df = load_insights_data()

if df is None:
    st.warning("Processed data not found — please upload and process data first.")
    st.stop()

st.success(f"✅ Model loaded: **{forecaster.model_type.replace('_', ' ').title()}**")

# ── Model Info ──────────────────────────────────────────────────────────────
st.markdown('<div class="content-section">', unsafe_allow_html=True)
st.markdown('<div class="content-section-title">📋 Model Information</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"""<div class="kpi-card kpi-card-blue"><div class="kpi-card-label">Model Type</div><div class="kpi-card-value">{forecaster.model_type.replace('_', ' ').title()}</div></div>""", unsafe_allow_html=True)

with col2:
    st.markdown(f"""<div class="kpi-card kpi-card-green"><div class="kpi-card-label">Features</div><div class="kpi-card-value">{len(forecaster.feature_names)}</div></div>""", unsafe_allow_html=True)

with col3:
    if hasattr(forecaster.model, 'n_estimators'):
        st.markdown(f"""<div class="kpi-card kpi-card-purple"><div class="kpi-card-label">Estimators</div><div class="kpi-card-value">{forecaster.model.n_estimators}</div></div>""", unsafe_allow_html=True)
    elif hasattr(forecaster.model, 'n_boost_round'):
        st.markdown(f"""<div class="kpi-card kpi-card-purple"><div class="kpi-card-label">Boosting Rounds</div><div class="kpi-card-value">{forecaster.model.n_boost_round}</div></div>""", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ── Model Comparison ────────────────────────────────────────────────────────
st.markdown('<div class="content-section">', unsafe_allow_html=True)
st.markdown('<div class="content-section-title">⚖️ Model Comparison</div>', unsafe_allow_html=True)

comparison_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'reports', 'exports', 'model_comparison.csv')
if os.path.exists(comparison_path):
    comparison_df = pd.read_csv(comparison_path)

    best_idx = comparison_df.dropna(subset=['MAE'])['MAE'].idxmin()
    best_model_name = comparison_df.loc[best_idx, 'model']

    styled = comparison_df.style.apply(
        lambda row: [
            'background-color: #d4edda; font-weight: bold;' if row.name == best_idx and col in ['MAE', 'RMSE', 'MAPE']
            else 'background-color: #e8f4e8' if row.name == best_idx
            else ''
            for col in comparison_df.columns
        ],
        axis=1
    ).format({
        'MAE': '{:.4f}', 'RMSE': '{:.4f}', 'R2': '{:.4f}',
        'MAPE': '{:.2f}%', 'training_time_sec': '{:.2f}s'
    })

    st.markdown(f'<div style="font-weight: 600; color: var(--primary); margin-bottom: 0.5rem;">Side-by-Side Model Performance</div>', unsafe_allow_html=True)
    st.dataframe(styled, use_container_width=True)
    st.success(f"🏆 **Best model**: {best_model_name.replace('_', ' ').title()} (lowest MAE)")

    fig, axes = plt.subplots(1, 4, figsize=(18, 5))

    colors = ['#2C5282', '#E53E3E', '#38A169', '#D69E2E', '#805AD5']
    for i, metric in enumerate(['MAE', 'RMSE', 'MAPE', 'R2']):
        subset = comparison_df.dropna(subset=[metric])
        bars = axes[i].bar(subset['model'], subset[metric], color=colors[:len(subset)])
        best_m = subset.loc[subset[metric].idxmax(), 'model'] if metric == 'R2' else subset.loc[subset[metric].idxmin(), 'model']
        for j, model_name in enumerate(subset['model']):
            if model_name == best_m:
                bars[j].set_color('#2C5282')
                bars[j].set_alpha(1.0)
            else:
                bars[j].set_alpha(0.5)
        axes[i].set_title(f'{metric} {"(higher is better)" if metric == "R2" else "(lower is better)"}')
        axes[i].tick_params(axis='x', rotation=45)

    plt.tight_layout()
    st.pyplot(fig)

    csv_compare = comparison_df.to_csv(index=False)
    st.download_button(
        label="📥 Download Model Comparison CSV",
        data=csv_compare,
        file_name="model_comparison.csv",
        mime="text/csv"
    )

else:
    st.info("Model comparison data not found — train models on the Dashboard to generate it.")

st.markdown('</div>', unsafe_allow_html=True)

# ── Feature Importance ─────────────────────────────────────────────────────
st.markdown('<div class="content-section">', unsafe_allow_html=True)
st.markdown('<div class="content-section-title">⭐ Feature Importance</div>', unsafe_allow_html=True)

importance_df = forecaster.get_feature_importance(top_n=20)

if importance_df is not None:
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown('<div style="font-weight: 600; color: var(--primary); margin-bottom: 0.5rem;">Top 20 Features</div>', unsafe_allow_html=True)
        st.dataframe(importance_df, use_container_width=True)

    with col2:
        st.markdown('<div style="font-weight: 600; color: var(--primary); margin-bottom: 0.5rem;">Visualization</div>', unsafe_allow_html=True)
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.barh(importance_df['feature'], importance_df['importance'], color='#2C5282')
        ax.set_xlabel('Importance')
        ax.set_title('Feature Importance')
        ax.invert_yaxis()
        plt.tight_layout()
        st.pyplot(fig)

st.markdown('</div>', unsafe_allow_html=True)

# ── SHAP Analysis ──────────────────────────────────────────────────────────
st.markdown('<div class="content-section">', unsafe_allow_html=True)
st.markdown('<div class="content-section-title">🔬 SHAP Analysis</div>', unsafe_allow_html=True)

st.markdown("""
SHAP (SHapley Additive exPlanations) values explain how each feature contributes to individual predictions.
Positive SHAP values increase the prediction; negative values decrease it.
""")

sample_size = st.slider("Sample Size for SHAP", min_value=100, max_value=1000, value=500, step=100)

if st.button("🔬 Generate SHAP Analysis", type="primary"):
    with st.spinner(f"Calculating SHAP values for {sample_size} samples... (this may take a few minutes)"):
        try:
            df_sample = df.sample(n=min(sample_size, len(df)), random_state=42)
            X_sample, y_sample = forecaster.prepare_features(df_sample, target_col='sales')

            explainer = ModelExplainer(forecaster.model, forecaster.feature_names)
            explainer.create_explainer(X_sample[:100], explainer_type='tree')

            shap_values = explainer.calculate_shap_values(X_sample)

            st.success("✅ SHAP values calculated!")

            st.markdown('<div style="font-weight: 600; color: var(--primary); margin: 0.75rem 0 0.5rem;">Most Important Features (by SHAP)</div>', unsafe_allow_html=True)

            top_features = explainer.get_top_features(X_sample, top_n=15)
            st.dataframe(top_features, use_container_width=True)

            st.markdown('<div style="font-weight: 600; color: var(--primary); margin: 0.75rem 0 0.5rem;">SHAP Summary Plot</div>', unsafe_allow_html=True)
            st.info("This plot shows feature impact distribution — red = high feature value, blue = low feature value")

            plt.close("all")
            explainer.plot_summary(X_sample, max_display=15)
            fig = plt.gcf()
            fig.set_size_inches(10, 8)
            st.pyplot(fig)

            st.session_state['explainer'] = explainer
            st.session_state['X_sample'] = X_sample
            st.session_state['y_sample'] = y_sample

        except Exception as e:
            st.error(f"Error calculating SHAP values: {str(e)}")

st.markdown('</div>', unsafe_allow_html=True)

# ── Explain Individual Prediction ──────────────────────────────────────────
if 'explainer' in st.session_state:
    st.markdown('<div class="content-section">', unsafe_allow_html=True)
    st.markdown('<div class="content-section-title">🔍 Explain Individual Prediction</div>', unsafe_allow_html=True)

    X_sample = st.session_state['X_sample']
    y_sample = st.session_state['y_sample']
    explainer = st.session_state['explainer']

    instance_idx = st.number_input(
        "Select Instance Index",
        min_value=0,
        max_value=len(X_sample)-1,
        value=0,
        step=1
    )

    if st.button("Explain This Prediction"):
        with st.spinner("Generating explanation..."):
            try:
                explanation = explainer.explain_prediction(X_sample, instance_idx)

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown(f"""<div class="kpi-card kpi-card-blue"><div class="kpi-card-label">Prediction</div><div class="kpi-card-value">{explanation['prediction']:.2f}</div></div>""", unsafe_allow_html=True)

                with col2:
                    st.markdown(f"""<div class="kpi-card kpi-card-green"><div class="kpi-card-label">Base Value</div><div class="kpi-card-value">{explanation['base_value']:.2f}</div></div>""", unsafe_allow_html=True)

                st.markdown('<div style="font-weight: 600; color: var(--primary); margin: 0.75rem 0 0.5rem;">Top 10 Contributing Features</div>', unsafe_allow_html=True)

                contrib_data = []
                for i, (feature, info) in enumerate(list(explanation['shap_values'].items())[:10], 1):
                    contrib_data.append({
                        'Rank': i,
                        'Feature': feature,
                        'Value': f"{info['value']:.2f}",
                        'SHAP Impact': f"{info['shap_value']:+.2f}"
                    })

                st.dataframe(pd.DataFrame(contrib_data), use_container_width=True)

                st.markdown('<div style="font-weight: 600; color: var(--primary); margin: 0.75rem 0 0.5rem;">Waterfall Plot</div>', unsafe_allow_html=True)
                st.info("Shows how each feature contributes from base value to final prediction")

                plt.close("all")
                explainer.plot_waterfall(X_sample, instance_index=instance_idx)
                fig = plt.gcf()
                fig.set_size_inches(10, 8)
                st.pyplot(fig)

            except Exception as e:
                st.error(f"Error generating explanation: {str(e)}")

    st.markdown('</div>', unsafe_allow_html=True)

# ── Model Performance Insights ─────────────────────────────────────────────
st.markdown("""
<div class="content-section">
    <div class="content-section-title">💡 Model Performance Insights</div>

### Key Takeaways

1. **Lag Features** — Previous sales values are highly predictive of future demand
2. **Rolling Statistics** — Moving averages and standard deviations capture trends and seasonality
3. **Price Dynamics** — Price changes and momentum affect consumer demand
4. **Calendar Effects** — Events, holidays, and SNAP programs measurably impact sales

### How to Use These Insights

| Area | Action |
|---|---|
| **Feature Engineering** | Focus on features with high importance scores |
| **Business Decisions** | Understand what truly drives demand for your products |
| **Model Trust** | SHAP values make predictions transparent and explainable |
| **Debugging** | Identify when the model behaves unexpectedly and investigate why |
</div>
""", unsafe_allow_html=True)
