from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import httpx

from schemas.models import WeatherContext

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def weather_cache_path(data_dir: Path, date: str) -> Path:
    return data_dir / "context" / "weather" / f"{date}.json"


def load_cached_weather(data_dir: Path, date: str) -> Optional[WeatherContext]:
    path = weather_cache_path(data_dir, date)
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return WeatherContext(**raw)
    except Exception:
        return None


def save_weather_cache(data_dir: Path, date: str, weather: WeatherContext) -> None:
    path = weather_cache_path(data_dir, date)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(weather.model_dump(by_alias=True), ensure_ascii=False), encoding="utf-8")


def fetch_weather_range(
    data_dir: Path,
    lat: float,
    lng: float,
    start_date: str,
    end_date: str,
) -> dict[str, WeatherContext]:
    cache_dir = data_dir / "context" / "weather"
    cache_dir.mkdir(parents=True, exist_ok=True)

    missing_dates: list[str] = []
    result: dict[str, WeatherContext] = {}

    from datetime import datetime, timedelta

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    d = start
    while d <= end:
        ds = d.strftime("%Y-%m-%d")
        cached = load_cached_weather(data_dir, ds)
        if cached:
            result[ds] = cached
        else:
            missing_dates.append(ds)
        d += timedelta(days=1)

    if not missing_dates:
        return result

    try:
        params = {
            "latitude": lat,
            "longitude": lng,
            "start_date": min(missing_dates),
            "end_date": max(missing_dates),
            "daily": "temperature_2m_mean,relative_humidity_2m_mean,precipitation_sum,sunshine_duration",
            "timezone": "Asia/Shanghai",
        }
        with httpx.Client(timeout=30.0) as client:
            res = client.get(ARCHIVE_URL, params=params)
            res.raise_for_status()
            data = res.json()

        daily = data.get("daily", {})
        dates = daily.get("time", [])
        temps = daily.get("temperature_2m_mean", [])
        humids = daily.get("relative_humidity_2m_mean", [])
        precips = daily.get("precipitation_sum", [])
        suns = daily.get("sunshine_duration", [])

        for i, ds in enumerate(dates):
            if ds not in missing_dates:
                continue
            w = WeatherContext(
                temp=temps[i] if i < len(temps) else None,
                humidity=humids[i] if i < len(humids) else None,
                precipitation=precips[i] if i < len(precips) else None,
                sunshine=(suns[i] / 3600 if suns[i] is not None else None) if i < len(suns) else None,
            )
            save_weather_cache(data_dir, ds, w)
            result[ds] = w
    except Exception:
        for ds in missing_dates:
            if ds not in result:
                result[ds] = WeatherContext()

    return result


def test_weather_connection(lat: float, lng: float) -> dict:
    """Fetch one recent day of weather to verify API connectivity."""
    from datetime import datetime, timedelta

    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    try:
        params = {
            "latitude": lat,
            "longitude": lng,
            "start_date": yesterday,
            "end_date": yesterday,
            "daily": "temperature_2m_mean",
            "timezone": "Asia/Shanghai",
        }
        with httpx.Client(timeout=15.0) as client:
            res = client.get(ARCHIVE_URL, params=params)
            res.raise_for_status()
            data = res.json()
        temps = data.get("daily", {}).get("temperature_2m_mean", [])
        sample = temps[0] if temps else None
        return {"ok": True, "sampleTemp": sample, "date": yesterday}
    except Exception as e:
        return {"ok": False, "error": str(e), "sampleTemp": None}
