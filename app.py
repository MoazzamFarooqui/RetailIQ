import streamlit as st
import pandas as pd
import sys, os
from datetime import datetime
sys.path.append(os.path.dirname(__file__))

import matplotlib.pyplot as plt
from src.database import Database
from src.upload_service import DataValidator
from src.weather_service import WeatherService
from src.holiday_service import HolidayService

st.set_page_config(
    page_title="RetailIQ - AI-Powered Retail Intelligence & Inventory Optimization Platform",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Load CSS ────────────────────────────────────────────────────────────────
css_path = os.path.join(os.path.dirname(__file__), 'assets', 'custom.css')
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Custom CSS injection to force center alignment and full width on native page links
st.markdown("""
<style>
    div[data-testid="stPageLink"] {
        text-align: center;
        justify-content: center;
        display: flex;
        width: 100%;
    }
    div[data-testid="stPageLink"] > a {
        justify-content: center;
        text-align: center;
        width: 100%;
        max-width: 350px;
    }
</style>
""", unsafe_allow_html=True)

# ── Sidebar Navigation ───────────────────────────────────────────────────────
with st.sidebar:
    # ── Brand header with monogram ──────────────────────────────────────────
    st.markdown(f'''
    <div class="sidebar-brand">
        <div class="sidebar-brand-monogram">R</div>
        <div class="sidebar-brand-text">
            <div class="sidebar-brand-name">RetailIQ</div>
            <div class="sidebar-brand-tagline">Intelligence Platform</div>
        </div>
    </div>
    ''', unsafe_allow_html=True)

    # ── User profile card ───────────────────────────────────────────────────
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

    # ── Primary Navigation ──────────────────────────────────────────────────
    st.markdown('<div class="sidebar-nav-section">Core Analytics</div>', unsafe_allow_html=True)

    st.page_link("app.py", label="Dashboard")
    st.page_link("pages/Analytics.py", label="Analytics")
    st.page_link("pages/Forecast.py", label="Forecast")

    st.markdown('<div class="sidebar-nav-section">Operations</div>', unsafe_allow_html=True)

    st.page_link("pages/Inventory.py", label="Inventory")
    st.page_link("pages/Model_Insights.py", label="Model Insights")
    st.page_link("pages/AI_Insights.py", label="AI Insights")

    st.markdown('<div class="sidebar-nav-divider"></div>', unsafe_allow_html=True)

    # ── System Status (pushed to bottom via flex spacer) ────────────────────
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

st.title("RetailIQ – AI-Powered Retail Intelligence & Inventory Optimization Platform")

# ── Init database ────────────────────────────────────────────────────────────
db = Database()
weather = WeatherService()
holiday_svc = HolidayService()

# ── Tabs ─────────────────────────────────────────────────────────────────────
tab_home, tab_upload, tab_retrain = st.tabs(["Dashboard", "Upload Data", "Train Model"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: HOME DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
with tab_home:
    # ── Helpers ──────────────────────────────────────────────────────────────
    def get_sales_metadata(data_dir):
        sales_path = os.path.join(data_dir, 'sales_train_evaluation.csv')
        if not os.path.exists(sales_path):
            sales_path = os.path.join(data_dir, 'sales_train_validation.csv')
        if not os.path.exists(sales_path):
            return None
        id_cols = ['item_id', 'store_id', 'cat_id', 'dept_id', 'state_id']
        return pd.read_csv(sales_path, usecols=id_cols)

    def get_calendar_meta(data_dir):
        cal_path = os.path.join(data_dir, 'calendar.csv')
        if not os.path.exists(cal_path):
            return None
        cal = pd.read_csv(cal_path, usecols=['date'])
        cal['date'] = pd.to_datetime(cal['date'])
        return cal

    # ── Live Context Row ────────────────────────────────────────────────────
    st.subheader("Today's Context")

    weather_data = weather.fetch_current_weather()
    today = datetime.now()
    today_holiday = holiday_svc.get_holiday_name(today)
    pakistan_season = weather_data.get('season', weather.get_season(today))
    season_emoji = weather.get_season_emoji(pakistan_season)

    # Check for pre-holiday shopping window
    pre_holiday_info = holiday_svc.is_in_pre_holiday_window(today)

    context_cols = st.columns(5)
    context_cols[0].metric("Date", today.strftime('%b %d, %Y'))
    context_cols[1].metric("Temperature",
                         f"{weather_data.get('temperature_c', 0):.0f}°C")
    context_cols[2].metric("Conditions",
                         weather_data.get('weather_condition', 'N/A'))
    context_cols[3].metric("Holiday", today_holiday if today_holiday else "None")
    context_cols[4].metric("Season", f"{season_emoji} {pakistan_season}")

    st.divider()

    # ── Key Metrics ─────────────────────────────────────────────────────────
    st.header("Platform Overview")

    try:
        data_dir = os.path.join(os.path.dirname(__file__), 'data', 'raw')
        sales_meta = get_sales_metadata(data_dir)
        calendar_small = get_calendar_meta(data_dir)

        if sales_meta is not None and calendar_small is not None:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Products", f"{sales_meta['item_id'].nunique():,}")
            col2.metric("Stores", f"{sales_meta['store_id'].nunique()}")
            col3.metric("Categories", f"{sales_meta['cat_id'].nunique()}")
            col4.metric("States", f"{sales_meta['state_id'].nunique()}")

            st.caption(f"Date range: {calendar_small['date'].min().date()} to {calendar_small['date'].max().date()} | "
                      f"{len(sales_meta):,} time series")

            # Dataset stats
            date_range = f"{calendar_small['date'].min().date()} to {calendar_small['date'].max().date()}"
            info_data = {
                "Metric": ["Date Range", "Total Time Series", "Departments", "Total Days"],
                "Value": [
                    date_range,
                    f"{len(sales_meta):,}",
                    f"{sales_meta['dept_id'].nunique()}",
                    f"{len(calendar_small):,}"
                ]
            }
            st.table(pd.DataFrame(info_data))
        else:
            st.warning("Data files not found in data/raw/. Upload data via the Upload tab or place CSV files manually.")
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")

    # ── Recent activity ──────────────────────────────────────────────────────
    st.divider()
    st.header("Recent Activity")

    try:
        uploads = db.get_uploaded_datasets()
        model_hist = db.get_model_history()

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Recent Uploads")
            if len(uploads) > 0:
                display = uploads[['filename', 'row_count', 'status', 'uploaded_at']].head(5)
                st.dataframe(display, use_container_width=True)
            else:
                st.info("No uploads yet. Go to the Upload tab to add data.")

        with col2:
            st.subheader("Model Training History")
            if len(model_hist) > 0:
                display = model_hist[['model_type', 'mae', 'rmse', 'mape', 'trained_at']].head(5)
                st.dataframe(display, use_container_width=True)
            else:
                st.info("No models trained yet. Go to Train Model tab.")
    except Exception:
        st.info("Database ready — upload data to get started.")

    # ── Seasonal / Holiday Alert Banner ──────────────────────────────────────
    if pre_holiday_info:
        st.info(f"📢 **{pre_holiday_info['advice']}** — {pre_holiday_info['days_until_holiday']} days until {pre_holiday_info['holiday_name']}")
    elif weather_data.get('temperature_c', 25) >= 35:
        st.warning(f"☀️ **Heat Alert** — {weather_data['temperature_c']:.0f}°C today. Expect high demand for cold drinks, water, and ice cream.")
    elif weather_data.get('temperature_c', 25) <= 10:
        st.warning(f"❄️ **Cold Wave** — {weather_data['temperature_c']:.0f}°C today. Stock up on tea, coffee, and winter essentials.")

    # ── Feature cards (Centered Grid Alignment) ───────────────────────────────
    st.divider()
    st.header("Platform Capabilities")

    features = [
        ("📤", "Upload & Validate", "Upload retail sales CSVs — auto-validate, clean, and append to historical data."),
        ("🔮", "AI Forecasting", "7/30/90 day demand predictions with live weather and holiday context."),
        ("📦", "Inventory Optimization", "Safety stock, reorder points, EOQ, stockout prediction, and overstock detection."),
        ("🌤", "Live Context", "Real-time weather and holiday integration for smarter predictions."),
        ("🧠", "Explainable AI", "SHAP-based prediction explanations and feature importance analysis."),
        ("📈", "Business Intelligence", "Revenue tracking, trend analysis, category and store performance."),
        ("📄", "Export & Reports", "Download forecasts, inventory plans, and insights as CSV or PDF."),
    ]

    cols = st.columns(3)
    for i, (emoji, title, desc) in enumerate(features):
        with cols[i % 3]:
            # Added "text-align: center" along with structural flex rules to perfectly center internal components
            st.markdown(f"""
            <div style="background:var(--bg-card,#fff); border:1px solid var(--border-light,#E2E8F0);
                        border-radius:10px; padding:1.25rem; margin-bottom:1rem;
                        transition:all 0.2s ease; height:100%; text-align: center;
                        display: flex; flex-direction: column; align-items: center; justify-content: center;"
                 onmouseover="this.style.boxShadow='0 4px 12px rgba(0,0,0,0.08)';this.style.borderColor='#2C5282'"
                 onmouseout="this.style.boxShadow='none';this.style.borderColor='#E2E8F0'">
                <div style="font-size:1.8rem; margin-bottom:0.4rem;">{emoji}</div>
                <div style="font-weight:700; color:var(--primary,#1E3A5F); margin-bottom:0.3rem;">{title}</div>
                <div style="font-size:0.85rem; color:var(--text-secondary,#718096); line-height:1.5;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: UPLOAD DATA
# ═══════════════════════════════════════════════════════════════════════════════
with tab_upload:
    st.header("Upload Your Retail Sales Data")
    st.markdown("""
    Upload a CSV file with your sales data. The system will:
    1. **Auto-validate** the file format and columns
    2. **Auto-clean** missing values and fix data types
    3. **Append** to existing historical data
    4. **Update** dashboards in real-time
    """)

    st.info("**Expected columns**: date, sales (or quantity/demand), item_id, store_id. Price, category, and department columns are optional but recommended.")

    uploaded_file = st.file_uploader(
        "Choose a CSV file",
        type="csv",
        help="Select a CSV file with retail sales data"
    )

    if uploaded_file is not None:
        # Save temp file
        temp_path = os.path.join(os.path.dirname(__file__), 'data', 'temp_upload.csv')
        with open(temp_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())

        # Validate
        with st.spinner("Validating file..."):
            validation = DataValidator.validate_csv(temp_path)

        if validation['valid']:
            st.success(f"File validated! **{validation['row_count']:,}** rows, **{validation['column_count']}** columns")

            # Show validation details
            col1, col2, col3 = st.columns(3)
            col1.metric("Rows", f"{validation['row_count']:,}")
            col2.metric("Columns", validation['column_count'])
            if validation.get('date_range'):
                col3.metric("Date Range", f"{validation['date_range']['days']} days")

            if validation.get('sales_stats'):
                s = validation['sales_stats']
                st.subheader("Sales Preview")
                sc1, sc2, sc3, sc4 = st.columns(4)
                sc1.metric("Total Sales", f"{s['sum']:,.0f}")
                sc2.metric("Avg", f"{s['mean']:.2f}")
                sc3.metric("Min", f"{s['min']:.0f}")
                sc4.metric("Max", f"{s['max']:.0f}")

            if validation.get('warnings'):
                st.subheader("Warnings")
                for w in validation['warnings']:
                    st.warning(w)

            # Auto-clean
            if st.button("Auto-Clean & Upload", type="primary", use_container_width=True):
                with st.spinner("Cleaning data..."):
                    df_raw = pd.read_csv(temp_path)
                    df_clean = DataValidator.auto_clean(df_raw, validation)

                    # Save to database
                    dataset_id, table_name = db.save_uploaded_dataset(
                        filename=uploaded_file.name, df=df_raw
                    )
                    db.save_cleaned_dataset(dataset_id, df_clean)
                    db.update_upload_status(dataset_id, 'cleaned')

                    # Also save to data/processed as uploaded_data.csv for the pipeline
                    processed_dir = os.path.join(os.path.dirname(__file__), 'data', 'processed')
                    os.makedirs(processed_dir, exist_ok=True)
                    df_clean.to_csv(os.path.join(processed_dir, 'uploaded_data.csv'), index=False)

                    st.success(f"Data cleaned and stored! **{len(df_clean)}** rows ready.")
                    st.balloons()

                    # Show cleaned preview
                    st.subheader("Cleaned Data Preview")
                    st.dataframe(df_clean.head(10), use_container_width=True)

                    st.info("""
                    **Next Steps:**
                    - Go to the **Train Model** tab to retrain with the new data
                    - Visit **Forecast** to generate predictions
                    - Check **AI Insights** for automated analysis
                    """)

        else:
            st.error("File validation failed")
            for err in validation['errors']:
                st.error(err)

            st.info("""
            **Tips:**
            - Your CSV must have at least a `date` and `sales` column
            - The system recognizes common column names like `quantity`, `demand`, `product_id`, etc.
            - Date should be in a standard format (YYYY-MM-DD)
            - Sales should be numeric
            """)

        # Cleanup temp
        try:
            os.remove(temp_path)
        except OSError:
            pass

    # Show upload history
    st.divider()
    with st.expander("Upload History"):
        try:
            uploads = db.get_uploaded_datasets()
            if len(uploads) > 0:
                st.dataframe(uploads, use_container_width=True)
            else:
                st.info("No uploads yet")
        except Exception:
            st.info("Database not yet initialized")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: RETRAIN MODEL
# ═══════════════════════════════════════════════════════════════════════════════
with tab_retrain:
    st.header("Retrain Forecasting Model")
    st.markdown("""
    Train all forecasting models on the latest data. The system will:
    1. Load the latest cleaned dataset
    2. Train **5 models**: Baseline, Random Forest, XGBoost, LightGBM, Prophet
    3. **Compare** performance (MAE, RMSE, MAPE)
    4. **Select** the best model and save it
    """)

    col1, col2 = st.columns(2)

    with col1:
        sample_size = st.number_input("Training Sample Size", 1000, 500000, 50000, 10000,
                                      help="Use a sample for faster training. Set to max for full dataset.")
        test_size = st.slider("Test Split %", 0.1, 0.4, 0.2, 0.05)

    with col2:
        include_prophet = st.checkbox("Include Prophet", value=False,
                                      help="Prophet can be slow on large datasets")
        include_baseline = st.checkbox("Include Baseline", value=True)

    st.markdown("---")
    st.markdown("### Pre-Retraining Checklist")

    checks = []
    checks.append(("Data available", os.path.exists(os.path.join(os.path.dirname(__file__), 'data', 'processed', 'engineered_features.csv'))))
    checks.append(("Uploaded data available", os.path.exists(os.path.join(os.path.dirname(__file__), 'data', 'processed', 'uploaded_data.csv'))))

    for label, ok in checks:
        if ok:
            st.success(f"{label}")
        else:
            st.warning(f"{label}")

    if st.button("Start Training", type="primary", use_container_width=True):
        with st.spinner("Training models... This may take several minutes."):
            try:
                from src.forecasting import DemandForecaster

                # Load the best available data
                upload_path = os.path.join(os.path.dirname(__file__), 'data', 'processed', 'uploaded_data.csv')
                engineered_path = os.path.join(os.path.dirname(__file__), 'data', 'processed', 'engineered_features.csv')

                if os.path.exists(upload_path):
                    from src.utils import load_dataframe
                    df = load_dataframe(upload_path)
                    df['date'] = pd.to_datetime(df['date'])

                    # Run feature engineering on uploaded data
                    from src.feature_engineering import FeatureEngineer
                    engineer = FeatureEngineer()
                    df = engineer.create_all_features(df)
                    df = df.dropna()
                    st.info(f"Feature engineering complete on uploaded data: {df.shape}")
                elif os.path.exists(engineered_path):
                    from src.utils import load_dataframe
                    df = load_dataframe(engineered_path)
                    df['date'] = pd.to_datetime(df['date'])
                else:
                    st.error("No data found to train on. Upload data first.")
                    st.stop()

                # Train all models
                forecaster = DemandForecaster()

                comparison_df, best_model = forecaster.train_all_models(
                    df, target_col='sales', test_size=test_size,
                    sample_frac=min(1.0, sample_size / len(df)),
                    include_prophet=include_prophet,
                    include_baseline=include_baseline
                )

                st.success("Training complete!")

                # Show comparison
                st.subheader("Model Comparison Results")
                st.dataframe(comparison_df.round(4), use_container_width=True)

                # Bar chart
                fig, axes = plt.subplots(1, 3, figsize=(16, 5))
                compare = comparison_df.dropna(subset=['MAE'])

                for i, metric in enumerate(['MAE', 'RMSE', 'MAPE']):
                    if metric in compare.columns:
                        bars = axes[i].bar(compare['model'], compare[metric],
                                         color=['#2C5282', '#E53E3E', '#38A169', '#D69E2E', '#805AD5'][:len(compare)])
                        best_idx = compare[metric].idxmin()
                        best_name = compare.loc[best_idx, 'model']
                        for j, name in enumerate(compare['model']):
                            if name == best_name:
                                bars[j].set_alpha(1.0)
                            else:
                                bars[j].set_alpha(0.4)
                        axes[i].set_title(f'{metric} (lower is better)')
                        axes[i].tick_params(axis='x', rotation=45)

                plt.tight_layout()
                st.pyplot(fig)

                # Save best model
                st.subheader(f"Best Model: **{best_model.replace('_', ' ').title()}**")

                # Train best model on full data
                best_forecaster = DemandForecaster(model_type=best_model)
                best_forecaster.train_model(df, target_col='sales')
                best_forecaster.save_model(
                    os.path.join(os.path.dirname(__file__), 'models', 'best_model.joblib')
                )

                # Save metrics to database
                best_metrics = comparison_df[comparison_df['model'] == best_model].iloc[0].to_dict() if len(comparison_df) > 0 else {}
                best_metrics['is_best'] = True

                try:
                    db.save_model_metrics(
                        dataset_id=1,
                        model_type=best_model,
                        metrics=best_metrics,
                        feature_count=len(best_forecaster.feature_names) if best_forecaster.feature_names else 0
                    )
                except Exception:
                    pass

                # Save comparison
                comparison_df.to_csv(
                    os.path.join(os.path.dirname(__file__), 'reports', 'exports', 'model_comparison.csv'),
                    index=False
                )

                st.success(f"Best model saved to `models/best_model.joblib`")
                st.balloons()

                st.info("""
                **Ready to use!** Go to:
                - **Forecast** → Generate predictions with the new model
                - **Model Insights** → See feature importance and SHAP analysis
                - **Inventory** → Get updated inventory recommendations
                """)

            except Exception as e:
                st.error(f"Training error: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

    # Show model history
    st.divider()
    with st.expander("Model Training History"):
        try:
            hist = db.get_model_history()
            if len(hist) > 0:
                st.dataframe(hist, use_container_width=True)
            else:
                st.info("No training history yet")
        except Exception:
            st.info("Database ready") 