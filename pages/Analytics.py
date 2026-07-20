import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import load_css
from src.data_loader import DataLoader
from src.preprocessing import DataPreprocessor
from src.weather_service import WeatherService
from src.holiday_service import HolidayService

st.set_page_config(page_title="Analytics — RetailIQ", layout="wide")

load_css()

st.markdown("""
<div class="page-header">
    <h1>📈 Sales & Revenue Analytics</h1>
    <p>Comprehensive analysis with season, holiday, and weather insights.</p>
</div>
""", unsafe_allow_html=True)

# ── Load data ───────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'processed', 'engineered_features.csv')
    if not os.path.exists(data_path):
        data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'processed', 'final_dataset.csv')
    if os.path.exists(data_path):
        sales_long = pd.read_csv(data_path)
        sales_long['date'] = pd.to_datetime(sales_long['date'])
        return sales_long
    loader = DataLoader(data_dir=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'raw'))
    calendar = loader.load_calendar()
    sales = loader.load_sales()
    prices = loader.load_prices()
    preprocessor = DataPreprocessor()
    calendar = preprocessor.clean_calendar(calendar)
    sales_long = preprocessor.melt_sales_data(sales)
    sales_long = sales_long.merge(calendar[['d', 'date', 'wm_yr_wk']], on='d')
    sales_long['date'] = pd.to_datetime(sales_long['date'])
    sales_long = sales_long.merge(prices[['item_id', 'store_id', 'wm_yr_wk', 'sell_price']],
                                  on=['item_id', 'store_id', 'wm_yr_wk'], how='left')
    return sales_long

try:
    with st.spinner("Loading data..."):
        sales_df = load_data()

    st.success(f"✅ Loaded {len(sales_df):,} sales records · {sales_df['item_id'].nunique():,} products · {sales_df['store_id'].nunique()} stores")

    # ── Add Pakistan season column ──────────────────────────────────────────
    sales_df['season'] = sales_df['date'].apply(WeatherService.get_season)
    season_emoji_map = {'Spring': '🌸', 'Summer': '☀️', 'Monsoon': '🌧️', 'Autumn': '🍂', 'Winter': '❄️'}

    # ── Filters ──────────────────────────────────────────────────────────────
    st.sidebar.header("Analysis Filters")

    stores = ['All'] + sorted(sales_df['store_id'].unique().tolist())
    selected_store = st.sidebar.selectbox("Store", stores)

    categories = ['All'] + sorted(sales_df['cat_id'].unique().tolist())
    selected_category = st.sidebar.selectbox("Category", categories)

    seasons = ['All'] + ['Spring', 'Summer', 'Monsoon', 'Autumn', 'Winter']
    selected_season = st.sidebar.selectbox("Season", seasons,
                                            format_func=lambda x: f"{season_emoji_map.get(x, '')} {x}" if x != 'All' else 'All')

    date_range = st.sidebar.date_input(
        "Date Range",
        value=(sales_df['date'].min(), sales_df['date'].max()),
        min_value=sales_df['date'].min(),
        max_value=sales_df['date'].max()
    )

    # Apply filters
    filtered_df = sales_df.copy()
    if selected_store != 'All':
        filtered_df = filtered_df[filtered_df['store_id'] == selected_store]
    if selected_category != 'All':
        filtered_df = filtered_df[filtered_df['cat_id'] == selected_category]
    if selected_season != 'All':
        filtered_df = filtered_df[filtered_df['season'] == selected_season]
    if len(date_range) == 2:
        filtered_df = filtered_df[
            (filtered_df['date'] >= pd.Timestamp(date_range[0])) &
            (filtered_df['date'] <= pd.Timestamp(date_range[1]))
        ]

    # ── Key Metrics ─────────────────────────────────────────────────────────
    st.markdown('<div class="content-section">', unsafe_allow_html=True)
    st.markdown('<div class="content-section-title">📊 Key Metrics</div>', unsafe_allow_html=True)

    total_sales = filtered_df['sales'].sum()
    avg_daily = filtered_df.groupby('date')['sales'].sum().mean()
    unique_items = filtered_df['item_id'].nunique()
    sales_days = filtered_df['date'].nunique()

    if 'sell_price' in filtered_df.columns:
        filtered_df['revenue'] = filtered_df['sales'] * filtered_df['sell_price'].fillna(0)
        total_revenue = filtered_df['revenue'].sum()
        avg_revenue = filtered_df.groupby('date')['revenue'].sum().mean()
        has_revenue = True
    else:
        total_revenue = 0
        avg_revenue = 0
        has_revenue = False

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(f"""<div class="kpi-card kpi-card-blue"><div class="kpi-card-label">Total Sales</div><div class="kpi-card-value">{total_sales:,.0f}</div></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="kpi-card kpi-card-green"><div class="kpi-card-label">Avg Daily Sales</div><div class="kpi-card-value">{avg_daily:,.0f}</div></div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="kpi-card kpi-card-purple"><div class="kpi-card-label">Products</div><div class="kpi-card-value">{unique_items:,}</div></div>""", unsafe_allow_html=True)
    with col4:
        st.markdown(f"""<div class="kpi-card kpi-card-orange"><div class="kpi-card-label">Sales Days</div><div class="kpi-card-value">{sales_days}</div></div>""", unsafe_allow_html=True)
    with col5:
        st.markdown(f"""<div class="kpi-card kpi-card-red"><div class="kpi-card-label">Stores</div><div class="kpi-card-value">{filtered_df['store_id'].nunique()}</div></div>""", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Charts Row ───────────────────────────────────────────────────────
    st.markdown('<div class="content-section">', unsafe_allow_html=True)
    st.markdown('<div class="content-section-title">📈 Trends</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    daily_data = filtered_df.groupby('date').agg({'sales': 'sum'}).reset_index()
    if has_revenue:
        rev_daily = filtered_df.groupby('date')['revenue'].sum().reset_index()
        daily_data = daily_data.merge(rev_daily, on='date')

    with col1:
        fig = px.line(daily_data, x='date', y='sales', title='Daily Sales Over Time',
                      template='plotly_white')
        fig.update_layout(xaxis_title='Date', yaxis_title='Units Sold',
                         margin=dict(l=10, r=10, t=30, b=10))
        fig.update_traces(line=dict(color='#2C5282', width=2))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        if has_revenue:
            fig = px.line(daily_data, x='date', y='revenue', title='Daily Revenue',
                         color_discrete_sequence=['#2E7D32'], template='plotly_white')
            fig.update_layout(xaxis_title='Date', yaxis_title='Revenue ($)',
                            margin=dict(l=10, r=10, t=30, b=10))
            fig.update_traces(line=dict(width=2))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Revenue data unavailable — price column not found")

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Pakistan Season Analysis ──────────────────────────────────────────
    st.markdown('<div class="content-section">', unsafe_allow_html=True)
    st.markdown('<div class="content-section-title">🌤 Season Analysis</div>', unsafe_allow_html=True)

    season_data = filtered_df.groupby('season').agg({
        'sales': ['sum', 'mean', 'std'],
        'item_id': 'nunique',
    }).round(2).reset_index()
    season_data.columns = ['Season', 'Total Sales', 'Avg Daily Sales', 'Std Dev', 'Products']

    col1, col2 = st.columns([3, 2])

    with col1:
        fig = px.bar(season_data, x='Season', y='Total Sales', color='Season',
                     title='Sales by Season',
                     color_discrete_map={'Spring': '#38A169', 'Summer': '#E53E3E',
                                         'Monsoon': '#3182CE', 'Autumn': '#D69E2E', 'Winter': '#805AD5'},
                     template='plotly_white',
                     category_orders={'Season': ['Spring', 'Summer', 'Monsoon', 'Autumn', 'Winter']})
        fig.update_layout(margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.dataframe(season_data.style.format({
            'Total Sales': '{:,.0f}',
            'Avg Daily Sales': '{:,.0f}',
            'Std Dev': '{:,.0f}',
            'Products': '{:,.0f}',
        }), use_container_width=True)

    # Season trend overlay
    daily_data['season'] = daily_data['date'].apply(WeatherService.get_season)
    fig = px.scatter(daily_data, x='date', y='sales', color='season',
                     title='Daily Sales Colored by Season',
                     color_discrete_map={'Spring': '#38A169', 'Summer': '#E53E3E',
                                         'Monsoon': '#3182CE', 'Autumn': '#D69E2E', 'Winter': '#805AD5'},
                     template='plotly_white',
                     category_orders={'season': ['Spring', 'Summer', 'Monsoon', 'Autumn', 'Winter']})
    fig.update_traces(marker=dict(size=4, opacity=0.6))
    fig.update_layout(margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Holiday Impact Analysis ───────────────────────────────────────────
    st.markdown('<div class="content-section">', unsafe_allow_html=True)
    st.markdown('<div class="content-section-title">🎉 Holiday Impact</div>', unsafe_allow_html=True)

    holiday_svc = HolidayService()
    holiday_df = holiday_svc.get_holiday_features(filtered_df.copy())

    # Check why holidays might not be found — data range issue?
    data_min = filtered_df['date'].min()
    data_max = filtered_df['date'].max()
    known_holiday_years = list(_ISLAMIC_HOLIDAYS.keys()) if hasattr(HolidayService, '_ISLAMIC_HOLIDAYS') else []
    # Also check fixed holidays: any date with month-day matching Pakistan Day etc.
    from src.holiday_service import _FIXED_PAK_HOLIDAYS

    if 'is_holiday' in holiday_df.columns and holiday_df['is_holiday'].sum() > 0:
        holiday_comparison = holiday_df.groupby('is_holiday')['sales'].mean().reset_index()
        holiday_comparison['is_holiday'] = holiday_comparison['is_holiday'].map({0: 'Regular Day', 1: 'Holiday'})

        col1, col2 = st.columns(2)

        with col1:
            fig = px.bar(holiday_comparison, x='is_holiday', y='sales', color='is_holiday',
                         title='Avg Sales: Holiday vs Regular Day',
                         color_discrete_map={'Regular Day': '#2C5282', 'Holiday': '#E53E3E'},
                         template='plotly_white')
            fig.update_layout(xaxis_title='', yaxis_title='Average Sales',
                            margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            if 'in_ramadan_window' in holiday_df.columns and holiday_df['in_ramadan_window'].sum() > 0:
                ramadan_data = holiday_df.groupby('in_ramadan_window')['sales'].mean().reset_index()
                ramadan_data['in_ramadan_window'] = ramadan_data['in_ramadan_window'].map({0: 'Regular', 1: 'Pre-Ramadan'})
                fig = px.bar(ramadan_data, x='in_ramadan_window', y='sales', color='in_ramadan_window',
                             title='Pre-Ramadan vs Regular Sales',
                             color_discrete_map={'Regular': '#2C5282', 'Pre-Ramadan': '#38A169'},
                             template='plotly_white')
                fig.update_layout(xaxis_title='', yaxis_title='Average Sales',
                                margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(fig, use_container_width=True)
    else:
        # Helpful message explaining WHY no holiday data was found
        st.info(f"""
        **No Pakistan holidays detected in this data range ({data_min.date()} to {data_max.date()}).**

        The M5 dataset (2011–2016) contains US retail data — Pakistan holidays like Eid,
        Ramadan, and Pakistan Day may not fall on sales days in this period.

        **To see holiday impact analysis:**
        - Upload your own Pakistan retail sales CSV with recent dates (2024+) via the **Upload** tab
        - Islamic holidays (Eid, Ramadan) are pre-loaded for 2024–2028
        - Fixed holidays (Pakistan Day, Independence Day, etc.) work for any year
        """)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Store Performance ────────────────────────────────────────────────
    st.markdown('<div class="content-section">', unsafe_allow_html=True)
    st.markdown('<div class="content-section-title">🏪 Store Performance</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        store_sales = filtered_df.groupby('store_id')['sales'].sum().sort_values(ascending=False).reset_index()
        fig = px.bar(store_sales, x='store_id', y='sales', color='sales',
                     title='Total Sales by Store', color_continuous_scale='Blues', template='plotly_white')
        fig.update_layout(xaxis_title='Store', yaxis_title='Total Sales',
                         margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Store performance by season
        store_season = filtered_df.groupby(['store_id', 'season'])['sales'].sum().reset_index()
        fig = px.bar(store_season, x='store_id', y='sales', color='season',
                     title='Store Sales by Season',
                     color_discrete_map={'Spring': '#38A169', 'Summer': '#E53E3E',
                                         'Monsoon': '#3182CE', 'Autumn': '#D69E2E', 'Winter': '#805AD5'},
                     template='plotly_white',
                     category_orders={'season': ['Spring', 'Summer', 'Monsoon', 'Autumn', 'Winter']})
        fig.update_layout(margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Category Analysis ─────────────────────────────────────────────────
    st.markdown('<div class="content-section">', unsafe_allow_html=True)
    st.markdown('<div class="content-section-title">📂 Category × Season Analysis</div>', unsafe_allow_html=True)

    cat_season = filtered_df.groupby(['cat_id', 'season'])['sales'].sum().reset_index()

    fig = px.bar(cat_season, x='cat_id', y='sales', color='season',
                 title='Sales by Category and Season',
                 color_discrete_map={'Spring': '#38A169', 'Summer': '#E53E3E',
                                     'Monsoon': '#3182CE', 'Autumn': '#D69E2E', 'Winter': '#805AD5'},
                 template='plotly_white', barmode='group',
                 category_orders={'season': ['Spring', 'Summer', 'Monsoon', 'Autumn', 'Winter']})
    fig.update_layout(margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Top Products ────────────────────────────────────────────────────────
    st.markdown('<div class="content-section">', unsafe_allow_html=True)
    st.markdown('<div class="content-section-title">🏆 Top Products</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        top_products = filtered_df.groupby('item_id')['sales'].sum().sort_values(ascending=False).head(20).reset_index()
        fig = px.bar(top_products, x='item_id', y='sales', color='sales',
                     title='Top 20 Products by Sales Volume', color_continuous_scale='Blues', template='plotly_white')
        fig.update_layout(xaxis_title='Product ID', yaxis_title='Total Sales',
                         margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        if has_revenue:
            top_rev = filtered_df.groupby('item_id')['revenue'].sum().sort_values(ascending=False).head(20).reset_index()
            fig = px.bar(top_rev, x='item_id', y='revenue', color='revenue',
                         title='Top 20 Products by Revenue', color_continuous_scale='Greens', template='plotly_white')
            fig.update_layout(xaxis_title='Product ID', yaxis_title='Total Revenue ($)',
                            margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Day of Week Analysis ───────────────────────────────────────────────
    st.markdown('<div class="content-section">', unsafe_allow_html=True)
    st.markdown('<div class="content-section-title">📅 Day of Week Analysis</div>', unsafe_allow_html=True)

    filtered_df['dayofweek'] = filtered_df['date'].dt.dayofweek
    dow_data = filtered_df.groupby('dayofweek').agg({'sales': 'mean'}).reset_index()
    dow_data['day_name'] = dow_data['dayofweek'].map({
        0: 'Monday', 1: 'Tuesday', 2: 'Wednesday', 3: 'Thursday',
        4: 'Friday', 5: 'Saturday', 6: 'Sunday'
    })

    fig = px.bar(dow_data, x='day_name', y='sales', title='Average Sales by Day of Week',
                 color='sales', color_continuous_scale='Blues', template='plotly_white')
    fig.update_layout(xaxis_title='', yaxis_title='Average Sales',
                     margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Export ──────────────────────────────────────────────────────────────
    st.markdown('<div class="content-section">', unsafe_allow_html=True)
    st.markdown('<div class="content-section-title">📥 Export</div>', unsafe_allow_html=True)

    csv_full = filtered_df.to_csv(index=False)
    st.download_button(
        label="📥 Download Analytics Data as CSV",
        data=csv_full,
        file_name="analytics_report.csv",
        mime="text/csv",
        use_container_width=True
    )

    summary_data = {
        'Metric': ['Total Sales', 'Avg Daily Sales', 'Products', 'Days', 'Stores', 'Categories'],
        'Value': [
            f"{total_sales:,.0f}", f"{avg_daily:,.0f}", f"{unique_items:,}",
            f"{sales_days}", f"{filtered_df['store_id'].nunique()}",
            f"{filtered_df['cat_id'].nunique()}"
        ]
    }
    summary_df = pd.DataFrame(summary_data)
    csv_summary = summary_df.to_csv(index=False)
    st.download_button(label="📊 Download Summary Stats as CSV", data=csv_summary,
                       file_name="analytics_summary.csv", mime="text/csv")

    st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("🔍 View Raw Data"):
        st.dataframe(filtered_df.head(1000), use_container_width=True)

except Exception as e:
    st.error(f"Error: {str(e)}")
    import traceback
    st.code(traceback.format_exc())
