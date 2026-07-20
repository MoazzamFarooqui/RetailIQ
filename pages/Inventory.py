import streamlit as st
import pandas as pd
import plotly.express as px
import sys, os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.inventory_optimizer import InventoryOptimizer
from src.utils import load_dataframe, load_css
from src.report_generator import ReportGenerator
from src.weather_service import WeatherService
from src.holiday_service import HolidayService

st.set_page_config(page_title="Inventory — RetailIQ", layout="wide")

load_css()

# ── Pakistan context ─────────────────────────────────────────────────────────
today = datetime.now()
weather_svc = WeatherService()
weather_data = weather_svc.fetch_current_weather()
pakistan_season = weather_data.get('season', WeatherService.get_season(today))
season_emoji = WeatherService.get_season_emoji(pakistan_season)
holiday_svc = HolidayService()
pre_window = holiday_svc.is_in_pre_holiday_window(today)
demand_mult_info = InventoryOptimizer.get_current_demand_multiplier()

st.markdown("""
<div class="page-header">
    <h1>📦 Inventory Optimization</h1>
    <p>AI-powered inventory recommendations with season & holiday demand multipliers.</p>
</div>
""", unsafe_allow_html=True)

# Season context bar
ctx_cols = st.columns(4)
ctx_cols[0].metric("Current Season", f"{season_emoji} {pakistan_season}")
ctx_cols[1].metric("Temp", f"{weather_data['temperature_c']:.0f}°C")
if pre_window:
    ctx_cols[2].metric("⚠️ Pre-Holiday", f"{pre_window['holiday_name']} in {pre_window['days_until_holiday']}d")
else:
    ctx_cols[2].metric("Next Holiday", holiday_svc.get_upcoming_holidays(today).iloc[0]['name'] if len(holiday_svc.get_upcoming_holidays(today)) > 0 else 'N/A')
ctx_cols[3].metric("Demand Multiplier", f"{demand_mult_info['multiplier']}x")

if demand_mult_info['reasons']:
    st.caption(f"📊 Multiplier reasons: {' | '.join(demand_mult_info['reasons'])}")
if pre_window:
    st.info(f"📢 **{pre_window['advice']}** ({pre_window['days_until_holiday']} days until {pre_window['holiday_name']})")

# ── Load ────────────────────────────────────────────────────────────────────
@st.cache_data
def load_inventory_data():
    data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'processed', 'engineered_features.csv')
    try:
        df = load_dataframe(data_path)
        df['date'] = pd.to_datetime(df['date'])
        return df
    except Exception:
        return None

df = load_inventory_data()

if df is None:
    st.error("❌ Processed data not found — please upload and process data first.")
    st.stop()

# ── Configuration ───────────────────────────────────────────────────────────
st.sidebar.header("Configuration")
service_level = st.sidebar.slider("Service Level", 0.80, 0.99, 0.95, 0.01,
                                  help="Probability of not stocking out (95% = Z=1.65)")
lead_time_days = st.sidebar.slider("Lead Time (days)", 1, 30, 7, 1)
excess_threshold_days = st.sidebar.slider("Excess Threshold (days)", 30, 180, 60, 10,
                                          help="Stock beyond this many days of demand is considered excess")

sample_size = st.sidebar.number_input("Item-Store Combos", 100, 20000, 2000, 100)
combos = df[["item_id", "store_id"]].drop_duplicates()
sampled_combos = combos.sample(n=min(sample_size, len(combos)), random_state=42)
df_sample = df.merge(sampled_combos, on=["item_id", "store_id"])

st.info(f"📊 Analyzing **{len(df_sample):,}** records across **{len(sampled_combos):,}** item-store combinations (sampled from {len(combos):,} total)")

# ── Generate ────────────────────────────────────────────────────────────────
if st.button("🚀 Generate Inventory Recommendations", type="primary", use_container_width=True):
    with st.spinner("Analyzing inventory levels..."):

        demand_mult = demand_mult_info['multiplier']
        optimizer = InventoryOptimizer(service_level=service_level)

        if 'current_stock' not in df_sample.columns:
            stock_series = df_sample.groupby(['item_id', 'store_id'])['sales'].transform(
                lambda x: max(x.tail(28).sum() * 1.5, 10)
            )
            df_sample = df_sample.copy()
            df_sample['current_stock'] = stock_series

        recommendations = optimizer.generate_inventory_recommendations(df_sample, demand_multiplier=demand_mult)

        st.success(f"✅ Generated recommendations for **{len(recommendations)}** item-store combinations")

        overstock_items = 0
        for _, row in recommendations.iterrows():
            overstock = optimizer.detect_overstock(
                row['current_stock'], row['avg_daily_demand'], excess_threshold_days
            )
            if overstock['is_overstock']:
                overstock_items += 1

        metrics = optimizer.calculate_inventory_metrics(recommendations)

        # ── KPIs ──────────────────────────────────────────────────────────────
        st.markdown('<div class="content-section">', unsafe_allow_html=True)
        st.markdown('<div class="content-section-title">📊 Inventory KPIs</div>', unsafe_allow_html=True)

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.markdown(f"""<div class="kpi-card kpi-card-blue"><div class="kpi-card-label">Total Items</div><div class="kpi-card-value">{metrics['total_items']:,}</div></div>""", unsafe_allow_html=True)
        with col2:
            ok_pct = metrics['items_ok'] / metrics['total_items'] * 100
            st.markdown(f"""<div class="kpi-card kpi-card-green"><div class="kpi-card-label">Items Healthy</div><div class="kpi-card-value">{metrics['items_ok']:,}</div><div class="kpi-card-sub">{ok_pct:.0f}% of total</div></div>""", unsafe_allow_html=True)
        with col3:
            low_critical = metrics['items_low'] + metrics['items_critical']
            lc_pct = low_critical / metrics['total_items'] * 100
            st.markdown(f"""<div class="kpi-card kpi-card-red"><div class="kpi-card-label">Low / Critical</div><div class="kpi-card-value">{low_critical:,}</div><div class="kpi-card-sub">{lc_pct:.0f}% at risk</div></div>""", unsafe_allow_html=True)
        with col4:
            excess_pct = overstock_items / metrics['total_items'] * 100
            st.markdown(f"""<div class="kpi-card kpi-card-orange"><div class="kpi-card-label">Overstock</div><div class="kpi-card-value">{overstock_items:,}</div><div class="kpi-card-sub">{excess_pct:.0f}% excess</div></div>""", unsafe_allow_html=True)
        with col5:
            st.markdown(f"""<div class="kpi-card kpi-card-purple"><div class="kpi-card-label">Avg Days of Stock</div><div class="kpi-card-value">{metrics['avg_days_of_stock']:.1f}</div></div>""", unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

        # ── Status Distribution ──────────────────────────────────────────────
        st.markdown('<div class="content-section">', unsafe_allow_html=True)
        st.markdown('<div class="content-section-title">📈 Inventory Status Distribution</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            status_counts = recommendations['status'].value_counts()
            color_map = {'OK': '#38A169', 'LOW': '#D69E2E', 'CRITICAL': '#E53E3E', 'EXCESS': '#3182CE'}
            fig = px.pie(values=status_counts.values, names=status_counts.index,
                        title='Inventory Status',
                        color=status_counts.index,
                        color_discrete_map=color_map, template='plotly_white')
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.bar(x=status_counts.index, y=status_counts.values,
                        title='Count by Status',
                        color=status_counts.index,
                        color_discrete_map=color_map, template='plotly_white')
            fig.update_layout(showlegend=False, xaxis_title='Status', yaxis_title='Count',
                            margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig, use_container_width=True)

        st.markdown('</div>', unsafe_allow_html=True)

        # ── Stockout Prediction ──────────────────────────────────────────────
        st.markdown('<div class="content-section">', unsafe_allow_html=True)
        st.markdown('<div class="content-section-title">⚠️ Stockout Predictions</div>', unsafe_allow_html=True)

        stockout_predictions = []
        for _, row in recommendations.iterrows():
            stockout = optimizer.predict_stockout_date(row['current_stock'], row['avg_daily_demand'])
            if stockout and stockout['days_remaining'] < 90:
                stockout_predictions.append({
                    'item_id': row['item_id'],
                    'store_id': row['store_id'],
                    'current_stock': row['current_stock'],
                    'avg_daily_demand': row['avg_daily_demand'],
                    'days_remaining': stockout['days_remaining'],
                    'predicted_stockout_date': stockout['predicted_date'],
                    'status': 'CRITICAL' if stockout['is_critical'] else 'WARNING'
                })

        if stockout_predictions:
            stockout_df = pd.DataFrame(stockout_predictions)
            stockout_df = stockout_df.sort_values('days_remaining')

            critical_count = len(stockout_df[stockout_df['status'] == 'CRITICAL'])
            st.error(f"🚨 **{critical_count} items** may stock out within 7 days!")

            st.dataframe(stockout_df.head(20), use_container_width=True)

            fig = px.bar(stockout_df.head(20), x='item_id', y='days_remaining',
                        color='status', title='Days Until Stockout (Top 20 at Risk)',
                        color_discrete_map={'CRITICAL': '#E53E3E', 'WARNING': '#D69E2E'},
                        hover_data=['store_id', 'current_stock', 'avg_daily_demand'],
                        template='plotly_white')
            fig.update_layout(xaxis_title='Product', yaxis_title='Days Until Stockout',
                            margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig, use_container_width=True)

            csv_stockout = stockout_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Stockout Predictions CSV",
                data=csv_stockout,
                file_name="stockout_predictions.csv",
                mime="text/csv"
            )
        else:
            st.success("✅ No items at risk of stockout within 90 days")

        st.markdown('</div>', unsafe_allow_html=True)

        # ── Overstock Detection ─────────────────────────────────────────────
        st.markdown('<div class="content-section">', unsafe_allow_html=True)
        st.markdown('<div class="content-section-title">📦 Overstock Detection</div>', unsafe_allow_html=True)

        overstock_items_list = []
        for _, row in recommendations.iterrows():
            overstock = optimizer.detect_overstock(
                row['current_stock'], row['avg_daily_demand'], excess_threshold_days
            )
            if overstock['is_overstock']:
                overstock_items_list.append({
                    'item_id': row['item_id'],
                    'store_id': row['store_id'],
                    'current_stock': row['current_stock'],
                    'avg_daily_demand': row['avg_daily_demand'],
                    'days_of_stock': overstock['days_of_stock'],
                    'excess_units': overstock.get('excess_units', 0),
                    'reason': overstock['reason']
                })

        if overstock_items_list:
            overstock_df = pd.DataFrame(overstock_items_list)
            overstock_df = overstock_df.sort_values('days_of_stock', ascending=False)

            total_excess = overstock_df['excess_units'].sum()
            st.warning(f"⚠️ **{len(overstock_df)} items** have excess inventory (total: **{total_excess:,.0f} excess units**)")

            st.dataframe(overstock_df.head(20), use_container_width=True)

            fig = px.bar(overstock_df.head(20), x='item_id', y='excess_units',
                        color='days_of_stock', title='Excess Inventory by Product (Top 20)',
                        color_continuous_scale='OrRd', template='plotly_white',
                        hover_data=['store_id', 'current_stock', 'days_of_stock'])
            fig.update_layout(xaxis_title='Product', yaxis_title='Excess Units',
                            margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("✅ No excess inventory detected")

        st.markdown('</div>', unsafe_allow_html=True)

        # ── Critical Items ─────────────────────────────────────────────────
        st.markdown('<div class="content-section">', unsafe_allow_html=True)
        st.markdown('<div class="content-section-title">🚨 Critical & Low Stock Items</div>', unsafe_allow_html=True)

        at_risk = optimizer.identify_stockout_risk(recommendations, threshold_days=7)

        if len(at_risk) > 0:
            st.error(f"🚨 **{len(at_risk)} items** need immediate attention!")

            display_cols = ['item_id', 'store_id', 'current_stock', 'avg_daily_demand',
                           'safety_stock', 'reorder_point', 'recommended_order_qty',
                           'stockout_in_days', 'stockout_date', 'status']

            display_cols = [c for c in display_cols if c in at_risk.columns]

            st.dataframe(at_risk[display_cols].head(20), use_container_width=True)

            csv_critical = at_risk.to_csv(index=False)
            st.download_button(
                label="📥 Download Critical Items CSV",
                data=csv_critical,
                file_name="critical_inventory_items.csv",
                mime="text/csv"
            )
        else:
            st.success("✅ No critical items found!")

        st.markdown('</div>', unsafe_allow_html=True)

        # ── Recommended Actions ─────────────────────────────────────────────
        st.markdown('<div class="content-section">', unsafe_allow_html=True)
        st.markdown('<div class="content-section-title">📋 Recommended Actions</div>', unsafe_allow_html=True)

        total_order_value = recommendations['recommended_order_qty'].sum()
        items_need_reorder = len(recommendations[recommendations['recommended_order_qty'] > 0])

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""<div class="kpi-card kpi-card-blue"><div class="kpi-card-label">Items Needing Reorder</div><div class="kpi-card-value">{items_need_reorder:,}</div></div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""<div class="kpi-card kpi-card-orange"><div class="kpi-card-label">Total Units to Order</div><div class="kpi-card-value">{total_order_value:,.0f}</div></div>""", unsafe_allow_html=True)
        with col3:
            avg_order = total_order_value / max(items_need_reorder, 1)
            st.markdown(f"""<div class="kpi-card kpi-card-green"><div class="kpi-card-label">Avg Order Size</div><div class="kpi-card-value">{avg_order:.0f}</div></div>""", unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

        # ── Export ──────────────────────────────────────────────────────────
        st.markdown('<div class="content-section">', unsafe_allow_html=True)
        st.markdown('<div class="content-section-title">📤 Export Inventory Report</div>', unsafe_allow_html=True)

        export_col1, export_col2 = st.columns(2)
        with export_col1:
            csv_all = recommendations.to_csv(index=False)
            st.download_button(
                label="📥 Download Full CSV Report",
                data=csv_all,
                file_name="inventory_report.csv",
                mime="text/csv",
                use_container_width=True
            )

        with export_col2:
            try:
                pdf_path = ReportGenerator.export_combined_pdf(inventory_df=recommendations)
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

        st.session_state['inventory_recommendations'] = recommendations
        st.session_state['overstock_items'] = overstock_items_list if overstock_items_list else []

# ── View Stored Recommendations ────────────────────────────────────────────
if 'inventory_recommendations' in st.session_state:
    st.markdown('<div class="content-section">', unsafe_allow_html=True)
    st.markdown('<div class="content-section-title">🔍 View All Recommendations</div>', unsafe_allow_html=True)

    recommendations = st.session_state['inventory_recommendations']

    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.multiselect(
            "Filter by Status",
            options=recommendations['status'].unique(),
            default=recommendations['status'].unique()
        )
    with col2:
        min_days = st.slider("Min Days of Stock", 0, 200, 0)

    filtered = recommendations[
        (recommendations['status'].isin(status_filter)) &
        (recommendations['days_of_stock'] >= min_days)
    ]
    st.dataframe(filtered, use_container_width=True)

    csv = filtered.to_csv(index=False)
    st.download_button(
        label="📥 Download Filtered Recommendations",
        data=csv,
        file_name="filtered_inventory_recommendations.csv",
        mime="text/csv"
    )
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("""
<div class="content-section">
    <div class="content-section-title">📖 About Inventory Optimization</div>

| Metric | Formula | Purpose |
|---|---|---|
| **Safety Stock** | Z × σ(demand) × √Lead Time | Buffer against demand variability |
| **Reorder Point** | (Avg Demand × Lead Time) + Safety Stock | When to place a new order |
| **EOQ** | √((2 × Annual Demand × Order Cost) / Holding Cost) | Optimal order quantity |
| **Stockout Date** | Current Stock / Avg Daily Demand | When inventory will run out |
| **Overstock** | Days of Stock > Threshold | Items tying up capital unnecessarily |
</div>
""", unsafe_allow_html=True)
