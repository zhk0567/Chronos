from __future__ import annotations

import json
from pathlib import Path

from context.geocoder import geocode_city, load_settings
from context.weather_client import fetch_weather_range


def save_settings_coords(data_dir: Path, lat: float, lng: float) -> None:
    """Persist geocoded coordinates back to settings.json."""
    path = data_dir / "settings.json"
    settings = load_settings(data_dir)
    settings["latitude"] = lat
    settings["longitude"] = lng
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")


def ingest_context(data_dir: Path, dates: list[str]) -> dict:
    """
    Load settings, geocode if needed, prefetch weather cache for diary date range.
    Returns resolved settings dict.
    """
    settings = load_settings(data_dir)

    if settings.get("residentCity") and (
        settings.get("latitude") is None or settings.get("longitude") is None
    ):
        coords = geocode_city(settings["residentCity"])
        if coords:
            lat, lng = coords
            settings["latitude"] = lat
            settings["longitude"] = lng
            save_settings_coords(data_dir, lat, lng)

    if dates and settings.get("latitude") is not None and settings.get("longitude") is not None:
        sorted_dates = sorted(set(dates))
        fetch_weather_range(
            data_dir,
            float(settings["latitude"]),
            float(settings["longitude"]),
            sorted_dates[0],
            sorted_dates[-1],
        )

    return settings
