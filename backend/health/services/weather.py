"""Daily weather from Open-Meteo (free, no key). Used to look for pressure and humidity patterns."""
import logging
from collections import defaultdict
from datetime import date, timedelta

import requests

log = logging.getLogger(__name__)
FORECAST = "https://api.open-meteo.com/v1/forecast"
GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"


def geocode(query):
    try:
        r = requests.get(GEOCODE, params={"name": query, "count": 5, "language": "en", "format": "json"}, timeout=6)
        r.raise_for_status()
        return [
            {"name": f"{x['name']}, {x.get('admin1', '')}, {x.get('country_code', '')}".replace(", ,", ","),
             "latitude": x["latitude"], "longitude": x["longitude"], "timezone": x.get("timezone")}
            for x in r.json().get("results", [])
        ]
    except requests.RequestException as exc:
        log.warning("Geocoding failed: %s", exc)
        return []


def sync_weather(user, past_days=30):
    from health.models import WeatherDay
    if user.latitude is None or user.longitude is None:
        return 0
    try:
        r = requests.get(FORECAST, params={
            "latitude": user.latitude, "longitude": user.longitude,
            "hourly": "surface_pressure,relative_humidity_2m",
            "daily": "temperature_2m_max,temperature_2m_min",
            "past_days": past_days, "forecast_days": 1, "timezone": user.timezone or "auto",
        }, timeout=8)
        r.raise_for_status()
        data = r.json()
    except requests.RequestException as exc:
        log.warning("Weather fetch failed for user %s: %s", user.pk, exc)
        return 0

    pressure, humidity = defaultdict(list), defaultdict(list)
    hourly = data.get("hourly", {})
    for t, p, h in zip(hourly.get("time", []), hourly.get("surface_pressure", []), hourly.get("relative_humidity_2m", [])):
        d = t[:10]
        if p is not None:
            pressure[d].append(p)
        if h is not None:
            humidity[d].append(h)
    daily = data.get("daily", {})
    count, prev_p = 0, None
    for d, tmax, tmin in zip(daily.get("time", []), daily.get("temperature_2m_max", []), daily.get("temperature_2m_min", [])):
        p = round(sum(pressure[d]) / len(pressure[d]), 1) if pressure[d] else None
        h = round(sum(humidity[d]) / len(humidity[d]), 1) if humidity[d] else None
        change = round(p - prev_p, 1) if (p is not None and prev_p is not None) else None
        WeatherDay.objects.update_or_create(
            user=user, date=date.fromisoformat(d),
            defaults={"temp_max": tmax, "temp_min": tmin, "pressure_mean": p, "pressure_change": change, "humidity_mean": h},
        )
        prev_p = p if p is not None else prev_p
        count += 1
    return count


def maybe_sync(user):
    from config.utils import user_today
    latest = user.weather.order_by("-date").first()
    if latest is None or latest.date < user_today(user) - timedelta(days=0):
        sync_weather(user, past_days=31 if latest is None else 3)
