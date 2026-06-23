from __future__ import annotations

import json
import sys
from pathlib import Path

# CLI: python -m context.import_cli <type> <source> <data_dir> [column_mapping_json]


def main():
    if len(sys.argv) < 4:
        print(json.dumps({"error": "usage: import_cli <type> <source> <data_dir> [mapping_json]"}))
        sys.exit(1)

    import_type = sys.argv[1]
    source = Path(sys.argv[2])
    data_dir = Path(sys.argv[3])
    mapping: dict = {}
    if len(sys.argv) >= 5 and sys.argv[4]:
        try:
            mapping = json.loads(sys.argv[4])
        except json.JSONDecodeError:
            print(json.dumps({"error": "invalid mapping JSON"}))
            sys.exit(1)

    count = 0
    if import_type == "apple_health":
        from context.importers.apple_health import parse_apple_health, save_wearable_daily

        daily = parse_apple_health(source)
        count = save_wearable_daily(data_dir, daily)
    elif import_type == "wearable_csv":
        from context.importers.csv_wearable import parse_wearable_csv, save_wearable_daily

        daily = parse_wearable_csv(
            source,
            date_col=mapping.get("date", "date"),
            steps_col=mapping.get("steps", "steps"),
            sleep_col=mapping.get("sleep", "sleep"),
            hr_col=mapping.get("hr", "hr"),
        )
        count = save_wearable_daily(data_dir, daily)
    elif import_type == "screen_time":
        from context.importers.screen_time import parse_screen_time_csv, save_digital_daily

        daily = parse_screen_time_csv(
            source,
            date_col=mapping.get("date", "date"),
            minutes_col=mapping.get("minutes", "minutes"),
            app_col=mapping.get("app", "app"),
        )
        count = save_digital_daily(data_dir, daily)
    elif import_type == "gpx":
        from context.importers.gpx_location import parse_gpx, save_location_daily

        daily = parse_gpx(source)
        count = save_location_daily(data_dir, daily)
    elif import_type == "manual_location":
        from context.importers.manual_location import parse_manual_location, save_location_daily

        daily = parse_manual_location(source)
        count = save_location_daily(data_dir, daily)
    else:
        print(json.dumps({"error": f"unknown type {import_type}"}))
        sys.exit(1)

    print(json.dumps({"daysImported": count, "type": import_type}))


if __name__ == "__main__":
    main()
