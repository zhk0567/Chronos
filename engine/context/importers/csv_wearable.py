from __future__ import annotations

import csv
import json
from pathlib import Path


def parse_wearable_csv(
    csv_path: Path,
    date_col: str = "date",
    steps_col: str = "steps",
    sleep_col: str = "sleep",
    hr_col: str = "hr",
) -> dict[str, dict]:
    daily: dict[str, dict] = {}
    with csv_path.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date = row.get(date_col, "")[:10]
            if not date:
                continue
            entry: dict = {}
            if steps_col in row and row[steps_col]:
                try:
                    entry["steps"] = float(row[steps_col])
                except ValueError:
                    pass
            if sleep_col in row and row[sleep_col]:
                try:
                    entry["sleepHours"] = float(row[sleep_col])
                except ValueError:
                    pass
            if hr_col in row and row[hr_col]:
                try:
                    entry["restingHr"] = float(row[hr_col])
                except ValueError:
                    pass
            if entry:
                daily[date] = entry
    return daily


def save_wearable_daily(data_dir: Path, daily: dict[str, dict]) -> int:
    out_dir = data_dir / "context" / "wearable"
    out_dir.mkdir(parents=True, exist_ok=True)
    for date, data in daily.items():
        (out_dir / f"{date}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return len(daily)
