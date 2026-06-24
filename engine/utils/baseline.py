from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from schemas.models import EmotionPoint


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


def save_emotion_baseline(data_dir: Path, emotion_series: list[EmotionPoint]) -> None:
    if not emotion_series:
        return
    scores = [p.score for p in emotion_series]
    out_dir = data_dir / "baseline"
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "updatedAt": emotion_series[-1].date,
        "sampleCount": len(scores),
        "medianScore": float(np.median(scores)),
        "meanScore": float(np.mean(scores)),
        "stdScore": float(np.std(scores)),
        "scoreByDate": {p.date: p.score for p in emotion_series},
    }
    (out_dir / "emotion.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_emotion_baseline(data_dir: Path) -> dict | None:
    path = data_dir / "baseline" / "emotion.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
