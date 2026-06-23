from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from typing import Optional

import numpy as np

from llm.ollama_client import OllamaClient, make_evidence
from llm.prompts.extract import EMOTION_SYSTEM, EMOTION_USER
from schemas.models import (
    DiaryEntry,
    EmotionPoint,
    EvidenceSource,
    StabilityMetric,
)
from utils.baseline import rolling_zscore


def score_emotions(
    entries: list[DiaryEntry],
    llm: OllamaClient,
    use_llm: bool = True,
    chunk_size: int = 30,
) -> list[EmotionPoint]:
    if not use_llm or not entries:
        return _heuristic_emotions(entries)

    all_points: list[EmotionPoint] = []
    for start in range(0, len(entries), chunk_size):
        chunk = entries[start : start + chunk_size]
        try:
            batch = [{"date": e.date, "content": e.content[:400]} for e in chunk]
            user = EMOTION_USER.format(entries_json=json.dumps(batch, ensure_ascii=False))
            data = llm.chat_json(EMOTION_SYSTEM, user)
            for item in data.get("emotions", []):
                all_points.append(
                    EmotionPoint(
                        date=item["date"],
                        score=float(item.get("score", 5)),
                        valence=float(item.get("valence", 0)),
                        arousal=float(item.get("arousal", 0.5)),
                        confidence=float(item.get("confidence", 0.7)),
                    )
                )
        except Exception:
            all_points.extend(_heuristic_emotions(chunk))

    if all_points:
        return _fill_missing(entries, all_points)
    return _heuristic_emotions(entries)


def _fill_missing(entries: list[DiaryEntry], points: list[EmotionPoint]) -> list[EmotionPoint]:
    by_date = {p.date: p for p in points}
    result = []
    for e in entries:
        if e.date in by_date:
            result.append(by_date[e.date])
        else:
            result.append(_heuristic_one(e))
    return sorted(result, key=lambda p: p.date)


def _heuristic_emotions(entries: list[DiaryEntry]) -> list[EmotionPoint]:
    return [_heuristic_one(e) for e in entries]


def _heuristic_one(entry: DiaryEntry) -> EmotionPoint:
    pos = ["开心", "高兴", "满足", "放松", "感激", "希望", "喜欢", "幸福", "顺利"]
    neg = ["难过", "焦虑", "沮丧", "愤怒", "疲惫", "压力", "失望", "害怕", "孤独", "烦"]
    text = entry.content
    p = sum(text.count(w) for w in pos)
    n = sum(text.count(w) for w in neg)
    score = 5.0 + min(4, p) - min(4, n)
    score = max(1.0, min(10.0, score))
    valence = (p - n) / max(1, p + n)
    arousal = min(1.0, (p + n) / 10)
    return EmotionPoint(
        date=entry.date,
        score=score,
        valence=valence,
        arousal=arousal,
        confidence=0.4 if p + n == 0 else 0.55,
    )


def analyze_stability(
    emotion_series: list[EmotionPoint],
    entries: list[DiaryEntry],
) -> list[StabilityMetric]:
    metrics: list[StabilityMetric] = []
    if len(emotion_series) < 3:
        metrics.append(
            StabilityMetric(
                name="数据量",
                trend="insufficient_data",
                confidence=0.2,
                description="日记数量不足（少于3篇），无法进行可靠的稳定性分析",
                evidence=[],
            )
        )
        return metrics

    scores = np.array([p.score for p in emotion_series])
    dates = [p.date for p in emotion_series]

    # Volatility trend
    window = min(7, len(scores) // 2)
    if window >= 2:
        early_std = float(np.std(scores[:window]))
        late_std = float(np.std(scores[-window:]))
        vol_trend = "improving" if late_std < early_std * 0.9 else (
            "declining" if late_std > early_std * 1.1 else "stable"
        )
        metrics.append(
            StabilityMetric(
                name="情绪波动幅度",
                trend=vol_trend,
                value=late_std,
                confidence=0.6 if len(scores) >= 10 else 0.4,
                window=f"前{window}篇 vs 后{window}篇",
                description=f"近期情绪波动标准差为 {late_std:.2f}（早期 {early_std:.2f}）",
                evidence=[
                    make_evidence(dates[0], f"早期情绪分数 {scores[0]:.1f}", source=EvidenceSource.INFERRED),
                    make_evidence(dates[-1], f"近期情绪分数 {scores[-1]:.1f}", source=EvidenceSource.INFERRED),
                ],
            )
        )

    # Recovery time
    recovery = _compute_recovery_times(scores, dates)
    if recovery:
        avg_recovery = float(np.mean(recovery))
        metrics.append(
            StabilityMetric(
                name="情绪恢复时间",
                trend="improving" if avg_recovery < 5 else "stable",
                value=avg_recovery,
                confidence=0.5,
                window="低谷至基线天数",
                description=f"平均从情绪低谷恢复至基线约需 {avg_recovery:.1f} 天",
                evidence=[],
            )
        )

    # Differentiation
    valences = np.array([p.valence for p in emotion_series])
    val_std = float(np.std(valences))
    metrics.append(
        StabilityMetric(
            name="情绪分化度",
            trend="stable",
            value=val_std,
            confidence=0.5,
            description=f"情绪效价分化标准差 {val_std:.2f}",
            evidence=[],
        )
    )

    # Writing rhythm
    rhythm = _writing_rhythm_stability(entries)
    metrics.append(rhythm)

    return metrics


def _compute_recovery_times(scores: np.ndarray, dates: list[str]) -> list[float]:
    if len(scores) < 4:
        return []
    baseline = float(np.median(scores))
    recoveries: list[float] = []
    i = 0
    while i < len(scores):
        if scores[i] < baseline - 1.5:
            start = i
            j = i + 1
            while j < len(scores) and scores[j] < baseline:
                j += 1
            if j < len(scores):
                d0 = datetime.strptime(dates[start], "%Y-%m-%d")
                d1 = datetime.strptime(dates[j], "%Y-%m-%d")
                recoveries.append((d1 - d0).days)
            i = j
        else:
            i += 1
    return recoveries


def _writing_rhythm_stability(entries: list[DiaryEntry]) -> StabilityMetric:
    if len(entries) < 2:
        return StabilityMetric(
            name="写作节律稳定性",
            trend="insufficient_data",
            confidence=0.2,
            description="数据不足",
            evidence=[],
        )
    gaps: list[int] = []
    for i in range(1, len(entries)):
        d0 = datetime.strptime(entries[i - 1].date, "%Y-%m-%d")
        d1 = datetime.strptime(entries[i].date, "%Y-%m-%d")
        gaps.append((d1 - d0).days)
    gap_std = float(np.std(gaps))
    trend = "stable" if gap_std < 7 else "declining"
    return StabilityMetric(
        name="写作节律稳定性",
        trend=trend,
        value=gap_std,
        confidence=0.5,
        description=f"日记间隔标准差 {gap_std:.1f} 天",
        evidence=[],
    )
