"""Pakistan holiday service — fixed dates + Islamic calendar lookup."""

import logging
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

API_KEY = os.environ.get("HOLIDAY_API_KEY", "")

_ISLAMIC_HOLIDAYS = {
    2024: [
        ("Shab-e-Miraj", "2024-02-08"), ("Shab-e-Barat", "2024-02-25"),
        ("Ramadan Starts", "2024-03-12"),
        ("Eid-ul-Fitr Day 1", "2024-04-10"), ("Eid-ul-Fitr Day 2", "2024-04-11"), ("Eid-ul-Fitr Day 3", "2024-04-12"),
        ("Eid-ul-Adha Day 1", "2024-06-17"), ("Eid-ul-Adha Day 2", "2024-06-18"), ("Eid-ul-Adha Day 3", "2024-06-19"),
        ("Muharram (Islamic New Year)", "2024-07-07"),
        ("Ashura (10th Muharram)", "2024-07-16"), ("Ashura Day 2", "2024-07-17"),
        ("Eid Milad-un-Nabi", "2024-09-16"),
    ],
    2025: [
        ("Shab-e-Miraj", "2025-01-27"), ("Shab-e-Barat", "2025-02-14"),
        ("Ramadan Starts", "2025-03-01"),
        ("Eid-ul-Fitr Day 1", "2025-03-31"), ("Eid-ul-Fitr Day 2", "2025-04-01"), ("Eid-ul-Fitr Day 3", "2025-04-02"),
        ("Eid-ul-Adha Day 1", "2025-06-07"), ("Eid-ul-Adha Day 2", "2025-06-08"), ("Eid-ul-Adha Day 3", "2025-06-09"),
        ("Muharram (Islamic New Year)", "2025-06-27"),
        ("Ashura (10th Muharram)", "2025-07-06"), ("Ashura Day 2", "2025-07-07"),
        ("Eid Milad-un-Nabi", "2025-09-05"),
    ],
    2026: [
        ("Shab-e-Miraj", "2026-01-16"), ("Shab-e-Barat", "2026-02-03"),
        ("Ramadan Starts", "2026-02-18"),
        ("Eid-ul-Fitr Day 1", "2026-03-20"), ("Eid-ul-Fitr Day 2", "2026-03-21"), ("Eid-ul-Fitr Day 3", "2026-03-22"),
        ("Eid-ul-Adha Day 1", "2026-05-28"), ("Eid-ul-Adha Day 2", "2026-05-29"), ("Eid-ul-Adha Day 3", "2026-05-30"),
        ("Muharram (Islamic New Year)", "2026-06-17"),
        ("Ashura (10th Muharram)", "2026-06-26"), ("Ashura Day 2", "2026-06-27"),
        ("Eid Milad-un-Nabi", "2026-08-26"),
    ],
    2027: [
        ("Shab-e-Miraj", "2027-01-05"), ("Shab-e-Barat", "2027-01-23"),
        ("Ramadan Starts", "2027-02-08"),
        ("Eid-ul-Fitr Day 1", "2027-03-09"), ("Eid-ul-Fitr Day 2", "2027-03-10"), ("Eid-ul-Fitr Day 3", "2027-03-11"),
        ("Eid-ul-Adha Day 1", "2027-05-17"), ("Eid-ul-Adha Day 2", "2027-05-18"), ("Eid-ul-Adha Day 3", "2027-05-19"),
        ("Muharram (Islamic New Year)", "2027-06-06"),
        ("Ashura (10th Muharram)", "2027-06-15"), ("Ashura Day 2", "2027-06-16"),
        ("Eid Milad-un-Nabi", "2027-08-15"),
    ],
    2028: [
        ("Shab-e-Miraj", "2027-12-25"), ("Shab-e-Barat", "2028-01-12"),
        ("Ramadan Starts", "2028-01-28"),
        ("Eid-ul-Fitr Day 1", "2028-02-26"), ("Eid-ul-Fitr Day 2", "2028-02-27"), ("Eid-ul-Fitr Day 3", "2028-02-28"),
        ("Eid-ul-Adha Day 1", "2028-05-05"), ("Eid-ul-Adha Day 2", "2028-05-06"), ("Eid-ul-Adha Day 3", "2028-05-07"),
        ("Muharram (Islamic New Year)", "2028-05-25"),
        ("Ashura (10th Muharram)", "2028-06-03"), ("Ashura Day 2", "2028-06-04"),
        ("Eid Milad-un-Nabi", "2028-08-03"),
    ],
}

_FIXED_PAK_HOLIDAYS = [
    "Pakistan Day", "Labour Day", "Independence Day", "Defence Day",
    "Air Force Day", "Iqbal Day", "Quaid-e-Azam Day",
]

HOLIDAY_CATEGORIES = {
    "Ramadan": ("ramadan", "religious_fasting"),
    "Eid-ul-Fitr": ("eid", "religious_feast"), "Eid-ul-Adha": ("eid", "religious_feast"),
    "Eid Milad": ("religious", "religious_observance"),
    "Pakistan Day": ("national", "patriotic"), "Independence Day": ("national", "patriotic"),
    "Defence Day": ("national", "patriotic"), "Iqbal Day": ("national", "patriotic"),
    "Quaid-e-Azam Day": ("national", "patriotic"),
    "Ashura": ("religious", "religious_observance"),
    "Shab-e-Barat": ("religious", "religious_observance"),
    "Shab-e-Miraj": ("religious", "religious_observance"),
    "Muharram": ("religious", "religious_observance"),
    "Labour Day": ("national", "public"),
}

HOLIDAY_PRODUCT_DEMAND = {
    "ramadan": {
        "categories": ["FOODS", "BEVERAGES", "FROZEN"],
        "products": ["dates", "juices", "frozen foods", "beverages", "cooking oil"],
        "demand_multiplier": 1.3, "pre_days": 14,
        "pre_window_label": "Pre-Ramadan stock-up",
        "advice": "Stock up on dates, juices, beverages, and frozen foods before Ramadan.",
    },
    "eid": {
        "categories": ["FOODS", "BEVERAGES", "HOUSEHOLD"],
        "products": ["soft drinks", "snacks", "gifts", "sweets", "cooking oil"],
        "demand_multiplier": 1.5, "pre_days": 7,
        "pre_window_label": "Pre-Eid shopping",
        "advice": "Increase stock of soft drinks, snacks, sweets, and gifts before Eid.",
    },
    "national": {
        "categories": ["FOODS", "BEVERAGES"],
        "products": ["soft drinks", "snacks", "beverages"],
        "demand_multiplier": 1.2, "pre_days": 3,
        "pre_window_label": "National holiday prep",
        "advice": "Stock up on beverages and snacks for national holiday celebrations.",
    },
}


class HolidayService:
    """Pakistan-focused holiday service with fixed + Islamic calendar dates."""

    def __init__(self, api_key: str = None, country: str = "PK"):
        self.api_key = api_key or API_KEY
        self.country = country
        self._cache = {}
        logger.debug("HolidayService initialized")

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def fetch_holidays(self, year: int = None, country: str = None) -> pd.DataFrame:
        """Fetch all Pakistan holidays for a given year — fixed + Islamic."""
        if year is None:
            year = datetime.now().year
        country = country or self.country
        cache_key = f"{country}_{year}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        all_holidays = []
        all_holidays.extend(self._fixed_holidays(year))
        if year in _ISLAMIC_HOLIDAYS:
            all_holidays.extend(_ISLAMIC_HOLIDAYS[year])

        df = pd.DataFrame(all_holidays, columns=["name", "date"])
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").drop_duplicates(subset="date").reset_index(drop=True)
        df["country"] = "PK"
        self._cache[cache_key] = df
        return df

    @staticmethod
    def _fixed_holidays(year: int) -> list:
        return [
            ("Kashmir Day", f"{year}-02-05"),
            ("Pakistan Day", f"{year}-03-23"),
            ("Labour Day", f"{year}-05-01"),
            ("Independence Day", f"{year}-08-14"),
            ("Defence Day", f"{year}-09-06"),
            ("Air Force Day", f"{year}-09-07"),
            ("Iqbal Day", f"{year}-11-09"),
            ("Quaid-e-Azam Day", f"{year}-12-25"),
        ]

    def is_holiday(self, date, country: str = "PK") -> bool:
        df = self.fetch_holidays(date.year, country)
        return (df["date"].dt.date == date.date()).any()

    def get_holiday_name(self, date, country: str = "PK") -> str:
        df = self.fetch_holidays(date.year, country)
        match = df[df["date"].dt.date == date.date()]
        return match["name"].iloc[0] if len(match) > 0 else None

    def get_holidays_in_range(self, start_date, end_date) -> pd.DataFrame:
        all_holidays = []
        for year in range(start_date.year, end_date.year + 1):
            all_holidays.append(self.fetch_holidays(year))
        combined = pd.concat(all_holidays, ignore_index=True)
        mask = (combined["date"] >= pd.Timestamp(start_date)) & (combined["date"] <= pd.Timestamp(end_date))
        return combined[mask].sort_values("date")

    @staticmethod
    def categorize_holiday(holiday_name: str) -> str:
        if holiday_name is None:
            return "none"
        for keyword, category in HOLIDAY_CATEGORIES.items():
            if keyword.lower() in holiday_name.lower():
                return category[0]
        hl = holiday_name.lower()
        if "ramadan" in hl or "ramzan" in hl:
            return "ramadan"
        if "eid" in hl:
            return "eid"
        if "ashura" in hl or "muharram" in hl:
            return "religious"
        if "independence" in hl or "pakistan day" in hl or "defence" in hl:
            return "national"
        return "other"

    @staticmethod
    def get_demand_multiplier(holiday_name: str) -> float:
        cat = HolidayService.categorize_holiday(holiday_name)
        for key, info in HOLIDAY_PRODUCT_DEMAND.items():
            if cat == key or cat in info.get("categories", []):
                return info["demand_multiplier"]
        return 1.0

    @staticmethod
    def get_pre_holiday_days(holiday_name: str) -> int:
        cat = HolidayService.categorize_holiday(holiday_name)
        for key, info in HOLIDAY_PRODUCT_DEMAND.items():
            if cat == key:
                return info["pre_days"]
        return 0

    @staticmethod
    def get_holiday_advice(holiday_name: str) -> str:
        cat = HolidayService.categorize_holiday(holiday_name)
        for key, info in HOLIDAY_PRODUCT_DEMAND.items():
            if cat == key:
                return info["advice"]
        return ""

    def is_in_pre_holiday_window(self, date) -> dict:
        """Check if date falls in the pre-holiday shopping window."""
        df = self.fetch_holidays(date.year)
        df_next = self.fetch_holidays(date.year + 1)
        df_all = pd.concat([df, df_next], ignore_index=True)
        target = pd.Timestamp(date)

        for _, row in df_all.iterrows():
            h_date = row["date"]
            h_name = row["name"]
            pre_days = self.get_pre_holiday_days(h_name)
            if pre_days > 0:
                window_start = h_date - timedelta(days=pre_days)
                if window_start <= target < h_date:
                    return {
                        "holiday_name": h_name,
                        "holiday_date": h_date.strftime("%Y-%m-%d"),
                        "days_until_holiday": (h_date - target).days,
                        "pre_window_days": pre_days,
                        "demand_multiplier": self.get_demand_multiplier(h_name),
                        "advice": self.get_holiday_advice(h_name),
                        "category": self.categorize_holiday(h_name),
                    }
        return {}

    def get_upcoming_holidays(self, date=None, limit=5) -> pd.DataFrame:
        if date is None:
            date = datetime.now()
        df = self.fetch_holidays(date.year)
        df_next = self.fetch_holidays(date.year + 1)
        df_all = pd.concat([df, df_next], ignore_index=True)
        future = df_all[df_all["date"] >= pd.Timestamp(date)].copy()
        future["days_until"] = (future["date"] - pd.Timestamp(date)).dt.days
        future["category"] = future["name"].apply(self.categorize_holiday)
        future["demand_multiplier"] = future["name"].apply(self.get_demand_multiplier)
        future["advice"] = future["name"].apply(self.get_holiday_advice)
        return future.sort_values("date").head(limit)

    def get_holiday_features(self, df: pd.DataFrame, date_col: str = "date") -> pd.DataFrame:
        """Add Pakistan holiday features to a dataframe."""
        df = df.copy()
        dates = pd.to_datetime(df[date_col])
        years = range(dates.dt.year.min(), dates.dt.year.max() + 1)
        all_holidays = pd.concat([self.fetch_holidays(y) for y in years], ignore_index=True)
        holiday_dates = all_holidays["date"].dt.date.drop_duplicates()

        df["is_holiday"] = dates.dt.date.isin(holiday_dates).astype(int)

        # Days to next / since last holiday
        holiday_set = set(holiday_dates)

        def _days_to_next(d):
            d_val = d.date()
            if d_val in holiday_set:
                return 0
            for offset in range(1, 91):
                if (d + timedelta(days=offset)).date() in holiday_set:
                    return offset
            return 30

        def _days_since_last(d):
            d_val = d.date()
            if d_val in holiday_set:
                return 0
            for offset in range(1, 91):
                if (d - timedelta(days=offset)).date() in holiday_set:
                    return offset
            return 30

        df["days_to_holiday"] = dates.apply(_days_to_next)
        df["days_since_holiday"] = dates.apply(_days_since_last)
        df["in_ramadan_window"] = 0
        df["in_eid_window"] = 0

        for _, row in all_holidays.iterrows():
            h_name, h_date = row["name"], row["date"]
            cat = self.categorize_holiday(h_name)
            pre_days = self.get_pre_holiday_days(h_name)
            if pre_days > 0:
                window_start = h_date - timedelta(days=pre_days)
                mask = (dates >= window_start) & (dates < h_date)
                if cat == "ramadan":
                    df.loc[mask, "in_ramadan_window"] = 1
                elif cat == "eid":
                    df.loc[mask, "in_eid_window"] = 1

        return df

