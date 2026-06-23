from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ASLEEP_VALUES = {
    "HKCategoryValueSleepAnalysisAsleep",
    "HKCategoryValueSleepAnalysisAsleepUnspecified",
    "HKCategoryValueSleepAnalysisAsleepCore",
    "HKCategoryValueSleepAnalysisAsleepDeep",
    "HKCategoryValueSleepAnalysisAsleepREM",
}


def _parse_apple_datetime(raw: str) -> datetime | None:
    if not raw:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S %z", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw.strip(), fmt)
        except ValueError:
            continue
    return None


def _sleep_hours(start_raw: str, end_raw: str) -> float:
    start = _parse_apple_datetime(start_raw)
    end = _parse_apple_datetime(end_raw)
    if not start or not end or end <= start:
        return 0.0
    return (end - start).total_seconds() / 3600.0


def parse_apple_health(xml_path: Path) -> dict[str, dict]:
    """Parse Apple Health export.xml into daily aggregates."""
    daily: dict[str, dict] = defaultdict(
        lambda: {"steps": 0, "sleepHours": 0.0, "restingHr": None, "_hr_values": []}
    )

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception:
        return {}

    for record in root.findall(".//Record"):
        rtype = record.get("type", "")
        start_raw = record.get("startDate", "")
        start = start_raw[:10]
        value = record.get("value")

        if "StepCount" in rtype and start and value:
            try:
                daily[start]["steps"] += float(value)
            except ValueError:
                pass
        elif "SleepAnalysis" in rtype and start:
            sleep_val = value or ""
            if sleep_val in ASLEEP_VALUES or "Asleep" in sleep_val:
                hours = _sleep_hours(start_raw, record.get("endDate", ""))
                if hours > 0:
                    daily[start]["sleepHours"] += hours
        elif "RestingHeartRate" in rtype and start and value:
            try:
                daily[start]["_hr_values"].append(float(value))
            except ValueError:
                pass

    result: dict[str, dict] = {}
    for date, data in daily.items():
        hr_values = data.pop("_hr_values", [])
        if hr_values:
            data["restingHr"] = round(sum(hr_values) / len(hr_values), 1)
        if data["sleepHours"]:
            data["sleepHours"] = round(data["sleepHours"], 2)
        clean: dict = {}
        if data["steps"]:
            clean["steps"] = data["steps"]
        if data.get("sleepHours"):
            clean["sleepHours"] = data["sleepHours"]
        if data.get("restingHr") is not None:
            clean["restingHr"] = data["restingHr"]
        if clean:
            result[date] = clean

    return result


def save_wearable_daily(data_dir: Path, daily: dict[str, dict]) -> int:
    out_dir = data_dir / "context" / "wearable"
    out_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for date, data in daily.items():
        path = out_dir / f"{date}.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        count += 1
    return count
