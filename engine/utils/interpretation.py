"""Plain-language interpretation helpers for report text."""

from __future__ import annotations


ANCHOR_TYPE_LABELS: dict[str, str] = {
    "intensity": "情绪强度",
    "frequency": "频率涌现",
    "structure": "写作结构",
    "narrative": "叙事重复",
    "silence": "沉默间隔",
    "contradiction": "自我矛盾",
}

TONE_TREND_LABELS: dict[str, str] = {
    "improving": "近期情绪基调有所改善",
    "declining": "近期情绪基调有所下滑",
    "stable": "情绪基调相对稳定",
    "insufficient_data": "样本不足以判断趋势",
}

LANGUAGE_TREND_LABELS: dict[str, str] = {
    "increasing": "上升",
    "decreasing": "下降",
    "stable": "稳定",
    "insufficient_data": "数据不足",
}

CONTROLLED_LABELS: dict[str, str] = {
    "weather": "天气",
    "weekday": "星期",
    "sleep": "睡眠",
    "temp": "气温",
    "precip": "降水",
}

MORPH_TYPE_LABELS: dict[str, str] = {
    "narrative": "叙事",
    "introspective": "内省",
    "sketch": "速写",
    "list": "清单",
    "mixed": "混合",
}


def anchor_type_label(emergence_type: str) -> str:
    return ANCHOR_TYPE_LABELS.get(emergence_type, emergence_type)


def morph_type_label(morph_type: str) -> str:
    return MORPH_TYPE_LABELS.get(morph_type, morph_type)


def interpret_weather_correlation(metric: str, r: float, p: float) -> str:
    strength = abs(r)
    if strength < 0.15:
        strength_note = "关联很弱，可能只是偶然波动"
    elif strength < 0.35:
        strength_note = "存在一定关联，但不宜过度解读"
    elif strength < 0.55:
        strength_note = "关联较为明显，值得留意"
    else:
        strength_note = "关联较强，可作为自我观察的参考"

    if metric == "温度":
        direction = "气温较高时，日记情绪评分倾向于更高" if r > 0 else "气温较低时，日记情绪评分倾向于更低"
    elif metric == "降水":
        direction = "降水较多时，情绪评分倾向于更高" if r > 0 else "降水较多时，情绪评分倾向于更低"
    elif metric == "日照":
        direction = "日照较多时，情绪评分倾向于更高" if r > 0 else "日照较少时，情绪评分倾向于更低"
    elif metric == "湿度":
        direction = "湿度较高时，情绪评分倾向于更高" if r > 0 else "湿度较高时，情绪评分倾向于更低"
    else:
        direction = f"{metric}与情绪呈{'正' if r > 0 else '负'}相关趋势"

    sig = "（统计上较显著）" if p < 0.05 else "（统计显著性有限）"
    return f"{direction}。{strength_note}{sig}"


def format_controlled_for(labels: list[str]) -> str:
    if not labels:
        return ""
    parts = [CONTROLLED_LABELS.get(x, x) for x in labels]
    return f"（已控制：{'、'.join(parts)}）"


def factor_implication(effect_size: float, factor_type: str) -> str:
    delta = abs(effect_size)
    if delta < 0.3:
        return "情绪变化幅度较小，可能只是日常波动。"
    direction = "升高" if effect_size > 0 else "降低"
    if factor_type == "damaging":
        return f"该因素出现后，你的情绪评分平均约 {direction} {delta:.1f} 分，值得关注其触发情境。"
    if factor_type == "pseudo_promoting":
        return f"表面上有积极感受，但情绪均值实际约 {direction} {delta:.1f} 分，可能存在「伪促进」模式。"
    return f"该因素出现后，情绪评分平均约 {direction} {delta:.1f} 分，可作为自我照顾的参考信号。"


def clean_factor_statement(statement: str) -> str:
    if " [controlled:" in statement:
        return statement.split(" [controlled:")[0].strip()
    return statement
