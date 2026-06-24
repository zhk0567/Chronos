from schemas.models import DiaryEntry
from pipeline.emotion_analyzer import score_emotions
from pipeline.theme_analyzer import _heuristic_themes, _lda_themes, _nmf_themes


def test_nmf_themes_on_work_keyword():
    entries = [
        DiaryEntry(
            date=f"2026-01-{i:02d}",
            content=f"今天工作{'顺利' if i % 2 else '很累'}，项目进度{'不错' if i % 2 else '滞后'}。" * 3,
        )
        for i in range(1, 13)
    ]
    emotion = score_emotions(entries, None, use_llm=False)
    emotion_by_date = {p.date: p.score for p in emotion}
    tracks = _nmf_themes(entries, emotion_by_date)
    assert len(tracks) >= 1


def test_lda_fallback_still_works():
    entries = [
        DiaryEntry(
            date=f"2026-01-{i:02d}",
            content=f"健身跑步第{i}天，身体状态{'好' if i % 2 else '一般'}。" * 4,
        )
        for i in range(1, 13)
    ]
    emotion = score_emotions(entries, None, use_llm=False)
    emotion_by_date = {p.date: p.score for p in emotion}
    tracks = _lda_themes(entries, emotion_by_date)
    assert isinstance(tracks, list)
