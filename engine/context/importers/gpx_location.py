from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def parse_gpx(gpx_path: Path) -> dict[str, dict]:
    daily: dict[str, dict] = defaultdict(lambda: {"primaryPlace": None, "placeType": "unknown"})
    try:
        import gpxpy

        with gpx_path.open(encoding="utf-8") as f:
            gpx = gpxpy.parse(f)
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    if point.time:
                        ds = point.time.strftime("%Y-%m-%d")
                        name = track.name or f"{point.latitude:.2f},{point.longitude:.2f}"
                        daily[ds]["primaryPlace"] = name
    except Exception:
        pass
    return dict(daily)


def save_location_daily(data_dir: Path, daily: dict[str, dict]) -> int:
    out_dir = data_dir / "context" / "location"
    out_dir.mkdir(parents=True, exist_ok=True)
    for date, data in daily.items():
        (out_dir / f"{date}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return len(daily)
