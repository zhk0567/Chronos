from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

# Common Chinese cities (lat, lng)
CITY_COORDS: dict[str, tuple[float, float]] = {
    "洛阳": (34.6197, 112.4540),
    "北京": (39.9042, 116.4074),
    "上海": (31.2304, 121.4737),
    "广州": (23.1291, 113.2644),
    "深圳": (22.5431, 114.0579),
    "杭州": (30.2741, 120.1551),
    "成都": (30.5728, 104.0668),
    "武汉": (30.5928, 114.3055),
    "西安": (34.3416, 108.9398),
    "南京": (32.0603, 118.7969),
    "重庆": (29.4316, 106.9123),
    "天津": (39.3434, 117.3616),
    "苏州": (31.2989, 120.5853),
    "郑州": (34.7466, 113.6254),
    "长沙": (28.2282, 112.9388),
    "青岛": (36.0671, 120.3826),
    "厦门": (24.4798, 118.0894),
    "大连": (38.9140, 121.6147),
    "沈阳": (41.8057, 123.4328),
    "哈尔滨": (45.8038, 126.5349),
    "昆明": (25.0389, 102.7183),
}


def geocode_city(city: str) -> Optional[tuple[float, float]]:
    city = city.strip().replace("市", "")
    if city in CITY_COORDS:
        return CITY_COORDS[city]
    for name, coords in CITY_COORDS.items():
        if name in city or city in name:
            return coords
    return None


def load_settings(data_dir: Path) -> dict:
    path = data_dir / "settings.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def get_location(data_dir: Path) -> Optional[tuple[float, float]]:
    settings = load_settings(data_dir)
    lat = settings.get("latitude")
    lng = settings.get("longitude")
    if lat is not None and lng is not None:
        return float(lat), float(lng)
    city = settings.get("residentCity", "")
    if city:
        return geocode_city(city)
    return None
