from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import numpy as np

from llm.ollama_client import make_evidence
from schemas.models import (
    EmotionPoint,
    EvidenceSource,
    FactorConclusion,
    FactorType,
    InfoUnit,
    InfoUnitType,
)


def analyze_factors(
    units: list[InfoUnit],
    emotion_series: list[EmotionPoint],
) -> tuple[list[FactorConclusion], list[FactorConclusion]]:
    emotion_by_date = {p.date: p.score for p in emotion_series}
    dates = sorted(emotion_by_date.keys())
    if len(dates) < 5:
        return [], []

    candidates = _extract_factor_candidates(units)
    promoting: list[FactorConclusion] = []
    damaging: list[FactorConclusion] = []

    for name, factor_dates in candidates.items():
        if len(factor_dates) < 2:
            continue
        result = _window_analysis(name, factor_dates, emotion_by_date, dates)
        if result is None:
            continue
        if result.type == FactorType.PROMOTING:
            promoting.append(result)
        elif result.type in (FactorType.DAMAGING, FactorType.PSEUDO_PROMOTING):
            damaging.append(result)

    promoting.sort(key=lambda f: -f.effect_size)
    damaging.sort(key=lambda f: -abs(f.effect_size))
    return promoting[:10], damaging[:10]


def _extract_factor_candidates(units: list[InfoUnit]) -> dict[str, list[str]]:
    candidates: dict[str, list[str]] = {}

    for unit in units:
        names: list[str] = []
        if unit.unit_type == InfoUnitType.EVENT_PACKAGE and unit.event_package:
            if unit.event_package.activity_type:
                names.append(unit.event_package.activity_type)
            if unit.event_package.summary:
                names.append(unit.event_package.summary[:30])
        elif unit.unit_type == InfoUnitType.THOUGHT_ANCHOR and unit.thought_anchor:
            if unit.thought_anchor.cognitive_pattern:
                names.append(unit.thought_anchor.cognitive_pattern)
            if unit.thought_anchor.core_concern:
                names.append(unit.thought_anchor.core_concern[:25])

        for name in names:
            if name and len(name) >= 2:
                candidates.setdefault(name, []).append(unit.date)

    return candidates


def _window_analysis(
    name: str,
    factor_dates: list[str],
    emotion_by_date: dict[str, float],
    all_dates: list[str],
) -> FactorConclusion | None:
    date_set = set(factor_dates)
    before_scores: list[float] = []
    after_7_scores: list[float] = []
    after_30_scores: list[float] = []

    for fd in factor_dates:
        if fd not in emotion_by_date:
            continue
        idx = all_dates.index(fd) if fd in all_dates else -1
        if idx < 0:
            continue
        before = [emotion_by_date[d] for d in all_dates[max(0, idx - 7) : idx] if d in emotion_by_date]
        after_7 = [emotion_by_date[d] for d in all_dates[idx + 1 : idx + 8] if d in emotion_by_date]
        after_30 = [emotion_by_date[d] for d in all_dates[idx + 1 : idx + 31] if d in emotion_by_date]
        if before:
            before_scores.extend(before)
        if after_7:
            after_7_scores.extend(after_7)
        if after_30:
            after_30_scores.extend(after_30)

    if len(before_scores) < 2 or len(after_7_scores) < 2:
        return None

    before_mean = float(np.mean(before_scores))
    after_7_mean = float(np.mean(after_7_scores))
    delta_7 = after_7_mean - before_mean

    effect_size = _cohens_d(before_scores, after_7_scores)
    confidence = min(0.85, 0.3 + len(factor_dates) * 0.1 + min(0.3, abs(effect_size) * 0.2))

    factor_type = FactorType.PROMOTING if delta_7 > 0.3 else (
        FactorType.DAMAGING if delta_7 < -0.3 else None
    )

    if after_30_scores:
        after_30_mean = float(np.mean(after_30_scores))
        if delta_7 > 0.3 and after_30_mean < before_mean:
            factor_type = FactorType.PSEUDO_PROMOTING

    if factor_type is None:
        return None

    type_labels = {
        FactorType.PROMOTING: "促进因素",
        FactorType.DAMAGING: "损害因素",
        FactorType.PSEUDO_PROMOTING: "伪促进因素",
    }

    return FactorConclusion(
        id=str(uuid.uuid4())[:8],
        name=name,
        type=factor_type,
        effectSize=round(effect_size, 3),
        window="前7天 vs 后7天/30天",
        confidence=round(confidence, 2),
        statement=(
            f"「{name}」出现后，情绪均值从 {before_mean:.1f} 变为 {after_7_mean:.1f}"
            f"（{type_labels[factor_type]}，效应量 d={effect_size:.2f}）"
        ),
        evidence=[
            make_evidence(
                factor_dates[-1],
                f"因素「{name}」出现",
                source=EvidenceSource.INFERRED,
            )
        ],
    )


def _cohens_d(a: list[float], b: list[float]) -> float:
    if len(a) < 2 or len(b) < 2:
        return 0.0
    pooled_std = np.sqrt((np.var(a, ddof=1) + np.var(b, ddof=1)) / 2)
    if pooled_std < 0.01:
        return 0.0
    return float((np.mean(b) - np.mean(a)) / pooled_std)
