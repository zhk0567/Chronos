from __future__ import annotations

import numpy as np

from llm.ollama_client import make_evidence
from schemas.models import DailyContext, EmotionPoint, EvidenceSource, InfoUnit, InfoUnitType, SpaceEmotionLink


def analyze_space_emotion(
    contexts: list[DailyContext],
    emotion_series: list[EmotionPoint],
    units: list[InfoUnit],
) -> list[SpaceEmotionLink]:
    emotion_by_date = {p.date: p.valence for p in emotion_series}
    place_scores: dict[str, list[tuple[str, float]]] = {}

    for unit in units:
        if unit.unit_type != InfoUnitType.EVENT_PACKAGE:
            continue
        place = None
        if unit.event_package and unit.event_package.location:
            place = unit.event_package.location
        elif unit.context_tags.get("location"):
            place = str(unit.context_tags["location"])
        if not place or len(place) < 2:
            continue
        valence = emotion_by_date.get(unit.date, 0)
        place_scores.setdefault(place, []).append((unit.date, valence))

    for ctx in contexts:
        if ctx.location and ctx.location.primary_place:
            place = ctx.location.primary_place
            valence = emotion_by_date.get(ctx.date, 0)
            place_scores.setdefault(place, []).append((ctx.date, valence))

    links: list[SpaceEmotionLink] = []
    for place, entries in place_scores.items():
        if len(entries) < 2:
            continue
        tones = [v for _, v in entries]
        avg = float(np.mean(tones))
        if avg > 0.15:
            link_type = "restorative"
        elif avg < -0.15:
            link_type = "stressful"
        else:
            link_type = "neutral"
        links.append(
            SpaceEmotionLink(
                place=place,
                emotionalTone=round(avg, 3),
                linkType=link_type,
                evidence=[
                    make_evidence(d, place[:80], source=EvidenceSource.EXPLICIT) for d, _ in entries[:3]
                ],
            )
        )

    links.sort(key=lambda x: -abs(x.emotional_tone))
    return links[:10]
