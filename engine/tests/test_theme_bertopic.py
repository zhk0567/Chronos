from pipeline.theme_analyzer import _bertopic_themes
from schemas.models import DiaryEntry, EmotionPoint


def test_bertopic_fallback_returns_empty_without_package():
    entries = [
        DiaryEntry(date=f"2026-05-{i:02d}", content=f"测试日记内容关于工作与生活第{i}天。")
        for i in range(1, 21)
    ]
    emotion = [EmotionPoint(date=e.date, score=5.0, valence=0.0, arousal=0.5, confidence=0.8) for e in entries]
    emotion_by_date = {p.date: p.score for p in emotion}
    tracks = _bertopic_themes(entries, emotion_by_date)
    assert isinstance(tracks, list)
