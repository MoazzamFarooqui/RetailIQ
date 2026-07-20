import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go

class Visualizer:
    def __init__(self, style='seaborn-v0_8-darkgrid'):
        plt.style.use('default')
        sns.set_palette("husl")

    def plot_sales_trend(self, df, date_col='date', sales_col='sales', title='Sales Trend Over Time'):
        """Plot sales trend over time"""
        fig = px.line(df, x=date_col, y=sales_col, title=title)
        fig.update_layout(xaxis_title='Date', yaxis_title='Sales')
        return fig

    def plot_sales_by_category(self, df, category_col='cat_id', sales_col='sales'):
        """Plot sales by category"""
        category_sales = df.groupby(category_col)[sales_col].sum().reset_index()
        category_sales = category_sales.sort_values(sales_col, ascending=False)

        fig = px.bar(category_sales, x=category_col, y=sales_col,
                    title='Total Sales by Category')
        fig.update_layout(xaxis_title='Category', yaxis_title='Total Sales')
        return fig

    def plot_sales_by_store(self, df, store_col='store_id', sales_col='sales'):
        """Plot sales by store"""
        store_sales = df.groupby(store_col)[sales_col].sum().reset_index()
        store_sales = store_sales.sort_values(sales_col, ascending=False)

        fig = px.bar(store_sales, x=store_col, y=sales_col,
                    title='Total Sales by Store', color=sales_col)
        fig.update_layout(xaxis_title='Store', yaxis_title='Total Sales')
        return fig

    def plot_top_products(self, df, item_col='item_id', sales_col='sales', top_n=20):
        """Plot top N products by sales"""
        product_sales = df.groupby(item_col)[sales_col].sum().reset_index()
        product_sales = product_sales.sort_values(sales_col, ascending=False).head(top_n)

        fig = px.bar(product_sales, x=item_col, y=sales_col,
                    title=f'Top {top_n} Products by Sales', color=sales_col)
        fig.update_layout(xaxis_title='Product', yaxis_title='Total Sales')
        return fig

    def plot_sales_heatmap(self, df, date_col='date', sales_col='sales'):
        """Plot sales heatmap by day of week and month"""
        df['dayofweek'] = df[date_col].dt.dayofweek
        df['month'] = df[date_col].dt.month

        heatmap_data = df.groupby(['dayofweek', 'month'])[sales_col].mean().unstack()

        fig = go.Figure(data=go.Heatmap(
            z=heatmap_data.values,
            x=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            y=['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            colorscale='Blues'
        ))

        fig.update_layout(title='Average Sales Heatmap (Day of Week vs Month)',
                         xaxis_title='Month', yaxis_title='Day of Week')
        return fig

    def plot_seasonal_pattern(self, df, date_col='date', sales_col='sales'):
        """Plot seasonal sales pattern"""
        monthly_sales = df.groupby(df[date_col].dt.to_period('M'))[sales_col].sum()
        monthly_sales.index = monthly_sales.index.to_timestamp()

        fig = px.line(x=monthly_sales.index, y=monthly_sales.values,
                     title='Monthly Sales Pattern')
        fig.update_layout(xaxis_title='Month', yaxis_title='Total Sales')
        return fig

    def plot_forecast_vs_actual(self, actual, forecast, dates):
        """Plot forecast vs actual values"""
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=dates, y=actual,
            mode='lines', name='Actual',
            line=dict(color='blue')
        ))

        fig.add_trace(go.Scatter(
            x=dates, y=forecast,
            mode='lines', name='Forecast',
            line=dict(color='red', dash='dash')
        ))

        fig.update_layout(
            title='Forecast vs Actual Sales',
            xaxis_title='Date',
            yaxis_title='Sales'
        )

        return fig

    def plot_inventory_status(self, inventory_df):
        """Plot inventory status distribution"""
        status_counts = inventory_df['status'].value_counts()

        fig = px.pie(values=status_counts.values, names=status_counts.index,
                    title='Inventory Status Distribution',
                    color=status_counts.index,
                    color_discrete_map={
                        'OK': 'green',
                        'LOW': 'orange',
                        'CRITICAL': 'red',
                        'EXCESS': 'blue'
                    })

        return fig

    def plot_price_distribution(self, df, price_col='sell_price'):
        """Plot price distribution"""
        fig = px.histogram(df, x=price_col, nbins=50,
                          title='Price Distribution')
        fig.update_layout(xaxis_title='Price', yaxis_title='Count')
        return fig

    def plot_correlation_heatmap(self, df, features):
        """Plot correlation heatmap for selected features"""
        corr_matrix = df[features].corr()

        fig = go.Figure(data=go.Heatmap(
            z=corr_matrix.values,
            x=features,
            y=features,
            colorscale='RdBu',
            zmid=0
        ))

        fig.update_layout(title='Feature Correlation Heatmap',
                         width=800, height=800)
        return fig

    def plot_event_impact(self, df, event_col='has_event', sales_col='sales'):
        """Plot sales comparison for events vs non-events"""
        event_sales = df.groupby(event_col)[sales_col].mean().reset_index()
        event_sales[event_col] = event_sales[event_col].map({0: 'No Event', 1: 'Event'})

        fig = px.bar(event_sales, x=event_col, y=sales_col,
                    title='Average Sales: Events vs Non-Events',
                    color=event_col)
        fig.update_layout(xaxis_title='', yaxis_title='Average Sales')
        return fig

    def create_kpi_cards(self, metrics):
        """Create KPI cards visualization"""
        fig = go.Figure()

        for i, (key, value) in enumerate(metrics.items()):
            fig.add_trace(go.Indicator(
                mode="number",
                value=value,
                title={'text': key.replace('_', ' ').title()},
                domain={'row': i // 3, 'column': i % 3}
            ))

        rows = (len(metrics) + 2) // 3
        fig.update_layout(
            grid={'rows': rows, 'columns': 3, 'pattern': 'independent'},
            height=200 * rows
        )

        return fig
