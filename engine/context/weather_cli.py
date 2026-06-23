from __future__ import annotations

import json
import sys

from context.weather_client import test_weather_connection


def main():
    if len(sys.argv) < 3:
        print(json.dumps({"ok": False, "error": "usage: weather_cli <lat> <lng>"}))
        sys.exit(1)
    try:
        lat = float(sys.argv[1])
        lng = float(sys.argv[2])
    except ValueError:
        print(json.dumps({"ok": False, "error": "invalid coordinates"}))
        sys.exit(1)
    print(json.dumps(test_weather_connection(lat, lng)))


if __name__ == "__main__":
    main()
