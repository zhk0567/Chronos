from __future__ import annotations

from pipeline.anchor_detector import detect_anchors
from schemas.models import (
    DiaryEntry,
    EmotionPoint,
    EmergenceType,
    InfoUnit,
    InfoUnitType,
    MorphResult,
    MorphType,
    SourceSpan,
    ThoughtAnchor,
)


def _thought_unit(date: str, concern: str, text: str) -> InfoUnit:
    return InfoUnit(
        id=f"u-{date}",
        date=date,
        unitType=InfoUnitType.THOUGHT_ANCHOR,
        morphType=MorphType.INTROSPECTIVE,
        sourceSpan=SourceSpan(
            date=date,
            paragraphIndex=0,
            charOffset=0,
            charLength=len(text),
            text=text,
        ),
        thoughtAnchor=ThoughtAnchor(coreConcern=concern),
    )


def test_contradiction_anchor_on_opposing_sentiment():
    entries = [
        DiaryEntry(date="2026-01-01", content="对工作很满意，充满干劲"),
        DiaryEntry(date="2026-01-15", content="对工作很失望，后悔选择这条路"),
    ]
    units = [
        _thought_unit("2026-01-01", "工作发展", "对工作很满意，充满干劲"),
        _thought_unit("2026-01-15", "工作发展", "对工作很失望，后悔选择这条路"),
    ]
    emotion = [
        EmotionPoint(date="2026-01-01", score=7.0, valence=0.5, arousal=0.3, confidence=0.8),
        EmotionPoint(date="2026-01-15", score=4.0, valence=-0.4, arousal=0.5, confidence=0.8),
    ]
    anchors = detect_anchors(entries, [], units, emotion)
    types = {a.emergence_type for a in anchors}
    assert EmergenceType.CONTRADICTION in types


def test_structure_anchor_skips_consecutive_days():
    morphs = [
        MorphResult(date="2026-01-01", paragraphIndex=0, type=MorphType.NARRATIVE),
        MorphResult(date="2026-01-02", paragraphIndex=0, type=MorphType.INTROSPECTIVE),
        MorphResult(date="2026-01-06", paragraphIndex=0, type=MorphType.NARRATIVE),
        MorphResult(date="2026-01-10", paragraphIndex=0, type=MorphType.SKETCH),
    ]
    entries = [DiaryEntry(date=m.date, content="x") for m in morphs]
    anchors = detect_anchors(entries, morphs, [], [])
    structure = [a for a in anchors if a.emergence_type == EmergenceType.STRUCTURE]
    assert len(structure) == 1
    assert structure[0].date == "2026-01-06"
