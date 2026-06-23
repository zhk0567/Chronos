from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path


def parse_screen_time_csv(
    csv_path: Path,
    date_col: str = "date",
    minutes_col: str = "minutes",
    app_col: str = "app",
) -> dict[str, dict]:
    daily: dict[str, dict] = defaultdict(lambda: {"screenTimeMin": 0, "topApps": []})
    with csv_path.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date = (row.get(date_col) or "")[:10]
            if not date:
                continue
            mins = row.get(minutes_col)
            app = row.get(app_col)
            if mins:
                try:
                    daily[date]["screenTimeMin"] += float(mins)
                except ValueError:
                    pass
            if app and app not in daily[date]["topApps"]:
                daily[date]["topApps"].append(app)
    return {k: dict(v) for k, v in daily.items()}


def save_digital_daily(data_dir: Path, daily: dict[str, dict]) -> int:
    out_dir = data_dir / "context" / "digital"
    out_dir.mkdir(parents=True, exist_ok=True)
    for date, data in daily.items():
        (out_dir / f"{date}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return len(daily)
