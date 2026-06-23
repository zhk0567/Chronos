from __future__ import annotations

import numpy as np

from llm.ollama_client import make_evidence
from schemas.models import DailyContext, EmotionPoint, EvidenceSource, PhysioCoupling


def analyze_physio_coupling(
    contexts: list[DailyContext],
    emotion_series: list[EmotionPoint],
) -> list[PhysioCoupling]:
    if len(emotion_series) < 10:
        return []

    dates = sorted(p.date for p in emotion_series)
    emotion_by_date = {p.date: p.score for p in emotion_series}
    ctx_by_date = {c.date: c for c in contexts}
    couplings: list[PhysioCoupling] = []

    metrics = [
        ("sleepHours", "睡眠时长"),
        ("steps", "步数"),
        ("restingHr", "静息心率"),
    ]

    for field, label in metrics:
        best_lag = 0
        best_corr = 0.0
        for lag in range(0, 8):
            xs, ys = [], []
            for i, date in enumerate(dates):
                if i < lag:
                    continue
                ctx = ctx_by_date.get(dates[i - lag])
                if not ctx or not ctx.wearable:
                    continue
                val = getattr(ctx.wearable, field, None)
                if val is None:
                    continue
                xs.append(val)
                ys.append(emotion_by_date.get(date, 0))
            if len(xs) < 8:
                continue
            r = float(np.corrcoef(xs, ys)[0, 1])
            if not np.isnan(r) and abs(r) > abs(best_corr):
                best_corr = r
                best_lag = lag

        if abs(best_corr) >= 0.25:
            leads = best_lag > 0
            couplings.append(
                PhysioCoupling(
                    metric=label,
                    lagDays=best_lag,
                    correlation=round(best_corr, 3),
                    leadsEmotion=leads,
                    description=(
                        f"{label}与情绪{'滞后' if leads else '同期'}相关 r={best_corr:.2f}"
                        + (f"（滞后 {best_lag} 天）" if leads else "")
                    ),
                    evidence=[make_evidence(dates[0], label, source=EvidenceSource.INFERRED)],
                )
            )

    return couplings
