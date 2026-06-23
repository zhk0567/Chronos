from __future__ import annotations

import json
import uuid
from collections import defaultdict

from llm.ollama_client import OllamaClient, make_evidence
from llm.prompts.extract import THEME_SYSTEM, THEME_USER
from schemas.models import DiaryEntry, EmotionPoint, EvidenceSource, ThemeIntensityPoint, ThemeTrack


def analyze_themes(
    entries: list[DiaryEntry],
    emotion_series: list[EmotionPoint],
    llm: OllamaClient,
    use_llm: bool = True,
) -> list[ThemeTrack]:
    emotion_by_date = {p.date: p.score for p in emotion_series}

    if use_llm and len(entries) >= 3:
        try:
            summaries = [{"date": e.date, "text": e.content[:200]} for e in entries]
            user = THEME_USER.format(summaries_json=json.dumps(summaries, ensure_ascii=False))
            data = llm.chat_json(THEME_SYSTEM, user)
            tracks = []
            for raw in data.get("themes", []):
                theme = raw.get("theme", "")
                dates = raw.get("dates", [])
                if not theme or not dates:
                    continue
                curve = _build_intensity_curve(theme, dates, entries, emotion_by_date)
                framework_shift = None
                early = raw.get("frameworkEarly")
                late = raw.get("frameworkLate")
                if early and late and early != late:
                    framework_shift = f"从「{early}」转向「{late}」"

                tracks.append(
                    ThemeTrack(
                        theme=theme,
                        firstSeen=min(dates),
                        lastSeen=max(dates),
                        peakDate=_peak_date(curve),
                        intensityCurve=curve,
                        frameworkShift=framework_shift,
                        evidence=[
                            make_evidence(
                                d,
                                next((e.content[:100] for e in entries if e.date == d), ""),
                                source=EvidenceSource.INFERRED,
                            )
                            for d in sorted(dates)[:3]
                        ],
                    )
                )
            if tracks:
                return tracks
        except Exception:
            pass

    return _heuristic_themes(entries, emotion_by_date)


def _build_intensity_curve(
    theme: str,
    dates: list[str],
    entries: list[DiaryEntry],
    emotion_by_date: dict[str, float],
) -> list[ThemeIntensityPoint]:
    curve: list[ThemeIntensityPoint] = []
    for entry in entries:
        count = entry.content.count(theme)
        if theme not in entry.content and count == 0:
            # fuzzy: check if any word from theme appears
            count = sum(1 for ch in theme if ch in entry.content) // max(1, len(theme))
        if count > 0 or entry.date in dates:
            emotion_weight = emotion_by_date.get(entry.date, 5.0) / 10.0
            intensity = count * (0.5 + emotion_weight)
            curve.append(ThemeIntensityPoint(date=entry.date, intensity=round(intensity, 2)))
    return curve


def _peak_date(curve: list[ThemeIntensityPoint]) -> str | None:
    if not curve:
        return None
    return max(curve, key=lambda p: p.intensity).date


def _heuristic_themes(
    entries: list[DiaryEntry],
    emotion_by_date: dict[str, float],
) -> list[ThemeTrack]:
    import jieba
    from collections import Counter

    word_counts: Counter[str] = Counter()
    word_dates: dict[str, list[str]] = defaultdict(list)

    stopwords = {"的", "了", "是", "在", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这", "今天", "明天", "昨天"}

    for entry in entries:
        words = [w for w in jieba.cut(entry.content) if len(w) >= 2 and w not in stopwords]
        for w in set(words):
            word_counts[w] += 1
            word_dates[w].append(entry.date)

    tracks: list[ThemeTrack] = []
    for word, count in word_counts.most_common(8):
        if count < 3:
            continue
        dates = sorted(set(word_dates[word]))
        curve = _build_intensity_curve(word, dates, entries, emotion_by_date)
        tracks.append(
            ThemeTrack(
                theme=word,
                firstSeen=dates[0],
                lastSeen=dates[-1],
                peakDate=_peak_date(curve),
                intensityCurve=curve,
                evidence=[
                    make_evidence(d, word, source=EvidenceSource.INFERRED) for d in dates[:2]
                ],
            )
        )
    return tracks
