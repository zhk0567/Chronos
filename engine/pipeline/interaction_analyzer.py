from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
from scipy import stats

from llm.ollama_client import make_evidence
from schemas.models import DailyContext, EmotionPoint, EvidenceSource, InteractionEffect


@dataclass
class _Rule:
    name_a: str
    name_b: str
    effect_type: str
    predicate_a: Callable[[DailyContext], bool]
    predicate_b: Callable[[DailyContext], bool]
    risk_direction: str  # "lower_when_both" | "higher_when_both"


def analyze_interactions(
    contexts: list[DailyContext],
    emotion_series: list[EmotionPoint],
) -> list[InteractionEffect]:
    if len(emotion_series) < 10:
        return []

    emotion_by_date = {p.date: p.score for p in emotion_series}
    ctx_by_date = {c.date: c for c in contexts}
    effects: list[InteractionEffect] = []

    wearable_cov = _source_coverage(contexts, "wearable")
    digital_cov = _source_coverage(contexts, "digital")

    rules: list[_Rule] = [
        _Rule(
            "周末",
            "日照充足",
            "protective",
            lambda c: bool(c.rhythm and c.rhythm.weekday >= 5),
            lambda c: bool(c.weather and (c.weather.sunshine or 0) > 4),
            "higher_when_both",
        ),
        _Rule(
            "高温",
            "高湿度",
            "risk",
            lambda c: bool(c.weather and c.weather.temp is not None and c.weather.temp > 30),
            lambda c: bool(c.weather and c.weather.humidity is not None and c.weather.humidity > 75),
            "lower_when_both",
        ),
        _Rule(
            "雨天",
            "周末",
            "risk",
            lambda c: bool(c.weather and (c.weather.precipitation or 0) > 1),
            lambda c: bool(c.rhythm and c.rhythm.weekday >= 5),
            "lower_when_both",
        ),
    ]

    if wearable_cov >= 0.15:
        rules.extend(
            [
                _Rule(
                    "雨天",
                    "睡眠不足",
                    "risk",
                    lambda c: bool(c.weather and (c.weather.precipitation or 0) > 1),
                    lambda c: bool(
                        c.wearable and c.wearable.sleep_hours is not None and c.wearable.sleep_hours < 6
                    ),
                    "lower_when_both",
                ),
                _Rule(
                    "低温",
                    "低步数",
                    "risk",
                    lambda c: bool(c.weather and c.weather.temp is not None and c.weather.temp < 5),
                    lambda c: bool(
                        c.wearable and c.wearable.steps is not None and c.wearable.steps < 5000
                    ),
                    "lower_when_both",
                ),
                _Rule(
                    "充足睡眠",
                    "高步数",
                    "protective",
                    lambda c: bool(
                        c.wearable and c.wearable.sleep_hours is not None and c.wearable.sleep_hours >= 7.5
                    ),
                    lambda c: bool(
                        c.wearable and c.wearable.steps is not None and c.wearable.steps >= 8000
                    ),
                    "higher_when_both",
                ),
            ]
        )

    if digital_cov >= 0.15:
        rules.append(
            _Rule(
                "工作日",
                "高屏幕时间",
                "risk",
                lambda c: bool(c.rhythm and c.rhythm.weekday < 5),
                lambda c: bool(
                    c.digital and c.digital.screen_time_min is not None and c.digital.screen_time_min > 180
                ),
                "lower_when_both",
            )
        )

    for rule in rules:
        effect = _eval_rule(rule, emotion_by_date, ctx_by_date)
        if effect:
            effects.append(effect)

    effects.sort(key=lambda e: -e.confidence)
    return effects[:6]


def _eval_rule(
    rule: _Rule,
    emotion_by_date: dict[str, float],
    ctx_by_date: dict[str, DailyContext],
) -> InteractionEffect | None:
    both: list[float] = []
    only_a: list[float] = []
    only_b: list[float] = []
    neither: list[float] = []

    for date, score in emotion_by_date.items():
        ctx = ctx_by_date.get(date)
        if not ctx:
            continue
        a = rule.predicate_a(ctx)
        b = rule.predicate_b(ctx)
        if a and b:
            both.append(score)
        elif a:
            only_a.append(score)
        elif b:
            only_b.append(score)
        else:
            neither.append(score)

    if len(both) < 3:
        return None

    if rule.risk_direction == "lower_when_both":
        control = only_a if len(only_a) >= 3 else neither
        if len(control) < 3:
            return None
        cmp = _significant_diff(both, control, expect_lower=True)
    else:
        control = neither if len(neither) >= 5 else only_a
        if len(control) < 3:
            return None
        cmp = _significant_diff(both, control, expect_lower=False)

    if not cmp:
        return None

    effect_size, p_value = cmp
    both_mean = float(np.mean(both))
    ctrl_mean = float(np.mean(control))
    return InteractionEffect(
        id=str(uuid.uuid4())[:8],
        factors=[rule.name_a, rule.name_b],
        effectType=rule.effect_type,
        combinedEffect=round(effect_size, 2),
        exceedsAdditive=p_value < 0.05,
        statement=(
            f"{rule.name_a}+{rule.name_b} 时情绪均值 {both_mean:.1f}，"
            f"对照组 {ctrl_mean:.1f}（p={p_value:.3f}）"
        ),
        confidence=min(0.75, 0.45 + (0.05 - min(p_value, 0.05))),
        evidence=[make_evidence(d, f"{rule.name_a}+{rule.name_b}", source=EvidenceSource.INFERRED) for d in list(emotion_by_date.keys())[:2]],
    )


def _significant_diff(
    group: list[float],
    control: list[float],
    expect_lower: bool,
    alpha: float = 0.1,
) -> Optional[tuple[float, float]]:
    if len(group) < 3 or len(control) < 3:
        return None
    _, p = stats.ttest_ind(group, control, equal_var=False)
    effect = float(np.mean(group) - np.mean(control))
    if p > alpha:
        return None
    if expect_lower and effect >= -0.3:
        return None
    if not expect_lower and effect <= 0.3:
        return None
    return effect, float(p)


def _source_coverage(contexts: list[DailyContext], source: str) -> float:
    if not contexts:
        return 0.0
    n = 0
    for c in contexts:
        if source == "wearable" and c.wearable and (
            c.wearable.sleep_hours is not None or c.wearable.steps is not None
        ):
            n += 1
        elif source == "digital" and c.digital and c.digital.screen_time_min is not None:
            n += 1
    return n / len(contexts)
