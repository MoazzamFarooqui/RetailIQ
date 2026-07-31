"""Weather and holiday data endpoints."""

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.weather_service import WeatherService
from app.services.holiday_service import HolidayService

router = APIRouter()


@router.get("/current")
async def get_current_weather(
    city: str = "Lahore",
    current_user: User = Depends(get_current_user),
):
    """Get current weather for a Pakistan city."""
    weather_svc = WeatherService()
    return weather_svc.fetch_current_weather(city)


@router.get("/forecast")
async def get_weather_forecast(
    city: str = "Lahore",
    days: int = 7,
    current_user: User = Depends(get_current_user),
):
    """Get weather forecast for a Pakistan city."""
    weather_svc = WeatherService()
    forecast = weather_svc.fetch_forecast(city, days=days)
    if forecast is None or len(forecast) == 0:
        return {"error": "Unable to fetch forecast", "forecast": []}
    return {"city": city, "days": days, "forecast": forecast.to_dict("records")}


@router.get("/holidays/upcoming")
async def get_upcoming_holidays(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
):
    """Get upcoming Pakistan holidays."""
    holiday_svc = HolidayService()
    from datetime import datetime
    holidays = holiday_svc.get_upcoming_holidays(datetime.now(), limit=limit)
    return {"holidays": holidays.to_dict("records") if len(holidays) > 0 else []}


@router.get("/holidays/current")
async def get_current_holiday_context(
    current_user: User = Depends(get_current_user),
):
    """Get current holiday context (pre-holiday window info)."""
    holiday_svc = HolidayService()
    weather_svc = WeatherService()
    from datetime import datetime

    now = datetime.now()
    pre_window = holiday_svc.is_in_pre_holiday_window(now)
    holiday_name = holiday_svc.get_holiday_name(now)
    weather_data = weather_svc.fetch_current_weather()

    from app.services.inventory_optimizer import InventoryOptimizer
    demand_mult = InventoryOptimizer.get_current_demand_multiplier()

    return {
        "current_date": now.strftime("%Y-%m-%d"),
        "holiday_today": holiday_name,
        "season": WeatherService.get_season(now),
        "season_emoji": WeatherService.get_season_emoji(WeatherService.get_season(now)),
        "temperature_c": weather_data.get("temperature_c"),
        "weather_condition": weather_data.get("weather_condition"),
        "pre_holiday_window": pre_window if pre_window else None,
        "demand_multiplier": demand_mult["multiplier"],
        "demand_multiplier_reasons": demand_mult["reasons"],
        "upcoming_holidays": holiday_svc.get_upcoming_holidays(now, limit=3).to_dict("records"),
    }
