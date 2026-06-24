from __future__ import annotations

import uuid

import numpy as np
from scipy import stats

from llm.ollama_client import make_evidence
from schemas.models import DailyContext, EmotionPoint, EvidenceSource, WeatherInsight
from utils.interpretation import interpret_weather_correlation


def analyze_weather_insights(
    contexts: list[DailyContext],
    emotion_series: list[EmotionPoint],
    pearson_results: list | None = None,
) -> list[WeatherInsight]:
    if len(emotion_series) < 5:
        return []

    emotion_by_date = {p.date: p.score for p in emotion_series}
    ctx_by_date = {c.date: c for c in contexts}
    insights: list[WeatherInsight] = []

    rainy_scores: list[float] = []
    dry_scores: list[float] = []
    for date, score in emotion_by_date.items():
        ctx = ctx_by_date.get(date)
        if not ctx or not ctx.weather:
            continue
        precip = ctx.weather.precipitation or 0
        if precip > 0.5:
            rainy_scores.append(score)
        else:
            dry_scores.append(score)

    if len(rainy_scores) >= 3 and len(dry_scores) >= 3:
        rainy_mean = float(np.mean(rainy_scores))
        dry_mean = float(np.mean(dry_scores))
        diff = rainy_mean - dry_mean
        _, p = stats.ttest_ind(rainy_scores, dry_scores, equal_var=False)
        p = float(p) if not np.isnan(p) else 1.0
        if abs(diff) >= 0.25 or p < 0.15:
            if diff < 0:
                stmt = (
                    f"雨天日记的平均情绪为 {rainy_mean:.1f}/10，"
                    f"非雨天为 {dry_mean:.1f}/10，雨天情绪约低 {abs(diff):.1f} 分。"
                )
            else:
                stmt = (
                    f"雨天日记的平均情绪为 {rainy_mean:.1f}/10，"
                    f"非雨天为 {dry_mean:.1f}/10，雨天情绪约高 {diff:.1f} 分。"
                )
            insights.append(
                WeatherInsight(
                    id=str(uuid.uuid4())[:8],
                    type="rain_compare",
                    title="晴雨对比",
                    statement=stmt,
                    confidence=round(min(0.8, 0.45 + min(len(rainy_scores), len(dry_scores)) * 0.02), 2),
                    evidence=[
                        make_evidence(
                            emotion_series[0].date,
                            f"雨天 {len(rainy_scores)} 天 vs 非雨天 {len(dry_scores)} 天",
                            source=EvidenceSource.INFERRED,
                        )
                    ],
                    chartData={
                        "labels": ["雨天", "非雨天"],
                        "values": [round(rainy_mean, 2), round(dry_mean, 2)],
                    },
                )
            )

    temps: list[float] = []
    scores_for_temp: list[float] = []
    for date, score in emotion_by_date.items():
        ctx = ctx_by_date.get(date)
        if not ctx or not ctx.weather or ctx.weather.temp is None:
            continue
        temps.append(ctx.weather.temp)
        scores_for_temp.append(score)

    if len(temps) >= 8:
        q33, q66 = np.percentile(temps, [33, 66])
        bands: dict[str, list[float]] = {"低温": [], "舒适": [], "高温": []}
        for t, s in zip(temps, scores_for_temp):
            if t <= q33:
                bands["低温"].append(s)
            elif t >= q66:
                bands["高温"].append(s)
            else:
                bands["舒适"].append(s)

        valid = {k: v for k, v in bands.items() if len(v) >= 3}
        if len(valid) >= 2:
            means = {k: float(np.mean(v)) for k, v in valid.items()}
            lowest_band = min(means, key=means.get)
            highest_band = max(means, key=means.get)
            if means[highest_band] - means[lowest_band] >= 0.35:
                stmt = (
                    f"在「{lowest_band}」日情绪均值为 {means[lowest_band]:.1f}/10，"
                    f"「{highest_band}」日为 {means[highest_band]:.1f}/10。"
                    f"你的情绪在{highest_band}条件下相对更好。"
                )
                insights.append(
                    WeatherInsight(
                        id=str(uuid.uuid4())[:8],
                        type="temp_band",
                        title="温度区间",
                        statement=stmt,
                        confidence=0.55,
                        evidence=[
                            make_evidence(
                                emotion_series[0].date,
                                "按气温分档统计情绪均值",
                                source=EvidenceSource.INFERRED,
                            )
                        ],
                        chartData={
                            "labels": list(means.keys()),
                            "values": [round(v, 2) for v in means.values()],
                        },
                    )
                )

    sunny_scores: list[float] = []
    dull_scores: list[float] = []
    for date, score in emotion_by_date.items():
        ctx = ctx_by_date.get(date)
        if not ctx or not ctx.weather or ctx.weather.sunshine is None:
            continue
        if ctx.weather.sunshine >= 4:
            sunny_scores.append(score)
        else:
            dull_scores.append(score)

    if len(sunny_scores) >= 3 and len(dull_scores) >= 3:
        sunny_mean = float(np.mean(sunny_scores))
        dull_mean = float(np.mean(dull_scores))
        diff = sunny_mean - dull_mean
        if abs(diff) >= 0.3:
            insights.append(
                WeatherInsight(
                    id=str(uuid.uuid4())[:8],
                    type="sunshine_compare",
                    title="日照对比",
                    statement=(
                        f"日照充足日情绪均值 {sunny_mean:.1f}/10，"
                        f"日照不足日 {dull_mean:.1f}/10"
                        f"（差值 {diff:+.1f} 分）。"
                    ),
                    confidence=0.5,
                    evidence=[
                        make_evidence(
                            emotion_series[0].date,
                            f"日照充足 {len(sunny_scores)} 天",
                            source=EvidenceSource.INFERRED,
                        )
                    ],
                    chartData={
                        "labels": ["日照充足", "日照不足"],
                        "values": [round(sunny_mean, 2), round(dull_mean, 2)],
                    },
                )
            )

    if pearson_results:
        for item in pearson_results:
            metric = item.metric if hasattr(item, "metric") else item.get("metric", "")
            r = item.coefficient if hasattr(item, "coefficient") else item.get("coefficient", 0)
            desc = item.description if hasattr(item, "description") else item.get("description", "")
            p = 0.5
            if "p=" in desc:
                try:
                    p = float(desc.split("p=")[1].split(")")[0])
                except ValueError:
                    pass
            if abs(r) < 0.12:
                continue
            insights.append(
                WeatherInsight(
                    id=str(uuid.uuid4())[:8],
                    type="correlation",
                    title=f"{metric}相关性",
                    statement=interpret_weather_correlation(metric, float(r), p),
                    confidence=item.confidence if hasattr(item, "confidence") else 0.45,
                    evidence=item.evidence if hasattr(item, "evidence") else [],
                    chartData={},
                )
            )

    insights.sort(key=lambda x: -x.confidence)
    return insights[:6]
