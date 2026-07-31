# RetailIQ – AI-Powered Retail Intelligence & Inventory Optimization Platform

A comprehensive AI-powered retail analytics platform with demand forecasting, inventory optimization, explainable AI, automated business insights, and real-time business intelligence — wrapped in a modern **React + FastAPI** web application, fully containerized with **Docker Compose**.

---

## Badges

![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-5-646CFF?style=for-the-badge&logo=vite&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?style=for-the-badge&logo=mysql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-FF4438?style=for-the-badge&logo=redis&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-5.3-37814A?style=for-the-badge&logo=celery&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-24.0-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![XGBoost](https://img.shields.io/badge/XGBoost-2.0-2C5282?style=for-the-badge)
![LightGBM](https://img.shields.io/badge/LightGBM-4.3-38A169?style=for-the-badge)
![Prophet](https://img.shields.io/badge/Prophet-1.1-805AD5?style=for-the-badge)
![SHAP](https://img.shields.io/badge/SHAP-Explainable%20AI-3182CE?style=for-the-badge)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)

---

## Table of Contents

* [Project Overview](#project-overview)
* [Features](#features)
* [Architecture](#architecture)
* [Prerequisites](#prerequisites)
* [Installation](#installation)
* [Configuration](#configuration)
* [Running the Application](#running-the-application)
* [Usage Guide](#usage-guide)
* [Project Structure](#project-structure)
* [Data Pipeline](#data-pipeline)
* [API Reference](#api-reference)
* [Celery Tasks](#celery-tasks)
* [Troubleshooting](#troubleshooting)
* [Technologies Used](#technologies-used)
* [Contributing](#contributing)
* [Support](#support)

---

# Project Overview

Retail businesses face constant challenges in managing inventory, forecasting demand, and making data-driven decisions. Without the right tools, they rely on intuition, leading to stockouts, overstock, lost revenue, and tied-up capital.

RetailIQ solves this by providing a complete AI-powered retail intelligence platform that ingests raw sales data and runs it through a full pipeline: data validation, automated feature engineering, multi-model demand forecasting (5 competing ML models), inventory optimization (safety stock, EOQ, reorder points, stockout prediction), SHAP-based explainability, and automated natural-language business insights.

The platform is **Pakistan-context aware**: it understands local seasons (Spring, Summer, Monsoon, Autumn, Winter), Islamic holidays (Eid, Ramadan, Muharram), and fixed Pakistan holidays (Pakistan Day, Independence Day, etc.), and adjusts demand multipliers and inventory recommendations accordingly. It also integrates live weather data via OpenWeatherMap for real-time context-aware forecasting.

The platform is built as a modern two-tier web application:

| Tier | Tech | Role |
|------|------|------|
| **Frontend** | React 18 + Vite + Tailwind CSS + Recharts | Interactive SPA dashboard |
| **Backend** | FastAPI + SQLAlchemy (async) + Celery + Redis | REST API, ML pipeline, background jobs |
| **Database** | MySQL 8.0 | Persistent relational storage |
| **Cache / Broker** | Redis 7 | Caching + Celery message broker |
| **Deployment** | Docker Compose | Single-command full-stack startup |

---

# Features

### Data Upload & Auto-Processing
* Upload your own retail sales CSV
* Auto-validate column structure and data quality
* Auto-clean missing values, fix data types, remove duplicates
* Append to existing historical data
* MySQL database stores all uploads, forecasts, and inventory history

### AI Demand Forecasting
* 5 competing ML models: Baseline, Random Forest, XGBoost, LightGBM, Prophet
* One-click model comparison (MAE, RMSE, MAPE, R²)
* Auto-selects and saves the best-performing model
* Preset horizons: 7 days, 30 days, 90 days
* Autoregressive forecasting based on today's date & data
* Async training via Celery worker with live progress tracking

### Live Context Integration
* Weather API: Real-time temperature, conditions, 5-day forecast
* Holiday API: Holiday-aware forecasting with built-in Pakistan holiday fallback
* Uses current date for all forecasting calculations

### Inventory Optimization
* Safety Stock calculation (Z-score × demand variability × √Lead Time)
* Reorder Point with lead time adjustment
* EOQ (Economic Order Quantity)
* Stockout Prediction — predicts exactly when stock will run out
* Overstock Detection — identifies items tying up capital
* Low-Stock Alerts with severity levels (OK / LOW / CRITICAL / EXCESS)
* Demand Multipliers — automatically adjusts for peak seasons & holidays
* Seasonal Product Alerts — flags in/out-of-season items

### Explainable AI (SHAP)
* Global feature importance rankings
* SHAP summary plot (feature impact distribution)
* Individual prediction explanations
* Feature dependency analysis

### Business Intelligence (Analytics Dashboard)
* Sales trend analysis (daily, seasonal, yearly)
* Product, store, and category performance rankings
* Day-of-week sales patterns
* Seasonal trend analysis across 5 Pakistan seasons
* Interactive charts (Recharts): line, bar, pie, KPI cards
* Date-range selector (30/90/180 days)

### AI-Generated Business Insights
* Automated natural-language insights about your data
* Seasonal demand advice with product-level recommendations
* Weather impact analysis (temperature vs. sales correlation)
* Holiday stock-up calendar with countdown timers
* Recommended actions (weekend promos, seasonal prep, diversification, etc.)
* Data Health Score (0–100) with specific improvement suggestions

### Reports & Export
* CSV export on every dashboard page
* PDF report generation (with fpdf2) — forecast, inventory, and model insights
* Combined summary reports with metrics and visualizations

### Operational Infrastructure
* **JWT authentication** (login, register, refresh tokens) with role-based access (admin/analyst)
* **Celery worker + beat** for background training and scheduled daily insight generation
* **Redis caching** layer for weather/holiday lookups and frequent queries
* **Container healthchecks** on every service

---

# Architecture

```
                         ┌──────────────────────────────────────────┐
                         │              Browser (SPA)               │
                         │    React 18 + Vite + Tailwind + Recharts │
                         └──────────────────┬───────────────────────┘
                                            │  HTTP :3000
                                            ▼
                         ┌──────────────────────────────────────────┐
                         │          Nginx (client container)        │
                         │        proxies /api → FastAPI :8000      │
                         └──────────────────┬───────────────────────┘
                                            │  HTTP :8000
                                            ▼
                    ┌───────────────────────────────────────────────────┐
                    │            FastAPI Backend (uvicorn)              │
                    │  /api/v1/auth · analytics · forecast · inventory  │
                    │  /api/v1/model · insights · upload · weather      │
                    └───────┬──────────────────────┬────────────────────┘
                            │                      │
                    ┌───────▼────────┐    ┌────────▼─────────┐
                    │   MySQL 8.0    │    │     Redis 7      │
                    │  relational DB │    │ cache + broker   │
                    └────────────────┘    └────────┬─────────┘
                                                   │
                              ┌────────────────────┴─────────────┐
                              │  Celery Worker        Celery Beat │
                              │  async training   scheduled jobs │
                              └──────────────────────────────────┘
```

### Container topology (`docker-compose.yml`)

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| `api` | `retailiq-api` | 8000 → 8000 | FastAPI backend |
| `client` | `retailiq-client` | 3000 → 80 | React SPA served by Nginx |
| `db` | `retailiq-db` | 3307 → 3306 | MySQL 8.0 |
| `redis` | `retailiq-redis` | 6379 → 6379 | Cache + Celery broker |
| `celery-worker` | `retailiq-celery-worker` | — | Async ML training |
| `celery-beat` | `retailiq-celery-beat` | — | Scheduled tasks (daily insights) |

---

# Prerequisites

* **Docker Desktop** (or Docker Engine + Compose v2) — Windows/macOS/Linux
* **Git** (optional, for cloning)
* **~4 GB free RAM** and ~10 GB free disk for images and data

No Python/Node installation needed — everything runs inside containers.

---

# Installation

### 1. Clone the repository

```bash
git clone https://github.com/MoazzamFarooqui/RetailIQ.git
cd RetailIQ
```

### 2. Configure environment (optional)

Copy the example file and add your API keys if you have them:

```bash
cp .env.example .env
```

### 3. Start the stack

```bash
docker compose up -d --build
```

The first build downloads base images and installs dependencies (Python ML packages + Node modules) — allow 10–20 minutes. Subsequent starts take seconds.

### 4. Verify

```bash
docker compose ps
```

All six containers should report `healthy` / `Up`.

---

# Configuration

### Environment Variables

Create a `.env` file in the project root (see `.env.example`):

```env
# ── Application ────────────────────────────────────────────────
APP_NAME=RetailIQ API
APP_VERSION=2.0.0
ENVIRONMENT=development
DEBUG=true

# ── Database ──────────────────────────────────────────────────
# For Docker Compose (internal network):
DATABASE_URL=mysql+aiomysql://retailiq:retailiq@db:3306/retailiq
# For local development (SQLite, no Docker):
# DATABASE_URL=sqlite+aiosqlite:///data/retailiq_v2.db

# ── Redis ─────────────────────────────────────────────────────
# For Docker Compose:
REDIS_URL=redis://redis:6379/0
# For local development:
# REDIS_URL=redis://localhost:6379/0

# ── JWT Authentication ────────────────────────────────────────
SECRET_KEY=change-this-to-a-long-random-string-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# ── API Keys (optional — app falls back gracefully) ───────────
# Weather data (free tier: https://openweathermap.org/api)
OPENWEATHER_API_KEY=your_key_here
# Holiday data (free tier: https://calendarific.com)
HOLIDAY_API_KEY=your_key_here

# ── Celery ────────────────────────────────────────────────────
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/1

# ── CORS ──────────────────────────────────────────────────────
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173","http://localhost:8000"]
```

> **Note:** in Docker, `docker-compose.yml` overrides `DATABASE_URL` with `mysql+aiomysql://retailiq:retailiq@db:3306/retailiq` so the backend always uses the containerized MySQL. Without API keys the platform falls back to built-in Pakistan Islamic holiday tables (2024–2028) and seasonal defaults — fully functional offline.

### Dataset

RetailIQ ships with the **M5 Walmart retail dataset** (30,490 products × 1,941 days) in `data/raw/`. A subsample (3 stores, full 2011–2016 range) is pre-processed into `data/processed/engineered_features.csv` plus compact analytics aggregates. You can upload your own retail sales CSV at any time via the Upload page.

---

# Running the Application

### Quick start

```bash
docker compose up -d
```

### Open the app

| What | URL |
|------|-----|
| **Frontend (main app)** | http://localhost:3000 |
| API interactive docs (Swagger) | http://localhost:8000/docs |
| API health check | http://localhost:8000/health |

### Default credentials

| Username | Password | Role |
|----------|----------|------|
| `admin` | `admin123` | Administrator |

### Everyday commands

| Action | Command |
|--------|---------|
| Start everything | `docker compose up -d` |
| Stop everything | `docker compose down` |
| Restart the API | `docker restart retailiq-api` |
| Rebuild backend image | `docker compose up -d --build api` |
| Rebuild frontend image | `docker compose up -d --build client` |
| View logs (all) | `docker compose logs -f` |
| View logs (API) | `docker logs retailiq-api -f` |
| Check status | `docker compose ps` |

---

# Usage Guide

### Dashboard (Home)
* View live KPIs: total sales, average daily sales, products, stores
* One-click navigation to every module via the sidebar

### Upload
* Upload a retail sales CSV file
* The system auto-validates required columns (`date`, `sales`, `item_id`, `store_id`)
* Auto-cleans missing values, fixes data types, caps negative sales
* Preview cleaned data before saving
* Append to historical database with one click

### Train Model
* Configure training parameters (sample size, test split)
* Select which models to train (Baseline, Random Forest, XGBoost, LightGBM, Prophet)
* One-click training — runs **asynchronously** via Celery with progress tracking
* View side-by-side comparison table (MAE, RMSE, MAPE, R²)
* Best model is automatically saved to `models/best_model.joblib`

### Analytics
* KPI row: total sales, average daily, product and store counts
* Sales trend over 30/90/180 days (interactive line chart)
* Top 10 products by revenue (bar chart)
* Store performance comparison table
* Day-of-week sales pattern with peak % (all 7 days)
* Seasonal breakdown across the 5 Pakistan seasons (pie chart)

### Forecast
* Select a specific product and store combination
* View live weather and holiday context
* Generate 7, 30, or 90-day demand forecast
* Interactive chart with historical vs. predicted overlay
* View forecast KPIs (total, average, change %, peak day)
* Check holidays in the forecast period with stock advice
* Get integrated inventory recommendations (safety stock, reorder point, EOQ, stockout date)
* Export forecast as CSV or PDF report

### Inventory
* Configurable service level (80%–99%), lead time, and excess threshold
* View inventory KPIs (total items, healthy %, at-risk %, overstock %)
* Stockout predictions — items sorted by days until stockout, with critical alerts
* Overstock detection — items flagged with excess units and days of stock
* Critical & low-stock items — items needing immediate reorder
* Recommended actions — total units to order, average order size
* Filterable recommendations table
* Export full report as CSV or PDF

### Model Insights
* View current model information (type, features, estimators)
* Compare all trained models side-by-side with metrics
* View feature importance — top features ranked
* Generate SHAP analysis — summary plot showing feature impact
* Explain individual predictions — pick any data point, see per-feature contributions
* Export model comparison as CSV

### AI Insights
* Live context: today's date, weather, season, and upcoming holidays
* Seasonal demand analysis — current season advice, high/low-demand products
* Weather impact — temperature vs. sales analysis
* AI-generated insights — categorized (Summary, Trends, Seasonality, Products, Stores, Revenue, Data Quality)
* Recommended actions — actionable recommendations with explanations
* Holiday stock-up calendar — countdown to upcoming holidays with priority levels
* Data health score — 0–100 rating with itemized deductions and improvement suggestions
* Export insights as text or CSV

---

# Project Structure

```
RetailIQ/
│
├── docker-compose.yml               # Full-stack orchestration (6 services)
├── README.md                        # Project documentation
├── .env / .env.example              # Environment configuration
│
├── backend/                         # FastAPI backend (bind-mounted into containers)
│   ├── Dockerfile                   # Multi-stage Python 3.12 image
│   ├── requirements.txt             # Python dependencies
│   ├── alembic/                     # DB migration scaffolding
│   ├── scripts/
│   │   ├── regenerate_engineered_data.py      # Rebuild engineered_features.csv from raw M5
│   │   └── regenerate_analytics_aggregates.py # Rebuild compact analytics aggregates
│   ├── tests/                       # Pytest suite
│   └── app/
│       ├── main.py                  # FastAPI app factory + lifespan
│       ├── core/                    # config, database, security, cache, dependencies
│       ├── models/                  # SQLAlchemy ORM models (7 tables)
│       ├── schemas/                 # Pydantic request/response schemas
│       ├── api/v1/endpoints/        # auth, users, upload, forecast, inventory,
│       │                            # analytics, model, insights, weather
│       ├── services/                # forecasting, inventory_optimizer, feature_engineering,
│       │                            # explainability, insights_engine, weather, holiday, report
│       └── tasks/                   # Celery app, training/forecast/report tasks
│
├── client/                          # React 18 SPA
│   ├── Dockerfile                   # Multi-stage: Vite build → Nginx serve
│   ├── nginx.conf                   # SPA + /api proxy to backend
│   ├── package.json
│   └── src/
│       ├── main.jsx / App.jsx       # Entry + routing
│       ├── services/                # API client (axios)
│       ├── contexts/AuthContext.jsx # JWT auth state
│       ├── components/              # Layout, KpiCard, LoadingState, StatusBadge
│       └── pages/                   # Dashboard, Analytics, Forecast, Inventory,
│                                    # ModelInsights, AIInsights, Upload, Login
│
├── data/                            # Mounted into containers
│   ├── raw/                         # Original M5 Walmart dataset
│   │   ├── calendar.csv             # Date metadata (1,969 rows)
│   │   ├── sales_train_evaluation.csv # Sales (30,490 products × 1,941 days)
│   │   └── sell_prices.csv          # Product pricing (6.8M records)
│   └── processed/                   # Auto-generated
│       ├── engineered_features.csv  # Long-format feature frame (subsampled stores)
│       ├── analytics_daily.csv      # Compact daily aggregates (analytics API)
│       ├── analytics_products.csv   # Per-product totals (analytics API)
│       ├── analytics_meta.json      # Overview metrics (analytics API)
│       └── backup/                  # Safety backups of previous generated files
│
├── models/
│   └── best_model.joblib            # Trained best model (auto-generated)
│
└── reports/
    ├── exports/                     # Generated reports (CSV, PDF)
    └── figures/                     # Generated figures (PNG)
```

---

# Data Pipeline

RetailIQ processes data through a structured pipeline with five major stages:

### 1. Ingestion & Validation
```
Upload CSV → validation (date, sales, item_id, store_id) → data quality report
```

### 2. Cleaning & Storage
```
Auto-clean (missing values, types, duplicates) → Save to MySQL → Save to data/processed/
```

### 3. Feature Engineering
```
Load cleaned data → FeatureEngineer.create_all_features()
  ├── Time features (year, month, day, dayofweek, is_weekend)
  ├── Cyclical encoding (sin/cos of month, day-of-week, day-of-year)
  ├── Pakistan seasons (Spring, Summer, Monsoon, Autumn, Winter)
  ├── Holiday features (is_holiday, days_to_holiday, pre-Ramadan/Eid windows)
  ├── Weather features (temp, humidity, rain flags, weather × season interactions)
  ├── Lag features (1, 7, 14, 28 days)
  ├── Rolling statistics (7, 14, 28 day means + stds)
  ├── Price features (change, momentum, price vs average)
  └── Event & SNAP features
```

### 4. Model Training & Forecasting
```
Train 5 models → Compare metrics (MAE, RMSE, MAPE, R²) → Select best → Save
Autoregressive forecast → 7/30/90 day horizon → Store in MySQL
(Async via Celery worker; scheduled daily insights via Celery beat)
```

### 5. Inventory & Insights
```
Forecast → InventoryOptimizer (safety stock, EOQ, reorder, stockout, overstock)
Data → InsightsEngine → NL insights, recommendations, health score
```

### Data regeneration scripts

The analytics endpoints read compact aggregate files (`analytics_daily.csv`, `analytics_products.csv`, `analytics_meta.json`) rather than the full engineered frame (which can reach hundreds of MB). Regenerate them after any raw-data change:

```bash
# 1. Rebuild the long-format engineered frame from data/raw/ (3 stores by default)
python backend/scripts/regenerate_engineered_data.py --stores CA_1,TX_2,WI_3

# 2. Rebuild the compact analytics aggregates
python backend/scripts/regenerate_analytics_aggregates.py
```

### Database Schema (MySQL)

| Table | Purpose |
|-------|---------|
| `users` | Users, roles (admin/analyst), password hashes |
| `datasets` | Upload metadata |
| `forecast_headers` | Forecast session metadata |
| `forecasts` | Individual forecast records |
| `inventory_recommendations` | Per-item inventory calculations |
| `model_history` | Training runs and metrics |
| `business_insights` | Generated insight text and categories |

---

# API Reference

Base URL: `http://localhost:8000` — interactive docs at `/docs` (Swagger UI).

All endpoints except `/auth/register` and `/auth/login` require an `Authorization: Bearer <token>` header.

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register a new user (role: analyst) |
| POST | `/api/v1/auth/login` | Login, returns JWT access + refresh tokens |
| POST | `/api/v1/auth/refresh` | Refresh an expired access token |

### Analytics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/analytics/overview` | KPI overview metrics |
| GET | `/api/v1/analytics/sales-trend?days=90` | Daily sales trend (last N days) |
| GET | `/api/v1/analytics/top-products?limit=10` | Top-selling products |
| GET | `/api/v1/analytics/store-performance` | Per-store sales comparison |
| GET | `/api/v1/analytics/seasonal` | Sales by Pakistan season |
| GET | `/api/v1/analytics/day-of-week` | Sales by day of week |

### Forecast & Model

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/forecast/generate` | Generate forecast (item, store, horizon) |
| GET | `/api/v1/forecast/history` | Forecast history |
| POST | `/api/v1/model/train` | Train all models (sync or async via Celery) |
| GET | `/api/v1/model/history` | Model training history |
| GET | `/api/v1/model/compare` | Model comparison metrics |
| GET | `/api/v1/model/features` | Feature importance |

### Inventory & Insights

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/inventory/recommendations` | Inventory recommendations |
| POST | `/api/v1/inventory/optimize` | Run inventory optimization |
| GET | `/api/v1/insights/recent` | Recent generated insights |
| POST | `/api/v1/insights/generate` | Generate new insights |

### Upload & Weather

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/upload` | Upload a sales CSV (multipart) |
| GET | `/api/v1/weather/current` | Current weather (with fallback) |
| GET | `/api/v1/weather/forecast` | 5-day weather forecast |

### External API integrations

**OpenWeatherMap** — live weather data for context-aware forecasting:

| Endpoint | Usage | Frequency |
|----------|-------|-----------|
| Current Weather | Fetch temperature, conditions, humidity, wind | On dashboard load |
| 5-Day Forecast | Weather forecast for the prediction period | On forecast generation |

Free Tier: 1,000 calls/day. Fallback: seasonal defaults when no API key.

**Calendarific** — national and religious holidays:

| Endpoint | Usage | Frequency |
|----------|-------|-----------|
| Holidays API | Fetch national and religious holidays | On application start |

Fallback: built-in Islamic holiday tables (2024–2028) and fixed Pakistan holidays — fully functional offline.

---

# Celery Tasks

Background jobs run on the `celery-worker` container, with the scheduler (`celery-beat`) triggering periodic work.

| Task | Schedule | Description |
|------|----------|-------------|
| `app.tasks.training_tasks.train_all_models_task` | On demand | Trains all 5 models, saves the best |
| `app.tasks.forecast_tasks.*` | On demand | Forecast generation jobs |
| `app.tasks.training_tasks.generate_daily_insights` | **Daily** | Generates automated business insights |
| `app.tasks.report_tasks.*` | On demand | PDF/CSV report generation |

Broker/result backend: Redis (database 1). Task time limit: 1 hour.

---

# Troubleshooting

### API container keeps restarting (`Exited (3)`)

Check the logs for the underlying error:

```bash
docker logs retailiq-api --tail 100
```

Historically resolved issues:
* **`ping() missing 1 required positional argument: 'reconnect'`** — caused by `aiomysql 0.2.0` / `PyMySQL ≥1.1` signature changes vs. SQLAlchemy's pool pre-ping. Fixed by pinning `sqlalchemy[asyncio]==2.0.31` and `PyMySQL==1.0.3` in `backend/requirements.txt`.
* **`Field "model_type" has conflict with protected namespace "model_"`** — Pydantic v2 warning; silenced via `model_config = {"protected_namespaces": ()}` on the schemas.

### Analytics page shows an error or empty charts

* The API needs `data/processed/analytics_daily.csv`, `analytics_products.csv` and `analytics_meta.json`. Regenerate them:

```bash
python backend/scripts/regenerate_analytics_aggregates.py
```

* Then hard-refresh the browser (Ctrl+F5) to load the rebuilt frontend bundle.

### Frontend changes don't appear

The client is a static build inside the image. After changing `client/src/*`:

```bash
docker compose up -d --build client
```

### Backend changes don't appear

`./backend` is bind-mounted, so after editing Python files just restart:

```bash
docker restart retailiq-api
```

### Port already in use

If port 3000, 8000, 3307 or 6379 is taken, change the host side of the mapping in `docker-compose.yml` (e.g. `"3001:80"`).

---

# Technologies Used

### Frontend & Visualization
* **React 18** — interactive single-page application
* **Vite 5** — fast build tooling and dev server
* **Tailwind CSS** — utility-first styling
* **Recharts** — interactive charts (line, bar, pie, KPI cards)
* **Lucide React** — icon library

### Backend & API
* **FastAPI** — high-performance async Python API
* **Uvicorn** — ASGI server
* **Pydantic v2** — validation and serialization
* **SQLAlchemy 2 (async)** — ORM with `aiomysql` driver
* **Alembic** — migration tooling

### Machine Learning
* **scikit-learn** — Random Forest, preprocessing, metrics
* **XGBoost** — gradient boosting
* **LightGBM** — leaf-wise gradient boosting
* **Prophet** — Facebook's time-series forecasting
* **SHAP** — Shapley additive explanations for model interpretability

### Data Processing & Storage
* **Pandas / NumPy** — data manipulation
* **SciPy / Statsmodels** — scientific and statistical computing
* **MySQL 8.0** — relational database (containerized)
* **Redis 7** — cache and Celery broker
* **Celery 5** — distributed task queue
* **Joblib** — model serialization

### Infrastructure
* **Docker Compose** — multi-container orchestration
* **Nginx** — frontend static serving and API reverse proxy
* **python-jose / passlib / bcrypt** — JWT auth and password hashing

### External APIs
* **OpenWeatherMap** — live weather data and forecasts
* **Calendarific** — national and religious holiday data

### Reporting
* **fpdf2** — PDF report generation

---

# Contributing

Contributions are welcome! Here's how you can help improve RetailIQ:

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/amazing-feature`).
3. Make your changes.
4. Test the application thoroughly (`docker compose up -d --build`).
5. Commit your changes (`git commit -m 'Add amazing feature'`).
6. Push to the branch (`git push origin feature/amazing-feature`).
7. Open a Pull Request.

### Development Ideas

* Add additional forecasting models (ARIMA, LSTM, Transformer)
* Implement multi-warehouse inventory support
* Add multi-tenant support beyond role-based auth
* Integrate with real POS systems via API
* Add email/SMS alerting for stockout predictions
* Add PostgreSQL as an alternative database backend
* Add comparative analysis across multiple stores/chains
* Implement A/B testing for promotional effectiveness

---

# Support

If you encounter any issues, have feature requests, or need assistance:

* Open an issue in this repository
* Check the existing documentation in the `notebooks/` directory for detailed walkthroughs
* Review the source code — each module has clear documentation and type hints
* Use the troubleshooting section above for common Docker-related issues
