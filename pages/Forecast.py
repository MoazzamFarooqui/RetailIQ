import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import sys, os
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.forecasting import DemandForecaster
from src.inventory_optimizer import InventoryOptimizer
from src.utils import load_dataframe, load_css
from src.report_generator import ReportGenerator
from src.weather_service import WeatherService
from src.holiday_service import HolidayService
from src.database import Database

st.set_page_config(page_title="Forecast — RetailIQ", layout="wide")

load_css()

st.markdown("""
<div class="page-header">
    <h1>🔮 AI Demand Forecasting</h1>
    <p>Generate demand forecasts with weather, season, and holiday context. Select a product and store to predict future sales.</p>
</div>
""", unsafe_allow_html=True)

model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models', 'best_model.joblib')

if not os.path.exists(model_path):
    st.error("❌ Model not found — please train a model first using the **Train Model** tab on the Dashboard.")
    st.info("Go to **Dashboard → Train Model** to train the forecasting model.")
    st.stop()

# ── Load ────────────────────────────────────────────────────────────────────
@st.cache_resource
def load_forecaster():
    f = DemandForecaster()
    f.load_model(model_path)
    return f

@st.cache_data
def load_processed_data():
    data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'processed', 'engineered_features.csv')
    try:
        df = load_dataframe(data_path)
        df['date'] = pd.to_datetime(df['date'])
        return df
    except:
        return None

try:
    with st.spinner("Loading model and data..."):
        forecaster = load_forecaster()
        df = load_processed_data()

    if df is None:
        st.warning("Processed data not found — please upload and process data first.")
        st.stop()

    st.success(f"✅ Model loaded: **{forecaster.model_type.replace('_', ' ').title()}** — {len(forecaster.feature_names)} features")

    # ── Live Context Banner ─────────────────────────────────────────────────
    st.markdown('<div class="content-section">', unsafe_allow_html=True)
    st.markdown('<div class="content-section-title">🌤 Live Context</div>', unsafe_allow_html=True)

    today = datetime.now()
    weather = WeatherService()
    weather_data = weather.fetch_current_weather()
    pakistan_season = weather_data.get('season', weather.get_season(today))
    season_emoji = weather.get_season_emoji(pakistan_season)

    holiday_svc = HolidayService()
    today_holiday = holiday_svc.get_holiday_name(today)
    pre_window = holiday_svc.is_in_pre_holiday_window(today)

    context_cols = st.columns(4)
    with context_cols[0]:
        st.markdown(f"""<div class="kpi-card kpi-card-blue"><div class="kpi-card-label">Today</div><div class="kpi-card-value">{today.strftime('%Y-%m-%d')}</div></div>""", unsafe_allow_html=True)
    with context_cols[1]:
        st.markdown(f"""<div class="kpi-card kpi-card-green"><div class="kpi-card-label">Temp / {season_emoji} Season</div><div class="kpi-card-value">{weather_data['temperature_c']:.0f}°C / {pakistan_season}</div></div>""", unsafe_allow_html=True)
    with context_cols[2]:
        st.markdown(f"""<div class="kpi-card kpi-card-orange"><div class="kpi-card-label">Condition</div><div class="kpi-card-value">{weather_data['weather_condition']}</div></div>""", unsafe_allow_html=True)
    with context_cols[3]:
        if today_holiday:
            st.markdown(f"""<div class="kpi-card kpi-card-purple"><div class="kpi-card-label">Holiday</div><div class="kpi-card-value">{today_holiday}</div></div>""", unsafe_allow_html=True)
        elif pre_window:
            st.markdown(f"""<div class="kpi-card kpi-card-red"><div class="kpi-card-label">⚠️ Pre-Holiday</div><div class="kpi-card-value">{pre_window['holiday_name']} in {pre_window['days_until_holiday']}d</div></div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""<div class="kpi-card kpi-card-blue"><div class="kpi-card-label">Next Holiday</div><div class="kpi-card-value">{holiday_svc.get_upcoming_holidays(today).iloc[0]['name'] if len(holiday_svc.get_upcoming_holidays(today)) > 0 else 'N/A'}</div></div>""", unsafe_allow_html=True)

    # ── Seasonal / Holiday Alert ──────────────────────────────────────────
    if pre_window:
        st.info(f"📢 **{pre_window['advice']}** ({pre_window['days_until_holiday']} days until {pre_window['holiday_name']})")
    elif weather_data.get('temperature_c', 25) >= 35:
        st.warning(f"☀️ **Extreme Heat ({weather_data['temperature_c']:.0f}°C)** — Expect high demand for cold drinks, water, ice cream.")
    elif weather_data.get('temperature_c', 25) <= 10:
        st.warning(f"❄️ **Cold Wave ({weather_data['temperature_c']:.0f}°C)** — Expect high demand for tea, coffee, soups, and warm clothing.")

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Sidebar Configuration ──────────────────────────────────────────────
    st.sidebar.header("Forecast Configuration")
    st.sidebar.markdown(f"**Current Season:** {season_emoji} {pakistan_season}")

    stores = sorted(df['store_id'].unique().tolist())
    selected_store = st.sidebar.selectbox("Store", stores)

    items_in_store = df[df['store_id'] == selected_store]['item_id'].unique()
    selected_item = st.sidebar.selectbox("Product", sorted(items_in_store.tolist()))

    st.sidebar.subheader("Forecast Period")
    horizon_preset = st.sidebar.radio(
        "Select horizon",
        options=['7 Days', '30 Days', '90 Days'],
        index=1,
        horizontal=True
    )
    forecast_days = int(horizon_preset.split()[0])
    st.sidebar.caption(f"Forecasting {forecast_days} days ahead")

    # ── Demand multiplier info ───────────────────────────────────────────
    demand_info = InventoryOptimizer.get_current_demand_multiplier()
    if demand_info['multiplier'] != 1.0:
        st.sidebar.markdown("---")
        st.sidebar.markdown(f"**📊 Active Demand Multiplier:** {demand_info['multiplier']}x")
        for reason in demand_info['reasons']:
            st.sidebar.caption(f"  • {reason}")

    # ── Seasonal product alert ───────────────────────────────────────────
    product_alert = InventoryOptimizer.check_seasonal_product_alerts(selected_item)
    if product_alert['alert'] == 'high_demand':
        st.sidebar.warning(product_alert['message'])
    elif product_alert['alert'] == 'low_demand':
        st.sidebar.info(product_alert['message'])

    # ── Get historical data ────────────────────────────────────────────────
    item_store_data = df[
        (df['item_id'] == selected_item) &
        (df['store_id'] == selected_store)
    ].sort_values('date').tail(90)

    if len(item_store_data) == 0:
        st.warning(f"No data found for {selected_item} at {selected_store}")
        st.stop()

    # ── Display Info ───────────────────────────────────────────────────────
    st.markdown('<div class="content-section">', unsafe_allow_html=True)
    st.markdown(f'<div class="content-section-title">📋 Product: {selected_item} @ {selected_store}</div>', unsafe_allow_html=True)

    avg_sales = item_store_data['sales'].mean()
    total_sales = item_store_data['sales'].sum()
    std_sales = item_store_data['sales'].std()
    last_sale = item_store_data['sales'].iloc[-1]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""<div class="kpi-card kpi-card-blue"><div class="kpi-card-label">Avg Daily Sales</div><div class="kpi-card-value">{avg_sales:.2f}</div></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="kpi-card kpi-card-green"><div class="kpi-card-label">Total Sales (90d)</div><div class="kpi-card-value">{total_sales:.0f}</div></div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="kpi-card kpi-card-orange"><div class="kpi-card-label">Std Deviation</div><div class="kpi-card-value">{std_sales:.2f}</div></div>""", unsafe_allow_html=True)
    with col4:
        st.markdown(f"""<div class="kpi-card kpi-card-purple"><div class="kpi-card-label">Last Day Sales</div><div class="kpi-card-value">{last_sale:.0f}</div></div>""", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Generate Forecast ──────────────────────────────────────────────────
    if st.button("🚀 Generate Forecast", type="primary", use_container_width=True):
        with st.spinner(f"Generating {forecast_days}-day forecast..."):
            try:
                last_data_date = item_store_data['date'].max()
                forecast_start = max(last_data_date, pd.Timestamp(today))
                start_from = last_data_date + timedelta(days=1)

                future_dates = pd.date_range(start=start_from, periods=forecast_days)

                history = item_store_data.sort_values('date').tail(90).copy()
                predictions = []

                base_row = history.iloc[-1:].copy()

                for fd in future_dates:
                    future_row = base_row.copy()

                    future_row['year'] = fd.year
                    future_row['month'] = fd.month
                    future_row['day'] = fd.day
                    future_row['dayofweek'] = fd.dayofweek()
                    future_row['is_weekend'] = 1 if fd.dayofweek() >= 5 else 0
                    future_row['date'] = fd
                    if 'wm_yr_wk' in future_row.columns:
                        iso_cal = fd.isocalendar()
                        future_row['wm_yr_wk'] = fd.year * 100 + iso_cal[1]

                    X_curr, _ = forecaster.prepare_features(future_row, target_col='sales')
                    pred = forecaster.predict(X_curr)[0]
                    predictions.append(max(0, pred))

                forecast_df = pd.DataFrame({
                    'date': future_dates,
                    'predicted_sales': predictions
                })

                # ── Forecast Visualization ──────────────────────────────────
                st.markdown('<div class="content-section">', unsafe_allow_html=True)
                st.markdown('<div class="content-section-title">📈 Forecast Visualization</div>', unsafe_allow_html=True)

                historical_plot = item_store_data[['date', 'sales']].copy()
                historical_plot.columns = ['date', 'value']
                historical_plot['type'] = 'Historical'

                forecast_plot = forecast_df.copy()
                forecast_plot.columns = ['date', 'value']
                forecast_plot['type'] = f'Forecast ({forecast_days}d)'

                combined = pd.concat([historical_plot, forecast_plot])

                fig = px.line(combined, x='date', y='value', color='type',
                             title=f'Sales Forecast — {selected_item} @ {selected_store}',
                             color_discrete_map={'Historical': '#2C5282', f'Forecast ({forecast_days}d)': '#E53E3E'},
                             template='plotly_white')
                fig.update_layout(xaxis_title='Date', yaxis_title='Sales', legend_title='',
                                 margin=dict(l=10, r=10, t=30, b=10))
                fig.update_traces(line=dict(width=2))
                st.plotly_chart(fig, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

                # ── Forecast Summary ────────────────────────────────────────
                st.markdown('<div class="content-section">', unsafe_allow_html=True)
                st.markdown('<div class="content-section-title">📊 Forecast Summary</div>', unsafe_allow_html=True)

                total_forecast = forecast_df['predicted_sales'].sum()
                avg_forecast = forecast_df['predicted_sales'].mean()
                peak_day = forecast_df.loc[forecast_df['predicted_sales'].idxmax()]
                low_day = forecast_df.loc[forecast_df['predicted_sales'].idxmin()]

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.markdown(f"""<div class="kpi-card kpi-card-blue"><div class="kpi-card-label">Total Forecast</div><div class="kpi-card-value">{total_forecast:.0f}</div></div>""", unsafe_allow_html=True)
                with col2:
                    st.markdown(f"""<div class="kpi-card kpi-card-green"><div class="kpi-card-label">Avg Daily</div><div class="kpi-card-value">{avg_forecast:.2f}</div></div>""", unsafe_allow_html=True)
                with col3:
                    change = ((avg_forecast - avg_sales) / avg_sales) * 100 if avg_sales > 0 else 0
                    st.markdown(f"""<div class="kpi-card kpi-card-orange"><div class="kpi-card-label">vs Historical</div><div class="kpi-card-value">{change:+.1f}%</div></div>""", unsafe_allow_html=True)
                with col4:
                    st.markdown(f"""<div class="kpi-card kpi-card-purple"><div class="kpi-card-label">Peak Day</div><div class="kpi-card-value">{peak_day['predicted_sales']:.0f}</div><div class="kpi-card-sub">{peak_day['date'].strftime('%m/%d')}</div></div>""", unsafe_allow_html=True)

                st.markdown('</div>', unsafe_allow_html=True)

                # ── Weather Forecast Context ────────────────────────────────
                with st.expander("🌤 Weather Forecast for Period", expanded=False):
                    weather_fc = weather.fetch_forecast(days=min(forecast_days, 7))
                    if weather_fc is not None and len(weather_fc) > 0:
                        st.dataframe(weather_fc, use_container_width=True)
                        # Weather alerts for forecast period
                        hot_days = weather_fc[weather_fc['temp_c'] >= 35]
                        rainy_days = weather_fc[weather_fc.get('rain_mm', 0) > 10]
                        cold_days = weather_fc[weather_fc['temp_c'] <= 10]
                        if len(hot_days) > 0:
                            st.warning(f"☀️ {len(hot_days)} hot day(s) in forecast period — ensure cold drink stock.")
                        if len(rainy_days) > 0:
                            st.warning(f"🌧️ {len(rainy_days)} rainy day(s) in forecast period — umbrellas/raincoats may see demand.")
                        if len(cold_days) > 0:
                            st.warning(f"❄️ {len(cold_days)} cold day(s) in forecast period — stock tea/coffee/soups.")

                # ── Holiday Alerts ──────────────────────────────────────────
                with st.expander("📅 Holidays in Forecast Period", expanded=False):
                    holidays_in_period = []
                    for fd in future_dates:
                        h_name = holiday_svc.get_holiday_name(fd)
                        if h_name:
                            holidays_in_period.append({'date': fd.strftime('%Y-%m-%d'), 'holiday': h_name})
                    if holidays_in_period:
                        st.dataframe(pd.DataFrame(holidays_in_period), use_container_width=True)
                        for h in holidays_in_period:
                            advice = HolidayService.get_holiday_advice(h['holiday'])
                            if advice:
                                st.info(f"📢 **{h['holiday']}** ({h['date']}): {advice}")
                    else:
                        st.info("No major holidays in this forecast period.")

                # ── Inventory Integration ────────────────────────────────────
                st.markdown('<div class="content-section">', unsafe_allow_html=True)
                st.markdown('<div class="content-section-title">📦 Inventory Recommendations</div>', unsafe_allow_html=True)

                optimizer = InventoryOptimizer(service_level=0.95)

                hist_for_inv = item_store_data['sales'].tail(28).values
                forecast_for_inv = np.array(predictions)
                full_demand = np.concatenate([hist_for_inv, forecast_for_inv])

                # Apply demand multiplier if in peak season
                demand_mult = demand_info['multiplier']
                opt_result = optimizer.optimize_inventory_for_item(
                    full_demand, lead_time_days=7, demand_multiplier=demand_mult
                )
                simulated_stock = max(hist_for_inv.sum() * 1.5, 10)

                stock_status = 'OK'
                if simulated_stock < opt_result['safety_stock']:
                    stock_status = 'CRITICAL'
                elif simulated_stock < opt_result['reorder_point']:
                    stock_status = 'LOW'
                elif simulated_stock > opt_result['reorder_point'] + opt_result['eoq']:
                    stock_status = 'EXCESS'

                stockout = optimizer.predict_stockout_date(simulated_stock, avg_forecast * demand_mult)

                inv_col1, inv_col2, inv_col3, inv_col4 = st.columns(4)
                with inv_col1:
                    st.markdown(f"""<div class="kpi-card kpi-card-blue"><div class="kpi-card-label">Current Stock (est.)</div><div class="kpi-card-value">{simulated_stock:.0f}</div></div>""", unsafe_allow_html=True)
                with inv_col2:
                    st.markdown(f"""<div class="kpi-card kpi-card-green"><div class="kpi-card-label">Safety Stock</div><div class="kpi-card-value">{opt_result['safety_stock']:.0f}</div></div>""", unsafe_allow_html=True)
                with inv_col3:
                    st.markdown(f"""<div class="kpi-card kpi-card-orange"><div class="kpi-card-label">Reorder Point</div><div class="kpi-card-value">{opt_result['reorder_point']:.0f}</div></div>""", unsafe_allow_html=True)
                with inv_col4:
                    st.markdown(f"""<div class="kpi-card kpi-card-purple"><div class="kpi-card-label">EOQ</div><div class="kpi-card-value">{opt_result['eoq']:.0f}</div></div>""", unsafe_allow_html=True)

                if stock_status == 'CRITICAL':
                    st.error(f"**CRITICAL**: Stock ({simulated_stock:.0f}) below safety stock ({opt_result['safety_stock']:.0f})!")
                elif stock_status == 'LOW':
                    st.warning(f"**LOW**: Stock ({simulated_stock:.0f}) below reorder point ({opt_result['reorder_point']:.0f})")
                elif stock_status == 'EXCESS':
                    st.info(f"**EXCESS**: Stock exceeds optimal levels")
                else:
                    st.success("**OK**: Stock levels are healthy")

                if stockout and stockout['days_remaining'] < 30:
                    st.warning(f"**Stockout predicted in {stockout['days_remaining']:.0f} days** (around {stockout['predicted_date']})")

                recommended_order = max(0, opt_result['reorder_point'] - simulated_stock)
                if recommended_order > 0:
                    st.info(f"**Recommended Order**: {recommended_order:.0f} units (demand multiplier: {demand_mult}x)")

                # Demand multiplier explanation
                if demand_info['multiplier'] != 1.0:
                    st.caption(f"📊 Inventory adjusted for {pakistan_season} demand ({' + '.join(demand_info['reasons'])} = {demand_info['multiplier']}x)")

                st.markdown('</div>', unsafe_allow_html=True)

                # ── Export ────────────────────────────────────────────────────
                st.markdown('<div class="content-section">', unsafe_allow_html=True)
                st.markdown('<div class="content-section-title">📤 Export Report</div>', unsafe_allow_html=True)

                export_col1, export_col2 = st.columns(2)

                with export_col1:
                    csv = forecast_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv,
                        file_name=f"forecast_{selected_item}_{selected_store}_{forecast_days}d.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

                with export_col2:
                    try:
                        inv_summary = pd.DataFrame([{
                            'item_id': selected_item, 'store_id': selected_store,
                            'current_stock': simulated_stock,
                            'safety_stock': opt_result['safety_stock'],
                            'reorder_point': opt_result['reorder_point'],
                            'eoq': opt_result['eoq'],
                            'recommended_order': recommended_order,
                            'status': stock_status,
                            'demand_multiplier': demand_mult,
                            'season': pakistan_season,
                        }])

                        insights_txt = (f"Forecast for {selected_item} at {selected_store}\n"
                                        f"Season: {pakistan_season}\n"
                                        f"Horizon: {forecast_days} days\n"
                                        f"Total forecasted: {total_forecast:.0f}\n"
                                        f"Model: {forecaster.model_type}\n"
                                        f"Demand multiplier: {demand_mult}x")

                        pdf_path = ReportGenerator.export_pdf_report(
                            forecast_df=forecast_df,
                            inventory_df=inv_summary,
                            insights_text=insights_txt
                        )
                        if os.path.exists(pdf_path) and pdf_path.endswith('.pdf'):
                            with open(pdf_path, 'rb') as f:
                                st.download_button(
                                    label="📥 Download PDF Report",
                                    data=f,
                                    file_name=os.path.basename(pdf_path),
                                    mime="application/pdf",
                                    use_container_width=True
                                )
                        else:
                            st.button("PDF export unavailable", disabled=True)
                    except Exception:
                        st.button("PDF export unavailable", disabled=True)

                st.markdown('</div>', unsafe_allow_html=True)

                with st.expander("📊 View Forecast Data"):
                    forecast_display = forecast_df.copy()
                    forecast_display['predicted_sales'] = forecast_display['predicted_sales'].round(2)
                    st.dataframe(forecast_display, use_container_width=True)

                try:
                    db = Database()
                    db.save_forecast(
                        dataset_id=1, model_type=forecaster.model_type,
                        horizon_days=forecast_days, forecast_df=forecast_df
                    )
                    db.save_forecast_header(
                        dataset_id=1, model_type=forecaster.model_type,
                        horizon_days=forecast_days, item_count=1, store_count=1,
                        total_forecast=total_forecast
                    )
                except Exception:
                    pass

            except Exception as e:
                st.error(f"Error generating forecast: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

    # ── Historical Trend (always visible) ──────────────────────────────────
    st.markdown('<div class="content-section">', unsafe_allow_html=True)
    st.markdown('<div class="content-section-title">📜 Historical Sales (Last 90 Days)</div>', unsafe_allow_html=True)
    fig = px.line(item_store_data, x='date', y='sales', title='Historical Sales Trend',
                 template='plotly_white')
    fig.update_layout(xaxis_title='Date', yaxis_title='Sales',
                     margin=dict(l=10, r=10, t=30, b=10))
    fig.update_traces(line=dict(color='#2C5282', width=2))
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

except Exception as e:
    st.error(f"Error: {str(e)}")
    import traceback
    st.code(traceback.format_exc())
