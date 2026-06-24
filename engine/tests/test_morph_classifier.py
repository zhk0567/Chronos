from pipeline.morph_classifier import _topic_concern
from schemas.models import DiaryEntry
from pipeline.morph_classifier import _heuristic_extract


def test_topic_concern_detects_work():
    assert _topic_concern("今天工作很累") == "工作"
    assert _topic_concern("天气不错") is None


def test_heuristic_extract_work_creates_thought_anchor():
    entry = DiaryEntry(date="2026-01-01", content="工作压力很大，项目进度滞后，感到焦虑。")
    _, units = _heuristic_extract(entry)
    assert any(u.thought_anchor and u.thought_anchor.core_concern == "工作" for u in units)
