from schemas.models import DailyContext, DiaryEntry, EmotionPoint, WeatherContext
from pipeline.weather_insights import analyze_weather_insights
from utils.interpretation import (
    anchor_type_label,
    clean_factor_statement,
    factor_implication,
    interpret_weather_correlation,
    morph_type_label,
)


def test_interpret_weather_correlation():
    text = interpret_weather_correlation("温度", 0.4, 0.03)
    assert "气温" in text
    assert "显著" in text or "关联" in text


def test_factor_implication_and_clean():
    stmt = "工作因素 [controlled: weather, weekday]"
    assert "controlled" not in clean_factor_statement(stmt)
    impl = factor_implication(-0.6, "damaging")
    assert "降低" in impl


def test_anchor_and_morph_labels():
    assert anchor_type_label("intensity") == "情绪强度"
    assert morph_type_label("narrative") == "叙事"


def test_rain_compare_insight():
    contexts = []
    emotions = []
    for i in range(10):
        date = f"2026-04-{i + 1:02d}"
        is_rain = i % 2 == 0
        contexts.append(
            DailyContext(
                date=date,
                weather=WeatherContext(
                    temp=15.0,
                    precipitation=5.0 if is_rain else 0.0,
                    sunshine=2.0,
                ),
            )
        )
        emotions.append(
            EmotionPoint(
                date=date,
                score=4.0 if is_rain else 7.0,
                valence=-0.2 if is_rain else 0.4,
                arousal=0.5,
                confidence=0.6,
            )
        )
    insights = analyze_weather_insights(contexts, emotions, [])
    rain = [x for x in insights if x.type == "rain_compare"]
    assert len(rain) >= 1
    assert "雨天" in rain[0].statement
