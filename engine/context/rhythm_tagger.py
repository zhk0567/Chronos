from __future__ import annotations

from datetime import datetime

from schemas.models import RhythmContext

WEEKDAY_LABELS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

# Approximate solar terms by month/day (simplified lookup)
SOLAR_TERMS = [
    (1, 6, "小寒"), (1, 20, "大寒"), (2, 4, "立春"), (2, 19, "雨水"),
    (3, 6, "惊蛰"), (3, 21, "春分"), (4, 5, "清明"), (4, 20, "谷雨"),
    (5, 6, "立夏"), (5, 21, "小满"), (6, 6, "芒种"), (6, 21, "夏至"),
    (7, 7, "小暑"), (7, 23, "大暑"), (8, 8, "立秋"), (8, 23, "处暑"),
    (9, 8, "白露"), (9, 23, "秋分"), (10, 8, "寒露"), (10, 23, "霜降"),
    (11, 7, "立冬"), (11, 22, "小雪"), (12, 7, "大雪"), (12, 22, "冬至"),
]


def _nearest_solar_term(month: int, day: int) -> str | None:
    best = None
    best_dist = 999
    for m, d, name in SOLAR_TERMS:
        dist = abs((month * 31 + day) - (m * 31 + d))
        if dist < best_dist and dist <= 7:
            best_dist = dist
            best = name
    return best


def _get_holiday(date_str: str) -> str | None:
    try:
        from chinese_calendar import is_holiday, get_holiday_detail

        dt = datetime.strptime(date_str, "%Y-%m-%d").date()
        if is_holiday(dt):
            detail = get_holiday_detail(dt)
            if detail and detail[1]:
                return detail[1]
            return "节假日"
    except Exception:
        pass
    return None


def tag_rhythm(date_str: str) -> RhythmContext:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    weekday = dt.weekday()
    return RhythmContext(
        weekday=weekday,
        weekdayLabel=WEEKDAY_LABELS[weekday],
        month=dt.month,
        holiday=_get_holiday(date_str),
        solarTerm=_nearest_solar_term(dt.month, dt.day),
    )
