from __future__ import annotations

import uuid

from llm.ollama_client import make_evidence
from schemas.models import DailyContext, EmotionPoint, EvidenceSource, InteractionEffect


def analyze_interactions(
    contexts: list[DailyContext],
    emotion_series: list[EmotionPoint],
) -> list[InteractionEffect]:
    if len(emotion_series) < 10:
        return []

    emotion_by_date = {p.date: p.score for p in emotion_series}
    ctx_by_date = {c.date: c for c in contexts}
    effects: list[InteractionEffect] = []

    # Risk: rain + poor sleep
    rain_sleep_low: list[float] = []
    rain_sleep_ok: list[float] = []
    for date, score in emotion_by_date.items():
        ctx = ctx_by_date.get(date)
        if not ctx or not ctx.weather:
            continue
        rainy = (ctx.weather.precipitation or 0) > 1
        poor_sleep = ctx.wearable and ctx.wearable.sleep_hours is not None and ctx.wearable.sleep_hours < 6
        if rainy and poor_sleep:
            rain_sleep_low.append(score)
        elif rainy:
            rain_sleep_ok.append(score)

    if len(rain_sleep_low) >= 3 and len(rain_sleep_ok) >= 3:
        import numpy as np

        low_mean = float(np.mean(rain_sleep_low))
        ok_mean = float(np.mean(rain_sleep_ok))
        if low_mean < ok_mean - 0.5:
            effects.append(
                InteractionEffect(
                    id=str(uuid.uuid4())[:8],
                    factors=["雨天", "睡眠不足"],
                    effectType="risk",
                    combinedEffect=round(ok_mean - low_mean, 2),
                    exceedsAdditive=True,
                    statement=f"雨天叠加睡眠不足时，情绪均值 {low_mean:.1f}，显著低于仅雨天 {ok_mean:.1f}",
                    confidence=0.55,
                    evidence=[make_evidence(d, "雨天+睡眠不足", source=EvidenceSource.INFERRED) for d in list(emotion_by_date.keys())[:2]],
                )
            )

    # Protective: weekend + good weather
    weekend_sunny: list[float] = []
    weekday: list[float] = []
    for date, score in emotion_by_date.items():
        ctx = ctx_by_date.get(date)
        if not ctx or not ctx.rhythm:
            continue
        sunny = ctx.weather and (ctx.weather.sunshine or 0) > 4
        is_weekend = ctx.rhythm.weekday >= 5
        if is_weekend and sunny:
            weekend_sunny.append(score)
        elif not is_weekend:
            weekday.append(score)

    if len(weekend_sunny) >= 3 and len(weekday) >= 5:
        import numpy as np

        ws = float(np.mean(weekend_sunny))
        wd = float(np.mean(weekday))
        if ws > wd + 0.5:
            effects.append(
                InteractionEffect(
                    id=str(uuid.uuid4())[:8],
                    factors=["周末", "日照充足"],
                    effectType="protective",
                    combinedEffect=round(ws - wd, 2),
                    exceedsAdditive=True,
                    statement=f"周末日照充足时情绪均值 {ws:.1f}，高于工作日 {wd:.1f}",
                    confidence=0.5,
                    evidence=[],
                )
            )

    return effects
