from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime

from llm.ollama_client import make_evidence
from schemas.models import (
    AnchorCard,
    DiaryEntry,
    EmotionPoint,
    EvidenceSource,
    ChainLink,
    InfoUnit,
    InfoUnitType,
    PersonNode,
    ThemeTrack,
)

CAUSAL_KEYWORDS = ("因为", "所以", "导致", "结果", "于是", "因此", "由于")


def build_chain_links(
    anchors: list[AnchorCard],
    units: list[InfoUnit],
    themes: list[ThemeTrack],
    relationships: list[PersonNode],
    entries: list[DiaryEntry],
    emotion_series: list[EmotionPoint],
) -> tuple[list[AnchorCard], list[ChainLink]]:
    if len(anchors) < 2:
        return anchors, []

    emotion_by_date = {p.date: p.score for p in emotion_series}
    entry_by_date = {e.date: e for e in entries}
    anchor_by_id = {a.id: a for a in anchors}
    all_chains: list[ChainLink] = []

    all_chains.extend(_theme_chains(anchors, themes))
    all_chains.extend(_person_chains(anchors, units, relationships, emotion_by_date))
    all_chains.extend(_causal_chains(anchors, entry_by_date))
    all_chains.extend(_contrast_chains(anchors, themes, units, emotion_by_date))
    all_chains.extend(_evolution_chains(anchors, units, themes))

    anchor_chains: dict[str, list[ChainLink]] = defaultdict(list)
    for chain in all_chains:
        for aid in chain.anchor_ids:
            if aid in anchor_by_id:
                anchor_chains[aid].append(chain)

    updated: list[AnchorCard] = []
    for anchor in anchors:
        updated.append(anchor.model_copy(update={"chain_links": anchor_chains.get(anchor.id, [])}))

    return updated, all_chains


def _theme_chains(anchors: list[AnchorCard], themes: list[ThemeTrack]) -> list[ChainLink]:
    chains: list[ChainLink] = []
    anchor_by_date: dict[str, list[AnchorCard]] = defaultdict(list)
    for a in anchors:
        anchor_by_date[a.date].append(a)

    for theme in themes:
        theme_dates = sorted({e.date for e in theme.evidence})
        linked = []
        for d in theme_dates:
            linked.extend(anchor_by_date.get(d, []))
        linked = sorted({a.id: a for a in linked}.values(), key=lambda a: a.date)
        if len(linked) < 2:
            continue
        chains.append(
            ChainLink(
                id=str(uuid.uuid4())[:8],
                type="theme",
                anchorIds=[a.id for a in linked],
                description=f"主题「{theme.theme}」关联的 {len(linked)} 个锚点",
                confidence=0.75,
                evidence=theme.evidence[:3],
            )
        )
    return chains


def _person_chains(
    anchors: list[AnchorCard],
    units: list[InfoUnit],
    relationships: list[PersonNode],
    emotion_by_date: dict[str, float],
) -> list[ChainLink]:
    chains: list[ChainLink] = []
    person_anchors: dict[str, list[AnchorCard]] = defaultdict(list)

    unit_by_id = {u.id: u for u in units}
    for anchor in anchors:
        for uid in anchor.related_unit_ids:
            unit = unit_by_id.get(uid)
            if not unit or not unit.event_package or not unit.event_package.participants:
                continue
            for p in unit.event_package.participants:
                person_anchors[p].append(anchor)

    for person in relationships:
        linked = sorted({a.id: a for a in person_anchors.get(person.name, [])}.values(), key=lambda a: a.date)
        if len(linked) < 2:
            continue
        scores = [emotion_by_date.get(a.date, 0) for a in linked]
        tone_desc = f"情绪基调从 {scores[0]:.1f} 到 {scores[-1]:.1f}"
        chains.append(
            ChainLink(
                id=str(uuid.uuid4())[:8],
                type="person",
                anchorIds=[a.id for a in linked],
                description=f"与「{person.name}」相关的锚点序列（{tone_desc}）",
                confidence=0.7,
                evidence=person.evidence[:2],
            )
        )
    return chains


def _causal_chains(anchors: list[AnchorCard], entry_by_date: dict[str, DiaryEntry]) -> list[ChainLink]:
    chains: list[ChainLink] = []
    sorted_anchors = sorted(anchors, key=lambda a: a.date)

    for i, a1 in enumerate(sorted_anchors):
        for a2 in sorted_anchors[i + 1 :]:
            d1 = datetime.strptime(a1.date, "%Y-%m-%d")
            d2 = datetime.strptime(a2.date, "%Y-%m-%d")
            if (d2 - d1).days > 7:
                break
            entry = entry_by_date.get(a2.date)
            if not entry:
                continue
            text = entry.content
            if not any(kw in text for kw in CAUSAL_KEYWORDS):
                continue
            chains.append(
                ChainLink(
                    id=str(uuid.uuid4())[:8],
                    type="causal",
                    anchorIds=[a1.id, a2.id],
                    description=f"{a1.date} → {a2.date}：日记含因果表述",
                    confidence=0.65,
                    evidence=[
                        make_evidence(a2.date, text[:120], source=EvidenceSource.EXPLICIT),
                    ],
                )
            )
    return chains


def _contrast_chains(
    anchors: list[AnchorCard],
    themes: list[ThemeTrack],
    units: list[InfoUnit],
    emotion_by_date: dict[str, float],
) -> list[ChainLink]:
    chains: list[ChainLink] = []
    theme_dates: dict[str, set[str]] = {}
    for t in themes:
        theme_dates[t.theme] = {e.date for e in t.evidence}

    for theme, dates in theme_dates.items():
        theme_anchors = [a for a in anchors if a.date in dates]
        for i, a1 in enumerate(theme_anchors):
            for a2 in theme_anchors[i + 1 :]:
                s1 = emotion_by_date.get(a1.date)
                s2 = emotion_by_date.get(a2.date)
                if s1 is None or s2 is None:
                    continue
                if abs(s1 - s2) > 2:
                    chains.append(
                        ChainLink(
                            id=str(uuid.uuid4())[:8],
                            type="contrast",
                            anchorIds=[a1.id, a2.id],
                            description=f"主题「{theme}」下情绪对比：{s1:.1f} vs {s2:.1f}",
                            confidence=0.6,
                            evidence=a1.evidence[:1] + a2.evidence[:1],
                        )
                    )
    return chains


def _evolution_chains(
    anchors: list[AnchorCard],
    units: list[InfoUnit],
    themes: list[ThemeTrack],
) -> list[ChainLink]:
    chains: list[ChainLink] = []
    concern_anchors: dict[str, list[AnchorCard]] = defaultdict(list)
    unit_by_id = {u.id: u for u in units}

    for anchor in anchors:
        for uid in anchor.related_unit_ids:
            unit = unit_by_id.get(uid)
            if unit and unit.thought_anchor and unit.thought_anchor.core_concern:
                key = unit.thought_anchor.core_concern[:30]
                concern_anchors[key].append(anchor)

    for concern, linked in concern_anchors.items():
        linked = sorted({a.id: a for a in linked}.values(), key=lambda a: a.date)
        if len(linked) < 2:
            continue
        shift = next((t.framework_shift for t in themes if t.framework_shift), None)
        desc = f"关切「{concern}」的跨期演变"
        if shift:
            desc += f"（{shift}）"
        chains.append(
            ChainLink(
                id=str(uuid.uuid4())[:8],
                type="evolution",
                anchorIds=[a.id for a in linked],
                description=desc,
                confidence=0.68,
                evidence=[e for a in linked for e in a.evidence[:1]][:3],
            )
        )
    return chains
