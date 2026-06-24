from __future__ import annotations

from collections import defaultdict


def cluster_points(
    points: list[tuple[float, float]],
    eps_deg: float = 0.003,
) -> list[list[tuple[float, float]]]:
    """Greedy spatial clustering on (lat, lon) in degrees."""
    clusters: list[list[tuple[float, float]]] = []
    for lat, lon in points:
        placed = False
        for cluster in clusters:
            clat = sum(p[0] for p in cluster) / len(cluster)
            clon = sum(p[1] for p in cluster) / len(cluster)
            if abs(lat - clat) + abs(lon - clon) <= eps_deg:
                cluster.append((lat, lon))
                placed = True
                break
        if not placed:
            clusters.append([(lat, lon)])
    clusters.sort(key=len, reverse=True)
    return clusters


def cluster_centroid(cluster: list[tuple[float, float]]) -> tuple[float, float]:
    lat = sum(p[0] for p in cluster) / len(cluster)
    lon = sum(p[1] for p in cluster) / len(cluster)
    return lat, lon


def infer_place_type(clusters: list[list[tuple[float, float]]], total: int) -> str:
    if not clusters or total == 0:
        return "unknown"
    dominant = len(clusters[0]) / total
    if dominant >= 0.75:
        return "routine"
    if len(clusters) >= 3:
        return "multi_stop"
    return "transit"
