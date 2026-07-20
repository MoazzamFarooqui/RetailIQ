"""Pakistan holiday service — fixed dates + Islamic calendar lookup.

Provides Pakistan-specific holidays including:
- Fixed national holidays (Pakistan Day, Independence Day, etc.)
- Islamic holidays (Ramadan, Eids, Muharram, etc.) with 2024-2028 lookup tables
- Pre-holiday shopping window detection (Ramadan, Eid, etc.)
"""

import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

API_KEY = os.environ.get('HOLIDAY_API_KEY', '')


# ── Islamic calendar holiday lookup: 2024-2028 ──────────────────────────────
# Source: verified against official Pakistan calendar / moonsighting forecasts
# Dates are observational (may shift ±1 day based on moon sighting)
_ISLAMIC_HOLIDAYS = {
    2024: [
        ('Shab-e-Miraj', '2024-02-08'),
        ('Shab-e-Barat', '2024-02-25'),
        ('Ramadan Starts', '2024-03-12'),
        ('Eid-ul-Fitr Day 1', '2024-04-10'),
        ('Eid-ul-Fitr Day 2', '2024-04-11'),
        ('Eid-ul-Fitr Day 3', '2024-04-12'),
        ('Eid-ul-Adha Day 1', '2024-06-17'),
        ('Eid-ul-Adha Day 2', '2024-06-18'),
        ('Eid-ul-Adha Day 3', '2024-06-19'),
        ('Muharram (Islamic New Year)', '2024-07-07'),
        ('Ashura (10th Muharram)', '2024-07-16'),
        ('Ashura Day 2', '2024-07-17'),
        ('Eid Milad-un-Nabi', '2024-09-16'),
    ],
    2025: [
        ('Shab-e-Miraj', '2025-01-27'),
        ('Shab-e-Barat', '2025-02-14'),
        ('Ramadan Starts', '2025-03-01'),
        ('Eid-ul-Fitr Day 1', '2025-03-31'),
        ('Eid-ul-Fitr Day 2', '2025-04-01'),
        ('Eid-ul-Fitr Day 3', '2025-04-02'),
        ('Eid-ul-Adha Day 1', '2025-06-07'),
        ('Eid-ul-Adha Day 2', '2025-06-08'),
        ('Eid-ul-Adha Day 3', '2025-06-09'),
        ('Muharram (Islamic New Year)', '2025-06-27'),
        ('Ashura (10th Muharram)', '2025-07-06'),
        ('Ashura Day 2', '2025-07-07'),
        ('Eid Milad-un-Nabi', '2025-09-05'),
    ],
    2026: [
        ('Shab-e-Miraj', '2026-01-16'),
        ('Shab-e-Barat', '2026-02-03'),
        ('Ramadan Starts', '2026-02-18'),
        ('Eid-ul-Fitr Day 1', '2026-03-20'),
        ('Eid-ul-Fitr Day 2', '2026-03-21'),
        ('Eid-ul-Fitr Day 3', '2026-03-22'),
        ('Eid-ul-Adha Day 1', '2026-05-28'),
        ('Eid-ul-Adha Day 2', '2026-05-29'),
        ('Eid-ul-Adha Day 3', '2026-05-30'),
        ('Muharram (Islamic New Year)', '2026-06-17'),
        ('Ashura (10th Muharram)', '2026-06-26'),
        ('Ashura Day 2', '2026-06-27'),
        ('Eid Milad-un-Nabi', '2026-08-26'),
    ],
    2027: [
        ('Shab-e-Miraj', '2027-01-05'),
        ('Shab-e-Barat', '2027-01-23'),
        ('Ramadan Starts', '2027-02-08'),
        ('Eid-ul-Fitr Day 1', '2027-03-09'),
        ('Eid-ul-Fitr Day 2', '2027-03-10'),
        ('Eid-ul-Fitr Day 3', '2027-03-11'),
        ('Eid-ul-Adha Day 1', '2027-05-17'),
        ('Eid-ul-Adha Day 2', '2027-05-18'),
        ('Eid-ul-Adha Day 3', '2027-05-19'),
        ('Muharram (Islamic New Year)', '2027-06-06'),
        ('Ashura (10th Muharram)', '2027-06-15'),
        ('Ashura Day 2', '2027-06-16'),
        ('Eid Milad-un-Nabi', '2027-08-15'),
    ],
    2028: [
        ('Shab-e-Miraj', '2027-12-25'),  # Note: late Dec 2027
        ('Shab-e-Barat', '2028-01-12'),
        ('Ramadan Starts', '2028-01-28'),
        ('Eid-ul-Fitr Day 1', '2028-02-26'),
        ('Eid-ul-Fitr Day 2', '2028-02-27'),
        ('Eid-ul-Fitr Day 3', '2028-02-28'),
        ('Eid-ul-Adha Day 1', '2028-05-05'),
        ('Eid-ul-Adha Day 2', '2028-05-06'),
        ('Eid-ul-Adha Day 3', '2028-05-07'),
        ('Muharram (Islamic New Year)', '2028-05-25'),
        ('Ashura (10th Muharram)', '2028-06-03'),
        ('Ashura Day 2', '2028-06-04'),
        ('Eid Milad-un-Nabi', '2028-08-03'),
    ],
}

# ── Fixed Pakistan national holidays ─────────────────────────────────────────
_FIXED_PAK_HOLIDAYS = [
    'Pakistan Day',
    'Labour Day',
    'Independence Day',
    'Defence Day',
    'Air Force Day',
    'Iqbal Day',
    'Quaid-e-Azam Day',
]

# ── Holiday categories for demand prediction ─────────────────────────────────
HOLIDAY_CATEGORIES = {
    'Ramadan': ('ramadan', 'religious_fasting'),
    'Eid-ul-Fitr': ('eid', 'religious_feast'),
    'Eid-ul-Adha': ('eid', 'religious_feast'),
    'Eid Milad': ('religious', 'religious_observance'),
    'Pakistan Day': ('national', 'patriotic'),
    'Independence Day': ('national', 'patriotic'),
    'Defence Day': ('national', 'patriotic'),
    'Iqbal Day': ('national', 'patriotic'),
    'Quaid-e-Azam Day': ('national', 'patriotic'),
    'Ashura': ('religious', 'religious_observance'),
    'Shab-e-Barat': ('religious', 'religious_observance'),
    'Shab-e-Miraj': ('religious', 'religious_observance'),
    'Muharram': ('religious', 'religious_observance'),
    'Labour Day': ('national', 'public'),
}

# ── Product categories that see demand spikes for each holiday type ──────────
HOLIDAY_PRODUCT_DEMAND = {
    'ramadan': {
        'categories': ['FOODS', 'BEVERAGES', 'FROZEN'],
        'products': ['dates', 'juices', 'frozen foods', 'beverages', 'cooking oil'],
        'demand_multiplier': 1.3,
        'pre_days': 14,
        'pre_window_label': 'Pre-Ramadan stock-up',
        'advice': 'Stock up on dates, juices, beverages, and frozen foods before Ramadan.',
    },
    'eid': {
        'categories': ['FOODS', 'BEVERAGES', 'HOUSEHOLD'],
        'products': ['soft drinks', 'snacks', 'gifts', 'sweets', 'cooking oil'],
        'demand_multiplier': 1.5,
        'pre_days': 7,
        'pre_window_label': 'Pre-Eid shopping',
        'advice': 'Increase stock of soft drinks, snacks, sweets, and gifts before Eid.',
    },
    'national': {
        'categories': ['FOODS', 'BEVERAGES'],
        'products': ['soft drinks', 'snacks', 'beverages'],
        'demand_multiplier': 1.2,
        'pre_days': 3,
        'pre_window_label': 'National holiday prep',
        'advice': 'Stock up on beverages and snacks for national holiday celebrations.',
    },
}

# ── Product keywords for demand pattern matching ────────────────────────────
SEASONAL_PRODUCT_MAP = {
    'summer': {
        'high_demand': ['cold drink', 'ice cream', 'water', 'juice', 'soft drink',
                        'beverage', 'mineral water', 'yogurt drink', 'soda', 'lemonade',
                        'melon', 'mango', 'ice', 'fan', 'air conditioner', 'sunscreen'],
        'low_demand': ['soup', 'coffee', 'tea', 'blanket', 'heater', 'winter'],
        'advice': 'Hot weather ahead — ensure adequate stock of cold drinks, ice cream, and beverages.'
    },
    'winter': {
        'high_demand': ['tea', 'coffee', 'soup', 'shawl', 'blanket', 'heater',
                        'winter', 'jacket', 'sweater', 'gloves', ' muffler',
                        'green tea', 'kashmiri chai'],
        'low_demand': ['ice cream', 'cold drink', 'mineral water', 'soda', 'lemonade',
                       'air conditioner', 'fan'],
        'advice': 'Cold weather ahead — stock up on tea, coffee, soups, and winter essentials.'
    },
    'monsoon': {
        'high_demand': ['soup', 'tea', 'coffee', 'pakora mix', 'snacks',
                        'medicine', 'cold relief', 'umbrella', 'raincoat'],
        'low_demand': ['ice cream', 'cold drink', 'sunblock'],
        'advice': 'Monsoon season — keep umbrellas, raincoats, and hot beverage supplies well-stocked.'
    },
    'spring': {
        'high_demand': ['juice', 'fresh fruit', 'yogurt', 'salad'],
        'low_demand': [],
        'advice': 'Mild weather — focus on fresh produce and dairy.'
    },
}


class HolidayService:
    """Pakistan-focused holiday service with fixed + Islamic calendar dates."""

    def __init__(self, api_key: str = None, country: str = 'PK'):
        self.api_key = api_key or API_KEY
        self.country = country
        self._cache = {}

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    # ── Main holiday fetch ─────────────────────────────────────────────────

    def fetch_holidays(self, year: int = None, country: str = None) -> pd.DataFrame:
        """Fetch all Pakistan holidays for a given year — fixed + Islamic."""
        if year is None:
            year = datetime.now().year
        country = country or self.country

        cache_key = f'{country}_{year}'
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Try API if configured (Calendarific can supplement)
        api_holidays = None
        if self.enabled:
            try:
                api_holidays = self._fetch_from_api(year, country)
            except Exception:
                pass

        # Build combined holiday list
        all_holidays = []

        # 1. Fixed Pakistan national holidays
        all_holidays.extend(self._fixed_holidays(year))

        # 2. Islamic calendar holidays (our lookup table)
        if year in _ISLAMIC_HOLIDAYS:
            all_holidays.extend(_ISLAMIC_HOLIDAYS[year])

        # 3. API holidays (deduplicate by date)
        if api_holidays is not None and len(api_holidays) > 0:
            existing_dates = {h[1] for h in all_holidays}
            for _, row in api_holidays.iterrows():
                date_str = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date'])[:10]
                if date_str not in existing_dates:
                    all_holidays.append((row['name'], date_str))

        df = pd.DataFrame(all_holidays, columns=['name', 'date'])
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').drop_duplicates(subset='date').reset_index(drop=True)
        df['country'] = 'PK'

        self._cache[cache_key] = df
        return df

    def _fetch_from_api(self, year: int, country: str = 'PK') -> pd.DataFrame:
        """Fetch holidays via Calendarific API."""
        import requests
        url = 'https://calendarific.com/api/v2/holidays'
        params = {'api_key': self.api_key, 'country': country, 'year': year}
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        holidays_list = []
        for h in data.get('response', {}).get('holidays', []):
            holidays_list.append({
                'date': pd.to_datetime(h['date']['iso']),
                'name': h['name'],
                'type': h.get('type', ['Unknown'])[0],
                'country': country,
            })

        if not holidays_list:
            return None
        return pd.DataFrame(holidays_list)

    # ── Fixed Pakistan holidays ─────────────────────────────────────────────

    @staticmethod
    def _fixed_holidays(year: int) -> list:
        """Return fixed-date Pakistan national holidays for a given year."""
        return [
            ('Kashmir Day', f'{year}-02-05'),
            ('Pakistan Day', f'{year}-03-23'),
            ('Labour Day', f'{year}-05-01'),
            ('Independence Day', f'{year}-08-14'),
            ('Defence Day', f'{year}-09-06'),
            ('Air Force Day', f'{year}-09-07'),
            ('Iqbal Day', f'{year}-11-09'),
            ('Quaid-e-Azam Day', f'{year}-12-25'),
        ]

    # ── Holiday check / name ────────────────────────────────────────────────

    def is_holiday(self, date, country: str = 'PK') -> bool:
        """Check if a given date is a holiday."""
        df = self.fetch_holidays(date.year, country)
        return (df['date'].dt.date == date.date()).any()

    def get_holiday_name(self, date, country: str = 'PK') -> str:
        """Get the holiday name for a given date."""
        df = self.fetch_holidays(date.year, country)
        match = df[df['date'].dt.date == date.date()]
        return match['name'].iloc[0] if len(match) > 0 else None

    def get_holidays_in_range(self, start_date, end_date) -> pd.DataFrame:
        """Get all holidays falling within a date range."""
        all_holidays = []
        for year in range(start_date.year, end_date.year + 1):
            h = self.fetch_holidays(year)
            all_holidays.append(h)
        combined = pd.concat(all_holidays, ignore_index=True)
        mask = (combined['date'] >= pd.Timestamp(start_date)) & \
               (combined['date'] <= pd.Timestamp(end_date))
        return combined[mask].sort_values('date')

    # ── Holiday category detection ──────────────────────────────────────────

    @staticmethod
    def categorize_holiday(holiday_name: str) -> str:
        """Categorize a holiday into a demand-impact group."""
        if holiday_name is None:
            return 'none'
        for keyword, category in HOLIDAY_CATEGORIES.items():
            if keyword.lower() in holiday_name.lower():
                return category[0]
        # Check substrings
        hl = holiday_name.lower()
        if 'ramadan' in hl or 'ramzan' in hl:
            return 'ramadan'
        if 'eid' in hl:
            return 'eid'
        if 'ashura' in hl or 'muharram' in hl:
            return 'religious'
        if 'independence' in hl or 'pakistan day' in hl or 'defence' in hl:
            return 'national'
        return 'other'

    @staticmethod
    def get_demand_multiplier(holiday_name: str) -> float:
        """Get expected demand multiplier for a holiday type."""
        cat = HolidayService.categorize_holiday(holiday_name)
        for key, info in HOLIDAY_PRODUCT_DEMAND.items():
            if cat == key or cat in info.get('categories', []):
                return info['demand_multiplier']
        return 1.0

    @staticmethod
    def get_pre_holiday_days(holiday_name: str) -> int:
        """Get how many days before a holiday the shopping window starts."""
        cat = HolidayService.categorize_holiday(holiday_name)
        for key, info in HOLIDAY_PRODUCT_DEMAND.items():
            if cat == key:
                return info['pre_days']
        return 0

    @staticmethod
    def get_holiday_advice(holiday_name: str) -> str:
        """Get inventory advice for a holiday."""
        cat = HolidayService.categorize_holiday(holiday_name)
        for key, info in HOLIDAY_PRODUCT_DEMAND.items():
            if cat == key:
                return info['advice']
        return ''

    # ── Pre-holiday shopping window detection ───────────────────────────────

    def is_in_pre_holiday_window(self, date) -> dict:
        """Check if date falls in the pre-holiday shopping window for any holiday.

        Returns a dict with holiday info if yes, empty dict if no.
        """
        df = self.fetch_holidays(date.year)
        # Check current year and next year (for holidays in Jan/Feb)
        df_next = self.fetch_holidays(date.year + 1)
        df_all = pd.concat([df, df_next], ignore_index=True)

        target = pd.Timestamp(date)
        for _, row in df_all.iterrows():
            h_date = row['date']
            h_name = row['name']
            pre_days = self.get_pre_holiday_days(h_name)
            if pre_days > 0:
                window_start = h_date - timedelta(days=pre_days)
                if window_start <= target < h_date:
                    return {
                        'holiday_name': h_name,
                        'holiday_date': h_date.strftime('%Y-%m-%d'),
                        'days_until_holiday': (h_date - target).days,
                        'pre_window_days': pre_days,
                        'demand_multiplier': self.get_demand_multiplier(h_name),
                        'advice': self.get_holiday_advice(h_name),
                        'category': self.categorize_holiday(h_name),
                    }
        return {}

    def get_upcoming_holidays(self, date=None, limit=5) -> pd.DataFrame:
        """Get the next N upcoming holidays from a given date."""
        if date is None:
            date = datetime.now()
        df = self.fetch_holidays(date.year)
        # Also check next year for year-end proximity
        df_next = self.fetch_holidays(date.year + 1)
        df_all = pd.concat([df, df_next], ignore_index=True)

        future = df_all[df_all['date'] >= pd.Timestamp(date)].copy()
        future['days_until'] = (future['date'] - pd.Timestamp(date)).dt.days
        future['category'] = future['name'].apply(self.categorize_holiday)
        future['demand_multiplier'] = future['name'].apply(self.get_demand_multiplier)
        future['advice'] = future['name'].apply(self.get_holiday_advice)
        return future.sort_values('date').head(limit)

    # ── Feature generation for ML ───────────────────────────────────────────

    def get_holiday_features(self, df: pd.DataFrame, date_col: str = 'date') -> pd.DataFrame:
        """Add Pakistan holiday features to a dataframe."""
        df = df.copy()
        dates = pd.to_datetime(df[date_col])

        years = range(dates.dt.year.min(), dates.dt.year.max() + 1)
        all_holidays = []
        for y in years:
            h = self.fetch_holidays(y)
            all_holidays.append(h)
        holidays_df = pd.concat(all_holidays, ignore_index=True)
        holiday_dates = holidays_df['date'].dt.date.drop_duplicates()

        # Basic holiday flag
        df['is_holiday'] = dates.dt.date.isin(holiday_dates).astype(int)

        # Holiday category one-hot
        holiday_cats = holidays_df.copy()
        holiday_cats['category'] = holiday_cats['name'].apply(self.categorize_holiday)
        cat_dummies = pd.get_dummies(holiday_cats['category'], prefix='holiday_cat')
        holiday_cats = pd.concat([holiday_cats, cat_dummies], axis=1)
        # Aggregate per date
        cat_agg = holiday_cats.groupby(holiday_cats['date'].dt.date)[
            [c for c in holiday_cats.columns if c.startswith('holiday_cat_')]
        ].max().reset_index()
        cat_agg.columns = ['date'] + [c for c in cat_agg.columns if c != 'date']
        cat_agg['date'] = pd.to_datetime(cat_agg['date'])

        df = df.merge(cat_agg, left_on=df[date_col].dt.date, right_on=cat_agg['date'].dt.date, how='left')
        df = df.drop(columns=['date_y'], errors='ignore')
        # Rename date_x back
        if 'date_x' in df.columns:
            df = df.rename(columns={'date_x': date_col})
        df = df.drop(columns=['date'], errors='ignore')
        # Fill missing category flags
        for c in df.columns:
            if c.startswith('holiday_cat_'):
                df[c] = df[c].fillna(0).astype(int)

        # Days to next / since last holiday (for each date)
        holiday_set = set(holiday_dates)

        def _days_to_next(d):
            d_val = d.date()
            if d_val in holiday_set:
                return 0
            for offset in range(1, 91):
                check = d + timedelta(days=offset)
                if check.date() in holiday_set:
                    return offset
            return 30

        def _days_since_last(d):
            d_val = d.date()
            if d_val in holiday_set:
                return 0
            for offset in range(1, 91):
                check = d - timedelta(days=offset)
                if check.date() in holiday_set:
                    return offset
            return 30

        df['days_to_holiday'] = dates.apply(_days_to_next)
        df['days_since_holiday'] = dates.apply(_days_since_last)

        # Pre-Ramadan / pre-Eid shopping window flags
        df['in_ramadan_window'] = 0
        df['in_eid_window'] = 0

        for idx, row in holidays_df.iterrows():
            h_name = row['name']
            h_date = row['date']
            cat = self.categorize_holiday(h_name)
            pre_days = self.get_pre_holiday_days(h_name)
            if pre_days > 0:
                window_start = h_date - timedelta(days=pre_days)
                mask = (dates >= window_start) & (dates < h_date)
                if cat == 'ramadan':
                    df.loc[mask, 'in_ramadan_window'] = 1
                elif cat == 'eid':
                    df.loc[mask, 'in_eid_window'] = 1

        return df
