from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta

import numpy as np

from llm.ollama_client import make_evidence
from utils.interpretation import morph_type_label
from schemas.models import (
    AnchorCard,
    DiaryEntry,
    EmotionPoint,
    EmergenceType,
    EvidenceSource,
    InfoUnit,
    InfoUnitType,
    MorphResult,
    MorphType,
)
from utils.baseline import rolling_zscore


def detect_anchors(
    entries: list[DiaryEntry],
    morphs: list[MorphResult],
    units: list[InfoUnit],
    emotion_series: list[EmotionPoint],
) -> list[AnchorCard]:
    anchors: list[AnchorCard] = []
    anchors.extend(_intensity_anchors(emotion_series, entries))
    anchors.extend(_frequency_anchors(units, entries))
    anchors.extend(_structure_anchors(morphs, entries))
    anchors.extend(_narrative_anchors(units, entries))
    anchors.extend(_silence_anchors(units, entries))
    anchors.extend(_contradiction_anchors(units, entries, emotion_series))
    return sorted(anchors, key=lambda a: a.date)


def _intensity_anchors(
    emotion_series: list[EmotionPoint],
    entries: list[DiaryEntry],
) -> list[AnchorCard]:
    anchors: list[AnchorCard] = []
    if len(emotion_series) < 3:
        return anchors
    scores = [p.score for p in emotion_series]
    zscores = rolling_zscore(scores, window=5)
    entry_map = {e.date: e for e in entries}

    for i, (point, z) in enumerate(zip(emotion_series, zscores)):
        if abs(z) >= 1.8:
            direction = "正向高峰" if z > 0 else "负向低谷"
            entry = entry_map.get(point.date)
            evidence = []
            if entry:
                evidence.append(
                    make_evidence(
                        point.date,
                        entry.content[:150],
                        char_offset=0,
                        char_length=min(150, len(entry.content)),
                        source=EvidenceSource.EXPLICIT,
                    )
                )
            anchors.append(
                AnchorCard(
                    id=str(uuid.uuid4())[:8],
                    date=point.date,
                    emergenceType=EmergenceType.INTENSITY,
                    title=f"情绪{direction}",
                    description=f"情绪分数 {point.score:.1f}，偏离个人基线 Z={z:.2f}",
                    confidence=min(0.9, 0.5 + abs(z) * 0.15),
                    evidence=evidence,
                )
            )
    return anchors


def _frequency_anchors(units: list[InfoUnit], entries: list[DiaryEntry]) -> list[AnchorCard]:
    anchors: list[AnchorCard] = []
    entity_counts: dict[str, list[str]] = defaultdict(list)

    for unit in units:
        if unit.event_package and unit.event_package.participants:
            for p in unit.event_package.participants:
                entity_counts[p].append(unit.date)
        if unit.thought_anchor and unit.thought_anchor.core_concern:
            entity_counts[unit.thought_anchor.core_concern[:20]].append(unit.date)

    for entity, dates in entity_counts.items():
        if len(dates) < 3:
            continue
        sorted_dates = sorted(set(dates))
        counts_by_month: Counter[str] = Counter()
        for d in sorted_dates:
            counts_by_month[d[:7]] += 1
        if len(counts_by_month) < 2:
            continue
        months = sorted(counts_by_month.keys())
        prev, curr = counts_by_month[months[-2]], counts_by_month[months[-1]]
        if curr >= prev * 2 and curr >= 3:
            anchors.append(
                AnchorCard(
                    id=str(uuid.uuid4())[:8],
                    date=sorted_dates[-1],
                    emergenceType=EmergenceType.FREQUENCY,
                    title=f"「{entity}」频率涌现",
                    description=f"「{entity}」在近期密集出现（{curr} 次/月 vs 前期 {prev} 次）",
                    confidence=0.55,
                    evidence=[make_evidence(sorted_dates[-1], f"提及 {entity}", source=EvidenceSource.INFERRED)],
                )
            )
    return anchors


def _structure_anchors(morphs: list[MorphResult], entries: list[DiaryEntry]) -> list[AnchorCard]:
    anchors: list[AnchorCard] = []
    by_date: dict[str, list[MorphType]] = defaultdict(list)
    for m in morphs:
        by_date[m.date].append(m.type)

    dates = sorted(by_date.keys())
    last_structure_date: str | None = None
    for i in range(1, len(dates)):
        gap_days = (
            datetime.strptime(dates[i], "%Y-%m-%d") - datetime.strptime(dates[i - 1], "%Y-%m-%d")
        ).days
        if gap_days < 3:
            continue
        if last_structure_date:
            since_last = (
                datetime.strptime(dates[i], "%Y-%m-%d")
                - datetime.strptime(last_structure_date, "%Y-%m-%d")
            ).days
            if since_last < 7:
                continue
        prev_dominant = Counter(by_date[dates[i - 1]]).most_common(1)[0][0]
        curr_dominant = Counter(by_date[dates[i]]).most_common(1)[0][0]
        if prev_dominant != curr_dominant:
            last_structure_date = dates[i]
            anchors.append(
                AnchorCard(
                    id=str(uuid.uuid4())[:8],
                    date=dates[i],
                    emergenceType=EmergenceType.STRUCTURE,
                    title="日记形态突变",
                    description=(
                        f"主导形态从「{morph_type_label(prev_dominant.value)}」"
                        f"转为「{morph_type_label(curr_dominant.value)}」（间隔 {gap_days} 天）"
                    ),
                    confidence=0.55 if gap_days >= 7 else 0.5,
                    evidence=[
                        make_evidence(
                            dates[i],
                            f"形态变化: {morph_type_label(prev_dominant.value)} → {morph_type_label(curr_dominant.value)}",
                            source=EvidenceSource.INFERRED,
                        )
                    ],
                )
            )
    return anchors


def _narrative_anchors(units: list[InfoUnit], entries: list[DiaryEntry]) -> list[AnchorCard]:
    anchors: list[AnchorCard] = []
    summaries: dict[str, list[tuple[str, str]]] = defaultdict(list)

    for unit in units:
        if unit.unit_type == InfoUnitType.EVENT_PACKAGE and unit.event_package:
            s = unit.event_package.summary
            if s and len(s) > 10:
                key = s[:30]
                summaries[key].append((unit.date, s))

    for key, occurrences in summaries.items():
        if len(occurrences) >= 2:
            dates = sorted(set(d for d, _ in occurrences))
            if (datetime.strptime(dates[-1], "%Y-%m-%d") - datetime.strptime(dates[0], "%Y-%m-%d")).days >= 7:
                anchors.append(
                    AnchorCard(
                        id=str(uuid.uuid4())[:8],
                        date=dates[-1],
                        emergenceType=EmergenceType.NARRATIVE,
                        title="叙事反复引用",
                        description=f"事件「{key}…」在 {len(dates)} 个日期被反复提及",
                        confidence=0.55,
                        relatedUnitIds=[],
                        evidence=[make_evidence(d, s[:100], source=EvidenceSource.EXPLICIT) for d, s in occurrences[:3]],
                    )
                )
    return anchors


def _silence_anchors(units: list[InfoUnit], entries: list[DiaryEntry]) -> list[AnchorCard]:
    anchors: list[AnchorCard] = []
    entity_dates: dict[str, list[str]] = defaultdict(list)

    for unit in units:
        if unit.event_package and unit.event_package.participants:
            for p in unit.event_package.participants:
                entity_dates[p].append(unit.date)

    if not entries:
        return anchors
    last_date = entries[-1].date
    last_dt = datetime.strptime(last_date, "%Y-%m-%d")

    for entity, dates in entity_dates.items():
        if len(dates) < 4:
            continue
        sorted_dates = sorted(set(dates))
        gaps = []
        for i in range(1, len(sorted_dates)):
            d0 = datetime.strptime(sorted_dates[i - 1], "%Y-%m-%d")
            d1 = datetime.strptime(sorted_dates[i], "%Y-%m-%d")
            gaps.append((d1 - d0).days)
        if not gaps:
            continue
        median_gap = float(np.median(gaps))
        last_mention = datetime.strptime(sorted_dates[-1], "%Y-%m-%d")
        silence_days = (last_dt - last_mention).days
        if silence_days > median_gap * 3 and silence_days > 14:
            anchors.append(
                AnchorCard(
                    id=str(uuid.uuid4())[:8],
                    date=last_date,
                    emergenceType=EmergenceType.SILENCE,
                    title=f"「{entity}」沉默涌现",
                    description=f"曾频繁出现的「{entity}」已 {silence_days} 天未出现（通常间隔 {median_gap:.0f} 天）",
                    confidence=0.5,
                    evidence=[make_evidence(sorted_dates[-1], f"最后提及 {entity}", source=EvidenceSource.INFERRED)],
                )
            )
    return anchors


_POSITIVE_CUES = frozenset(
    {"开心", "满意", "喜欢", "希望", "轻松", "高兴", "值得", "期待", "顺利", "幸福", "感恩", "热爱"}
)
_NEGATIVE_CUES = frozenset(
    {"焦虑", "后悔", "讨厌", "担心", "失望", "痛苦", "害怕", "愤怒", "沮丧", "失败", "绝望", "内疚", "疲惫"}
)


def _text_sentiment(text: str) -> int:
    """返回 -1 / 0 / +1 粗粒度情感极性。"""
    pos = sum(1 for w in _POSITIVE_CUES if w in text)
    neg = sum(1 for w in _NEGATIVE_CUES if w in text)
    if pos > neg:
        return 1
    if neg > pos:
        return -1
    return 0


def _topic_key(unit: InfoUnit) -> str | None:
    if unit.thought_anchor and unit.thought_anchor.core_concern:
        return unit.thought_anchor.core_concern.strip()[:20]
    if unit.event_package and unit.event_package.summary:
        return unit.event_package.summary.strip()[:20]
    return None


def _contradiction_anchors(
    units: list[InfoUnit],
    entries: list[DiaryEntry],
    emotion_series: list[EmotionPoint],
) -> list[AnchorCard]:
    anchors: list[AnchorCard] = []
    emotion_by_date = {p.date: p for p in emotion_series}
    topic_occurrences: dict[str, list[tuple[str, str, int]]] = defaultdict(list)

    for unit in units:
        key = _topic_key(unit)
        if not key or len(key) < 2:
            continue
        text = unit.source_span.text if unit.source_span else ""
        sentiment = _text_sentiment(text)
        if unit.emotion_marker and unit.emotion_marker.label:
            label_sent = _text_sentiment(unit.emotion_marker.label)
            if label_sent != 0:
                sentiment = label_sent
        if sentiment == 0 and unit.date in emotion_by_date:
            val = emotion_by_date[unit.date].valence
            sentiment = 1 if val > 0.15 else (-1 if val < -0.15 else 0)
        if sentiment == 0:
            continue
        topic_occurrences[key].append((unit.date, text[:120], sentiment))

    for topic, occurrences in topic_occurrences.items():
        if len(occurrences) < 2:
            continue
        sorted_occ = sorted(occurrences, key=lambda x: x[0])
        for i in range(len(sorted_occ)):
            for j in range(i + 1, len(sorted_occ)):
                d0, t0, s0 = sorted_occ[i]
                d1, t1, s1 = sorted_occ[j]
                if s0 * s1 >= 0:
                    continue
                span = (
                    datetime.strptime(d1, "%Y-%m-%d") - datetime.strptime(d0, "%Y-%m-%d")
                ).days
                if span > 60:
                    continue
                anchors.append(
                    AnchorCard(
                        id=str(uuid.uuid4())[:8],
                        date=d1,
                        emergenceType=EmergenceType.CONTRADICTION,
                        title=f"「{topic}」自我矛盾",
                        description=f"关于「{topic}」在 {span} 天内出现相反态度（{d0} vs {d1}）",
                        confidence=min(0.75, 0.5 + span * 0.003),
                        evidence=[
                            make_evidence(d0, t0, source=EvidenceSource.EXPLICIT),
                            make_evidence(d1, t1, source=EvidenceSource.EXPLICIT),
                        ],
                    )
                )
                break
            else:
                continue
            break
    return anchors
