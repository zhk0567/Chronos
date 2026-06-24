from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from utils.geo_cluster import cluster_centroid, cluster_points, infer_place_type


def parse_gpx(gpx_path: Path) -> dict[str, dict]:
    daily_points: dict[str, list[tuple[float, float]]] = defaultdict(list)
    daily_track_names: dict[str, str] = {}
    try:
        import gpxpy

        with gpx_path.open(encoding="utf-8") as f:
            gpx = gpxpy.parse(f)
        for track in gpx.tracks:
            track_label = track.name or ""
            for segment in track.segments:
                for point in segment.points:
                    if point.time:
                        ds = point.time.strftime("%Y-%m-%d")
                        daily_points[ds].append((point.latitude, point.longitude))
                        if track_label and ds not in daily_track_names:
                            daily_track_names[ds] = track_label
    except Exception:
        pass

    daily: dict[str, dict] = {}
    for ds, points in daily_points.items():
        if not points:
            continue
        clusters = cluster_points(points)
        dominant = clusters[0]
        lat, lon = cluster_centroid(dominant)
        place_type = infer_place_type(clusters, len(points))
        name = daily_track_names.get(ds) or f"{lat:.4f},{lon:.4f}"
        daily[ds] = {
            "primaryPlace": name,
            "placeType": place_type,
            "clusterCount": len(clusters),
            "pointCount": len(points),
        }
    return daily


def save_location_daily(data_dir: Path, daily: dict[str, dict]) -> int:
    out_dir = data_dir / "context" / "location"
    out_dir.mkdir(parents=True, exist_ok=True)
    for date, data in daily.items():
        (out_dir / f"{date}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return len(daily)
