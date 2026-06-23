from __future__ import annotations

import numpy as np


def rolling_zscore(values: list[float], window: int = 5) -> list[float]:
    if len(values) < 2:
        return [0.0] * len(values)
    arr = np.array(values, dtype=float)
    result: list[float] = []
    for i in range(len(arr)):
        start = max(0, i - window + 1)
        segment = arr[start : i + 1]
        mean = float(np.mean(segment))
        std = float(np.std(segment))
        if std < 0.01:
            result.append(0.0)
        else:
            result.append(float((arr[i] - mean) / std))
    return result


def dynamic_baseline(values: list[float], span: int = 7) -> list[float]:
    if not values:
        return []
    arr = np.array(values, dtype=float)
    baselines: list[float] = []
    for i in range(len(arr)):
        start = max(0, i - span)
        baselines.append(float(np.median(arr[start:i])) if i > 0 else float(arr[0]))
    return baselines
