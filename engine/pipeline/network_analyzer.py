from __future__ import annotations

from collections import defaultdict

import numpy as np

from llm.ollama_client import make_evidence
from schemas.models import (
    EmotionPoint,
    EvidenceSource,
    InfoUnit,
    InfoUnitType,
    PersonNode,
    RelationshipType,
)
from utils.person_names import build_canonical_map, normalize_person_name


def analyze_network(
    units: list[InfoUnit],
    emotion_series: list[EmotionPoint],
) -> list[PersonNode]:
    emotion_by_date = {p.date: p for p in emotion_series}
    raw_names: list[str] = []

    for unit in units:
        if unit.unit_type != InfoUnitType.EVENT_PACKAGE or not unit.event_package:
            continue
        for person in unit.event_package.participants or []:
            if person and len(person.strip()) >= 1:
                raw_names.append(person.strip())

    canonical_map = build_canonical_map(raw_names)
    person_dates: dict[str, list[str]] = defaultdict(list)
    person_evidence: dict[str, list] = defaultdict(list)

    for unit in units:
        if unit.unit_type != InfoUnitType.EVENT_PACKAGE or not unit.event_package:
            continue
        participants = unit.event_package.participants or []
        for person in participants:
            if not person or len(person.strip()) < 1:
                continue
            canonical = normalize_person_name(person.strip(), canonical_map)
            person_dates[canonical].append(unit.date)
            person_evidence[canonical].append(
                make_evidence(
                    unit.date,
                    unit.source_span.text[:100],
                    char_offset=unit.source_span.char_offset,
                    source=EvidenceSource.EXPLICIT,
                )
            )

    nodes: list[PersonNode] = []
    for name, dates in person_dates.items():
        if len(dates) < 2:
            continue
        tones = [emotion_by_date[d].valence for d in dates if d in emotion_by_date]
        if not tones:
            continue
        avg_tone = float(np.mean(tones))
        tone_var = float(np.var(tones))

        if len(tones) >= 4:
            early = float(np.mean(tones[: len(tones) // 2]))
            late = float(np.mean(tones[len(tones) // 2 :]))
            if late - early > 0.15:
                trend = "improving"
            elif early - late > 0.15:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        if tone_var > 0.3:
            rel_type = RelationshipType.AMBIVALENT
        elif avg_tone > 0.1:
            rel_type = RelationshipType.POSITIVE
        elif avg_tone < -0.1:
            rel_type = RelationshipType.NEGATIVE
        else:
            rel_type = RelationshipType.AMBIVALENT

        nodes.append(
            PersonNode(
                name=name,
                mentionCount=len(dates),
                emotionalTone=round(avg_tone, 3),
                toneTrend=trend,
                relationshipType=rel_type,
                evidence=person_evidence[name][:5],
            )
        )

    nodes.sort(key=lambda n: -n.mention_count)
    return nodes[:20]
