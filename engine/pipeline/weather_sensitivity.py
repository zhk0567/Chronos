from __future__ import annotations

import numpy as np
from scipy import stats

from llm.ollama_client import make_evidence
from schemas.models import DailyContext, EmotionPoint, EvidenceSource, WeatherSensitivity


def analyze_weather_sensitivity(
    contexts: list[DailyContext],
    emotion_series: list[EmotionPoint],
) -> list[WeatherSensitivity]:
    if len(emotion_series) < 8:
        return []

    emotion_by_date = {p.date: p.score for p in emotion_series}
    ctx_by_date = {c.date: c for c in contexts}
    results: list[WeatherSensitivity] = []

    pairs: dict[str, tuple[list[float], list[float]]] = {
        "温度": ([], []),
        "降水": ([], []),
        "日照": ([], []),
        "湿度": ([], []),
    }

    for date, score in emotion_by_date.items():
        ctx = ctx_by_date.get(date)
        if not ctx or not ctx.weather:
            continue
        w = ctx.weather
        if w.temp is not None:
            pairs["温度"][0].append(w.temp)
            pairs["温度"][1].append(score)
        if w.precipitation is not None:
            pairs["降水"][0].append(w.precipitation)
            pairs["降水"][1].append(score)
        if w.sunshine is not None:
            pairs["日照"][0].append(w.sunshine)
            pairs["日照"][1].append(score)
        if w.humidity is not None:
            pairs["湿度"][0].append(w.humidity)
            pairs["湿度"][1].append(score)

    for metric, (xs, ys) in pairs.items():
        if len(xs) < 8:
            continue
        r, p = stats.pearsonr(xs, ys)
        if np.isnan(r):
            continue
        direction = "正相关" if r > 0 else "负相关"
        results.append(
            WeatherSensitivity(
                metric=metric,
                coefficient=round(float(r), 3),
                confidence=round(min(0.85, 0.4 + len(xs) * 0.03), 2),
                description=f"{metric}与情绪呈{direction}（r={r:.2f}，p={p:.3f}）",
                evidence=[make_evidence(emotion_series[0].date, f"{metric}敏感度", source=EvidenceSource.INFERRED)],
            )
        )

    return results
