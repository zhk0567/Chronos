from __future__ import annotations

import json
from pathlib import Path


def parse_manual_location(source_path: Path) -> dict[str, dict]:
    """Parse manual location JSON (array or single object)."""
    raw = json.loads(source_path.read_text(encoding="utf-8"))
    items = raw if isinstance(raw, list) else [raw]
    daily: dict[str, dict] = {}
    for item in items:
        date = (item.get("date") or "")[:10]
        if not date:
            continue
        entry: dict = {}
        place = item.get("primaryPlace") or item.get("placeName") or item.get("place")
        if place:
            entry["primaryPlace"] = place
        place_type = item.get("placeType") or item.get("type")
        if place_type:
            entry["placeType"] = place_type
        if entry:
            daily[date] = entry
    return daily


def save_location_entry(data_dir: Path, date: str, primary_place: str, place_type: str) -> None:
    out_dir = data_dir / "context" / "location"
    out_dir.mkdir(parents=True, exist_ok=True)
    data = {"primaryPlace": primary_place, "placeType": place_type}
    (out_dir / f"{date}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def save_location_daily(data_dir: Path, daily: dict[str, dict]) -> int:
    out_dir = data_dir / "context" / "location"
    out_dir.mkdir(parents=True, exist_ok=True)
    for date, data in daily.items():
        (out_dir / f"{date}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return len(daily)
