"""Weather service with Pakistan-specific seasons and OpenWeatherMap integration."""

import logging
import os
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")
BASE_URL = "https://api.openweathermap.org/data/2.5"

PAKISTAN_CITIES = {
    "Karachi": {"lat": 24.8607, "lon": 67.0011, "state": "Sindh"},
    "Lahore": {"lat": 31.5204, "lon": 74.3587, "state": "Punjab"},
    "Islamabad": {"lat": 33.6844, "lon": 73.0479, "state": "ICT"},
    "Rawalpindi": {"lat": 33.5651, "lon": 73.0169, "state": "Punjab"},
    "Faisalabad": {"lat": 31.4504, "lon": 73.1350, "state": "Punjab"},
}

SEASONAL_PRODUCT_DEMAND = {
    "Summer": {
        "months": [4, 5, 6],
        "high_demand_keywords": [
            "cold drink", "ice cream", "water", "mineral water", "juice",
            "soft drink", "soda", "lemonade", "yogurt drink", "lassi",
            "melon", "mango", "watermelon", "cucumber", "coconut water",
            "ice", "fan", "air conditioner", "sunscreen", "shampoo",
        ],
        "low_demand_keywords": ["soup", "coffee", "hot tea", "blanket", "heater", "winter", "jacket", "sweater", "gloves"],
        "advice": "☀️ Hot summer — stock up on cold drinks, ice cream, juices, and beverages.",
        "temp_threshold": 35,
    },
    "Monsoon": {
        "months": [7, 8, 9],
        "high_demand_keywords": [
            "soup", "tea", "coffee", "pakora mix", "snacks", "kachori",
            "samosa", "medicine", "cold relief", "cough syrup",
            "umbrella", "raincoat", "towel", "soap", "detergent",
        ],
        "low_demand_keywords": ["ice cream", "cold drink", "sunblock", "sunglasses"],
        "advice": "🌧️ Monsoon season — stock umbrellas, raincoats, hot beverages, and snacks.",
        "rain_alert": True,
    },
    "Winter": {
        "months": [11, 12, 1, 2],
        "high_demand_keywords": [
            "tea", "coffee", "green tea", "kashmiri chai", "soup",
            "blanket", "heater", "shawl", "jacket", "sweater",
            "gloves", "muffler", "wool", "winter", "hoodie",
            "socks", "quilt", "hot water bottle",
        ],
        "low_demand_keywords": ["ice cream", "cold drink", "mineral water", "soda", "air conditioner", "fan", "sunscreen"],
        "advice": "❄️ Cold weather — stock up on tea, coffee, soups, blankets, and winter essentials.",
        "temp_threshold": 10,
    },
    "Spring": {
        "months": [3],
        "high_demand_keywords": ["juice", "fresh fruit", "yogurt", "salad", "green vegetable"],
        "low_demand_keywords": [],
        "advice": "🌸 Spring — focus on fresh produce, dairy, and light beverages.",
    },
    "Autumn": {
        "months": [10],
        "high_demand_keywords": ["tea", "coffee", "soup", "dry fruit", "nuts"],
        "low_demand_keywords": ["ice cream", "cold drink"],
        "advice": "🍂 Autumn — mild demand for warm beverages and dry fruits.",
    },
}


class WeatherService:
    """Weather service with Pakistan season awareness."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or API_KEY
        self._cache = {}
        logger.debug("WeatherService initialized")

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def fetch_current_weather(self, city: str = "Lahore") -> dict:
        """Fetch current weather for a Pakistan city."""
        if not self.enabled:
            return self._fallback()

        cache_key = f"current_{city}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            if city in PAKISTAN_CITIES:
                params = {
                    "lat": PAKISTAN_CITIES[city]["lat"],
                    "lon": PAKISTAN_CITIES[city]["lon"],
                    "appid": self.api_key, "units": "metric",
                }
            else:
                params = {"q": f"{city},PK", "appid": self.api_key, "units": "metric"}

            resp = requests.get(f"{BASE_URL}/weather", params=params, timeout=5)
            resp.raise_for_status()
            data = resp.json()

            result = {
                "temperature_c": data["main"]["temp"],
                "feels_like_c": data["main"]["feels_like"],
                "temp_min_c": data["main"]["temp_min"],
                "temp_max_c": data["main"]["temp_max"],
                "humidity_pct": data["main"]["humidity"],
                "pressure_hpa": data["main"]["pressure"],
                "weather_condition": data["weather"][0]["main"],
                "weather_description": data["weather"][0]["description"],
                "wind_speed_ms": data["wind"]["speed"],
                "cloud_cover_pct": data.get("clouds", {}).get("all", 0),
                "rain_1h_mm": data.get("rain", {}).get("1h", 0),
                "rain_3h_mm": data.get("rain", {}).get("3h", 0),
                "city": city, "country": "PK",
                "source": "openweathermap",
                "fetched_at": datetime.now().isoformat(),
                "season": self.get_season(datetime.now()),
            }
            self._cache[cache_key] = result
            return result
        except Exception as e:
            logger.warning(f"Weather API error: {e}, using fallback")
            return self._fallback()

    def fetch_forecast(self, city: str = "Lahore", days: int = 7) -> pd.DataFrame:
        """Fetch weather forecast for a Pakistan city."""
        if not self.enabled:
            return self._fallback_forecast(days)

        cache_key = f"forecast_{city}_{days}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            lat_lon = PAKISTAN_CITIES.get(city, PAKISTAN_CITIES["Lahore"])
            params = {
                "lat": lat_lon["lat"], "lon": lat_lon["lon"],
                "appid": self.api_key, "units": "metric", "cnt": days * 8,
            }
            resp = requests.get(f"{BASE_URL}/forecast", params=params, timeout=5)
            resp.raise_for_status()
            data = resp.json()

            records = []
            for item in data["list"]:
                records.append({
                    "datetime": datetime.fromtimestamp(item["dt"]),
                    "temperature_c": item["main"]["temp"],
                    "feels_like_c": item["main"]["feels_like"],
                    "temp_min_c": item["main"]["temp_min"],
                    "temp_max_c": item["main"]["temp_max"],
                    "humidity_pct": item["main"]["humidity"],
                    "pressure_hpa": item["main"]["pressure"],
                    "weather_condition": item["weather"][0]["main"],
                    "weather_description": item["weather"][0]["description"],
                    "wind_speed_ms": item["wind"]["speed"],
                    "cloud_cover_pct": item.get("clouds", {}).get("all", 0),
                    "rain_3h_mm": item.get("rain", {}).get("3h", 0),
                })

            df = pd.DataFrame(records)
            df["date"] = df["datetime"].dt.date
            daily = df.groupby("date").agg({
                "temperature_c": "mean", "feels_like_c": "mean",
                "temp_min_c": "min", "temp_max_c": "max",
                "humidity_pct": "mean", "pressure_hpa": "mean",
                "wind_speed_ms": "max",
                "rain_3h_mm": "sum",
                "weather_condition": lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else "Unknown",
                "weather_description": lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else "",
            }).reset_index()
            daily.columns = [
                "date", "temp_c", "feels_like_c", "temp_min_c", "temp_max_c",
                "humidity_pct", "pressure_hpa", "wind_speed_ms", "rain_mm",
                "weather_condition", "weather_description",
            ]
            daily["season"] = daily["date"].apply(lambda d: self.get_season(datetime.combine(d, datetime.min.time())))
            self._cache[cache_key] = daily
            return daily
        except Exception as e:
            logger.warning(f"Weather forecast API error: {e}, using fallback")
            return self._fallback_forecast(days)

    @staticmethod
    def _fallback() -> dict:
        """Return Pakistan-appropriate fallback when API is unavailable."""
        now = datetime.now()
        season = WeatherService.get_season(now)
        defaults = {
            "Summer": {"temp": 35, "humidity": 40, "condition": "Clear"},
            "Monsoon": {"temp": 32, "humidity": 75, "condition": "Rain"},
            "Winter": {"temp": 15, "humidity": 60, "condition": "Clear"},
            "Spring": {"temp": 25, "humidity": 50, "condition": "Clear"},
            "Autumn": {"temp": 22, "humidity": 55, "condition": "Clear"},
        }
        d = defaults.get(season, {"temp": 25, "humidity": 50, "condition": "Clear"})
        return {
            "temperature_c": d["temp"], "feels_like_c": d["temp"],
            "temp_min_c": d["temp"] - 3, "temp_max_c": d["temp"] + 3,
            "humidity_pct": d["humidity"], "pressure_hpa": 1013,
            "weather_condition": d["condition"],
            "weather_description": f"{season} conditions",
            "wind_speed_ms": 5.0, "cloud_cover_pct": 30,
            "rain_1h_mm": 0, "rain_3h_mm": 0,
            "city": "Lahore", "country": "PK", "season": season,
            "source": "fallback", "fetched_at": datetime.now().isoformat(),
        }

    @staticmethod
    def _fallback_forecast(days: int) -> pd.DataFrame:
        """Return Pakistan-appropriate placeholder forecast."""
        today = datetime.now()
        records = []
        for i in range(days):
            d = today + timedelta(days=i)
            season = WeatherService.get_season(d)
            defaults = {
                "Summer": {"temp": 35, "humidity": 40, "condition": "Clear"},
                "Monsoon": {"temp": 32, "humidity": 75, "condition": "Rain"},
                "Winter": {"temp": 15, "humidity": 60, "condition": "Clear"},
                "Spring": {"temp": 25, "humidity": 50, "condition": "Clear"},
                "Autumn": {"temp": 22, "humidity": 55, "condition": "Clear"},
            }
            s = defaults.get(season, {"temp": 25, "humidity": 50, "condition": "Clear"})
            records.append({
                "date": d.date(), "temp_c": s["temp"],
                "feels_like_c": s["temp"], "temp_min_c": s["temp"] - 3,
                "temp_max_c": s["temp"] + 3, "humidity_pct": s["humidity"],
                "pressure_hpa": 1013, "wind_speed_ms": 5.0,
                "rain_mm": 15 if season == "Monsoon" else 0,
                "weather_condition": s["condition"],
                "weather_description": f"{season} conditions",
                "season": season,
            })
        return pd.DataFrame(records)

    @staticmethod
    def get_season(date) -> str:
        """Get Pakistan-appropriate season for a given date."""
        month = date.month
        if month == 3:
            return "Spring"
        elif 4 <= month <= 6:
            return "Summer"
        elif 7 <= month <= 9:
            return "Monsoon"
        elif month == 10:
            return "Autumn"
        else:
            return "Winter"

    @staticmethod
    def get_season_for_month(month: int) -> str:
        if month == 3: return "Spring"
        elif 4 <= month <= 6: return "Summer"
        elif 7 <= month <= 9: return "Monsoon"
        elif month == 10: return "Autumn"
        else: return "Winter"

    @staticmethod
    def get_season_emoji(season: str) -> str:
        emojis = {"Spring": "🌸", "Summer": "☀️", "Monsoon": "🌧️", "Autumn": "🍂", "Winter": "❄️"}
        return emojis.get(season, "🌤️")

    @staticmethod
    def get_seasonal_demand_advice(date=None) -> dict:
        if date is None:
            date = datetime.now()
        season = WeatherService.get_season(date)
        info = SEASONAL_PRODUCT_DEMAND.get(season, {})
        if not info:
            return {"season": season, "advice": "Normal demand patterns.", "high_demand": [], "low_demand": []}
        return {
            "season": season, "advice": info.get("advice", ""),
            "high_demand": info.get("high_demand_keywords", []),
            "low_demand": info.get("low_demand_keywords", []),
        }

    @staticmethod
    def get_extreme_weather_advice(weather_data: dict) -> str:
        temp = weather_data.get("temperature_c", 25)
        season = weather_data.get("season", WeatherService.get_season(datetime.now()))
        humidity = weather_data.get("humidity_pct", 50)
        condition = weather_data.get("weather_condition", "").lower()
        rain = weather_data.get("rain_1h_mm", 0) or weather_data.get("rain_3h_mm", 0) or 0
        alerts = []

        if temp >= SEASONAL_PRODUCT_DEMAND.get("Summer", {}).get("temp_threshold", 40):
            alerts.append(f"🔥 Extreme heat ({temp:.0f}°C) — high demand for cold drinks, water, ice cream.")
        if temp <= SEASONAL_PRODUCT_DEMAND.get("Winter", {}).get("temp_threshold", 10):
            alerts.append(f"❄️ Cold wave ({temp:.0f}°C) — stock up on tea, coffee, soups, warm clothing.")
        if rain > 10 or "rain" in condition:
            alerts.append("🌧️ Heavy rain — umbrellas, raincoats, indoor snacks will see higher demand.")
        if humidity > 80:
            alerts.append("💧 High humidity — beverages and cold drinks may see increased demand.")

        if not alerts:
            demand_info = SEASONAL_PRODUCT_DEMAND.get(season, {})
            if demand_info.get("advice"):
                alerts.append(demand_info["advice"])

        return " | ".join(alerts) if alerts else "Normal conditions — standard demand patterns."

    @staticmethod
    def get_seasonality_features(df: pd.DataFrame, date_col: str = "date") -> pd.DataFrame:
        """Add Pakistan seasonal features based on date."""
        df = df.copy()
        dates = pd.to_datetime(df[date_col])

        df["season"] = dates.apply(WeatherService.get_season)
        season_dummies = pd.get_dummies(df["season"], prefix="season")
        for s in ["Spring", "Summer", "Monsoon", "Autumn", "Winter"]:
            col = f"season_{s}"
            if col not in season_dummies.columns:
                season_dummies[col] = 0
        df = pd.concat([df, season_dummies], axis=1)

        df["month_sin"] = dates.apply(lambda d: np.sin(2 * np.pi * d.month / 12))
        df["month_cos"] = dates.apply(lambda d: np.cos(2 * np.pi * d.month / 12))
        df["dow_sin"] = dates.apply(lambda d: np.sin(2 * np.pi * d.dayofweek / 7))
        df["dow_cos"] = dates.apply(lambda d: np.cos(2 * np.pi * d.dayofweek / 7))
        return df

    @staticmethod
    def add_weather_features(df: pd.DataFrame, weather_df: pd.DataFrame = None) -> pd.DataFrame:
        """Add weather features if weather data is available, else synthetic based on season."""
        df = df.copy()
        if "date" not in df.columns:
            return df
        dates = pd.to_datetime(df["date"])

        if weather_df is not None and len(weather_df) > 0:
            weather_df = weather_df.copy()
            weather_df["date"] = pd.to_datetime(weather_df["date"])
            df["_merge_date"] = dates.dt.date
            weather_df["_merge_date"] = weather_df["date"].dt.date
            df = df.merge(weather_df.drop(columns=["date"]), on="_merge_date", how="left")
            df = df.drop(columns=["_merge_date"])
        else:
            df["season"] = dates.apply(WeatherService.get_season)
            season_weather = {
                "Spring": {"temp": 25, "humidity": 50, "rain": 5},
                "Summer": {"temp": 35, "humidity": 40, "rain": 10},
                "Monsoon": {"temp": 32, "humidity": 75, "rain": 50},
                "Autumn": {"temp": 22, "humidity": 55, "rain": 5},
                "Winter": {"temp": 15, "humidity": 60, "rain": 10},
            }
            df["temp_c"] = df["season"].map(lambda s: season_weather.get(s, {}).get("temp", 25))
            df["humidity_pct"] = df["season"].map(lambda s: season_weather.get(s, {}).get("humidity", 50))
            df["rain_mm"] = df["season"].map(lambda s: season_weather.get(s, {}).get("rain", 5))
        return df

    @staticmethod
    def get_weather_impact_multiplier(temp_c: float, season: str, condition: str = "") -> float:
        multiplier = 1.0
        if temp_c >= 35: multiplier = 1.3
        elif temp_c >= 30: multiplier = 1.15
        elif temp_c <= 10: multiplier = 1.25
        elif temp_c <= 15: multiplier = 1.1
        if "rain" in condition.lower() or season == "Monsoon":
            multiplier *= 1.1
        return multiplier

