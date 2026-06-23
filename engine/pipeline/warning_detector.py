from __future__ import annotations

import uuid
from collections import Counter

from llm.ollama_client import make_evidence
from schemas.models import DailyContext, EmotionPoint, EvidenceSource, WarningPattern
from utils.baseline import rolling_zscore


def detect_warning_patterns(
    contexts: list[DailyContext],
    emotion_series: list[EmotionPoint],
) -> list[WarningPattern]:
    if len(emotion_series) < 10:
        return []

    scores = [p.score for p in emotion_series]
    dates = [p.date for p in emotion_series]
    zscores = rolling_zscore(scores, window=7)
    ctx_by_date = {c.date: c for c in contexts}

    drop_indices = [i for i, z in enumerate(zscores) if z < -1.5]
    if len(drop_indices) < 1:
        return []

    signal_counts: Counter[str] = Counter()
    min_count = 1 if len(drop_indices) >= 5 else 2

    for idx in drop_indices:
        for lookback in range(3, 15):
            pre_idx = idx - lookback
            if pre_idx < 0:
                break
            pre_date = dates[pre_idx]
            ctx = ctx_by_date.get(pre_date)
            if not ctx:
                continue
            signals = _collect_signals(ctx)
            if signals:
                key = "+".join(sorted(signals))
                signal_counts[key] += 1

    patterns: list[WarningPattern] = []
    for sig_key, count in signal_counts.most_common(5):
        if count < min_count:
            continue
        signals = sig_key.split("+")
        patterns.append(
            WarningPattern(
                id=str(uuid.uuid4())[:8],
                signals=signals,
                leadDays=7,
                confidence=round(min(0.8, 0.35 + count * 0.08), 2),
                statement=f"情绪低谷前反复出现：{' + '.join(signals)}（出现 {count} 次）",
                evidence=[
                    make_evidence(dates[drop_indices[0]], sig_key, source=EvidenceSource.INFERRED)
                ],
            )
        )

    return patterns


def _collect_signals(ctx: DailyContext) -> list[str]:
    signals: list[str] = []
    if ctx.weather and (ctx.weather.precipitation or 0) > 2:
        signals.append("雨天")
    if ctx.wearable and ctx.wearable.sleep_hours is not None and ctx.wearable.sleep_hours < 6:
        signals.append("睡眠不足")
    if ctx.digital and ctx.digital.screen_time_min and ctx.digital.screen_time_min > 300:
        signals.append("屏幕时间过长")
    if ctx.rhythm:
        if ctx.rhythm.weekday >= 5:
            signals.append("周末")
        if ctx.rhythm.holiday:
            signals.append("节假日前")
    return signals
