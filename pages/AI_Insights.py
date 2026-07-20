import streamlit as st
import pandas as pd
import plotly.express as px
import sys, os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_loader import DataLoader
from src.preprocessing import DataPreprocessor
from src.insights_engine import InsightsEngine
from src.weather_service import WeatherService
from src.holiday_service import HolidayService
from src.inventory_optimizer import InventoryOptimizer
from src.utils import load_css

st.set_page_config(page_title="AI Insights — RetailIQ", layout="wide")

load_css()

st.markdown("""
<div class="page-header">
    <h1>🤖 AI-Powered Business Insights</h1>
    <p>Automated analysis of sales data with season, weather, and holiday awareness.</p>
</div>
""", unsafe_allow_html=True)

# ── Load data ───────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    loader = DataLoader(data_dir=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'raw'))
    calendar = loader.load_calendar()
    sales = loader.load_sales()
    prices = loader.load_prices()

    preprocessor = DataPreprocessor()
    calendar = preprocessor.clean_calendar(calendar)
    sales_long = preprocessor.melt_sales_data(sales)
    sales_long = sales_long.merge(calendar[['d', 'date', 'wm_yr_wk']], on='d')
    sales_long['date'] = pd.to_datetime(sales_long['date'])
    sales_long = sales_long.merge(prices, on=['item_id', 'store_id', 'wm_yr_wk'], how='left')

    return sales_long

try:
    with st.spinner("Loading data for analysis..."):
        sales_df = load_data()

    # ── Sidebar ──────────────────────────────────────────────────────────────
    st.sidebar.header("Analysis Scope")

    stores = ['All'] + sorted(sales_df['store_id'].unique().tolist())
    selected_store = st.sidebar.selectbox("Store", stores)

    categories = ['All'] + sorted(sales_df['cat_id'].unique().tolist())
    selected_category = st.sidebar.selectbox("Category", categories)

    if st.sidebar.button("🔄 Regenerate Insights", type="primary", use_container_width=True):
        st.cache_data.clear()

    # ── Filter ───────────────────────────────────────────────────────────────
    filtered_df = sales_df.copy()
    if selected_store != 'All':
        filtered_df = filtered_df[filtered_df['store_id'] == selected_store]
    if selected_category != 'All':
        filtered_df = filtered_df[filtered_df['cat_id'] == selected_category]

    # ── Run Insights Engine ────────────────────────────────────────────────
    with st.spinner("Analyzing data patterns..."):
        engine = InsightsEngine()
        insights = engine.analyze(filtered_df)

    # ── Live Context ─────────────────────────────────────────────────────────
    st.markdown('<div class="content-section">', unsafe_allow_html=True)
    st.markdown('<div class="content-section-title">🌤 Live Context</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div style="font-weight: 600; color: var(--primary); margin-bottom: 0.5rem;">📅 Today</div>
        """, unsafe_allow_html=True)
        st.markdown(f"""<div class="kpi-card kpi-card-blue"><div class="kpi-card-label">Current Date</div><div class="kpi-card-value">{datetime.now().strftime('%Y-%m-%d')}</div></div>""", unsafe_allow_html=True)
        st.markdown(f"""<div class="kpi-card kpi-card-purple"><div class="kpi-card-label">Day of Week</div><div class="kpi-card-value">{datetime.now().strftime('%A')}</div></div>""", unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div style="font-weight: 600; color: var(--primary); margin-bottom: 0.5rem;">🌤 Weather & Season</div>
        """, unsafe_allow_html=True)
        weather = WeatherService()
        w = weather.fetch_current_weather()
        season = w.get('season', weather.get_season(datetime.now()))
        season_emoji = weather.get_season_emoji(season)
        st.markdown(f"""<div class="kpi-card kpi-card-green"><div class="kpi-card-label">Temperature</div><div class="kpi-card-value">{w['temperature_c']:.0f}°C</div></div>""", unsafe_allow_html=True)
        st.markdown(f"""<div class="kpi-card kpi-card-orange"><div class="kpi-card-label">{season_emoji} Season</div><div class="kpi-card-value">{season}</div></div>""", unsafe_allow_html=True)
        if not weather.enabled:
            st.caption("Weather API not configured — showing seasonal defaults")

    with col3:
        st.markdown("""
        <div style="font-weight: 600; color: var(--primary); margin-bottom: 0.5rem;">🎉 Holidays</div>
        """, unsafe_allow_html=True)
        holiday_svc = HolidayService()
        today = datetime.now()
        h_name = holiday_svc.get_holiday_name(today)
        if h_name:
            st.markdown(f"""<div class="kpi-card kpi-card-red"><div class="kpi-card-label">Today's Holiday</div><div class="kpi-card-value">{h_name}</div></div>""", unsafe_allow_html=True)
        else:
            next_holidays = holiday_svc.fetch_holidays(today.year)
            future = next_holidays[next_holidays['date'].dt.date >= today.date()]
            if len(future) > 0:
                next_h = future.iloc[0]
                days_to = (next_h['date'] - pd.Timestamp(today)).days
                st.markdown(f"""<div class="kpi-card kpi-card-purple"><div class="kpi-card-label">Next Holiday ({days_to}d)</div><div class="kpi-card-value">{next_h['name']}</div></div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""<div class="kpi-card kpi-card-blue"><div class="kpi-card-label">Next Holiday</div><div class="kpi-card-value">N/A</div></div>""", unsafe_allow_html=True)

        # Pre-holiday window check
        pre_window = holiday_svc.is_in_pre_holiday_window(today)
        if pre_window:
            st.warning(f"📢 **{pre_window['advice']}** ({pre_window['days_until_holiday']} days until {pre_window['holiday_name']})")

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Seasonal Demand Advice Section ─────────────────────────────────────
    st.markdown('<div class="content-section">', unsafe_allow_html=True)
    st.markdown('<div class="content-section-title">🌤 Seasonal Demand Analysis</div>', unsafe_allow_html=True)

    season_advice = InsightsEngine.get_current_season_advice()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**{season_advice['season_emoji']} Current Season: {season_advice['current_season']}**")
        st.markdown(f"_{season_advice['season_advice']}_")

        if season_advice['high_demand_products']:
            st.markdown("**📈 High Demand Products:**")
            products_text = ', '.join([f'`{p}`' for p in season_advice['high_demand_products'][:8]])
            st.markdown(products_text)

        if season_advice['low_demand_products']:
            st.markdown("**📉 Low Demand Products:**")
            low_text = ', '.join([f'`{p}`' for p in season_advice['low_demand_products'][:5]])
            st.markdown(low_text)

    with col2:
        if season_advice['upcoming_holidays']:
            st.markdown("**📅 Upcoming Holidays:**")
            for h in season_advice['upcoming_holidays']:
                days = h.get('days_until', 0)
                st.markdown(f"- **{h['name']}** — in {days} day(s)")
                if h.get('advice'):
                    st.caption(f"  {h['advice']}")

        # Stock advice
        stock_advice = InventoryOptimizer.get_holiday_stock_advice()
        if stock_advice:
            urgent = [a for a in stock_advice if a['priority'] == 'high']
            if urgent:
                st.markdown("**⚠️ Urgent Stock Recommendations:**")
                for a in urgent[:3]:
                    st.info(f"**{a['holiday']}** in {a['days_until']}d: {a['suggestion']}")

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Weather Impact Analysis ───────────────────────────────────────────
    if 'temp_c' in sales_df.columns or 'temperature_c' in sales_df.columns:
        st.markdown('<div class="content-section">', unsafe_allow_html=True)
        st.markdown('<div class="content-section-title">🌡️ Weather Impact on Sales</div>', unsafe_allow_html=True)

        temp_col = 'temp_c' if 'temp_c' in sales_df.columns else 'temperature_c'
        # Temperature vs sales scatter
        temp_sample = sales_df.sample(min(5000, len(sales_df)))
        fig = px.scatter(temp_sample, x=temp_col, y='sales',
                         title='Temperature vs Sales (Sample)',
                         labels={temp_col: 'Temperature (°C)', 'sales': 'Units Sold'},
                         trendline='lowess',
                         template='plotly_white',
                         opacity=0.3)
        fig.update_traces(marker=dict(size=3))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # ── Display Insights by Category ─────────────────────────────────────────
    st.markdown('<div class="content-section">', unsafe_allow_html=True)
    st.markdown('<div class="content-section-title">💡 Insights Summary</div>', unsafe_allow_html=True)

    categories_order = ['Summary', 'Trends', 'Seasonality', 'Products', 'Stores', 'Revenue', 'Data Quality']
    grouped = {}
    for ins in insights:
        grouped.setdefault(ins['category'], []).append(ins)

    # Summary first
    if 'Summary' in grouped:
        for ins in grouped['Summary']:
            st.markdown(f"""
            <div class="insight-card">
                <div class="insight-card-icon" style="background: rgba(37, 99, 235, 0.1);">💡</div>
                <div class="insight-card-insight">
                    <div class="insight-card-text">{ins['insight_text']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Create expander cards for other categories
    for category in categories_order:
        if category not in grouped or category == 'Summary':
            continue

        icon_map = {
            'Trends': '📈',
            'Seasonality': '🌤',
            'Products': '🏷️',
            'Stores': '🏪',
            'Revenue': '💰',
            'Data Quality': '✅'
        }
        cat_icon = icon_map.get(category, '📌')

        with st.expander(f"{cat_icon} {category}", expanded=True):
            for ins in grouped[category]:
                if ins['severity'] == 'warning':
                    st.warning(ins['insight_text'])
                elif ins['severity'] == 'error':
                    st.error(ins['insight_text'])
                else:
                    st.markdown(f"""
                    <div class="insight-card">
                        <div class="insight-card-icon" style="background: rgba(37, 99, 235, 0.1);">📌</div>
                        <div class="insight-card-insight">
                            <div class="insight-card-text">{ins['insight_text']}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Auto Recommendations ────────────────────────────────────────────────
    st.markdown('<div class="content-section">', unsafe_allow_html=True)
    st.markdown('<div class="content-section-title">🎯 Recommended Actions</div>', unsafe_allow_html=True)

    recommendations = []
    for ins in insights:
        if ins['insight_type'] == 'weekend_effect':
            recommendations.append("**Target weekend promotions**: Align marketing campaigns with the weekend sales uplift to maximize revenue.")
        if ins['insight_type'] == 'seasonal_peak':
            recommendations.append("**Prepare for seasonal peaks**: Ramp up inventory and staffing ahead of identified high-sales months.")
        if ins['insight_type'] == 'concentration':
            recommendations.append("**Diversify product portfolio**: Heavy concentration in top products creates risk. Consider promoting mid-tier products.")
        if ins['insight_type'] == 'store_disparity':
            recommendations.append("**Investigate underperforming stores**: Review inventory levels, local marketing, and staffing at low-performing locations.")
        if ins['insight_type'] == 'slow_movers':
            recommendations.append("**Review slow-moving products**: Consider markdowns, bundle deals, or discontinuation for poorly performing items.")
        if ins['insight_type'] == 'anomalies':
            recommendations.append("**Investigate sales anomalies**: High-value outliers may indicate promotions, data errors, or special events worth recording.")
        if ins['insight_type'] == 'ramadan_window':
            recommendations.append("**Prepare for Ramadan**: Stock up on dates, juices, frozen foods, and cooking oil before Ramadan.")
        if ins['insight_type'] == 'eid_window':
            recommendations.append("**Prepare for Eid**: Increase stock of soft drinks, snacks, sweets, and gift items before Eid.")
        if ins['insight_type'] == 'monsoon_impact':
            recommendations.append("**Monsoon prep**: Stock umbrellas, raincoats, and indoor snacks. Plan for reduced foot traffic.")
        if ins['insight_type'] == 'season_performance':
            recommendations.append("**Seasonal planning**: Align staffing and inventory budgets with peak seasons.")
        if ins['insight_type'] == 'weather_correlation':
            recommendations.append("**Weather-based promotions**: Run targeted ads for cold drinks on hot days, soups/tea on cold days.")

    # Add current season advice
    if season_advice['season_advice']:
        recommendations.append(f"**{season_advice['season_emoji']} {season_advice['current_season']} action**: {season_advice['season_advice']}")

    if not recommendations:
        recommendations.append("**All clear** — No special actions recommended at this time.")

    for rec in recommendations:
        st.markdown(f"""
        <div class="rec-card">
            <div class="rec-card-icon">💡</div>
            <div class="rec-card-text">{rec}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Holiday Stock-Up Calendar ──────────────────────────────────────────
    st.markdown('<div class="content-section">', unsafe_allow_html=True)
    st.markdown('<div class="content-section-title">📅 Holiday Stock-Up Calendar</div>', unsafe_allow_html=True)

    stock_advice = InventoryOptimizer.get_holiday_stock_advice()
    if stock_advice:
        advice_df = pd.DataFrame(stock_advice)
        st.dataframe(advice_df[['holiday', 'date', 'days_until', 'priority', 'suggestion']].sort_values('days_until'),
                     use_container_width=True)

        # Color code by priority
        for _, a in advice_df.sort_values('days_until').head(5).iterrows():
            color = '#E53E3E' if a['priority'] == 'high' else '#D69E2E' if a['priority'] == 'medium' else '#2C5282'
            st.markdown(f"""
            <div style="border-left: 4px solid {color}; padding: 0.5rem 1rem; margin: 0.5rem 0;
                        background: rgba(255,255,255,0.05); border-radius: 0 4px 4px 0;">
                <strong>{a['holiday']}</strong> — {a['days_until']} days away<br>
                <span style="font-size: 0.9rem;">{a['suggestion']}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No immediate holiday stock-up actions needed.")

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Overall Health Score ────────────────────────────────────────────────
    st.markdown('<div class="content-section">', unsafe_allow_html=True)
    st.markdown('<div class="content-section-title">📊 Data Health Score</div>', unsafe_allow_html=True)

    score = 100
    details = []

    max_date = filtered_df['date'].max()
    days_since = (datetime.now() - pd.Timestamp(max_date)).days
    if days_since > 30:
        score -= 15
        details.append(f"-15: Data is {days_since} days old (recommend < 30)")
    else:
        details.append("✓ Data is current")

    items = filtered_df['item_id'].nunique()
    if items < 5:
        score -= 10
        details.append(f"-10: Only {items} products tracked")
    else:
        details.append(f"✓ {items} products tracked")

    stores_n = filtered_df['store_id'].nunique()
    if stores_n < 2:
        score -= 5
        details.append(f"-5: Only {stores_n} store")

    if 'sell_price' in filtered_df.columns:
        pct_missing = filtered_df['sell_price'].isnull().mean() * 100
        if pct_missing > 50:
            score -= 15
            details.append(f"-15: {pct_missing:.0f}% prices missing")
        else:
            details.append("✓ Price data available")
    else:
        score -= 10
        details.append("-10: No price data — revenue analysis limited")

    score = max(score, 0)

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown(f"""
        <div class="health-score-card">
            <div class="health-score-value">{score}/100</div>
            <div class="health-score-label">Data Health Score</div>
        </div>
        """, unsafe_allow_html=True)
        fig = px.pie(values=[score, 100 - score], names=['Health Score', 'Improvement Needed'],
                    color=['Health Score', 'Improvement Needed'],
                    color_discrete_map={'Health Score': '#2E7D32', 'Improvement Needed': '#E53935'},
                    hole=0.6, title='', template='plotly_white')
        fig.update_traces(textinfo='none')
        fig.add_annotation(text=f'{score}/100', x=0.5, y=0.5, font_size=24, showarrow=False)
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=250)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<div style="font-weight: 600; color: var(--primary); margin-bottom: 0.75rem;">Health Details</div>', unsafe_allow_html=True)
        for d in details:
            if d.startswith("✓"):
                st.markdown(f"""<div class="status-bar status-bar-ok" style="margin-bottom: 0.35rem;">{d}</div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""<div class="status-bar status-bar-critical" style="margin-bottom: 0.35rem;">{d}</div>""", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Export Insights ──────────────────────────────────────────────────────
    st.markdown('<div class="content-section">', unsafe_allow_html=True)
    st.markdown('<div class="content-section-title">📥 Export Insights</div>', unsafe_allow_html=True)

    insights_text = "\n\n".join([
        f"[{i['category']}] {i['insight_text']}" for i in insights
    ])
    st.download_button(
        label="📥 Download Insights as Text",
        data=insights_text,
        file_name="ai_insights.txt",
        mime="text/plain",
        use_container_width=True
    )

    insights_df = pd.DataFrame(insights)
    csv = insights_df.to_csv(index=False)
    st.download_button(
        label="📥 Download Insights as CSV",
        data=csv,
        file_name="ai_insights.csv",
        mime="text/csv"
    )

    st.markdown('</div>', unsafe_allow_html=True)

except Exception as e:
    st.error(f"Error: {str(e)}")
    import traceback
    st.code(traceback.format_exc())
