from __future__ import annotations

import json
from pathlib import Path

from context.geocoder import get_location
from context.rhythm_tagger import tag_rhythm
from context.weather_client import fetch_weather_range, load_cached_weather
from schemas.models import (
    DailyContext,
    DigitalContext,
    InfoUnit,
    LocationContext,
    WearableContext,
    WeatherContext,
)


def _load_json_dir(data_dir: Path, sub: str, date: str) -> dict | None:
    path = data_dir / "context" / sub / f"{date}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def align_contexts(
    data_dir: Path,
    dates: list[str],
    units: list[InfoUnit] | None = None,
) -> list[DailyContext]:
    if not dates:
        return []

    sorted_dates = sorted(set(dates))
    loc = get_location(data_dir)
    weather_by_date: dict[str, WeatherContext] = {}

    if loc:
        lat, lng = loc
        weather_by_date = fetch_weather_range(
            data_dir, lat, lng, sorted_dates[0], sorted_dates[-1]
        )

    contexts: list[DailyContext] = []

    for date in sorted_dates:
        missing: list[str] = []

        w = weather_by_date.get(date) or load_cached_weather(data_dir, date)
        if not w or (w.temp is None and w.humidity is None):
            missing.append("weather")

        rhythm = tag_rhythm(date)

        wearable_raw = _load_json_dir(data_dir, "wearable", date)
        wearable = WearableContext(**wearable_raw) if wearable_raw else None
        if not wearable:
            missing.append("wearable")

        digital_raw = _load_json_dir(data_dir, "digital", date)
        digital = DigitalContext(**digital_raw) if digital_raw else None
        if not digital:
            missing.append("digital")

        location_raw = _load_json_dir(data_dir, "location", date)
        location = LocationContext(**location_raw) if location_raw else None
        if not location:
            missing.append("location")

        ctx = DailyContext(
            date=date,
            weather=w,
            rhythm=rhythm,
            wearable=wearable,
            digital=digital,
            location=location,
            missingFlags=missing,
        )
        contexts.append(ctx)

    if units:
        ctx_by_date = {c.date: c for c in contexts}
        for unit in units:
            ctx = ctx_by_date.get(unit.date)
            if not ctx:
                continue
            tags: dict = {}
            if ctx.weather:
                tags["weather"] = ctx.weather.model_dump(by_alias=True)
            if ctx.rhythm:
                tags["rhythm"] = ctx.rhythm.model_dump(by_alias=True)
            if ctx.wearable:
                tags["sleep"] = ctx.wearable.sleep_hours
                tags["steps"] = ctx.wearable.steps
            if ctx.location:
                tags["location"] = ctx.location.primary_place
            unit.context_tags = tags

    return contexts


def compute_completeness(contexts: list[DailyContext]) -> dict[str, float]:
    if not contexts:
        return {"weather": 0, "wearable": 0, "digital": 0, "location": 0, "rhythm": 0}
    n = len(contexts)
    return {
        "weather": sum(1 for c in contexts if c.weather and c.weather.temp is not None) / n,
        "wearable": sum(1 for c in contexts if c.wearable) / n,
        "digital": sum(1 for c in contexts if c.digital) / n,
        "location": sum(1 for c in contexts if c.location) / n,
        "rhythm": 1.0,
    }
