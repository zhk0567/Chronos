from __future__ import annotations

import numpy as np
import pandas as pd

from pipeline.factor_analyzer import _cohens_d, _extract_factor_candidates, _window_analysis
from schemas.models import DailyContext, EmotionPoint, FactorConclusion, InfoUnit


def analyze_controlled_factors(
    units: list[InfoUnit],
    emotion_series: list[EmotionPoint],
    contexts: list[DailyContext],
) -> tuple[list[FactorConclusion], list[FactorConclusion]]:
    promoting, damaging = _base_factors(units, emotion_series)

    ctx_by_date = {c.date: c for c in contexts}
    emotion_by_date = {p.date: p.score for p in emotion_series}
    dates = sorted(emotion_by_date.keys())

    weather_days = sum(
        1 for c in contexts if c.weather and c.weather.temp is not None
    )
    sleep_days = sum(
        1 for c in contexts if c.wearable and c.wearable.sleep_hours is not None
    )
    can_control = len(dates) >= 15 and weather_days >= 10

    if not can_control:
        for f in promoting + damaging:
            f.confidence = round(f.confidence * 0.85, 2)
        return promoting, damaging

    for flist in (promoting, damaging):
        for f in flist:
            _apply_control(f, units, emotion_by_date, dates, ctx_by_date, sleep_days)

    return promoting, damaging


def _base_factors(
    units: list[InfoUnit], emotion_series: list[EmotionPoint]
) -> tuple[list[FactorConclusion], list[FactorConclusion]]:
    from pipeline.factor_analyzer import analyze_factors

    return analyze_factors(units, emotion_series)


def _apply_control(
    factor: FactorConclusion,
    units: list[InfoUnit],
    emotion_by_date: dict[str, float],
    dates: list[str],
    ctx_by_date: dict[str, DailyContext],
    sleep_days: int,
) -> None:
    candidates = _extract_factor_candidates(units)
    factor_dates = set(candidates.get(factor.name, []))
    if len(factor_dates) < 2:
        return

    base_result = _window_analysis(factor.name, list(factor_dates), emotion_by_date, dates)
    if not base_result:
        return

    original_effect = abs(base_result.effect_size)
    ols_result = _try_ols_control(
        factor_dates, emotion_by_date, dates, ctx_by_date, sleep_days >= 10
    )

    if ols_result:
        controlled_for, new_effect = ols_result
        if original_effect > 0 and abs(new_effect) < original_effect * 0.7:
            factor.controlled_for = controlled_for
            factor.effect_size = round(new_effect, 3)
            factor.confidence = min(0.9, factor.confidence + 0.05)
            factor.statement += f"（已控制: {', '.join(controlled_for)}，效应量由 {base_result.effect_size:.2f} 调整为 {new_effect:.2f}）"
        elif controlled_for:
            factor.controlled_for = controlled_for
            factor.confidence = min(0.88, factor.confidence + 0.03)
            factor.statement += f"（已控制: {', '.join(controlled_for)}）"
        return

    controlled = _try_heuristic_control(
        factor, factor_dates, emotion_by_date, dates, ctx_by_date, base_result
    )
    if controlled:
        factor.controlled_for = controlled
        factor.confidence = min(0.9, factor.confidence + 0.05)
        factor.statement += f"（已控制: {', '.join(controlled)}）"


def _try_ols_control(
    factor_dates: set[str],
    emotion_by_date: dict[str, float],
    dates: list[str],
    ctx_by_date: dict[str, DailyContext],
    has_sleep: bool,
) -> tuple[list[str], float] | None:
    rows: list[dict] = []
    for d in dates:
        if d not in emotion_by_date:
            continue
        ctx = ctx_by_date.get(d)
        if not ctx or not ctx.weather or ctx.weather.temp is None:
            continue
        row: dict = {
            "emotion": emotion_by_date[d],
            "factor": 1.0 if d in factor_dates else 0.0,
            "temp": ctx.weather.temp or 0.0,
            "precip": ctx.weather.precipitation or 0.0,
            "weekday": ctx.rhythm.weekday if ctx.rhythm else 0,
        }
        if has_sleep and ctx.wearable and ctx.wearable.sleep_hours is not None:
            row["sleep"] = ctx.wearable.sleep_hours
        rows.append(row)

    if len(rows) < 15:
        return None

    try:
        import statsmodels.api as sm

        df = pd.DataFrame(rows)
        y = df["emotion"]
        x0 = sm.add_constant(df[["factor"]])
        m0 = sm.OLS(y, x0).fit()
        beta0 = float(m0.params.get("factor", 0))

        control_cols = ["temp", "precip", "weekday"]
        controlled_for = ["weather", "weekday"]
        if has_sleep and "sleep" in df.columns and df["sleep"].notna().sum() >= 10:
            control_cols.append("sleep")
            controlled_for.append("sleep")

        x1 = sm.add_constant(df[["factor"] + control_cols])
        m1 = sm.OLS(y, x1).fit()
        beta1 = float(m1.params.get("factor", 0))

        if abs(beta0) < 1e-6:
            return None

        change_ratio = abs(abs(beta1) - abs(beta0)) / abs(beta0)
        emotion_std = float(df["emotion"].std()) or 1.0
        new_effect = beta1 / emotion_std

        if change_ratio > 0.3:
            return controlled_for, new_effect
        if abs(beta1) < abs(beta0) * 0.85:
            return controlled_for, new_effect
    except Exception:
        return None

    return None


def _try_heuristic_control(
    factor: FactorConclusion,
    factor_dates: set[str],
    emotion_by_date: dict[str, float],
    dates: list[str],
    ctx_by_date: dict[str, DailyContext],
    base_result,
) -> list[str]:
    with_scores: list[float] = []
    without_scores: list[float] = []

    for d in dates:
        if d not in emotion_by_date or d not in factor_dates:
            continue
        ctx = ctx_by_date.get(d)
        if not ctx:
            continue
        bad_weather = ctx.weather and ctx.weather.precipitation and ctx.weather.precipitation > 5
        bad_sleep = ctx.wearable and ctx.wearable.sleep_hours is not None and ctx.wearable.sleep_hours < 6
        with_scores.append(emotion_by_date[d])
        if bad_weather or bad_sleep:
            without_scores.append(emotion_by_date[d])

    if len(with_scores) >= 3 and len(without_scores) >= 3:
        d = _cohens_d(without_scores, with_scores)
        if abs(d) > 0.3 and abs(d) < abs(base_result.effect_size) * 0.7:
            controlled: list[str] = []
            if any(ctx_by_date.get(d) and ctx_by_date[d].weather for d in factor_dates):
                controlled.append("weather")
            if any(
                ctx_by_date.get(d)
                and ctx_by_date[d].wearable
                and ctx_by_date[d].wearable.sleep_hours is not None
                for d in factor_dates
            ):
                controlled.append("sleep")
            return controlled

    return []
