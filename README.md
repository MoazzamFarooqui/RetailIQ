# RetailIQ – AI-Powered Retail Intelligence & Inventory Optimization Platform

A comprehensive AI-powered retail analytics platform with demand forecasting, inventory optimization, explainable AI, automated business insights, and real-time business intelligence , all wrapped in an interactive Streamlit dashboard.

---

## Badges

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)
![XGBoost](https://img.shields.io/badge/XGBoost-2.0-2C5282?style=for-the-badge)
![LightGBM](https://img.shields.io/badge/LightGBM-4.3-38A169?style=for-the-badge)
![Prophet](https://img.shields.io/badge/Prophet-1.1-805AD5?style=for-the-badge)
![SHAP](https://img.shields.io/badge/SHAP-Explainable%20AI-3182CE?style=for-the-badge)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)
![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen?style=for-the-badge)

---

## Table of Contents

* [Project Overview](#project-overview)
* [Features](#features)
* [Prerequisites](#prerequisites)
* [Installation](#installation)
* [Configuration](#configuration)
* [Running the Application](#running-the-application)
* [Usage Guide](#usage-guide)
* [Screenshots](#screenshots)
* [Project Structure](#project-structure)
* [Data Pipeline](#data-pipeline)
* [API Reference](#api-reference)
* [Technologies Used](#technologies-used)
* [Contributing](#contributing)
* [Support](#support)

---

# Project Overview

Retail businesses face constant challenges in managing inventory, forecasting demand, and making data-driven decisions. Without the right tools, they rely on intuition , leading to stockouts, overstock, lost revenue, and tied-up capital.

RetailIQ solves this by providing a complete AI-powered retail intelligence platform that ingests raw sales data and runs it through a full pipeline: data validation, automated feature engineering, multi-model demand forecasting (5 competing ML models), inventory optimization (safety stock, EOQ, reorder points, stockout prediction), SHAP-based explainability, and automated natural-language business insights.

The platform is Pakistan-context aware , it understands local seasons (Spring, Summer, Monsoon, Autumn, Winter), Islamic holidays (Eid, Ramadan, Muharram), fixed Pakistan holidays (Pakistan Day, Independence Day, etc.), and adjusts demand multipliers and inventory recommendations accordingly. It also integrates live weather data via OpenWeatherMap for real-time context-aware forecasting.

Built entirely with Python, Streamlit, and open-source ML libraries, RetailIQ runs on any machine with a single command: `streamlit run app.py`.

---

# Features

### Data Upload & Auto-Processing
* Upload your own retail sales CSV
* Auto-validate column structure and data quality
* Auto-clean missing values, fix data types, remove duplicates
* Append to existing historical data
* SQLite database stores all uploads, forecasts, and inventory history

### AI Demand Forecasting
* 5 competing ML models: Baseline, Random Forest, XGBoost, LightGBM, Prophet
* One-click model comparison (MAE, RMSE, MAPE, R²)
* Auto-selects and saves the best-performing model
* Preset horizons: 7 days, 30 days, 90 days
* Autoregressive forecasting based on today's date & data

### Live Context Integration
* Weather API: Real-time temperature, conditions, 5-day forecast
* Holiday API: Holiday-aware forecasting with built-in Pakistan holiday fallback
* Uses current date for all forecasting calculations

### Inventory Optimization
* Safety Stock calculation (Z-score × demand variability × √Lead Time)
* Reorder Point with lead time adjustment
* EOQ (Economic Order Quantity)
* Stockout Prediction , predicts exactly when stock will run out
* Overstock Detection , identifies items tying up capital
* Low-Stock Alerts with severity levels (OK / LOW / CRITICAL / EXCESS)
* Demand Multipliers , automatically adjusts for peak seasons & holidays
* Seasonal Product Alerts , flags in/out-of-season items

### Explainable AI (SHAP)
* Global feature importance rankings
* SHAP summary plot (feature impact distribution)
* Individual prediction explanations (waterfall plots)
* Force plot visualizations
* Feature dependency analysis

### Business Intelligence
* Sales trend analysis (daily, seasonal, yearly)
* Product, store, and category performance rankings
* Revenue analysis (sales × price)
* Seasonal trend analysis across 5 Pakistan seasons
* Holiday impact analysis (holiday vs. regular day sales)
* Day-of-week sales patterns

### AI-Generated Business Insights
* Automated natural-language insights about your data
* Seasonal demand advice with product-level recommendations
* Weather impact analysis (temperature vs. sales correlation)
* Holiday stock-up calendar with countdown timers
* Recommended actions (weekend promos, seasonal prep, diversification, etc.)
* Data Health Score (0–100) with specific improvement suggestions
* Pre-Ramadan and pre-Eid shopping window detection

### Reports & Export
* CSV export on every dashboard page
* PDF report generation (with fpdf2) , forecast, inventory, and model insights
* Combined summary reports with metrics and visualizations

---

# Prerequisites

* Python 3.10 or higher
* pip (Python package installer)
* OpenWeatherMap API key (optional , for live weather data)
* Calendarific API key (optional , for live holiday data)

---

# Installation

### Clone the repository

```bash
git clone https://github.com/MoazzamFarooqui/RetailIQ.git
cd RetailIQ
```

### Install dependencies using pip

```bash
pip install -r requirements.txt
```

### Or install with uv (fast alternative)

Linux/macOS

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows PowerShell

```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

```bash
uv sync
```

---

# Configuration

### Environment Variables (Optional)

Create a `.env` file in the project root:

```env
# Weather data (free tier: https://openweathermap.org/api)
OPENWEATHER_API_KEY=your_key_here

# Holiday data (free tier: https://calendarific.com)
HOLIDAY_API_KEY=your_key_here
```

Without these API keys, the system falls back to built-in US holidays, Pakistan-specific Islamic holiday tables (2024–2028), fixed Pakistan holidays, and seasonal defaults , the platform is fully functional offline.

### Dataset

RetailIQ ships with the M5 Walmart retail dataset (30,490 products × 1,941 days) for immediate exploration. You can upload your own retail sales CSV at any time via the Upload Data tab.

---

# Running the Application

Start the Streamlit application:

```bash
streamlit run app.py
```

Open your browser and visit:

```text
http://localhost:8501
```

---

# Usage Guide

### Dashboard (Home)

* View live KPIs: total products, stores, categories, states
* Check today's weather, season, and holiday at a glance
* Monitor recent uploads and model training history
* See pre-holiday alerts and extreme weather warnings
* Navigate to any module via the platform capability cards

### Upload Data

* Upload a retail sales CSV file
* The system auto-validates required columns (`date`, `sales`, `item_id`, `store_id`)
* Auto-cleans missing values, fixes data types, caps negative sales
* Preview cleaned data before saving
* Append to historical database with one click

### Train Model

* Configure training parameters (sample size, test split)
* Select which models to train (Baseline, Random Forest, XGBoost, LightGBM, Prophet)
* One-click training of all selected models
* View side-by-side comparison table (MAE, RMSE, MAPE, R²)
* Best model is automatically saved to `models/best_model.joblib`

### Analytics

* Filter by store, category, season, and date range
* View daily sales and revenue trends over time
* Analyze sales across 5 Pakistan seasons with color-coded visualizations
* Compare holiday vs. regular day sales performance
* Drill into store performance by season
* Explore category × season cross-analysis
* View top 20 products by volume and revenue
* Analyze day-of-week sales patterns
* Export filtered analytics as CSV

### Forecast

* Select a specific product and store combination
* View live weather and holiday context
* See 90-day historical trend for context
* Generate 7, 30, or 90-day demand forecast
* Interactive chart with historical vs. predicted overlay
* View forecast KPIs (total, average, change %, peak day)
* Check weather forecast for the period (hot/rainy/cold day alerts)
* Review holidays in the forecast period with stock advice
* Get integrated inventory recommendations (safety stock, reorder point, EOQ, stockout date)
* Export forecast as CSV or PDF report

### Inventory

* Configurable service level (80%–99%), lead time, and excess threshold
* View inventory KPIs (total items, healthy %, at-risk %, overstock %)
* Analyze inventory status distribution (pie chart + bar chart)
* Stockout Predictions , items sorted by days until stockout, with critical alerts
* Overstock Detection , items flagged with excess units and days of stock
* Critical & Low-Stock Items , items needing immediate reorder
* Recommended Actions , total units to order, average order size
* Filterable recommendations table
* Export full report as CSV or PDF

### Model Insights

* View current model information (type, features, estimators)
* Compare all trained models side-by-side with metrics
* Visualize model comparison with bar charts
* View Feature Importance , top 20 features ranked
* Generate SHAP Analysis , summary plot showing feature impact
* Explain Individual Predictions , pick any data point, see waterfall plot with per-feature contributions
* Export model comparison as CSV

### AI Insights

* Live context: today's date, weather, season, and upcoming holidays
* Seasonal Demand Analysis , current season advice, high/low-demand products
* Weather Impact , temperature vs. sales scatter plot with trendline
* AI-Generated Insights , categorized automatically (Summary, Trends, Seasonality, Products, Stores, Revenue, Data Quality)
* Recommended Actions , actionable business recommendations with explanations
* Holiday Stock-Up Calendar , countdown to upcoming holidays with priority levels and specific product suggestions
* Data Health Score , 0–100 rating with itemized deductions and improvement suggestions
* Export insights as text or CSV

---

# Screenshots

## Dashboard , Live KPIs & Context

*[Add screenshot of the Home dashboard with weather, holiday, and KPI cards]*

## Upload & Auto-Clean

*[Add screenshot of the CSV upload page with validation results]*

## Model Training & Comparison

*[Add screenshot of the training results with 5-model comparison table and charts]*

## Sales & Revenue Analytics

*[Add screenshot of analytics page with trend charts, season analysis, and category breakdowns]*

## AI Demand Forecasting

*[Add screenshot of the forecast page with historical vs. predicted overlay and inventory integration]*

## Inventory Optimization

*[Add screenshot of inventory KPIs, stockout predictions, and overstock detection]*

## SHAP Explainability

*[Add screenshot of SHAP summary plot and individual prediction waterfall]*

## AI Business Insights

*[Add screenshot of generated insights, recommendations, and data health score]*

---

# Project Structure

```
RetailIQ/
│
├── app.py                              # Main Streamlit entry point (Home, Upload, Train tabs)
├── README.md                           # Project documentation
├── requirements.txt                    # Python package dependencies
├── .env                                # API keys (not tracked in git)
├── .gitignore                          # Git exclusion rules
│
├── pages/                              # Streamlit multi-page application
│   ├── Analytics.py                    # Sales & revenue analytics with season/holiday context
│   ├── Forecast.py                     # 7/30/90-day demand forecasting with live context
│   ├── Inventory.py                    # Inventory optimization & stockout/overstock detection
│   ├── Model_Insights.py               # SHAP analysis, feature importance, model comparison
│   └── AI_Insights.py                  # Automated business insights & recommendations
│
├── src/                                # Core Python modules
│   ├── __init__.py                     # Package initializer
│   ├── data_loader.py                  # M5 retail dataset loader (calendar, sales, prices)
│   ├── preprocessing.py                # Data cleaning, melting, merging, label encoding
│   ├── feature_engineering.py          # 36+ time/lag/rolling/price/season/holiday features
│   ├── forecasting.py                  # 5 ML models: Baseline, RF, XGBoost, LightGBM, Prophet
│   ├── inventory_optimizer.py          # Safety stock, EOQ, reorder point, stockout prediction
│   ├── explainability.py               # SHAP analysis (summary, waterfall, force plots)
│   ├── visualization.py                # Plotly/Matplotlib chart generators
│   ├── upload_service.py               # CSV validation & auto-cleaning pipeline
│   ├── database.py                     # SQLite storage layer (7 tables, full CRUD)
│   ├── insights_engine.py              # AI-generated business insights & recommendations
│   ├── weather_service.py              # OpenWeatherMap API + Pakistan season definitions
│   ├── holiday_service.py              # Pakistan holidays (Islamic + fixed) + pre-holiday windows
│   ├── report_generator.py             # CSV & PDF report export (fpdf2)
│   └── utils.py                        # Helpers: load/save, metrics, memory reduction
│
├── assets/
│   └── custom.css                      # Professional dashboard CSS theme (500+ lines)
│
├── data/
│   ├── raw/                            # Original M5 Walmart dataset
│   │   ├── calendar.csv                # Date metadata (1,969 rows)
│   │   ├── sales_train_evaluation.csv  # Sales data (30,490 products × 1,941 days)
│   │   └── sell_prices.csv             # Product pricing (6.8M records)
│   ├── processed/                      # Cleaned & feature-engineered data (auto-generated)
│   └── retailiq.db                     # SQLite database (auto-created on first run)
│
├── models/
│   └── best_model.joblib               # Trained RandomForestRegressor (36 features)
│
├── notebooks/                          # Jupyter notebooks for exploration
│   ├── 01_Data_Understanding.ipynb     # Explore raw data structure
│   ├── 02_EDA.ipynb                    # Visual analysis & patterns
│   ├── 03_Data_Cleaning.ipynb          # Missing values, types, duplicates
│   ├── 04_Feature_Engineering.ipynb    # Time/lag/rolling/price features
│   ├── 05_Model_Training.ipynb         # All 5 models training & comparison
│   ├── 06_Model_Evaluation.ipynb       # Performance diagnostics
│   └── 07_SHAP_Analysis.ipynb          # Model interpretability
│
├── reports/
│   ├── exports/                        # Generated reports (CSV, PDF, Excel)
│   └── figures/                        # Generated figures (PNG)
```

---

# Data Pipeline

RetailIQ processes data through a structured pipeline with five major stages:

### 1. Ingestion & Validation
```
Upload CSV → DataValidator.validate_csv() → Column check → Data quality report
```

### 2. Cleaning & Storage
```
Auto-clean (missing values, types, duplicates) → Save to SQLite → Save to data/processed/
```

### 3. Feature Engineering
```
Load cleaned data → FeatureEngineer.create_all_features()
  ├── Time features (year, month, day, dayofweek, is_weekend)
  ├── Cyclical encoding (sin/cos of month, day)
  ├── Pakistan seasons (Spring, Summer, Monsoon, Autumn, Winter)
  ├── Holiday features (is_holiday, days_to_holiday, pre-Ramadan/Eid windows)
  ├── Weather features (temp, humidity, rain flags, weather × season interactions)
  ├── Lag features (1, 7, 14, 28 days)
  ├── Rolling statistics (7, 14, 28 day means + stds)
  ├── Price features (change, momentum, price_rank)
  └── Event & SNAP features
```

### 4. Model Training & Forecasting
```
Train 5 models → Compare metrics (MAE, RMSE, MAPE, R²) → Select best → Save
Autoregressive forecast → 7/30/90 day horizon → Store in SQLite
```

### 5. Inventory & Insights
```
Forecast → InventoryOptimizer (safety stock, EOQ, reorder, stockout, overstock)
Data → InsightsEngine → NL insights, recommendations, health score
```

### Database Schema (SQLite)

| Table | Purpose |
|-------|---------|
| `uploaded_datasets` | Raw upload metadata and contents |
| `cleaned_datasets` | Auto-cleaned version of each upload |
| `forecasts` | Individual forecast records |
| `forecast_headers` | Forecast session metadata |
| `inventory_recommendations` | Per-item inventory calculations |
| `model_history` | Training runs and metrics |
| `business_insights` | Generated insight text and categories |

---

# API Reference

### OpenWeatherMap 

RetailIQ integrates with the OpenWeatherMap API for live weather data:

| Endpoint | Usage | Frequency |
|----------|-------|-----------|
| Current Weather | Fetch temperature, conditions, humidity, wind | On dashboard load |
| 5-Day Forecast | Weather forecast for the prediction period | On forecast generation |

Free Tier: 1,000 calls/day , sufficient for standard usage.
Fallback: Returns seasonal defaults when API key is not configured.

### Calendarific 

| Endpoint | Usage | Frequency |
|----------|-------|-----------|
| Holidays API | Fetch national and religious holidays | On application start |

Fallback: Built-in Islamic holiday tables (2024–2028) and fixed Pakistan holidays (Pakistan Day, Independence Day, Iqbal Day, Quaid-e-Azam Day, etc.) , fully functional offline.

---

# Technologies Used

### Frontend & Visualization
* Streamlit , Interactive web application framework
* Plotly , Interactive charts and graphs
* Matplotlib , Static visualization and publication-quality figures
* Seaborn , Statistical data visualization

### Machine Learning
* scikit-learn , Random Forest, feature preprocessing, metrics
* XGBoost , Gradient boosting with extreme gradient boosting
* LightGBM , Gradient boosting with leaf-wise tree growth
* Prophet , Facebook's time-series forecasting model

### Explainability
* SHAP , SHapley Additive exPlanations for model interpretability

### Data Processing & Storage
* Pandas , Data manipulation and analysis
* NumPy , Numerical computing
* SciPy , Scientific computing (statistical functions)
* Statsmodels , Statistical modeling
* SQLite , Lightweight embedded database
* Joblib , Model serialization and persistence

### External APIs
* OpenWeatherMap , Live weather data and forecasts
* Calendarific , National and religious holiday data

### Reporting
* fpdf2 , PDF report generation

---

# Contributing

Contributions are welcome! Here's how you can help improve RetailIQ:

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/amazing-feature`).
3. Make your changes.
4. Test the application thoroughly.
5. Commit your changes (`git commit -m 'Add amazing feature'`).
6. Push to the branch (`git push origin feature/amazing-feature`).
7. Open a Pull Request.

### Development Ideas

* Add additional forecasting models (ARIMA, LSTM, Transformer)
* Implement multi-warehouse inventory support
* Add user authentication and multi-tenant support
* Integrate with real POS systems via API
* Add email/SMS alerting for stockout predictions
* Support for PostgreSQL/MySQL as an alternative database backend
* Add comparative analysis across multiple stores/chains
* Implement A/B testing for promotional effectiveness

---

# Support

If you encounter any issues, have feature requests, or need assistance:

* Open an issue in this repository
* Check the existing documentation in the `notebooks/` directory for detailed walkthroughs
* Review the source code , each module has clear documentation and type hints

---

